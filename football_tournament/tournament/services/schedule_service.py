# tournament/services/schedule_service.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable, List

from django.db import transaction

from tournament.models import Group, Match, Team
from tournament.domain.schedule_schema import (
    load_schedule_schema,
    build_slots,
    build_group_matches_from_schema,
)
from tournament.services.draw_service import validate_draw_completed_equal_groups

@dataclass(frozen=True)
class TournamentConfig:
    """
    A class that allows to set tournaments parameters
    """

    # TODO: read this from a config file 
    start_date: date
    match_times: tuple[str, ...] = ("20:30", "21:30", "22:30")
    valid_weekdays: tuple[int, ...] = (1, 2)  # Tue=1, Wed=2

def cleanup_matches() -> None:
    """
    A function to detete all the matches
    """
    Match.objects.all().delete()


def create_group_stage_schedule_from_csv(
    *,   # This means all the arguments must be passed as keywords arguments
    csv_path: str,
    config: TournamentConfig,
) -> int:
    """
    Creates group-stage matches based on CSV schema and current Group/Team assignments.
    Returns number of created matches.
    """

    status = validate_draw_completed_equal_groups()
    if not status.ok:
        raise ValueError(status.reason)

    schema = load_schedule_schema(csv_path)

    # groups -> ordered team names (ordered by name for deterministic positions)
    groups = Group.objects.prefetch_related("teams").all()
    group_teams = {
        g.name: [t.name for t in sorted(list(g.teams.all()), key=lambda x: x.name)]
        for g in groups
    }

    slots = build_slots(
        start_date=config.start_date,
        total_matches=len(schema),
        match_times=config.match_times,
        valid_weekdays=config.valid_weekdays,
    )

    schedule = build_group_matches_from_schema(
        schema=schema,
        group_teams=group_teams,
        slots=slots,
    )

    created = 0
    with transaction.atomic():
        for m in schedule:
            Match.objects.create(
                stage=m["stage"],
                group=m["group_name"],  # <-- Match.group è CharField oggi :contentReference[oaicite:1]{index=1}
                home_team=Team.objects.get(name=m["home_team_name"]),
                away_team=Team.objects.get(name=m["away_team_name"]),
                date=m["date"],
                time=m["time"],
                mvp=None,
            )
            created += 1

    return created
