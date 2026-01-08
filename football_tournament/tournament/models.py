from django.db import models
from django.utils.translation import gettext_lazy as _


class Group(models.Model):
    name = models.CharField(max_length=100)
    note = models.CharField(_("Note"), max_length=500, default='', blank=True)
    def __str__(self):
        return self.name


class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)
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
    date = models.DateField(_("Date"), default="2025-06-05")
    time = models.TimeField(_("Time"), default="20:00:00")
    home_team = models.ForeignKey(
        Team, related_name='home_matches', on_delete=models.CASCADE, verbose_name=_("Home Team"))
    away_team = models.ForeignKey(
        Team, related_name='away_matches', on_delete=models.CASCADE, verbose_name=_("Away Team"))
    score_home_team = models.IntegerField(_("Home Score"), default=0)
    score_away_team = models.IntegerField(_("Away Score"), default=0)
    stage = models.CharField(_("Stage"), max_length=50, default='Gironi')
    group = models.CharField(_("Group"), max_length=50, default='')
    validated = models.BooleanField(_('Validate'), default=False)
    dts = models.BooleanField(default=False, verbose_name='Overtime')
    dcr = models.BooleanField(default=False, verbose_name='Penalties')
    note = models.CharField(_("Note"), max_length=500, default='', blank=True)
    mvp = models.ForeignKey(
        Player,
        on_delete=models.SET_NULL,
        null=True,  blank=True,
        related_name='mvp_matches'
    )

    def __str__(self):
        return f"{self.home_team} vs {self.away_team}"


class Goal(models.Model):
    player = models.ForeignKey(
        Player, on_delete=models.CASCADE, null=True, blank=True)
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    number_of_goals = models.IntegerField(default=0)

    @property
    def goals_count(self):
        return range(self.number_of_goals)

    def __str__(self):
        player_name = self.player.name if self.player else "Unknown"
        return f"{player_name} scored {self.number_of_goals} goals in {self.match}"


class Document(models.Model):
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='documents/')

    def __str__(self):
        return self.title
