"""ZONA 3 — Kernel Python Daemon persistente com warm-up no boot.

Roda como processo residente via asyncio + redis.asyncio.
Hiperparâmetros são carregados UMA VEZ no boot e mantidos em RAM.
A grade bivariada NB é computada por função Numba @njit compilada no boot
(cache=True → compilação persiste entre restarts do processo).

Meta histórica por invocação após boot: < 15ms; não é garantia medida.

Contratos:
  Entrada  : canal Redis  "system:invoke_kernel:v2"    (JSON KernelInvokePayload)
  Saída    : chave Redis  "fair_odds:{match_id}"       (JSON FairOddsPayload, TTL 5s)
           + canal Redis  "fair_odds_ready:{match_id}" (notificação para o C#)

Inicialização:
    brasileirao-kernel --db /absolute/path/sports.db --redis "$REDIS_URL"

Não acessa disco após o boot — toda I/O é via Redis.
"""

import asyncio
import json
import logging
import math
import os
import signal
import time
from numbers import Integral, Real
from uuid import uuid4

import numpy as np

from brasileirao_predictor import db as _db
from brasileirao_predictor import kernel_redis_v2 as protocol
from brasileirao_predictor.kernel_message import parse_invoke as _parse_invoke

log = logging.getLogger("kernel_daemon")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)

# ---------------------------------------------------------------------------
# Compilação Numba da grade bivariada — zero imports scipy no hot path
# ---------------------------------------------------------------------------

try:
    from numba import njit

    @njit(cache=True)
    def _compute_grid_numba(lam_a: float, lam_b: float, alpha: float, rho: float, max_goals: int) -> np.ndarray:
        """Grade bivariada NB + correção Dixon-Coles, compilada JIT.
        Sem scipy, sem imports externos — aritmética pura com math.lgamma."""
        G = max_goals + 1
        r = 1.0 / alpha if alpha > 1e-9 else 1e9

        p_a = r / (r + lam_a)
        p_b = r / (r + lam_b)

        pa = np.empty(G)
        pb = np.empty(G)
        log_pa = math.log(p_a)
        log_1mpa = math.log(1.0 - p_a)
        log_pb = math.log(p_b)
        log_1mpb = math.log(1.0 - p_b)
        lgamma_r = math.lgamma(r)

        for k in range(G):
            lk = float(k)
            lgk1 = math.lgamma(lk + 1.0)
            pa[k] = math.exp(math.lgamma(lk + r) - lgamma_r - lgk1 + r * log_pa + lk * log_1mpa)
            pb[k] = math.exp(math.lgamma(lk + r) - lgamma_r - lgk1 + r * log_pb + lk * log_1mpb)

        grid = np.empty((G, G))
        for i in range(G):
            for j in range(G):
                grid[i, j] = pa[i] * pb[j]

        # Dixon-Coles: quatro células de placar baixo
        v00 = 1.0 - lam_a * lam_b * rho
        v01 = 1.0 + lam_a * rho
        v10 = 1.0 + lam_b * rho
        v11 = 1.0 - rho
        grid[0, 0] *= v00 if v00 > 0.0 else 0.0
        grid[0, 1] *= v01 if v01 > 0.0 else 0.0
        grid[1, 0] *= v10 if v10 > 0.0 else 0.0
        grid[1, 1] *= v11 if v11 > 0.0 else 0.0

        total = 0.0
        for i in range(G):
            for j in range(G):
                if grid[i, j] < 0.0:
                    grid[i, j] = 0.0
                total += grid[i, j]
        if total > 0.0:
            for i in range(G):
                for j in range(G):
                    grid[i, j] /= total

        return grid

    _compute_grid_jit = _compute_grid_numba
    _NUMBA_AVAILABLE = True
    log.info("[kernel] Numba disponível — grade será compilada JIT no boot.")

