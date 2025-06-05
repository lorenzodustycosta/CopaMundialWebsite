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
    image_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.name


class Player(models.Model):
    team = models.ForeignKey(
        Team, related_name='players', on_delete=models.CASCADE)
    name = models.CharField(max_length=100, default='', blank=True)
    surname = models.CharField(max_length=100, default='', blank=True)
    is_fake = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.surname} {self.name} {self.team.name}"


class Match(models.Model):
    PITCH_CHOICES = (
        ('Blu', 'Blu'),
        ('Verde', 'Verde'),
        ('Da definire', 'Da definire')
    )
    date = models.DateField(_("Date"), default="2025-06-05")
    time = models.TimeField(_("Time"), default="20:00:00")
    home_team = models.ForeignKey(
        Team, related_name='home_matches', on_delete=models.CASCADE, verbose_name=_("Home Team"))
    away_team = models.ForeignKey(
        Team, related_name='away_matches', on_delete=models.CASCADE, verbose_name=_("Away Team"))
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
    dts = models.BooleanField(default=False, verbose_name='Overtime')
    dcr = models.BooleanField(default=False, verbose_name='Penalties')
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
        fields = ['date', 'time', 'pitch', 'stage', 'group', 'home_team', 'away_team', 'score_home_team', 'score_away_team',
                  'dts', 'dcr', 'mvp', 'validated']
        labels = {
            'date': _('Date'),
            'time': _('Time'),
            'home_team': _('Home Team'),
            'away_team': _('Away Team'),
            'score_home_team': _('Home Score'),
            'score_away_team': _('Away Score'),
            'pitch': _('Pitch'),
            'stage': _('Stage'),
            'group': _('Group'),
            'mvp': _('MVP'),
            'validated': _('Validated')
        }
        widgets = {
            'dts': forms.CheckboxInput(),
            'dcr': forms.CheckboxInput(),
        }

    def __init__(self, *args, **kwargs):
        super(MatchForm, self).__init__(*args, **kwargs)
        instance = kwargs.get('instance')

        if instance:
            valid_teams = [instance.home_team_id, instance.away_team_id]
            self.fields['mvp'].queryset = Player.objects.filter(
                team_id__in=valid_teams,  is_fake=False)
        elif self.is_bound:
            home_team_id = self.data.get('home_team')
            away_team_id = self.data.get('away_team')
            if home_team_id and away_team_id:
                valid_teams = [home_team_id, away_team_id]
                self.fields['mvp'].queryset = Player.objects.filter(
                    team_id__in=valid_teams, is_fake=False)
            else:
                self.fields['mvp'].queryset = Player.objects.none()
        else:
            self.fields['mvp'].queryset = Player.objects.none()


class Goal(models.Model):
    player = models.ForeignKey(
        Player, on_delete=models.CASCADE, null=True, blank=True)
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    number_of_goals = models.IntegerField(default=0)

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
        fields = []  # No fields defined since we're adding them dynamically

    def __init__(self, *args, **kwargs):
        team = kwargs.pop('team', None)
        match = kwargs.pop('match', None)
        super(PlayerGoalsForm, self).__init__(*args, **kwargs)

        if team and match:
            # Add fields for real players
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
