"""Contrato para arquitetura xG isolada, sem reativar o ensemble H12."""

from src.research.pit_features.contracts import FeatureDeclaration

ARCHITECTURE_POLICY = {
    "architecture": "ISOLATED_XG_NEW_LINEAGE",
    "forbidden": ("H12_ENSEMBLE_REUSE", "PROBABILITY_BLEND", "GRID_BLEND_WITH_SERVING"),
    "serving_integration": "PROHIBITED_IN_SCAFFOLD_PHASE",
}

DECLARATION = FeatureDeclaration(
    feature_family="isolated_xg",
    version="pit-isolated-xg/1",
    mechanism_ex_ante=(
        "xG PIT forma uma arquitetura causal independente para estimar criação "
        "e concessão; não mistura grades ou saídas do H12."
    ),
    required_source_fields=("event_id", "team", "xg", "provider_published_at"),
    output_contract=("team", "historical_xg_for", "historical_xg_against", "asof_cutoff"),
    provenance_policy=(
        "Cada xG só entra após o provedor publicá-lo e apenas em partidas cujo "
        "kickoff e disponibilidade precedem o corte."
    ),
)
