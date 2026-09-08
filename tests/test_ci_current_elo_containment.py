"""The static guard permits the audited emitter, not arbitrary research code."""

from pathlib import Path

import pytest

from brasileirao_scripts import ci_check


@pytest.fixture
def isolated_guard(tmp_path, monkeypatch):
    scripts = tmp_path / "brasileirao_scripts"
    scripts.mkdir()
    (tmp_path / "brasileirao_predictor" / "research").mkdir(parents=True)
    monkeypatch.setattr(ci_check, "ROOT", tmp_path)
    monkeypatch.setattr(ci_check, "failures", [])
    monkeypatch.setattr(ci_check, "warnings_", [])
    return tmp_path


def test_audited_h14_prospective_capture_is_allowed(isolated_guard):
    # Copy only source text. Never import or execute the prospective collector.
    actual = Path(ci_check.__file__).with_name("persist_h14_prospective.py")
    destination = isolated_guard / "brasileirao_scripts" / actual.name
    destination.write_text(actual.read_text(encoding="utf-8"), encoding="utf-8")
    ci_check.check_current_elo_containment()
    assert ci_check.failures == []
    assert ci_check.warnings_ == []


@pytest.mark.parametrize(
    "relative_path",
    [
        "brasileirao_predictor/research/new_replay.py",
        "brasileirao_scripts/new_backtest.py",
        "brasileirao_scripts/persist_h14_prospective_copy.py",
    ],
)
def test_new_research_or_similarly_named_script_still_fails(isolated_guard, relative_path):
    (isolated_guard / relative_path).write_text("ratings = db.load_elo(conn)\n", encoding="utf-8")
    ci_check.check_current_elo_containment()
    assert len(ci_check.failures) == 1
    assert relative_path in ci_check.failures[0]
    assert "fora do serving" in ci_check.failures[0]
    assert ci_check.warnings_ == []
