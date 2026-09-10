"""Clarify tested hypotheses versus pre-existing claims and tidy current prose."""
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parent
REPO=Path('C:/BRASILEIRAO/brasileirao-predictor')
RI=REPO/'docs/continuation/integral_review_2026-09-09'
registry=json.loads((RI/'REGISTROS.json').read_text(encoding='utf-8'))
origins={
 'A01':'Inferência de prontidão a testar, contraposta aos guias ER/README que já indicavam ambiente mínimo, 09/09',
 'A02':'Inferência de suficiência a testar; DC distingue completude do universo e admissão, 09/09',
 'A11':'Premissa de capacidade a testar pelo nome do projeto; simulator.py já descrevia herança de Copa',
 'A13':'Hipótese de uso econômico do serving, confrontada com predict.py/display.py e não atribuída como promessa ao README',
 'A14':'Premissa de integração comercial a testar; contratos/runtime genéricos',
 'A15':'Inferência de abrangência a testar; CI da base ac22c56',
 'A17':'Hipótese de alcance da recuperação; recibos de consolidação/migração já limitam a garantia',
}
for row in registry['claims']:
    row['origin']=origins.get(row['id'],row['origin'])
registry['claims'].append({
 'id':'A20','claim':'Disponibilidade temporal das features, transformações e artefatos aprendidos está demonstrada em todas as rotas.',
 'origin':'Premissa de causalidade integral a testar, código de features/ratings/xG/cache e armazenamento bitemporal',
 'scope':'Rotas legadas/shared e pesquisa distinta; sem dados de coortes',
 'required':'Publicação/recebimento/revisões por campo, split e estado aprendido por decisão; conflitos resolvidos explicitamente.',
 'found':'Calendário é respeitado em rotas testadas, mas não substitui proveniência de publicação; fallback xG por gols é proxy, cache não comprova frescor. Ordenação determinística de versões por hash não comprova verdade de uma revisão conflitante.',
 'conclusion':'parcialmente confirmada','impact':'Não promover features/cache legados a dados PIT; P11/P18.'})
registry['problems'].append({
 'id':'P18','claims':'A18,A20','problem':'Disponibilidade histórica por feature e artefato aprendido não demonstrada integralmente.',
 'severity':'causalidade/modelagem / crítica','cause':'Data da partida, cache e desempate por hash não comprovam publicação, disponibilidade ou validade da revisão.',
 'dependencies':'Proveniência por campo e artefato; dependências compartilhadas cuja alteração pode afetar coleta protegida.',
 'action':'Mapear e manter rotas não demonstradas fora da inferência econômica; manter ensemble xG desligado; não consultar coortes para completar campos.',
 'closure':'Dataset/artefatos permitidos com clocks e política de conflito verificáveis, em estudo futuro separado e pré-especificado.',
 'status':'bloqueado'})
(RI/'REGISTROS.json').write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def table(rows,labels):
    return '\n'.join(['| '+' | '.join(labels)+' |','| '+' | '.join('---' for _ in labels)+' |']+
        ['| '+' | '.join(str(v).replace('|',' / ') for v in row.values())+' |' for row in rows])

intro='As entradas distinguem afirmações encontradas no código/documentação e hipóteses de suficiência formuladas para teste. Uma hipótese refutada não é atribuída como promessa a documentos que já a restringiam. As conclusões referem-se à versão e ao escopo indicados.\n\n'
(RI/'ALEGACOES.md').write_text('# Matriz central de alegações — RI-20260909\n\n'+intro+'Gerada de [REGISTROS.json](REGISTROS.json). [Problemas](PROBLEMAS.md), [mapas](MAPA_SISTEMA.md) e [testes](evidence/tests.json).\n\n'+table(registry['claims'],['ID','Alegação/premissa','Origem/data','Escopo/versão','Evidência exigida','Evidência encontrada','Conclusão','Impacto'])+'\n',encoding='utf-8')
(RI/'PROBLEMAS.md').write_text('# Registro central de problemas — RI-20260909\n\nGerado de [REGISTROS.json](REGISTROS.json), ligado à [matriz](ALEGACOES.md). Bloqueado exige informação externa ou autorização ausente, sem representar resolução por documentação.\n\n'+table(registry['problems'],['ID','Alegações','Problema','Tipo/gravidade','Evidência/causa','Dependências','Correção/ação','Teste de fechamento','Status'])+'\n',encoding='utf-8')

