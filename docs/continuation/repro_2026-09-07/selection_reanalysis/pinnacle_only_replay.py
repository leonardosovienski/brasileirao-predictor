"""Explicit adaptive exploratory branch; does not replace common-panel result."""
import hashlib
import json
from pathlib import Path

import numpy as np

from price_discovery_replay import dt, fit_ridge, normalized

ROOT = Path(__file__).resolve().parent


def evaluate(source):
    cutoff = dt(source["primary_B"]["first_selected_test_decision_at"])
    eligible = set(source["coverage_panels"]["momentum"]["eligible_ids"])
    all_rows = source["snapshots"]
    training = [r for r in all_rows if r["split"] == "train" and r["fixture_id"] in eligible and not r["purged_training_boundary"]]
    testing = [r for r in all_rows if r["split"] == "test" and r["fixture_id"] in eligible]
    assert all(dt(r["snapshots"]["pinnacle"]["T10M"]["cutoff_at"]) < cutoff for r in training)
    if len(training)<10 or len(testing)<5:
        return {"status":"INSUFFICIENT_DATA","train_n":len(training),"test_n":len(testing)}
    beta = float(fit_ridge(training,cross=False)[0])
    losses = {"persistence":[],"momentum_unit":[],"ridge_momentum":[]}
    per_event=[]
    for row in testing:
        p6=np.asarray(row["snapshots"]["pinnacle"]["T6H"]["q"])
        p1=np.asarray(row["snapshots"]["pinnacle"]["T1H"]["q"])
        target=np.asarray(row["snapshots"]["pinnacle"]["T10M"]["q"])
        predictions={"persistence":normalized(p1),"momentum_unit":normalized(p1+p1-p6),"ridge_momentum":normalized(p1+beta*(p1-p6))}
        record={"fixture_id":row["fixture_id"],"losses":{}}
        for name,pred in predictions.items():
            loss=float(np.mean((pred-target)**2))
            losses[name].append(loss)
            record["losses"][name]=loss
        per_event.append(record)
    base=float(np.mean(losses["persistence"]))
    metrics={name:{"mse":float(np.mean(values)),"delta_vs_persistence":float(np.mean(np.array(values)-losses["persistence"])),"relative_mse_reduction":1-float(np.mean(values))/base if base>0 else None,"events_better":int(np.sum(np.array(values)<losses["persistence"]))} for name,values in losses.items()}
    return {"status":"EXPLORATORY_POST_COVERAGE_BRANCH","train_n":len(training),"test_n":len(testing),"ridge_beta":beta,"metrics":metrics,"per_test_event":per_event,"training_ids":[r["fixture_id"] for r in training],"test_ids":[r["fixture_id"] for r in testing],"confirmation":False,"profit_measured":False}


if __name__ == "__main__":
    output=ROOT/"pinnacle_only_results.json"
    if output.exists(): raise SystemExit("Existing result: refuse overwrite")
    plan=(ROOT/"price_history"/"pinnacle_only_plan.json").read_bytes()
    source=(ROOT/"price_discovery_report.json").read_bytes()
    source_document=json.loads(source)
    dependency_hash=hashlib.sha256((ROOT/"price_discovery_replay.py").read_bytes()).hexdigest()
    assert dependency_hash==source_document["provenance"]["script_sha256"]
    assert source_document["primary_B"]["coefficients"] is None
    result=evaluate(source_document)
    result["provenance"]={"plan_sha256":hashlib.sha256(plan).hexdigest(),"source_sha256":hashlib.sha256(source).hexdigest(),"script_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),"dependency_price_discovery_replay_sha256":dependency_hash}
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k not in ('per_test_event','training_ids','test_ids')},ensure_ascii=False))
