"""Apply the user's round split in an independent paper-research namespace."""
import hashlib
import json
import shutil
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from split_policy import DECISION_LEAD_HOURS, eligibility_for_paper, role_for

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parents[1]
REPO = Path(r"C:\Users\Superleo13\projetos\brasileirao-predictor")
OUT = WORKSPACE / "outputs/DIVISAO_2026"
DATA = REPO / "data/research/season_2026_turn_split"
CONTRACT = REPO / "contracts/season-2026-turn-split-paper.json"
SOURCE_URL = "https://stcbfsiteprdimgbrs.blob.core.windows.net/img-site/cdn/Tabela_BA_sica_Brasileiro_SA_rie_A_2026_d64996b4d8.pdf"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")


def main():
    assert not CONTRACT.exists(), "Existing contract must be versioned rather than overwritten"
    OUT.mkdir(exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    rows = json.loads((ROOT / "schedule_manifest.json").read_text(encoding="utf-8"))
    assert len(rows) == 380 and len({r['event_id'] for r in rows}) == 380
    assert all(r['identity_status'] == 'MATCHED' for r in rows)
    freeze = datetime.now(timezone.utc)
    for row in rows:
        assert row['role'] == role_for(row['season'], row['round'])
        row['current_paper_state'] = eligibility_for_paper(row['role'], row['kickoff_at'], freeze, False, False, False)
        row['decision_at'] = (datetime.fromisoformat(row['kickoff_at'].replace('Z','+00:00')) - timedelta(hours=DECISION_LEAD_HOURS)).isoformat() if row['kickoff_at'] else None
        row['bet_placed'] = False
    roles = Counter(r['role'] for r in rows)
    assert roles == {'test_exploratory':190, 'paper_betting':190}
    second = [r for r in rows if r['role'] == 'paper_betting']
    states = Counter(r['current_paper_state'] for r in second)
    # No outcomes, odds, forecasts or protected ledgers are loaded here.
    save(DATA / "schedule_manifest.json", rows)
    historical = json.loads((ROOT / 'historical_metadata_counts.json').read_text(encoding='utf-8'))
    contract = {
        "id": "SEASON-2026-TURN-SPLIT-PAPER-V1",
        "frozen_at": freeze.isoformat(),
        "user_instruction": "considera o segundo turno de 2026 como inteiro como pra apostar ok? o primeiro como teste e o resto vc escolhe",
        "scope": "New evaluation namespace; older studies and protected cohorts remain as originally recorded",
        "execution_mode": "paper",
        "capital_enabled": False,
        "splits": [
            {"seasons":[2021,2022,2023,2024],"role":"train","purpose":"model estimation/development before later-year evaluation"},
            {"seasons":[2025],"role":"calibration","purpose":"calibration and rule choice before evaluating2026"},
            {"seasons":[2026],"rounds_inclusive":[1,19],"role":"test_exploratory","expected_fixtures":190,"fit_allowed":False},
            {"seasons":[2026],"rounds_inclusive":[20,38],"role":"paper_betting","expected_fixtures":190,"fit_allowed":False},
        ],
        "round_source": SOURCE_URL,
        "round_source_pdf_sha256": sha(ROOT/'cbf_tabela_basica_2026.pdf'),
        "schedule_manifest": "data/research/season_2026_turn_split/schedule_manifest.json",
        "schedule_manifest_sha256": sha(DATA/'schedule_manifest.json'),
        "role_key": "season + official CBF round; official fixture linked by ordered home/away identities, never chronological encounter count",
        "postponed_games": "retain original round; never use future labels to approve an earlier paper decision",
        "decision_before_kickoff_hours": DECISION_LEAD_HOURS,
        "historical_second_turn": "decisions at/before frozen_at may only be reconstructed as exploratory replay, never backdated prospective bets",
        "future_second_turn": "paper signal requires decision later than frozen_at, candidate and price attested available no later than decision, and a passed economic criterion",
        "model_selection_source": "2025 calibration, without optimizing on either2026turn",
        "current_candidate": None,
        "current_candidate_note": "No strategy was promoted. The prior price candidate failed its additional51fixture study; changing the split does not revive it.",
        "bet_every_fixture": False,
        "max_virtual_bets_per_fixture": 1,
        "missing_policy": "retain every scheduled fixture; missing time=>pending, missing eligible candidate/price/economic criterion=>NO_BET; do not invent odds, outcomes or dates",
        "research_history": "2025/2026 have already been examined, including first-turn price training/testing. This is an exploratory reorganization, not an untouched holdout or erasure of past searches.",
        "prior_studies": "Do not rewrite H14/H15/H9/A1 source, cohort ledgers, contracts or closed study results",
        "operational_change": "Added explicit split contract, metadata universe and pure paper classifier; no scheduler or live decision runner changed",
        "identity_resolutions": [r['identity_resolution'] for r in rows if 'identity_resolution' in r],
        "sources": [SOURCE_URL, "https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-a/2026/botafogo-x-gremio/832091?view=escalacao"],
    }
    save(CONTRACT, contract)
    module = REPO / "brasileirao_predictor/research/season_2026_split.py"
    test = REPO / "tests/test_season_2026_split.py"
    assert not module.exists() and not test.exists()
    shutil.copyfile(ROOT/'split_policy.py', module)
    test_source = (ROOT/'test_split_policy.py').read_text(encoding='utf-8').replace(
        'from split_policy import DECISION_LEAD_HOURS, eligibility_for_paper, role_for',
        'from brasileirao_predictor.research.season_2026_split import DECISION_LEAD_HOURS, eligibility_for_paper, role_for')
    test.write_text(test_source, encoding='utf-8')
    summary = {'id':contract['id'], 'frozen_at':freeze.isoformat(), 'historical_counts':historical,
               'roles':dict(roles), 'second_turn_states':dict(states), 'local_rows_before_identity_dedup':386,
               'canonical_fixtures':380, 'duplicate_rows_not_double_counted':6,
               'rounds':dict(Counter(r['round'] for r in rows)),
               'matches_confirmed_finished': 'not assessed; no result fields read',
               'bets_placed':0, 'profit_computed':False, 'candidate_promoted':False}
    save(OUT/'resumo.json', summary)
    for source, name in [(CONTRACT,'contrato.json'),(DATA/'schedule_manifest.json','jogos_2026.json'),
                         (module,'season_2026_split.py'),(test,'test_season_2026_split.py'),
                         (ROOT/'build_manifest.py','build_manifest.py')]:
        shutil.copyfile(source, OUT/name)
    decision = f"""# Decisão — divisão de 2026 por turnos

O usuário determinou o primeiro turno como teste e todo o segundo como universo
para apostar; neste projeto a execução permanece simulada. Definimos 2021–2024
para treino e 2025 para calibração. Rodadas oficiais 1–19/20–38 fornecem 190 jogos
em cada grupo. Esta divisão vale para a nova avaliação, sem reescrever estudos.

A mudança foi aplicada em contracts/season-2026-turn-split-paper.json, com
manifesto dos380jogos e classificador em research/season_2026_split.py.
Contrato SHA-256: `{sha(CONTRACT)}`. Manifesto SHA-256: `{sha(DATA/'schedule_manifest.json')}`.

Nenhum label foi revelado: apenas tabela CBF e identidade/data/linhagem locais.
Botafogo×Grêmio foi reconciliado pela data oficial de16/09/2026 às19h30; os outros
cinco duplicados tinham superseded_by_event_id preenchido. Nenhum banco foi editado.

O segundo turno inteiro é o denominador, não obrigação de190apostas. Sem candidato
aprovado, preço válido ou critério econômico, não há sinal. Decisões anteriores ao
congelamento são replay retrospectivo; futuras exigem preço/modelo disponíveis
emT−1h e regra congelada. 2025/2026 já foram explorados, sem alegar teste cego.
O primeiro turno não será usado para reajustar modelo desta divisão.

Nenhuma avaliação de H14/H15/H9/A1, nova trial, agendamento, uso de capital ou aposta.
Esta etapa termina com divisão, manifesto e testes, sem iniciar outra busca de
parâmetros ou promover a hipótese de preço que falhou.
"""
    (REPO/'docs/decisions/2026-09-07-season-turn-split-paper.md').write_text(decision,encoding='utf-8')
    (OUT/'DECISAO.md').write_text(decision,encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=True))


if __name__ == '__main__':
    main()
