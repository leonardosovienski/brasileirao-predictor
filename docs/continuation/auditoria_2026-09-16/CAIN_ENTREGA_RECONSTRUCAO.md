# Entrega ao CAIN — inventário, fontes e reconstruções

## Entrega operacional

O material foi efetivamente admitido na coleção principal `brasileirao` do usuário
`leo`: **82 registros novos, 85 no total**. Não ficou apenas nos relatórios de QA.
Foram adicionadas duas autorizações exatas para as duas fontes derivadas desta
auditoria. Permissões anteriores e demais coleções permaneceram preservadas.

Consulte `CAIN_O_QUE_TEM.md` e `CAIN_O_QUE_FALTA.md` para a separação solicitada.
As fontes complementares obtidas estão na pasta `FONTES_COMPLEMENTARES_EXP001`.

## Verificação

- Admissão e leitura no CAIN instalado, primeiro em QA isolado e depois na coleção principal.
- 82 consultas por registro confirmaram todos os campos literais, estados e ressalvas.
- Seis perguntas gerais passaram após a inclusão de um índice específico das lacunas.
- Nenhuma dessas respostas exigiu geração de fatos pelo modelo; usaram o caminho literal validado.
- Admissão repetida testada em QA sem duplicar registros.
- Banco SQLite com `integrity_check=ok`.
- Todos os registros anteriores do banco foram preservados, comparados por hashes de linhas.
- Hashes das fontes de reconstrução/originais conferidos antes e depois.

Uma primeira versão do anexo falhou em quatro consultas: um cabeçalho duplicava
ID/id e três tabelas ultrapassavam o limite aceito por linha. Os cabeçalhos foram
qualificados e os campos foram divididos em blocos menores, mantendo todo o conteúdo.
O anexo corrigido passou 26/26 consultas antes da admissão principal. A tentativa
reprovada foi preservada em QA e não foi admitida na coleção principal.

## Limite real

O conteúdo disponível e as lacunas estão preparados para consulta rastreável no
CAIN. Isso não significa que os arquivos históricos ausentes apareceram: continuam
2/6 braços H15 reconstruídos, nenhuma reconstrução H14 e dois relatórios originais
ausentes. Os três documentos obtidos são complementares, não substitutos.
Não se afirma perfeição universal do CAIN, de toda pergunta livre ou dos modelos.

## Preservação e rastreabilidade

Recibos: `CAIN_RECIBO_ADMISSAO.json` e `CAIN_PERGUNTAS_VERIFICADAS.json`.
Backups consistentes do banco e da política anteriores às duas admissões, mantidos
somente localmente por conterem material privado:

- `C:/CAIN/work/brasileirao-reconstruction-20260915/primary-backup`
- `C:/CAIN/work/brasileirao-reconstruction-20260915/primary-backup-annex`

Esses bancos privados não integram o ZIP de entrega. Não restaurar um banco antigo
sobre novas conversas/admissões. Se for necessário ocultar esse material, remover
somente as duas autorizações do stream `reconstruction-audit` para as fontes
`local-audit/brasileirao-reconstruction-20260915.md` e
`local-audit/brasileirao-reconstruction-details-20260915.md`, preservando os arquivos
de evidência e as demais autorizações. Nenhum código ou dado foi publicado no Git.