def polish(text):
    protected=[]
    pattern=r'`[^`]+`|\]\([^)]+\)|https?://[^\s)]+|[A-Z]:/[^\s|;,)]+|\b(?:H14|H15|H9|A1|A\d{2}|P\d{2}|SHA256|SHA512|1X2|HTTP200|HTTP503|v1|v2)\b|[a-fA-F0-9]{32,}|\b(?:participant[12]Id|market101)\b'
    def hold(match):
        index=len(protected)
        key='\x00'+chr(0xE000+index)+'\x00'
        protected.append((key,match.group(0)))
        return key
    text=re.sub(pattern,hold,text)
    text=re.sub(r'(?<=[A-Za-zÀ-ÿ])(?=\d)', ' ',text)
    text=re.sub(r'(?<=\d)(?=[A-Za-zÀ-ÿ])', ' ',text)
    text=re.sub(r'(?<!\d),(?=\S)', ', ',text)
    text=re.sub(r'(?<=[A-Za-zÀ-ÿ])\.(?=[A-Z\d])', '. ',text)
    text=re.sub(r'(?<=[A-Za-zÀ-ÿ]):(?=\S)', ': ',text)
    text=re.sub(r'\*\*(?=[A-Za-zÀ-ÿ\d])', lambda m:m.group(0),text)
    text=text.replace('.**', '.** ').replace('e.NETbuild','e .NET build').replace(' e4 ', ' e 4 ')
    text=text.replace('HTTP200','HTTP 200').replace('HTTP503','HTTP 503')
    for key,value in protected:
        text=text.replace(key,value)
    return text

for path in list(RI.glob('*.md'))+[REPO/'README.md',REPO/'docs/ESTADO_ATUAL.md',REPO/'docs/continuation/RETOMADA.md',Path('C:/BRASILEIRAO/LEIA_PRIMEIRO.md')]:
    if path.name not in {'PROTOCOLO.md','CHECKPOINT_INICIAL.md'}:
        path.write_text(polish(path.read_text(encoding='utf-8')),encoding='utf-8')

path=RI/'MAPA_SISTEMA.md'
text=path.read_text(encoding='utf-8').replace('P11/P17. |','P11/P17/P18. |')
text=text.replace('## Nota de cobertura adicional','## Nota de cobertura adicional')
text += '\nA camada bitemporal de pesquisa conserva versões e consultas as_known_at; o desempate determinístico por hash não autentica uma versão conflitante nem substitui published_at/ingested_at por campo. Essa limitação, o cache e a proveniência dos modelos estão em A20/P18. Nenhum conteúdo de coorte foi usado para sanar a lacuna.\n'
path.write_text(text,encoding='utf-8')

# Correct a crowded count sentence without changing its quantitative meaning.
path=RI/'RESULTADO.md'
text=path.read_text(encoding='utf-8').replace('Desses 131,129 provinham','Dessas 131 falhas, 129 provinham').replace('(126 socketpair,3 arquivos','(126 de socketpair e 3 de arquivos')
text=text.replace('e 348 abstenções.222','e 348 abstenções. 222').replace('0 principal','0 de principal').replace('0 aporte','0 aportes')
text=text.replace('P11/P17 têm limite','P11/P17/P18 têm limite')
path.write_text(text,encoding='utf-8')
Path('C:/BRASILEIRAO/INSTRUCOES/PROXIMO_PROMPT_APOS_REVISAO_2026-09-09.md').write_bytes((RI/'PROXIMO_PROMPT.md').read_bytes())
print(json.dumps({'claims':len(registry['claims']),'problems':len(registry['problems'])}))