except ImportError:
    _NUMBA_AVAILABLE = False
    log.warning("[kernel] Numba NÃO disponível — usando NumPy puro (fallback adequado).")

    def _compute_grid_fallback(lam_a, lam_b, alpha, rho, max_goals):
        """Fallback NumPy quando Numba não está instalado."""
        from scipy.stats import nbinom

        G = max_goals + 1
        k = np.arange(G)
        r = 1.0 / max(alpha, 1e-9)
        pa = nbinom.pmf(k, r, r / (r + lam_a))
        pb = nbinom.pmf(k, r, r / (r + lam_b))
        grid = np.outer(pa, pb)
        grid[0, 0] *= max(0.0, 1.0 - lam_a * lam_b * rho)
        grid[0, 1] *= max(0.0, 1.0 + lam_a * rho)
        grid[1, 0] *= max(0.0, 1.0 + lam_b * rho)
        grid[1, 1] *= max(0.0, 1.0 - rho)
        grid = np.clip(grid, 0.0, None)
        s = grid.sum()
        return grid / s if s > 0 else grid

    _compute_grid_jit = _compute_grid_fallback


def _fair_odds_from_grid(grid: np.ndarray) -> dict:
    """Extrai fair odds (preço justo = 1/p) da grade bivariada. Vetorizado."""
    G = grid.shape[0]
    k = np.arange(G)
    totals = k[:, None] + k[None, :]

    p_home = float(np.tril(grid, -1).sum())
    p_draw = float(np.trace(grid))
    p_away = float(np.triu(grid, 1).sum())
    p_over = float(grid[totals > 2.5].sum())
    p_under = 1.0 - p_over

    def safe_odd(p):
        return round(1.0 / p, 4) if p > 1e-6 else None

    return {
        "1": safe_odd(p_home),
        "X": safe_odd(p_draw),
        "2": safe_odd(p_away),
        "o25": safe_odd(p_over),
        "u25": safe_odd(p_under),
    }


# ---------------------------------------------------------------------------
# Warm-up JIT (executa no boot para compilar o cache Numba)
# ---------------------------------------------------------------------------


def _validate_params(params: tuple) -> tuple[float, float, float, float, float, int]:
    """Reject unsafe grid dimensions and invalid coefficients before native JIT.

    The implementation supports one to 100 goals per side. This bounds native
    allocations and ensures the four low-score cells exist; it is not a fitted
    economic filter or evidence about the probability of extreme scores.
    """
    if len(params) != 6:
        raise ValueError("six kernel parameters are required")
    values = params[:5]
    try:
        if any(isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value) for value in values):
            raise ValueError("kernel coefficients must be finite real numbers")
        a, b, alpha, rho, theta = map(float, values)
    except (OverflowError, TypeError) as exc:
        raise ValueError("kernel coefficients must be finite real numbers") from exc
    maximum = params[5]
    if alpha < 0 or isinstance(maximum, bool) or not isinstance(maximum, Integral):
        raise ValueError("kernel requires nonnegative dispersion and integer max_goals in [1,100]")
    maximum = int(maximum)
    if not 1 <= maximum <= 100:
        raise ValueError("kernel requires nonnegative dispersion and integer max_goals in [1,100]")
    try:
        rate = math.exp(a)
    except OverflowError as exc:
        raise ValueError("kernel baseline rate is not representable") from exc
    if not math.isfinite(rate) or rate <= 0:
        raise ValueError("kernel baseline rate must be finite and positive")
    return a, b, alpha, rho, theta, int(maximum)


def _warmup_jit(params: tuple) -> float:
    """Compila a grade JIT uma vez. Retorna o tempo em ms."""
    a, b, alpha, rho, theta, max_goals = _validate_params(params)
    lam_a, lam_b = math.exp(a), math.exp(a)
    t0 = time.perf_counter()
    _compute_grid_jit(lam_a, lam_b, alpha, abs(rho), max_goals)
    # Segunda chamada aquecida; elapsed abaixo inclui ambas as invocações.
    _compute_grid_jit(lam_a, lam_b, alpha, abs(rho), max_goals)
    elapsed = (time.perf_counter() - t0) * 1000
    log.info("[kernel] JIT warm-up concluído em %.2f ms (2 invocações)", elapsed)
    return elapsed


# ---------------------------------------------------------------------------
# Carregamento de hiperparâmetros (uma vez no boot)
# ---------------------------------------------------------------------------


