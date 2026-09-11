"""Exercise the portable runner's real I/O boundaries before publication."""

import copy
import socket
import subprocess
import sys
from pathlib import Path

import pytest

from tools.publication_validation.compose_config import isolate

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("name", ["config.yaml", ".env", "data/trials.json", "reports/never-open.json"])
def test_protected_reads_are_refused_before_open(name):
    with pytest.raises(PermissionError, match="private_or_protected"):
        (ROOT / name).read_bytes()


def test_network_is_refused():
    with pytest.raises(PermissionError, match="network_or_subprocess"):
        socket.create_connection(("127.0.0.1", 9), timeout=0.1)


def test_subprocess_is_refused():
    with pytest.raises(PermissionError, match="network_or_subprocess"):
        subprocess.run([sys.executable, "-c", "raise SystemExit(99)"], check=True)


def test_checkout_mutation_is_refused():
    with pytest.raises(PermissionError, match="write_outside"):
        (ROOT / ".publication-guard-write-probe").write_text("must never be created", encoding="utf-8")


def spec(repo):
    return {
        "services": {
            "worker": {
                "environment": {"LINEUP_Exchange__WebSocketUrl": "wss://example.invalid"},
                "volumes": [
                    {"type": "bind", "source": str(repo / "config.yaml"), "target": "/app/config.yaml"},
                    {"type": "bind", "source": str(repo / "docker"), "target": "/app/config"},
                    {"type": "volume", "source": "app-data", "target": "/app/data"},
                ],
            }
        }
    }


def test_compose_uses_only_synthetic_configuration(tmp_path):
    raw = spec(ROOT)
    snapshot = copy.deepcopy(raw)
    actual = isolate(raw, ROOT, tmp_path)
    worker = actual["services"]["worker"]
    assert worker["volumes"][0]["source"] == str(tmp_path / "config.json")
    assert worker["volumes"][1]["source"] == snapshot["services"]["worker"]["volumes"][1]["source"]
    assert worker["environment"]["LINEUP_Exchange__WebSocketUrl"] == ""
    assert worker["environment"]["LINEUP_Worker__AllowSyntheticInputs"] == "true"


def test_compose_refuses_unreviewed_host_mount(tmp_path):
    raw = spec(ROOT)
    raw["services"]["worker"]["volumes"].append({"type": "bind", "source": str(tmp_path), "target": "/operational"})
    with pytest.raises(ValueError, match="unexpected_host_mount"):
        isolate(raw, ROOT, tmp_path)
