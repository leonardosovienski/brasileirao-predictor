# Experimentos executados e reprodução

O [PROTOCOL.json](PROTOCOL.json) foi gravado antes dos testes; SHA-256 `e51cb8d3dd7d5a83f6978c05031701c3aa50671e31f9766ec9c4a84ad3164d54`. Resultados integrais e entradas sintéticas estão em `evidence/N01.json`, `N02.json`, `N03.json`. As tabelas/resumos derivam desses resultados via registro.

N01: domínio μ [0.05,10], alpha [0.01,2], fatores DC estritamente positivos; rejeita valores inválidos, sem clamp silencioso. Tolerância de massa 1e-6, mercados 1.0001e-6, normalização/simetria 1e-12, identidade de massa 1e-10. Busca suporte mínimo até 512, referência até 1024 com cauda <=1e-12. 147 casos, 16 entradas inválidas, falha explícita de limite. Avalia 1X2, dupla chance, BTTS, frações de DNB, totais, handicaps e placares exatos. O limite de cauda controla expectativas de pagamentos limitados em [0,1]; não garante diretamente razões de odds condicionais. Medianas: baseline 0.7064 ms e candidato 16.7493 ms, descrição desta execução única.

N02: odds reais finitas >1, 2–32 seleções, exaustividade explicitamente requerida. Underround rejeitado por padrão; proporcional só como cenário explicitamente rotulado. Mercado justo normalizado e solver sem fallback disfarçado. Sete cenários, dois métodos, dez entradas inválidas, seis engines inválidas; falha forçada com uma iteração. Quatro casos de scoring e seis contratos inválidos; Brier soma das classes e log loss natural com clip declarado. Calibração toy verifica endpoints e bins vazios, não qualidade preditiva.

N03: 18 casos adversariais do adapter e 15 asserts de contratos extraídos; 15 mutações efetivas compiladas, nenhuma inválida e nenhum sobrevivente na suite escolhida. Consulte a auditoria adicional [N03-mutation-audit.json](evidence/N03-mutation-audit.json): M04 foi detectado apenas por motivo de recusa, pois outras regras preservaram a rejeição; M02 alterou vintage/status, sem admissão insegura testemunhada. Os outros seis mutantes do adapter produziram admissão insegura. Não se reivindica taxa semântica de proteção de 100%. Curadoria aceita publicação ausente, recebimento após decisão e campos de mando adicionais em exemplos; são lacunas frente ao contrato mais estrito do estudo, não prova de vazamento em todo runtime. Mercado 1X2 completo/common vintage e autenticidade permanecem sem cobertura.

## Ambiente e isolamento efetivos

Python gerenciado 3.13.12; NumPy 2.2.6 e SciPy 1.15.3 do ambiente isolado anterior. Nenhuma instalação. Extrações AST/localizadas preservam hashes e linhas em [extractions.json](evidence/extractions.json). Não houve import do pacote operacional. SQLite somente em memória. Referência penaltyblog no SHA fixado no registro, com licença MIT anexada.

Runner usa Windows Job Object, atribuição obrigatória, máximo um processo, memória 768 MiB e timeout 120 s. Ambiente transmitido por allowlist, flags -I -S -B; hooks bloqueiam sockets/processos e leituras/escritas fora das raízes permitidas. Probes verificaram essas recusas e ausência do canário de ambiente. **Hooks Python não são sandbox de SO contra código nativo malicioso**. Foram usados apenas segmentos numéricos revisados. Docker não estava disponível; nenhum serviço foi iniciado.

Primeira tentativa com launcher do venv falhou com exit 101 devido ao limite de processos antes dos cálculos. O runner passou a usar o interpretador base diretamente. Recibos abortados foram preservados, não contados como testes concluídos. O probe de timeout de 0.3 s encerrou o job com exit 124. O primeiro diagnóstico suplementar de mutantes abortou em timestamp inválido; foi ajustado para registrar ValueError e reexecutado, mantendo ambos os recibos. Não houve escolha de parâmetros pelos resultados.

## Comandos e artefatos

Os comandos filhos exatos, cwd, chaves de ambiente, hashes, stdout/stderr, códigos de saída e duração estão nos recibos; [execution_index.json](execution_index.json) reúne inclusive falhas. No host, o launcher utilizado foi:

```powershell
& 'C:/Users/leona/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' 'C:/BRASILEIRAO/brasileirao-predictor/docs/open_source_research/OSR-20260911-02/research/runner.py' test_n01.py N01-receipt.json
```

Outros argumentos efetivamente executados: `timeout_probe.py timeout-receipt-02.json 0.3`, `reproduce.py reproduction-receipt-02.json`, `test_n02.py N02-receipt.json`, `test_n03.py N03-receipt.json` e `audit_mutations.py N03-audit-receipt-02.json`. Não executar automaticamente ao abrir a entrega: o runner contém caminhos deste host, escreve recibos e depende do ambiente isolado existente. Para nova reprodução, usar novo RUN_ID e preservar estas evidências.

Código entregue é protótipo; testes acima foram executados; N05 é somente protocolo preparado; N04 foi adiado. Não há patch operacional proposto/aplicado nem pytest/CI global.
