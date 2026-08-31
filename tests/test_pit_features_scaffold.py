from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from brasileirao_predictor.research.pit_features import (
    ExternalResearchGate,
    PITFeatureEvidence,
    assert_training_unlocked,
)
from brasileirao_predictor.research.pit_features.absences import DECLARATION as ABSENCES
from brasileirao_predictor.research.pit_features.hierarchical_home_advantage import DECLARATION as HOME
from brasileirao_predictor.research.pit_features.isolated_xg import ARCHITECTURE_POLICY
from brasileirao_predictor.research.pit_features.isolated_xg import DECLARATION as XG
from brasileirao_predictor.research.pit_features.lineup import DECLARATION as LINEUP

KICKOFF = datetime(2026, 8, 24, 22, tzinfo=UTC)


def evidence(**changes) -> PITFeatureEvidence:
    row = {
        "event_id": "123",
        "feature_family": "lineup",
        "declaration_version": LINEUP.version,
        "source": "sofascore",
        "source_record_id": "lineup-123-v1",
        "observed_at": KICKOFF - timedelta(minutes=70),
        "available_at": KICKOFF - timedelta(minutes=65),
        "ingested_at": KICKOFF - timedelta(minutes=60),
        "kickoff_at": KICKOFF,
        "payload": {"team": "A", "players": ["p1"], "confirmed": True, "published_at": "timestamp"},
    }
    row.update(changes)
    return PITFeatureEvidence.model_validate(row)


def test_todas_as_familias_declaram_mecanismo_proveniencia_e_bloqueio() -> None:
    for declaration in (ABSENCES, LINEUP, XG, HOME):
        assert declaration.mechanism_ex_ante
        assert declaration.provenance_policy
        assert declaration.training_status == "SCAFFOLD_ONLY_TRAINING_BLOCKED"


@pytest.mark.parametrize("offset", [timedelta(0), timedelta(seconds=1)])
def test_informacao_no_ou_apos_kickoff_falha_fechado(offset: timedelta) -> None:
    with pytest.raises(ValidationError, match="strictly before kickoff"):
        evidence(available_at=KICKOFF + offset, ingested_at=KICKOFF + offset)


def test_rejeita_relogio_ingenuo_e_ingestao_anterior_a_publicacao() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        evidence(available_at=datetime(2026, 8, 24, 20))
    with pytest.raises(ValidationError, match="ingested_at"):
        evidence(ingested_at=KICKOFF - timedelta(minutes=66))


def test_envelope_precisa_corresponder_a_declaracao_e_campos_ex_ante() -> None:
    item = evidence()
    item.assert_matches(LINEUP)
    with pytest.raises(ValueError, match="feature_family"):
        item.assert_matches(ABSENCES)
    with pytest.raises(ValueError, match="missing declared"):
        evidence(payload={"team": "A"}).assert_matches(LINEUP)


def test_xg_isolado_proibe_linhagem_h12_e_blends() -> None:
    assert ARCHITECTURE_POLICY["architecture"] == "ISOLATED_XG_NEW_LINEAGE"
    assert "H12_ENSEMBLE_REUSE" in ARCHITECTURE_POLICY["forbidden"]
    assert "GRID_BLEND_WITH_SERVING" in ARCHITECTURE_POLICY["forbidden"]


def test_treino_bloqueado_sem_go_e_referencia() -> None:
    with pytest.raises(RuntimeError, match="blocked"):
        assert_training_unlocked(ExternalResearchGate())
    with pytest.raises(RuntimeError, match="reference"):
        assert_training_unlocked(ExternalResearchGate(phase0b_go=True))
    assert_training_unlocked(ExternalResearchGate(live_viability_go=True, evidence_reference="report:sha256:abc"))
