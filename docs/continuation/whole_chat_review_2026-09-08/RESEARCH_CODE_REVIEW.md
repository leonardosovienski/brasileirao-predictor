# Revisão adversarial da pesquisa de preços e xG

Revisão concluída em 08/09/2026. Quatro falhas mecânicas foram demonstradas com dados sintéticos e corrigidas na implementação atual. Não foi encontrado erro adicional na fórmula de combinação convexa, no cálculo dos custos ou na direção das classes. Isso não equivale a provar ausência de erros no projeto inteiro nem valida a rentabilidade dos candidatos.

O escopo foi `research/price_strength` (`quotes`, `study`, `artifacts`, CLI, `dynamic_xg`, demonstração e documentação), `price_strength_reliability` e leitura do código/metadados do runner da correção. Não houve leitura de banco operacional ou coortes protegidas, novo ajuste com dados reais, nova busca de parâmetros ou repetição de backtest. Os exemplos executados contêm apenas partidas fabricadas em 2030. Não alterei HANDOFF, planos congelados, fórmulas, configuração, runner condicional ou relatórios econômicos anteriores.

## Falhas verificadas e impacto exato

| Achado | Evidência antes da correção | Correção atual e limite |
| --- | --- | --- |
| P2 — identidade inversa de evento ausente | `scan_quotes` verificava um ID canônico associado a vários IDs do provedor, mas aceitava o mesmo `(source, source_event_id)` sob dois IDs canônicos. O exemplo gerou duas seleções para `synthetic-20`, contrariando a restrição de uma por evento real. | `quotes.py` rejeita ambos os lados da colisão e registra a razão nos reviews. `study.py` também verifica a identidade entre fixtures, pois seus scans individuais não enxergariam essa colisão. IDs iguais de provedores distintos continuam permitidos. Não comprova autenticação da identidade fornecida. |
| P2 — snapshot futuro alterava validade de replay anterior | `study.py` confrontava o kickoff de todas as quotes com a fixture antes de verificar o recebimento. Acrescentar uma revisão recebida apenas após a decisão, com kickoff corrigido, fazia o estudo abortar; o scanner isolado excluiria a revisão. | O estudo confronta kickoff apenas quando `received_at` é legível e não posterior à decisão da fixture. Identidade global só usa recibos visíveis para a respectiva decisão. Recibos ilegíveis ou sem fuso continuam no scanner e bloqueiam seu lote; não são interpretados como futuros. A exigência global de pertencer às fixtures explícitas foi mantida. |
| P2 — string de elegibilidade liberava calibração | `LambdaCalibration(eligible="false")` passava pela validação e era tratada como verdadeira por `forecast`, permitindo previsão calibrada quando havia histórico suficiente. | O construtor exige `type(eligible) is bool`. Strings, 0, 1 e `None` são recusados. Não muda calibrações produzidas pelo ajuste normal, que já fornece booleanos. |
| P2 — erro da CLI reproduzia fragmentos arbitrários | Um `--as-of` inválido contendo um canário sintético aparecia integralmente em stderr via exceção de `datetime.fromisoformat`, apesar do comentário que prometia não reproduzir entradas. | A CLI imprime apenas a classe da exceção e uma mensagem fixa. O teste não usou credencial e não demonstra exposição histórica de credenciais. Os erros estruturados das funções continuam disponíveis ao chamador; não foram removidos. |

Os quatro testes iniciais falharam como esperado no código anterior. Foram mantidos como evidência em `work/whole_chat_review/test_research_adversarial.py` e ampliados para 16 regressões em `tests/test_price_strength_review_regressions.py`. As ampliações cobrem ordem de entrega, colisão entre fixtures, namespace por provedor, alias exclusivamente futuro, recibo ilegível e booleanos estritos.

Essas correções afetam entradas ambíguas ou inválidas e a composição temporal do CLI. Não sustentam revisão dos valores já publicados pelo runner condicional: ele não usa o scanner/CLI estrito, constrói sua própria calibração como dicionário com validação explícita e teve auditoria aritmética separada. Nenhum número econômico foi recalculado nesta revisão.

## Reprodução e metadados

