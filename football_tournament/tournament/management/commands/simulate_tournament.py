from __future__ import annotations

import random

from django.core.management.base import BaseCommand

from tournament.config.tournament_schedule import KNOCKOUT_DATES
from tournament.models import Goal, Match
from tournament.services.knockout_service import (
    end_group_stage_and_create_quarterfinals,
    end_quarterfinals_and_create_semifinals,
    end_semifinals_and_create_finals,
)


def simulate_matches(matches, max_goals_per_player: int) -> None:
    for match in matches:
        home_players = list(match.home_team.players.all())[:3]
        away_players = list(match.away_team.players.all())[:3]
        all_players = home_players + away_players

        for player in all_players:
            goals = random.randint(0, max_goals_per_player)
            if goals > 0:
                Goal.objects.update_or_create(
                    match=match,
                    player=player,
                    defaults={"number_of_goals": goals},
                )

        if all_players:
            match.mvp = random.choice(all_players)

        total_home_goals = sum(
            goal.number_of_goals
            for goal in Goal.objects.filter(match=match, player__in=home_players)
        )
        total_away_goals = sum(
            goal.number_of_goals
            for goal in Goal.objects.filter(match=match, player__in=away_players)
        )

        if match.group in ["Quarti", "Semifinali"] or match.group.startswith("Finale"):
            if total_home_goals == total_away_goals:
                r = random.random()
                if r < 0.25:
                    total_home_goals += 1
                    match.dts = True
                elif 0.25 <= r < 0.5:
                    total_away_goals += 1
                    match.dts = True
                elif 0.5 <= r < 0.75:
                    total_home_goals += 1
                    match.dcr = True
                else:
                    total_away_goals += 1
                    match.dcr = True

        match.score_home_team = total_home_goals
        match.score_away_team = total_away_goals
        match.validated = True
        match.save()


class Command(BaseCommand):
    help = "Simulate the full tournament and advance knockout phases."

    def add_arguments(self, parser):
        parser.add_argument(
            "--max-goals-per-player",
            type=int,
            default=4,
            help="Maximum goals assigned to a player in a match.",
        )

    def handle(self, *args, **options):
        max_goals = options["max_goals_per_player"]

        Match.objects.filter(stage="Eliminazione").delete()

        matches = Match.objects.filter(stage="Gironi")
        simulate_matches(matches, max_goals_per_player=max_goals)
        end_group_stage_and_create_quarterfinals(dates=KNOCKOUT_DATES)

        matches = Match.objects.filter(group="Quarti")
        simulate_matches(matches, max_goals_per_player=max_goals)
        end_quarterfinals_and_create_semifinals(dates=KNOCKOUT_DATES)

        matches = Match.objects.filter(group="Semifinali")
        simulate_matches(matches, max_goals_per_player=max_goals)
        end_semifinals_and_create_finals(dates=KNOCKOUT_DATES)

        matches = Match.objects.filter(group__startswith="Finale")
        simulate_matches(matches, max_goals_per_player=max_goals)

        self.stdout.write(self.style.SUCCESS("Tournament simulation completed."))
