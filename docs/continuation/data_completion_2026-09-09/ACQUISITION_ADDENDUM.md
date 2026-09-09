# Complemento de fontes e piloto de captura — DC-20260909

09/09/2026. Registrado antes de calcular desempenho em novos dados. Apenas
schema e cobertura não vazia do CSV 2025 foram examinados até aqui; nenhuma
odd numérica, label ou saldo novo foi examinado pelo pesquisador.

## Histórico público recuperado

O host oficial sem www respondeu ao CSV BRA.csv; o host www continua em 503.
Há 380 jogos de 2025, colunas individuais PSCH/PSCD/PSCA e
B365CH/B365CD/B365CA. As notas da própria fonte dizem que C significa closing.
Não são preços de T−60 min nem há clocks por preço.

Autoriza-se executar o replay CONDICIONAL explicitamente previsto no protocolo
PF-20260909, mantendo seu par, ano, remoção de margem, seleção, desempate,
stake, custo 2%, sensibilidades, banca 100, reserva diária de capital e bootstrap
semanal. Resultado sempre CONDITIONAL_NON_EXECUTABLE; não adaptar o scanner
preenchendo disponibilidade fictícia. Esse replay é um diagnóstico exploratório
com preços closing retrospectivos, nunca validação da decisão T−60.
Fixar seleções antes de abrir HG/AG/Res. Manter jogos faltantes e inconclusivos.
O protocolo PF e seu resultado anterior não serão editados. Não promover dados
sem clocks; comparação com abstenção apenas. A regra de liquidação hipotética
é a da fonte e não prova liquidação histórica pela casa.

## Conta, reserva e identidade regional

GET account atual retornou HTTP200: assinatura ativa, request_limit250,
request_count62, auto_renew=false, price=null, acesso a Pinnacle e Bet365.
O campo price=null isolado não é preço conhecido. A documentação oficial de
cadastro/preços identifica o plano gratuito de 250 chamadas mensais; histórico
e conta são não tarifados conforme contrato de quota. O contrato A1 mantém
minimum_monthly_reserve20. Nenhuma chamada desta pesquisa pode usar essa reserva.
Conta e cadência protegidas não serão modificadas. Registrar delta final.

A identidade regional será conferida em UMA chamada de catálogo bookmakers.
O fornecedor separa o slug genérico bet365 de bet365.bet.br. Não substituir
um pelo outro no replay congelado nem transferir sua rentabilidade entre regiões.
O domínio brasileiro também aparece nos termos oficiais da HS do Brasil.

## Piloto prospectivo independente (medição, sem aposta)

Após verificar novamente a conta, até CINCO chamadas de quota gratuita:
1 catálogo de bookmakers, 1 catálogo de fixtures Série A status Pre-Game dos
próximos14dias, até3 capturas de odds do MESMO primeiro fixture cronológico
cujo kickoff seja posterior à descoberta em pelo menos65min. Congelar fixture
antes de abrir odds. Sem reposição por preço ausente. Apenas casa
bet365.bet.br e referência pinnacle; não trocar casas por melhor odd/cobertura.
Se houver cloneOf, registrar e bloquear qualquer referência não independente.

Capturas pontuais separadas por pelo menos30s após resposta, contendo relógio
real de início e recebimento, payload bruto, HTTP Date e hash. Não denominar
createdAt/updatedAt como prova de disponibilidade no bookmaker. Mudanças de
estado/kickoff e limites desconhecidos devem aparecer na auditoria.
Não emitir picks: são capturas de homologação temporal em horário de sessão,
não a decisão congelada T−60. Stake0, nenhuma liquidação ou label de jogo.
Só abrir fixture previamente selecionado e payload adquirido por esta pesquisa;
nenhum join/import de coortes, arquivos de observadores ou banco existente.

Consultar conta antes/depois; confirmar active, plano compatível250, count
válido e saldo após a reserva e todas5 chamadas >=20. Registrar cooldowns e
qualquer uso externo concorrente. Falha de acesso/cota encerra as chamadas;
não ativar plano nem comprar recurso. Esta cota explícita é um máximo, não
meta de consumo. No máximo6 consultas de conta na rodada conforme protocolo.

Fontes: https://oddspapi.io/us/sign-up ;
https://oddspapi.io/us/docs/requests-and-quota ;
https://oddspapi.io/us/docs/get-bookmakers ;
https://football-data.co.uk/brazil.php ; https://football-data.co.uk/notes.txt ;
https://help.bet365.bet.br/s/pt-br/terms-and-conditions .
