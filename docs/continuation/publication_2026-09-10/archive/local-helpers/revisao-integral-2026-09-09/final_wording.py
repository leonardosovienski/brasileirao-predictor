from pathlib import Path
import json,hashlib,re
repo=Path('C:/BRASILEIRAO/brasileirao-predictor');ri=repo/'docs/continuation/integral_review_2026-09-09'
for p in [ri/'RESULTADO.md',ri/'MAPA_DADOS.md',ri/'MAPA_SISTEMA.md',ri/'REPRODUZIR.md']:
 text=p.read_text(encoding='utf-8').replace('e. NETbuild','e build .NET').replace('duasURLs','duas URLs').replace('harness(126 socketpair, 3 arquivos','harness (126 de socketpair e 3 de arquivos').replace('perda−','perda −').replace('stakes−','stakes −').replace('banca−','banca −').replace('.**  ','.** ')
 p.write_text(text,encoding='utf-8',newline='\n')
reg=json.loads((ri/'REGISTROS.json').read_text())
for c in reg['claims']:
 if c['id']=='A17':
  c['found']='Recibo da migração é histórico, conteúdo protegido não reaberto. Bundle anterior da base verificado; recuperação do novo bundle em bare isolado registrada no recibo final. Serviços/dados privados não restaurados.'
(ri/'REGISTROS.json').write_text(json.dumps(reg,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
p=ri/'ALEGACOES.md'
t=p.read_text(encoding='utf-8').replace('Novo bundle Git terá verificação em repositório bare; serviços/dados privados não restaurados.','Bundle anterior da base verificado; recuperação do novo bundle em bare isolado registrada no recibo final. Serviços/dados privados não restaurados.')
p.write_text(t,encoding='utf-8',newline='\n')
files={p.relative_to(ri).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(ri.rglob('*')) if p.is_file() and p.name!='MANIFESTO.json'}
(ri/'MANIFESTO.json').write_text(json.dumps({'base_commit':'ac22c56c3318623e07a722f34d44dc6cd877ea37','files':files},ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
