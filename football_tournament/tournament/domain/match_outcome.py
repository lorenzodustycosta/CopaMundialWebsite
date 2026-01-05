from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from tournament.models import Match


@dataclass(frozen=True)
class MatchWLT:
    """Winner/loser team ids for a validated match."""
    winner_id: int
    loser_id: int


def get_winner_loser_ids(match: Match) -> MatchWLT:
    """
    Compute winner/loser for a validated match.

    Note: for draws in knockout you must have a deterministic resolution.
    """
    if not match.validated:
        raise ValueError("Match must be validated to compute winner/loser.")

    if match.score_home_team != match.score_away_team:
        if match.score_home_team > match.score_away_team:
            return MatchWLT(winner_id=match.home_team_id, loser_id=match.away_team_id)
        return MatchWLT(winner_id=match.away_team_id, loser_id=match.home_team_id)

    # Draw case: with only boolean dts/dcr you still need to know who won.
    # If your app encodes the winner some other way, implement it here.
    raise ValueError("Draw match has no deterministic winner/loser with current fields.")
