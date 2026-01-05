# tournament/services/knockout_view_service.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from tournament.models import Match


@dataclass(frozen=True)
class KnockoutMatchesDTO:
    """DTO containing knockout matches grouped by round for template rendering."""
    quarterfinals: List[Match]
    semifinals: List[Match]
    finals: List[Match]  # includes both "Finale 3-4" and "Finale 1-2" when available


def get_knockout_matches() -> KnockoutMatchesDTO:
    """Load knockout matches grouped by round, ordered by date/time for consistent rendering."""
    quarterfinals = list(
        Match.objects.filter(stage="Eliminazione", group="Quarti").order_by("date", "time", "id")
    )
    semifinals = list(
        Match.objects.filter(stage="Eliminazione", group="Semifinali").order_by("date", "time", "id")
    )
    finals = list(
        Match.objects.filter(stage="Eliminazione", group__in=["Finale 3-4", "Finale 1-2"])
        .order_by("date", "time", "group", "id")
    )

    return KnockoutMatchesDTO(
        quarterfinals=quarterfinals,
        semifinals=semifinals,
        finals=finals,
    )
