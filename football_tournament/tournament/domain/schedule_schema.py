# tournament/domain/schedule_schema.py
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable, List, Dict, Any


@dataclass(frozen=True)
class MatchDef:
    """
    Class that represents a match
    """
    group: str
    home_pos: int
    away_pos: int
    round: int


@dataclass(frozen=True)
class Slot:
    """
    Class that represents a time slot when a match can be played
    """
    date: date
    time: str

def load_schedule_schema(csv_path: str) -> List[MatchDef]:
    """
    This function creates a list of matches given a schema
    """
    schema: List[MatchDef] = []
    with open(csv_path, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            schema.append(
                MatchDef(
                    group=row["group"],
                    home_pos=int(row["home_pos"]),
                    away_pos=int(row["away_pos"]),
                    round=int(row["round"]),
                )
            )
    return schema

def build_slots(
    start_date: date,
    total_matches: int,
    match_times: Iterable[str],
    valid_weekdays: Iterable[int],
) -> List[Slot]:
    """
    This function creates a list of slots for all the matches in the tournament.
    valid_weekdays: Python weekday (Mon=0 ... Sun=6)
    """
    match_times = list(match_times)
    valid_weekdays = set(valid_weekdays)

    slots: List[Slot] = []
    current = start_date

    while len(slots) < total_matches:
        if current.weekday() in valid_weekdays:
            for t in match_times:
                slots.append(Slot(date=current, time=t))
                if len(slots) >= total_matches:
                    break
        current += timedelta(days=1)

    return slots

def build_group_matches_from_schema(
    schema: List[MatchDef],
    group_teams: Dict[str, List[str]],
    slots: List[Slot],
) -> List[Dict[str, Any]]:
    """
    This function create a list of dicts with all the matches for the group phase following the schema and the slots
    group_teams: {"Gruppo A": ["Team1", "Team2", ...]} ordered list.
    Returns list of dicts ready for DB create (strings only).
    """
    schedule: List[Dict[str, Any]] = []
    slot_index = 0

    for md in schema:
        teams = group_teams.get(md.group)
        if not teams:
            continue

        # positions in CSV are 1-based
        home = teams[md.home_pos - 1]
        away = teams[md.away_pos - 1]

        slot = slots[slot_index]
        schedule.append(
            {
                "group_name": md.group,
                "home_team_name": home,
                "away_team_name": away,
                "date": slot.date,
                "time": slot.time,
                "stage": "Gironi",
            }
        )
        slot_index += 1

    return schedule