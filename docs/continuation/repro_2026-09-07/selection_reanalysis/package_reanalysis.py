import hashlib
import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = Path(r"C:\Users\Superleo13\projetos\brasileirao-predictor")
OUT = Path(r"C:\Users\Superleo13\Documents\Codex\2026-09-07\le\outputs\REANALISE")
OUT.mkdir(exist_ok=True)
results = json.loads((ROOT / "selection_results.json").read_text(encoding="utf-8"))
forecasts = json.loads((ROOT / "forecasts_manifest.json").read_text(encoding="utf-8"))
old_integrity = json.loads((OUT.parent / "retomada_integridade.json").read_text(encoding="utf-8"))
observed = {name: hashlib.sha256((REPO / name).read_bytes()).hexdigest() for name in old_integrity["protected_sha256"]}
assert observed == old_integrity["protected_sha256"], "Protected source/config changed"
integrity = {"checked_at": datetime.now(timezone.utc).isoformat(), "protected_sha256": observed, "protected_files_unchanged": True, "protected_cohorts_evaluated": False, "new_historical_evaluation": True, "price_parser_fix_applied": True, "capital_enabled": False}
(OUT / "integridade.json").write_text(json.dumps(integrity,indent=2)+"\n",encoding="utf-8")

labels = {
    "no_bet":"Não apostar", "confidence_60":"Confiança ≥60%", "confidence_70":"Confiança ≥70%",
    "raw_ev":"Maior retorno estimado pelo modelo", "half_market_blend":"Mistura fixa 50% modelo/50% mercado",
    "learned_market_blend":"Peso modelo/mercado aprendido no passado", "calibrated_residual":"Correção calibrada por mercado",
    "conservative_residual":"Correção calibrada com desconto de 3pp",
    "residual_1x2_only":"Correção restrita a resultado 1X2", "residual_ou25_only":"Correção restrita a OU2.5",
    "residual_btts_only":"Correção restrita a ambas marcam", "hash_placebo":"Seleção placebo determinística",
}

def number(value, pct=False):
    if value is None: return '—'
    return (f'{value*100:+.2f}%' if pct else f'{value:+.3f}').replace('.',',')

lines = ["# Reanálise executada — seleção de apostas e preço", "", "## Resultado", "",
    "Foi executado um replay novo, com 12 políticas fixadas antes do cálculo dos resultados. Nenhuma demonstrou uma vantagem econômica robusta. O filtro de 60% acertou bastante e ainda perdeu; os dois sinais positivos tiveram apenas 20 e 19 apostas e perderam no cenário adverso de custos/preços. Isso rejeita as soluções testadas como justificativa para liberar apostas, sem afirmar que nenhuma oportunidade pode existir.", "",
    "**Os retornos abaixo são contrafactuais, com odds históricas agregadas e custo adicional simulado de 2% por unidade. Não são lucro executado, nem prova de que a cotação estava disponível no instante da previsão.**", "",
    "| Política | Apostas virtuais | Resultado (u) | ROI |", "|---|---:|---:|---:|"]
for key,value in results["policies"].items():
    s=value["overall"]
    lines.append(f"| {labels[key]} | {s['bets']} | {number(s['profit_units'])} | {number(s['roi'],True)} |")
