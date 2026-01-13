from django.contrib import admin
from django import forms
from django.http import JsonResponse
from django.urls import path

from .forms import HallOfFameForm, MatchForm
from .models import Group, Team, Player, Match, Goal, Document, HallOfFame


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    """Admin configuration for groups."""
    list_display = ("name", "note")
    search_fields = ("name", "note")


class PlayerInline(admin.TabularInline):
    """Inline players inside Team admin."""
    model = Player
    extra = 12
    fields = ("surname", "name", "is_fake")
    ordering = ("surname", "name")
    show_change_link = False


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    """Admin configuration for teams, with inline player management."""
    list_display = ("name", "group")
    search_fields = ("name",)
    list_filter = ("group",)
    inlines = [PlayerInline]

    def save_related(self, request, form, formsets, change):
        """
        Ensure the fake 'autogoal' player always exists for each team.
        """
        super().save_related(request, form, formsets, change)

        team = form.instance
        Player.objects.update_or_create(
            team=team,
            is_fake=True,
            defaults={
                "name": "autogoal",
                "surname": "autogoal",
                "is_fake": True,
            },
        )


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    """Admin configuration for players (useful even if you mostly edit via Team inline)."""
    list_display = ("surname", "name", "team", "is_fake")
    list_filter = ("team", "is_fake")
    search_fields = ("surname", "name", "team__name")
    ordering = ("team__name", "surname", "name")


class GoalInlineForm(forms.ModelForm):
    """Inline form for goals to allow filtering player choices per match."""
    class Meta:
        model = Goal
        fields = ("player", "number_of_goals")


class BaseGoalInline(admin.TabularInline):
    """Base inline for goals with per-team filtering."""
    model = Goal
    form = GoalInlineForm
    extra = 0
    fields = ("player", "number_of_goals")
    autocomplete_fields = ()
    team_side = None  # "home" or "away"

    def _get_match_id(self, request):
        try:
            return request.resolver_match.kwargs.get("object_id")
        except Exception:
            return None

    def _get_team_id(self, match):
        if self.team_side == "home":
            return match.home_team_id
        if self.team_side == "away":
            return match.away_team_id
        return None

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        match_id = self._get_match_id(request)
        if not match_id:
            return queryset.none()
        try:
            match = Match.objects.only("home_team_id", "away_team_id").get(pk=match_id)
        except Match.DoesNotExist:
            return queryset.none()
        team_id = self._get_team_id(match)
        return queryset.filter(player__team_id=team_id) if team_id else queryset.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name != "player":
            return field

        match_id = self._get_match_id(request)
        if not match_id:
            field.queryset = Player.objects.none()
            return field

        try:
            match = Match.objects.select_related("home_team", "away_team").get(pk=match_id)
        except Match.DoesNotExist:
            field.queryset = Player.objects.none()
            return field

        team_id = self._get_team_id(match)
        field.queryset = Player.objects.filter(team_id=team_id) if team_id else Player.objects.none()
        return field


class HomeGoalInline(BaseGoalInline):
    """Inline goals for the home team."""
    verbose_name = "Home goal"
    verbose_name_plural = "Home goals"
    team_side = "home"


class AwayGoalInline(BaseGoalInline):
    """Inline goals for the away team."""
    verbose_name = "Away goal"
    verbose_name_plural = "Away goals"
    team_side = "away"


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    """Admin configuration for matches, with inline goals and MVP filtering via MatchForm."""
    form = MatchForm
    inlines = [HomeGoalInline, AwayGoalInline]

    list_display = (
        "date",
        "time",
        "stage",
        "group",
        "home_team",
        "away_team",
        "score_home_team",
        "score_away_team",
        "validated",
        "dts",
        "dcr",
    )
    list_filter = ("stage", "group", "validated", "dts", "dcr", "date")
    search_fields = ("home_team__name", "away_team__name", "group", "stage", "note")
    ordering = ("date", "time")
    list_select_related = ("home_team", "away_team", "mvp")
    autocomplete_fields = ("home_team", "away_team")

    fieldsets = (
        (None, {
            "fields": (
                ("date", "time"),
                ("stage", "group"),
                ("home_team", "away_team"),
                ("score_home_team", "score_away_team"),
                ("dts", "dcr"),
                ("mvp", "validated"),
                "note",
            )
        }),
    )


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    """Admin configuration for goals (mostly redundant if you use Match inline, but useful for audits)."""
    list_display = ("match", "player", "number_of_goals")
    list_filter = ("match__date", "match__stage", "match__group", "player__team")
    search_fields = ("player__surname", "player__name", "player__team__name", "match__group", "match__stage")
    list_select_related = ("match", "player", "player__team")
    autocomplete_fields = ("match", "player")


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """Admin configuration for uploaded documents."""
    list_display = ("title", "file")
    search_fields = ("title",)

@admin.register(HallOfFame)
class HallOfFameAdmin(admin.ModelAdmin):
    """Admin configuration for the hall of fame"""
    form = HallOfFameForm
    list_display = ("year", "title", "display_team", "display_player")
    fields = ("year", "title", "team", "team_name", "player", "player_name")

    class Media:
        js = ("admin/hall_of_fame.js",)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "player-options/",
                self.admin_site.admin_view(self.player_options),
                name="halloffame-player-options",
            ),
        ]
        return custom_urls + urls

    def player_options(self, request):
        team_id = request.GET.get("team_id")
        if not team_id:
            return JsonResponse({"players": []})

        players = Player.objects.filter(team_id=team_id).order_by("surname", "name")
        payload = [{"id": player.id, "label": str(player)} for player in players]
        return JsonResponse({"players": payload})
