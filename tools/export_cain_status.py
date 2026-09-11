"""Export one explicitly admitted public status report; stdlib only, no pipeline.

ResearchSnapshotV1 wire serialization; the receiver uses the canonical validator.
"""

import argparse
import hashlib
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

DOMAIN = "brasileirao"
SOURCE = "docs/EVIDENCE_REGISTRY.md"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def export(root, expected_sha, output):
    root = Path(root).resolve(strict=True)
    output = Path(output).resolve()
    if output.is_relative_to(root):
        raise ValueError("Publication must be outside the source checkout")
    if not re.fullmatch("[a-f0-9]{64}", expected_sha):
        raise ValueError("Explicit SHA-256 admission required")
    source = root / SOURCE
    current = source
    while current != root:
        if current.is_symlink() or (hasattr(current, "is_junction") and current.is_junction()):
            raise ValueError("Source links are not admitted")
        current = current.parent
    with source.open("rb") as handle:
        raw = handle.read(100001)
    if len(raw) > 100000 or digest(raw) != expected_sha:
        raise ValueError("Source differs from admitted report")
    revision = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    if subprocess.check_output(["git", "-C", str(root), "status", "--porcelain", "--", SOURCE]):
        raise ValueError("Source must be committed before export")
    records, evidence, offset = [], [], 0
    for line in raw.decode("utf-8").splitlines(keepends=True):
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        selected = line.startswith("| CLAIM-BR-MARKET-")
        if selected:
            if len(cells) != 9 or not cells[2]:
                raise ValueError("Unsupported report layout")
            eid = digest(canonical([SOURCE, offset, line]))
            evidence.append(
                dict(
                    id=eid,
                    source=SOURCE,
                    availability="received",
                    text=line,
                    sha256=digest(line.encode("utf-8")),
                    hash_basis="received_utf8",
                    locator="table-row:" + cells[0],
                    start=offset,
                    end=offset + len(line),
                    offset_unit="unicode_codepoints",
                )
            )
            record = dict(
                source_id=cells[0],
                kind="documented_status_row",
                identity_basis="source_assigned",
                source_status=cells[2],
                status_axis="domain_lifecycle",
                mapping=None,
                reason=None,
                event_at=None,
                recorded_at=None,
                available_at=None,
                supersedes=[],
                evidence_ids=[eid],
            )
            records.append(dict(record, revision=digest(canonical(record))))
        offset += len(line)
    if len(records) != 3 or len({r["source_id"] for r in records}) != len(records):
        raise ValueError("Missing or duplicate admitted status rows")
    with source.open("rb") as handle:
        if handle.read(100001) != raw:
            raise ValueError("Source changed during export")
    package = dict(
        contract="ResearchSnapshotV1",
        profile="local-evidence/1",
        extensions={},
        origin=dict(
            domain=DOMAIN,
            repository="https://github.com/leonardosovienski/" + DOMAIN + "-predictor",
            publisher=DOMAIN + "-local",
            stream="public-status-reports",
            code_revision=revision,
            exporter_revision="sha256:" + digest(Path(__file__).read_bytes()),
            inputs={SOURCE: expected_sha},
        ),
        exported_at=datetime.now(UTC).isoformat(),
        restrictions=dict(policy=DOMAIN + "-public-status-local/1", read=True, disclose=False, generate=True),
        coverage=dict(
            scope="Selected public documented status rows",
            completeness="partial",
            included=[SOURCE],
            missing=[],
            excluded=["All other domain sources and databases"],
            limitations=[
                "Documented reports, not reproduced experiments",
                "No present validity or historical availability attestation",
                "Literal source state; no scientific or capital decision",
                "Structured reason absent; narrative retained in evidence",
            ],
        ),
        records=records,
        evidence=evidence,
    )
    package["publication_id"] = digest(canonical(package))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as handle:
        handle.write(canonical(package))
    return dict(
        publication_id=package["publication_id"],
        records=len(records),
        source_sha256=expected_sha,
        source_revision=revision,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    print(json.dumps(export(**vars(parser.parse_args())), ensure_ascii=False))


if __name__ == "__main__":
    main()
