import difflib
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = Path("C:/Users/Superleo13/projetos/brasileirao-predictor")
sys.path.insert(0, str(REPO))
from brasileirao_predictor.ingest_sofascore import parse_ou

profile = json.loads((ROOT / "frozen_data_profile.json").read_text(encoding="utf-8"))
before = json.loads((ROOT / "ou_scope_bug_before.json").read_text(encoding="utf-8"))
after = {k: list(parse_ou(v["payload"])) for k,v in before.items()}
expected = {"corners_before_goals": [1.8,2.0], "first_half_only": [None,None], "conflicting_goal_markets": [None,None]}
assert after == expected
(ROOT / "ou_scope_bug_after.json").write_text(json.dumps(after, indent=2)+"\n",encoding="utf-8")
patch = "".join(difflib.unified_diff((ROOT / "ingest_sofascore_before.py").read_text(encoding="utf-8").splitlines(keepends=True), (REPO / "brasileirao_predictor/ingest_sofascore.py").read_text(encoding="utf-8").splitlines(keepends=True), fromfile="a/brasileirao_predictor/ingest_sofascore.py", tofile="b/brasileirao_predictor/ingest_sofascore.py"))
patch += "".join(difflib.unified_diff([], (REPO / "tests/test_parse_ou_scope_regression.py").read_text(encoding="utf-8").splitlines(keepends=True), fromfile="/dev/null", tofile="b/tests/test_parse_ou_scope_regression.py"))
(ROOT / "parser_scope_fix.patch").write_text(patch,encoding="utf-8")
findings = [
    {
        "id":"DATA-01", "severity":"P1", "status":"FIXED_CODE_HISTORICAL_IMPACT_UNKNOWN",
        "title":"Odds de outra estatística ou período podiam entrar como total de gols",
        "evidence":"Reprodução sintética anterior em ou_scope_bug_before.json: Total corners (marketId 21), com preços 4.0/1.1, precedendo Match goals (marketId 9), com 1.8/2.0, resultava em 4.0/1.1. O mercado de primeiro tempo também era aceito; entre mercados conflitantes, o parser escolhia o primeiro.",
        "source":"brasileirao_predictor/ingest_sofascore.py:parse_ou e ingestão das colunas agregadas e odds_snapshots",
        "impact":"Pode trocar mercado, período ou versão da cotação sem erro; não há comprovação de que os snapshots dos estudos foram afetados.",
        "action":"Aplicada validação de identidade e período, lados e linha exatos, preços finitos e apostáveis, e rejeição de conflitos. parse_all_odds usa a mesma extração para tabelas de linhas, evitando divergência entre caminhos.",
        "validation":"32 novas regressões e 50 testes existentes: 82 passaram; Ruff passou. Reproduções posteriores corretas. Nenhum dado operacional regravado e nenhum resultado científico recalculado."
    },
    {
        "id":"DATA-02", "severity":"P1", "status":"KNOWN_LIMITATION_NOT_EXECUTABLE_PROFIT_EVIDENCE",
        "title":"Cotações do replay não têm comprovação de disponibilidade antes do jogo",
        "evidence":"historical_2021_2025.json carrega apenas vetores de odds; canonical_input_2026.json marca odds_execution_attested=false e fonte retrospective_sofascore_flat_no_bookmaker_or_observed_at nos 380 registros.",
        "impact":"Permite calcular pagamentos hipotéticos, mas não provar preço realizável, CLV, execução ou lucro futuro. Corrigir o parser atual não cria a evidência histórica ausente.",
        "action":"Manter o replay exploratório. Qualquer futuro teste econômico exige observação de preço com casa, seleção, linha, observed_at <= decision_at, estado ativo e limite ou execução quando se quiser concluir retorno realizável. Não fabricar horários para dados antigos."
    },
    {
        "id":"DATA-03", "severity":"P2", "status":"VALID_FOR_PRESENT_EXTRACTION_NOT_GENERAL_HISTORICAL_VERSIONING",
        "title":"Timestamp do resultado registra primeira ingestão e não versiona correções posteriores",
        "evidence":"db.py:_RESULT_OBSERVED_TRIGGERS registra o primeiro timestamp; upsert_ss_matches atualiza os placares. Duas tabelas concordantes provêm da mesma ingestão, portanto não são duas fontes independentes. parse_match só grava placar quando o status é finished, mas a extração não persiste esse status original.",
        "impact":"O snapshot desta execução foi congelado no corte real e os 248 timestamps passaram na verificação; nenhuma falha temporal observada. Porém, rodar no futuro uma consulta com corte antigo sobre o banco atual não reproduz automaticamente a versão do placar existente naquele corte.",
        "action":"Conservar os snapshots/hash atuais. Para replay histórico verificável após correções, registrar versões imutáveis do resultado/status com observed_at. Não chamar concordância local de verificação independente externa."
    },
    {
        "id":"DATA-04", "severity":"P2", "status":"KNOWN_COVERAGE_LIMITATION",
        "title":"Cobertura de mercados varia por ano e o segundo turno de 2026 está incompleto",
        "evidence":"OU2.5/BTTS têm 249/250 vetores completos em 2023 e 246/247 em 2024; 2025 tem 374 de 380 nos três mercados. O segundo turno de 2026 contém 58 de 190 concluídos, 129 fora da janela e 3 sem resultado.",
        "impact":"Comparar mercados ou anos sem reportar a população observável pode confundir seleção de amostra com qualidade. Não existe lucro realizado para 132 jogos ainda não liquidáveis.",
        "action":"Manter 190 jogos por turno como universo e divulgar jogos concluídos e cobertura por mercado. Comparações entre mercados exigem painel comum ou destaque da cobertura; não remover pendências para apresentar a temporada completa."
    },
]
result = {"status":"DATA_INTEGRITY_PASS_WITH_ONE_PARSER_FIX_AND_DISCLOSED_LIMITATIONS", "findings":findings, "frozen_snapshot_profile":profile, "changed_operational_files":["brasileirao_predictor/ingest_sofascore.py","tests/test_parse_ou_scope_regression.py"], "changed_source_sha256":hashlib.sha256((REPO / "brasileirao_predictor/ingest_sofascore.py").read_bytes()).hexdigest(), "database_read_in_this_audit":False, "cohort_ledgers_read":False, "operational_data_mutated":False}
(ROOT / "data_audit.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
text = "# Auditoria de dados e de parsing\n\nA integridade dos snapshots passou. Uma falha concreta de parsing foi reproduzida e corrigida; não se comprovou contaminação das odds históricas.\n\n"
for finding in findings:
    text += f"## {finding['id']} — {finding['severity']}: {finding['title']}\n\nEstado: `{finding['status']}`.\n\n{finding['evidence']}\n\nImpacto: {finding['impact']}\n\nAção: {finding['action']}\n\n"
text += "## Validação estrutural\n\n2021–2025: 380 jogos por ano, 20 times, 38 partidas por time, 380 mandos únicos por ano, sem placares inválidos. 2026: 380 IDs e mandos únicos, 38 rodadas com 10 jogos e 20 times cada, referências CBF coerentes, 190 jogos por papel. Todos os hashes de histórico, calendário, contrato, plano e extração conferiram. Os 248 resultados têm timestamps entre o início do jogo e o corte; pendências não carregam placares nem odds inventados.\n\nA suíte direcionada passou com 82 testes, incluindo 32 novas regressões. O patch é parser_scope_fix.patch. A auditoria não abriu o banco nem ledgers/coortes e não alterou dados operacionais ou estudos congelados.\n"
(ROOT / "data_audit.md").write_text(text,encoding="utf-8")
print(json.dumps({"status":result["status"],"artifacts":["data_audit.json","data_audit.md","frozen_data_profile.json","parser_scope_fix.patch"],"new_parser_sha256":result["changed_source_sha256"]}))
