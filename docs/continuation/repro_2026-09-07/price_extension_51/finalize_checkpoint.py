"""Record this completed exploratory experiment without changing protected protocols."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = Path(r"C:\Users\Superleo13\projetos\brasileirao-predictor")
OUT = ROOT.parents[1] / "outputs/EXTENSAO_51"
result = json.loads((ROOT / "result.json").read_text(encoding="utf-8"))
manifest = json.loads((ROOT / "acquisition_manifest.json").read_text(encoding="utf-8"))
receipt = json.loads((ROOT / "implementation_receipt.json").read_text(encoding="utf-8-sig"))
for name, expected in receipt["hashes"].items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
assert result["primary_metrics"]["n"] == 50 and result["secondary_price_proxy"]["signal_n"] == 0
assert manifest["saved_count"] == 51
checkpoint = """## CHECKPOINT — EXTENSÃO HISTÓRICA 51 CONCLUÍDA (2026-09-07)

Após o usuário perguntar se precisava esperar o próximo fim de semana, executamos
uma extensão exploratória separada usando o histórico adicional já identificado.
O estudo anterior permaneceu encerrado. Plano e 51 IDs foram congelados antes
dos novos preços; código e recibo de 90 testes foram fixados antes da avaliação.
Decisão: docs/decisions/2026-09-07-price-extension-51.md.

51/51 históricos Pinnacle foram coletados sem falhas nem retries, com intervalo
de 7s após cada resposta. Quota da conta permaneceu 62/250; nenhum gasto. Todos os
30 IDs anteriores ficaram excluídos, incluindo as falhas. A regra temporal exige
T−1h posterior ao último alvo do treino de 13 eventos. Não houve refit: beta
permaneceu −0,31988646513691255. Os novos jogos intercalam o período de teste
anterior; isto NÃO é holdout virgem nem replicação em um novo período futuro.

Resultado em 50 eventos válidos: MSE persistência 0,0003203463381416489 versus
candidato 0,0003250714434251413, piora de 1,475%; 23 jogos melhores e 27 piores.
Um evento tinha mercado suspenso em T−1h/T−10min e permaneceu no denominador51.
Nenhum sinal superou o prêmio implícito previsto de2% no diagnóstico secundário.
Conclusão: a melhora anterior de3,35% não se repetiu; não há suporte econômico
para promover este candidato. A diferença é descritiva, não prova estatística
de impossibilidade de qualquer oportunidade. Não alterar parâmetros, incluir
novos jogos ou somar amostras retrospectivamente para forçar resultado positivo.

A extensão terminou após a única coleta e avaliação previstas. Nenhum resultado
de partida, coorte protegida, registro de trial, agenda ou regra de aposta foi
alterado/avaliado. Os 14 hashes de arquivos protegidos foram novamente conferidos.
Entregas: Documents/Codex/2026-09-07/le/outputs/EXTENSAO_51/RESULTADO.md e pacote
com plano, seleção, código, testes e resumos. Históricos brutos permanecem privados.
"""
path = REPO / "HANDOFF.md"
body = path.read_text(encoding="utf-8-sig")
assert checkpoint.splitlines()[0] not in body
first, rest = body.split("\n", 1)
quoted = "\n".join("> " + line if line else ">" for line in checkpoint.splitlines())
path.write_text(first + "\n\n" + quoted + "\n" + rest, encoding="utf-8")
(OUT / "CHECKPOINT_FINAL.md").write_text(checkpoint, encoding="utf-8")
print(json.dumps({"checkpoint": str(OUT / "CHECKPOINT_FINAL.md"), "implementation_hashes_unchanged": True}))
