# Encerramento — auditoria e correções do Brasileirão / CAIN

## Resultado em 15/09/2026

Auditoria documental E1–E6 entregue. As correções identificadas e implementáveis
com as evidências disponíveis foram integradas ao código e agora também aplicadas
às instalações operacionais. Não resta a pendência de instalar estes sete módulos.

- Brasileirão: três módulos na instalação `.venv` do projeto, incluindo os
  avaliadores H14/H15 e o componente puro de métricas.
- CAIN: quatro módulos de pesquisa em `C:/CAIN/.venv`, ambiente efetivamente
  selecionado pelo atalho `ABRIR_CAIN.cmd` por meio de `.cain.local.json`.
- Aplicação como patch local rastreável, sem publicar uma nova versão de pacote.
  Dependências, configuração, dados pessoais e agendamentos não foram alterados.
- Sete módulos com backup dos bytes anteriores; metadados RECORD atualizados.
  Os outros arquivos Python das instalações conferem com o estado preparado.

## Validação concluída

Primeiro foram testadas cópias das instalações com apenas esses módulos alterados:
108 testes Brasileirão e 48 CAIN passaram. Depois da aplicação, os mesmos conjuntos
passaram novamente carregando os pacotes instalados: **108 + 48, sem falhas**.
Os dados dos testes são sintéticos e os bancos ficam em QA.
Os testes não avaliam coortes protegidas nem abrem o banco pessoal.
Há dois avisos de depreciação de dependências do CAIN; não são falhas dos testes.

O primeiro ensaio de instalação encontrou uma restrição excessiva do harness ao
ler o pytest de QA. O caminho de ferramentas foi liberado sem liberar os dados
protegidos; o log da tentativa está preservado. As tentativas de geração real
anteriores também permanecem nos pacotes anteriores, inclusive a resposta
semanticamente incorreta e a falha de geração.

Os hashes das previsões originais H14/H15 e dos arquivos de configuração
selecionados foram conferidos novamente. A correção literal de tabelas mantém
IDs, horizontes, estados e ressalvas; não certifica toda geração livre do modelo.

## Lacunas que permanecem registradas

| Item | Estado final e requisito para avançar |
| --- | --- |
| Previsões antigas H15 | 2 de 6 previsões por braço reconstruídas retrospectivamente, em suplemento separado. As outras 4 precisam de estado/configuração histórica compatível. Originais mantidos. |
| Previsões antigas H14 | Probabilidades OU2.5 e baseline histórica insuficientes. Não há reconstrução única a partir de 1X2. |
| Avaliação protegida H14/H15 | Bloqueio preventivo instalado. Resolver documentação da baseline OU2.5, definição dos p-values e demais lacunas de protocolo antes de qualquer avaliação. A função Holm isolada não completa o protocolo. |
| Fontes documentais | Dois relatórios EXP-001 ausentes no inventário consultado; identidade integrated_xg_v2 e ligação histórica H11 dependem de fontes adicionais. |
| Qualidade preditiva e semântica geral | Esta entrega não constitui nova validação científica, econômica ou certificação de toda resposta do CAIN. |

Essas lacunas não foram encerradas com valores inventados, alteração de contratos
congelados ou leitura de resultados protegidos. São dependências de evidência,
não tarefas de implementação restantes que possam ser resolvidas honestamente
com o material disponível.

## Rastreabilidade e reversão

Recibo final: `RECIBO_ENCERRAMENTO.json`. Entrega anterior detalhada:
`PARECER_E_CORRECOES.md`, `CONTINUACAO_REPAROS.md` e
`CORRECOES_INTEGRADAS.md`. Esses documentos são registros das respectivas etapas;
a indicação anterior de “instalação não atualizada” foi superada por este encerramento.

Backup e manifesto locais:
`C:/BRASILEIRAO/work/audit-fixes-20260915/runtime-closeout`.
Reversão, se necessária, com aplicativos encerrados:

```powershell
& C:/CAIN/.venv/Scripts/python.exe C:/BRASILEIRAO/work/audit-fixes-20260915/deploy_runtime_patch.py --rollback
```

A reversão confere hashes e recusa sobrescrever alterações posteriores. Uma
reinstalação futura dos pacotes pode substituir este patch: antes dela, levar
as correções dos checkouts para a versão que será instalada.

Não houve commit, push, merge nem publicação por esta execução. Não se afirma
ausência universal de bugs: os resultados estão limitados aos casos e bytes
verificados. O trabalho implementável desta auditoria está encerrado.
