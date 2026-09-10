"""Coverage gates must reject absent evidence without manufacturing percentages."""

import copy
import json
import sys

import pytest

from brasileirao_scripts import coverage_report as report


def payload():
    names = report.RUNTIME | report.PROVIDERS | report.KERNEL | report.EVIDENCIA | report.REDIS_INTEGRATION
    return {
        "meta": {"branch_coverage": True},
        "files": {
            name: {"summary": {"covered_lines": 8, "num_statements": 10, "covered_branches": 8, "num_branches": 10}}
            for name in names
        },
        "totals": {"percent_covered": 80.0},
    }


def invoke(tmp_path, monkeypatch, raw):
    source, output = tmp_path / "coverage.json", tmp_path / "report.md"
    source.write_text(json.dumps(raw), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["coverage-report", str(source), "--output", str(output)])
    return report.main(), output.read_text(encoding="utf-8")


def test_empty_input_cannot_approve(tmp_path, monkeypatch):
    raw = payload()
    raw["files"] = {}
    code, text = invoke(tmp_path, monkeypatch, raw)
    assert code == 1
    assert "100.00%" not in text
    assert "N/A" in text


def test_one_missing_required_file_cannot_approve(tmp_path, monkeypatch, capsys):
    raw = payload()
    missing = sorted(report.RUNTIME)[0]
    del raw["files"][missing]
    assert invoke(tmp_path, monkeypatch, raw)[0] == 1
    assert missing in capsys.readouterr().out


def test_zero_denominator_is_unknown():
    assert report._percent({}, [])[0] is None


@pytest.mark.parametrize("name", ["kernel_cli.py", "kernel_redis_v2.py"])
def test_current_kernel_surface_is_gated(name):
    assert report.classify("brasileirao_predictor/" + name) == "kernel"


def test_report_never_invents_dotnet_rates(tmp_path, monkeypatch):
    code, text = invoke(tmp_path, monkeypatch, payload())
    assert code == 0
    assert "85,15" not in text and "80,92" not in text
    assert "Cobertura" in text


def test_line_only_coverage_cannot_approve(tmp_path, monkeypatch):
    raw = payload()
    raw["meta"]["branch_coverage"] = False
    assert invoke(tmp_path, monkeypatch, raw)[0] == 1


@pytest.mark.parametrize("value", [True, -1, 11, 1.5])
def test_invalid_counts_cannot_approve(value):
    raw = payload()
    name = sorted(raw["files"])[0]
    item = copy.deepcopy(raw["files"][name])
    item["summary"]["covered_lines"] = value
    with pytest.raises(ValueError):
        report._percent({name: item}, [name])


def test_real_regression_keeps_ratchet(tmp_path, monkeypatch):
    raw = payload()
    for name in report.EVIDENCIA:
        raw["files"][name]["summary"]["covered_lines"] = 5
        raw["files"][name]["summary"]["covered_branches"] = 5
    assert report.EVIDENCIA_PISO == 56.0
    assert invoke(tmp_path, monkeypatch, raw)[0] == 1
