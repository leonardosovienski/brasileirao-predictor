# Decisão — divisão de 2026 por turnos

O usuário determinou o primeiro turno como teste e todo o segundo como universo
para apostar; neste projeto a execução permanece simulada. Definimos 2021–2024
para treino e 2025 para calibração. Rodadas oficiais 1–19/20–38 fornecem 190 jogos
em cada grupo. Esta divisão vale para a nova avaliação, sem reescrever estudos.

A mudança foi aplicada em contracts/season-2026-turn-split-paper.json, com
manifesto dos380jogos e classificador em research/season_2026_split.py.
Contrato SHA-256: `c71f980a6281d14c9d3a688baf359df833b4a5085b19b6c52e505de3ec994706`. Manifesto SHA-256: `30a726e635cc7e9546977a9b96771eb3ffc58fd7900346ddc6a12e17ea60aeda`.

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

Proveniência finalizada antes de qualquer novo ajuste/avaliação: fonte histórica validada de1900eventos,1520treino e380calibração. SHA final do contrato `4ea8c62a77cd07deb05ef6887318d811a9ed8204573a2839801bab2c1b9d5e68` substitui o hash preliminar acima; a divisão e as regras permaneceram iguais.
