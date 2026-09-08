"""Execute and enrich the real RPS power harness under predictor-core 3.x."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from brasileirao_scripts.research_01a_refit_cadence import TRIALS, attest_rps_power

ROOT = Path(__file__).resolve().parent.parent


def run() -> dict:
    record = attest_rps_power()
    reference = json.dumps(
        {
            "positive": {"generator": "probabilistic_predictor", "n": 300, "skill": 0.6, "seed": 13},
            "negative": {"generator": "probabilistic_predictor", "n": 300, "skill": 0.0, "seed": 17},
            "metric": "rps",
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    record.update(
        {
            "executed_at": record["passed_at"],
            # `code_version` NAO e sobrescrito aqui. Ate o core 3.1.0 este script
            # calculava o seu proprio, com um problema de ordenacao: run() chama
            # attest_rps_power() primeiro, que ESCREVE o arquivo do atestado, e so
            # entao media a arvore -- que a essa altura estava suja por causa da
            # propria escrita. O `;dirty` do atestado anterior era, ao menos em
            # parte, esse artefato, e nao uma arvore genuinamente suja.
            #
            # O core 3.2.0 grava code_version dentro de attest_pipeline_power,
            # ANTES de escrever, e no formato mais rico `package:X;git:Y`. Esse
            # valor e o autoritativo, e a recusa de arvore suja (achado 7 da
            # auditoria adversarial de 2026-09-05) mora la tambem.
            "dataset_reference_fingerprint": "sha256:" + hashlib.sha256(reference).hexdigest(),
            "positive_control_result": "COMPROVADA",
            "negative_control_result": "REFUTADA",
        }
    )
    path = TRIALS.with_name(TRIALS.stem + ".harness_attestation.json")
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    return record


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
