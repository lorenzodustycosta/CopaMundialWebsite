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

def home(request):
    return render(request, 'tournament/home.html')


def match_schedule(request):
    # Fetching all matches ordered by date
    matches = Match.objects.all().order_by('date')
    return render(request, 'tournament/match_schedule.html', {'matches': matches})


def manage_matches(request):
    # Fetching all matches ordered by date
    matches = Match.objects.all().order_by('date')

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

    finals_matches = matches.filter(group='Finali')
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
        date=date(2024, 7, 2),
        pitch='Blu',
        time='20:30',

    )

    Match.objects.create(
        stage='Eliminazione',
        group='Semifinali',
        home_team=winners[2],
        away_team=winners[3],
        date=date(2024, 7, 2),
        pitch='Blu',
        time='21:30',
    )

    return redirect('manage_matches')


def end_semifinals(request):
    matches = Match.objects.all().order_by('date')
    return render(request, 'tournament/manage_matches.html', {'matches': matches})


def end_finals(request):
    matches = Match.objects.all().order_by('date')
    return render(request, 'tournament/manage_matches.html', {'matches': matches})


def end_group(request):

    all_teams = Team.objects.all()
    sorted_groups = compute_ranking(all_teams)
    first_place_teams, second_place_teams, qualified_third_place_teams = get_knockout_teams(
        sorted_groups)

    matchups = create_quarterfinals_matchups(
        first_place_teams, second_place_teams, qualified_third_place_teams)

    time = cycle(['20:30', '21:30'])

    for i, teams in enumerate(matchups):
        Match.objects.create(
            stage='Eliminazione',
            group='Quarti',
            home_team=Team.objects.get(name=teams[0]['team_name']),
            away_team=Team.objects.get(name=teams[1]['team_name']),
            date=date(2024, 6, 25) if i <= 1 else date(2024, 6, 26),
            pitch='Blu',
            time=next(time),

        )

    matches = Match.objects.all().order_by('date')

    return redirect('manage_matches')


def create_quarterfinals_matchups(first_place_teams, second_place_teams, qualified_third_place_teams):

    matchups = []

    matchups.append([first_place_teams[0], qualified_third_place_teams[1]])
    matchups.append([second_place_teams[0], second_place_teams[1]])
    matchups.append([first_place_teams[2], second_place_teams[2]])
    matchups.append([first_place_teams[1], qualified_third_place_teams[0]])

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

    first_place_teams = sorted(
        first_place_teams,
        key=lambda x: (x['points'], x['goal_difference'], x['goals_scored']),
        reverse=True
    )

    second_place_teams = sorted(
        second_place_teams,
        key=lambda x: (x['points'], x['goal_difference'], x['goals_scored']),
        reverse=True
    )

    # Sort the third place teams based on the criteria and select the top two
    qualified_third_place_teams = sorted(
        third_place_teams,
        key=lambda x: (x['points'], x['goal_difference'], x['goals_scored']),
        reverse=True
    )[:2]

    return first_place_teams, second_place_teams, qualified_third_place_teams


def group_draw(request):
    if 'draw' in request.POST:
        # Perform draw for one random team
        unassigned_teams = Team.objects.filter(group__isnull=True)
        if unassigned_teams:
            team = random.choice(unassigned_teams)
            # Get groups with less than 4 teams
            groups = Group.objects.annotate(
                num_teams=Count('teams')).filter(num_teams__lt=4)
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
            tournament_schedule = create_tournament_schedule(
                start_date, all_groups)
            tournament_schedule = adjust_for_special_team(tournament_schedule)

            for match_info in tournament_schedule:
                group = get_object_or_404(Group, name=match_info['group'])
                Match.objects.create(
                    group=group,
                    home_team=Team.objects.get(
                        name=match_info['home_team']),
                    away_team=Team.objects.get(
                        name=match_info['away_team']),
                    date=match_info['date'],
                    time=match_info['time'],
                    pitch=match_info['pitch'],
                    mvp=None
                )

    # Teams without a group
    unassigned_teams = Team.objects.filter(group__isnull=True)
    # All groups (to display assigned teams under each group)
    groups = Group.objects.prefetch_related('teams').order_by('name').all()
    return render(request, 'tournament/group_draw.html', {'unassigned_teams': unassigned_teams, 'groups': groups})


def adjust_for_special_team(tournament_schedule, special_team_name='Sottomarini Gialli'):
    # Go through each match in the schedule
    for match_info in tournament_schedule:
        # Check if the special team is playing in this match
        if match_info['home_team'] == special_team_name or match_info['away_team'] == special_team_name:
            # Assign the special team to the Green pitch
            match_info['pitch'] = 'Verde'
            # Get the date and time of the current match
            match_date = match_info['date']
            match_time = match_info['time']

            # Find all matches that occur at the same date and time
            same_time_matches = [
                m for m in tournament_schedule if m['date'] == match_date and m['time'] == match_time]

            # Assign the other match at the same time to the Blue pitch
            for other_match_info in same_time_matches:
                if other_match_info is not match_info:
                    other_match_info['pitch'] = 'Blu'

    return tournament_schedule


