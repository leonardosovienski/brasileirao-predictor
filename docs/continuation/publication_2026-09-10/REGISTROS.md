# Registro corrente — PUB-20260910

Deriva de REGISTROS.json. O histórico RES foi preservado. 59 itens: 52 validados e sete bloqueados. A parcela Linux de RCA-P09 foi resolvida; o escopo global protegido permanece aberto.

| ID | Estado | Problema |
| --- | --- | --- |
| CPL-P01 | validado | Duas chamadas e perda da data no formatter |
| CPL-P02 | validado | PK ignorava charter/event_at; hash arbitrava empate material |
| CPL-P03 | validado | Primeira pÃ¡gina ou metadata ausente eram tratadas como coleÃ§Ã£o completa |
| CPL-P04 | validado | Interface afirmava ALTA e validaÃ§Ã£o lucrativa sem evidÃªncia correspondente |
| CPL-P05 | validado | AusÃªncia de checagem de ingestÃ£o; empate arbitrÃ¡rio de vintages |
| CPL-P06 | validado | Inventava publicaÃ§Ã£o antes da requisiÃ§Ã£o e ecoava erro arbitrÃ¡rio da fonte |
| CPL-P07 | validado | Descartava data que o contrato retorna no fuso da requisiÃ§Ã£o |
| CPL-P08 | validado | Mistura de eventos/linhas, vintages e seleÃ§Ã£o duplicada; ofertante na referÃªncia |
| CPL-P09 | validado | Teste sintÃ©tico reproduz PROSPECTIVE_ELIGIBLE apÃ³s kickoff no legado compartilhado |
| CPL-P10 | validado | CDF do total nÃ£o correspondia Ã  soma de duas NB ajustadas; entradas/fallbacks invÃ¡lidos aceitos |
| CPL-P11 | validado | Aceitava NaN, massas negativas/nÃ£o normalizadas e linha nÃ£o implementada |
| CPL-P12 | validado | Placar negativo passava pela prontidÃ£o |
| CPL-P13 | validado | Recalculava; ignorava falha de log; perÃ­odo usava cache e caminho diferentes |
| CPL-P14 | validado | NaN/Inf/bool, ID duplicado, HT impossÃ­vel; banca/lista associavam pela posiÃ§Ã£o |
| CPL-P15 | validado | build abria conexÃ£o RW |
| CPL-P16 | validado | Assumia tupla de cinco; quatro valores/dict falhavam |
| CPL-P17 | validado | ComparaÃ§Ã£o lexical de offsets, HHI dividido por jogos e bootstrap nÃ£o finito |
| CPL-P18 | validado | Stake negativa, entradas nÃ£o finitas, fair odd invÃ¡lida e recibo futuro aceitos |
| CPL-P19 | validado | Nomes sugeriam publicaÃ§Ã£o comprovada e recomendaÃ§Ã£o financeira |
| CPL-P20 | validado | Poderia sobrescrever parÃ¢metros existentes; data fixa parecia instante real |
| CPL-P21 | validado | runtime-after-02 excedeu inicializaÃ§Ã£o; log da causa nÃ£o existia |
| CPL-P22 | bloqueado | Cache por contagem/config; escrita separada Elo/params; placar revisado conserva primeiro relÃ³gio; xG/proveniÃªncia incompletos |
| CPL-P23 | bloqueado | Endpoint de exemplo, Elo1500 fixo, posiÃ§Ã£o UNKNOWN e parÃ¢metros de demonstraÃ§Ã£o |
| CPL-P24 | bloqueado | Ferramenta view sÃ³ devolve cartÃ£o de UI; configuraÃ§Ã£o documental nÃ£o prova ativo |
| CPL-P25 | validado | InventÃ¡rio/estÃ¡tica foram confundidos com revisÃ£o integral anterior |
| CPL-P26 | bloqueado | Casas/timestamps/aceitaÃ§Ã£o/capacidade continuam ausentes |
| CLO-P01 | validado | Resumo somava duplicatas/Ã³rfÃ£os; int truncava gols; JSON aceitava NaN/chaves repetidas |
| CLO-P02 | validado | Ãšltimo preÃ§o vÃ¡lido ressuscitava estado antigo e misturava eventos/linhas |
| CLO-P03 | validado | OFFICIAL e elegibilidade prospectiva eram emitidos apenas a partir da declaraÃ§Ã£o do chamador |
| CLO-P04 | validado | Universo vazio dividia por zero; Ã³rfÃ£os geravam300% de cobertura |
| CLO-P05 | validado | Abrir status podia criar/migrar banco e classificava cache existente como fresh mesmo desatualizado |
| CLO-P06 | validado | NaN, stake negativo e intervalo invertido podiam gerar SHADOW_BET |
| CLO-P07 | validado | Booleano textual viravaTrue; coordenadas impossÃ­veis, contagens de jogos fracionÃ¡rias e recibo pÃ³s-kickoff admitidos |
| CLO-P08 | validado | Sorted set crescia indefinidamente; read-modify-write perdia versÃ£o nova e admitia T4 anterior a T3 |
| LGC-P01 | validado | Leitura seguida de append sem exclusÃ£o permitia duplicar ID e liquidaÃ§Ã£o; Ãºltima linha sem LF era concatenada. |
| LGC-P02 | validado | Duas leituras combinavam lucro antigo com exposiÃ§Ã£o nova; JSON bancÃ¡rio aceitava NaN, booleanos, negativos, campos repetidos e relÃ³gios sem timezone. |
| LGC-P03 | validado | Contrato importado invÃ¡lido era liquidado; placar invertido ficava sob mando errado; ID estÃ¡vel exigia linha legada; NaN desativava teto; CLI afirmava CLV comprovado. |
| ARI-P01 | validado | NaN/Inf/escalas e covariÃ¢ncias invÃ¡lidas eram aceitos; arrays emprestados mudavam modelo; sigmoid overflow; otimizador sem sucesso podia publicar estado; labels multinomiais truncados. |
| RCA-P01 | validado | Guias sobrepostos usavam vÃ¡rios estados vigentes; cobertura parcial e pendÃªncias apenas em mapas impediam a alegaÃ§Ã£o de conclusÃ£o. |
| RCA-P02 | validado | float aceitava strings/bools e infinito negativo podia satisfazer melhora; estruturas invÃ¡lidas produziam exceÃ§Ãµes acidentais. |
| RCA-P03 | validado | Aceitava nÃºmeros/configuraÃ§Ãµes invÃ¡lidos, descartava incompletos e podia retornar GO no subconjunto; ignorava stake explÃ­cita diferente de um. |
| RCA-P04 | validado | PSR usa retornos por linha sem ajuste de dependÃªncia; DSR Ã© fornecido, nÃ£o calculado de um registro de tentativas. |
| RCA-P05 | validado | Calcula retorno por seleÃ§Ã£o em unidade fixa, sem aplicar stake da decisÃ£o e sem caixa/reserva/execuÃ§Ã£o; linha de resultado usa int(outcome). |
| RCA-P06 | validado | curated_odds nÃ£o possui status, perÃ­odo ou linha; matches tÃªm PK latest-state. NÃ£o permite reconstruÃ§Ã£o integral de revisÃµes a partir dessa tabela. |
| RCA-P07 | validado | persist_lineups grava somente linhas de jogadores; vazio nÃ£o registra envelope/tombstone; JSON invÃ¡lido histÃ³rico Ã© ignorado e gravaÃ§Ã£o nÃ£o coordena escritores. |
| RCA-P08 | validado | RecordAsync usa SET incondicional no Lua; chegada atrasada pode substituir o registro da chave por versÃ£o T3 anterior. |
| RCA-P09 | bloqueado | Compose Linux e CI delimitada agora executados; CI global inclui avaliações protegidas e permanece fora do escopo autorizado. |
| RCA-P10 | bloqueado | LGC estabilizou escritores cooperantes e reconciliaÃ§Ã£o por IDs; moeda/unidade/fluxos e custos declarados nÃ£o sÃ£o fatos comerciais autenticados nem transaÃ§Ã£o conjunta dos dois arquivos. |
| RCA-P11 | bloqueado | Git/ZIP e manifesto recebido sÃ£o verificÃ¡veis; restauraÃ§Ã£o de bancos/serviÃ§os protegidos e conteÃºdo nÃ£o recebido nÃ£o foi demonstrada. |
| RES-P01 | validado | PreÃ§os residuais usavam casa ofertante como referÃªncia, descartavam pendÃªncias e omitiam disponibilidade de contexto |
| RES-P02 | validado | Health/imports pesados e PubSub sem limite de handlers |
| RES-P03 | validado | ParÃ¢metros nÃ£o finitos ou grade invÃ¡lida chegavam ao Numba |
| RES-P04 | validado | Detector aceitava oferta soft antiga e inputs invÃ¡lidos; raiz power limitada artificialmente |
| RES-P05 | validado | Promovidos tinham coerÃ§Ãµes silenciosas, duplicatas e temporadas incompletas |
| RES-P06 | validado | Player stats carimbava pÃ³s-jogo como prÃ©-jogo e aceitava nÃºmeros invÃ¡lidos |
| RES-P07 | validado | Cobertura tratava zero denominador/arquivo ausente como aprovaÃ§Ã£o e publicava .NET antigo |
| RES-P08 | validado | Importador podia gravar em DB existente, publicar parcial e aceitar odds/contagens invÃ¡lidas |
| RES-P09 | validado | ExibiÃ§Ã£o de odds anunciava janela validada e emitia comandos de aposta sem evidÃªncia |
| RES-P10 | validado | LiquidaÃ§Ã£o diagnÃ³stica aceitava evento/placar/probabilidades invÃ¡lidos e concorrÃªncia/retry inseguros |
