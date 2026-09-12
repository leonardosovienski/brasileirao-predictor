"""Producer-owned documentary lineage; no protected prediction/cohort access."""

import argparse
from pathlib import Path

from research_bundle import canonical, digest, loads
from research_bundle.export import Builder, admitted_sources, exporter_provenance

SOURCE = "docs/EVIDENCE_REGISTRY.md"
REPLAY = "reports/replay_round_2026_08_22.json"


def export(root, expected, destination, exported_at):
    revision, sources = admitted_sources(root, expected, {SOURCE, REPLAY})
    provenance = exporter_provenance({"export_cain_bundle.py": Path(__file__)})
    builder = Builder(dict(domain="brasileirao", repository="https://github.com/leonardosovienski/brasileirao-predictor",
                           publisher="brasileirao-local", stream="research-bundle", code_revision=revision,
                           exporter_revision="sha256:" + digest(canonical(provenance)), inputs=expected),
                      dict(policy="brasileirao-research-bundle/1", read=True, disclose=False, generate=False),
                      exported_at, provenance=provenance)
    artifact = builder.resource(SOURCE, "producer:" + SOURCE, raw=sources[SOURCE], media_type="text/markdown")
    header, count = None, 0
    for line in sources[SOURCE].decode("utf-8").splitlines():
        if line.startswith("| Claim ID |"):
            header = [c.strip() for c in line.strip("|").split("|")]
        elif line.startswith("| CLAIM-BR-"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if header is None or len(header) != len(cells):
                raise ValueError("Unsupported registry")
            payload = dict(zip(header, cells))
            node = builder.entity(cells[0], "claim", payload["State"], payload, SOURCE)
            builder.relation(node, "SUPPORTED_BY", artifact)
            count += 1
    if count == 0:
        raise ValueError("No admitted claims")
    # These resource names are literally referenced by this admitted registry.
    text = sources[SOURCE].decode("utf-8")
    for name in (
        "reports/exp001_data_pilot_2026-09-02.json",
        "reports/exp001_coverage_audit_2026-09-02.json",
        "reports/exp001_coverage_identity_assessment_2026-09-02.json",
    ):
        if name in text:
            reference = builder.resource(
                name,
                "producer:" + name,
                role="report",
                metadata={"availability_reason": "Referenced by registry; bytes not admitted"},
            )
            builder.relation(artifact, "REFERENCES", reference)
    if REPLAY in sources:
        replay = loads(sources[REPLAY])
        if (
            replay.get("schema_version") != "retrospective-round-replay/1"
            or replay.get("status") != "DIAGNOSTIC_CONTAMINATED_NOT_CONFIRMATORY"
        ):
            raise ValueError("Unsupported diagnostic replay")
        if type(replay.get("games")) is not list or len(replay["games"]) > 20:
            raise ValueError("Bounded replay games required")
        resource = builder.resource(
            REPLAY,
            "producer:" + REPLAY,
            raw=sources[REPLAY],
            role="report",
            metadata={"scope": "Existing retrospective contaminated diagnostic; not prospective prediction evidence"},
        )
        report = builder.entity(
            REPLAY,
            "measurement",
            replay["status"],
            {k: v for k, v in replay.items() if k != "games"},
            REPLAY,
            axis="diagnostic",
            identity_basis="source_locator",
            recorded_at=replay.get("generated_at"),
        )
        builder.relation(report, "REPRESENTED_BY", resource)
        identities = set()
        for game in replay["games"]:
            identity = "replay-match:" + str(game["event_id"])
            if identity in identities:
                raise ValueError("Duplicate replay event")
            identities.add(identity)
            node = builder.entity(
                identity,
                "match",
                replay["status"],
                dict(
                    game,
                    temporal_admissibility="UNKNOWN",
                    published_at=None,
                    ingested_at=None,
                    prediction_cutoff=None,
                    observation_selection="NOT_PROVEN",
                ),
                REPLAY,
                axis="diagnostic",
                identity_basis="source_key",
                event_at=game.get("kickoff_at"),
                recorded_at=replay.get("generated_at"),
            )
            builder.relation(report, "USES", node)
            builder.relation(node, "SUPPORTED_BY", resource)
        builder.body["coverage"]["limitations"].append(
            "Retrospective replay preserves kickoff_at/captured_at/generated_at separately. "
            "It does not prove which observations were known at prediction time; no PIT engine was invoked."
        )
    builder.body["coverage"]["missing"] = [
        "No admissible prediction or settlement exported",
        "Event, publication, ingestion and cutoff clocks unknown for these documentary claims",
    ]
    builder.body["coverage"]["limitations"].append(
        "Horizon selection text is preserved; no PIT observation slice or new prediction"
    )
    return builder.publish(root, destination, sources)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--replay-sha", help="Explicit pin for existing contaminated retrospective diagnostic")
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--exported-at", required=True)
    args = parser.parse_args()
    expected = {SOURCE: args.expected_sha}
    if args.replay_sha:
        expected[REPLAY] = args.replay_sha
    print(export(args.root, expected, args.destination, args.exported_at)["bundle_id"])


if __name__ == "__main__":
    main()
