from django.urls import path
from . import views
from django.contrib.auth.views import LoginView

urlpatterns = [
    path('', views.home, name='home'),
    path('matches/', views.match_schedule, name='match_schedule'),  # New URL for matches
    path('teams-and-playoffs/', views.teams_and_playoffs, name='teams_and_playoffs'),  # New URL pattern
    path('sorteggio/', views.group_draw, name='group_draw'),
    path('ranking/', views.ranking, name='ranking'),
    path('matches/edit/<int:match_id>/', views.edit_match, name='edit_match'),
    path('login/', LoginView.as_view(template_name='../templates/tournament/login.html'), name='login'),
]