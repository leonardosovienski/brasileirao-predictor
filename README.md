# brasileirao-predictor

Pesquisa quantitativa e software para o Brasileirão Série A, em C:/BRASILEIRAO.

**Correções e integração local validadas; lucro executável ainda não demonstrado.** O projeto não está globalmente pronto para operação financeira. [Estado atual](docs/ESTADO_ATUAL.md) · [Resultado IE](docs/continuation/implementation_2026-09-10/RESULTADO.md) · [Reproduzir](docs/continuation/implementation_2026-09-10/REPRODUZIR.md).

## Implementação atual

O parser de mensagens do kernel é compartilhado e leve, recusando duplicatas JSON. O smoke verifica resultados sem iniciar NumPy/Numba e consumir sua validade durante o import. Um laboratório descartável comprova a integração Python/.NET/Redis, incluindo recuperação de notificação perdida e um único sinal para a requisição corrente.

O comando offline `python -m brasileirao_predictor.research.price_strength.capture_decision --help` audita arquivos explícitos de captura e recibo, exige identidade/kickoff congelados, preserva tentativas fracassadas e recusa preços antigos após um estado posterior inválido. Seu resultado separa comparação API condicional e execução; faltando evidência comercial, mantém abstenção. Não envia ordens ou liquida partidas.

Foram aprovados282 testes Python do escopo afetado,27 com Redis real,110 .NET e7 ensaios de isolamento. Quatro testes Python foram pulados com motivos registrados. [Logs, cobertura e limites](docs/continuation/implementation_2026-09-10/REPRODUZIR.md). Instalação, testes sintéticos e vantagem hipotética de preço não demonstram rentabilidade.

## Dados e continuidade

As3 capturas permitidas de1 fixture voltaram a ser rejeitadas como par API. Zero apostas/exposição; custos fixos e lucro líquido total seguem desconhecidos. A [revisão RI](docs/continuation/integral_review_2026-09-09/RESULTADO.md) preserva a auditoria dos177 históricos,380 jogos2025 e o resultado condicional negativo já conhecido, sem nova escolha de filtro.

Leia [registros atuais](docs/continuation/implementation_2026-09-10/REGISTROS.json), [mapa de dados](docs/DATA_MAP.md), [índice](docs/INDICE_DOCUMENTACAO.md), [retomada](docs/continuation/RETOMADA.md), [próximo prompt](docs/continuation/implementation_2026-09-10/PROXIMO_PROMPT.md) e [mandato](docs/continuation/MANDATO_LUCRO_2026-09-09.md). A errata UTF8 dos registros RI é sucessora, sem reescrever evidências congeladas.

H14/H15/H9/A1 permanecem protegidos. O [protocolo DC](docs/continuation/data_completion_2026-09-09/CONTINUIDADE.md) conserva fixture, casas, janela e decisão de 11/09 23:00UTC; a automação existente não foi duplicada. O serving legado, Compose operacional e feed comercial não estão homologados pelo laboratório. Código/entrega: C:/BRASILEIRAO/brasileirao-predictor e C:/BRASILEIRAO/ENTREGAS/BRASILEIRAO_IE_20260910.