Há uma lacuna no congelamento transitivo da correção: `work/price_strength_diagnosis/evaluate_correction.py:23` importa `MARKETS`, `accounting`, `flatten` e `losses` de `work/price_strength_evaluation/evaluate.py`, mas esse helper não consta em `PLANO.json.inputs` nem em `EXECUTION_LOCK.json.source_sha256`. Os hashes dos arquivos declarados, por si só, não detectariam uma alteração naquele helper. Isso é uma lacuna de recibo, não prova de alteração ou erro de resultado.

O coordenador informou ter conciliado o helper com o backup anterior e as 28 fontes prévias, além dos backups e protegidos. Essa verificação retrospectiva complementa a evidência; não deve ser descrita como um hash previamente incluído no plano. Eu manteria os planos antigos intactos e arquivaria o adendo de conciliação. Em futura execução, congelaria todos os módulos diretamente usados, seus arquivos transitivos de cálculo e as versões de Python/SciPy/NumPy antes do cálculo.

`artifacts.py` tem boas barreiras locais: JSON estrito, hash dos mesmos bytes interpretados, verificação de alteração posterior de inputs, saída nova, publicação de manifest completo somente ao final e registro de falha parcial. Os hashes de fontes são coletados ao publicar; portanto não são prova independente de que o código em disco não mudou entre importação/cálculo e publicação. Manter o snapshot de código anterior à execução resolve essa condição para uma reprodução auditável. A guarda de caminhos cobre o `data/` do repositório atual, não certifica automaticamente qualquer arquivo explicitamente fornecido de outro diretório como cientificamente admissível.

Uma armadilha de validação foi identificada e evitada nesta etapa: o Pyright com `pyproject.toml` terminava sem erros porque a configuração exclui `research`; `--stats` confirmou zero fontes verificadas. O gate válido usou a configuração já existente `work/price_strength_pyright.json`, com oito fontes efetivamente verificadas. O recibo de zero arquivos não deve ser contado como aprovação desses módulos.

## Regras que manteria

- Comparar mercados completos, sem fabricar campos legados; escolher o estado por recebimento antes de verificar atividade, preço ou frescor; impedir recuperação de preço anterior após estado inválido, suspenso ou vencido.
- Excluir a casa ofertante da referência, remover margem por casa e ponderar cada casa uma única vez. A média das referências é uma hipótese de benchmark, não uma probabilidade verdadeira demonstrada.
- Manter custo fixo em vitórias e derrotas, comissão explicitamente aplicada ao lucro de cada aposta vencedora e no máximo uma seleção por evento. A comissão implementada não equivale a compensação de perdas de uma bolsa sobre todo o mercado; essa limitação está documentada.
- Reconstruir previsões com disponibilidade estritamente anterior à decisão, excluir o próprio evento das forças e impedir sobreposição entre o alvo e a calibração. `training_end` delimita alvos; a atualização das forças durante a janela é intencional e documentada.
- Ajustar um único peso convexo por mercado, usando previsões raw temporalmente fora da amostra e Brier. A solução `clip(numerador/denominador, 0, 1)` está correta; denominador zero retorna mercado. Brier 1X2 soma três classes e Brier binário usa a classe positiva uma vez. IDs repetidos são responsabilidade do runner, não devem ser inferidos por igualdade de vetores.
- Publicar todos os braços, exclusões, controles, custos e resultados negativos. Peso zero e ausência de apostas são resultados válidos de abstenção; ROI com stake zero é indefinido, não 0% de rentabilidade demonstrada.

## Limites científicos que uma correção de código não resolve

2025 já foi examinado. A alternativa de qualidade e combinação com mercado veio depois do diagnóstico; congelá-la antes de suas novas métricas limita a execução, mas não transforma esse ano em um novo holdout. Não escolheria outro limiar, janela, mercado ou filtro a partir dos subgrupos positivos do diagnóstico.

Pares xG zero foram colocados em quarentena sob uma hipótese explícita de qualidade, não identificados como faltantes por evidência do provedor. Manteria os bytes originais e os labels, com comparação na interseção comum e abstenções explícitas no painel original. Atribuir melhora à qualidade exige separar alteração de previsões da simples remoção de fixtures.

