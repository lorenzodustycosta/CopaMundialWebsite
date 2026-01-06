import json
import os
import random

from datetime import date
from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from tournament.config.tournament_schedule import KNOCKOUT_DATES

from .models import Document, Goal, Group, Match, Team
from .services.knockout_service import (
    end_group_stage_and_create_quarterfinals,
    end_quarterfinals_and_create_semifinals, end_semifinals_and_create_finals)
from .services.ranking_service import build_ranking_page_data
from .services.schedule_service import (TournamentConfig, cleanup_matches,
                                        create_group_stage_schedule_from_csv)


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

@login_required
@require_POST
@csrf_protect
def end_group(request):
    """Close group stage and generate quarterfinals."""
    end_group_stage_and_create_quarterfinals(dates=KNOCKOUT_DATES)
    return redirect("manage_tournament")

@login_required
@require_POST
@csrf_protect
def end_quarterfinals(request):
    """Close quarterfinals and generate semifinals."""
    end_quarterfinals_and_create_semifinals(dates=KNOCKOUT_DATES)
    return redirect("manage_tournament")

@login_required
@require_POST
@csrf_protect
def end_semifinals(request):
    """Close semifinals and generate finals."""
    end_semifinals_and_create_finals(dates=KNOCKOUT_DATES)
    return redirect("manage_tournament")

@login_required
@require_POST
@csrf_protect
def end_finals(request):      
    return redirect("manage_tournament")

def match_schedule(request):
    # Fetching all matches ordered by date
    matches = Match.objects.all().order_by('date', 'time')
    return render(request, 'tournament/match_schedule.html', {'matches': matches})

def manage_tournament(request):
    return render(request, 'tournament/manage_tournament.html')

@login_required
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

@login_required
@require_POST
@csrf_protect
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