from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_project_logic_registry_preserves_all_hypothesis_families():
    text = (ROOT / "docs" / "PROJECT_LOGIC_REGISTER.md").read_text(encoding="utf-8").lower()
    families = (
        "força das equipes",
        "geração de gols",
        "informação externa",
        "tempo:",
        "decisão:",
        "mercado:",
        "outros mercados",
        "ciência:",
        "operação:",
    )
    assert all(family in text for family in families)


def test_draw_catalog_preserves_distinct_draw_hypotheses_and_controls():
    text = (ROOT / "docs" / "DRAW_VARIABLE_CATALOG.md").read_text(encoding="utf-8")
    required = (
        "p_draw_1x2",
        "modal_score_is_draw",
        "draw_is_1x2_argmax",
        "balanced_sides",
        "low_scoring",
        "lambda_total",
        "lambda_gap",
        "rho_dc",
        "top_1x2_gap",
        "side_probability_gap",
        "draw_vs_best_side_gap",
        "entropy_1x2",
        "diagonal_concentration",
        "Brier binário específico para `draw`",
        "calibração/reliability de `p_draw`",
        "não é regra validada",
    )
    assert all(item in text for item in required)
