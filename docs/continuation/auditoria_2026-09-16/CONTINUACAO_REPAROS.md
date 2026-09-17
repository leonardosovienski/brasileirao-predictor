# Continuação: reparos e preservação das previsões

## Resultado

O pedido posterior foi preservar as previsões antigas e tentar repará-las.
Foram feitas cópias byte a byte dos ledgers arquivados H14/H15, com verificação
SHA-256. Os arquivos originais, estados canônicos e avaliações únicas não foram
alterados. Nenhum placar/desfecho foi consultado, nenhum modelo foi treinado e
nenhuma avaliação de desempenho foi executada.

Houve inferência retrospectiva limitada com estados congelados existentes,
apenas para reconstruir probabilidades ausentes, conforme essa nova autorização.
Isso difere dos testes sintéticos da entrega anterior.

## Previsões antigas

### H15

No recorte arquivado há 3 registros, cada um com 2 braços: 6 previsões por braço.
A primeira tentativa encontrou 2 reconstruções, 2 divergências de fingerprint de
configuração e 2 estados históricos não localizados. A ampliação dirigida para
4 configurações e 4 arquivos de estado preservados manteve **2/6 reconstruções**.
As quatro restantes continuam visíveis como `UNRECOVERED`, com valor nulo.

Para as duas reconstruções foram exigidos: mesma data de refit; estado anterior
à previsão e previsão anterior ao kickoff; Elo armazenado compatível; fingerprint
do desenho/configuração coincidente; reprodução exata das probabilidades 1X2
na precisão de 6 casas originalmente gravada. Nenhum resultado do jogo participou.

**Limite decisivo:** a coincidência não demonstra a identidade completa do código
original nem a existência da probabilidade OU2.5 registrada antes do jogo.
O suplemento é `RETROSPECTIVE_RECONSTRUCTION_NOT_ORIGINAL_FORECAST`, com
`original_code_identity_proven=false` e `prospective_eligibility_restored=false`.
Não foi anexado ao ledger protegido nem habilitado para avaliação confirmatória.

### H14

O schema arquivado confirma apenas probabilidades 1X2 e n_prior na climatologia;
não contém grade de placares, probabilidades OU2.5 nem histórico da baseline OU.
Não existe transformação única de probabilidades 1X2 em OU2.5: distribuições de
placares diferentes podem ter a mesma proporção vitória/empate/derrota e totais
de gols diferentes. Portanto nenhum valor foi imputado.

O manifesto local de recuperação registra por previsão/ braço o campo ausente,
hash, localizador e dependência mínima. Caminho:
`C:/BRASILEIRAO/work/audit-fixes-20260915/forecast-recovery/recovery-manifest.json`.
As cópias originais ficam na subpasta `originals`, sem envio a serviços externos.

## Código e testes

### Brasileirão

Além dos bloqueios H14/H15 da primeira candidata, foi implementado o módulo puro
`brasileirao_scripts/prospective_metrics.py`:

- Brier OU2.5 na convenção de soma de duas classes usada pelo produtor, intervalo
  0–2; recusa probabilidades inválidas e resultados fora do domínio.
- Holm step-down sobre a família completa; recusa membro ausente, p-value inválido
  e tentativa de reduzir o denominador da família.

Esses componentes não leem dados nem autorizam uma claim. Holm depende de
p-values válidos cuja forma de obtenção precisa estar especificada no protocolo;
não se fabricou um método a partir dos intervalos de bootstrap existentes.
Os avaliadores antigos continuam bloqueados quando incompatíveis com o contrato.

**84 testes aprovados** no conjunto dirigido do Brasileirão, com arquivos
sintéticos, incluindo os 69 anteriores e 15 novos. Ruff passou nos dois arquivos
novos. Isso não é validação científica das probabilidades reconstruídas.

### CAIN

Candidata separada em `C:/CAIN/work/brasileirao-audit-20260915`.
As instruções de análise agora exigem qualificar explicitamente o enunciado como
hipótese e preservar o significado técnico de features (variáveis de entrada),
sem convertê-lo em falta de recursos. Versão do prompt `addressable-review/15`;
workflow `research-workflow/19`, para não continuar silenciosamente jobs anteriores.

**2 testes de integração sintética aprovados**, cobrindo o contexto enviado ao
provider e abstenção sem fonte. Usaram usuário QA e banco novo separado. Dois
avisos de depreciação das dependências ficaram no log. Houve falhas iniciais de
ambiente/fixture; os quatro logs foram preservados.

Não se afirma que a falha semântica do modelo esteja resolvida: o endpoint
configurado `http://127.0.0.1:11434` recusou conexão. Nenhuma geração real ocorreu.
O checkout do CAIN também recebeu alterações concorrentes externas durante esta
execução; a candidata preserva a base copiada, mas não foi instalada sobre elas.

## Recuperação documental

As consultas ao inventário `C:/BRASILEIRAO/AUDITORIA/inventario_dados_preservados.json`
não localizaram os dois relatórios EXP-001 nem um artefato com identidade
`integrated_xg_v2`. O histórico Git disponível para os dois caminhos exatos de
relatórios também não retornou commits. Isso não comprova ausência global.
Essas pendências precisam de outra fonte/backup identificável; não foram
substituídas por relatórios novos com nomes antigos.

## O que o CAIN pode fazer com o material

Pode localizar candidatos, relacionar hashes, datas, IDs e estados e explicar as
lacunas. O suplemento e o manifesto fornecem uma trilha verificável para isso.
Não deve completar probabilidades por linguagem natural, usar placares para
melhorar previsões anteriores nem apresentar reconstrução como previsão original.
Nenhum desses documentos foi admitido automaticamente no corpus principal.

## Pendências efetivas

1. Quatro previsões por braço H15: estado/configuração histórica compatível não
   encontrado na busca delimitada. H14: baseline/grade OU original não localizada.
2. Proveniência integral do código original e disponibilidade temporal: ainda não
   demonstradas; reconstruções não restauram a validade prospectiva.
3. Definição de baseline OU, semântica do bloco de data e p-values familiares:
   decisão de protocolo ainda necessária, sem alterar experimento congelado.
4. CAIN: execução semântica real quando o backend local estiver disponível,
   usando candidata e corpus QA identificados; testes de prompt não substituem isso.
5. EXP-001/integrated_xg_v2/linhagem H11: dependências documentais continuam abertas.
6. Implantação: nenhuma alteração na instalação principal. A candidata de CAIN
   precisa ser conciliada com as mudanças concorrentes; os bloqueios do produtor
   precisam permanecer até resolver os requisitos científicos.

Não foi criado protocolo futuro, pois a resposta do usuário priorizou recuperar
as previsões antigas. Não houve publicação, merge, operação financeira ou
consumo de avaliação única.
