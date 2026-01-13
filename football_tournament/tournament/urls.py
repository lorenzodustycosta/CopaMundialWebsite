from django.urls import path
from . import views
from django.contrib.auth.views import LoginView, LogoutView

urlpatterns = [
    path('', views.home, name='home'),
    path('matches/', views.match_schedule, name='match_schedule'),  # New URL for matches
    path('sorteggio/', views.group_draw, name='group_draw'),
    path('ajax/draw_team/', views.draw_team_ajax, name='draw_team_ajax'),
    path('ranking/', views.ranking, name='ranking'),
    path('ranking/groups/', views.ranking_groups, name='ranking_groups'),
    path('ranking/knockout/', views.ranking_knockout, name='ranking_knockout'),
    path('ranking/players/', views.ranking_players, name='ranking_players'),
    path('matches/end_group/', views.end_group, name='end_group'),
    path('matches/end_quarterfinals/', views.end_quarterfinals, name='end_quarterfinals'),
    path('matches/end_semifinals/', views.end_semifinals, name='end_semifinals'),
    path('matches/end_finals/', views.end_finals, name='end_finals'),
    path('hall_of_fame/', views.hall_of_fame, name='hall_of_fame'),
    path('login/', LoginView.as_view(template_name='../templates/tournament/login.html'), name='login'),
    path('logout/', LogoutView.as_view(next_page='home'), name='logout'),
    path('team_and_player_list/', views.team_and_player_list, name='team_and_player_list'),
    path('manage_tournament/', views.manage_tournament, name='manage_tournament'),
    path('matches/<int:match_id>/', views.match_detail, name='match_detail'),
    path('document_list/', views.document_list, name='document_list'),
    path('download/<int:doc_id>/', views.download_document, name='download_document'),
    path('health-check/', views.health_check, name='health-check'),
]
