from django.db import models
from datetime import datetime
from django import forms
from django.db import models
from django import forms
from django.forms.models import BaseInlineFormSet
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum


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


class Player(models.Model):
    team = models.ForeignKey(
        Team, related_name='players', on_delete=models.CASCADE)
    name = models.CharField(max_length=100, default='')
    surname = models.CharField(max_length=100, default='')

    def __str__(self):
        return f"{self.surname} {self.name} {self.team.name}"


class Match(models.Model):
    PITCH_CHOICES = (
        ('Blu', 'Blu'),
        ('Verde', 'Verde'),
        ('Da definire', 'Da definire')
    )
    date = models.DateField(_("Date"), default="2024-06-05")
    time = models.TimeField(_("Time"), default="20:00:00")
    home_team = models.ForeignKey(Team, related_name='home_matches', on_delete=models.CASCADE, verbose_name=_("Home Team"))
    away_team = models.ForeignKey(Team, related_name='away_matches', on_delete=models.CASCADE, verbose_name=_("Away Team"))
    pitch = models.CharField(
        _("Pitch"), 
        max_length=50,
        choices=PITCH_CHOICES,
        default='Da definire'
    )
    score_home_team = models.IntegerField(_("Home Score"), default=0)
    score_away_team = models.IntegerField(_("Away Score"), default=0)
    stage = models.CharField(_("Stage"), max_length=50, default='Gironi')
    group = models.CharField(_("Group"), max_length=50, default='')
    validated = models.BooleanField(_('Validate'), default=False)
    mvp = models.ForeignKey(
        Player,
        on_delete=models.SET_NULL,
        null=True,  blank=True,
        related_name='mvp_matches'
    )

    def __str__(self):
        return f"{self.home_team} vs {self.away_team}"

class MatchForm(forms.ModelForm):
    class Meta:
        model = Match
        fields = ['date', 'time', 'home_team', 'away_team', 'score_home_team',
                  'score_away_team', 'pitch', 'stage', 'group', 'mvp', 'validated']
        labels = {
            'date': _('Date'),
            'time': _('Time'),
            'score_home_team': _('Home Score'),
            'score_away_team': _('Away Score'),
            'pitch': _('Pitch'),
            'group': _('Group'),
            'stage': _('Stage'),
            'home_team': _('Home Team'),
            'away team': _('Away Team'),
            'validated': _('Validated'),
            'mvp': _('MVP')
        }

    def __init__(self, *args, **kwargs):
            super(MatchForm, self).__init__(*args, **kwargs)
            instance = kwargs.get('instance')
            
            # Filter the mvp queryset based on the instance of the match if it exists
            if instance and instance.home_team and instance.away_team:
                valid_teams = [instance.home_team_id, instance.away_team_id]
                self.fields['mvp'].queryset = Player.objects.filter(team_id__in=valid_teams)
            elif self.is_bound:
                # Handle dynamically when creating a new match or when teams are changed in the form
                home_team_id = self.data.get('home_team')
                away_team_id = self.data.get('away_team')
                if home_team_id and away_team_id:
                    valid_teams = [home_team_id, away_team_id]
                    self.fields['mvp'].queryset = Player.objects.filter(team_id__in=valid_teams)
                else:
                    self.fields['mvp'].queryset = Player.objects.none()
            else:
                # Default empty queryset or all players if no teams are selected yet
                self.fields['mvp'].queryset = Player.objects.none()
                

class Goal(models.Model):
    match = models.ForeignKey(
        'Match', on_delete=models.CASCADE, related_name='goals')
    player = models.ForeignKey(
        'Player', on_delete=models.CASCADE, related_name='goals')
    number_of_goals = models.PositiveIntegerField(default=0)

    @property
    def goals_count(self):
        return range(self.number_of_goals)

    def __str__(self):
        return f"{self.player.name} scored {self.number_of_goals} goals in {self.match}"


class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ['name']
        labels = {
            'name': _('Team Name'),
        }


class PlayerForm(forms.ModelForm):
    class Meta:
        model = Player
        fields = ['name', 'surname']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': '', 'class': 'player-name'}),
            'surname': forms.TextInput(attrs={'placeholder': '', 'class': 'player-surname'}),
        }
        labels = {
            'name': _('Name'),
            'surname': _('Surname'),
        }


class PlayerGoalsForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = []

    def __init__(self, *args, **kwargs):
        # Extract the team argument before initializing the superclass
        team = kwargs.pop('team', None)
        match = kwargs.pop('match', None)
        super(PlayerGoalsForm, self).__init__(*args, **kwargs)

        if team and match:
            for player in Player.objects.filter(team=team):
                field_name = f'goals_{player.id}'
                initial_goals = Goal.objects.filter(player=player, match=match).aggregate(
                    Sum('number_of_goals'))['number_of_goals__sum'] or 0
                self.fields[field_name] = forms.IntegerField(
                    required=False,
                    label=f'{player.name} {player.surname}',
                    widget=forms.NumberInput(attrs={
                        'placeholder': 'Goals',
                        'style': 'width: 60px; margin-left: 10px;',
                    }),
                    initial=initial_goals
                )

class Document(models.Model):
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='documents/')

    def __str__(self):
        return self.title
