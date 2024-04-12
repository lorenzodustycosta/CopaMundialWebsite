from django.urls import path
from . import views
from django.contrib.auth.views import LoginView, LogoutView

urlpatterns = [
    path('', views.home, name='home'),
    path('matches/', views.match_schedule, name='match_schedule'),  # New URL for matches
    path('teams-and-playoffs/', views.teams_and_playoffs, name='teams_and_playoffs'),  # New URL pattern
    path('sorteggio/', views.group_draw, name='group_draw'),
    path('ranking/', views.ranking, name='ranking'),
    path('matches/edit/<int:match_id>/', views.edit_match, name='edit_match'),
    path('login/', LoginView.as_view(template_name='../templates/tournament/login.html'), name='login'),
    path('logout/', LogoutView.as_view(next_page='home'), name='logout'),
    path('team_and_player_list/', views.team_and_player_list, name='team_and_player_list'),
    path('teams/edit/<int:team_id>/', views.create_or_update_team, name='create_or_update_team'),
    path('manage_matches/', views.manage_matches, name='manage_matches'),
    path('manage_teams/', views.team_list, name='manage_teams'),
    path('teams/create/', views.create_or_update_team, name='create_team'),
    path('teams/<int:pk>/delete/', views.DeleteTeamView.as_view(), name='delete_team'),
    path('team/<int:pk>/edit/', views.create_or_update_team, name='create_or_update_team'),  # For editing an existing team
]