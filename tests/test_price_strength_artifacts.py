from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from brasileirao_predictor.research.price_strength import artifacts as io


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    package = root / "brasileirao_predictor" / "research" / "price_strength"
    package.mkdir(parents=True)
    (package / "candidate.py").write_bytes(b"VERSION = 'synthetic'\n")
    monkeypatch.setattr(io, "REPOSITORY_ROOT", root)
    monkeypatch.setattr(io, "PACKAGE_ROOT", package)
    return root


def input_file(tmp_path, content=b'{"x":1}\n'):
    path = tmp_path / "input.jsonl"
    path.write_bytes(content)
    return path


@pytest.mark.parametrize("content", [b'{"x":NaN}', b'{"x":Infinity}', b'{"x":-Infinity}', b'{"x":1e999}'])
def test_reader_rejects_nonfinite_json_numbers(isolated, tmp_path, content):
    path = input_file(tmp_path, content)
    with pytest.raises(ValueError, match="non-finite"):
        io.read_json(path)
    with pytest.raises(ValueError, match="line 1"):
        io.read_jsonl(path)


@pytest.mark.parametrize("content", [b'{"x":1,"x":2}', b'{"nested":{"x":1,"x":2}}'])
def test_reader_rejects_duplicate_keys_at_every_depth(isolated, tmp_path, content):
    path = input_file(tmp_path, content)
    with pytest.raises(ValueError, match="duplicate"):
        io.read_json(path)
    with pytest.raises(ValueError, match="duplicate"):
        io.read_jsonl(path)


def test_reader_preserves_boolean_types_and_requires_utf8_objects(isolated, tmp_path):
    path = input_file(tmp_path, b'{"flag":true,"number":1,"text":"1"}\n')
    assert io.read_json(path) == {"flag": True, "number": 1, "text": "1"}
    assert type(io.read_jsonl(path)[0]["flag"]) is bool
    path.write_bytes(b'{"text":"\xff"}')
    with pytest.raises(UnicodeDecodeError):
        io.read_json(path)
    path.write_bytes(b"[]")
    with pytest.raises(ValueError, match="object"):
        io.read_json(path)
    with pytest.raises(ValueError, match="object"):
        io.read_jsonl(path)


def test_jsonl_rejects_blank_lines_and_keeps_error_line(isolated, tmp_path):
    path = input_file(tmp_path, b'{"x":1}\n\n{"x":2}\n')
    with pytest.raises(ValueError, match="line 2"):
        io.read_jsonl(path)


@pytest.mark.parametrize("jsonl", [False, True])
def test_read_hashed_parses_and_hashes_one_identical_read(isolated, tmp_path, monkeypatch, jsonl):
    original = b'{"x":1}\n'
    path = input_file(tmp_path, original)
    read_bytes = Path.read_bytes
    calls = []

    def changing_read(candidate):
        calls.append(candidate)
        content = read_bytes(candidate)
        candidate.write_bytes(b'{"x":2}\n')
        return content

    monkeypatch.setattr(Path, "read_bytes", changing_read)
    value, fingerprint = io.read_hashed(path, jsonl=jsonl)
    assert value == ([{"x": 1}] if jsonl else {"x": 1})
    assert fingerprint == hashlib.sha256(original).hexdigest()
    assert calls == [path]


def test_jsonl_preserves_unicode_separator_inside_json_string(isolated, tmp_path):
    path = input_file(tmp_path, '{"text":"a\u2028b"}\n'.encode())
    assert io.read_jsonl(path) == [{"text": "a\u2028b"}]


def test_repository_data_is_rejected_before_open(isolated, monkeypatch):
    target = isolated / "data" / "forbidden.jsonl"
    monkeypatch.setattr(Path, "read_bytes", lambda path: pytest.fail("blocked input was opened"))
    with pytest.raises(ValueError, match="repository data"):
        io.read_json(target)
    with pytest.raises(ValueError, match="repository data"):
        io.read_jsonl(target)


def test_symlink_input_resolved_into_repository_data_is_rejected(isolated, tmp_path):
    data = isolated / "data"
    data.mkdir()
    target = data / "synthetic.jsonl"
    target.write_text("{}", encoding="utf-8")
    linked = tmp_path / "linked.jsonl"
    try:
        linked.symlink_to(target)
    except OSError:
        pytest.skip("platform does not permit creating a synthetic symlink")
    with pytest.raises(ValueError, match="repository data"):
        io.read_jsonl(linked)


