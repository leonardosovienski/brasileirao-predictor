import json
import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

ROOT=Path('C:/Users/Superleo13/projetos/brasileirao-predictor')
rows=[]
for job in ['fixture-refresh','model-update','h14-persist','h15-persist','a1-discover','a1-collect','a1-metrics']:
    path=ROOT/'data/runtime/passive'/job/'heartbeat.json'
    if not path.exists():
        rows.append({'job':job,'status':'NOT_RUN_BY_WRAPPER'})
        continue
    state=json.loads(path.read_text(encoding='utf-8'))
    row={k:state.get(k) for k in ['job','status','started_at','finished_at','exit_code','error','last_success_at']}
    log=Path(state['log_path'])
    if log.exists():
        content=log.read_text(encoding='utf-8',errors='replace')
        row['log_bytes']=log.stat().st_size
        if job=='fixture-refresh':
            row['input_refresh_steps_completed']=re.findall(r'H9_INPUT_REFRESH_OK step=(\w+)',content)
            row['seasons_processing_completed']=re.findall(r'Série A (20\d{2}): \d+ jogos processados',content)
            progress=re.findall(r'\[(\d+)/(\d+)\]',content)
            row['source_loop_progress']=list(map(int,progress[-1])) if progress else None
            row['source_error_lines']=sum(' ERROR ' in line or ' WARNING ' in line for line in content.splitlines())
            row['current_season_processing_completed']=bool(re.search(r'Série A 2026: \d+ jogos processados',content))
            row['source_failure_markers']=sum(' falhou' in line for line in content.splitlines())
    rows.append(row)
with sqlite3.connect((ROOT/'data/matches.db').as_uri()+'?mode=ro',uri=True) as conn:
    cache=conn.execute('SELECT computed_at FROM model_parameters WHERE id=1').fetchone()
    # Only upcoming fixture metadata; never reads outcomes or joins a cohort.
    horizon=conn.execute('SELECT MAX(kickoff_at) FROM sofascore_matches WHERE home_score IS NULL').fetchone()
report={'checked_at':datetime.now(UTC).isoformat(),'jobs':rows,'model_cache_computed_at':cache[0] if cache else None,
        'latest_upcoming_kickoff':horizon[0] if horizon else None,'scientific_metrics_computed':False}
(Path(__file__).resolve().parent/'operational_health_result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
