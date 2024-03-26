from django.shortcuts import render, get_object_or_404, redirect
from .models import Match, Team, Group, MatchForm

import random
from django.db.models import Count, Sum, F, Case, When, IntegerField, F, Q, Value
from django.contrib.auth.decorators import login_required

from itertools import combinations
from collections import defaultdict 
from django.utils import timezone
from operator import itemgetter

def ranking(request):
    # Assuming 'groups' is your dict with group names as keys and lists of team stats as values
    groups

# Create your views here.
def home(request):
    return render(request, 'tournament/home.html')

def match_schedule(request):
    matches = Match.objects.all().order_by('date')  # Fetching all matches ordered by date
    return render(request, 'tournament/match_schedule.html', {'matches': matches})

def teams_and_playoffs(request):
    # Example: Fetch all teams (modify this logic to calculate group standings and playoff seeding)
    groups = calculate_group_standings()
    playoffs = determine_playoff_teams(groups)
    # Assume these functions return data structures that your template can iterate over
    context = {
        'groups': groups,
        'playoffs': playoffs,
    }
    return render(request, 'tournament/teams_and_playoffs.html', context)

# This is a placeholder function. You will need to implement the logic based on your models and data structure.
def calculate_group_standings():
    groups = {}  # A dictionary to hold standings for each group
    # Your logic to populate groups with team standings
    return groups

# This is a placeholder function. You will need to implement the logic based on your models and data structure.
def determine_playoff_teams(groups):
    playoff = {}  # A dictionary to hold standings for each group
    # Your logic to populate groups with team standings
    return playoff

def group_draw(request):
    if 'draw' in request.POST:
        # Perform draw for one random team
        unassigned_teams = Team.objects.filter(group__isnull=True)
        if unassigned_teams:
            team = random.choice(unassigned_teams)
            # Get groups with less than 4 teams
            groups = Group.objects.annotate(num_teams=Count('teams')).filter(num_teams__lt=4)
            if groups:
                group = random.choice(list(groups))
                team.group = group
                team.save()

    elif 'reset' in request.POST:
        # Reset all group-team assignments
        Team.objects.all().update(group=None)
    elif 'start_tournament' in request.POST:
        # Logic to initialize matches
        Match.objects.all().delete()
        groups = Group.objects.annotate(num_teams=Count('teams')).filter(num_teams__gt=1)
        for group in groups:
            teams = list(group.teams.all())
            # Create a match for every possible pairing if not already created
            for team1, team2 in combinations(teams, 2):
                Match.objects.get_or_create(
                    group=group,
                    team1=team1,
                    team2=team2,
                    #defaults={'score1': 0, 'score2': 0, 'date': None}  # Set a default date or modify as needed
                )
        
    # Teams without a group
    unassigned_teams = Team.objects.filter(group__isnull=True)
    # All groups (to display assigned teams under each group)
    groups = Group.objects.prefetch_related('teams').order_by('name').all()
    return render(request, 'tournament/group_draw.html', {'unassigned_teams': unassigned_teams, 'groups': groups})

def ranking(request):
    groups = defaultdict(list)
    all_teams = Team.objects.all()
    for team in all_teams:
        print(team.name)
        groups[team.group.name].append({
            'team_name': team.name,
            'points': 0,
            'goals_scored': 0,
            'goals_conceded': 0,
            'goal_difference': 0,
        })
    
    validated_matches = Match.objects.filter(validated=True)
    for match in validated_matches:
        # Determine points, goals scored, goals conceded, and goal difference from the match
        if match.score1 > match.score2:
            team1_points = 3
            team2_points = 0
        elif match.score1 < match.score2:
            team1_points = 0
            team2_points = 3
        else:
            team1_points = 1
            team2_points = 1

        team1_goal_difference = match.score1 - match.score2
        team2_goal_difference = match.score2 - match.score1

        # Update statistics for team1 and team2 in the groups dictionary
        for team_stats in groups[match.group]:
            if team_stats['team_name'] == match.team1.name:
                team_stats['points'] += team1_points
                team_stats['goals_scored'] += match.score1
                team_stats['goals_conceded'] += match.score2
                team_stats['goal_difference'] += team1_goal_difference
            elif team_stats['team_name'] == match.team2.name:
                team_stats['points'] += team2_points
                team_stats['goals_scored'] += match.score2
                team_stats['goals_conceded'] += match.score1
                team_stats['goal_difference'] += team2_goal_difference

            
    # Sort teams within each group
    sorted_groups = {}
    for group_name, teams in groups.items():
        sorted_teams = sorted(teams, key=lambda x: (-x['points'], -x['goal_difference'], -x['goals_scored'], x['team_name']))
        sorted_groups[group_name] = sorted_teams

    return render(request, 'tournament/ranking.html', {'groups': sorted_groups.items()})

@login_required
def edit_match(request, match_id):
    print(f"User: {request.user}, Authenticated: {request.user.is_authenticated}")
    match = get_object_or_404(Match, pk=match_id)
    if request.method == 'POST':
        form = MatchForm(request.POST, instance=match)
        if form.is_valid():
            form.save()
            # Redirect to matches list or detail view as appropriate
            return redirect('match_schedule')
    else:
        form = MatchForm(instance=match)
    return render(request, 'tournament/edit_match.html', {'form': form, 'match': match})