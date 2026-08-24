from src.ecosystem_plugin import PLUGIN


def test_ecosystem_plugin_contract_shape():
    health = PLUGIN.health()
    caps = PLUGIN.capabilities()
    assert health["domain"] == "brasileirao"
    assert health["status"] in {
        "SUCCEEDED",
        "DEGRADED",
        "WAITING",
        "FAILED",
        "SOURCE_UNAVAILABLE",
        "NO_UPSTREAM_EVENTS",
    }
    assert caps["domain"] == "brasileirao"
    assert caps["supports_prediction"] is True
    assert caps["economic_status"] == "NOT_VALIDATED"
    assert caps["capital_permission"] == "FORBIDDEN"
