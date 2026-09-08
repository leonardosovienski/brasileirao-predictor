# Auditoria de dados e de parsing

A integridade dos snapshots passou. Uma falha concreta de parsing foi reproduzida e corrigida; não se comprovou contaminação das odds históricas.

## DATA-01 — P1: Odds de outra estatística ou período podiam entrar como total de gols

Estado: `FIXED_CODE_HISTORICAL_IMPACT_UNKNOWN`.

Reprodução sintética anterior em ou_scope_bug_before.json: Total corners (marketId 21), com preços 4.0/1.1, precedendo Match goals (marketId 9), com 1.8/2.0, resultava em 4.0/1.1. O mercado de primeiro tempo também era aceito; entre mercados conflitantes, o parser escolhia o primeiro.

Impacto: Pode trocar mercado, período ou versão da cotação sem erro; não há comprovação de que os snapshots dos estudos foram afetados.

Ação: Aplicada validação de identidade e período, lados e linha exatos, preços finitos e apostáveis, e rejeição de conflitos. parse_all_odds usa a mesma extração para tabelas de linhas, evitando divergência entre caminhos.

## DATA-02 — P1: Cotações do replay não têm comprovação de disponibilidade antes do jogo

Estado: `KNOWN_LIMITATION_NOT_EXECUTABLE_PROFIT_EVIDENCE`.

historical_2021_2025.json carrega apenas vetores de odds; canonical_input_2026.json marca odds_execution_attested=false e fonte retrospective_sofascore_flat_no_bookmaker_or_observed_at nos 380 registros.

Impacto: Permite calcular pagamentos hipotéticos, mas não provar preço realizável, CLV, execução ou lucro futuro. Corrigir o parser atual não cria a evidência histórica ausente.

Ação: Manter o replay exploratório. Qualquer futuro teste econômico exige observação de preço com casa, seleção, linha, observed_at <= decision_at, estado ativo e limite ou execução quando se quiser concluir retorno realizável. Não fabricar horários para dados antigos.

## DATA-03 — P2: Timestamp do resultado registra primeira ingestão e não versiona correções posteriores

Estado: `VALID_FOR_PRESENT_EXTRACTION_NOT_GENERAL_HISTORICAL_VERSIONING`.

db.py:_RESULT_OBSERVED_TRIGGERS registra o primeiro timestamp; upsert_ss_matches atualiza os placares. Duas tabelas concordantes provêm da mesma ingestão, portanto não são duas fontes independentes. parse_match só grava placar quando o status é finished, mas a extração não persiste esse status original.

Impacto: O snapshot desta execução foi congelado no corte real e os 248 timestamps passaram na verificação; nenhuma falha temporal observada. Porém, rodar no futuro uma consulta com corte antigo sobre o banco atual não reproduz automaticamente a versão do placar existente naquele corte.

Ação: Conservar os snapshots/hash atuais. Para replay histórico verificável após correções, registrar versões imutáveis do resultado/status com observed_at. Não chamar concordância local de verificação independente externa.

## DATA-04 — P2: Cobertura de mercados varia por ano e o segundo turno de 2026 está incompleto

Estado: `KNOWN_COVERAGE_LIMITATION`.

OU2.5/BTTS têm 249/250 vetores completos em 2023 e 246/247 em 2024; 2025 tem 374 de 380 nos três mercados. O segundo turno de 2026 contém 58 de 190 concluídos, 129 fora da janela e 3 sem resultado.

Impacto: Comparar mercados ou anos sem reportar a população observável pode confundir seleção de amostra com qualidade. Não existe lucro realizado para 132 jogos ainda não liquidáveis.

Ação: Manter 190 jogos por turno como universo e divulgar jogos concluídos e cobertura por mercado. Comparações entre mercados exigem painel comum ou destaque da cobertura; não remover pendências para apresentar a temporada completa.

## Validação estrutural

2021–2025: 380 jogos por ano, 20 times, 38 partidas por time, 380 mandos únicos por ano, sem placares inválidos. 2026: 380 IDs e mandos únicos, 38 rodadas com 10 jogos e 20 times cada, referências CBF coerentes, 190 jogos por papel. Todos os hashes de histórico, calendário, contrato, plano e extração conferiram. Os 248 resultados têm timestamps entre o início do jogo e o corte; pendências não carregam placares nem odds inventados.

A suíte direcionada passou com 82 testes, incluindo 32 novas regressões. O patch é parser_scope_fix.patch. A auditoria não abriu o banco nem ledgers/coortes e não alterou dados operacionais ou estudos congelados.
