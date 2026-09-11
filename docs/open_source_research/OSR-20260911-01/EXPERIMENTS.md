# Experimentos e próximos gates — OSR-20260911-01

## G1 registrado antes dos resultados

[G1_PROTOCOL.json](G1_PROTOCOL.json) foi gravado antes dos ensaios; hash registrado no resultado: `0aa29df183486655ceb098b8d30bd8836bdddb995122527bcdcc87ef78f70f76`. Três perguntas de engenharia, parâmetros fixos, sem fitting, tuning, sementes aleatórias ou partidas reais. Não é derivação econômica de H14/H15/H9/A1/BE. Nenhum resultado de coorte foi usado para escolher entradas.

Evidência executada em [evidence/benchmark_results.json](evidence/benchmark_results.json), código em [evidence/benchmark.py](evidence/benchmark.py), módulos e hashes em `evidence/lab` e manifesto. Só os módulos locais relevantes e dois arquivos de penaltyblog foram copiados; `__init__.py` vazios evitam inicialização do pacote operacional. São cópias para teste, não mudanças do runtime.

Comando executado: `C:/BRASILEIRAO/work/open-source-research-OSR-20260911-01/venv/Scripts/python.exe -I -B C:/BRASILEIRAO/work/open-source-research-OSR-20260911-01/benchmark.py`.

Ambiente: Python 3.13.12, numpy 2.2.6, scipy 1.15.3, Windows 11; sem carga de desempenho equivalente entre engines. O tempo `0.268184s` mede somente o trecho numérico após imports, não instalação/startup e não é benchmark de performance.

**Limitações e desvios do isolamento:** audit hook bloqueou caminhos fora do laboratório/raízes Python, conexão de rede e criação de subprocessos durante o harness. Isso não é sandbox de sistema operacional. Variáveis de ambiente não foram sanitizadas e ausência de credenciais no processo não foi certificada; os módulos revisados executados não leem credenciais ou stores operacionais. O timeout de 120 s declarado no protocolo não foi aplicado como limite de subprocesso. A primeira tentativa falhou no import de NumPy/datetime antes dos cálculos; após pré-import de datetime e normalização dos caminhos permitidos, houve uma execução numérica concluída. O protocolo original foi preservado, sem apagar o desvio. Não houve segunda exploração numérica nem ajuste baseado em resultados. Para futuras execuções, corrigir essas condições antes do gate; não é necessária reexecução para reinterpretar os números já guardados.

## T01 — cauda da NB + Dixon–Coles

Hipótese: normalizar suporte 0..12 oculta erro que pode ser material. Controle: produto de CDFs NB mais a alteração exata das quatro células DC, dividido pela massa total corrigida; grade 0..100 serve de comparação expandida. Parâmetros são `(lambda_home, lambda_away, alpha, rho)`, com `Var = mu + alpha*mu²`.

| Parâmetros sintéticos | Massa omitida 0..12 | Maior diferença 1X2 contra 0..100 | Acima de 1e-6 |
| --- | --- | --- | --- |
| [1.4, 1.1, 0.1, -0.05] | 0.000026108% | 0.000013054 pp | False |
| [2.5, 2.0, 0.5, -0.05] | 0.415325763% | 0.130143309 pp | True |
| [5.0, 4.0, 1.0, -0.02] | 14.203866339% | 2.332642881 pp | True |


A identidade entre soma bruta e cálculo analítico ficou dentro de 8,9e-16. A referência expandida não foi declarada infinita: a massa omitida é calculada pela CDF, e a comparação 1X2 usa grade finita 100. A normalização DC foi incluída; usar apenas `1 − soma da grade normalizada` sempre daria zero e esconderia o problema.

**EXECUTION_VERIFIED / C4 / E5 LOCAL ENGINEERING:** diagnóstico confirmado nos dois stresses. RECOMMENDATION K01: expor massa omitida e tolerância; avaliar suporte adaptativo. Não sabemos a frequência desses parâmetros nos forecasts reais, nem efeito em calibração, empate ou PnL. Resultado não demonstra modelo inviável em todo domínio.

## T02 — margem e referência externa limitada

