# Entrega — filtro de recomendação OU2.5

Data: 2026-08-27
Repositório-base: `leonardosovienski/brasileirao-predictor`
Commit auditado: `1d83b02b83bbd8d7a14bc66deef93bb969711328`

## Resultado

Foi implementado um filtro OU2.5 por replay temporal walk-forward aninhado.
Cada fold seleciona parâmetros apenas em replays internos do prefixo passado e
aplica a combinação congelada ao bloco externo imediatamente seguinte, sem
retuning. Todas as combinações, inclusive perdedoras, ficam no resultado.

Chance do resultado, probabilidade de mercado de-vigada, EV bruto, EV
conservador e força 0–100 são campos separados. O EV conservador desconta
fricção e um haircut de calibração estimado exclusivamente no passado. A força
fica limitada a 40 e capital permanece `false` sem evidência prospectiva A1.

A escolha não usa o maior ROI isolado. A prioridade é: limite inferior IC95 do
ROI, limite inferior IC95 do CLV, pior temporada, pior lado, pior faixa de odd
e tamanho da amostra. Há correção de Holm para multiplicidade em cada fold e
comparação com apostar sempre, nunca apostar e preço de mercado de-vigado.

## Limitação empírica encontrada

Foi coletado um painel real de 1.140 jogos encerrados de 2021–2023. SHA-256 do
banco local: `5f6c35dfc25d886d7d3c6a88bdd3f6686e93bd41803c26152b04c466738c462b`.

O endpoint histórico do SofaScore retornou 1X2, mas **zero pares OU2.5**. O
runner, corretamente, encerra antes de ajustar o modelo com a mensagem
`zero pares OU2.5 no banco`. Portanto não há ROI, CLV ou perdas individuais
reais a divulgar. Produzir esses números com odds sintéticas seria evidência
falsa. O CSV de perdas será produzido automaticamente quando existir preço
OU2.5 executável/PIT.

As temporadas 2024–2026 estão explicitamente marcadas como observadas e
contaminadas. O candidato entregue é um congelamento de protocolo, não o
“vencedor” de um backtest indisponível, e requer uma coorte A1 futura.

## Verificação

- suíte completa: 800 testes aprovados, 1 desmarcado, 3 warnings preexistentes;
- módulo novo: 4/4 testes aprovados em cinco execuções consecutivas;
- painel ampliado afetado: 42/42 testes aprovados;
- Ruff lint e format: aprovados;
- `git diff --check`: aprovado;
- teste contrafactual de leakage: alterar labels futuros não altera a seleção
  nem os picks do fold passado.

## Hashes dos arquivos entregues

| SHA-256 | Arquivo |
|---|---|
| `f725aad74fcede34b3fbf3288cd6745daa89aff2c296919856c2940e613ee231` | `scripts/benchmark_predictor.py` |
| `0354a8a3f00fd352c3029abbfb96f60ea6acc434201d6abf344ccf0be0c19c89` | `src/ingest_sofascore.py` |
| `1311b489eeeb3aa3897057f8787f72b87dfeca6937e53580c34ed0ce4b0df313` | `contracts/ou25-nested-future-candidate.json` |
| `a9439436ae39bda2f41d72fdcffc32d13bdb6b7f9e9c2da2f725197305b8b196` | `docs/OU25_NESTED_REPLAY.md` |
| `6caec562472c2889689e44c25800a39ed02569903a8b6ab31a348f51b65cda70` | `scripts/research_ou25_nested_replay.py` |
| `ef4430e7d98bcb66e3a8d09cda7645d9bda504e5f33e91905a68412be61a61bc` | `src/research/ou25_nested_replay.py` |
| `0caf8825f63de09faa6b21547ee78cf2b7cdcdfd0a5bec4b5484e0e5d7fa5033` | `tests/test_ou25_nested_replay.py` |

O runner gera um `manifest.json` novo, contendo o hash do banco, configuração,
grade integral e hashes dos artefatos, em cada execução com dados elegíveis.