O lag de 48 horas é uma suposição declarada, não horário observado de publicação/ingestão. As odds retrospectivas agregadas não demonstram casa, oferta simultânea, status, recebimento local ou aceitação. Nenhuma dessas lacunas autoriza adaptar o histórico para satisfazer artificialmente o contrato do scanner.

Uma melhor média global de gols previstos não garante melhor distribuição de probabilidades na seleção de apostas. Comparações entre o candidato xG dinâmico e o baseline antigo tampouco isolam causalmente apenas o uso de xG. Combinar marginais de três mercados separadamente não assegura uma distribuição conjunta coerente de placares; não usaria esses marginais como matriz de placar correto.

Os intervalos existentes por semana são descritivos. Não corrigem múltiplas buscas, exploração anterior, incerteza de ajuste nem todas as dependências entre times/partidas. Esta revisão não calculou novos intervalos ou selecionou políticas a partir deles.

## O que mudaria numa execução futura

Faria a verificação de qualidade e admissibilidade dos insumos antes de executar o diagnóstico econômico: contagens de ausências/zeros, identidade, revisões e existência real dos relógios necessários. Isso teria tornado mais cedo visível a necessidade de quarentena e a impossibilidade de testar execução entre casas com o histórico disponível.

Congelaria a dependência completa dos cálculos e registraria o ambiente antes das métricas. Usaria primeiro o benchmark de mercado e a pergunta probabilística declarada; só trataria rentabilidade como testável em snapshots por casa admissíveis, com custo e disponibilidade reais. Uma futura avaliação separada precisaria de observações prospectivas fora das coortes protegidas e plano autorizado próprio; não repetiria buscas encerradas nem apresentaria novo reaproveitamento de 2025 como confirmação independente.

Repetiria o isolamento, os testes sintéticos de contrato, a reconciliação aritmética independente e a publicação integral dos resultados. Não repetiria a execução econômica apenas para melhorar números. As quatro correções encontradas justificaram novos testes de engenharia, não um novo candidato ou backtest.

## Validação e estado final

Todos os comandos foram executados por `work/validation_runner.py`, com ambiente allowlist, rede Python externa bloqueada e diretório `work/integration-repo`.

| Recibo em `work/validation/` | Resultado |
| --- | --- |
| `research_adversarial_regressions.json` | Antes do patch: quatro falhas esperadas em exemplos sintéticos. |
| `research_review_targeted_pytest.json` | 230 testes passaram, um teste de symlink não executado por restrição da plataforma. Inclui scanner, estudo, artefatos, xG, reliability e novas regressões. |
| `research_review_regressions_final.json` | Após o último ajuste apenas de tipagem: 30 testes afetados passaram. |
| `research_review_lint_final.json` | Ruff lint aprovado. |
| `research_review_format_final.json` | Cinco arquivos conferidos, todos formatados. |
| `research_review_pyright_final.json` | Configuração de pesquisa existente: oito fontes verificadas, zero erros/avisos. |

Os comandos exatos e tempos estão nos recibos JSON. As mudanças de tipo/formato posteriores à suíte não alteraram fórmulas ou parâmetros. Operacional e worktree isolado têm os mesmos hashes finais:

| Arquivo | SHA-256 |
| --- | --- |
| `brasileirao_predictor/research/price_strength/quotes.py` | `31e04a5b5739e1f13aa8c3339a0bb527dc3616decb2697aa9995ce69e0ee8889` |
| `brasileirao_predictor/research/price_strength/study.py` | `ff513cada2f69394a89c5d3067a952a556f71f036ce978124d8de54a4d7da998` |
| `brasileirao_predictor/research/price_strength/__main__.py` | `6d65c28142f583a1cf2aaa1be17e52f1fefa1253c67eea2f9ab3554dd3040119` |
| `brasileirao_predictor/research/price_strength/dynamic_xg.py` | `e780a459b08dd778877ceddb029fbc2855d02490b692a3bd456239754ba75d06` |
| `tests/test_price_strength_review_regressions.py` | `30d482f625597399e851dc135094b9f61a2797a57f20090c7d1b6100361e57de` |

Não há promoção de candidato, capital liberado ou nova evidência de lucro realizável resultante desta revisão.
