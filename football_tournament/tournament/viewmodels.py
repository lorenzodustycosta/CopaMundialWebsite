from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from tournament.models import Match


@dataclass(frozen=True)
class MatchRowVM:
    """View model for rendering a match row in templates."""
    home: str
    away: str
    score: str
    suffix: str
    is_validated: bool


def build_match_row_vm(match: Match) -> MatchRowVM:
    """Build a template-friendly match representation."""
    suffix = ""
    if match.dts:
        suffix = "DTS"
    elif match.dcr:
        suffix = "DCR"

    score = "-"
    if match.score_home_team is not None and match.score_away_team is not None:
        score = f"{match.score_home_team} - {match.score_away_team}"

    return MatchRowVM(
        home=match.home_team.name,
        away=match.away_team.name,
        score=score,
        suffix=suffix,
        is_validated=bool(match.validated),
    )
