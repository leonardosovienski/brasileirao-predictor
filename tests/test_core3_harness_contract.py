from brasileirao_scripts import renew_core3_harness


def test_committed_harness_is_real_core3_execution_with_both_controls():
    import json

    path = renew_core3_harness.TRIALS.with_name("trials.harness_attestation.json")
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["core_version"] == "3.1.0"
    assert record["executed_at"] == record["passed_at"]
    assert record["code_version"].startswith("git:")
    assert record["dataset_reference_fingerprint"].startswith("sha256:")
    assert record["positive_control_result"] == "COMPROVADA"
    assert record["negative_control_result"] == "REFUTADA"
