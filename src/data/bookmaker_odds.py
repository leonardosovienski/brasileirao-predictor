"""Odds de bookmaker auditável para a coorte prospectiva H3/H5.

Por que existe: até 2026-07-25 o `scripts/sombra.py` lia a odd de
`sofascore_matches` (agregado da plataforma) e carimbava nela o nome vindo de
`BRASILEIRAO_BOOKMAKER`. O guard exigia a variável, mas defini-la não trocava a
fonte do preço — produzia pick com proveniência FALSA, e o campo
`closing_definition_version` afirmava "by-bookmaker" sem que o código cumprisse.
Este módulo fecha esse buraco: o preço passa a vir do book nomeado, via
`TheOddsApiProvider`, e o fechamento é reconstruído dos snapshots desse mesmo book.

Identidade entre fontes segue a mesma disciplina de `pit_backfill.resolve_entity`
e do `EloModel._elo` do cs-predictor: exato → dobra de acento determinística →
alias explícito, e SÓ quando o resultado é único. Ambíguo ou desconhecido falha
fechado — nunca se escolhe silenciosamente entre candidatos, porque parear a
partida errada contamina odd, resultado e CLV de uma vez só.
"""

from __future__ import annotations

import json
import unicodedata
from collections.abc import Iterable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

SNAPSHOTS = "bookmaker_odds_snapshots.jsonl"
MAPPING_VERSION = "brasileirao-bookmaker-identity/1.0"
# Tolerância entre o horário do book e o do Sofascore. A The Odds API publica
# `commence_time` = meia-noite UTC como PLACEHOLDER enquanto o horário não é
# confirmado (observado em 2026-07-25: Botafogo x Grêmio e Chapecoense x Vasco
# vieram 00:00 contra 18:00 reais — 18h de diferença). 36h cobre o placeholder
# com folga e continua muito abaixo do risco real: em Série A o par
# (mandante, visitante) nessa orientação ocorre UMA vez por temporada, então
# só um pareamento entre temporadas seria perigoso — e esse dista meses.
# A exigência de casamento ÚNICO continua sendo a trava principal.
KICKOFF_TOLERANCE = timedelta(hours=36)

# Aliases que NENHUMA normalização determinística resolve — nome comercial
# diferente, não variação de acento. Observados na The Odds API em 2026-07-25.
EXPLICIT_ALIASES = {
    "Bragantino-SP": "Red Bull Bragantino",
    "Athletico-PR": "Athletico",
    "Athletico Paranaense": "Athletico",
    "Atletico Paranaense": "Athletico",  # a API omite o "h" do nome oficial
    "Atletico-GO": "Atlético Goianiense",
    "Atletico-MG": "Atlético Mineiro",
    "Sport Club Recife": "Sport Recife",
    "Vasco": "Vasco da Gama",
}


def fold(value: str) -> str:
    """Chave de comparação: sem acento, sem caixa, sem borda. Determinística.

    Não é fuzzy-match: é uma normalização fechada. `Sao Paulo` e `São Paulo`
    colidem de propósito; `Atlético Mineiro` e `Atlético Goianiense`, não."""
    decomposed = unicodedata.normalize("NFD", value.strip())
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return unicodedata.normalize("NFC", stripped).casefold()


def resolve_team(raw_name: str, known: Iterable[str]) -> tuple[str | None, str]:
    """(nome canônico, status). Status: EXACT | RULE_BASED | AMBIGUOUS | REJECTED."""
    known = list(known)
    if raw_name in known:
        return raw_name, "EXACT"
    alias = EXPLICIT_ALIASES.get(raw_name)
    if alias is not None:
        return (alias, "RULE_BASED") if alias in known else (None, "REJECTED")
    candidates = [name for name in known if fold(name) == fold(raw_name)]
    if len(candidates) == 1:
        return candidates[0], "RULE_BASED"
    if len(candidates) > 1:
        return None, "AMBIGUOUS"
    return None, "REJECTED"


def _utc(value: str) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else None


def match_fixture(row: dict[str, Any], fixtures: list[dict[str, Any]]) -> tuple[dict | None, str]:
    """Casa uma cotação do book com o fixture do Sofascore. Falha fechado.

    `fixtures`: dicts com event_id, home_team, away_team, kickoff_at (ISO UTC)."""
    known = {f["home_team"] for f in fixtures} | {f["away_team"] for f in fixtures}
    home, hs = resolve_team(row.get("home_team") or "", known)
    away, aws = resolve_team(row.get("away_team") or "", known)
    if home is None or away is None:
        return None, f"identidade_nao_resolvida:{hs}/{aws}"
    if home == away:
        return None, "identidade_degenerada"
    kickoff = _utc(row.get("kickoff_at") or "")
    if kickoff is None:
        return None, "kickoff_invalido"
    hits = []
    for f in fixtures:
        if f["home_team"] != home or f["away_team"] != away:
            continue
        fk = _utc(f.get("kickoff_at") or "")
        if fk is None or abs(fk - kickoff) > KICKOFF_TOLERANCE:
            continue
        hits.append(f)
    if len(hits) == 1:
        return hits[0], "RULE_BASED" if (hs != "EXACT" or aws != "EXACT") else "EXACT"
    return None, "sem_fixture" if not hits else "fixture_ambiguo"


def persist_snapshots(path: Path, rows: list[dict[str, Any]]) -> int:
    """Append-only; idempotente por (event_id, selection, odds_captured_at)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    seen = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            seen.add((r.get("event_id"), r.get("selection"), r.get("odds_captured_at")))
    novos = 0
    with path.open("a", encoding="utf-8") as fh:
        for row in rows:
            key = (row.get("event_id"), row.get("selection"), row.get("odds_captured_at"))
            if key in seen:
                continue
            seen.add(key)
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            novos += 1
    return novos


def load_snapshots(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def closing_quote(
    snapshots: list[dict[str, Any]], *, event_id: Any, market: str, selection: str, kickoff_at: str
) -> dict | None:
    """Última cotação VÁLIDA do book antes do apito. Sem ela, não se liquida.

    É a definição `closing-v1:last-valid-pre-kickoff-by-bookmaker` — e agora o
    código a cumpre de fato, lendo o histórico do próprio book."""
    kickoff = _utc(kickoff_at)
    if kickoff is None:
        return None
    elegiveis = []
    for s in snapshots:
        if s.get("event_id") != event_id or s.get("market") != market or s.get("selection") != selection:
            continue
        captured = _utc(s.get("odds_captured_at") or "")
        odd = s.get("odd")
        if captured is None or captured >= kickoff:
            continue
        if not isinstance(odd, (int, float)) or odd <= 1:
            continue
        elegiveis.append((captured, s))
    if not elegiveis:
        return None
    return max(elegiveis, key=lambda pair: pair[0])[1]
