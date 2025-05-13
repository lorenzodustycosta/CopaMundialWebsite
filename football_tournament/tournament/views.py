from django.shortcuts import render, get_object_or_404, redirect
from .models import Match, Team, Group, MatchForm, Player, TeamForm, PlayerForm, Goal, PlayerGoalsForm, Document
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
import random
from django.http import HttpResponse
import os
from pathlib import Path
import csv

def home(request):
    return render(request, 'tournament/home.html')


def match_schedule(request):
    # Fetching all matches ordered by date
    matches = Match.objects.all().order_by('date', 'time')
    return render(request, 'tournament/match_schedule.html', {'matches': matches})


def manage_matches(request):
    # Fetching all matches ordered by date
    matches = Match.objects.all().order_by('date', 'time')

    group_matches = matches.filter(group__startswith='Gruppo')
    if group_matches.count() > 0:
        group_all_validated = group_matches.filter(
            validated=False).count() == 0
    else:
        group_all_validated = False

    quarterfinals_matches = matches.filter(group='Quarti')
    if quarterfinals_matches.count() > 0:
        quarterfinals_all_validated = quarterfinals_matches.filter(
            validated=False).count() == 0
    else:
        quarterfinals_all_validated = False

    semifinals_matches = matches.filter(group='Semifinali')
    if semifinals_matches.count() > 0:
        semifinals_all_validated = semifinals_matches.filter(
            validated=False).count() == 0
    else:
        semifinals_all_validated = False

    finals_matches = matches.filter(group__startswith='Finale')
    if finals_matches.count() > 0:
        finals_all_validated = finals_matches.filter(
            validated=False).count() == 0
    else:
        finals_all_validated = False

    context = {
        'group_all_validated': group_all_validated,
        'quarterfinals_all_validated': quarterfinals_all_validated,
        'semifinals_all_validated': semifinals_all_validated,
        'finals_all_validated': finals_all_validated
    }

    return render(request, 'tournament/manage_matches.html', {'matches': matches, 'context': context})


def end_quarterfinals(request):
    all_matches = Match.objects.filter(validated=True, group='Quarti')
    winners = []
    for m in all_matches:
        if m.score_home_team > m.score_away_team:
            winners.append(m.home_team)
        else:
            winners.append(m.away_team)

    Match.objects.create(
        stage='Eliminazione',
        group='Semifinali',
        home_team=winners[0],
        away_team=winners[1],
        date=date(2025, 7, 8),
        pitch='Blu',
        time='20:30',

    )

    Match.objects.create(
        stage='Eliminazione',
        group='Semifinali',
        home_team=winners[2],
        away_team=winners[3],
        date=date(2025, 7, 8),
        pitch='Blu',
        time='21:30',
    )

    return redirect('manage_matches')


def end_semifinals(request):
    all_matches = Match.objects.filter(validated=True, group='Semifinali')
    winners = []
    loosers = []
    for m in all_matches:
        if m.score_home_team > m.score_away_team:
            winners.append(m.home_team)
            loosers.append(m.away_team)
        else:
            winners.append(m.away_team)
            loosers.append(m.home_team)
    
    Match.objects.create(
        stage='Eliminazione',
        group='Finale 3-4',
        home_team=loosers[0],
        away_team=loosers[1],
        date=date(2025, 7, 11),
        pitch='Blu',
        time='20:30',
    )
    
    Match.objects.create(
        stage='Eliminazione',
        group='Finale 1-2',
        home_team=winners[0],
        away_team=winners[1],
        date=date(2025, 7, 11),
        pitch='Blu',
        time='21:30',
    )
           
    matches = Match.objects.all().order_by('date')
    return render(request, 'tournament/manage_matches.html', {'matches': matches})


def end_finals(request):      
    matches = Match.objects.all().order_by('date')
    return render(request, 'tournament/manage_matches.html', {'matches': matches})


