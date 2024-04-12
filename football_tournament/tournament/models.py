from django.db import models
from datetime import datetime
from django import forms
from django.db import models
from django import forms
from django.forms.models import BaseInlineFormSet

class Group(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Team(models.Model):
    name = models.CharField(max_length=100)
    group = models.ForeignKey(
        Group, related_name='teams', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.name


class Match(models.Model):
    PITCH_CHOICES = (
        ('Blu', 'Blu'),
        ('Verde', 'Verde'),
        ('Da definire','Da definire')
    )
    date = models.DateField(default="2024-06-05")
    time = models.TimeField(default="20:00:00")
    home_team = models.ForeignKey(
        Team, related_name='home_team', on_delete=models.CASCADE, default='home_team')
    away_team = models.ForeignKey(
        Team, related_name='away_team', on_delete=models.CASCADE, default='away_team')
    pitch = models.CharField(
        max_length=50, default='Da definire', choices=PITCH_CHOICES)
    score_home_team = models.IntegerField(default=0)
    score_away_team = models.IntegerField(default=0)
    stage = models.CharField(max_length=50, default='Gironi')
    group = models.CharField(max_length=50, default='')
    validated = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.home_team} vs {self.away_team}"


class Player(models.Model):
    team = models.ForeignKey(Team, related_name='players', on_delete=models.CASCADE)
    name = models.CharField(max_length=100, default='')
    surname = models.CharField(max_length=100, default='')
    def __str__(self):
            return f"{self.surname} {self.name}"
        
class Goal(models.Model):
    match = models.ForeignKey('Match', on_delete=models.CASCADE, related_name='goals')
    player = models.ForeignKey('Player', on_delete=models.CASCADE, related_name='goals')
    number_of_goals = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.player.name} scored {self.number_of_goals} goals in {self.match}"
    
class MatchForm(forms.ModelForm):
    class Meta:
        model = Match
        fields = ['date', 'time', 'home_team', 'away_team', 'score_home_team',
                  'score_away_team', 'pitch', 'stage', 'group', 'validated']
        
class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ['name']

class PlayerForm(forms.ModelForm):
    class Meta:
        model = Player
        fields = ['name', 'surname']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': '', 'class': 'player-name'}),
            'surname': forms.TextInput(attrs={'placeholder': '', 'class': 'player-surname'}),
        }
        
class GoalForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = ['player', 'number_of_goals']

    def __init__(self, *args, match=None, **kwargs):
        super(GoalForm, self).__init__(*args, **kwargs)
        if match:
            self.fields['player'].queryset = Player.objects.filter(team__in=[match.home_team, match.away_team])

class GoalFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        self.match = kwargs.pop('match', None)
        super(GoalFormSet, self).__init__(*args, **kwargs)
        for form in self.forms:
            form.fields['player'].queryset = Player.objects.filter(
                team__in=[self.match.home_team, self.match.away_team]
            ) if self.match else Player.objects.none()