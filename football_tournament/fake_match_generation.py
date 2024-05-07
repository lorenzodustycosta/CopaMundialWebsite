import os
import django
import random

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'football_tournament.settings')
django.setup()

# Now we can safely import and use Django models
from tournament.models import Match, Team, Player, Goal

matches = Match.objects.all()

max_goals_per_player = 4

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
            print(f"  - {player.name} scored {goals} goals.")

    # Randomly choose an MVP from all players
    if all_players:
        mvp = random.choice(all_players)
        match.mvp = mvp  # Set the MVP for the match
        print(f"MVP of the match: {mvp.name}")
    else:
        print("No players available to choose an MVP from.")

    # Optionally, calculate and print total goals
    total_home_goals = sum(goal.number_of_goals for goal in Goal.objects.filter(match=match, player__in=home_players))
    total_away_goals = sum(goal.number_of_goals for goal in Goal.objects.filter(match=match, player__in=away_players))
    
    match.score_home_team = total_home_goals
    match.score_away_team = total_away_goals
    match.validated = True
    
    match.save()  # Save the match to update the MVP
            
    print(f"Total goals for {match.home_team.name}: {total_home_goals}")
    print(f"Total goals for {match.away_team.name}: {total_away_goals}")

    print()  # Adds a newline for better separation between match details