lines += ["", "Uma unidade é uma aposta virtual fixa; não houve uso de banca real. Zero apostas tem lucro zero e ROI indefinido, por isso aparece como traço.", "", "## O que mudou no diagnóstico", "",
    "- Confiança ≥60%: 239 apostas, acerto de 60,67% e ROI de −7,34%. A probabilidade alta não compensou as odds.",
    "- Confiança ≥70%: 20 apostas, ROI de +4,82%; 2023 perdeu e 2024 teve apenas uma aposta. Com custo de 5% e odds 3% menores, ROI de −1,39%.",
    "- Correção calibrada: 19 apostas, ROI de +2,21%, mas 2025 perdeu 14,50%. No mesmo estresse, ROI de −3,92%. As 19 escolhas foram todas 1X2: permitir OU2.5/BTTS não acrescentou apostas nesta política.",
    "- Selecionar o maior retorno previsto sem correção ampliou os erros: 952 apostas, ROI de −22,15%. Isso é evidência contra confiar automaticamente no maior edge calculado por este modelo.",
    "- A versão conservadora, descontando 3 pontos percentuais da probabilidade calibrada, não encontrou apostas. Esse desconto é um cenário fixo, não um intervalo de confiança estatístico.", "",
    "## Método e cobertura", "",
    "Foram usados 1.900 eventos de 2021–2025 já explorados. O gerador produziu 1.697 previsões; 203 eventos ficaram no burn-in. A decisão foi simulada uma hora antes do início, com resultados de treino separados por um buffer de 48 horas, grade de 12 gols e refit a cada 100 novos jogos elegíveis. Houve 17 refits, sem falhas de otimizador; 42 previsões recorreram ao rating inicial de clubes ausentes no estado congelado, com identificação no manifesto. Não foram eliminadas por seu resultado.", "",
    "A seleção foi avaliada em 1.140 eventos de 2023–2025. Calibração mensal usa exclusivamente eventos anteriores ao corte do primeiro jogo daquele mês. Há no máximo uma aposta por evento. Todas as políticas e anos são publicados, sem escolher um limiar depois de observar o resultado. O novo namespace não apaga as buscas anteriores do projeto.", "",
    "As odds de OU2.5/BTTS cobrem aproximadamente 65% dos jogos em 2023–2024. O painel comum aos três mercados tem 869 jogos. Nele, confiança ≥60% também perdeu (ROI −6,08%); confiança ≥70% fez 19 apostas (+3,42%); a correção calibrada manteve as mesmas 19 apostas. As ausências estão discriminadas por ano e mercado no JSON.", "",
    "O bootstrap usa 2.000 reamostragens de blocos de quatro semanas, incluindo semanas vazias e preservando os mesmos jogos entre políticas. Seus intervalos são descritivos, não ajustados pela busca múltipla. Abaixo de 30 apostas ou oito semanas ativas, o intervalo é omitido. Não há veredito confirmatório.", "",
    "## Defeito corrigido no projeto", "",
    "O leitor de históricos da EXP001 descartava registros de suspensão antes de procurar a última cotação. Assim, podia devolver como disponível um preço antigo que já havia sido suspenso. Corrigimos a ordem: procurar o último estado primeiro e rejeitar suspensão, estado sem confirmação ativa ou empate de timestamp conflitante. A correção foi aplicada em brasileirao_scripts/exp001_data_pilot.py, com testes de regressão. Os números antigos de cobertura 245/245 não comprovam mais disponibilidade; a quantidade afetada permanece desconhecida, pois as timelines completas não foram preservadas.", "",
    "## Verificação e limites", "",
    "63 testes passaram: 5 do gerador, 40 do seletor e 18 do parser/integração existente. Uma revisão independente reconciliou 13.680 decisões, suas odds, resultados, custos, rankings, desempates, totais anuais e cenários de estresse, sem divergências. Os 14 arquivos principais protegidos mantiveram seus hashes. H14/H15/H9/A1 não foram avaliadas nem tiveram regras alteradas. Não houve aposta, compra, depósito, nova conta ou promoção de trial.", "",
    "O buffer de 48 horas não prova a data histórica de publicação de placares/xG. As odds agregadas não têm bookmaker e horário de observação suficientes para demonstrar execução. Refit a cada 100 jogos é a cadência deste experimento, não uma reprodução exata do cron operacional. O histórico já observado continua sendo exploratório.", "",
    "[Resultados completos](selection_results.json) · [Testes](verification_tests.txt) · [Integridade](integridade.json) · [Patch aplicado](price_history_parser_fix.patch)", ""]
(OUT/"RESULTADOS.md").write_text('\n'.join(lines),encoding="utf-8")
for name in ["analysis_plan.json","validation_addendum_before_results.json","input_manifest.json","selection_results.json","forecasts_manifest.json","verification_tests.txt"]:
    shutil.copyfile(ROOT/name,OUT/name)
shutil.copyfile(ROOT/"price_history"/"price_history_parser_fix.patch",OUT/"price_history_parser_fix.patch")
files = ["prepare_input.py","generate_predictions.py","selective_replay.py","test_generate_predictions.py","test_selective_replay.py","historical_input.json","forecasts.json","analysis_plan.json","validation_addendum_before_results.json","config_frozen.yaml","input_manifest.json","forecasts_manifest.json","selection_results.json","selection_decisions.jsonl","calibration_fits.json","verification_tests.txt","generation.log","selection_run.log"]
with zipfile.ZipFile(OUT/"reanalise_reproduzivel.zip","w",zipfile.ZIP_DEFLATED) as z:
    for name in files: z.write(ROOT/name,name)
    z.write(OUT/"RESULTADOS.md","RESULTADOS.md")
    z.write(OUT/"price_history_parser_fix.patch","price_history_parser_fix.patch")
    z.writestr("REPRODUZIR.txt","Este pacote é um diagnóstico histórico, não um robô de apostas.\nUse o ambiente operacional já instalado do brasileirao-predictor.\nNa pasta extraída, execute generate_predictions.py e selective_replay.py com esse Python.\nNão execute prepare_input.py para repetir: os dados e o plano congelados já estão incluídos.\nNenhuma chave é necessária para este replay 2021–2025.\n")
print(json.dumps({"report":str(OUT/"RESULTADOS.md"),"protected_files":len(observed),"zip_bytes":(OUT/"reanalise_reproduzivel.zip").stat().st_size}))
