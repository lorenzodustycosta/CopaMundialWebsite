from django.db import models
from datetime import datetime
from django import forms


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
    team1 = models.ForeignKey(
        Team, related_name='team1', on_delete=models.CASCADE)
    team2 = models.ForeignKey(
        Team, related_name='team2', on_delete=models.CASCADE)
    pitch = models.CharField(
        max_length=50, default='Da definire', choices=PITCH_CHOICES)
    score1 = models.IntegerField(default=0)
    score2 = models.IntegerField(default=0)
    stage = models.CharField(max_length=50, default='Gironi')
    group = models.CharField(max_length=50, default='')
    validated = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.team1} vs {self.team2}"


class Player(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)


class Goal(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    player = models.ForeignKey(Player, on_delete=models.CASCADE)


class MatchForm(forms.ModelForm):
    class Meta:
        model = Match
        fields = ['date', 'time', 'team1', 'team2', 'score1',
                  'score2', 'pitch', 'stage', 'group', 'validated']
