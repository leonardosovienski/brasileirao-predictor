"""Apply only the reviewed files and preserve the self-contained continuation package."""
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

WORK = Path(__file__).resolve().parent
SOURCE = WORK / "integration-repo"
LIVE = Path("C:/Users/Superleo13/projetos/brasileirao-predictor")
STAGE = LIVE / "docs/continuation/runtime_contracts_2026-09-07"
OUTPUT = WORK.parent / "outputs" / "MELHORIA_RUNTIME"
BACKUP = Path("C:/Users/Superleo13/projetos/brasileirao-predictor-sessoes/2026-09-07/runtime_contracts_2026-09-07")
CHANGED = [
    "brasileirao_predictor/kernel_daemon.py", "tests/test_kernel_protocol.py", "compose.yaml",
    "dotnet/LineupWorker/Models/KernelContracts.cs", "dotnet/LineupWorker/Services/MarketStateEngine.cs",
    "dotnet/LineupWorker/Worker.cs", "dotnet/LineupWorker.Tests/RedisProtocolTests.cs",
    "dotnet/LineupWorker.Tests/WorkerRuntimeTests.cs", "dotnet/LineupWorker.Tests/KernelInvocationIdentityTests.cs",
    "dotnet/LineupWorker.Tests/FairOddsCorrelationTests.cs",
]


def git(*args):
    return subprocess.check_output(["git", "-C", str(LIVE), *args], text=True, encoding="utf-8").strip()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert not git("status", "--porcelain"), "Operational worktree changed; inspect before applying"
assert not STAGE.exists() and not BACKUP.exists(), "Do not overwrite a preserved stage"
base = git("rev-parse", "HEAD")
assert base.startswith("4dfdec6")
before = {name: sha(LIVE / name) if (LIVE / name).exists() else None for name in CHANGED}
for name in CHANGED:
    assert (SOURCE / name).is_file()
    target = LIVE / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE / name, target)
    assert sha(target) == sha(SOURCE / name)
STAGE.mkdir(parents=True)
for name in CHANGED:
    target = STAGE / "codigo" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE / name, target)
for name in ("RESULTADO.md", "REPRODUZIR.md", "validation_runner.py", "VALIDAR_REDIS_ISOLADO.ps1"):
    shutil.copy2(WORK / name, STAGE / name)
