# Migrar para outro Windows: código no Git, dados no ZIP

O código, testes, contratos e documentação ficam no Git. O pacote
`brasileirao-predictor-dados.zip` guarda os dados locais, backups de dados,
configurações privadas, definições do Agendador e cópias consistentes dos bancos.
Ele deriva da captura anterior verificada; não é uma nova coleta de dados nem
uma imagem do Windows. Consulte as inclusões e exclusões no manifesto do pacote.

## Recuperar o código

O arquivo separado `brasileirao-predictor-codigo.bundle` transporta o histórico
Git da branch `main`, incluindo o commit da migração. É útil mesmo sem acesso
ao GitHub. Copie esse arquivo e os arquivos do pacote de dados para
`C:\Transferencia`. Com Git instalado, crie uma pasta de projeto nova:

```powershell
git clone --branch main 'C:\Transferencia\brasileirao-predictor-codigo.bundle' 'C:\projetos\brasileirao-predictor'
if ($LASTEXITCODE -ne 0) { throw 'Falha ao recuperar o Git.' }
git -C 'C:\projetos\brasileirao-predictor' remote set-url origin https://github.com/leonardosovienski/brasileirao-predictor.git
git -C 'C:\projetos\brasileirao-predictor' rev-parse HEAD
```

Compare o commit com `code.commit` no manifesto dos dados. O bundle é um
backup Git local; sua criação não significa que o commit foi enviado ao GitHub.
Se o commit já estiver publicado no repositório remoto, também é possível
clonar por lá e selecionar esse mesmo commit.

Uma consolidação posterior da `main` não altera a captura de dados já entregue.
O ZIP anterior referencia `d42a3e0`; esse commit permanece no histórico. Para
reproduzir exatamente aquela captura, selecione o commit do manifesto em
checkout destacado. Para adotar a `main` posterior, mantenha os registros
versionados de governança da versão escolhida: não os sobrescreva com versões
mais antigas do ZIP. Preserve as duas versões como histórico. O código
consolidado usa Core 3.2.0 / Ops 4.1.0, enquanto a instalação operacional da
captura anterior usava Core 3.1.0 / Ops 4.0.0; a migração não atualiza essa
instalação automaticamente.

Se houver tentativas H14/H15 após a captura, transporte a pasta oculta
`.prospective_evaluation_claims` junto do ledger correspondente. Essa pasta
conserva o bloqueio de avaliação única ao mudar a raiz do projeto. Copiar somente
o ledger ou renomeá-lo não é uma migração completa desse estado; relatórios e
travas de tentativas anteriores também precisam acompanhar os dados.

## Verificar e extrair os dados

Mantenha o ZIP e seu arquivo `.zip.sha256` juntos. O verificador está no código
recuperado, em `scripts/migration/verify_archive.py`. Com Python instalado:

```powershell
python 'C:\projetos\brasileirao-predictor\scripts\migration\verify_archive.py' 'C:\Transferencia\brasileirao-predictor-dados.zip' --extrair 'C:\Migracao-Dados' --recibo 'C:\Transferencia\verificacao-dados.json'
```

A pasta de extração precisa ser nova ou vazia; o recibo também precisa ser novo.
Somente prossiga após `PASS`. O verificador confere SHA-256, CRC e os nomes dos
arquivos. Se falhar, não use a extração parcial. Preserve a extração verificada
e faça os ajustes de execução em uma cópia de trabalho.

O layout conserva os caminhos do pacote original:

- `projetos/brasileirao-predictor/data` e `reports`: dados e relatórios do projeto.
- `projetos/brasileirao-predictor-sessoes`: dados e evidências dos backups de sessões.
- `externos/predictor-data`: dados anteriormente em `C:\predictor\data`, incluindo
  os dados compartilhados de Binance, preservados sem análise.
- `externos/localappdata-brasileirao-backups`: backups locais históricos.
- `externos/predictor-ops-default-state`: estado legado arquivado como referência.
- `tarefa`: dados e evidências locais selecionados; os fontes ficam fora do ZIP.
- `migracao/private` e `migracao/tasks`: variáveis privadas e definições do Agendador.
- `snapshots_sqlite`: as cinco cópias consistentes dos bancos.

Copie os dados para os locais correspondentes da instalação de trabalho.
Para os cinco bancos em `snapshot_restore_map`, use o arquivo indicado em
`snapshot_archive_path` no destino indicado por `source_archive_path`.
Não junte um snapshot com os arquivos WAL/SHM da cópia bruta antiga. Preserve os
originais extraídos como histórico. Não altere ledgers, coortes, planos congelados
ou resultados para acomodar a migração. A consistência é por banco, não uma
captura simultânea de todo o computador.

## Recriar o ambiente e preparar a mudança

Na origem foram observados Python 3.14.6, uv 0.12.1 e SDK .NET 10.0.302.
As dependências estão fixadas no repositório. Na pasta do projeto novo:

```powershell
Set-Location -LiteralPath 'C:\projetos\brasileirao-predictor'
uv sync --python 3.14.6 --all-extras --locked
if ($LASTEXITCODE -ne 0) { throw 'Falha ao recriar o ambiente.' }
```

Não copie `.venv` nem artefatos compilados da máquina antiga. Adapte os caminhos
das configurações privadas e revise as chaves localmente, sem expô-las em logs.
O arquivo privado exporta cinco variáveis selecionadas do projeto; não todo o
ambiente do Windows. A configuração e os dados privados nunca devem entrar no Git.

As 27 tarefas XML são definições exportadas: sete estavam prontas e vinte
desabilitadas. Não foram importadas ou ativadas. Antes de ativá-las no destino,
adapte usuário/caminhos e defina qual computador fica responsável por cada
rotina, evitando execução duplicada. Dados produzidos depois da captura precisam
ser sincronizados na mudança definitiva.

Consulte `HANDOFF.md` antes de operar. A validação Docker/Compose permanecia
pendente na origem por indisponibilidade do hipervisor; isso não diagnostica o
computador novo. Instalação de serviços e teste de execução no destino são etapas
posteriores à transferência. Os testes da origem não comprovam compatibilidade
do computador novo.

**O ZIP contém chaves de API e dados privados. Guarde-o em local privado.**