def end_group(request):

    all_teams = Team.objects.all()
    sorted_groups = compute_ranking(all_teams)
    # first_place_teams, second_place_teams, qualified_third_place_teams = get_knockout_teams(
    #     sorted_groups)
    first_place_teams, second_place_teams = get_knockout_teams(
        sorted_groups)

    # matchups = create_quarterfinals_matchups(
    #     first_place_teams, second_place_teams, qualified_third_place_teams)

    matchups = create_quarterfinals_matchups(first_place_teams, second_place_teams)
    
    time = cycle(['20:30', '21:30'])

    for i, teams in enumerate(matchups):
        Match.objects.create(
            stage='Eliminazione',
            group='Quarti',
            home_team=Team.objects.get(name=teams[0]['team_name']),
            away_team=Team.objects.get(name=teams[1]['team_name']),
            date=date(2025, 7, 1) if i <= 1 else date(2025, 7, 2),
            pitch='Blu',
            time=next(time),

        )

    matches = Match.objects.all().order_by('date')

    return redirect('manage_matches')


# def create_quarterfinals_matchups(first_place_teams, second_place_teams, qualified_third_place_teams):

#     matchups = []

#     matchups.append([first_place_teams[0], qualified_third_place_teams[1]])
#     matchups.append([second_place_teams[0], second_place_teams[1]])
#     matchups.append([first_place_teams[2], second_place_teams[2]])
#     matchups.append([first_place_teams[1], qualified_third_place_teams[0]])

#     return matchups

def create_quarterfinals_matchups(first_place_teams, second_place_teams):

    matchups = []

    matchups.append([first_place_teams[0], second_place_teams[1]])
    matchups.append([first_place_teams[1], second_place_teams[0]])
    matchups.append([first_place_teams[2], second_place_teams[3]])
    matchups.append([first_place_teams[3], second_place_teams[2]])

    return matchups



def get_knockout_teams(sorted_groups):
    first_place_teams = []
    second_place_teams = []
    third_place_teams = []

    # Iterate over each group and their teams, already sorted by standings
    for group_name, teams in sorted_groups.items():
        first_place_teams.append(teams[0])
        second_place_teams.append(teams[1])
        third_place_teams.append(teams[2])

    # first_place_teams = sorted(
    #     first_place_teams,
    #     key=lambda x: (x['points'], x['goal_difference'], x['goals_scored']),
    #     reverse=True
    # )

    # second_place_teams = sorted(
    #     second_place_teams,
    #     key=lambda x: (x['points'], x['goal_difference'], x['goals_scored']),
    #     reverse=True
    # )

    # Sort the third place teams based on the criteria and select the top two
    # qualified_third_place_teams = sorted(
    #     third_place_teams,
    #     key=lambda x: (x['points'], x['goal_difference'], x['goals_scored']),
    #     reverse=True
    # )[:2]

    return first_place_teams, second_place_teams #qualified_third_place_teams


