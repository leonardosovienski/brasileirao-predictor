"""Add completed publication evidence before the final documentary commit."""
import hashlib
import json
import shutil
import subprocess
import tarfile
from datetime import UTC, datetime
from pathlib import Path

base=Path('C:/BRASILEIRAO')
repo=base/'brasileirao-predictor'
root=base/'work/publication-2026-09-10'
dest=repo/'docs/continuation/publication_2026-09-10'
first=json.loads((root/'remote-first.json').read_text())
package=json.loads((root/'package-final/receipt.json').read_text())
assert first['all_index_objects_equal'] and package['completed']
shutil.copyfile(root/'remote-first.json',dest/'evidence/remote-first.json')
shutil.copytree(root/'package-final',dest/'evidence/package-final',ignore=shutil.ignore_patterns('venv','dist','tmp*'))
for name in ('verify_remote.py','backup_final.py','close_publication.py'):
    shutil.copyfile(root/name,dest/'archive/publication-helpers'/name)
failure={'recorded_at':datetime.now(UTC).isoformat(),'initial_check':'FileNotFoundError on an existing 272-character Windows checkout path','git_file_missing':False,'normal_path_exists':False,'extended_path_exists':True,'proof_bytes':280926,'correction':'verify_remote.py uses the scoped extended Windows path for file reads; clone config core.longpaths=true; no source/evidence bytes moved or rewritten','after':'227 evidence files byte-verified; complete index and tree equality; both checkouts clean'}
(dest/'evidence/windows-path-verification.json').write_text(json.dumps(failure,indent=2)+'\n',encoding='utf-8')
sdist=next((root/'package-final/dist').glob('*.tar.gz'))
with tarfile.open(sdist) as tar:
    names=tar.getnames()
    prefix=names[0].split('/')[0]+'/'
    available={name.removeprefix(prefix) for name in names}
    tracked=subprocess.check_output(['git','-C',str(repo),'ls-files','-z']).decode().split('\0')
    mds=[name for name in tracked if name.endswith('.md')]
    missing=[name for name in mds if name not in available]
    record={'at':datetime.now(UTC).isoformat(),'package_head':package['head'],'tracked_markdown_at_payload':len(mds),'missing_markdown_in_sdist':missing,'sdist_members':len(names),'source_archive_scope':'final Git archive is separately checked against every versioned blob'}
    (dest/'evidence/sdist-document-check.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    assert not missing,missing
text=f'''# Publicação e recuperação conferidas

O main do GitHub recebeu a entrega no commit `{first['head']}`. Uma cópia independente clonada do remoto antigo `ac22c56` recebeu `pull --ff-only origin main`: HEAD e árvore iguais, índice completo idêntico, Git fsck aprovado e 227 arquivos de evidência verificados byte a byte. Os dois checkouts estavam limpos. [Recibo](evidence/remote-first.json).

O código da aplicação, testes, infraestrutura e configurações permanece igual ao commit `cc38b57` aprovado no [workflow Linux](https://github.com/leonardosovienski/brasileirao-predictor/actions/runs/34552247397). Esta conclusão adicional é documental. A atualização final desses recibos é publicada novamente e conferida por pull; o recibo terminal com HEAD e hashes fica em C:/BRASILEIRAO/AUDITORIA/PUBLICACAO_2026-09-10.json, fora do arquivo cujo próprio hash ele descreve.

Wheel e sdist foram gerados offline a partir do clone remoto da primeira entrega. Os **231 módulos** conferem byte a byte; instalação em um novo venv e os comandos leves de help/health passaram sem PYTHONPATH ou dependências reutilizadas. A cadeia completa de dependências foi validada separadamente no Linux. O sdist contém os {len(mds)} Markdown versionados daquele payload. [Recibo do pacote](evidence/package-final/receipt.json).

O bundle final fica em C:/BRASILEIRAO/BACKUPS/brasileirao-predictor-PUB-20260910.bundle. O ZIP final fica em C:/BRASILEIRAO/ENTREGAS/BRASILEIRAO_PUB_20260910_entrega.zip; contém a árvore Git final, o bundle e os pacotes. A validação terminal verifica o ZIP contra cada blob Git, CRC, hashes e restauração do bundle. O pacote Python identifica seu commit de origem; a árvore Git final inclui os recibos documentais acrescentados depois dele.

No Windows, clone em caminho curto ou use `git -c core.longpaths=true clone ...`. O verificador lê arquivos extensos pelo formato de caminho estendido. A primeira falha de leitura foi preservada e corrigida; o arquivo não estava faltando no Git. Isso evita tratar uma limitação de caminho como perda de evidência.

O histórico visível, mandatos, decisões, códigos, roteiros, resultados e próximas ações estão persistidos. A continuidade não precisa desta conversa, **desde que C:/BRASILEIRAO seja preservada**. Dados privados/operacionais e raws sem redistribuição estabelecida permanecem locais, com seus mapas e backups anteriores; GitHub público não substitui esse acervo. Não apagar a tarefa proprietária da automação DC junto com este chat.

Os sete requisitos externos/protegidos continuam no registro, a CI global não foi executada e lucro executável não foi demonstrado. A publicação recuperável não altera essas conclusões nem autoriza capital.
'''
(dest/'PUBLICADO.md').write_text(text,encoding='utf-8',newline='\n')
result=dest/'RESULTADO.md'
current=result.read_text(encoding='utf-8')
result.write_text(current+'\n[Publicação, pacote e recuperação conferidos](PUBLICADO.md).\n',encoding='utf-8',newline='\n')
readme=repo/'README.md'
current=readme.read_text(encoding='utf-8')
readme.write_text(current+'\n[Publicação e recuperação conferidas](docs/continuation/publication_2026-09-10/PUBLICADO.md).\n',encoding='utf-8',newline='\n')
print(json.dumps({'package_completed':True,'modules':package['module_count'],'sdist_markdown':len(mds),'missing_markdown':len(missing)}))
