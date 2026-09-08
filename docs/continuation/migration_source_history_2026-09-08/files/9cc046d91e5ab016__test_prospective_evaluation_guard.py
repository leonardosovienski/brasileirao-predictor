"""Relatório existente impede nova avaliação e divulgação de métricas."""

import json
from unittest.mock import Mock

import pytest

from brasileirao_scripts import evaluate_h14_prospective as h14
from brasileirao_scripts import evaluate_h15_prospective as h15


@pytest.mark.parametrize(("job", "prefix"), [(h14, "h14"), (h15, "h15")])
def test_relatorio_existente_impede_avaliacao_e_saida_de_metricas(job, prefix, tmp_path, monkeypatch, capsys):
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    report = reports_dir / f"{prefix}_avaliacao_2027-01-01T000000Z.json"
    report.write_text('{"synthetic": true}\n', encoding="utf-8")
    original = report.read_bytes()
    evaluate = Mock(side_effect=AssertionError("não pode ler ou avaliar a coorte"))
    monkeypatch.setattr(job, "REPORTS_DIR", reports_dir)
    monkeypatch.setattr(job, "evaluate", evaluate)

    assert job.main() == 1

    evaluate.assert_not_called()
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Nenhuma avaliação foi executada." in captured.err
    assert report.read_bytes() == original
    assert list(reports_dir.iterdir()) == [report]


@pytest.mark.parametrize("job", [h14, h15], ids=["h14", "h15"])
def test_primeira_chamada_aguardando_n_permanece_permitida(job, tmp_path, monkeypatch, capsys):
    reports_dir = tmp_path / "reports"
    result = {"status": "AGUARDANDO_N", "n": 3, "min_n_avaliacao": 900, "faltam": 897}
    evaluate = Mock(return_value=result)
    monkeypatch.setattr(job, "REPORTS_DIR", reports_dir)
    monkeypatch.setattr(job, "evaluate", evaluate)

    assert job.main() == 0

    evaluate.assert_called_once_with()
    captured = capsys.readouterr()
    assert json.loads(captured.out) == result
    assert captured.err == ""
    assert not reports_dir.exists()
