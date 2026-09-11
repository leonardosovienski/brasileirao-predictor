"""Record honest review depth and unchanged protected dependencies without running them."""
import ast
import hashlib
import json
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parent
repo = Path('C:/BRASILEIRAO/brasileirao-predictor')
docs = repo / 'docs/continuation/completion_2026-09-10'
evidence = docs/'evidence'
evidence.mkdir(exist_ok=True)
initial = json.loads((root/'inventory.json').read_text(encoding='utf-8'))
protected = {r['path'] for r in initial if r['review'].startswith('dependency_contract')}
protected.add('brasileirao_predictor/serving_evaluator.py')
reviewed_modules = '''predict display settings prediction_protocol identity cron_update_models feature_builder ratings ingest db market_pricer simulator settle model xg_model dynamic_strength prediction_log event_models dixon_coles bet_log net obs temporal_policy backup_restore ecosystem_plugin'''.split()
reviewed = {'brasileirao_predictor/'+name+'.py' for name in reviewed_modules}
reviewed.update('brasileirao_predictor/data/'+name+'.py' for name in '''bookmaker_odds bitemporal_store api_football_provider the_odds_api_provider sportmonks_provider market_anchor lineup_archive historical_expansion collection_only_archive bookmaker_stability pit_backfill xg_quality missingness_audit odds_api_snapshot'''.split())
reviewed.update(['brasileirao_predictor/research/residual_features.py','brasileirao_predictor/research/price_strength/artifacts.py','brasileirao_predictor/research/price_strength/__main__.py','brasileirao_scripts/prever.py','brasileirao_scripts/check_prediction_readiness.py','brasileirao_scripts/init_compose_data.py','tools/runtime_lab/run.py','tools/runtime_lab/kernel_synthetic.py','tools/runtime_lab/lab_guard.py'])
reviewed.update('dotnet/LineupWorker/'+p+'.cs' for p in '''Program Worker OperationalSettings Models/LineupEvent Models/KernelContracts Models/LatencyRecord Services/MarketStateEngine Services/MarketOddsCache Services/LineupStreamConsumer Services/VorpStateService'''.split())
reviewed.update('dotnet/LineupWorker.Tests/'+p+'.cs' for p in ['CompletionContractTests','KellyMathTests','RedisProtocolTests','ModelBranchTests'])
changed = subprocess.check_output(['git','diff','--name-only'],cwd=repo,text=True).splitlines()
new = subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=repo,text=True).splitlines()
reviewed.update(p for p in new if p.startswith('tests/') and p.endswith('.py'))
reviewed.update('tests/'+p+'.py' for p in '''test_bitemporal_store test_market_anchor test_sportmonks_provider test_api_football_provider test_prediction_protocol test_completion_math_consumer'''.split())
rows=[]
for base in ('brasileirao_predictor','brasileirao_scripts','tests','dotnet','scripts','tools'):
    for path in sorted((repo/base).rglob('*')):
        if not path.is_file() or path.suffix not in {'.py','.cs','.ps1','.json','.csproj','.yml','.yaml'} or any(x in path.parts for x in ('obj','bin','__pycache__')):
            continue
        rel=path.relative_to(repo).as_posix()
        record=dict(path=rel,bytes=path.stat().st_size)
        if rel in protected:
            record['review']='protected_contract_only_no_execution'
        else:
            raw=path.read_bytes()
            record.update(sha256=hashlib.sha256(raw).hexdigest(),lines=len(raw.splitlines()),
                          review='semantic_read_with_recorded_findings' if rel in reviewed else 'inventory_static_or_targeted_review_only')
        rows.append(record)
boundary = {'base': '456b9025cfa3a596e754088ec3001fbeb5fcc7de',
            'protected_files_modified':sorted(set(changed)&protected),'function_checks':[],
            'no_operational_results_or_cohort_metrics_read':True,
            'scope_note':'Files with mixed protected functionality preserved. This inventory does not assert a full semantic reading of every file.'}
assert not boundary['protected_files_modified']
for rel, names in [('brasileirao_predictor/predict.py',['_canon','_market_probs']),('brasileirao_predictor/data/market_anchor.py',['persist_market_observations'])]:
    old=ast.parse(subprocess.check_output(['git','show','HEAD:'+rel],cwd=repo).decode('utf-8'))
    current=ast.parse((repo/rel).read_text(encoding='utf-8'))
    for name in names:
        def content(tree):
            return ast.dump(next(n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name),include_attributes=False)
        before,after=content(old),content(current)
        assert before==after,(rel,name)
        boundary['function_checks'].append(dict(path=rel,function=name,unchanged=True,ast_sha256=hashlib.sha256(after.encode()).hexdigest()))
frozen = ['brasileirao_predictor/db.py','brasileirao_predictor/ratings.py','brasileirao_predictor/model.py','brasileirao_predictor/xg_model.py','brasileirao_predictor/cron_update_models.py','brasileirao_predictor/identity.py','brasileirao_predictor/data/the_odds_api_provider.py','brasileirao_predictor/data/bookmaker_stability.py','brasileirao_predictor/research/price_strength/economic_search.py']
assert not set(frozen)&set(changed)
boundary['shared_or_frozen_files_unchanged']=frozen
counts={kind:sum(r['review']==kind for r in rows) for kind in sorted({r['review'] for r in rows})}
for name,value in [('source-inventory.json',rows),('boundary-check.json',boundary),('coverage-summary.json',dict(files=len(rows),by_depth=counts))]:
    (evidence/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(files=len(rows),depth=counts,boundary_ok=True)))
