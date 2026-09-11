# Publicação e recuperação conferidas

O main do GitHub recebeu a entrega no commit `23245635553d8be91244c48534120f0fb4eacfc1`. Uma cópia independente clonada do remoto antigo `ac22c56` recebeu `pull --ff-only origin main`: HEAD e árvore iguais, índice completo idêntico, Git fsck aprovado e 227 arquivos de evidência verificados byte a byte. Os dois checkouts estavam limpos. [Recibo](evidence/remote-first.json).

O código da aplicação, testes, infraestrutura e configurações permanece igual ao commit `cc38b57` aprovado no [workflow Linux](https://github.com/leonardosovienski/brasileirao-predictor/actions/runs/34552247397). Esta conclusão adicional é documental. A atualização final desses recibos é publicada novamente e conferida por pull; o recibo terminal com HEAD e hashes fica em C:/BRASILEIRAO/AUDITORIA/PUBLICACAO_2026-09-10.json, fora do arquivo cujo próprio hash ele descreve.

Wheel e sdist foram gerados offline a partir do clone remoto da primeira entrega. Os **231 módulos** conferem byte a byte; instalação em um novo venv e os comandos leves de help/health passaram sem PYTHONPATH ou dependências reutilizadas. A cadeia completa de dependências foi validada separadamente no Linux. O sdist contém os 248 Markdown versionados daquele payload. [Recibo do pacote](evidence/package-final/receipt.json).

O bundle final fica em C:/BRASILEIRAO/BACKUPS/brasileirao-predictor-PUB-20260910.bundle. O ZIP final fica em C:/BRASILEIRAO/ENTREGAS/BRASILEIRAO_PUB_20260910_entrega.zip; contém a árvore Git final, o bundle e os pacotes. A validação terminal verifica o ZIP contra cada blob Git, CRC, hashes e restauração do bundle. O pacote Python identifica seu commit de origem; a árvore Git final inclui os recibos documentais acrescentados depois dele.

No Windows, clone em caminho curto ou use `git -c core.longpaths=true clone ...`. O verificador lê arquivos extensos pelo formato de caminho estendido. A primeira falha de leitura foi preservada e corrigida; o arquivo não estava faltando no Git. Isso evita tratar uma limitação de caminho como perda de evidência.

O histórico visível, mandatos, decisões, códigos, roteiros, resultados e próximas ações estão persistidos. A continuidade não precisa desta conversa, **desde que C:/BRASILEIRAO seja preservada**. Dados privados/operacionais e raws sem redistribuição estabelecida permanecem locais, com seus mapas e backups anteriores; GitHub público não substitui esse acervo. Não apagar a tarefa proprietária da automação DC junto com este chat.

Os sete requisitos externos/protegidos continuam no registro, a CI global não foi executada e lucro executável não foi demonstrado. A publicação recuperável não altera essas conclusões nem autoriza capital.

A conferência completa do ZIP revelou conversão de LF para CRLF no Windows. O exportador agora usa core.autocrlf=false e core.eol=lf somente na criação desse arquivo, preservando os atributos -text das evidências. O teste corrigido comparou os 2.362 blobs da versão fae6e0e sem divergências; as tentativas anteriores permanecem em work/publication-2026-09-10/backup-attempt-01. A regra é aplicada novamente ao ZIP definitivo.

A organização da pasta foi conferida pelo sistema de arquivos. A abertura do Explorador foi recusada pela revisão automática de permissões (blocked by policy); não foi declarada inspeção visual da janela.