Referência: [penaltyblog no SHA fixado](https://github.com/martineastwood/penaltyblog/tree/15ebb8a299fa75524ac57e32f3778f174bd5b42b), somente `implied.py`/`models.py` revisados, comparados com Shin local e power de structural_edge. Tolerância predefinida 1e-8; seis vetores × dois métodos.

| Odds decimais sintéticas | Método | Overround | Erro máximo | Resultado externo |
| --- | --- | --- | --- | --- |
| [2.7, 2.3, 4.4] | shin | 0.0324257 | 3.82e-13 | ambos retornaram |
| [2.7, 2.3, 4.4] | power | 0.0324257 | 3.57e-13 | ambos retornaram |
| [1.9, 1.9] | shin | 0.0526316 | 2.5e-13 | ambos retornaram |
| [1.9, 1.9] | power | 0.0526316 | 3.2e-13 | ambos retornaram |
| [1.5, 4.0, 7.0] | shin | 0.0595238 | 4e-13 | ambos retornaram |
| [1.5, 4.0, 7.0] | power | 0.0595238 | 3.15e-13 | ambos retornaram |
| [3.0, 3.0, 3.0] | shin | 0 | 0 | ambos retornaram |
| [3.0, 3.0, 3.0] | power | 0 | 5.55e-17 | ambos retornaram |
| [4.0, 4.0, 4.0] | shin | -0.25 | não comparável | ValueError: f(a) and f(b) must have different signs |
| [4.0, 4.0, 4.0] | power | -0.25 | 4.62e-13 | ambos retornaram |
| [1.001, 1.001, 1.001] | shin | 1.997 | 1.61e-13 | ambos retornaram |
| [1.001, 1.001, 1.001] | power | 1.997 | não comparável | ValueError: f(a) and f(b) must have different signs |


Dez dos doze pares retornaram dos dois lados; diferença máxima 4,63e-13. Os dois pares restantes não contam como concordância. Underround Shin gera erro de bracket externo; power externo usa limite fixo que falha no vetor extremo 1.001. O local retorna terços nesses casos. Isso demonstra robustez nestes controles, não preço economicamente correto.

Controle negativo: `ImpliedProbabilities([-0.1, 0.5, 0.6], ...)` foi aceito pelo dataclass externo. Uma soma próxima de 1 não valida não negatividade. A política local de fallback Shin também precisa ser exposta para não parecer solução Shin bem-sucedida quando houve fallback proporcional.

**C4 / E5 LOCAL ENGINEERING, resultado misto:** manter implementação local e usar referências com validação de domínio. Não há evidência de superioridade preditiva universal de Shin, power ou outro método. A docstring que chama probabilidades de “reais” não constitui demonstração; sugerimos linguagem de estimativa por convenção, sem editar o original nesta rodada.

## T03 — pagamentos atômicos e caixa simultâneo

25 point masses de placar (0..4 × 0..4), 11 linhas AH e sete totais = **450 comparações** contra oráculo aritmético independente do pricer. Máximo erro observado **0**. Asserções adicionais de 1X2, DNB e BTTS passaram. Para handicap de quarto, o resultado é fração da stake em win/push/lose, não três eventos mutuamente exclusivos por partida.

Duas ordens simbólicas simultâneas de 60 sobre caixa 100, odd 2 e custo 0: SYN-A foi aceita pela ordenação determinística; SYN-B recebeu NO_CAPITAL. Antes da liquidação: caixa 40, aberto 60 e ROI indisponível. Depois: caixa 160. A vitória foi definida no fixture sintético, não prevista. O capital real continuou desabilitado.

**C4 / E5 LOCAL ENGINEERING:** KEEP pagamentos e reserva testados. Não foram certificados lay, comissão de exchange, void por regra nominal, fills parciais, atraso real, mudança de preço, múltiplos mercados da mesma partida ou imposto. O simulador lido rejeita `event_id` duplicado, portanto não é carteira multi-market por jogo sem extensão contratual. Totais de quarto são rejeitados no pricer atual; AH de quarto existe. Esse limite é explícito, não bug inferido pela ausência de mercado.

## Registro de tentativas e inferência

- T00/ambiente: um import probe do ambiente antigo sem numpy; ambiente novo criado. Primeira chamada do harness abortou durante imports, sem observação numérica ou econômica.
- T01–T03: uma execução numérica determinística concluída; sem ajustes de parâmetros, repetição de holdout ou busca de significância.
- Os testes existentes foram lidos; nenhuma suíte pytest oficial foi executada. O pacote externo completo não foi instalado/executado.
- C4 é atribuído somente aos contrastes descritos; E5 só engenharia. E4, E6-H e E6-P não foram produzidos.

## Até cinco próximos experimentos, por utilidade de decisão

N01–N04 são propostas delimitadas; não executadas. N05 está bloqueado e precisa completar pré-registro com dados/permissões antes de se tornar protocolo executável. A ordem privilegia informação e dependências, não apenas décimos do score.

### N01 — K01

**Pergunta:** Qual suporte atende erro de massa <=1e-6 sem alterar a família NB/DC?

**Teste mínimo:** Em cópia isolada, usar os três vetores já registrados mais grade de stress fixada antes de executar (mu em {0.2,1,3,5}, alpha em {0.05,0.5,1}, rho admissível). Comparar diagnóstico analítico e suporte adaptativo com CDF, incluindo inversão de mando e limite máximo explícito.

**Pré-requisitos:** Revisão do pequeno adapter e protocolo novo. Só entradas sintéticas; nenhum ajuste de modelo ou resultado histórico.

**Decisão:** Erro de identidade <=1e-10 e massa omitida <=1e-6 para casos convergentes; falha explícita se teto impedir tolerância. Registrar variação de 1X2 e custo com carga igual. Não escolher tolerância pelo PnL.

**Próximo gate:** G1 sintético elegível; integração em runtime requer autorização posterior.

**Informação / esforço / risco:** Alta: decide se diagnóstico basta ou se suporte adaptativo é necessário. Esforço baixo; risco baixo; nenhuma coorte real.

### N02 — K03, K04, K05

**Pergunta:** As convenções matemáticas são explícitas e os adapters rejeitam saídas inválidas?

**Teste mínimo:** Um protocolo, subcontrastes independentes e sem tuning: 6 vetores T02 + NaN/inf/odds<=1; scoring com classes 1/X/2, previsão perfeita/uniforme/invertida e clipping registrado; repetir apenas invariantes afetadas de pagamentos se houver adapter novo. Terceiro Shin e scoringrules só após revisão dos imports.

**Pré-requisitos:** Fixar redução Brier soma 0–2, log loss natural com clip 1e-12 e política underround/fallback. Não usar ROI para escolher de-vig. Não repetir T03 sem mudança pertinente.

**Decisão:** Diferencial <=1e-8 no domínio comum; probabilidade negativa/não finita deve ser rejeitada; classe/redução idênticas; pagamentos conservam stake e caixa. Divergência de convenção deve ser explicitada, não forçada a passar.

**Próximo gate:** G1 de engenharia; lay, comissão de exchange, fills parciais e extensão multi-market continuam fora até contrato nominal.

**Informação / esforço / risco:** Alta: impede comparações inválidas e adoção cega da referência. Esforço baixo a médio; risco baixo.

### N03 — K02, K08, K10

**Pergunta:** O caminho de dados rejeita informação não disponível no cutoff sem ressuscitar uma versão antiga?

**Teste mínimo:** Fixtures inventadas de publicação tardia, revisão tardia, relógio ausente, remarcação, mesmo kickoff, ID invertido, suspended após active e fonte sem recibo. Mutation tests removem cada guard; medir falsos negativos e motivos de exclusão, sem qualquer acesso ao store oficial.

**Pré-requisitos:** Cópia mínima dos contratos e dependências revisadas; declarar diferença entre replay condicional e observação recebida. Não consultar H14/H15/H9/A1/BE. Confirmar relação com gap CPL-P22 sem reabrir seus trials.

**Decisão:** Cada mutação inválida deve falhar no gate designado; exemplos válidos preservados. UNKNOWN não vira known_at inferido. Registrar limite: teste de schema não demonstra autenticidade do timestamp.

**Próximo gate:** G1 sintético; nova coleta só com orçamento e autorização específicos, preservando DC e reservas.

**Informação / esforço / risco:** Muito alta: decide quais caminhos podem alimentar comparação preditiva futura. Esforço médio; risco baixo no sintético; alto se extrapolado aos dados reais.

### N04 — K09

**Pergunta:** O contrato de eventos preserva orientação, unidade e missingness antes de estimar xT?

**Teste mínimo:** Campo sintético com pontos conhecidos, troca de lado no intervalo, passe bem-sucedido/falho e lacuna de tracking. Transformar e inverter coordenadas com kloppy; calcular transição xT analítica mínima sem treinar em partidas. Não combinar sincronização e ganho preditivo no mesmo teste.

**Pré-requisitos:** Ambiente separado compatível; fixture própria. socceraction 1.5.3 não cabe no Python 3.13/3.14 operacional. Sem compra/download de partidas nem tracking protegido.

**Decisão:** Roundtrip espacial dentro de tolerância pré-fixada (1e-8 metros); falha e missing não equivalem a sucesso/zero; xT de toy coincide com conta manual. Resultado só habilita análise de eventos.

**Próximo gate:** G1 sintético condicional à revisão de dependências; dados brasileiros exigem contrato/licença/PIT próprios.

**Informação / esforço / risco:** Média: decide se há utilidade antes do custo de eventos/tracking. Esforço médio; risco baixo científico; dependências moderadas.

### N05 — K06, K07, K11, K12

**Pergunta:** Em uma coorte nova e admissível, força/contexto melhora probabilidades além do mercado contemporâneo?

**Teste mínimo:** Protocolo antes dos dados: baseline simples de gols, vigente sem odds, market-only e composição com uma única feature adicional escolhida por mecanismo. Walk-forward por jogo; fit/calibração só no treino. Comparação pareada de log loss, Brier e calibração de empate; no-bet na camada econômica. Não executar nesta rodada.

**Pré-requisitos:** Revisão explícita da relação com famílias BE e hipóteses encerradas; coorte materialmente nova, clocks observados, bookmaker/linha/cutoff equivalentes, cobertura e orçamento fixados, holdout não exposto. Tamanho, janelas, mínimo efeito e multiplicidade ainda pendentes: este é desenho condicionado, não protocolo econômico executável aprovado.

**Decisão:** Definir antes da abertura dos labels o mínimo efeito relevante e IC pareado/cluster por jogo ou blocos adequados. Ganho precisa sobreviver à ablação de odds e cobertura; IC inconclusivo não é ganho. Economia somente com custos/fills admissíveis; sem isso conclusão exclusivamente preditiva.

**Próximo gate:** BLOCKED_DATA_AND_PROTOCOL_REVIEW. Qualquer integração/capital continua sem autorização.

**Informação / esforço / risco:** Alta quando os dados existirem: distingue informação esportiva de reprodução de preço. Esforço alto e ainda incerto; risco alto: vazamento, multiplicidade e acesso a coortes; não elegível agora.
