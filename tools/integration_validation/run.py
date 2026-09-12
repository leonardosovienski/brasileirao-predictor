"""BR-CAIN-MAIN-20260912: real documentary source, isolated installed consumer."""

import argparse
import copy
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("producer", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    root, out = args.producer.resolve(), args.output.resolve()
    out.mkdir(exist_ok=False)
    for key in list(os.environ):
        if key.startswith(("CAIN_", "OLLAMA_", "EXCHANGE_", "REDIS_", "PYTHONPATH")):
            del os.environ[key]
    os.environ.update(PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1", TEMP=str(out), TMP=str(out))
    import threading

    from cain.research import ResearchService
    from cain.research.api import mount
    from cain.research.bundles import BundleService
    from cain.research.historian import metadata_context
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from research_bundle import canonical, digest, loads, seal, validate
    from research_snapshot import validate as validate_snapshot

    def save(name, value):
        (out / name).write_bytes(canonical(value))

    def content(value):
        # service.query records each invocation with uuid4().hex. It is a receipt,
        # not a source identity/version: compare every other field unchanged.
        value = copy.deepcopy(value)
        value.get("snapshots", {}).pop("query_id", None)
        return value

    def load_tool(name):
        spec = importlib.util.spec_from_file_location(name, root / "tools" / (name + ".py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    source = "docs/EVIDENCE_REGISTRY.md"
    raw = (root / source).read_bytes()
    pin = digest(raw)
    sha = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    expected = {}
    header = None
    for line in raw.decode().splitlines():
        if line.startswith("| Claim ID |"):
            header = [c.strip() for c in line.strip("|").split("|")]
        if line.startswith("| CLAIM-BR-MARKET-"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            expected[cells[0]] = dict(zip(header, cells))
    assert set(expected) == {f"CLAIM-BR-MARKET-00{i}" for i in (1, 2, 3)}
    assert all(p["State"] == "BLOCKED_PENDING_PIT_FEATURES" for p in expected.values())
    save(
        "expected.json",
        dict(sha=sha, pin=pin, claims=expected, classification="REAL_VERSIONED_DOCUMENT_ISOLATED_RUNTIME"),
    )
    inbox = out / "inbox"
    inbox.mkdir()
    load_tool("export_cain_status").export(root, pin, inbox / "snapshot.json", "2026-09-12T00:00:00Z")
    snapshot = loads((inbox / "snapshot.json").read_bytes())
    validate_snapshot(snapshot)
    bundle = load_tool("export_cain_bundle").export(
        root, {source: pin}, out / "producer-bundle", "2026-09-12T00:00:00Z"
    )
    validate(bundle)
    shutil.copytree(out / "producer-bundle", inbox / "bundle")
    identity = dict(
        user="validation",
        project="",
        collection="brasileirao",
        domain="brasileirao",
        repository=bundle["origin"]["repository"],
        publisher="brasileirao-local",
        sources=[source],
    )
    policy = dict(
        version=3,
        imports=[dict(user="validation", project="", collection="brasileirao", root=str(inbox))],
        grants=[
            dict(
                identity, stream="public-status-reports", policies=["brasileirao-public-status-local/1"], generate=False
            )
        ],
        bundle_grants=[
            dict(
                identity,
                stream="research-bundle",
                policies=["brasileirao-research-bundle/1"],
                generate=False,
                roles=["document", "report"],
                reference_only=True,
                max_manifest_bytes=2000000,
                max_object_bytes=16000000,
                max_received_bytes=64000000,
            )
        ],
    )
    policy_path = out / "policy.json"
    policy_path.write_bytes(canonical(policy))
    service = ResearchService(out / "research.db", policy_path)
    scope = service.scope("validation", None, "brasileirao")
    store = BundleService(service)
    checks = {}

    def rejects(name, call):
        try:
            call()
        except (ValueError, PermissionError, FileNotFoundError) as exc:
            checks[name] = dict(rejected=True, error=str(exc), error_type=type(exc).__name__)
        else:
            raise AssertionError(name + " unexpectedly accepted")

    rejects("unapproved", lambda: store.ingest("bundle/bundle.json", scope))
    save("approval.json", store.approve("bundle/bundle.json", scope))
    assert store.ingest("bundle/bundle.json", scope)["status"] == "admitted"
    assert store.ingest("bundle/bundle.json", scope)["status"] == "duplicate"
    assert service.ingest("snapshot.json", scope)["status"] == "admitted"
    assert service.ingest("snapshot.json", scope)["status"] == "duplicate"
    query = store.query(scope)
    save("query.json", query)
    assert query["total"] == 3
    for e in query["entities"]:
        assert e["payload"] == expected[e["entity_id"]]
        assert e["status"] == "BLOCKED_PENDING_PIT_FEATURES"
        assert e["origin"]["code_revision"] == sha and e["origin"]["inputs"][source] == pin
        assert e["event_at"] is e["recorded_at"] is e["available_at"] is None
    context = metadata_context(service, scope, bundles=store)
    save("historian.json", context)
    assert context["classification"] == "FACTUAL" and context["derived"] == []
    assert context["bundles"]["entities"] == query["entities"]
    assert context["snapshots"]["total_record_revisions"] == 3
    # Real HTTP adapter in-process, no model, network or production application.
    app = FastAPI()

    def forbidden_provider():
        raise AssertionError("No generation permitted in this case")

    mount(app, out / "workspace.db", lambda *a: None, forbidden_provider, threading.Lock(), policy_path, service.path)
    with TestClient(app) as client:
        req = dict(user_id="validation", collection="brasileirao")
        api_query = client.post("/research/bundles/query", json=req)
        assert api_query.status_code == 200
        assert api_query.json() == query
        api_context = client.post("/research/bundles/historian", json=req)
        save("api-context-observed.json", dict(status=api_context.status_code, body=api_context.json()))
        assert api_context.status_code == 200 and content(api_context.json()) == content(context)
        assert client.post("/research/bundles/query", json=dict(req, unknown=True)).status_code == 422
        save("api.json", dict(query=api_query.json(), historian=api_context.json()))
    command = [
        str(Path(sys.executable).with_name("cain.exe" if os.name == "nt" else "cain")),
        "research",
        "--policy",
        str(policy_path),
        "--db",
        str(service.path),
        "--user",
        "validation",
        "--collection",
        "brasileirao",
    ]
    cli = subprocess.run(
        command + ["bundle", "historian"], capture_output=True, text=True, encoding="utf-8", check=True, cwd=out
    )
    assert content(json.loads(cli.stdout)) == content(context)
    save("cli-historian.json", json.loads(cli.stdout))
    search = subprocess.run(
        command + ["search", "CLAIM-BR-MARKET-002 H-6h"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
        cwd=out,
    )
    save("cli-search.json", json.loads(search.stdout))
    assert "CLAIM-BR-MARKET-002" in search.stdout and "H-6h" in search.stdout
    invalid = copy.deepcopy(bundle)
    invalid["profile"] = "unsupported/99"
    rejects("schema", lambda: validate(seal(invalid)))
    invalid = copy.deepcopy(bundle)
    del invalid["origin"]["publisher"]
    rejects("missing_required", lambda: validate(invalid))
    corrupted = inbox / "corrupt"
    shutil.copytree(inbox / "bundle", corrupted)
    corrupt_manifest = copy.deepcopy(bundle)
    corrupt_manifest["exported_at"] = "2026-09-12T00:01:00Z"
    (corrupted / "bundle.json").write_bytes(canonical(seal(corrupt_manifest)))
    received = next(a for a in bundle["artifacts"] if a["availability"] == "received")
    (corrupted / received["relative_path"]).write_bytes(b"corrupted test transport")
    # Approval reserves manifest semantics only; objects are checked at ingestion.
    store.approve("corrupt/bundle.json", scope)
    rejects("corrupted_object", lambda: store.ingest("corrupt/bundle.json", scope))
    conflict = copy.deepcopy(bundle)
    conflict["entities"][0]["payload"]["State"] = "UNSUPPORTED_TEST_CONFLICT"
    (inbox / "conflict").mkdir()
    (inbox / "conflict/bundle.json").write_bytes(canonical(seal(conflict)))
    rejects("identity_conflict", lambda: store.approve("conflict/bundle.json", scope))
    rejects("missing_manifest", lambda: store.ingest("missing/bundle.json", scope))
    inbox.rename(out / "transport-offline")
    save("verify-offline.json", store.verify(scope))
    assert store.query(scope) == query
    store.materialize(scope, bundle["bundle_id"], received["artifact_id"], out / "recovered-source.md")
    assert (out / "recovered-source.md").read_bytes() == raw
    policy["bundle_grants"] = []
    policy_path.write_bytes(canonical(policy))
    assert store.query(scope)["total"] == 0
    checks["revocation"] = dict(hidden=True)
    assert (root / source).read_bytes() == raw
    save("negative-cases.json", checks)
    save(
        "result.json",
        dict(
            status="PASS",
            producer_sha=sha,
            source_sha256=pin,
            bundle_id=bundle["bundle_id"],
            publication_id=snapshot["publication_id"],
            entities=3,
            negative_cases=checks,
            source_unchanged=True,
            cli_api_equal=True,
            offline_recovery=True,
        ),
    )
    print((out / "result.json").read_text())


if __name__ == "__main__":
    main()
