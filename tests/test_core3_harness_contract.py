import json
from importlib.metadata import version

from brasileirao_scripts import renew_core3_harness


def test_committed_harness_is_real_core3_execution_with_both_controls():
    path = renew_core3_harness.TRIALS.with_name("trials.harness_attestation.json")
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["core_version"] == version("predictor-core")
    assert record["executed_at"] == record["passed_at"]
    assert record["dataset_reference_fingerprint"].startswith("sha256:")
    assert record["positive_control_result"] == "COMPROVADA"
    assert record["negative_control_result"] == "REFUTADA"


def test_o_atestado_committado_aponta_para_codigo_identificavel():
    """Achado 7 da auditoria adversarial de 2026-09-05, virado contrato.

    O atestado destrava o registro de trials novas. Um atestado cujo
    `code_version` termina em `;dirty` destrava trials que ninguém consegue
    reproduzir, porque o código avaliado não existe em lugar nenhum.

    Até o core 3.1.0 este campo era escrito pelo `renew_core3_harness`, que o
    calculava DEPOIS de o atestado já ter sido gravado em disco — e portanto
    media uma árvore suja pela própria escrita. O `;dirty` do atestado anterior
    era, ao menos em parte, esse artefato. O core 3.2.0 passou a gravar o campo
    dentro de `attest_pipeline_power`, antes da escrita, e a recusar árvore
    suja; este teste trava o resultado para que a regressão não volte calada.
    """
    path = renew_core3_harness.TRIALS.with_name("trials.harness_attestation.json")
    record = json.loads(path.read_text(encoding="utf-8"))

    assert not record["code_version"].endswith(";dirty")
    assert record["code_version"].startswith(f"package:{version('predictor-core')};git:")
    sha = record["code_version"].split(";git:", 1)[1]
    assert len(sha) == 40 and sha != "0" * 40
