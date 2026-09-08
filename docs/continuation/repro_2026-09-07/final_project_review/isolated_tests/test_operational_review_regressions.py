"""Isolated regression probes; no operational job, dataset or network is used.

Red tests document review findings. Only a temporary synthetic process tree is
started, and its leaf exits on its own after writing a marker in pytest tmp_path.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch

import pytest
import requests


OPERATIONAL_ROOT = Path(r"C:\Users\Superleo13\projetos\brasileirao-predictor")


def module_from_path(name, relative):
    spec = importlib.util.spec_from_file_location(name, OPERATIONAL_ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_example_job_resolves_to_an_existing_local_script():
    document = json.loads((OPERATIONAL_ROOT / "jobs.market-research.example.json").read_text(encoding="utf-8"))
    missing = [row["command"][1] for row in document["jobs"] if not (OPERATIONAL_ROOT / row["command"][1]).is_file()]
    assert missing == []


def test_transport_failure_does_not_propagate_key_into_exception_chain():
    module = module_from_path("exp001_review_probe", "brasileirao_scripts/exp001_data_pilot.py")
    key = "SYNTHETIC_REVIEW_KEY_NOT_A_CREDENTIAL"
    simulated = requests.ConnectionError(f"Failed to connect https://example.invalid/?apiKey={key}")
    with patch.object(module.requests, "get", side_effect=simulated):
        with pytest.raises(Exception) as caught:
            module._get("historical-odds", key)
    import traceback

    rendered = "".join(traceback.format_exception(caught.value))
    assert key not in rendered


@pytest.mark.skipif(sys.platform != "win32", reason="Windows process-tree termination regression")
def test_timeout_stops_descendants_before_marking_job_finished(tmp_path, monkeypatch):
    launcher = module_from_path("passive_review_probe", "brasileirao_scripts/run_passive_task.py")
    marker = tmp_path / "grandchild_survived.txt"
    leaf_code = "import time; from pathlib import Path; time.sleep(1.3); Path('grandchild_survived.txt').write_text('synthetic')"
    parent_code = (
        "import subprocess,sys,time\n"
        f"subprocess.Popen([sys.executable, '-c', {leaf_code!r}], creationflags=subprocess.CREATE_NO_WINDOW)\n"
        "time.sleep(20)\n"
    )
    (tmp_path / "synthetic_refresh_parent.py").write_text(parent_code, encoding="utf-8")
    monkeypatch.setattr(launcher, "ROOT", tmp_path)
    monkeypatch.setattr(launcher, "JOBS", {"fixture-refresh": ("synthetic_refresh_parent", (), 1.0)})
    assert launcher.run_job("fixture-refresh") == 124
    state = json.loads((tmp_path / "data/runtime/passive/fixture-refresh/heartbeat.json").read_text(encoding="utf-8"))
    assert state["status"] == "finished" and state["error"] == "timeout"
    # Leaf writes only after the wrapper has reported it finished, then exits.
    # This bounded delay is for this synthetic test only, not an operational job.
    time.sleep(1.0)
    assert not marker.exists(), "Timed-out job left a descendant able to perform writes after finished heartbeat"
