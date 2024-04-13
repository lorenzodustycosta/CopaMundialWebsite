from django.shortcuts import render, get_object_or_404, redirect
from .models import Match, Team, Group, MatchForm, Player, TeamForm, PlayerForm, Goal, PlayerGoalsForm
from django.db.models import Prefetch
import random
from django.db.models import Count, Sum, F, Case, When, IntegerField, F, Q, Value
from django.contrib.auth.decorators import login_required
from django.forms import inlineformset_factory
from django.views.generic.edit import CreateView, DeleteView
from django.urls import reverse_lazy
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

def manage_matches(request):
    matches = Match.objects.all().order_by('date')  # Fetching all matches ordered by date
    return render(request, 'tournament/manage_matches.html', {'matches': matches})

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
            for home_team, away_team in combinations(teams, 2):
                Match.objects.get_or_create(
                    group=group,
                    home_team=home_team,
                    away_team=away_team,
                    #defaults={'score_home_team': 0, 'score_away_team': 0, 'date': None}  # Set a default date or modify as needed
                )
        
    # Teams without a group
    unassigned_teams = Team.objects.filter(group__isnull=True)
    # All groups (to display assigned teams under each group)
    groups = Group.objects.prefetch_related('teams').order_by('name').all()
    return render(request, 'tournament/group_draw.html', {'unassigned_teams': unassigned_teams, 'groups': groups})

def ranking(request):
    groups = defaultdict(list)
    all_teams = Team.objects.all()
    drawing_done = any(team.group for team in all_teams)
    
    if drawing_done: 
        for team in all_teams:
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
            if match.score_home_team > match.score_away_team:
                home_team_points = 3
                away_team_points = 0
            elif match.score_home_team < match.score_away_team:
                home_team_points = 0
                away_team_points = 3
            else:
                home_team_points = 1
                away_team_points = 1

            home_team_goal_difference = match.score_home_team - match.score_away_team
            away_team_goal_difference = match.score_away_team - match.score_home_team

            # Update statistics for home_team and away_team in the groups dictionary
            for team_stats in groups[match.group]:
                if team_stats['team_name'] == match.home_team.name:
                    team_stats['points'] += home_team_points
                    team_stats['goals_scored'] += match.score_home_team
                    team_stats['goals_conceded'] += match.score_away_team
                    team_stats['goal_difference'] += home_team_goal_difference
                elif team_stats['team_name'] == match.away_team.name:
                    team_stats['points'] += away_team_points
                    team_stats['goals_scored'] += match.score_away_team
                    team_stats['goals_conceded'] += match.score_home_team
                    team_stats['goal_difference'] += away_team_goal_difference

                
        # Sort teams within each group
        sorted_groups = {}
        for group_name, teams in sorted(groups.items()):
            sorted_teams = sorted(teams, key=lambda x: (-x['points'], -x['goal_difference'], -x['goals_scored'], x['team_name']))
            sorted_groups[group_name] = sorted_teams
            
        sorted_groups = sorted_groups.items()
        
    else:
        sorted_groups = None
        
    return render(request, 'tournament/ranking.html', {'groups': sorted_groups, 'drawing_done': drawing_done})
        
@login_required
def edit_match(request, match_id):
    match = get_object_or_404(Match, pk=match_id)
    if request.method == 'POST':
        match_form = MatchForm(request.POST, instance=match)
        home_goals_form = PlayerGoalsForm(request.POST, team=match.home_team)
        away_goals_form = PlayerGoalsForm(request.POST, team=match.away_team)
        if match_form.is_valid() and home_goals_form.is_valid() and away_goals_form.is_valid():
            match_form.save()
            # Logic to save goal data, including autogols
            return redirect('manage_matches')
    else:
        match_form = MatchForm(instance=match)
        home_goals_form = PlayerGoalsForm(team=match.home_team)
        away_goals_form = PlayerGoalsForm(team=match.away_team)

    return render(request, 'tournament/edit_match.html', {
        'match_form': match_form,
        'home_goals_form': home_goals_form,
        'away_goals_form': away_goals_form,
    })

def team_and_player_list(request):
    teams = Team.objects.prefetch_related('players').order_by('name')
    # Find the maximum number of players in any team to define the number of rows
    max_players = max([team.players.count() for team in teams]) if teams else 0

    # Create a list of lists, each sublist being a row of players in the position order across all teams
    player_rows = [[] for _ in range(max_players)]
    for team in teams:
        players = list(team.players.all())
        # Fill the rows with players or None if the team has fewer players
        for index in range(max_players):
            player_rows[index].append(players[index] if index < len(players) else None)

    return render(request, 'tournament/team_and_player_list.html', {'teams': teams, 'player_rows': player_rows})

@login_required
def team_list(request):
    teams = Team.objects.order_by('name')   
    return render(request, 'tournament/team_list.html', {'teams': teams})

@login_required
def create_or_update_team(request, pk=None):
    if pk:
        team = get_object_or_404(Team, pk=pk)  # Safely get the object or return 404
    else:
        team = None  # Define team as None if no pk is provided
    if request.method == 'POST':
        team_form = TeamForm(request.POST, instance=team)  # Bind form to POST data and instance
        PlayerFormSet = inlineformset_factory(Team, Player, form=PlayerForm, extra=10, can_delete=True)
        formset = PlayerFormSet(request.POST, instance=team)  # Bind formset to POST data and instance
        
        if team_form.is_valid() and formset.is_valid():
            created_team = team_form.save()  # Save the team and capture the instance
            formset.instance = created_team  # Ensure the formset instance is the newly created team
            formset.save()  # Save the formset data
            return redirect('manage_teams')  # Redirect to a page that lists all teams
        else:
            if not team_form.is_valid():
                print("Team Form Errors:", team_form.errors)
            if not formset.is_valid():
                print("Formset Errors:", formset.errors)
                
    else:
        team_form = TeamForm(instance=team)  # Unbound form for initial GET request
        PlayerFormSet = inlineformset_factory(Team, Player, form=PlayerForm, extra=10, can_delete=True)
        formset = PlayerFormSet(instance=team)  # Unbound formset for initial GET request

    return render(request, 'tournament/create_or_update_team.html', {
        'team_form': team_form,
        'formset': formset,
        'team': team
    })

class DeleteTeamView(DeleteView):
    model = Team
    template_name = 'tournament/delete_team.html'  # Name of the confirmation template
    success_url = reverse_lazy('manage_teams')  # Redirect URL after deletion

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cancel_url'] = reverse_lazy('manage_teams')
        return context