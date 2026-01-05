from __future__ import annotations

from dataclasses import dataclass
from collections import defaultdict
from typing import Dict, Iterable, List, Tuple


@dataclass(frozen=True)
class TeamStats:
    """Represents aggregated stats for a team within a group."""
    team_name: str
    points: int = 0
    goals_scored: int = 0
    goals_conceded: int = 0
    goal_difference: int = 0


@dataclass(frozen=True)
class MatchResult:
    """Represents a validated match result for ranking computation."""
    group_name: str
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int


def compute_rankings(results: List[MatchResult]) -> Dict[str, List[TeamStats]]:
    """Compute sorted standings per group."""
    tables = compute_group_tables(results)

    # Group results for head-to-head checks
    group_results: Dict[str, List[MatchResult]] = defaultdict(list)
    for r in results:
        group_results[r.group_name].append(r)

    rankings: Dict[str, List[TeamStats]] = {}
    for group_name, table in sorted(tables.items()):
        rankings[group_name] = sort_group_table(
            group_name=group_name,
            table=table,
            group_results=group_results.get(group_name, []),
        )
    return rankings

def compute_group_tables(results: List[MatchResult]) -> Dict[str, Dict[str, TeamStats]]:
    """Compute per-group team stats from match results."""

    grouped: Dict[str, List[MatchResult]] = defaultdict(list)
    for r in results:
        grouped[r.group_name].append(r)

    return {
        group: _accumulate_stats(results=group_results)
        for group, group_results in grouped.items()
    }

def sort_group_table(*, group_name: str, table: Dict[str, TeamStats], group_results: List[MatchResult]) -> List[TeamStats]:
    """Sort a group's table using basic criteria (points, goal difference, goals scored)."""

    stats = list(table.values())
    
    stats.sort(key=lambda s: (s.points, s.goal_difference, s.goals_scored, s.team_name), reverse=True)

    return _apply_head_to_head_tiebreak(stats, group_results)


def pick_top_2_per_group(rankings: Dict[str, List[TeamStats]]) -> Tuple[List[TeamStats], List[TeamStats]]:
    """Pick first and second placed teams from each group."""
    first: List[TeamStats] = []
    second: List[TeamStats] = []

    for _, table in rankings.items():
        if len(table) < 2:
            continue
        first.append(table[0])
        second.append(table[1])

    return first, second

def _accumulate_stats(
    *,
    results: List[MatchResult],
    teams: set[str] | None = None,
) -> Dict[str, TeamStats]:
    """
    Accumulate stats for the given matches.
    If `teams` is provided, only matches between those teams are considered.
    """
    table: Dict[str, TeamStats] = {}

    def ensure(team: str) -> None:
        if team not in table:
            table[team] = TeamStats(team_name=team)

    for r in results:
        if teams is not None:
            if r.home_team not in teams or r.away_team not in teams:
                continue

        ensure(r.home_team)
        ensure(r.away_team)

        if r.home_goals > r.away_goals:
            home_pts, away_pts = 3, 0
        elif r.home_goals < r.away_goals:
            home_pts, away_pts = 0, 3
        else:
            home_pts, away_pts = 1, 1

        home = table[r.home_team]
        away = table[r.away_team]

        home_gd = r.home_goals - r.away_goals
        away_gd = -home_gd

        table[r.home_team] = TeamStats(
            team_name=home.team_name,
            points=home.points + home_pts,
            goals_scored=home.goals_scored + r.home_goals,
            goals_conceded=home.goals_conceded + r.away_goals,
            goal_difference=home.goal_difference + home_gd,
        )
        table[r.away_team] = TeamStats(
            team_name=away.team_name,
            points=away.points + away_pts,
            goals_scored=away.goals_scored + r.away_goals,
            goals_conceded=away.goals_conceded + r.home_goals,
            goal_difference=away.goal_difference + away_gd,
        )

    return table

def _apply_head_to_head_tiebreak(
    sorted_stats: List[TeamStats],
    group_results: List[MatchResult],
) -> List[TeamStats]:
    """
    Apply head-to-head tie-breakers to teams with equal points.

    The input list is already sorted by overall criteria (points, goal difference, goals scored).
    This function refines that order by resolving ties using a mini-league
    (head-to-head matches) among teams with the same number of points.
    """

    out: List[TeamStats] = []
    i = 0
    # Iterate over the sorted list and process contiguous blocks of equal points
    while i < len(sorted_stats):
        j = i + 1
        while j < len(sorted_stats) and sorted_stats[j].points == sorted_stats[i].points:  # <-- retrieve teams with same points
            j += 1

        # Teams from index i to j-1 have the same number of points
        block = sorted_stats[i:j]

        # No tie to resolve if the block has a single team
        if len(block) <= 1:
            out.extend(block)
            i = j
            continue
        
        # Extract team names involved in this tie
        tied_names = {t.team_name for t in block}

        # Compute head-to-head statistics considering only matches between tied teams
        h2h = _compute_head_to_head_table(group_results, tied_names)


        # Re-sort the tied block using head-to-head criteria first,
        # then fall back to overall statistics for deterministic ordering
        block.sort(
            key=lambda s: (
                h2h.get(s.team_name, TeamStats(s.team_name)).points,
                h2h.get(s.team_name, TeamStats(s.team_name)).goal_difference,
                h2h.get(s.team_name, TeamStats(s.team_name)).goals_scored,
                s.goal_difference,
                s.goals_scored,
                s.team_name,
            ),
            reverse=True,
        )
        
        # Append the resolved block to the final output
        out.extend(block)
        i = j

    return out

def _compute_head_to_head_table(
    group_results: Iterable[MatchResult],
    tied_teams: set[str],
) -> Dict[str, TeamStats]:
    """Compute head-to-head stats among tied teams."""
    return _accumulate_stats(
        results=list(group_results),
        teams=tied_teams,
    ) 

