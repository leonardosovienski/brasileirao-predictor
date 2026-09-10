# Estado atual — RI-20260909

Revisão executada em 09/09 à noite de São Paulo (recibos UTC em 10/09). Raiz C:/BRASILEIRAO, trabalho solo. **Projeto globalmente não pronto; dados insuficientes para execução em T−60; lucro líquido executável não mensurável.**  [Resultado completo](continuation/integral_review_2026-09-09/RESULTADO.md), [registros centrais](continuation/integral_review_2026-09-09/REGISTROS.json) e [próximo prompt](continuation/integral_review_2026-09-09/PROXIMO_PROMPT.md).

## Base, ambiente e verificação

Checkout main, base inicial e remoto conferido ac22c56c3318623e07a722f34d44dc6cd877ea37, sem mudanças locais iniciais ou AGENTS.md aplicável. Commit final, diff e backup: C:/BRASILEIRAO/AUDITORIA/REVISAO_INTEGRAL_2026-09-09.json. Históricos e branches preservados, sem reset/force-push.

Foi instalado novo ambiente RI em work/revisao-integral-2026-09-09/venv: Python 3.13.12, pytest 9.1.1, Ruff 0.16.6, Pyright 1.1.411, Core 3.2.0, Ops 4.1.0 e extras do uv.lock. O ambiente mínimo PF, usado pela captura, ficou inalterado. SDK .NET 10.0.401 portátil e caches em RI; build em cópia pública isolada do código. Sistema Windows, Git, aplicativo Codex e serviços externos não pertencem à garantia da pasta.

1.291 casos únicos com último resultado aprovado e um skip nos lotes delimitados; quatro ensaios da barreira de isolamento aprovados. Não é suíte única integral. .NET: restore/build Release --warnaserror e 69 testes aprovados, 41 de integração pulados. Python: sdist/wheel e ajuda da CLI a partir do wheel passaram. Ruff/format no escopo CI passaram (390 arquivos); tipagem padrão exclui research, complementada por quatro arquivos explícitos. O lint de todo o repo achou 805 questões em cópias históricas fora da CI, preservadas. [Reprodução e logs](continuation/integral_review_2026-09-09/REPRODUZIR.md).

CI success confirmado apenas na base ac22c56, run 34419406215. Não atribuir esse resultado ao código RI. Docker ausente do PATH e local padrão; Redis/Compose real e aplicação operacional não foram iniciados. O worker usa contrato genérico de feed e não comprova oferta/execução comercial.

## Dados e conclusões

177/177 históricos DC conferidos por SHA256/bytes, 623.271.596 bytes. Os recibos são posteriores às decisões históricas; idade da última mudança não é idade do recebimento. CSV 2025: 380 partidas, 20 clubes, 38 jogos por clube, sem duplicação de pares dirigidos. Três capturas representam um evento, zero pares API admitidos e zero execuções.

A conta DC congelada foi reproduzida sem novo candidato: 32 apostas condicionais, 348 abstenções, stakes 32 u, custo 0,64 u, retorno incluindo principal 23,40 u, banca 100→90,76 u, perda 9,24 u. Fonte/clock e referência comprometidos impedem interpretar isso como ROI executável. Nenhum label de 2026 ou de coorte protegida foi lido para avaliação.

Quatro contratos públicos recuperados e duas tentativas Football-Data HTTP503; sem consulta autenticada, consumo de reserva, conta ou compra. Condições pessoais de capacidade, moeda, custo, aceite e validação futura seguem ausentes. [Mapa detalhado](continuation/integral_review_2026-09-09/MAPA_DADOS.md).

## Correções e caminho ativo

Admissão independente passa a rejeitar participantes/competição trocados, estados contraditórios, clocks ausentes/futuros, JSON duplicado/não finito; publicação final não substitui auditoria concorrente. TemporalPolicy v2 conserva o dia UTC com kickoff parcial; event-backtest/v2 separa dias, deduplica alvos e abstém por mercados/probabilidades/odds não suportados. Import não grava log operacional. Simulador recusa liga antes de abrir DB.

Serving legado (predict/display) não estabelece identidade e clocks de preços suficientes; permanece fora do caminho de decisão econômica. Config/modelos e dependências capazes de mudar coleta protegida não foram alterados. Não ligar xG/ajustar filtros para encobrir falta de preços/custos. [Problemas e critérios de fechamento](continuation/integral_review_2026-09-09/PROBLEMAS.md).

## Agenda independente

ID completar-dados-do-brasileir-o, tarefa anterior 01 a 08756-2962-7 c 43-9773-c 790 cc 81329 d. A consulta atual via view apenas apresentou cartão, sem estado legível ao modelo; o TOML de AUDITORIA é histórico. Não afirmar agenda ativa a partir dessa cópia e não duplicar. Na conferência RI não havia tentativa followup ou processo de captura concorrente.

Coletor followup_capture.py preservado (SHA 31de8315c687cc596ae3fb9aebd221701e9f6df690903248c15dfb9b84b33d88). Auditor audit_followup.py corrigido ativado (SHA ebce7ddeb384b347be4985b7a3812a1b83c7dfaceafdb3e2a6cb00f7e2d09a24), com versão anterior guardada. Fixture/casas/decisão/janela/reserva 20/quota/agenda não mudaram. [Ativação](continuation/integral_review_2026-09-09/evidence/activation.json).

Decisão 11/09/2026 23:00 UTC (20:00 São Paulo), kickoff 12/09 00:00 UTC, fixture id 1000032566887012, Pinnacle/bet 365.bet.br. Seguir [protocolo DC](continuation/data_completion_2026-09-09/CONTINUIDADE.md) e o próximo prompt RI; sem coleta antecipada, retry não autorizado, mudança retrospectiva ou consulta de desfecho.

## Preservação e limites

H14/H15/H9/A1 integralmente preservados: sem resultados intermediários, métricas, avaliadores, claims, agendas, DB/Redis operacionais ou mudanças de dependências da coleta. A cobertura dessas áreas limita-se a metadados/contratos permitidos. A revisão não as homologou.

Migração anterior: recibo de 12.423 entradas mais manifesto, 9.477.623.208 bytes e cinco snapshots, sem nova abertura do conteúdo protegido. O novo backup verifica recuperação Git em repositório bare, sem restaurar operação. Não garante arquivos nunca enviados, ferramentas de sistema ou alterações posteriores no computador antigo. [Mapa geral](DATA_MAP.md), [mandato](continuation/MANDATO_LUCRO_2026-09-09.md) e [histórico](../HANDOFF.md).
