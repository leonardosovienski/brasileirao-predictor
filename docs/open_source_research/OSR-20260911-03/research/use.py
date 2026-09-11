"""Repeatable offline example. Every invocation creates a fresh evidence directory."""
import datetime,json
from pathlib import Path
import numpy,scipy
from workflow import run,compare
from goals_demo import diagnose
ROOT=Path(__file__).resolve().parent.parent
if __name__=='__main__':
    tag='use-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    destination=ROOT/'evidence'/tag
    run(ROOT/'examples/before.json',destination/'before')
    run(ROOT/'examples/after.json',destination/'after')
    value=compare(destination/'before',destination/'after')
    (destination/'comparison.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
    goals=diagnose(json.loads((ROOT/'examples/goals.json').read_text())['parameters'])
    (destination/'goals.json').write_text(json.dumps(goals,indent=2,allow_nan=False),encoding='utf-8')
    lines=['# Demonstração offline — dados sintéticos','','| Partida | Antes | Depois | Mudança de probabilidade 1/X/2 |','|---|---|---|---|']
    for c in value['changes']:
        delta=', '.join(f'{v:+.6f}' for v in c['probability_delta']) if c['probability_delta'] is not None else 'Não comparável: mudou admissão'
        lines.append(f"| {c['fixture_id']} | {c['before_status']} / {c['before_reason']} | {c['after_status']} / {c['after_reason']} | {delta} |")
    lines.extend(['','Clocks, identidade e preços são fixtures de desenvolvimento. A mudança de cobertura não mede ganho preditivo.','',f"Entrada mudou: {value['input_changed']}; código mudou entre as execuções: {value['code_changed']}.",'','Arquivos: before/manifest.json, after/manifest.json, comparison.json, goals.json.'])
    (destination/'COMPARACAO.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'directory':str(destination),'report':str(destination/'COMPARACAO.md'),'numpy':numpy.__version__,'scipy':scipy.__version__,'status':'COMPLETE_RESEARCH_ONLY'}))