def _load_params(db_path: str) -> tuple:
    """Carrega cache compatível ou falha fechado antes de iniciar o daemon."""
    conn = _db.connect(db_path, read_only=True)
    try:
        prow = _db.load_params(conn)
        if prow and len(prow) >= 7:
            from .cron_update_models import cache_is_current
            from .ingest import load_config

            if not cache_is_current(load_config(), conn, prow):
                raise RuntimeError("cache desatualizado — rode cron_update_models primeiro")
    finally:
        conn.close()
    if not prow:
        raise RuntimeError("cache vazio — rode cron_update_models primeiro")
    theta = float(os.environ.get("KERNEL_VORP_THETA", "0.0"))
    max_goals = int(os.environ.get("KERNEL_MAX_GOALS", "12"))
    log.info(
        "[kernel] params carregados: a=%.4f b=%.4f alpha=%.4f rho=%.4f theta=%.4f",
        prow[0],
        prow[1],
        prow[2],
        prow[3],
        theta,
    )
    return _validate_params((float(prow[0]), float(prow[1]), float(prow[2]), float(prow[3]), theta, max_goals))


# ---------------------------------------------------------------------------
# Handler de invocação (hot path)
# ---------------------------------------------------------------------------


def _status(result) -> str:
    return result.decode("ascii") if isinstance(result, bytes) else str(result)


async def _release_attempt(client, keys: tuple[str, ...], raw: bytes, run_id: str, token: str) -> None:
    try:
        await asyncio.wait_for(
            client.eval(protocol.RELEASE_SCRIPT, len(keys), *keys, raw, run_id, token, protocol.RETRY_MS),
            timeout=2,
        )
    except Exception as exc:
        # An unavailable Redis cannot acknowledge release. The finite lease and
        # durable pending index retain recovery; never delete another owner's lease.
        log.warning("[kernel] liberação não confirmada run=%s erro=%s", run_id, type(exc).__name__)


async def _handle_invoke(client, payload_bytes: bytes, params: tuple) -> None:
    """Processa uma mensagem; mede a latência sem presumir cumprimento de SLA."""
    t_recv = time.perf_counter()
    try:
        msg = _parse_invoke(payload_bytes)
    except (ValueError, TypeError, OverflowError):
        log.error("[kernel] payload inválido para redis-protocol-v2")
        return

    match_id = msg["match_id"]
    job_id = msg["job_id"]
    run_id = msg["run_id"]
    a, b, alpha, rho, theta, max_goals = params

    # Rejeita taxas fora da representação numérica antes de reservar a chave.
    try:
        diff = (msg["elo_a"] - msg["elo_b"]) / 400.0
        lam_a = math.exp(a + b * diff + theta * msg["dvorp_a"])
        lam_b = math.exp(a - b * diff + theta * msg["dvorp_b"])
    except (OverflowError, ValueError):
        log.error("[kernel] taxas de gols não representáveis")
        return
    if not all(math.isfinite(rate) and rate > 0 for rate in (lam_a, lam_b)):
        log.error("[kernel] taxas de gols não positivas ou não finitas")
        return

    keys = (
        protocol.CURRENT_PREFIX + match_id,
        protocol.REQUEST_PREFIX + run_id,
        protocol.LEASE_PREFIX + run_id,
        protocol.PENDING_KEY,
        f"lineup_state:{match_id}",
    )
    token = uuid4().hex
    try:
        claimed = await client.eval(
            protocol.CLAIM_SCRIPT, len(keys), *keys, payload_bytes, run_id, token, protocol.LEASE_MS
        )
        if _status(claimed) != "CLAIMED":
            log.info("[kernel] tentativa não adquirida run=%s status=%s", run_id, _status(claimed))
            return
        # Mathematical model and grid remain unchanged; only lifecycle is v2.
        grid = _compute_grid_jit(lam_a, lam_b, alpha, rho, max_goals)
        fair = _fair_odds_from_grid(grid)
        fair.update(
            {
                "protocol_version": protocol.PROTOCOL_VERSION,
                "job_id": job_id,
                "run_id": run_id,
                "match_id": match_id,
                "idempotency_key": msg["idempotency_key"],
                "state_version": msg["state_version"],
            }
        )
        t_compute = time.perf_counter()
        payload = json.dumps(fair, allow_nan=False)
        completed = await client.eval(
            protocol.COMPLETE_SCRIPT,
            7,
            *keys[:3],
            f"fair_odds:{match_id}",
            protocol.PENDING_KEY,
            keys[4],
            protocol.READY_KEY,
            payload_bytes,
            run_id,
            token,
            payload,
            protocol.FAIR_MS,
            f"fair_odds_ready:{match_id}",
        )
        if _status(completed) != "COMPLETED":
            log.info("[kernel] conclusão recusada run=%s status=%s", run_id, _status(completed))
            await _release_attempt(client, keys, payload_bytes, run_id, token)
            return
    except asyncio.CancelledError:
        await _release_attempt(client, keys, payload_bytes, run_id, token)
        raise
    except Exception as exc:
        # This includes an uncertain EVAL response. Release checks token/status:
        # a successful completion is never reset or published twice by this path.
        await _release_attempt(client, keys, payload_bytes, run_id, token)
        log.error("[kernel] tentativa falhou run=%s erro=%s", run_id, type(exc).__name__)
        return

    t_write = time.perf_counter()

    elapsed_ms = (t_write - t_recv) * 1000
    log.info(
        "[kernel] %s -> lambda=(%.3f,%.3f) compute=%.2fms write=%.2fms total=%.2fms odds=%s",
        match_id,
        lam_a,
        lam_b,
        (t_compute - t_recv) * 1000,
        (t_write - t_compute) * 1000,
        elapsed_ms,
        payload,
    )

    if elapsed_ms > 15:
        log.warning("[kernel] LATÊNCIA ACIMA DE 15ms: %.2fms — investigar JIT ou GC.", elapsed_ms)


