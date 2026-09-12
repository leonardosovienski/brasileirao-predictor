# Exportação ResearchBundleV1 — candidato local

Este incremento é aditivo ao exportador ResearchSnapshotV1, que permanece intacto.
O produtor usa somente o pacote independente predictor-research-bundle 1.0.0 do Ecosystem;
não importa CAIN nem executa o runtime científico. Instale o wheel compartilhado em ambiente
auxiliar separado. Não instale o runtime de produção para usar estas ferramentas.

Fontes têm allowlist fixa, SHA256 explícito, limite de 100 KB e precisam estar commitadas.
O exportador verifica novamente os hashes antes de criar saída. O destino é novo, fora do
checkout e dentro da raiz do produtor. Manifest é escrito por último; não há sobrescrita.
O horário --exported-at é explícito para permitir repetição determinística e nunca preenche
os clocks científicos ausentes. Cada entity tem status, eixo, payload, clocks e proveniência.

Entrada: `python tools/export_cain_bundle.py --root ROOT --expected-sha SHA --destination DESTINO_NOVO --exported-at ISO_OFFSET`.
Fonte única: docs/EVIDENCE_REGISTRY.md. Exporta as três claims documentadas com todas as
colunas literais, relações SUPPORTED_BY com o documento recebido e REFERENCES para relatórios
explicitamente citados. Sem prediction/settlement admissível neste recorte; não foram inventados.
A indicação de horizonte permanece no payload; event_at/recorded_at/available_at ficam null.
O contrato bitemporal existente distingue event_at/published_at/ingested_at e o cutoff pertinente;
qualquer futuro slice deverá conservar esses clocks e usar o mecanismo PIT existente. Este
exportador não abre observações/coortes H14/H15/H9/A1 nem reavalia holdout.

Testes: `python tools/test_export_cain_bundle.py`. E2E em
C:/BRASILEIRAO/bundle-v1-final-e2e; logs em C:/BRASILEIRAO/work/bundle-installed-tests.log.

Validação: 9 testes específicos com fixtures fictícias e fontes commitadas: determinismo,
UNKNOWN/null, leitura sem alteração, fonte inesperada/ausente/alterada, hash incorreto,
destino existente/checkout, entrada malformada e credencial fictícia. Wheels e E2E foram
exercitados separadamente; isso não é validação científica ou econômica.

Nenhum push, release, instalação operacional, modelo, hipótese, trial, holdout, ledger ou
banco científico foi executado/alterado. Rollback desativa esta ferramenta opcional e mantém
as publicações/bundles existentes. Não apagar evidências para retornar ao caminho SnapshotV1.

## Ampliação documental da retomada

`--replay-sha SHA256` admite somente reports/replay_round_2026_08_22.json,
com status obrigatório DIAGNOSTIC_CONTAMINATED_NOT_CONFIRMATORY e até 20 jogos.
Preserva kickoff_at, captured_at e generated_at separadamente. Published_at,
ingested_at e prediction_cutoff permanecem null; observation_selection=NOT_PROVEN.
O replay não é convertido em prediction prospectiva nem settlement certificado.
Nenhum motor PIT foi duplicado ou executado: não há entrada admissível que demonstre
as observações conhecidas na previsão. H14/H15/H9/A1 continuam protegidos.

10 testes do exportador instalado passaram. O bundle real em
C:/BRASILEIRAO/bundle-v1-completion-e2e contém 14 entidades, 27 relações e dois
objetos recebidos. As duas fontes pinadas permaneceram byte a byte inalteradas.