def test_receipt_hashes_exact_inputs_artifacts_and_source_code(isolated, tmp_path):
    source = input_file(tmp_path)
    output = tmp_path / "run"
    manifest = io.write_artifacts(
        output,
        inputs={"history": source},
        artifacts={"rows.jsonl": [{"x": 1}], "summary.json": {"n": 1}},
        metadata={"scientific_state": "SYNTHETIC_DEMONSTRATION"},
    )
    assert manifest["status"] == "COMPLETE"
    assert manifest["inputs"]["history"]["sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert manifest["source_code"]["candidate.py"]["sha256"] == hashlib.sha256(b"VERSION = 'synthetic'\n").hexdigest()
    for name in ("rows.jsonl", "summary.json"):
        assert manifest["artifacts"][name]["sha256"] == hashlib.sha256((output / name).read_bytes()).hexdigest()
    assert json.loads((output / "manifest.json").read_text(encoding="utf-8")) == manifest
    assert io.read_jsonl(output / "rows.jsonl") == [{"x": 1}]


@pytest.mark.parametrize("relative", ["data/run", ".git/run", "."])
def test_output_cannot_target_data_git_or_repository_root(isolated, tmp_path, relative):
    source = input_file(tmp_path)
    with pytest.raises(ValueError):
        io.write_artifacts(isolated / relative, inputs={"input": source}, artifacts={}, metadata={})


def test_existing_directory_or_input_cannot_be_overwritten(isolated, tmp_path):
    source = input_file(tmp_path)
    for destination in (tmp_path, source):
        with pytest.raises(FileExistsError):
            io.write_artifacts(destination, inputs={"input": source}, artifacts={}, metadata={})
    assert source.read_bytes() == b'{"x":1}\n'


@pytest.mark.parametrize(
    "name",
    ["../escape.json", "nested/x.json", "nested\\x.json", "C:x.json", "manifest.json", "failure.json", "wrong.txt"],
)
def test_invalid_artifact_names_fail_before_creating_output(isolated, tmp_path, name):
    output = tmp_path / "run"
    with pytest.raises(ValueError, match="filename"):
        io.write_artifacts(output, inputs={}, artifacts={name: {}}, metadata={})
    assert not output.exists()


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_output_rejected_before_directory_creation(isolated, tmp_path, value):
    output = tmp_path / "run"
    with pytest.raises(ValueError):
        io.write_artifacts(output, inputs={}, artifacts={"bad.json": {"value": value}}, metadata={})
    assert not output.exists()


def test_jsonl_requires_list_of_objects_and_case_collisions_are_rejected(isolated, tmp_path):
    for artifacts in ({"rows.jsonl": {}}, {"rows.jsonl": [1]}, {"A.json": {}, "a.json": {}}):
        with pytest.raises(ValueError):
            io.write_artifacts(tmp_path / "run", inputs={}, artifacts=artifacts, metadata={})
        assert not (tmp_path / "run").exists()


def test_failed_write_preserves_existing_artifact_without_success_manifest(isolated, tmp_path, monkeypatch):
    original_open = Path.open
    output = tmp_path / "run"

    def fail_second(path, mode="r", *args, **kwargs):
        if path == output / "b.json" and mode == "xb":
            raise OSError("synthetic storage failure")
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fail_second)
    with pytest.raises(OSError, match="synthetic"):
        io.write_artifacts(output, inputs={}, artifacts={"a.json": {}, "b.json": {}}, metadata={})
    assert (output / "a.json").exists()
    assert not (output / "manifest.json").exists()
    assert io.read_json(output / "failure.json")["status"] == "FAILED"


def test_failed_manifest_publication_cannot_leave_complete_receipt(isolated, tmp_path, monkeypatch):
    def fail_publish(*args):
        raise OSError("synthetic publication failure")

    monkeypatch.setattr(io.os, "link", fail_publish)
    output = tmp_path / "run"
    with pytest.raises(OSError, match="publication"):
        io.write_artifacts(output, inputs={}, artifacts={"summary.json": {}}, metadata={})
    assert (output / "summary.json").exists()
    assert not (output / "manifest.json").exists()
    assert io.read_json(output / "failure.json")["status"] == "FAILED"


def test_changed_input_fails_before_artifact_write_and_records_failure(isolated, tmp_path):
    source = input_file(tmp_path)
    rows, fingerprint = io.read_hashed(source, jsonl=True)
    source.write_bytes(b'{"x":2}\n')
    output = tmp_path / "run"
    with pytest.raises(ValueError, match="changed"):
        io.write_artifacts(
            output,
            inputs={"history": source},
            artifacts={"rows.jsonl": rows},
            metadata={"input_hashes_used": {"history": fingerprint}},
        )
    assert not (output / "rows.jsonl").exists()
    assert not (output / "manifest.json").exists()
    assert io.read_json(output / "failure.json")["status"] == "FAILED"


@pytest.mark.parametrize("expected", [{}, {"wrong": "hash"}, None])
def test_input_hash_expectations_cannot_silently_omit_inputs(isolated, tmp_path, expected):
    source = input_file(tmp_path)
    output = tmp_path / "run"
    with pytest.raises(ValueError, match="exactly"):
        io.write_artifacts(output, inputs={"history": source}, artifacts={}, metadata={"input_hashes_used": expected})
    assert not (output / "manifest.json").exists()
    assert io.read_json(output / "failure.json")["status"] == "FAILED"


def test_matching_input_hashes_connect_receipt_to_processed_bytes(isolated, tmp_path):
    source = input_file(tmp_path)
    rows, fingerprint = io.read_hashed(source, jsonl=True)
    manifest = io.write_artifacts(
        tmp_path / "run",
        inputs={"history": source},
        artifacts={"rows.jsonl": rows},
        metadata={"input_hashes_used": {"history": fingerprint}},
    )
    assert manifest["inputs"]["history"]["sha256"] == fingerprint
    assert manifest["metadata"]["input_hashes_used"]["history"] == fingerprint
