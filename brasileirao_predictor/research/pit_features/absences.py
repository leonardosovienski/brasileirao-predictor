"""Contrato para desfalques conhecidos antes do kickoff."""

from brasileirao_predictor.research.pit_features.contracts import FeatureDeclaration

DECLARATION = FeatureDeclaration(
    feature_family="absences",
    version="pit-absences/1",
    mechanism_ex_ante=(
        "Ausências alteram a força esperada da equipe pela indisponibilidade "
        "declarada de jogadores, sem usar o resultado."
    ),
    required_source_fields=("team", "player_id", "status", "reason", "announced_at"),
    output_contract=("team", "player_id", "availability_status", "reason_code"),
    provenance_policy=(
        "available_at é o timestamp real da publicação da fonte; coleta posterior não retroage a disponibilidade."
    ),
)