def cleanup_matches():
    # Assuming `Match` has related objects that need to be cleared as well
    # This will delete all matches and any related objects via cascade deletion
    Match.objects.all().delete()


def create_tournament_schedule(start_date, groups_queryset):
    # Initialize a list for all matches across all groups
    all_matches = []

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
        if i % 6 < 4:  # First four matches on Tuesday
            if i % 6 == 0:  # Reset to the next Tuesday every 6 matches
                current_date += timedelta(days=7 - current_date.weekday() +
                                          1) if i != 0 else timedelta(0)
            # Alternate match times for Tuesday
            match_time = '20:30' if i % 2 == 0 else '21:30'
            pitch = 'Blu' if i % 4 < 2 else 'Verde'  # Alternate pitches
        else:  # Remaining two matches on Wednesday
            if i % 6 == 4:  # Move to Wednesday after the first four matches
                current_date += timedelta(days=1)
            match_time = '20:30'  # Fixed match time for Wednesday
            pitch = 'Blu' if i % 6 == 4 else 'Verde'  # Alternate pitches

        sorted_schedule.append({
            'date': current_date,
            'group': match['group'],
            'home_team': match['home_team'],
            'away_team': match['away_team'],
            'time': match_time,
            'pitch': pitch
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
            }

    # Fetch matches grouped by group name
    for group_name, teams_info in groups.items():
        validated_matches = Match.objects.filter(
            validated=True, group=group_name)

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

    # Sort teams within each group
    sorted_groups = {group_name: sorted(team_stats.values(), key=lambda x: (-x['points'], -x['goal_difference'], -x['goals_scored'], x['team_name']))
                     for group_name, team_stats in sorted(groups.items())}

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
            total_goals=Coalesce(Sum('goals__number_of_goals'), 0)
        ).filter(
            total_goals__gt=0  # This filters out players with 0 goals
        ).order_by('-total_goals')[:10]

        mvp_ranking = Player.objects.annotate(
            mvp_count=Count('mvp_matches')).filter(
            mvp_count__gt=0).order_by('-mvp_count')[:5]

        quarterfinals_matches = Match.objects.filter(
            stage='Eliminazione', group='Quarti')
        semifinals_matches = Match.objects.filter(
            stage='Eliminazione', group='Semifinali')
        finals_matches = Match.objects.filter(
            stage='Eliminazione', group='Finali')

        first_place_teams, second_place_teams, qualified_third_place_teams = get_knockout_teams(
            sorted_groups)
        qualified_teams = first_place_teams + \
            second_place_teams + qualified_third_place_teams
        qualified_team_names = [team['team_name'] for team in qualified_teams]

        context = {
            'qualified_team_names': qualified_team_names,
            'quarterfinals_matches': quarterfinals_matches,
            'semifinals_matches': semifinals_matches,
            'finals_matches': finals_matches,
        }

    return render(request, 'tournament/ranking.html', {'sorted_groups': sorted_groups,
                                                       'drawing_done': drawing_done,
                                                       'top_scorers': top_scorers,
                                                       'mvp_ranking': mvp_ranking,
                                                       'context': context
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
        home_goals_form = PlayerGoalsForm(
            request.POST or None, team=match.home_team, match=match)
        away_goals_form = PlayerGoalsForm(
            request.POST or None, team=match.away_team, match=match)

    return render(request, 'tournament/edit_match.html', {
        'match_form': match_form,
        'home_goals_form': home_goals_form,
        'away_goals_form': away_goals_form,
    })


def save_goals(form, match, team):
    for field_name, value in form.cleaned_data.items():
        if value and value > 0:  # Make sure there is a value to save
            player_id = int(field_name.split('_')[1])
            player = Player.objects.get(id=player_id)
            Goal.objects.update_or_create(
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
    if pk:
        # Safely get the object or return 404
        team = get_object_or_404(Team, pk=pk)
    else:
        team = None  # Define team as None if no pk is provided

    TeamFormSet = inlineformset_factory(
        Team, Player, form=PlayerForm, extra=12, can_delete=True)

    if request.method == 'POST':
        team_form = TeamForm(request.POST, instance=team)
        formset = TeamFormSet(request.POST, instance=team)

        if team_form.is_valid() and formset.is_valid():
            created_team = team_form.save()  # Save the team and capture the instance
            formset.instance = created_team
            formset.save()  # Save the formset data
            return redirect('manage_teams')

    else:
        team_form = TeamForm(instance=team)

        if team is None:
            # If creating a new team, prepopulate the players
            initial_players = [{
                'name': f'name_{i}',
                'surname': f'surname_{i}'
            } for i in range(1, 13)]

            formset = TeamFormSet(instance=team, initial=initial_players)
        else:
            TeamFormSet = inlineformset_factory(
                Team, Player, form=PlayerForm, extra=0, can_delete=True)
            formset = TeamFormSet(instance=team)

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

    return render(request, 'tournament/match_detail.html', {
        'match': match,
        'home_goals': home_goals,
        'away_goals': away_goals,
        'mvp': match.mvp
    })


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