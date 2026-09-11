# OSR-20260911-02 — continuação verificável

Foram entregues e executados protótipos isolados de cauda NB/DC, matemática de mercado e admissão temporal. N05 tem protocolo preparado, mas não está elegível. Não houve fitting, evidência preditiva nova ou operação econômica. Tabelas geradas de `registry.json`; esta é uma atualização da rodada 01.

| Frente | Mudança entregue | Decisão | Próximo gate |
|---|---|---|---|
| N01 | Diagnóstico analítico e suporte adaptativo mínimo com falha explícita no limite. | Conservar diagnóstico e protótipo; corrigir custo e validar domínio completo em pesquisa antes de revisão de integração. | Cobertura dos limites operacionais, orçamento de latência e revisão de chamadas/mercados condicionais. |
| N02 | Adapter estrito de odds/probabilidades, regimes explícitos, scoring 1X2 e bins fixos. | Merece revisão do contrato para futura integração; manter implementação isolada. | Revisão da API, chamadores e semântica de mercados reais completos. |
| N03 | Admissão estrita de uma seleção, casos adversariais e mutação efetiva de código extraído. | Conservar suite e adapter de pesquisa; tratar lacunas como escopo de admissão, sem declarar defeito global. | Completar admissão conjunta 1X2 e evidência de identidade/relógios reais. |
| N04 | Não executado. | Adiar; não duplicar descanso/contexto existentes. | Questão concreta de transferência e fonte admissível. |
| N05 | Protocolo A/B separado, ajuste limitado e contrato de dados explícito. | Não executar fitting nem consultar desfechos para decidir viabilidade. | Manifesto imutável aprovado, resolução de linhagem e auditoria de clocks/odds/histórico. |

N01 reproduziu primeiro as massas omitidas anteriores: aproximadamente 0.0000002611, 0.00415326 e 0.14203866. Em 147 casos sintéticos, o suporte adaptativo apresentou erro máximo nos mercados de 9.38246789e-07, abaixo de 1.0001e-6. A cauda máxima da referência foi 2.062e-13. Isso corrige uma propriedade numérica no domínio ensaiado, sem demonstrar melhora de previsão. O domínio menor e o custo impedem tratá-lo como substituto operacional.

N02 tornou explícitos underround, mercado justo, convergência e rejeição de entradas/saídas inválidas. As métricas e bins foram verificados por fórmulas e fixtures: não foi medida calibração de jogos reais.

N03 detectou todos os 15 mutantes escolhidos. A auditoria semântica distingue seis mutantes do adapter que permitiram admissão insegura, um que alterou vintage/status e outro que apenas mudou o motivo da recusa; há também sete mutantes de funções baseline detectados. O número bruto não certifica cobertura total ou autenticidade de fontes.

Dados: foram aprofundadas documentações de finalistas, sem chamadas pagas ou amostras de resultados. Football-Data oferece fechamento, insuficiente para T−60; The Odds API documenta snapshots históricos pagos, ainda sem comprovação da coorte/casa/clocks requeridos; Sportmonks não deve ser presumido um arquivo plurianual. Detalhes e ações possíveis em [DATA_ADMISSIBILITY.md](DATA_ADMISSIBILITY.md).

N05-A exige manifesto autorizado, resolução da sobreposição BE e informação contemporânea verificável. **Aceitação pessoal de apostas não é requisito de A.** N05-B continua separado e exige evidência econômica adicional. O protocolo não inventa temporadas para aparentar independência.

## Evidências e limites

- [Baseline e proteções](BASELINE.md)
- [Experimentos, comandos e falhas preservadas](EXPERIMENTS.md)
- [Protocolo N05](N05_PROTOCOL.md) e [contrato de dados](N05_DATA_CONTRACT.json)
- [Decisões por frente](DECISIONS.md) e [registro estruturado](registry.json)
- [Verificação de entrega](evidence/delivery_validation.json)

Runtime, locks, dependências globais, serviços, agendamentos e automações não foram alterados. Não há commit, push ou merge, nem patch operacional aplicado. O código entregue permanece sob `docs/open_source_research/OSR-20260911-02/research/`.
