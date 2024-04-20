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
import random

def home(request):
    return render(request, 'tournament/home.html')


def match_schedule(request):
    # Fetching all matches ordered by date
    matches = Match.objects.all().order_by('date')
    return render(request, 'tournament/match_schedule.html', {'matches': matches})


def manage_matches(request):
    # Fetching all matches ordered by date
    matches = Match.objects.all().order_by('date')
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
            print(tournament_schedule)
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
            match_info['pitch'] = 'Green'
            # Get the date and time of the current match
            match_date = match_info['date']
            match_time = match_info['time']

            # Find all matches that occur at the same date and time
            same_time_matches = [m for m in tournament_schedule if m['date'] == match_date and m['time'] == match_time]

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
            pitch = 'Blu' if i % 4 < 2 else 'Green'  # Alternate pitches
        else:  # Remaining two matches on Wednesday
            if i % 6 == 4:  # Move to Wednesday after the first four matches
                current_date += timedelta(days=1)
            match_time = '20:30'  # Fixed match time for Wednesday
            pitch = 'Blu' if i % 6 == 4 else 'Green'  # Alternate pitches

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
        print(day_matches)
        schedule.append(day_matches)

    return schedule


def compute_ranking(all_teams):
    groups = defaultdict(list)
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
        sorted_teams = sorted(
            teams, key=lambda x: (-x['points'], -x['goal_difference'], -x['goals_scored'], x['team_name']))
        sorted_groups[group_name] = sorted_teams

    sorted_groups = sorted_groups.items()

    return sorted_groups


def ranking(request):

    all_teams = Team.objects.all()
    drawing_done = any(team.group for team in all_teams)

    if drawing_done:
        sorted_groups = compute_ranking(all_teams)
    else:
        sorted_groups = None

    top_scorers = Player.objects.annotate(
        total_goals=Coalesce(Sum('goals__number_of_goals'), 0)
    ).filter(
        total_goals__gt=0  # This filters out players with 0 goals
    ).order_by('-total_goals')[:10]

    ko_matches = Match.objects.filter(group='Eliminazione')
    qualified_teams = get_knockout_teams(sorted_groups)

    return render(request, 'tournament/ranking.html', {'groups': sorted_groups,
                                                       'drawing_done': drawing_done,
                                                       'top_scorers': top_scorers,
                                                       'qualified_teams': qualified_teams,
                                                       'ko_matches': ko_matches
                                                       })

# @transaction.atomic


def end_group(request):

    all_teams = Team.objects.all()
    sorted_groups = compute_ranking(all_teams)
    qualified_teams = get_knockout_teams(sorted_groups)
    matchups = create_quarterfinals_matchups(qualified_teams)
    print(matchups)
    print("------------------------")
    for home_team, away_team in matchups:
        Match.objects.create(
            stage='Quarti',
            group='Eliminazione',
            home_team=Team.objects.get(name=home_team['team_name']),
            away_team=Team.objects.get(name=away_team['team_name']),
            date=date(2024, 6, 25)
        )

    matches = Match.objects.all().order_by('date')
    print("All mathes")
    print(matches)
    print("------------------")
    return render(request, 'tournament/manage_matches.html', {'matches': matches})


def create_quarterfinals_matchups(qualified_teams):
    # Sort teams based on rank
    qualified_teams.sort(
        key=lambda x: (-x['points'], -x['goal_difference'], -x['goals_scored']))
    # Create matchups: 1st vs 8th, 2nd vs 7th, etc.
    num_teams = len(qualified_teams)
    matchups = [
        (qualified_teams[i], qualified_teams[num_teams - i - 1])
        for i in range(num_teams // 2)
    ]
    return matchups


def get_knockout_teams(sorted_groups):
    top_two_teams = []
    third_place_teams = []

    # Iterate over each group and their teams, already sorted by standings
    for group_name, teams in sorted_groups:
        # Add top two teams from each group to the list of top two teams
        if len(teams) >= 2:
            top_two_teams.extend(teams[:2])

        # Collect the third place team from each group
        if len(teams) > 2:
            third_place_teams.append(teams[2])

    # Sort the third place teams based on the criteria and select the top two
    qualified_third_place_teams = sorted(
        third_place_teams,
        key=lambda x: (x['points'], x['goal_difference'], x['goals_scored']),
        reverse=True
    )[:2]

    # Combine top two teams from all groups with the top two from the third place teams

    team_to_ko = top_two_teams + qualified_third_place_teams

    return top_two_teams + qualified_third_place_teams


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
            player_rows[index].append(
                players[index] if index < len(players) else None)

    return render(request, 'tournament/team_and_player_list.html', {'teams': teams, 'player_rows': player_rows})


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
    if request.method == 'POST':
        # Bind form to POST data and instance
        team_form = TeamForm(request.POST, instance=team)
        PlayerFormSet = inlineformset_factory(
            Team, Player, form=PlayerForm, extra=10, can_delete=True)
        # Bind formset to POST data and instance
        formset = PlayerFormSet(request.POST, instance=team)

        if team_form.is_valid() and formset.is_valid():
            created_team = team_form.save()  # Save the team and capture the instance
            # Ensure the formset instance is the newly created team
            formset.instance = created_team
            formset.save()  # Save the formset data
            # Redirect to a page that lists all teams
            return redirect('manage_teams')
        else:
            if not team_form.is_valid():
                print("Team Form Errors:", team_form.errors)
            if not formset.is_valid():
                print("Formset Errors:", formset.errors)

    else:
        # Unbound form for initial GET request
        team_form = TeamForm(instance=team)
        PlayerFormSet = inlineformset_factory(
            Team, Player, form=PlayerForm, extra=10, can_delete=True)
        # Unbound formset for initial GET request
        formset = PlayerFormSet(instance=team)

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
        'away_goals': away_goals
    })
