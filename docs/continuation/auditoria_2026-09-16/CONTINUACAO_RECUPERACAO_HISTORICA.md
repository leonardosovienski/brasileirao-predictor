# Continuação da recuperação histórica

## Resultado

Esta rodada não recuperou novas previsões nem os dois relatórios originais. Permanecem duas reconstruções retrospectivas H15 de seis braços; quatro H15 e seis H14 continuam sem OU2.5 comprovada. As reconstruções não se tornam previsões prospectivas.

## Verificações adicionais concluídas

- 864 representações numéricas equivalentes das configurações disponíveis, variando apenas a serialização inteiro/decimal: nenhum novo fingerprint histórico correspondente. Nenhum valor foi otimizado para ajustar previsões.
- 17 versões de `data/trials.json`: somente a identidade de algoritmo `nbdc-normalized-elo-horizon-v2` identificada para H15.
- Objetos Git fora das referências: 27 blobs, uma árvore e um commit. Nenhuma configuração adicional encontrada pelo filtro de estrutura de configuração, nem os relatórios procurados na árvore.
- GitHub: 51 execuções entre 1 e 8 de setembro; as 48 de CI consultadas não disponibilizam artefatos. As outras três são atualizações de dependências.
- Release v0.2.0: pacote fonte adquirido, SHA256 conferido contra os metadados da release, 2.344 membros listados. Os dois relatórios não constam; as três cópias de config.yaml são idênticas a configurações já examinadas.
- OneDrive local resolvido pelas variáveis do usuário: somente desktop.ini no diretório. Isso não equivale a uma busca na conta remota do OneDrive.

## Bloqueio específico restante

Nos eventos H15 15235455 e 15235459, ambos os braços têm estados candidatos compatíveis com os metadados de refit e Elo examinados, mas nenhuma configuração recuperada reproduz o fingerprint de desenho registrado. Não basta substituir esse fingerprint ou escolher números que pareçam plausíveis.

H14 ainda exige o estado/grade de probabilidades histórico e a definição histórica da baseline OU2.5. Probabilidades 1X2 não determinam OU2.5 de forma única.

Os arquivos `exp001_data_pilot_2026-09-02.json` e `exp001_coverage_audit_2026-09-02.json` continuam não localizados. Reexecutar seus produtores hoje geraria novos relatórios, sem recuperar os originais.

O caminho offsite documentado sob `Superleo13/OneDrive/Codex-Offsite` continua sendo uma fonte potencial não acessada remotamente. Ausência local e ausência nos artefatos consultados não provam inexistência global.

## Preservação e limites

Os hashes dos originais foram novamente conferidos e permanecem iguais:

- H14: `00030c961a3b42760a9f8d41fde096c213b75b5ec65e9b74f3f0809898789d99`.
- H15: `f3337e0567c53ac3af15b2e8ef3113470a5c7e854e3b69f269418fa38230a46f`.

Nenhuma avaliação de coorte protegida, alteração de previsão original, ativação de protocolo ou mudança no código instalado foi feita nesta continuação. Os 82 registros previamente admitidos no CAIN não foram modificados. Este relatório adicional está entregue em arquivo; não foi admitido como uma nova publicação no banco do CAIN.

As verificações desta rodada são de recuperação e integridade de arquivos. Não certificam ausência geral de bugs nem resolvem as demais lacunas científicas listadas em CAIN_O_QUE_FALTA.md.

## Evidências reproduzíveis

Pasta de trabalho: `C:/BRASILEIRAO/work/audit-fixes-20260915/continued-recovery`.

- `equivalent-config-search.json`
- `dangling-git-search.json`
- `github-search.json`
- `release-archive-search.json`

Os recibos e scripts desta rodada acompanham `CONTINUACAO_RECUPERACAO_EVIDENCIAS.zip`.
