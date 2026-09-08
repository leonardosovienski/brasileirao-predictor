"""ZONA 3 — Kernel Python Daemon (Persistent, Zero Cold Start).

Roda como processo residente via asyncio + redis.asyncio.
Hiperparâmetros são carregados UMA VEZ no boot e mantidos em RAM.
A grade bivariada NB é computada por função Numba @njit compilada no boot
(cache=True → compilação persiste entre restarts do processo).

Tempo esperado por invocação após boot: < 15ms.

Contratos:
  Entrada  : canal Redis  "system:invoke_kernel:v2"    (JSON KernelInvokePayload)
  Saída    : chave Redis  "fair_odds:{match_id}"       (JSON FairOddsPayload, TTL 5s)
           + canal Redis  "fair_odds_ready:{match_id}" (notificação para o C#)

Inicialização:
    brasileirao-kernel --db /absolute/path/sports.db --redis "$REDIS_URL"

Não acessa disco após o boot — toda I/O é via Redis.
"""

import argparse
import asyncio
import json
import logging
import math
import os
import signal
import sys
import time
from pathlib import Path
from uuid import uuid4

import numpy as np

from brasileirao_predictor import db as _db
from brasileirao_predictor import kernel_redis_v2 as protocol

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


def _warmup_jit(params: tuple) -> float:
    """Compila a grade JIT uma vez. Retorna o tempo em ms."""
    a, b, alpha, rho, theta, max_goals = params
    lam_a, lam_b = math.exp(a), math.exp(a)
    t0 = time.perf_counter()
    _compute_grid_jit(lam_a, lam_b, alpha, abs(rho), max_goals)
    # segunda chamada: usa o cache compilado — esta é a latência real
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
    return (float(prow[0]), float(prow[1]), float(prow[2]), float(prow[3]), theta, max_goals)


# ---------------------------------------------------------------------------
# Handler de invocação (hot path)
# ---------------------------------------------------------------------------


_INVOKE_ID_FIELDS = ("job_id", "run_id", "match_id", "idempotency_key")
_INVOKE_NUMBER_FIELDS = ("elo_a", "elo_b", "dvorp_a", "dvorp_b")
_INVOKE_FIELDS = frozenset(
    (*_INVOKE_ID_FIELDS, *_INVOKE_NUMBER_FIELDS, "protocol_version", "timestamp_t3", "state_version")
)


def _parse_invoke(payload_bytes: bytes) -> dict:
    """Valida redis-protocol-v2 sem I/O nem coerção de tipos JSON."""
    msg = json.loads(payload_bytes)
    if not isinstance(msg, dict) or msg.keys() != _INVOKE_FIELDS:
        raise ValueError("campos fora do contrato")
    if msg["protocol_version"] != protocol.PROTOCOL_VERSION:
        raise ValueError("protocol_version incompatível")
    for field in _INVOKE_ID_FIELDS:
        if not isinstance(msg[field], str) or not msg[field]:
            raise ValueError("identifiers obrigatórios inválidos")
    for field in _INVOKE_NUMBER_FIELDS:
        value = msg[field]
        if type(value) not in (int, float):
            raise ValueError("entrada numérica inválida")
        value = float(value)
        if not math.isfinite(value):
            raise ValueError("entrada numérica não finita")
        msg[field] = value
    timestamp = msg["timestamp_t3"]
    # JSON Schema integer também admite representações como 1.0, mas não bool.
    if not (type(timestamp) is int or (type(timestamp) is float and timestamp.is_integer())) or timestamp < 0:
        raise ValueError("timestamp_t3 inválido")
    version = msg["state_version"]
    if (
        not isinstance(version, str)
        or not version.isascii()
        or not version.isdecimal()
        or version.startswith("0")
        or len(version) > 19
        or int(version) > 9223372036854775807
    ):
        raise ValueError("state_version inválida")
    return msg


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
    """Processa uma mensagem de kernel_invoke. Custo: < 15ms após warm-up."""
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
                async for message in pubsub.listen():
                    if message["type"] != "message":
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
    parser = argparse.ArgumentParser(description="Kernel Python Daemon — Zona 3")
    parser.add_argument("--db", default=os.environ.get("SPORTS_DB_PATH"))
    parser.add_argument("--redis", default=os.environ.get("REDIS_URL"))
    parser.add_argument("--healthcheck", action="store_true")
    args = parser.parse_args()

    if not args.db or not Path(args.db).is_absolute():
        parser.error("--db or SPORTS_DB_PATH must be an absolute path")
    if not args.redis:
        parser.error("--redis or REDIS_URL is required")

    if args.healthcheck:
        import redis

        client = redis.from_url(args.redis)
        try:
            return 0 if client.eval(protocol.HEALTHCHECK_SCRIPT, 1, protocol.HEALTH_KEY) == 1 else 1
        finally:
            client.close()

    try:
        import redis.asyncio  # noqa: F401
    except ImportError:
        sys.exit("[kernel] redis[hiredis] não instalado. Execute: pip install -r requirements-kernel.txt")

    asyncio.run(_run_daemon(args.db, args.redis))


if __name__ == "__main__":
    raise SystemExit(main())
