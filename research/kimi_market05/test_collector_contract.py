"""test_collector_contract.py — Testes contratuais do Gate A1 (MARKET-05).

Estes testes definem o contrato do coletor ANTES dele existir.
O coletor só é considerado implementado quando todos passarem.
Integração esperada: copiar para tests/ do brasileirao-predictor e ajustar
os imports para o módulo real do coletor.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

KICKOFF = datetime(2026, 9, 1, 19, 0, tzinfo=UTC)
T0 = KICKOFF - timedelta(hours=2)


def make_snapshot(**over):
    base = {
        "snapshot_id": "a" * 64,
        "event_id": "br-serie-a|2026|flamengo|palmeiras|2026-09-01",
        "bookmaker": "pinnacle",
        "market": "1X2",
        "line": None,
        "selection": "home",
        "odd": 1.95,
        "captured_at": T0.isoformat(),
        "kickoff_at": KICKOFF.isoformat(),
        "source_id": "odds_api_v4",
        "mapping_version": "2026-08-24.v1",
        "market_status": "open",
        "hash_prev": "GENESIS",
    }
    base.update(over)
    return base


# ------------------------------------------------------------------
# Contrato 1: PIT estrito — nenhum snapshot com captured_at >= kickoff
# ------------------------------------------------------------------
class TestPIT:
    def test_pos_kickoff_rejeitado(self, collector):
        with pytest.raises(ValueError):
            collector.ingest(make_snapshot(captured_at=(KICKOFF + timedelta(seconds=1)).isoformat()))

    def test_exatamente_no_kickoff_rejeitado(self, collector):
        with pytest.raises(ValueError):
            collector.ingest(make_snapshot(captured_at=KICKOFF.isoformat()))

    def test_timezone_naive_rejeitado(self, collector):
        with pytest.raises(ValueError):
            collector.ingest(make_snapshot(captured_at="2026-09-01T17:00:00"))  # sem timezone


# ------------------------------------------------------------------
# Contrato 2: odds válidas
# ------------------------------------------------------------------
class TestOdds:
    @pytest.mark.parametrize("odd", [0.5, 1.0, -2.0, float("nan"), float("inf"), 1001.0])
    def test_odd_invalida_vai_para_quarentena(self, collector, odd):
        result = collector.ingest(make_snapshot(odd=odd))
        assert result.status == "quarantine"

    def test_odd_limite_aceita(self, collector):
        assert collector.ingest(make_snapshot(odd=1.01)).status == "accepted"
        assert collector.ingest(make_snapshot(odd=1000.0)).status == "accepted"


# ------------------------------------------------------------------
# Contrato 3: identidade canônica
# ------------------------------------------------------------------
class TestIdentidade:
    def test_alias_desconhecido_vai_para_quarentena(self, collector):
        result = collector.ingest_raw(
            home="CR Flamengo",  # nome fora da alias table
            away="SE Palmeiras",
            kickoff=KICKOFF,
            bookmaker="bet365",
        )
        assert result.identity_status == "unresolved"

    def test_fuzzy_nao_resolve_sozinho(self, collector):
        """Fuzzy matching pode sugerir, jamais resolver automaticamente."""
        result = collector.ingest_raw(
            home="Flamengo RJ",  # variação plausível mas não registrada
            away="Palmeiras SP",
            kickoff=KICKOFF,
            bookmaker="bet365",
        )
        assert result.identity_status == "unresolved"
        assert result.suggested_alias is not None  # sugestão para humano

    def test_event_id_canonico_estavel(self, collector):
        """Mesma partida vinda de duas fontes → mesmo event_id."""
        e1 = collector.ingest_raw(home="Flamengo", away="Palmeiras", kickoff=KICKOFF, bookmaker="pinnacle")
        e2 = collector.ingest_raw(home="Flamengo", away="Palmeiras", kickoff=KICKOFF, bookmaker="bet365")
        assert e1.event_id == e2.event_id


# ------------------------------------------------------------------
# Contrato 4: append-only e hash-chain
# ------------------------------------------------------------------
class TestImutabilidade:
    def test_nenhuma_linha_editada(self, collector, tmp_path):
        snap = make_snapshot()
        collector.ingest(snap)
        before = Path(collector.current_file).read_bytes()
        with pytest.raises((PermissionError, NotImplementedError, AttributeError)):
            collector.edit(snap["snapshot_id"], odd=2.0)  # não deve existir API de edição
        assert Path(collector.current_file).read_bytes() == before

    def test_correcao_cria_nova_linha_com_supersedes(self, collector):
        s1 = collector.ingest(make_snapshot(odd=1.90))
        s2 = collector.correct(s1.snapshot_id, odd=1.95)
        assert s2.supersedes == s1.snapshot_id
        assert len(collector.all_snapshots()) == 2  # original preservado

    def test_hash_chain_integro(self, collector):
        for i in range(10):
            collector.ingest(make_snapshot(odd=1.90 + i * 0.01))
        assert collector.verify_chain() is True
        # adulterar uma linha quebra a cadeia
        collector.tamper_for_test(3)
        assert collector.verify_chain() is False


# ------------------------------------------------------------------
# Contrato 5: deduplicação e conflitos
# ------------------------------------------------------------------
class TestDedupe:
    def test_duplicata_exata_dedupada(self, collector):
        s = make_snapshot()
        collector.ingest(s)
        collector.ingest(s)
        assert len(collector.all_snapshots()) == 1

    def test_mesmo_segundo_odd_diferente_marca_conflito(self, collector):
        collector.ingest(make_snapshot(odd=1.90))
        collector.ingest(make_snapshot(odd=1.95))  # mesma chave, odd diferente
        snaps = collector.all_snapshots()
        assert len(snaps) == 2
        assert all(s.get("conflict") for s in snaps)
        assert collector.coverage_metrics()["conflict_rate"] > 0


# ------------------------------------------------------------------
# Contrato 6: suspensão e linhas
# ------------------------------------------------------------------
class TestMercado:
    def test_suspended_excluido_de_coverage_operavel(self, collector):
        collector.ingest(make_snapshot(market_status="suspended"))
        m = collector.coverage_metrics()
        assert m["operable_coverage"] == 0.0

    def test_linha_nova_nao_reescreve_antiga(self, collector):
        collector.ingest(make_snapshot(market="OU", line=2.5, selection="over", odd=1.9))
        collector.ingest(make_snapshot(market="OU", line=3.0, selection="over", odd=2.1))
        lines = {s["line"] for s in collector.all_snapshots() if s["market"] == "OU"}
        assert lines == {2.5, 3.0}

    def test_evento_reagendado_novo_event_id(self, collector):
        ko2 = KICKOFF + timedelta(days=1)
        e1 = collector.ingest_raw(home="Flamengo", away="Palmeiras", kickoff=KICKOFF, bookmaker="pinnacle")
        e2 = collector.ingest_raw(home="Flamengo", away="Palmeiras", kickoff=ko2, bookmaker="pinnacle")
        assert e1.event_id != e2.event_id


# ------------------------------------------------------------------
# Contrato 7: separação coletor/detector
# ------------------------------------------------------------------
class TestSeparacaoDetector:
    def test_detector_rejeita_snapshot_nao_homologado(self, collector, detector):
        collector.ingest(make_snapshot(homologated=False))
        with pytest.raises(PermissionError):
            detector.feed(collector.all_snapshots())

    def test_homologated_so_com_gate_a1_pass(self, collector):
        with pytest.raises(PermissionError):
            collector.mark_homologated()  # sem Gate A1 PASS registrado


# ------------------------------------------------------------------
# Contrato 8: proibições do gate
# ------------------------------------------------------------------
class TestProibicoes:
    def test_coletor_nao_tem_api_de_roi_ou_stake(self, collector):
        for attr in ["roi", "stake", "place_bet", "calculate_ev"]:
            assert not hasattr(collector, attr), f"coletor não deve expor {attr}"

    def test_sofascore_nao_e_fonte(self, collector):
        with pytest.raises(ValueError):
            collector.register_source("sofascore_aggregate")


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------
@pytest.fixture
def collector():
    """Instância do coletor real (a implementar no projeto)."""
    pytest.skip("implementar coletor conforme MARKET_05_A1_COLLECTOR_SPEC.md")


@pytest.fixture
def detector():
    """Instância do structural_edge (já existe no projeto)."""
    pytest.skip("integrar com src/research/structural_edge.py")