def load_schedule_schema(path='scheduling_schema.csv'):
    schema = []
    with open(path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            schema.append({
                'group': row['group'],
                'home_pos': int(row['home_pos']),
                'away_pos': int(row['away_pos']),
                'round': int(row['round'])
            })
    return schema

def create_schedule_from_schema(start_date, groups_queryset, schema):
    # Orari fissi e giorni validi (Martedì = 1, Mercoledì = 2)
    match_times = ['20:30', '21:30', '22:30']
    valid_weekdays = [1, 2]

    # Mapping dei gruppi → lista di squadre ordinate per nome
    group_dict = {
        group.name: sorted(list(group.teams.all()), key=lambda t: t.name)
        for group in groups_queryset
    }

    # Costruzione di tutti gli slot disponibili, uno per partita
    slots = []
    current_date = start_date
    total_matches = len(schema)

    while len(slots) < total_matches:
        if current_date.weekday() in valid_weekdays:
            for t in match_times:
                slots.append({
                    'date': current_date,
                    'time': t,
                    'day_label': 'Mar' if current_date.weekday() == 1 else 'Mer'
                })
        current_date += timedelta(days=1)

    # Assegnazione degli slot
    schedule = []
    slot_index = 0

    for match_def in schema:
        group_name = match_def['group']
        round_number = int(match_def['round'])

        if group_name not in group_dict:
            continue

        teams = group_dict[group_name]
        home_team = teams[int(match_def['home_pos']) - 1]
        away_team = teams[int(match_def['away_pos']) - 1]

        slot = slots[slot_index]
        schedule.append({
            'group': group_name,
            'home_team': home_team.name,
            'away_team': away_team.name,
            'date': slot['date'],
            'time': slot['time'],
            'pitch': 'Blu'
        })

        slot_index += 1

    return schedule

def group_draw(request):
    last_picked_team_id = None  # Initialize variable to store the ID of the last picked team

    if 'draw' in request.POST:
        unassigned_teams = Team.objects.filter(group__isnull=True)
        if unassigned_teams:
            team = random.choice(list(unassigned_teams))
            groups = Group.objects.annotate(
                num_teams=Count('teams')).filter(num_teams__lt=4)
            if groups:
                group = random.choice(list(groups))
                team.group = group
                team.save()
                last_picked_team_id = team.id  # Store the last picked team's ID

    elif 'reset' in request.POST:
        Team.objects.all().update(group=None)

    elif 'start_tournament' in request.POST:
        with transaction.atomic():
            BASE_DIR = Path(__file__).resolve().parent.parent
            schema_path = os.path.join(BASE_DIR, 'schedules', 'scheduling_schema.csv')
            schema = load_schedule_schema(path=schema_path)

            # Assume cleanup_matches() and create_tournament_schedule() are defined elsewhere
            cleanup_matches()
            start_date = date(2025, 6, 3)
            all_groups = Group.objects.all()
            tournament_schedule = create_schedule_from_schema(start_date, all_groups, schema)

            print(tournament_schedule)

            for match_info in tournament_schedule:
                group = get_object_or_404(Group, name=match_info['group'])
                Match.objects.create(
                    group=group,
                    home_team=Team.objects.get(name=match_info['home_team']),
                    away_team=Team.objects.get(name=match_info['away_team']),
                    date=match_info['date'],
                    time=match_info['time'],
                    pitch=match_info['pitch'],
                    mvp=None
                )

    unassigned_teams = Team.objects.filter(group__isnull=True)
    groups = Group.objects.prefetch_related('teams').order_by('name').all()
    return render(request, 'tournament/group_draw.html', {
        'unassigned_teams': unassigned_teams,
        'groups': groups,
        'last_picked_team_id': last_picked_team_id  # Pass the last picked team's ID to the template
    })


def cleanup_matches():
    # Assuming `Match` has related objects that need to be cleared as well
    # This will delete all matches and any related objects via cascade deletion
    Match.objects.all().delete()


def create_tournament_schedule(start_date, groups_queryset):
    # Initialize a list for all matches across all groups
    all_matches = []

    match_times = cycle(['20:30','21:30','22:30'])
    
    # Generate round-robin schedules for each group
    for group in groups_queryset:
        rounds = round_robin(list(group.teams.all()))
        for round_number, round_matches in enumerate(rounds):
            for match in round_matches:
                all_matches.append({
                    'round_number': round_number,
                    'group': group.name,
                    'home_team': match[0].name if match[0] else None,
                    'away_team': match[1].name if match[1] else None
                })

    # Sort the matches by round number
    random.shuffle(all_matches)
    all_matches.sort(key=lambda x: x['round_number'])

    # Initialize the final sorted schedule
    sorted_schedule = []

    # Assign match dates, times, and pitches
    current_date = start_date
    for i, match in enumerate(all_matches):
        if i % 6 < 3:  # First four matches on Tuesday
            if i % 6 == 0:  # Reset to the next Tuesday every 6 matches
                current_date += timedelta(days=7 - current_date.weekday() +
                                                1) if i != 0 else timedelta(0)
        else:  # Remaining two matches on Wednesday
            if i % 6 == 3:  # Move to Wednesday after the first four matches
                current_date += timedelta(days=1)
        
        print(f"{i} {current_date} {match['home_team']} - {match['away_team']}")

        match_time = next(match_times)
        sorted_schedule.append({
            'date': current_date,
            'group': match['group'],
            'home_team': match['home_team'],
            'away_team': match['away_team'],
            'time': match_time,
            'pitch': 'Blu'
        })

    return sorted_schedule


def round_robin(teams):
    """Generates a round-robin schedule for an even list of teams."""
    # If the number of teams is odd, add a dummy team for byes
    if len(teams) % 2:
        teams.append(None)

    num_days = len(teams) - 1  # Days needed to complete the round-robin
    half_size = len(teams) // 2

    schedule = []
    teams = list(teams)  # Copy teams to mutable list
    for day in range(num_days):
        day_matches = []
        for i in range(half_size):
            if teams[i] is not None and teams[-i - 1] is not None:  # Skip byes
                day_matches.append((teams[i], teams[-i - 1]))
        teams.insert(1, teams.pop())  # Rotate the list of teams

        schedule.append(day_matches)

    return schedule


def compute_ranking(all_teams):
    # Initialize groups with a dictionary to hold team data by team name.
    groups = defaultdict(dict)

    # Initialize team data structure.
    for team in all_teams:
        if team.group:  # Make sure the team is assigned to a group
            groups[team.group.name][team.name] = {
                'team_name': team.name,
                'points': 0,
                'goals_scored': 0,
                'goals_conceded': 0,
                'goal_difference': 0,
                'head_to_head_points': defaultdict(int),  # For head-to-head points
                'head_to_head_goal_difference': defaultdict(int)  # For head-to-head goal difference
            }

    # Fetch matches grouped by group name
    for group_name, teams_info in groups.items():
        validated_matches = Match.objects.filter(validated=True, group=group_name)

        for match in validated_matches:
            home_team = match.home_team.name
            away_team = match.away_team.name

            # Calculate points and goal differences
            if match.score_home_team > match.score_away_team:
                home_points, away_points = 3, 0
            elif match.score_home_team < match.score_away_team:
                home_points, away_points = 0, 3
            else:
                home_points, away_points = 1, 1

            home_goal_diff = match.score_home_team - match.score_away_team
            away_goal_diff = match.score_away_team - match.score_home_team

            # Update team statistics
            teams_info[home_team]['points'] += home_points
            teams_info[home_team]['goals_scored'] += match.score_home_team
            teams_info[home_team]['goals_conceded'] += match.score_away_team
            teams_info[home_team]['goal_difference'] += home_goal_diff

            teams_info[away_team]['points'] += away_points
            teams_info[away_team]['goals_scored'] += match.score_away_team
            teams_info[away_team]['goals_conceded'] += match.score_home_team
            teams_info[away_team]['goal_difference'] += away_goal_diff

            # Update head-to-head statistics
            teams_info[home_team]['head_to_head_points'][away_team] += home_points
            teams_info[home_team]['head_to_head_goal_difference'][away_team] += home_goal_diff

            teams_info[away_team]['head_to_head_points'][home_team] += away_points
            teams_info[away_team]['head_to_head_goal_difference'][home_team] += away_goal_diff

    # Function to calculate the sorting key for a given team
    def sort_key(team, teams_info):
        return (
            -teams_info[team]['points'],
            -teams_info[team]['goal_difference'],
            -teams_info[team]['goals_scored'],
            team
        )

    # Sort teams within each group with additional head-to-head comparison for tiebreakers
    sorted_groups = {}
    for group_name, team_stats in sorted(groups.items()):
        teams = list(team_stats.keys())

        # Initial sorting based on primary criteria
        sorted_teams = sorted(teams, key=lambda team: sort_key(team, team_stats))

        # Adjust sorting for teams with equal points based on head-to-head results
        i = 0
        while i < len(sorted_teams) - 1:
            j = i + 1
            while j < len(sorted_teams) and team_stats[sorted_teams[i]]['points'] == team_stats[sorted_teams[j]]['points']:
                j += 1
            if j > i + 1:  # More than one team with the same points
                sorted_teams[i:j] = sorted(sorted_teams[i:j], key=lambda team: (
                    -sum(team_stats[team]['head_to_head_points'][opponent] for opponent in sorted_teams[i:j] if opponent != team),
                    -sum(team_stats[team]['head_to_head_goal_difference'][opponent] for opponent in sorted_teams[i:j] if opponent != team),
                    -team_stats[team]['goal_difference'],
                    -team_stats[team]['goals_scored'],
                    team
                ))
            i = j

        sorted_groups[group_name] = [team_stats[team] for team in sorted_teams]

    return sorted_groups


def ranking(request):

    sorted_groups = None
    top_scorers = None
    mvp_ranking = None
    context = None
    
    all_teams = Team.objects.all()
    drawing_done = any(team.group for team in all_teams)
    
    if drawing_done:
        sorted_groups = compute_ranking(all_teams)

        top_scorers = Player.objects.annotate(
            total_goals=Coalesce(Sum('goal__number_of_goals'), 0)
        ).filter(
            total_goals__gt=0, is_fake=False # This filters out players with 0 goals
        ).order_by('-total_goals')[:10]

        mvp_ranking = Player.objects.annotate(
            mvp_count=Count('mvp_matches')).filter(
            mvp_count__gt=0).order_by('-mvp_count')[:5]

        quarterfinals_matches = Match.objects.filter(
            stage='Eliminazione', group='Quarti')
        semifinals_matches = Match.objects.filter(
            stage='Eliminazione', group='Semifinali')
        finals_matches = Match.objects.filter(
            stage='Eliminazione', group__startswith='Finale')

        # first_place_teams, second_place_teams, qualified_third_place_teams = get_knockout_teams(
        #     sorted_groups)
        first_place_teams, second_place_teams = get_knockout_teams(
            sorted_groups)
        qualified_teams = first_place_teams + second_place_teams
        qualified_team_names = [team['team_name'] for team in qualified_teams]


        finale_3_4 = Match.objects.filter(validated=True, group='Finale 3-4')
        finale_1_2 = Match.objects.filter(validated=True, group='Finale 1-2')
        winners = []
        
        if finale_3_4 and finale_1_2:
            finale_3_4 = finale_3_4[0]
            finale_1_2 = finale_1_2[0]

            if finale_1_2.score_home_team > finale_1_2.score_away_team:
                winners.append(finale_1_2.home_team)
                winners.append(finale_1_2.away_team)
            else:
                winners.append(finale_1_2.away_team)
                winners.append(finale_1_2.home_team)
                
            if finale_3_4.score_home_team > finale_3_4.score_away_team:
                winners.append(finale_3_4.home_team)
            else:
                winners.append(finale_3_4.away_team)

        context = {
            'qualified_team_names': qualified_team_names,
            'quarterfinals_matches': quarterfinals_matches,
            'semifinals_matches': semifinals_matches,
            'finals_matches': finals_matches,
            'winners': winners
        }

    return render(request, 'tournament/ranking.html', {'sorted_groups': sorted_groups,
                                                       'drawing_done': drawing_done,
                                                       'top_scorers': top_scorers,
                                                       'mvp_ranking': mvp_ranking,
                                                       'context': context,
                                                       })


@login_required
def edit_match(request, match_id):
    match = get_object_or_404(Match, pk=match_id)
    if request.method == 'POST':
        match_form = MatchForm(request.POST, instance=match)
        home_goals_form = PlayerGoalsForm(
            request.POST, team=match.home_team, match=match)
        away_goals_form = PlayerGoalsForm(
            request.POST, team=match.away_team, match=match)
       
        if match_form.is_valid() and home_goals_form.is_valid() and away_goals_form.is_valid():

            updated_match = match_form.save()
            save_goals(home_goals_form, match, match.home_team)
            save_goals(away_goals_form, match, match.away_team)
            return redirect('manage_matches')

    else:
        match_form = MatchForm(instance=match)
        home_goals_form = PlayerGoalsForm(team=match.home_team, match=match)
        away_goals_form = PlayerGoalsForm(team=match.away_team, match=match)

    return render(request, 'tournament/edit_match.html', {
        'match_form': match_form,
        'home_goals_form': home_goals_form,
        'away_goals_form': away_goals_form,
    })


def save_goals(form, match, team):
    print(form)
    for field_name, value in form.cleaned_data.items():
        if value and value > 0:  # Make sure there is a value to save
            if field_name.startswith('goals'):
                player_id = int(field_name.split('_')[1])
                player = Player.objects.get(id=player_id)
            else:
                # Use the dummy player for own goals
                player = Player.objects.get(id=-1, team=team)
                print(player)
            # Handle saving/updating the goal
            g, created = Goal.objects.update_or_create(
                match=match,
                player=player,
                defaults={'number_of_goals': value}
            )

def team_and_player_list(request):
    # Fetch all teams, ordered by name
    teams = Team.objects.prefetch_related('players').order_by('name')
    
    # Dictionary to hold sorted players for each team
    sorted_players = {}
    max_players = 0

    # Iterate over each team to sort players by surname and update the maximum count
    for team in teams:
        # Sort players by surname
        players = list(team.players.all().order_by('surname'))
        sorted_players[team.id] = players
        # Update maximum number of players for any team
        if len(players) > max_players:
            max_players = len(players)

    # Create a list of lists for the player rows
    player_rows = [[] for _ in range(max_players)]
    for team in teams:
        players = sorted_players[team.id]
        # Fill rows with players or None if fewer players in this team
        for index in range(max_players):
            player_rows[index].append(players[index] if index < len(players) else None)

    return render(request, 'tournament/team_and_player_list.html', {
        'teams': teams,
        'player_rows': player_rows,
        'sorted_players': sorted_players
    })


@login_required
def team_list(request):
    teams = Team.objects.order_by('name')
    return render(request, 'tournament/team_list.html', {'teams': teams})


@login_required
def create_or_update_team(request, pk=None):
    # Fetch the team instance by pk or set to None for creation
    team = get_object_or_404(Team, pk=pk) if pk else None

    # Define the formset with deletion enabled
    TeamFormSet = inlineformset_factory(
        Team, Player, form=PlayerForm, extra=12 if not pk else 0, can_delete=True)

    if request.method == 'POST':
        # Handle form submission
        return handle_post(request, team, TeamFormSet)
    else:
        # Handle initial form loading
        return handle_initial_form(request, team, TeamFormSet)

def handle_post(request, team, TeamFormSet):
    print("Handle post")
    # Initialize forms with POST data
    team_form = TeamForm(request.POST, instance=team)
    formset = TeamFormSet(request.POST, instance=team)

    if team_form.is_valid() and formset.is_valid():
        # Save the team and update the formset instance
        created_team = team_form.save()
        formset.instance = created_team
        formset.save()
        
        Player.objects.update_or_create(
            team=created_team,
            is_fake=True,
            defaults={'name': 'autogoal', 'surname': 'autogoal', 'is_fake': True}
        )
                
        return redirect('manage_teams')
    
    # If forms are not valid, re-render the page with error messages
    return render(request, 'tournament/create_or_update_team.html', {
        'team_form': team_form,
        'formset': formset,
        'team': team
    })

def handle_initial_form(request, team, TeamFormSet):
    print("Handle Initial Form")
    # Prepare an empty form or preload data for editing
    team_form = TeamForm(instance=team)
    if team is None:
        initial_players = [{
            'name': f'name_{i}',
            'surname': f'surname_{i}'
        } for i in range(1, 13)] 
    else:
        initial_players = []
    formset = TeamFormSet(instance=team, initial=initial_players)
    return render(request, 'tournament/create_or_update_team.html', {
        'team_form': team_form,
        'formset': formset,
        'team': team
    })


class DeleteTeamView(DeleteView):
    model = Team
    # Name of the confirmation template
    template_name = 'tournament/delete_team.html'
    success_url = reverse_lazy('manage_teams')  # Redirect URL after deletion

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cancel_url'] = reverse_lazy('manage_teams')
        return context

# Assuming you have models named Match, Goal, and Team


def match_detail(request, match_id):
    match = get_object_or_404(Match, id=match_id)
    # Assuming that Goal has a 'player' ForeignKey and 'team' ForeignKey
    home_goals = Goal.objects.filter(match=match, player__team=match.home_team).select_related(
        'player').annotate(total_goals=Sum('number_of_goals')).order_by('-total_goals')
    away_goals = Goal.objects.filter(match=match, player__team=match.away_team).select_related(
        'player').annotate(total_goals=Sum('number_of_goals')).order_by('-total_goals')

    home_goals = list(home_goals)
    away_goals = list(away_goals)
    max_len = max(len(home_goals), len(away_goals))

    context = {
        "match": match,
        "home_goals": home_goals,
        "away_goals": away_goals,
        "mvp": match.mvp,
        "max_range": range(max_len),
    }

    return render(request, 'tournament/match_detail.html', context)


def document_list(request):
    documents = Document.objects.all()
    return render(request, 'tournament/document_list.html', {'documents': documents})


def download_document(request, doc_id):
    doc = get_object_or_404(Document, id=doc_id)
    response = HttpResponse(doc.file, content_type='application/octet-stream')
    new_filename = doc.file.name.replace("documents/","").replace("_","").capitalize()
    response['Content-Disposition'] = 'attachment; filename="%s"' % new_filename
    return response

def health_check(request):
    response = HttpResponse("OK", content_type="text/plain")
    return response