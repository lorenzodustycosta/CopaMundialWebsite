# tournament/services/group_stage_service.py
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List

from tournament.domain.ranking import MatchResult, TeamStats, compute_group_tables, sort_group_table, pick_top_2_per_group
from tournament.models import Match, Group

from django.db.models import Prefetch


@dataclass(frozen=True)
class GroupStageOutcome:
    """Computed outcome of the group stage used by multiple features (ranking page, knockouts)."""
    group_notes: Dict[str, str]
    rankings: Dict[str, List[TeamStats]]
    first: List[TeamStats]
    second: List[TeamStats]


def compute_group_stage_outcome() -> GroupStageOutcome:
    """
    Compute group-stage standings for all groups.

    This function:
    - Loads all groups and their teams (so groups with zero matches still appear).
    - Loads validated group-stage matches from DB.
    - Builds MatchResult objects for domain ranking computation.
    - Produces per-group rankings and qualified teams (top-2 per group).
    """

    groups = (
            Group.objects
            .prefetch_related(Prefetch("teams"))
            .order_by("name")
            .all()
        )

    group_notes = {g.name: (g.note or "") for g in groups}

    validated = Match.objects.filter(validated=True, group__startswith="Gruppo")

    # Results containes the list of result of all matches of all groups
    results: List[MatchResult] = [
        MatchResult(
            group_name=m.group,
            home_team=m.home_team.name,
            away_team=m.away_team.name,
            home_goals=m.score_home_team,
            away_goals=m.score_away_team,
        )
        for m in validated
    ]

    tables = compute_group_tables(results)

    # Ensure every group/team exists with zero stats even if no matches are played yet.
    for g in groups:
        tables.setdefault(g.name, {})
        for t in g.teams.all():
            tables[g.name].setdefault(t.name, TeamStats(team_name=t.name))

    # Group results by group name so tie-breakers can use head-to-head within each group.
    group_results: Dict[str, List[MatchResult]] = defaultdict(list)
    for r in results:
        group_results[r.group_name].append(r)

    # Sort standings per group using points + head-to-head tie-breakers.
    rankings: Dict[str, List[TeamStats]] = {}
    for group_name, table in sorted(tables.items()):
        rankings[group_name] = sort_group_table(
            group_name=group_name,
            table=table,
            group_results=group_results.get(group_name, []),
        )

    first, second = pick_top_2_per_group(rankings)

    return GroupStageOutcome(
        group_notes=group_notes,
        rankings=rankings,
        first=first,
        second=second,
    )
