"""BR-F011: o plugin reporta a versão da distribuição instalada, não um literal."""

from importlib.metadata import version

from brasileirao_predictor.ecosystem_plugin import PLUGIN


def test_plugin_health_reports_the_installed_distribution_version() -> None:
    assert PLUGIN.health()["version"] == version("brasileirao-predictor")
