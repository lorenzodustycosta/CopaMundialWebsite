# tournament/services/ranking_service.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from django.db.models import Count, Sum
from django.db.models.functions import Coalesce

from tournament.domain.knockout import get_winner_team_id
from tournament.domain.ranking import TeamStats
from tournament.models import Match, Player, Team

from .group_stage_service import compute_group_stage_outcome
from .knockout_view_service import get_knockout_matches
from tournament.domain.match_outcome import get_winner_loser_ids

@dataclass(frozen=True)
class RankingPageData:
    """DTO for the ranking page context."""
    drawing_done: bool
    rankings: Optional[Dict[str, List[TeamStats]]]
    top_scorers: object
    mvp_ranking: object
    qualified_team_names: List[str]
    group_notes: str
    winners: List = field(default_factory=list)
    quarterfinals_matches: List[Match] = field(default_factory=list)
    semifinals_matches: List[Match] = field(default_factory=list)
    finals_matches: List[Match] = field(default_factory=list)

def build_ranking_page_data() -> RankingPageData:
    """Build all data needed to render the ranking page."""
    all_teams = Team.objects.all()
    drawing_done = any(t.group_id for t in all_teams)

    outcome = compute_group_stage_outcome()
    qualified_team_names = [t.team_name for t in (outcome.first + outcome.second)]

    knockout = get_knockout_matches()

    return RankingPageData(
        drawing_done=drawing_done,
        rankings=outcome.rankings,
        group_notes=outcome.group_notes,
        qualified_team_names=qualified_team_names,
        top_scorers=_get_top_scorers(),
        mvp_ranking=_get_mvp_ranking(),
        winners=_get_winners(knockout.finals),
        quarterfinals_matches=knockout.quarterfinals,
        semifinals_matches=knockout.semifinals,
        finals_matches=knockout.finals,
    )    
    
def _get_top_scorers():
    """Return a queryset of top scorers (including ties at the cutoff)."""
    scorers = (
        Player.objects.annotate(total_goals=Coalesce(Sum("goal__number_of_goals"), 0))
        .filter(total_goals__gt=0, is_fake=False)
    )

    top_counts = list(
            scorers.values_list("total_goals", flat=True)
            .distinct()
            .order_by("-total_goals")[:3]
        )

    if not top_counts:
        return scorers.none()

    cutoff = top_counts[-1]

    return scorers.filter(total_goals__gte=cutoff).order_by("-total_goals")

def _get_mvp_ranking():
    """Return a queryset of MVP ranking (including ties at the cutoff)."""
    mvp_players = Player.objects.annotate(mvp_count=Count("mvp_matches")).filter(mvp_count__gt=0)

    top_counts = list(
        mvp_players.values_list("mvp_count", flat=True)
        .distinct()
        .order_by("-mvp_count")[:5]
    )

    if not top_counts:
        return mvp_players.none()

    cutoff = top_counts[-1]
    return mvp_players.filter(mvp_count__gte=cutoff).order_by("-mvp_count")

def _get_winners(finals: List[Match]) -> List[Team]:
    """
    Return the podium teams in order: [1st, 2nd, 3rd].

    Preconditions:
    - A validated "Finale 1-2" match must exist.
    - A validated "Finale 3-4" match must exist.
    - Winner/loser extraction must be deterministic for those matches.
    """
    final_3_4 = next((m for m in finals if m.group == "Finale 3-4"), None)
    final_1_2 = next((m for m in finals if m.group == "Finale 1-2"), None)

    if final_3_4 is None or final_1_2 is None:
        return []

    if not final_3_4.validated or not final_1_2.validated:
        return []

    final_3_4_ids = get_winner_loser_ids(final_3_4)
    final_1_2_ids = get_winner_loser_ids(final_1_2)

    third_id = final_3_4_ids.winner_id
    second_id = final_1_2_ids.loser_id
    first_id = final_1_2_ids.winner_id

    teams_by_id = Team.objects.in_bulk([first_id, second_id, third_id])

    # Defensive: if anything is missing from DB, return empty podium rather than crashing the page.
    if first_id not in teams_by_id or second_id not in teams_by_id or third_id not in teams_by_id:
        return []

    return [teams_by_id[first_id], teams_by_id[second_id], teams_by_id[third_id]]