import os
import django
import random

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'football_tournament.settings')
django.setup()

# Now we can safely import and use Django models
from tournament.models import Match, Team, Player, Goal
from tournament.views import end_group, end_quarterfinals, end_semifinals, end_finals

def simulate_matches(matches, max_goals_per_player=4):
    for match in matches:
        print("Match:", match)
        home_players = list(match.home_team.players.all())
        away_players = list(match.away_team.players.all())
        all_players = home_players + away_players  # Combine lists of players from both teams

        # Assign goals for each player as previously described
        for player in all_players:
            goals = random.randint(0, max_goals_per_player)
            if goals>0:
                goal_obj, created = Goal.objects.update_or_create(
                    match=match,
                    player=player,
                    defaults={'number_of_goals': goals}
                )

        # Randomly choose an MVP from all players
        if all_players:
            mvp = random.choice(all_players)
            match.mvp = mvp  # Set the MVP for the match

        # Optionally, calculate and print total goals
        total_home_goals = sum(goal.number_of_goals for goal in Goal.objects.filter(match=match, player__in=home_players))
        total_away_goals = sum(goal.number_of_goals for goal in Goal.objects.filter(match=match, player__in=away_players))
        
        match.score_home_team = total_home_goals
        match.score_away_team = total_away_goals
        match.validated = True
        
        match.save()  # Save the match to update the MVP

matches = Match.objects.all()
simulate_matches(matches)
end_group(request=None)

matches = Match.objects.filter(group='Quarti')
simulate_matches(matches)
end_quarterfinals(request=None)

matches = Match.objects.filter(group='Semifinali')
simulate_matches(matches)
end_semifinals(request=None)

matches = Match.objects.filter(group__startswith='Finale')
simulate_matches(matches)
end_finals(request=None)
