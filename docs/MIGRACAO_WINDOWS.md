# Migração e preservação — situação em C:/BRASILEIRAO

## O que já foi concluído

O código foi recuperado do bundle e atualizado por avanço direto para a main
remota f003045; a pesquisa posterior foi registrada localmente em f33f92b.
O histórico Git e os commits desta organização ficam no checkout
`C:/BRASILEIRAO/brasileirao-predictor`. Consulte [ESTADO_ATUAL](ESTADO_ATUAL.md)
e o recibo final em `C:/BRASILEIRAO/AUDITORIA` para o SHA consolidado.

O pacote em `C:/BRASILEIRAO/MIGRACAO_DADOS/MIGRACAO_DADOS` foi preservado.
A extração integral foi verificada em `C:/BRASILEIRAO/DADOS_PRESERVADOS`:
12.423 entradas do manifesto mais o manifesto, conferidas por CRC e SHA-256.
Recibo: `C:/BRASILEIRAO/AUDITORIA/verificacao_migracao_2026-09-09.json`.

Código, dados recebidos, entregas e documentação estão na raiz solicitada.
A operação completa ainda não foi instalada/ativada; o ambiente Python existente
é o de pesquisa isolada. Não houve importação de tarefas, abertura de bancos,
renovação de atestados ou alteração de coortes.

## Repetir a conferência do pacote sem extrair novamente

```powershell
$migrationPython = 'C:/BRASILEIRAO/work/price-feasibility-2026-09-09/venv/Scripts/python.exe'
& $migrationPython -I 'C:/BRASILEIRAO/brasileirao-predictor/scripts/migration/verify_archive.py' 'C:/BRASILEIRAO/MIGRACAO_DADOS/MIGRACAO_DADOS/brasileirao-predictor-dados.zip' --recibo 'C:/BRASILEIRAO/AUDITORIA/verificacao_repetida.json'
if ($LASTEXITCODE -ne 0) { throw 'Falha na verificação' }
```

O recibo deve ser novo. Essa ferramenta lê bytes e metadados; não importa a
aplicação nem consulta bancos. Não reextrair por cima de `DADOS_PRESERVADOS`.
Para uma extração adicional, usar uma pasta nova e manter a original intacta.

Alguns arquivos históricos têm caminhos com mais de 260 caracteres. A extração
e a conferência no disco usam a forma estendida de caminhos do Windows. Um erro
da API comum nesses caminhos não comprova ausência do arquivo. Não renomear
evidências ou modificar o registro do Windows para contornar essa limitação.

## Preparar outra instalação no futuro

O [mapa de dados](DATA_MAP.md) e `snapshot_restore_map` indicam os destinos
corretos. A captura dos dados está vinculada a d42a3e0 e não deve sobrescrever
governança versionada mais nova. Preservar as duas versões, inclusive claims
e bloqueios de avaliação única eventualmente recebidos depois da captura.

O lock do código atual fixa Core 3.2.0 / Ops 4.1.0 e requer Python >=3.13,<3.15.
Uma instalação completa deve usar esse lock em ambiente novo; copiar um venv
não torna seus caminhos portáveis. Não iniciar coleta/serving como teste de
instalação. Dependências externas e serviços precisam de validação própria.

As 27 definições de tarefas foram apenas preservadas. A ativação depende de
definir qual máquina será responsável por cada rotina e de conservar os contratos
protegidos, evitando duplicação. Agendas não serão adaptadas automaticamente.

Arquivos gerados no computador antigo depois de 08/09 não estão comprovados
por esta captura. O pacote contém dados privados e chaves; mantê-lo privado.
As [instruções originais de migração](history/antes_consolidacao_2026-09-09/docs/MIGRACAO_WINDOWS.md)
continuam arquivadas com seus caminhos e contexto históricos.
