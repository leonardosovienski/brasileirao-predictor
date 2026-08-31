import json

import pytest

from brasileirao_predictor.identity import CanonicalTeamResolver


def _catalogs(tmp_path, aliases):
    teams = tmp_path / "teams.json"
    mapping = tmp_path / "aliases.json"
    teams.write_text(
        json.dumps({"teams": {"São Paulo": {"slug": "sao-paulo"}, "Flamengo": {"slug": "flamengo"}}}), encoding="utf-8"
    )
    mapping.write_text(json.dumps({"mapping_version": "v1", "aliases": aliases}), encoding="utf-8")
    return mapping, teams


def test_resolves_canonical_name_id_and_normalized_alias(tmp_path):
    aliases, teams = _catalogs(tmp_path, {"CR Flamengo RJ": "flamengo"})
    resolver = CanonicalTeamResolver(aliases, teams)
    assert resolver.resolve("São Paulo").canonical == "sao-paulo"
    assert resolver.resolve("sao-paulo").match_method == "canonical_id"
    result = resolver.resolve("  cr flâmengo rj ")
    assert result.canonical == "flamengo"
    assert result.status == "ALIASED"


def test_unknown_only_suggests_and_never_resolves(tmp_path):
    aliases, teams = _catalogs(tmp_path, {"CR Flamengo RJ": "flamengo"})
    result = CanonicalTeamResolver(aliases, teams).resolve("CR Flameng RJ")
    assert result.canonical is None
    assert result.status == "UNKNOWN"
    assert result.suggestion == "CR Flamengo RJ"


def test_rejects_unknown_target_and_normalized_collision(tmp_path):
    aliases, teams = _catalogs(tmp_path, {"Unknown": "missing"})
    with pytest.raises(ValueError, match="unknown canonical"):
        CanonicalTeamResolver(aliases, teams)
    aliases, teams = _catalogs(tmp_path, {"Clube Á": "flamengo", "clube a": "sao-paulo"})
    with pytest.raises(ValueError, match="normalization collision"):
        CanonicalTeamResolver(aliases, teams)
