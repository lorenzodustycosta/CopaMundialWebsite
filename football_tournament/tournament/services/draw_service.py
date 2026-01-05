# tournament/services/draw_service.py
from __future__ import annotations

from dataclasses import dataclass
from django.db.models import Count
from tournament.models import Group, Team


@dataclass(frozen=True)
class DrawStatus:
    """
    This class represents the status of the draw
    """
    ok: bool
    reason: str = ""


def validate_draw_completed_equal_groups() -> DrawStatus:
    # All the reams must have a group
    if Team.objects.filter(group__isnull=True).exists():
        return DrawStatus(ok=False, reason="Ci sono squadre non assegnate a nessun gruppo.")

    # All the groups must have the same number of teams
    groups = Group.objects.annotate(n=Count("teams")).order_by("name")
    counts = [g.n for g in groups]

    if not counts:
        return DrawStatus(ok=False, reason="Non ci sono gruppi.")

    if min(counts) != max(counts):
        return DrawStatus(ok=False, reason=f"Gruppi sbilanciati: {counts}")

    if counts[0] < 2:
        return DrawStatus(ok=False, reason="Ogni gruppo deve avere almeno 2 squadre.")

    return DrawStatus(ok=True)