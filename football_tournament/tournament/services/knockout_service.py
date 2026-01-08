# tournament/services/knockout_service.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from itertools import cycle
from typing import Dict, List, Tuple

from django.db import transaction

from tournament.domain.knockout import get_winner_team_id
from tournament.models import Match, Team
from tournament.services.group_stage_service import compute_group_stage_outcome


@dataclass(frozen=True)
class KnockoutDates:
    """Dates configuration for knockout rounds."""
    quarter_day1: date
    quarter_day2: date
    semi_day: date
    final_day: date


def end_group_stage_and_create_quarterfinals(*, dates: KnockoutDates, times: Tuple[str, ...] = ("20:30", "21:30")) -> int:
    """
    Close group stage and create quarterfinal matches.

    Preconditions:
    - All group-stage matches must be validated.
    - Rankings must produce exactly 8 qualified teams (top-2 of 4 groups).
    """
    _ensure_group_stage_completed()

    outcome = compute_group_stage_outcome()
    first = [t.team_name for t in outcome.first]
    second = [t.team_name for t in outcome.second]

    if len(first) != 4 or len(second) != 4:
        raise ValueError("Quarterfinals require 4 groups with at least 2 teams each (8 qualified teams).")

    matchups = _basic_quarterfinal_matchups(first, second)
    time_it = cycle(times)

    created = 0
    with transaction.atomic():
        # Prevent duplicate quarterfinals if called twice
        Match.objects.filter(group="Quarti").delete()
        for i, (home_name, away_name) in enumerate(matchups):
            Match.objects.create(
                stage="Eliminazione",
                group="Quarti",
                home_team=Team.objects.get(name=home_name),
                away_team=Team.objects.get(name=away_name),
                date=dates.quarter_day1 if i <= 1 else dates.quarter_day2,
                time=next(time_it),
                validated=False,
                mvp=None,
            )
            created += 1

    return created


def end_quarterfinals_and_create_semifinals(*, dates: KnockoutDates, time: str = "21:00") -> int:
    """
    Create semifinals from validated quarterfinal matches.

    Preconditions:
    - Exactly 4 quarterfinal matches exist and are validated.
    - Each match must have a deterministic winner.
    """
    qf = _get_validated_round_matches(round_name="Quarti", expected=4)
    winners = _extract_winners(qf)

    # Standard bracket: winner(QF1) vs winner(QF2), winner(QF3) vs winner(QF4)
    matchups = [(winners[0], winners[1]), (winners[2], winners[3])]

    with transaction.atomic():
        # Optional: prevent duplicate semifinals if called twice
        Match.objects.filter(group="Semifinali").delete()

        for home_id, away_id in matchups:
            Match.objects.create(
                stage="Eliminazione",
                group="Semifinali",
                home_team=Team.objects.get(id=home_id),
                away_team=Team.objects.get(id=away_id),
                date=dates.semi_day,
                time=time,
                validated=False,
                mvp=None,
            )

    return 2


def end_semifinals_and_create_finals(*, dates: KnockoutDates, time_finale: str = "21:00", time_3_4: str = "20:00") -> int:
    """
    Create final (1-2) and third-place (3-4) matches from validated semifinals.

    Preconditions:
    - Exactly 2 semifinal matches exist and are validated.
    - Each match must have a deterministic winner.
    """
    sf = _get_validated_round_matches(round_name="Semifinali", expected=2)

    winners = _extract_winners(sf)
    losers = _extract_losers(sf)

    with transaction.atomic():
        # Optional: prevent duplicates if called twice
        Match.objects.filter(group__in=["Finale 1-2", "Finale 3-4"]).delete()

        # Third place match
        Match.objects.create(
            stage="Eliminazione",
            group="Finale 3-4",
            home_team=Team.objects.get(id=losers[0]),
            away_team=Team.objects.get(id=losers[1]),
            date=dates.final_day,
            time=time_3_4,
            validated=False,
            mvp=None,
        )

        # Final match
        Match.objects.create(
            stage="Eliminazione",
            group="Finale 1-2",
            home_team=Team.objects.get(id=winners[0]),
            away_team=Team.objects.get(id=winners[1]),
            date=dates.final_day,
            time=time_finale,
            validated=False,
            mvp=None,
        )

    return 2


# -------------------------
# Internal helpers
# -------------------------

def _basic_quarterfinal_matchups(first: List[str], second: List[str]) -> List[Tuple[str, str]]:
    """Build quarterfinal matchups for 4 groups (A-D): A1-B2, B1-A2, C1-D2, D1-C2."""
    return [
        (first[0], second[1]),
        (first[1], second[0]),
        (first[2], second[3]),
        (first[3], second[2]),
    ]


def _ensure_group_stage_completed() -> None:
    """Ensure all group-stage matches are validated before closing the group stage."""
    total = Match.objects.filter(group__startswith="Gruppo").count()
    validated = Match.objects.filter(group__startswith="Gruppo", validated=True).count()
    if total == 0:
        raise ValueError("No group-stage matches found.")
    if validated != total:
        raise ValueError("Group stage is not completed: some matches are not validated yet.")


def _get_validated_round_matches(*, round_name: str, expected: int) -> List[Match]:
    """Load and validate a knockout round's matches."""
    matches = list(Match.objects.filter(group=round_name))
    if len(matches) != expected:
        raise ValueError(f"Expected {expected} matches for '{round_name}', found {len(matches)}.")
    not_valid = [m.id for m in matches if not m.validated]
    if not_valid:
        raise ValueError(f"Some '{round_name}' matches are not validated: {not_valid}")
    return matches


def _extract_winners(matches: List[Match]) -> List[int]:
    """Extract winners (Team IDs) from validated matches."""
    winners: List[int] = []
    for m in matches:
        if m.score_home_team == m.score_away_team:
            raise ValueError(f"Knockout match {m.id} is tied; set final score including DTS/DCR.")

        idx = get_winner_team_id(
            score_home=m.score_home_team,
            score_away=m.score_away_team,
        )

        winners.append(m.home_team_id if idx == 0 else m.away_team_id)

    return winners


def _extract_losers(matches: List[Match]) -> List[int]:
    """Extract losers (Team IDs) from validated matches."""
    losers: List[int] = []
    for m in matches:
        if m.score_home_team == m.score_away_team:
            raise ValueError(f"Knockout match {m.id} is tied; set final score including DTS/DCR.")
        
        idx = get_winner_team_id(
            score_home=m.score_home_team,
            score_away=m.score_away_team,
        )
        losers.append(m.away_team_id if idx == 0 else m.home_team_id)
    return losers
