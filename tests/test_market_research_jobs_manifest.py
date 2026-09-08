"""The example manifest must not retain paths from the old scripts directory."""

import json
from pathlib import Path


def test_every_market_research_job_resolves_to_an_existing_script():
    root = Path(__file__).resolve().parent.parent
    document = json.loads((root / "jobs.market-research.example.json").read_text(encoding="utf-8"))
    for job in document["jobs"]:
        script = Path(job["command"][1])
        assert not script.is_absolute()
        assert script.parts[0] == "brasileirao_scripts"
        assert (root / script).is_file(), job["id"]
