# Reprodução e conferência da publicação

O ensaio Linux completo está em [Actions](https://github.com/leonardosovienski/brasileirao-predictor/actions/runs/34552247397). O código executado é `cc38b57bd3ba6f8c2cbdce6353eaf085d4ece14f`. `tools/publication_validation/README.md`, scope.json e workflow descrevem os comandos exatos; logs e artefatos têm hashes verificados. O ambiente do runner foi descartável e sua instalação veio dos lockfiles.

No Windows, use um diretório novo sob C:/BRASILEIRAO. `git clone https://github.com/leonardosovienski/brasileirao-predictor.git DIRETORIO_NOVO` e `git -C DIRETORIO_NOVO pull --ff-only origin main` recuperam o código. Não substituir o checkout ou dados existentes. Verifique `git status --short`, HEAD, origin/main e o recibo em C:/BRASILEIRAO/AUDITORIA/PUBLICACAO_2026-09-10.json. A cópia de conferência desta entrega fica em C:/BRASILEIRAO/work/publication-2026-09-10/remote-clone.

Instale a cadeia fixada com `uv sync --locked --all-extras`; não execute coletores ou pytest global. Para a lista sintética revisada, use o Python do ambiente com `-I -B tools/publication_validation/run.py C:/BRASILEIRAO/work/NOVA_SAIDA`. Ela recusa saída dentro do checkout ou que já exista. Runtimes, provedores e instalação da cadeia requerem dependências externas; não vêm embutidos no Git.

O pacote e bundle finais possuem recibo separado na pasta AUDITORIA. A restauração de Git/arquivos não migra bancos, não restaura Redis operacional e não prova disponibilidade de dados nunca recebidos. Recibos CI referem-se ao commit testado; alterações posteriores somente documentais têm relação de árvore verificada na publicação.
