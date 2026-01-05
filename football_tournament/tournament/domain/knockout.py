from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class MatchOutcome:
    """Represents a validated match outcome and its winner."""
    winner_team_id: int

def get_winner_team_id(
    *,
    score_home: int,
    score_away: int,
) -> int:
    """
    Determine the winner team id from match scores.
    """
    if score_home != score_away:
        return 0 if score_home > score_away else 1