async def _poll_pending(client, params: tuple, stop: asyncio.Event, heartbeat_payload: str | None = None) -> None:
    """Recover durable requests after lost wake-ups, worker loss or expired leases."""
    while not stop.is_set():
        payloads = await client.eval(
            protocol.POLL_SCRIPT,
            1,
            protocol.PENDING_KEY,
            protocol.POLL_LIMIT,
            protocol.REQUEST_PREFIX,
            protocol.CURRENT_PREFIX,
            protocol.LEASE_PREFIX,
        )
        await asyncio.gather(*(_handle_invoke(client, raw, params) for raw in payloads))
        if heartbeat_payload is not None:
            await client.eval(
                protocol.HEARTBEAT_SCRIPT,
                1,
                protocol.HEALTH_KEY,
                heartbeat_payload,
                protocol.HEALTH_MS,
                "renew",
            )
        try:
            await asyncio.wait_for(stop.wait(), timeout=protocol.POLL_SECONDS)
        except TimeoutError:
            pass


# ---------------------------------------------------------------------------
# Daemon principal
# ---------------------------------------------------------------------------


def _install_stop_signals(loop, stop: asyncio.Event):
    """Install process shutdown on Unix and Windows; restore handlers on exit."""
    originals = {sig: signal.getsignal(sig) for sig in (signal.SIGTERM, signal.SIGINT)}
    installed = []
    try:
        for sig in originals:
            try:
                loop.add_signal_handler(sig, stop.set)
                installed.append(sig)
            except NotImplementedError:
                # Windows event loops do not implement add_signal_handler.
                # signal.signal requires the main thread, as does daemon main().
                signal.signal(sig, lambda *_: loop.call_soon_threadsafe(stop.set))
    except BaseException:
        for sig in installed:
            loop.remove_signal_handler(sig)
        for sig, previous in originals.items():
            signal.signal(sig, previous)
        raise

    def restore() -> None:
        for sig in installed:
            loop.remove_signal_handler(sig)
        for sig, previous in originals.items():
            signal.signal(sig, previous)

    return restore


async def _run_daemon(db_path: str, redis_url: str) -> None:
    # Boot: carrega params uma vez
    params = _load_params(db_path)

    # Warm-up JIT (compilação Numba — lenta na primeira vez, O(ms) depois)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _warmup_jit, params)

    # Graceful shutdown via SIGTERM/SIGINT
    stop = asyncio.Event()
    restore_signals = _install_stop_signals(loop, stop)
    try:
        await _serve_sessions(params, redis_url, stop)
    finally:
        restore_signals()


