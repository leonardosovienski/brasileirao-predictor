from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUTS = ROOT / "outputs"
REPO = ROOT / "work" / "brasileirao-predictor"
FILES = [
    "HANDOFF.md",
    "brasileirao_scripts/evaluate_h14_prospective.py",
    "brasileirao_scripts/evaluate_h15_prospective.py",
    "brasileirao_scripts/price_discovery_preflight.py",
    "docs/ESTADO_LOCAL_E_OPERACAO.md",
    "tests/test_price_discovery_preflight.py",
    "tests/test_prospective_evaluation_guard.py",
]
DELIVERIES = [
    "VALIDACAO_BRASILEIRAO.md",
    "COMO_REPRODUZIR.md",
    "estado_operacional_observado.json",
    "price_discovery_preflight.json",
    "testes_validacao.txt",
    "alteracoes.patch",
]
payloads = {name: (OUTPUTS / name).read_bytes() for name in DELIVERIES}
payloads.update({"arquivos/" + name: (REPO / name).read_bytes() for name in FILES})
manifest = {
    "schema_version": "brasileirao-validation-delivery/1",
    "base_commit": "02b8d88fa0b15ba28565351848a9737b2edcda48",
    "operational_commit_observed": "7b5f833",
    "delivery_state": "ISOLATED_WORKING_COPY_AND_PATCH_ONLY",
    "horizon_decision": "AWAITING_OPERATOR",
    "tests": {"passed": 70, "full_ci_run": False},
    "ruff_check": "PASS",
    "ruff_format_check": {"status": "PASS", "files": 344},
    "git_diff_check": "PASS",
    "git_apply_check_against_clean_base": "PASS",
    "protected_contracts_data_collector_dependencies_diff": "EMPTY",
    "real_cohort_contents_read": False,
    "tasks_changed": False,
    "real_capital_used": False,
    "cost_brl": 0,
    "files": {
        name: {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        for name, data in sorted(payloads.items())
    },
}
manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
(OUTPUTS / "manifesto_entrega.json").write_bytes(manifest_bytes)
payloads["manifesto_entrega.json"] = manifest_bytes
archive = OUTPUTS / "validacao_brasileirao.zip"
with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as handle:
    for name, data in sorted(payloads.items()):
        handle.writestr(name, data)
with zipfile.ZipFile(archive) as handle:
    assert handle.testzip() is None
    for name, info in manifest["files"].items():
        assert hashlib.sha256(handle.read(name)).hexdigest() == info["sha256"]
print(json.dumps({"archive": str(archive), "bytes": archive.stat().st_size, "entries": len(payloads), "sha256": hashlib.sha256(archive.read_bytes()).hexdigest()}))
