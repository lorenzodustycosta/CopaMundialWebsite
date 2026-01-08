from django.contrib import admin
from django import forms

from .forms import MatchForm
from .models import Group, Team, Player, Match, Goal, Document


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


class GoalInline(admin.TabularInline):
    """Inline goals inside Match admin."""
    model = Goal
    form = GoalInlineForm
    extra = 0
    fields = ("player", "number_of_goals")
    autocomplete_fields = ("player",)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Filter player choices to home/away team players (including fake autogoal).
        """
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)

        if db_field.name == "player":
            # Match ID is in the URL for change view: /admin/app/match/<id>/change/
            # We can try to parse it safely.
            match_id = None
            try:
                # request.resolver_match.kwargs often includes 'object_id' in admin
                match_id = request.resolver_match.kwargs.get("object_id")
            except Exception:
                match_id = None

            if match_id:
                try:
                    match = Match.objects.select_related("home_team", "away_team").get(pk=match_id)
                    valid_team_ids = [match.home_team_id, match.away_team_id]
                    field.queryset = Player.objects.filter(team_id__in=valid_team_ids)
                except Match.DoesNotExist:
                    field.queryset = Player.objects.none()
            else:
                # On "add match" page, teams aren't chosen yet -> keep empty to avoid wrong selections.
                field.queryset = Player.objects.none()

        return field


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    """Admin configuration for matches, with inline goals and MVP filtering via MatchForm."""
    form = MatchForm
    inlines = [GoalInline]

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
    autocomplete_fields = ("home_team", "away_team", "mvp")

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
