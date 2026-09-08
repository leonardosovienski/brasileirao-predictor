from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from pinnacle_only_replay import evaluate


def source_fixture():
    rows=[]
    for i in range(30):
        target_time=datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(days=i,hours=12)
        rows.append({"fixture_id":str(i),"split":"train" if i<20 else "test","purged_training_boundary":False,"snapshots":{"pinnacle":{
            "T6H":{"q":[0.40,0.30,0.30]},
            "T1H":{"q":[0.41,0.295,0.295]},
            "T10M":{"q":[0.415,0.2925,0.2925],"cutoff_at":target_time.isoformat()},
        }}})
    return {"primary_B":{"first_selected_test_decision_at":"2026-01-21T11:10:00+00:00"},"coverage_panels":{"momentum":{"eligible_ids":[str(i) for i in range(30)]}},"snapshots":rows}


def test_test_targets_cannot_change_training_coefficient():
    original=source_fixture()
    changed=deepcopy(original)
    for row in changed["snapshots"][20:]: row["snapshots"]["pinnacle"]["T10M"]["q"]=[0.1,0.1,0.8]
    a,b=evaluate(original),evaluate(changed)
    assert a["ridge_beta"]==b["ridge_beta"]
    assert a["metrics"]!=b["metrics"]


def test_purged_target_does_not_enter_fit():
    source=source_fixture()
    source["snapshots"][19]["purged_training_boundary"]=True
    a=evaluate(source)
    source["snapshots"][19]["snapshots"]["pinnacle"]["T10M"]["q"]=[0.1,0.2,0.7]
    b=evaluate(source)
    assert a["ridge_beta"]==b["ridge_beta"]
    assert a["train_n"]==19


def test_missing_test_ids_not_replaced_from_training():
    source=source_fixture()
    source["coverage_panels"]["momentum"]["eligible_ids"]=[str(i) for i in range(24)]
    result=evaluate(source)
    assert result=={"status":"INSUFFICIENT_DATA","train_n":20,"test_n":4}


def test_training_target_at_first_test_decision_is_rejected():
    source=source_fixture()
    source["snapshots"][19]["snapshots"]["pinnacle"]["T10M"]["cutoff_at"]=source["primary_B"]["first_selected_test_decision_at"]
    with pytest.raises(AssertionError): evaluate(source)
