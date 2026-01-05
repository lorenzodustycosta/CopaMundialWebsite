import csv
import datetime
import os
import random
import traceback
from collections import defaultdict
from datetime import date, timedelta
from itertools import combinations, cycle
from operator import itemgetter
from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.core.management import call_command
from django.db import transaction
from django.db.models import (Case, Count, F, IntegerField, Prefetch, Q, Sum,
                              Value, When)
from django.db.models.functions import Coalesce
from django.forms import inlineformset_factory
from django.http import HttpResponse, HttpResponseServerError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic.edit import CreateView, DeleteView

from django.http import JsonResponse
import random
import json

from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect

from .models import (Document, Goal, Group, Match, MatchForm, Player,
                     PlayerForm, PlayerGoalsForm, Team, TeamForm)

from .services.schedule_service import TournamentConfig, create_group_stage_schedule_from_csv, cleanup_matches
from .services.knockout_service import KnockoutDates, end_group_stage_and_create_quarterfinals, end_quarterfinals_and_create_semifinals, end_semifinals_and_create_finals
from .services.group_stage_service import compute_group_stage_outcome
from .services.ranking_service import build_ranking_page_data
from tournament.config.tournament_schedule import KNOCKOUT_DATES

def home(request):
    return render(request, 'tournament/home.html')

def ranking(request):
    """Render the ranking page using precomputed service data."""
    outcome = build_ranking_page_data()

    drawing_done = any(t.group_id for t in Team.objects.all())

    return render(
        request,
        "tournament/ranking.html",
        {
            "drawing_done": drawing_done,
            "rankings": outcome.rankings,
            "group_notes": outcome.group_notes,
            "qualified_team_names": [t for t in outcome.qualified_team_names],
            "top_scorers": outcome.top_scorers,
            "mvp_ranking": outcome.mvp_ranking,
            "winners": outcome.winners,
            "quarterfinals_matches": outcome.quarterfinals_matches,
            "semifinals_matches": outcome.semifinals_matches,
            "final_3_4_match": outcome.final_3_4_match,
            "final_1_2_match": outcome.final_1_2_match,
        },
    )

def end_group(request):
    """Close group stage and generate quarterfinals."""
    end_group_stage_and_create_quarterfinals(dates=KNOCKOUT_DATES)
    return redirect("manage_matches")

def end_quarterfinals(request):
    """Close quarterfinals and generate semifinals."""
    end_quarterfinals_and_create_semifinals(dates=KNOCKOUT_DATES)
    return redirect("manage_matches")

def end_semifinals(request):
    """Close semifinals and generate finals."""
    end_semifinals_and_create_finals(dates=KNOCKOUT_DATES)
    return redirect("manage_matches")

def end_finals(request):      
    return redirect("manage_matches")

#############################################################


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


@require_POST
@csrf_protect
def draw_team_ajax(request):
    
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        unassigned_teams = list(Team.objects.filter(group__isnull=True))
        groups = list(Group.objects.annotate(num_teams=Count('teams')).filter(num_teams__lt=4))

        if not unassigned_teams or not groups:
            return JsonResponse({'status': 'no_teams_or_groups'})

        team = random.choice(unassigned_teams)
        group = random.choice(groups)
        team.group = group
        team.save()

        return JsonResponse({
            'status': 'ok',
            'team_id': team.id,
            'team_name': team.name,
            'group_id': group.id,
            'group_name': group.name
        })

    return JsonResponse({'status': 'invalid'}, status=400)

def group_draw(request):
    last_picked_team_id = None  # Initialize variable to store the ID of the last picked team
    error = None
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
        BASE_DIR = Path(__file__).resolve().parent.parent
        schema_path = os.path.join(BASE_DIR, 'schedules', 'scheduling_schema.csv')
        try:
            cleanup_matches()
            config = TournamentConfig(start_date=date(2025, 6, 3))
            created = create_group_stage_schedule_from_csv(csv_path=schema_path, config=config)
        except ValueError as e:
            print(e)
            error = str(e)
            return render(request, 'tournament/group_draw.html', {
                'unassigned_teams': None,
                'groups': None,
                'last_picked_team_id': last_picked_team_id,  # Pass the last picked team's ID to the template
                "error": error})
        
    unassigned_teams = Team.objects.filter(group__isnull=True)
    groups = Group.objects.prefetch_related('teams').order_by('name').all()
    
    return render(request, 'tournament/group_draw.html', {
        'unassigned_teams': unassigned_teams,
        'groups': groups,
        'last_picked_team_id': last_picked_team_id,  # Pass the last picked team's ID to the template
        "error": error})

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
    for field_name, value in form.cleaned_data.items():
        if value and value > 0:  # Make sure there is a value to save
            if field_name.startswith('goals'):
                player_id = int(field_name.split('_')[1])
                player = Player.objects.get(id=player_id)
            else:
                # Use the dummy player for own goals
                player = Player.objects.get(id=-1, team=team)
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

def migrate_view(request):
    try:
        call_command("migrate")
        return HttpResponse("✅ Migrations executed.")
    except Exception as e:
        tb = traceback.format_exc()
        return HttpResponseServerError(f"<pre>❌ Migration failed:\n\n{tb}</pre>")