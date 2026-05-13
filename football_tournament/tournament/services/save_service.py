"""
Persistence helpers for LLM-parsed data.

save_roster(data)  – create/update Team + Player objects
save_result(data)  – update existing Match score + Goal objects

Team / player names from OCR are fuzzy-matched against existing DB records
via difflib to survive minor typos.
"""
import difflib

from tournament.models import Goal, Match, Player, Team

# ─── helpers ────────────────────────────────────────────────────────────────

def _fuzzy_match_team(name: str, cutoff: float = 0.6) -> Team | None:
    """Return the closest existing Team, or None if nothing is close enough."""
    all_names = list(Team.objects.values_list("name", flat=True))
    matches = difflib.get_close_matches(name, all_names, n=1, cutoff=cutoff)
    if matches:
        return Team.objects.get(name=matches[0])
    return None


def _fuzzy_match_player(
    name: str, surname: str, team: Team, cutoff: float = 0.6
) -> Player | None:
    """Return the closest existing Player in *team*, or None."""
    players = list(team.players.all())
    full_names = [f"{p.surname} {p.name}" for p in players]
    query = f"{surname} {name}"
    matches = difflib.get_close_matches(query, full_names, n=1, cutoff=cutoff)
    if matches:
        idx = full_names.index(matches[0])
        return players[idx]
    return None


# ─── public API ─────────────────────────────────────────────────────────────

def save_roster(data: dict) -> Team:
    """
    Create or update a Team and its Players from parsed roster data.

    Expected data shape:
        {
            "team_name": str,
            "players": [{"name": str, "surname": str, "number": int | None}, ...]
        }

    Returns the Team instance.
    """
    team_name: str = data["team_name"].strip()
    players_data: list[dict] = data.get("players", [])

    # Reuse existing team if name matches closely, else create
    team = _fuzzy_match_team(team_name) or Team.objects.create(name=team_name)

    for p in players_data:
        name = p.get("name", "").strip()
        surname = p.get("surname", "").strip()
        if not name and not surname:
            continue

        existing = _fuzzy_match_player(name, surname, team)
        if not existing:
            Player.objects.create(team=team, name=name, surname=surname)
        # If the player already exists we leave them as-is (avoid duplicates)

    return team


def save_result(data: dict) -> Match:
    """
    Update an existing Match with scores and Goal objects from parsed result data.

    Looks up the match by fuzzy-matching home/away team names against existing
    Match records. Replaces any existing Goals for that match with the new ones.

    Expected data shape:
        {
            "home_team": str,
            "away_team": str,
            "home_goals": int,
            "away_goals": int,
            "date": str | None,   # ISO-8601 date or null (used to narrow the search)
            "scorers": [{"name": str, "surname": str, "team": str}, ...]
        }

    Returns the updated Match instance.
    Raises ValueError if either team or the match itself cannot be resolved.
    """
    home_name: str = data["home_team"].strip()
    away_name: str = data["away_team"].strip()

    home_team = _fuzzy_match_team(home_name)
    away_team = _fuzzy_match_team(away_name)

    if home_team is None:
        raise ValueError(
            f"Could not find a team matching '{home_name}'. Fix the name and try again."
        )
    if away_team is None:
        raise ValueError(
            f"Could not find a team matching '{away_name}'. Fix the name and try again."
        )

    # Find the existing match between these two teams.
    # If a date was parsed, use it to narrow the search; otherwise take the latest.
    qs = Match.objects.filter(home_team=home_team, away_team=away_team)

    raw_date = data.get("date")
    if raw_date:
        try:
            from datetime import datetime as _dt
            parsed_date = _dt.fromisoformat(raw_date).date()
            date_qs = qs.filter(date=parsed_date)
            if date_qs.exists():
                qs = date_qs
        except (ValueError, TypeError):
            pass

    if not qs.exists():
        raise ValueError(
            f"No match found between '{home_team}' and '{away_team}'. "
            "Make sure the match has been scheduled first."
        )

    match = qs.order_by("-date").first()

    # Update scores
    match.score_home_team = int(data.get("home_goals", 0))
    match.score_away_team = int(data.get("away_goals", 0))
    match.save(update_fields=["score_home_team", "score_away_team"])

    # Replace existing goals for this match
    match.goal_set.all().delete()

    # Group scorers by player (handles multiple entries for same player)
    scorer_counts: dict[tuple[str, str, str], int] = {}
    for scorer in data.get("scorers", []):
        key = (
            scorer.get("name", "").strip(),
            scorer.get("surname", "").strip(),
            scorer.get("team", "").strip(),
        )
        scorer_counts[key] = scorer_counts.get(key, 0) + 1

    for (name, surname, team_name_raw), count in scorer_counts.items():
        scorer_team = _fuzzy_match_team(team_name_raw) if team_name_raw else None
        player = None

        if scorer_team:
            player = _fuzzy_match_player(name, surname, scorer_team)

        if player is None:
            # Fall back: search both sides
            player = _fuzzy_match_player(
                name, surname, home_team
            ) or _fuzzy_match_player(name, surname, away_team)

        Goal.objects.create(
            match=match,
            player=player,  # may be None if name couldn't be resolved
            number_of_goals=count,
        )

    return match