shutil.copytree(WORK / "guard", STAGE / "guard", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
shutil.copytree(WORK / "validation", STAGE / "evidencias")
prior = json.loads((LIVE / "docs/continuation/review_2026-09-07/estado_final.json").read_text())
protected = {name: sha(LIVE / name) == expected for name, expected in prior["protected_sha256"].items()}
assert all(protected.values())
integrity_after = {"checked_at_utc": datetime.now(UTC).isoformat(), "protected_matches": protected, "passed": True}
(STAGE / "evidencias/integrity_after.json").write_text(json.dumps(integrity_after, indent=2) + "\n")
state = {
    "completed_at_utc": datetime.now(UTC).isoformat(), "base_commit": base,
    "operational_repo": str(LIVE), "branch": git("branch", "--show-current"),
    "commit_created": False, "push_performed": False,
    "engineering_status": "TARGETED_CHECKS_PASS_REDIS_COMPOSE_PENDING",
    "economic_status": "PROFITABILITY_NOT_DEMONSTRATED_NO_NEW_REPLAY",
    "python_tests_passed": 119, "dotnet_tests_passed": 46,
    "python_redis_tests_not_run": 1, "dotnet_redis_tests_not_run": 13,
    "full_python_suite_reexecuted": False, "compose_e2e_executed": False,
    "real_capital_enabled": False, "orders_placed": 0,
    "protected_sha256": prior["protected_sha256"], "protected_files_unchanged": all(protected.values()),
    "changed_sha256": {name: sha(LIVE / name) for name in CHANGED}, "previous_sha256": before,
    "baseline_scientific_fingerprint_preserved_reference": prior["scientific_fingerprint"],
    "scientific_fingerprint_recomputed": False,
    "pending": ["Disposable Redis Python/.NET tests", "Full isolated Compose E2E"],
}
(STAGE / "estado.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
checkpoint = """> ## CHECKPOINT — CONTRATOS DO RUNTIME CORRIGIDOS (2026-09-07, 08/09 UTC)
>
> Executado o prompt de melhoria. Cinco correções mecânicas: idempotência do
> kernel por evento+inputs; correlação de match/job/run entre canal, notificação
> e chave; validação Python completa antes de reservar a chave; odds null
> preservadas no .NET; variáveis do Compose mapeadas ao provider LINEUP_.
> Código aplicado em main, sem commit/push. Base 4dfdec6.
>
> Worktree isolado sem banco/credenciais: 119 testes Python e 46 .NET passaram;
> Ruff/formato, tipagem do kernel, restore locked, build Release e configuração
> Compose passaram. Asserções Redis do Worker foram corrigidas e compiladas,
> mas 1 teste Python Redis, 13 WorkerRuntime e Compose E2E continuam pendentes.
> Docker Desktop iniciado; engines indisponíveis e Windows negou iniciar o serviço.
> O novo preflight rejeita também docker info com exit zero e versão vazia.
>
> Conferidos 477 arquivos do backup; 14 hashes protegidos preservados antes/depois.
> Sem mudança de agenda, coorte, trial, atestado, dependências ou parâmetros.
> Sem nova busca econômica: principal 2T preservado em −1,23 u / 9 apostas / 58
> jogos avaliáveis de 190. Lucro realizável continua não demonstrado.
>
> Contexto, comandos, recibos e fontes: docs/continuation/runtime_contracts_2026-09-07/.
> Backup independente: brasileirao-predictor-sessoes/2026-09-07/runtime_contracts_2026-09-07/.
> Ler RESULTADO.md, estado.json e REPRODUZIR.md dessa etapa antes das pendências
> históricas. As 1.082 passagens gerais anteriores não foram reexecutadas agora.

"""
handoff = LIVE / "HANDOFF.md"
existing = handoff.read_text(encoding="utf-8")
heading, rest = existing.split("\n", 1)
handoff.write_text(heading + "\n\n" + checkpoint + rest.lstrip("\n"), encoding="utf-8")
resume = LIVE / "docs/continuation/RETOMADA.md"
existing = resume.read_text(encoding="utf-8")
heading, rest = existing.split("\n", 1)
notice = """> Atualização posterior nesta mesma data: [contratos do runtime](runtime_contracts_2026-09-07/RESULTADO.md)
> corrigidos, com 119 testes Python e 46 .NET direcionados aprovados. Redis/Compose
> continua pendente. Leia o primeiro checkpoint do HANDOFF e a reprodução desta
> etapa; o material abaixo preserva o encerramento anterior e seus números.

"""
resume.write_text(heading + "\n\n" + notice + rest.lstrip("\n"), encoding="utf-8")
OUTPUT.mkdir(parents=True, exist_ok=True)
shutil.copy2(STAGE / "RESULTADO.md", OUTPUT / "RESULTADO.md")
shutil.copy2(STAGE / "estado.json", OUTPUT / "estado.json")
shutil.copytree(STAGE, BACKUP)
manifest = []
for source in sorted(STAGE.rglob("*")):
    if source.is_file():
        rel = source.relative_to(STAGE)
        target = BACKUP / rel
        assert sha(source) == sha(target)
        manifest.append({"path": rel.as_posix(), "bytes": source.stat().st_size, "sha256": sha(source)})
(BACKUP / "BACKUP_MANIFEST.json").write_text(json.dumps({"created_at_utc": datetime.now(UTC).isoformat(), "files": manifest}, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"applied_files": len(CHANGED), "protected_matches": sum(protected.values()),
                  "backup_files_verified": len(manifest), "report": str(OUTPUT / "RESULTADO.md")}, indent=2))
