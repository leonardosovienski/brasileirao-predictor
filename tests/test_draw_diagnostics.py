from brasileirao_predictor import display

CFG = {
    "elo": {"home_advantage": 0},
    "model": {"max_goals": 8},
    "backtest": {},
}


def test_display_exposes_draw_hypotheses_in_structured_and_human_output(capsys, monkeypatch):
    monkeypatch.setattr(display, "get_clv_summary", lambda: {})
    data = display.compute(
        "Equilibrado A",
        "Equilibrado B",
        {"Equilibrado A": 1500, "Equilibrado B": 1500},
        (0.2, 0.7, 0.1, -0.03),
        CFG,
        neutral=True,
    )

    draw = data["core"]["draw_diagnostics"]
    assert draw["modal_score_is_draw"] is True
    assert draw["side_probability_gap"] == 0
    assert draw["robust_choice"] is None

    display.render(data)
    output = capsys.readouterr().out
    assert "diagnóstico empate/incerteza" in output
    assert "gap dos líderes" in output
    assert "escolha robusta NÃO AVALIADA" in output
