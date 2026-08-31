"""Contrato para escalações prováveis ou confirmadas PIT."""

from brasileirao_predictor.research.pit_features.contracts import FeatureDeclaration

DECLARATION = FeatureDeclaration(
    feature_family="lineup",
    version="pit-lineup/1",
    mechanism_ex_ante=(
        "A composição disponível antes do jogo representa força e continuidade "
        "dos onze relacionados sem usar minutos pós-jogo."
    ),
    required_source_fields=("team", "players", "confirmed", "published_at"),
    output_contract=("team", "player_ids", "lineup_confirmed", "continuity_inputs"),
    provenance_policy=(
        "available_at vem da primeira publicação observável da escalação; "
        "confirmed deve refletir o estado daquela versão."
    ),
)
