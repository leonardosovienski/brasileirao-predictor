"""Canonical, deterministic team identity resolution shared by providers."""

import json
import unicodedata
from dataclasses import dataclass
from difflib import get_close_matches
from pathlib import Path
from typing import Literal

ResolutionStatus = Literal["CANONICAL", "ALIASED", "UNKNOWN"]


def normalize_team_name(value: str) -> str:
    text = unicodedata.normalize("NFKD", value.strip().casefold())
    return " ".join("".join(char for char in text if not unicodedata.combining(char)).split())


@dataclass(frozen=True)
class AliasResult:
    canonical: str | None
    suggestion: str | None
    status: ResolutionStatus
    raw_input: str
    normalized_input: str
    mapping_version: str
    match_method: Literal["canonical_id", "canonical_name", "alias", "none"]


class CanonicalTeamResolver:
    """Resolve explicit identities; fuzzy matching only returns a suggestion."""

    def __init__(self, aliases_path: Path, canonical_teams_path: Path) -> None:
        alias_payload = json.loads(aliases_path.read_text(encoding="utf-8"))
        teams_payload = json.loads(canonical_teams_path.read_text(encoding="utf-8"))
        if not isinstance(alias_payload.get("aliases"), dict) or not alias_payload.get("mapping_version"):
            raise ValueError("alias catalog requires mapping_version and aliases object")
        teams = teams_payload.get("teams")
        if not isinstance(teams, dict) or not teams:
            raise ValueError("canonical team catalog requires a non-empty teams object")
        self.mapping_version = str(alias_payload["mapping_version"])
        self._canonical: dict[str, str] = {}
        self._ids: set[str] = set()
        for display, metadata in teams.items():
            if not isinstance(metadata, dict) or not isinstance(metadata.get("slug"), str):
                raise ValueError(f"canonical team {display!r} requires a string slug")
            canonical_id = metadata["slug"]
            self._ids.add(canonical_id)
            for value in (str(display), canonical_id):
                key = normalize_team_name(value)
                previous = self._canonical.get(key)
                if previous is not None and previous != canonical_id:
                    raise ValueError(f"canonical normalization collision for {value!r}")
                self._canonical[key] = canonical_id
        self._aliases: dict[str, str] = {}
        self._raw_aliases: list[str] = []
        for raw_alias, raw_target in alias_payload["aliases"].items():
            alias, target = str(raw_alias), str(raw_target)
            if target not in self._ids:
                raise ValueError(f"alias {alias!r} targets unknown canonical id {target!r}")
            key = normalize_team_name(alias)
            previous = self._aliases.get(key)
            if previous is not None and previous != target:
                raise ValueError(f"alias normalization collision for {alias!r}: {previous!r} != {target!r}")
            canonical_collision = self._canonical.get(key)
            if canonical_collision is not None and canonical_collision != target:
                raise ValueError(f"alias {alias!r} collides with canonical id {canonical_collision!r}")
            self._aliases[key] = target
            self._raw_aliases.append(alias)

    def resolve(self, source_name: str) -> AliasResult:
        raw = str(source_name)
        normalized = normalize_team_name(raw)
        canonical = self._canonical.get(normalized)
        if canonical is not None:
            method = "canonical_id" if normalized == normalize_team_name(canonical) else "canonical_name"
            return AliasResult(canonical, None, "CANONICAL", raw, normalized, self.mapping_version, method)
        canonical = self._aliases.get(normalized)
        if canonical is not None:
            return AliasResult(canonical, None, "ALIASED", raw, normalized, self.mapping_version, "alias")
        suggestions = get_close_matches(raw, self._raw_aliases, n=1, cutoff=0.72)
        return AliasResult(
            None, suggestions[0] if suggestions else None, "UNKNOWN", raw, normalized, self.mapping_version, "none"
        )


class TeamAliases(CanonicalTeamResolver):
    """Backward-compatible A1 constructor using the adjacent team catalog."""

    def __init__(self, path: Path, canonical_teams_path: Path | None = None) -> None:
        super().__init__(path, canonical_teams_path or path.with_name("teams_brasileirao.json"))
