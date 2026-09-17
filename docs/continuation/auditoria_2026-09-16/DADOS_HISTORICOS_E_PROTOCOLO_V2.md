# Dados históricos e protocolos — resultado da nova rodada

## Resultado

Foi implementada e instalada uma versão sucessora explícita de protocolo,
`br-prospective-repair-v2-20260915`, com cálculos e validação de entradas.
**155 testes passaram carregando o código instalado**, sendo 47 casos novos.
Um desses testes compara 200 combinações aleatórias de probabilidades e placares
com as métricas do Core. Ruff passou. Não houve nova alteração no CAIN.
Isso confirma os casos testados, não ausência universal de bugs.

A busca histórica foi ampliada, mas **não recuperou novas previsões**.
Continuam reconstruídas retrospectivamente 2 das 6 previsões por braço H15.
Não se restaurou validade prospectiva nem identidade completa do código original.

## O que foi especificado e implementado

- Climatologia 1X2 Dirichlet(1,1,1) e OU2.5 Beta(1,1), com fórmulas explícitas.
- Bloco pela data UTC da partida; corte fixo às 00:00 UTC do dia anterior.
  Essa escolha nova, mais conservadora, permite a janela de previsão de 24 horas.
  Só entram resultados finalizados e disponíveis estritamente antes do corte.
  São exigidos pelo menos 200 jogos; chegadas tardias não mudam o snapshot anterior.
- Registro com probabilidades completas, estado do modelo, código, configuração,
  corte de treino, timestamps e hashes. A baseline deve ser reproduzível a partir
  do histórico incluído no registro. A probabilidade OU2.5 não pode ser omitida.
- Recibos precisam preceder o kickoff. Hashes e consistência temporal são
  verificados; autenticar a origem e o timestamp do recibo continua sendo uma
  exigência externa de admissão, não algo que um hash sozinho prove.
- Amostra conjunta previamente congelada de exatamente 900 eventos por membro,
  com mesmos IDs e kickoffs. Duplicatas, perdas silenciosas, resultados incompletos,
  dados adulterados e mistura com registros legados são rejeitados.
- Métricas RPS, log loss, Brier 1X2 e Brier OU2.5, com ordem de classes e escalas
  explícitas. Ganho positivo significa perda do controle menos perda do tratamento.
- Bootstrap móvel não circular, blocos de 21 jogos, 10.000 replicações, PCG64/seed 42,
  IC percentil, p-value unilateral sobre médias reamostradas centradas na hipótese nula.
  Empates contam na cauda; correção (1 + contagem)/(10000 + 1). Série constante é
  inconclusiva, com p=1, e não pode aprovar um modelo.
- Holm a 5% sobre a família completa. Exige-se também limite inferior positivo
  no RPS e não negativo em cada guardrail. Intervalo incerto não vira “sem piora”.
- As funções não abrem bancos nem ledgers, não treinam modelos e não ativam tarefas.
  Recebem entradas explícitas. As saídas mantêm autorização científica e capital falsos.

Essas definições são **escolhas novas declaradas**, não conteúdo atribuído ao
pré-registro de agosto. Os contratos antigos e seus bloqueios foram preservados.
A versão nova está disponível como biblioteca e especificação, ainda sem ativação
de coleta, sem nova inscrição canônica e sem avaliação de coorte real.
Para uma futura ativação, a configuração exata, a identidade do código executado,
o registro imutável, os ledgers novos e a integração ao coletor devem ser congelados
antes das previsões. Esta entrega não afirma que essa ativação ocorreu.

## Evidência histórica procurada

Foram examinados índices e entradas selecionadas de 16 ZIPs de backup/entrega,
12 revisões de configuração no Git e os arquivos preservados relacionados.
Foram obtidos 27 candidatos de configuração (4 identidades distintas) e 8 cópias
de estados (2 estados distintos). Não houve erros de leitura nessa busca.
Os ZIPs foram consultados seletivamente, sem extração geral e sem ler resultados
das coortes protegidas ou abrir bancos. Configurações privadas não estão neste pacote.

| Lacuna | Resultado desta rodada |
| --- | --- |
| Quatro previsões H15 | Nenhuma combinação adicional de estado/configuração conseguiu reconstruí-las com a proveniência exigida. As tentativas e identidades estão nos recibos. |
| H14 OU2.5 | Ausência de grade/estado e de baseline histórica suficientes. Não é possível identificar OU2.5 apenas com 1X2: previsões certas de 1–0 e de 3–0 têm o mesmo 1X2 e OU opostos. O teste cobre esse contraexemplo. |
| EXP-001 | Os dois nomes de relatórios ausentes não apareceram nos arquivos examinados. Isso não prova inexistência fora do inventário. |
| integrated_xg_v2 / H11 | Não apareceu nova fonte que encerre as lacunas de identidade e ligação histórica já relatadas. |

O suplemento V3 preserva as duas reconstruções anteriores e amplia a rastreabilidade
da busca. Não substitui os originais e não altera sua elegibilidade científica.

## Validade estatística e fontes

O p-value escolhido é uma aproximação por bootstrap, não uma garantia exata de
erro tipo I para toda série temporal. Sua adequação depende das propriedades
da série, inclusive dependência e estacionariedade. Testes de software não
demonstram essas propriedades nos dados reais.
Referência de bootstrap de blocos: Künsch (1989), *The jackknife and the bootstrap
for general stationary observations*, conforme [publicações do autor](https://people.math.ethz.ch/~kuensch/papers/).
O ajuste Holm aceita dependência entre testes, mas requer p-values individuais
adequados; ver [documentação oficial de p.adjust](https://stat.ethz.ch/R-manual/R-devel/library/stats/html/p.adjust.html).
Essas referências fundamentam componentes gerais; não aprovam as escolhas
particulares desta nova especificação nem os dados deste projeto.

## Arquivos e reversão

- `PROTOCOLO_SUCESSOR_V2.json`: especificação completa.
- `BUSCA_HISTORICA_AMPLIADA.json`: arquivos e identidades consultados.
- `H15_SUPLEMENTO_RETROSPECTIVO_V3.json`: suplemento separado, sem resultados reais.
- `RECIBO_PROTOCOLO_V2.json`: hashes, instalação e limites da validação.
- `PROTOCOLO_V2_CODIGO_TESTES_E_EVIDENCIAS.zip`: código, testes e evidências desta rodada.

Código integrado ao checkout em `brasileirao_scripts/prospective_protocol_v2.py`
e à instalação `.venv/Lib/site-packages/brasileirao_scripts/prospective_protocol_v2.py`.
O patch acrescenta esse módulo e atualiza RECORD, sem atualizar dependências.
Backup do RECORD anterior e recibo em
`C:/BRASILEIRAO/work/audit-fixes-20260915/protocol-v2-installation`.
Reversão da instalação, com o aplicativo encerrado:

```powershell
& C:/BRASILEIRAO/brasileirao-predictor/.venv/Scripts/python.exe C:/BRASILEIRAO/work/audit-fixes-20260915/install_protocol_v2.py --rollback
```

A reversão exige hashes iguais aos instalados e mantém o código-fonte entregue.
Os patches da rodada anterior continuam preservados. Não houve publicação Git,
alteração de configuração pessoal ou avaliação dos experimentos protegidos.
