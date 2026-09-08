import hashlib
import json
import math
import shutil
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent
REPO=Path(r"C:\Users\Superleo13\projetos\brasileirao-predictor")
OUT=Path(r"C:\Users\Superleo13\Documents\Codex\2026-09-07\le\outputs\REANALISE")
b=json.loads((ROOT/"price_discovery_report.json").read_text(encoding="utf-8"))
p=json.loads((ROOT/"pinnacle_only_results.json").read_text(encoding="utf-8"))
delta=[r["losses"]["ridge_momentum"]-r["losses"]["persistence"] for r in p["per_test_event"]]
leave_one=[(sum(delta)-v)/(len(delta)-1) for v in delta]
summary={
    "original_common_panel":{"status":b["primary_B"]["status"],"train_n":b["primary_B"]["train_n"],"test_n":b["primary_B"]["test_n"],"fit_executed":False},
    "acquisition":{"selected_events":30,"http200":22,"http429":8,"retries":0,"request_count_before_catalog":61,"request_count_after_history":62,"request_limit":250,"paid_cost":0},
    "snapshot_coverage":b["snapshot_coverage"],
    "secondary_C":{"status":b["secondary_C"]["status"],"summary":b["secondary_C"]["summary"],"reference_at_followup":b["secondary_C"]["reference_at_followup"]},
    "pinnacle_only_adaptive":p,
    "post_result_descriptive_sensitivity_no_refit":{"leave_one_event_delta_range":[min(leave_one),max(leave_one)],"improvement_can_reverse_by_removing_one_event":max(leave_one)>0},
    "assessment":"WATCH_SMALL_FRAGILE_PRICE_SIGNAL_NOT_PROFIT",
    "no_protected_cohort_opened":True,
    "primary_source_sha256":hashlib.sha256((ROOT/"price_discovery_report.json").read_bytes()).hexdigest(),
    "provider_raw_data_distributed":False,
}
(OUT/"price_discovery_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
rmse0=math.sqrt(p["metrics"]["persistence"]["mse"])*100
rmse1=math.sqrt(p["metrics"]["ridge_momentum"]["mse"])*100
text=f"""# Preço futuro — teste executado e limite do sinal

**Encontramos uma pista pequena e frágil de reversão do movimento de preço.
Ainda não há solução de lucro demonstrada.** O ajuste treinado com 13 jogos
reduziu o erro quadrático médio em 3,35% nos 9 jogos seguintes, contra conservar
o preço atual. Retirar um dos jogos pode fazer essa melhora desaparecer.

## Aquisição e protocolo original

Uma consulta ao catálogo encontrou 177 eventos do Brasileirão no primeiro semestre
de 2026. Trinta foram selecionados por posições equidistantes na ordem cronológica,
antes de ler preços. A janela já era observada/exploratória conforme os contratos
H8/OU25 e termina antes das coortes prospectivas identificadas.

Foram feitas 30 chamadas ao histórico: 22 respostas HTTP 200 e 8 respostas HTTP 429. Nenhuma falha foi repetida
ou substituída. O contador gratuito foi de 61 para 62: só o catálogo consumiu uma
requisição. Nenhum plano, conta nova ou gasto foi necessário. O histórico bruto privado permanece
em work/selection_reanalysis/price_history/raw e não acompanha esta entrega.

O teste original compararia persistência, continuação do movimento, ridge de
movimento e ridge com diferença Bet365−Pinnacle. Pinnacle teve 22 vetores válidos nas
três janelas; Bet365 teve 7 em T−1h. Doze eventos Bet365 tinham último estado com mais
de 6 horas, três não tinham a seleção histórica necessária e oito ficaram sem arquivo.
O painel comum ficou com 4 eventos de treino e 3 de teste: **INSUFFICIENT_DATA, nenhum modelo ajustado.**
Esse resultado permanece preservado.

## Análise exploratória adicional, explicitamente adaptativa

Depois do diagnóstico de cobertura, foi registrado um segundo plano para a questão
que depende apenas de Pinnacle. Não é confirmação independente nem teste cego.
Ele usa os mesmos 30 IDs, divisão de 20 para treino e 10 para teste, horários, preços, critérios, fórmulas e o parâmetro de regularização
de ridge de 1e−4. A única diferença é não exigir a variável da outra casa.

Restaram 13 eventos de treino e 9 de teste. O alvo é a probabilidade implícita sem
margem de Pinnacle em T−10min, prevista com preços conhecidos na reconstrução até
T−1h e movimento desde T−6h. Todos os 22 vetores mudaram entre T−1h e T−10min. Resultados
de partidas não foram consultados para este teste.

| Previsor | Erro quadrático médio no teste | Variação do erro contra persistência |
|---|---:|---:|
| Conservar preço atual | {p['metrics']['persistence']['mse']:.9f} | referência |
| Continuar integralmente o movimento anterior | {p['metrics']['momentum_unit']['mse']:.9f} | +21,06% (pior) |
| Ajustar a intensidade no treino | {p['metrics']['ridge_momentum']['mse']:.9f} | −3,35% (melhor) |

O coeficiente aprendido foi −0,3199: pequena reversão, não continuação automática.
O ajuste foi melhor em 5 dos 9 eventos. Em erro de probabilidade mais legível, a raiz
do erro quadrático médio caiu de {rmse0:.4f} para {rmse1:.4f} pontos percentuais.

Uma verificação descritiva posterior, sem reajustar nada, retirou cada evento
individualmente: a vantagem pode trocar de sinal. Portanto **WATCH: pista para
replicação, amostra pequena e efeito frágil; não CONFIRMED_EDGE.** Nenhum parâmetro,
mercado ou seleção adicional foi procurado após esse resultado.

## Diferença entre casas

O diagnóstico C encontrou um prêmio cotado acima de 2% somente no treino e zero
no teste. O exemplo do treino ainda estava acima desse nível cinco minutos depois,
usando a referência Pinnacle inicial fixa. Isso não é prova de probabilidade real,
preço aceito, execução ou lucro; C também permanece insuficiente.

## Código e verificação

A correção de suspensão do leitor de históricos EXP001 foi aplicada ao projeto operacional.
O parser reconstrói o último estado antes de decidir se a cotação é válida;
não ressuscita uma odd anterior à suspensão. A pesquisa B permanece em uma pasta separada
de pesquisa. Nenhuma coorte protegida ou regra de aposta foi alterada.

O conjunto tem 97 testes pytest aprovados, além de 11 verificações sintéticas
independentes dos dois analisadores de preço. A revisão independente também
reconciliou as 13.680 decisões da análise de filtros. Essas verificações cobrem os componentes alterados e os experimentos; a suíte completa do projeto não foi executada.

Limites adicionais: createdAt mede o último registro de estado, não latência de
recebimento nem necessariamente a idade original da odd; estados globais históricos
de suspensão não foram reconstruídos. Odds cotadas e probabilidades implícitas
não comprovam que uma aposta seria aceita. A análise adaptativa e toda a busca
anterior permanecem contabilizadas; não foi promovida nenhuma trial.

[Resumo numérico e hashes](price_discovery_summary.json) ·
[Análise de filtros](RESULTADOS.md) · [Testes completos](verification_all_tests.txt)

Fontes públicas: [histórico OddsPapi](https://oddspapi.io/us/docs/get-historical-odds)
e [quota](https://oddspapi.io/us/docs/requests-and-quota). Os números deste relatório
foram medidos na sessão; os preços brutos não são redistribuídos.
"""
(OUT/"PRICE_DISCOVERY.md").write_text(text,encoding="utf-8")
for name in ["price_discovery_plan.json","pinnacle_only_plan.json","ADMISSIBILITY.md","INDEPENDENT_AUDIT_PRICE_DISCOVERY_B.md","INDEPENDENT_AUDIT_PINNACLE_ADAPTIVE.md"]:
    shutil.copyfile(ROOT/"price_history"/name,OUT/name)
for name in ["2026-09-07-price-discovery-historical-first-half.md","2026-09-07-price-discovery-pinnacle-exploratory.md"]:
    shutil.copyfile(REPO/"docs"/"decisions"/name,OUT/name)
with zipfile.ZipFile(OUT/"price_discovery_codigo_e_resumos.zip","w",zipfile.ZIP_DEFLATED) as z:
    for name in ["price_discovery_replay.py","test_price_discovery_replay.py","pinnacle_only_replay.py","test_pinnacle_only_replay.py"]: z.write(ROOT/name,name)
    for name in ["PRICE_DISCOVERY.md","price_discovery_summary.json","price_discovery_plan.json","pinnacle_only_plan.json","ADMISSIBILITY.md","INDEPENDENT_AUDIT_PRICE_DISCOVERY_B.md","INDEPENDENT_AUDIT_PINNACLE_ADAPTIVE.md"]: z.write(OUT/name,name)
    z.writestr("RAW_PRIVADO.txt","As timelines originais não são redistribuídas. Permanecem na pasta work/selection_reanalysis/price_history/raw nesta máquina, com hashes no manifesto. O diagnóstico primário completo está em work/selection_reanalysis/price_discovery_report.json. Não execute nova coleta ou trate esses resultados como autorização de apostas.\n")
print(json.dumps({"report":str(OUT/"PRICE_DISCOVERY.md"),"assessment":summary['assessment'],"raw_data_distributed":False}))