async def _serve_sessions(params: tuple, redis_url: str, stop: asyncio.Event) -> None:
    params = _validate_params(params)
    import redis.asyncio as aioredis
    from redis.exceptions import RedisError

    reconnect_delay = 1.0
    first_session = True

    while first_session or not stop.is_set():
        first_session = False
        client = aioredis.from_url(redis_url, decode_responses=False, socket_timeout=5, socket_connect_timeout=5)
        pubsub = client.pubsub()
        heartbeat_payload = json.dumps({"protocol_version": protocol.PROTOCOL_VERSION, "session_id": uuid4().hex})
        invocations: set[asyncio.Task[None]] = set()
        session_tasks: list[asyncio.Task] = []

        def invocation_done(task: asyncio.Task) -> None:
            invocations.discard(task)
            if not task.cancelled() and (failure := task.exception()) is not None:
                log.error("[kernel] handler encerrado com erro=%s", type(failure).__name__)

        try:
            await pubsub.subscribe(protocol.INVOKE_CHANNEL)
            await client.eval(
                protocol.HEARTBEAT_SCRIPT,
                1,
                protocol.HEALTH_KEY,
                heartbeat_payload,
                protocol.HEALTH_MS,
                "start",
            )
            reconnect_delay = 1.0
            log.info("[kernel] DAEMON PRONTO. Protocolo %s", protocol.PROTOCOL_VERSION)

            async def listen() -> None:
                deferred = 0
                async for message in pubsub.listen():
                    if message["type"] != "message":
                        continue
                    if len(invocations) >= protocol.POLL_LIMIT:
                        # Pub/Sub is only a wake-up. Registration already saved
                        # the request in the durable pending index; recovery
                        # processes it in bounded batches without queuing an
                        # unbounded number of in-memory tasks or payloads.
                        deferred += 1
                        if deferred == 1:
                            log.warning("[kernel] limite de notificações concorrentes; recuperação durável ativa")
                        continue
                    task = asyncio.create_task(_handle_invoke(client, message["data"], params))
                    invocations.add(task)
                    task.add_done_callback(invocation_done)

            listener = asyncio.create_task(listen())
            recovery = asyncio.create_task(_poll_pending(client, params, stop, heartbeat_payload))
            shutdown = asyncio.create_task(stop.wait())
            session_tasks = [listener, recovery, shutdown]
            done, _ = await asyncio.wait(session_tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                await task
        except (RedisError, OSError) as exc:
            if not stop.is_set():
                log.warning(
                    "[kernel] Redis indisponível; reconectando em %.1fs: %s",
                    reconnect_delay,
                    exc,
                )
                try:
                    await asyncio.wait_for(stop.wait(), timeout=reconnect_delay)
                except TimeoutError:
                    reconnect_delay = min(reconnect_delay * 2, 30.0)
        finally:
            # Keep this session's client alive until its handlers have released
            # their own leases (or left them to expire after unavailable Redis).
            for task in session_tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*session_tasks, return_exceptions=True)
            unfinished = tuple(invocations)
            for task in unfinished:
                task.cancel()
            await asyncio.gather(*unfinished, return_exceptions=True)
            try:
                await pubsub.unsubscribe(protocol.INVOKE_CHANNEL)
                await client.eval(
                    protocol.HEARTBEAT_SCRIPT,
                    1,
                    protocol.HEALTH_KEY,
                    heartbeat_payload,
                    protocol.HEALTH_MS,
                    "release",
                )
            except (RedisError, OSError):
                pass
            await pubsub.aclose()
            await client.aclose()

    log.info("[kernel] daemon encerrado com sucesso.")


def main():
    # Preserve python -m kernel_daemon and callers while the installed entry
    # point avoids numerical imports for --help and --healthcheck.
    from brasileirao_predictor.kernel_cli import main as cli_main

    return cli_main()


if __name__ == "__main__":
    raise SystemExit(main())
