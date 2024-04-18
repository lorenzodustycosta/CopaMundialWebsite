from django.shortcuts import render, get_object_or_404, redirect
from .models import Match, Team, Group, MatchForm, Player, TeamForm, PlayerForm, Goal, PlayerGoalsForm
from django.db.models import Prefetch, Count
import random
from django.db.models import Count, Sum, F, Case, When, IntegerField, F, Q, Value
from django.db.models.functions import Coalesce
from django.contrib.auth.decorators import login_required
from django.forms import inlineformset_factory
from django.views.generic.edit import CreateView, DeleteView
from django.urls import reverse_lazy
from itertools import combinations, cycle
from collections import defaultdict 
from django.utils import timezone
from operator import itemgetter
from datetime import date, timedelta
import datetime
from django.db import transaction

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
        with transaction.atomic():
            cleanup_matches()
            start_date = date(2024, 6, 4)
            all_groups = Group.objects.all()
            tournament_schedule = create_tournament_schedule(start_date, all_groups)
            tournament_schedule = adjust_for_special_team(tournament_schedule)
            
            for group_name, matches in tournament_schedule.items():
                    for match_info in matches:
                        Match.objects.create(
                            group=Group.objects.get(name=group_name),
                            home_team=Team.objects.get(name=match_info['home_team']),
                            away_team=Team.objects.get(name=match_info['away_team']),
                            date=match_info['date'],
                            time=match_info['time'],
                            pitch=match_info['pitch'],
                        )
                            
    # Teams without a group
    unassigned_teams = Team.objects.filter(group__isnull=True)
    # All groups (to display assigned teams under each group)
    groups = Group.objects.prefetch_related('teams').order_by('name').all()
    return render(request, 'tournament/group_draw.html', {'unassigned_teams': unassigned_teams, 'groups': groups})

def adjust_for_special_team(tournament_schedule, special_team_name='Sottomarini Gialli'):
    for group_name, matches in tournament_schedule.items():
        for match_info in matches:
            # Check if the special team is playing in this match
            if match_info['home_team'] == special_team_name or match_info['away_team'] == special_team_name:
                # Assign the special team to the Green pitch
                match_info['pitch'] = 'Green'

                # Find the match at the same time that is not the special team's match
                for other_match_info in matches:
                    if (other_match_info['date'] == match_info['date'] and
                        other_match_info['time'] == match_info['time'] and
                        other_match_info is not match_info):
                        # Assign the other match to the Blue pitch
                        other_match_info['pitch'] = 'Blu'
    return tournament_schedule

def cleanup_matches():
    # Assuming `Match` has related objects that need to be cleared as well
    # This will delete all matches and any related objects via cascade deletion
    Match.objects.all().delete()
    
def create_tournament_schedule(start_date, groups):
    schedule = {}
    match_days = [1, 2]  # 1 for Tuesday, 2 for Wednesday
    match_times = cycle(['21:00', '22:00'])  # Cycle through match times for each match day
    pitches = ['Blu', 'Green']  # Available pitches
    current_date = start_date

    # Ensure start_date is a Tuesday
    while current_date.weekday() != match_days[0]:
        current_date += timedelta(days=1)

    # Loop through the groups and create a round-robin schedule for each
    for group in groups:
        rounds = round_robin(list(group.teams.all()))
        for round_num, round_matches in enumerate(rounds):
            # Determine the match day (Tuesday or Wednesday) and time slots
            day_matches_count = 0
            for match in round_matches:
                # Schedule matches for Tuesday first, then Wednesday
                if day_matches_count == 4:
                    # If it's already Wednesday, move to next week's Tuesday
                    if current_date.weekday() == match_days[1]:
                        current_date += timedelta(days=6)
                    else:  # Otherwise, just move to the next day (Wednesday)
                        current_date += timedelta(days=1)
                    day_matches_count = 0

                time_slot = next(match_times)  # Get the next available time slot
                pitch = pitches[day_matches_count % len(pitches)]  # Alternate between pitches

                # Create match entry if not a dummy team
                if match[0] is not None and match[1] is not None:
                    schedule.setdefault(group.name, []).append({
                        'date': current_date,
                        'home_team': match[0].name,
                        'away_team': match[1].name,
                        'time': time_slot,
                        'pitch': pitch
                    })
                    day_matches_count += 1

            # After scheduling a round (2 matches per group), move to the next week
            if current_date.weekday() == match_days[1]:
                current_date += timedelta(days=6)
            else:  # It's a Tuesday, move to the next day (Wednesday)
                current_date += timedelta(days=1)

    return schedule

def round_robin(teams):
    """Generates a round-robin schedule for a list of teams."""
    schedule = []
    if len(teams) % 2:
        teams.append(None)  # If odd number of teams, add a dummy team for bye weeks

    for i in range(len(teams) - 1):
        round_matches = []
        for j in range(len(teams) // 2):
            if teams[j] is not None and teams[-j - 1] is not None:
                round_matches.append((teams[j], teams[-j - 1]))
        teams.insert(1, teams.pop())  # Rotate the list of teams
        schedule.append(round_matches)
    return schedule

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
        
    top_scorers = Player.objects.annotate(
        total_goals=Coalesce(Sum('goals__number_of_goals'), 0)
    ).filter(
        total_goals__gt=0  # This filters out players with 0 goals
    ).order_by('-total_goals')[:10]
        
    return render(request, 'tournament/ranking.html', {'groups': sorted_groups, 'drawing_done': drawing_done, 'top_scorers': top_scorers,})
        
@login_required
def edit_match(request, match_id):
    match = get_object_or_404(Match, pk=match_id)
    if request.method == 'POST':
        match_form = MatchForm(request.POST, instance=match)
        home_goals_form = PlayerGoalsForm(request.POST, team=match.home_team, match=match)
        away_goals_form = PlayerGoalsForm(request.POST, team=match.away_team, match=match)
        
        if match_form.is_valid() and home_goals_form.is_valid() and away_goals_form.is_valid():
            updated_match = match_form.save()
            save_goals(home_goals_form, match, match.home_team)
            save_goals(away_goals_form, match, match.away_team)
            return redirect('manage_matches')

    else:
        match_form = MatchForm(instance=match)
        home_goals_form = PlayerGoalsForm(request.POST or None, team=match.home_team, match=match)
        away_goals_form = PlayerGoalsForm(request.POST or None, team=match.away_team, match=match)

    return render(request, 'tournament/edit_match.html', {
        'match_form': match_form,
        'home_goals_form': home_goals_form,
        'away_goals_form': away_goals_form,
    })

def save_goals(form, match, team):
    for field_name, value in form.cleaned_data.items():
        if value:  # Make sure there is a value to save
            player_id = int(field_name.split('_')[1])
            player = Player.objects.get(id=player_id)
            Goal.objects.update_or_create(
                match=match,
                player=player,
                defaults={'number_of_goals': value}
            )
            
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


# Assuming you have models named Match, Goal, and Team
def match_detail(request, match_id):
    match = get_object_or_404(Match, id=match_id)
    # Assuming that Goal has a 'player' ForeignKey and 'team' ForeignKey
    home_goals = Goal.objects.filter(match=match, player__team=match.home_team).select_related('player').annotate(total_goals=Sum('number_of_goals')).order_by('-total_goals')
    away_goals = Goal.objects.filter(match=match, player__team=match.away_team).select_related('player').annotate(total_goals=Sum('number_of_goals')).order_by('-total_goals')

    return render(request, 'tournament/match_detail.html', {
        'match': match,
        'home_goals': home_goals,
        'away_goals': away_goals
    })
