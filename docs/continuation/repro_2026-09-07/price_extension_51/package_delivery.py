"""Publish derived summaries only after the fixed experiment has completed."""
import hashlib
import json
import re
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parents[1] / "outputs/EXTENSAO_51"
REPO = Path(r"C:\Users\Superleo13\projetos\brasileirao-predictor")
OUT.mkdir(exist_ok=True)
result = json.loads((ROOT / "result.json").read_text(encoding="utf-8"))
manifest = json.loads((ROOT / "acquisition_manifest.json").read_text(encoding="utf-8"))
plan = json.loads((ROOT / "plan.json").read_text(encoding="utf-8"))
assert manifest["status"] != "RUNNING"
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
assert manifest["plan_file_sha256_before_first_request"] == sha(ROOT / "plan.json")
def number(value, digits=2):
    return "não definido" if value is None else f"{value:.{digits}f}".replace(".", ",")
def pct(value):
    return number(None if value is None else value * 100) + "%"

summary = {k: v for k, v in result.items() if k not in ("records",)}
summary["excluded_events"] = [{k: row[k] for k in ("fixture_id", "kickoff_at", "feature_exclusion_reasons", "target_exclusion_reasons")}
                              for row in result["records"] if not row["paired_mse_eligible"]]
summary["acquisition"] = {k: v for k, v in manifest.items() if k != "records"}
summary["result_file_sha256"] = sha(ROOT / "result.json")
summary["provider_raw_data_distributed"] = False
(OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
metrics = result["primary_metrics"]
proxy = result["secondary_price_proxy"]
lower = metrics["paired_mean_mse_delta"] is not None and metrics["paired_mean_mse_delta"] < 0
if metrics["n"] < plan["minimum_complete_test_events"]:
    conclusion = "A cobertura ficou abaixo do mínimo de 30 eventos válidos; a extensão é insuficiente."
elif lower:
    conclusion = "O candidato reduziu o erro também neste lote, em comparação com conservar o preço atual. Isso é um resultado exploratório, sem confirmação de lucro."
else:
    conclusion = "O candidato não reduziu o erro neste lote. A melhora pequena do teste anterior não se repetiu; esta hipótese não tem suporte para avançar a apostas."
if proxy["signal_n"] == 0:
    economic = "Nenhum evento atendeu ao prêmio implícito previsto acima de 2%. Pelo critério congelado, a previsão não produziu sinal de preço para avaliar."
else:
    economic = (f"Houve {proxy['signal_n']} sinais, dos quais {proxy['signal_target_available_n']} tinham referência futura disponível e "
                f"{proxy['signal_target_missing_n']} ficaram sem avaliação. O prêmio observado médio contra a referência futura foi "
                f"{pct(proxy['observed_reference_proxy_mean'])}; após descontar o cenário fixo de 2%, {pct(proxy['after_cost_scenario_proxy_mean'])}. "
                "Esses números são proxies de preço, não retornos de apostas.")
months = "\n".join(f"| {month} | {data['metrics']['n']} | {pct(data['metrics']['relative_mse_reduction'])} |"
                   for month, data in result["monthly"].items())
verification = (ROOT / "verification_tests.txt").read_text(encoding="utf-8")
tests = re.findall(r"(\d+) passed", verification)
assert tests, "No successful test receipt"
protected = json.loads((ROOT.parents[1] / "outputs/REANALISE/integridade.json").read_text(encoding="utf-8"))["protected_sha256"]
assert len(protected) == 14
assert all(sha(REPO / name) == value for name, value in protected.items())
integrity = {"checked_at": datetime.now(timezone.utc).isoformat(), "protected_sha256": protected,
             "protected_files_unchanged": True, "plan_sha256": sha(ROOT / "plan.json"),
             "selection_sha256": sha(ROOT / "selection.json"), "result_sha256": sha(ROOT / "result.json"),
             "provider_raw_data_distributed": False}
(OUT / "integridade.json").write_text(json.dumps(integrity, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
text = f"""# Extensão histórica — 51 jogos adicionais

**{conclusion}**

O teste foi executado com jogos já terminados; não foi necessário aguardar novas partidas.
Foram selecionados 51 eventos por metadados, excluindo todos os 30 IDs da análise anterior.
Cada decisão simulada uma hora antes do jogo ocorre estritamente após o último alvo usado
no treino original. O coeficiente permaneceu em −0,31988646513691255, sem novo ajuste.

## Coleta e cobertura

- Selecionados: 51; pedidos tentados: {manifest['attempted_count']}; históricos salvos: {manifest['saved_count']}.
- Estado final: {manifest['status']}; sem repetição de pedidos ou substituição de jogos.
- Eventos com todas as janelas válidas: {metrics['n']} de 51.
- Contador da conta antes/depois: {manifest['quota_before']['request_count']}/{manifest['quota_before']['request_limit']} → {manifest['quota_after']['request_count']}/{manifest['quota_after']['request_limit']}.
- Nenhuma chamada a endpoint tarifado foi feita por este coletor; nenhum gasto ou aposta.

O evento excluído tinha as três opções do mercado suspensas em T−1h e T−10min.
Ele permanece no denominador de 51; o leitor não reaproveitou as cotações anteriores à suspensão.

## Previsão do preço futuro

O alvo é a probabilidade implícita de Pinnacle sem margem em T−10min. As entradas são
preços conhecidos na reconstrução em T−6h e T−1h. Comparamos dois previsores fixos:
conservar a probabilidade de T−1h ou aplicar a reversão aprendida no treino anterior.

| Métrica | Resultado |
|---|---:|
| Erro quadrático médio da persistência | {number(metrics['persistence_mean_mse'], 9)} |
| Erro quadrático médio do candidato congelado | {number(metrics['frozen_ridge_momentum_mean_mse'], 9)} |
| Redução relativa do erro (negativo significa piora) | {pct(metrics['relative_mse_reduction'])} |
| Jogos com erro menor / igual / maior | {metrics['events_lower_mse']} / {metrics['events_equal_mse']} / {metrics['events_higher_mse']} |

| Mês | Eventos válidos | Redução relativa do erro |
|---|---:|---:|
{months}

Retirando um evento por vez, sem reajuste, a diferença média de erro candidato−persistência
ficou entre {number(result['leave_one_event_out']['paired_delta_min'], 9)} e
{number(result['leave_one_event_out']['paired_delta_max'], 9)}. É sensibilidade descritiva,
não intervalo de confiança ou correção pela quantidade de hipóteses já pesquisadas.

## Utilidade do sinal de preço

{economic}

A seleção foi definida antes de conhecer o alvo: no máximo uma opção por evento,
maior `q_prevista_T10 × odd_T1 − 1`, exigindo valor acima de 0,02. Depois avaliamos
a mesma opção usando `q_observada_T10 × odd_T1 − 1`. Subtrair 0,02 é apenas um cenário
de custo fixo. A referência futura não é a probabilidade verdadeira do resultado;
não medimos lucro, retorno executado, aceitação de aposta nem resultado de partida.
Sinais sem alvo disponível continuam no denominador.

## Limites e verificação

Os 51 jogos pertencem a abril–maio de 2026 e se intercalam com o teste anterior.
A extensão foi decidida depois de observar aquele resultado; não é uma replicação
em período futuro, teste cego ou confirmação independente. O plano anterior e seu
resultado permanecem encerrados e preservados. Esta extensão também termina após
uma única coleta e avaliação, qualquer que seja o resultado.

O leitor exige o último estado explicitamente ativo e rejeita conflitos, estados
com mais de seis horas, odds fora da faixa ou vetores incompletos. O timestamp
indica registro de estado, sem comprovar latência, idade original da odd ou execução.
Suspensões globais históricas não são reconstruídas.

{tests[-1]} testes sintéticos/de componentes passaram antes da avaliação real. A integridade
dos 14 arquivos protegidos foi conferida; nenhuma coorte protegida foi avaliada.
Uma auditoria independente do resultado fez 3.214 verificações aritméticas e de
proveniência, sem divergências e sem repetir a avaliação ou ajustar o modelo.
Os históricos brutos permanecem privados em work/price_extension_51/raw.

[Resumo numérico](summary.json) · [Plano congelado](plan.json) ·
[Seleção por metadados](selection.json) · [Verificação](verification_tests.txt) ·
[Integridade](integridade.json)

Documentação consultada: [histórico de odds](https://oddspapi.io/us/docs/get-historical-odds)
e [requisições e quota](https://oddspapi.io/us/docs/requests-and-quota). O provedor documenta
históricos desde janeiro de 2026 e esse endpoint não incrementa o contador tarifado.
"""
(OUT / "RESULTADO.md").write_text(text, encoding="utf-8")
for name in ["plan.json", "selection.json", "DECISION_RECORD.md", "verification_tests.txt", "acquisition_manifest.json"]:
    shutil.copyfile(ROOT / name, OUT / name)
if (ROOT / "INDEPENDENT_REVIEW.md").exists():
    shutil.copyfile(ROOT / "INDEPENDENT_REVIEW.md", OUT / "INDEPENDENT_REVIEW.md")
if (ROOT / "implementation_receipt.json").exists():
    shutil.copyfile(ROOT / "implementation_receipt.json", OUT / "implementation_receipt.json")
if (ROOT / "independent_result_audit.json").exists():
    shutil.copyfile(ROOT / "independent_result_audit.json", OUT / "independent_result_audit.json")
with zipfile.ZipFile(OUT / "codigo_e_resumos.zip", "w", zipfile.ZIP_DEFLATED) as archive:
    for name in ["acquire.py", "evaluate.py", "package_delivery.py", "audit_result_independently.py"]:
        archive.write(ROOT / name, name)
    for path in ROOT.glob("test*.py"):
        archive.write(path, path.name)
    for path in OUT.iterdir():
        if path.is_file() and path.suffix != ".zip":
            archive.write(path, path.name)
    archive.writestr("DADOS_PRIVADOS.txt", "Timelines brutas não redistribuídas. Na máquina de origem: work/price_extension_51/raw. O resultado detalhado com preços reconstruídos está em work/price_extension_51/result.json. O avaliador reutiliza work/selection_reanalysis/price_discovery_replay.py e verifica seu hash congelado.\n")
with zipfile.ZipFile(OUT / "codigo_e_resumos.zip") as archive:
    assert archive.testzip() is None
    assert not any("/raw/" in name for name in archive.namelist())
print(json.dumps({"report": str(OUT / "RESULTADO.md"), "status": result['status'], "valid_n": metrics['n'], "protected_hashes_verified": 14}))
