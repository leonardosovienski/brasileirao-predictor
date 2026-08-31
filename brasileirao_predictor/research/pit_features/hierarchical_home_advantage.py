"""Contrato para mando por equipe com shrinkage hierárquico."""

from brasileirao_predictor.research.pit_features.contracts import FeatureDeclaration

DECLARATION = FeatureDeclaration(
    feature_family="hierarchical_home_advantage",
    version="pit-hierarchical-home-advantage/1",
    mechanism_ex_ante=(
        "O efeito de mando específico da equipe é parcialmente agrupado ao "
        "efeito da liga para controlar amostras pequenas."
    ),
    required_source_fields=("team", "venue_role", "eligible_match_ids", "asof_cutoff"),
    output_contract=("team", "home_effect_input", "league_prior_input", "eligible_n"),
    provenance_policy=(
        "Somente jogos finalizados e publicados antes do corte PIT podem compor os agregados de equipe e da liga."
    ),
)
