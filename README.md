# brasileirao-predictor

## Candidato local ResearchBundleV1

[Exportador aditivo de claims/lineage](docs/RESEARCH_BUNDLE_V1.md), com dez testes
e E2E de backup/restore. Prediction/settlement/PIT não foram fabricados nem reexecutados;
coortes protegidas preservadas. Sem instalação operacional ou publicação nesta tarefa.

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


Pesquisa de capacidades **OSR-20260911-01 a 03** preservada: [retomada sem o chat, código offline, evidências e decisões](docs/open_source_research/README.md). Integração somente de pesquisa; nenhuma nova evidência preditiva/econômica ou ativação operacional.

Estado **PUB-20260910**: correções de dados temporais, caixa, persistência e runtime validadas em laboratório Windows e Linux. **345 testes Python por versão (3.13/3.14), 160 .NET e Compose Linux aprovados no escopo sintético.** Lucro executável e homologação global ainda não demonstrados; capital desabilitado.

[Resultado e limites](docs/continuation/publication_2026-09-10/RESULTADO.md) · [registro corrente](docs/continuation/publication_2026-09-10/REGISTROS.md) · [reprodução](docs/continuation/publication_2026-09-10/REPRODUZIR.md) · [retomada sem o chat](docs/continuation/publication_2026-09-10/PROXIMO_PROMPT.md) · [CI delimitada](https://github.com/leonardosovienski/brasileirao-predictor/actions/runs/34552247397).

O histórico visível, os mandatos e os roteiros locais estão arquivados na entrega. [Revisão das decisões](docs/continuation/publication_2026-09-10/REVISAO_DO_CHAT.md), [dados/fontes](docs/continuation/publication_2026-09-10/DADOS_E_FONTES.md) e [índice documental](docs/INDICE_DOCUMENTACAO.md). Conteúdo versionado é recuperável por clone/pull; dados privados e fontes com restrição de redistribuição permanecem em C:/BRASILEIRAO.

Registro: 52 itens validados e sete bloqueados; Compose Linux fechado dentro de RCA-P09, CI global ainda não executada por incluir avaliações protegidas. Inventário base: 399 arquivos com leitura semântica e 59 protegidos restritos a contratos/metadados. H14/H15/H9/A1 permanecem preservados. Trabalho local em C:/BRASILEIRAO, solo. Não confundir testes sintéticos com oferta aceita ou autorização financeira.

[Publicação e recuperação conferidas](docs/continuation/publication_2026-09-10/PUBLICADO.md).


## Implementação arquitetural local — 2026-09-11

As alterações candidatas, seus limites, verificações e rollback estão em [ARCHITECTURE_IMPLEMENTATION.md](ARCHITECTURE_IMPLEMENTATION.md). Esta implementação local não publica releases, não atualiza automaticamente os consumidores e não altera os vereditos científicos históricos.
