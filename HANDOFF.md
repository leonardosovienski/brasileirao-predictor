# Handoff — PUB-20260910

## Entrega arquitetural publicada — 11/09/2026

Versão **0.2.0** publicada: [release e artefatos](https://github.com/leonardosovienski/brasileirao-predictor/releases/tag/v0.2.0). [CI de engenharia aprovada](https://github.com/leonardosovienski/brasileirao-predictor/actions/runs/34630041002) para a fonte `4dbd35332344000d116ea2ac56903c77e73f9aa2`. Consulte [ARCHITECTURE_IMPLEMENTATION.md](ARCHITECTURE_IMPLEMENTATION.md) para comportamento, migração e limites. Este registro atualiza a entrega de software; estados científicos e registros datados abaixo conservam sua autoridade e contexto histórico.

## Exportação local de relatos para Cain — 11/09/2026

[tools/export_cain_status.py](tools/export_cain_status.py) é um exportador stdlib
independente do runtime científico. Lê somente `docs/EVIDENCE_REGISTRY.md`, com SHA-256
previamente conferido e fonte commitada. Preserva estados literais, offsets, hashes,
cobertura parcial e tempos desconhecidos. Não abre bancos, usa LLM ou executa pipeline.
Publicações desta instalação ficam em `C:\BRASILEIRAO\work\cain-l0\publications`.
Cain recebe cópias autorizadas; este produtor continua independente do consumidor.

```text
python tools/export_cain_status.py --root CAMINHO_DO_CHECKOUT --expected-sha SHA256_CONFERIDO --output DESTINO_NOVO_FORA_DO_CHECKOUT.json
python tools/test_export_cain_status.py
```

O destino deve permanecer na raiz local autorizada do projeto. Não reutilizar um hash
antigo depois de mudar a fonte. A publicação é ResearchSnapshotV1; o consumidor usa o
validador canônico do contrato. O exportador não impõe instalações ao ambiente científico.
No Windows, os checks usam Python auxiliar stdlib; temporários ficam na raiz do projeto.

Integração real Brasileirão → Cain exercitada nesta rodada: exportação, validação
canônica, importação/reimportação, consulta na interface, referências e recuperação
sem acesso ao produtor. É integração de relatos públicos selecionados, sem nova
validação científica/econômica. O estado do runtime e os protocolos anteriores permanecem.
Mudança restrita a ferramentas de intercâmbio; não altera pacote ou recibos R8/operacionais.
Branch de continuidade deste incremento: `integration/cain-status-20260911`.


Comece por [resultado](docs/continuation/publication_2026-09-10/RESULTADO.md), [retomada](docs/continuation/publication_2026-09-10/PROXIMO_PROMPT.md), [registro](docs/continuation/publication_2026-09-10/REGISTROS.json) e [revisão do chat](docs/continuation/publication_2026-09-10/REVISAO_DO_CHAT.md). O contexto visível e os dois mandatos integrais estão arquivados na mesma pasta; não é necessário depender da conversa para saber o que foi feito ou o que continua pendente.

345 testes Python por versão, 160 .NET e Compose Linux passaram no workflow delimitado. CI global não executada; seus critérios foram preservados. Não executar avaliadores protegidos ou pytest global. Publicação e recuperação são atestadas por seus próprios recibos, não apenas por esta afirmação documental.

Mantenha C:/BRASILEIRAO: código em brasileirao-predictor; acervo em DADOS_PRESERVADOS; roteiros/evidências em work; pacotes em ENTREGAS; bundles em BACKUPS; recibos em AUDITORIA. Sete requisitos externos/protegidos continuam no registro. Capital false; lucro executável não demonstrado. A automação DC pertence a outra tarefa identificada no próximo prompt; não a excluir junto com esta conversa.


## Implementação arquitetural local — 2026-09-11

As alterações candidatas, seus limites, verificações e rollback estão em [ARCHITECTURE_IMPLEMENTATION.md](ARCHITECTURE_IMPLEMENTATION.md). Esta implementação local não publica releases, não atualiza automaticamente os consumidores e não altera os vereditos científicos históricos.
