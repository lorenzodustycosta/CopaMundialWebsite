from __future__ import annotations

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import HallOfFame, Match, Player


class MatchForm(forms.ModelForm):
    class Meta:
        model = Match
        fields = [
            "date",
            "time",
            "stage",
            "group",
            "home_team",
            "away_team",
            "score_home_team",
            "score_away_team",
            "dts",
            "dcr",
            "mvp",
            "validated",
        ]
        labels = {
            "date": _("Date"),
            "time": _("Time"),
            "home_team": _("Home Team"),
            "away_team": _("Away Team"),
            "score_home_team": _("Home Score"),
            "score_away_team": _("Away Score"),
            "stage": _("Stage"),
            "group": _("Group"),
            "mvp": _("MVP"),
            "validated": _("Validated"),
        }
        widgets = {
            "dts": forms.CheckboxInput(),
            "dcr": forms.CheckboxInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get("instance")

        if instance:
            valid_teams = [instance.home_team_id, instance.away_team_id]
            self.fields["mvp"].queryset = Player.objects.filter(
                team_id__in=valid_teams, is_fake=False
            )
        elif self.is_bound:
            home_team_id = self.data.get("home_team")
            away_team_id = self.data.get("away_team")
            if home_team_id and away_team_id:
                valid_teams = [home_team_id, away_team_id]
                self.fields["mvp"].queryset = Player.objects.filter(
                    team_id__in=valid_teams, is_fake=False
                )
            else:
                self.fields["mvp"].queryset = Player.objects.none()
        else:
            self.fields["mvp"].queryset = Player.objects.none()


class HallOfFameForm(forms.ModelForm):
    class Meta:
        model = HallOfFame
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = self.instance

        if instance and instance.team_id:
            self.fields["player"].queryset = Player.objects.filter(team_id=instance.team_id)
        elif self.is_bound:
            team_id = self.data.get("team")
            if team_id:
                self.fields["player"].queryset = Player.objects.filter(team_id=team_id)
            else:
                self.fields["player"].queryset = Player.objects.none()
        else:
            self.fields["player"].queryset = Player.objects.none()
