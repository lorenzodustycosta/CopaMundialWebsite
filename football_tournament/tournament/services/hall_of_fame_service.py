# tournament/services/hall_of_fame_service.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from django.db.models import Count, Sum
from django.db.models.functions import Coalesce

from tournament.domain.match_outcome import get_winner_loser_ids
from tournament.models import HallOfFame, Match, Player, Team

@dataclass(frozen=True)
class HallOfFameYear:
    """DTO for a single hall of fame year."""
    year: int
    first: Optional[str]
    second: Optional[str]
    third: Optional[str]
    top_scorer: Optional[str]
    mvp: Optional[str]
    best_gk: Optional[str]


@dataclass(frozen=True)
class HallOfFameData:
    """DTO for the hall of fame page context."""
    entries: List[HallOfFameYear]
    year: Optional[int]

def build_all_of_fame_data() -> HallOfFameData:
    """Build all data needed to render the ranking page."""
    hall_of_fame = HallOfFame.objects.all().order_by("-year", "title")
    entries_by_year: Dict[int, Dict[str, HallOfFame]] = {}
    for entry in hall_of_fame:
        entries_by_year.setdefault(entry.year, {})[entry.title] = entry

    entries: List[HallOfFameYear] = []
    for year in sorted(entries_by_year.keys(), reverse=True):
        by_title = entries_by_year[year]

        def team_value(title: str) -> Optional[str]:
            record = by_title.get(title)
            return record.display_team() if record else None

        def player_value(title: str) -> Optional[str]:
            record = by_title.get(title)
            return record.display_player() if record else None

        entries.append(
            HallOfFameYear(
                year=year,
                first=team_value(HallOfFame.TitleChoices.FIRST_PLACE),
                second=team_value(HallOfFame.TitleChoices.SECOND_PLACE),
                third=team_value(HallOfFame.TitleChoices.THIRD_PLACE),
                top_scorer=player_value(HallOfFame.TitleChoices.TOP_SCORER),
                mvp=player_value(HallOfFame.TitleChoices.MVP),
                best_gk=player_value(HallOfFame.TitleChoices.BEST_GK),
            )
        )

    return HallOfFameData(
        entries=entries,
        year=entries[0].year if entries else None,
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
            .order_by("-total_goals")[:10]
        )

    if not top_counts:
        return scorers.none()

    cutoff = top_counts[-1]

    scorers_to_display = scorers.filter(total_goals__gte=cutoff).order_by("-total_goals")
    
    if len(scorers_to_display)>20:
        scorers_to_display = scorers.order_by("-total_goals")[:20]



    return scorers_to_display

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

    return mvp_players.order_by("-mvp_count")[:20]

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
