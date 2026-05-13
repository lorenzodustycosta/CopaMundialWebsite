"""
Ollama LLM parser for WhatsApp messages (text or image).

Calls the local Ollama API to extract structured data
from team rosters and match results. All data stays on-device.
"""
import base64
import json
import tempfile
from pathlib import Path

import httpx

OLLAMA_URL = "http://localhost:11434/api/generate"
# MODEL = "llama3.2-vision"  # switch to "llama3.2-vision" once Ollama is updated to ≥0.6
MODEL = "qwen2.5vl:3b"  # switch to "llama3.2-vision" once Ollama is updated to ≥0.6

TIMEOUT = 300

_ROSTER_SCHEMA = {
    "team_name": "string",
    "players": [{"name": "string", "surname": "string", "number": "int or null"}],
}

_RESULT_SCHEMA = {
    "home_team": "string",
    "away_team": "string",
    "home_goals": "int",
    "away_goals": "int",
    "date": "string ISO-8601 or null",
    "scorers": [
        {"name": "string", "surname": "string", "team": "string"}
    ],
}

_ROSTER_PROMPT = (
    "You are a data extraction assistant for a 5-a-side football tournament. "
    "Extract the team name and player list from the following input. "
    "Players have a first name and a surname. The shirt number may or may not be present. "
    "A roster has between 5 and 12 players. "
    "Reply ONLY with valid JSON matching this schema exactly:\n"
    f"{json.dumps(_ROSTER_SCHEMA, indent=2)}\n\n"
    "Input:\n"
)

_RESULT_PROMPT = (
    "You are a data extraction assistant for a 5-a-side football tournament. "
    "Extract the match result from the following input. "
    "Identify home team, away team, their scores, the match date (if present), "
    "and for each scorer their name, surname, team they play for. "
    "Reply ONLY with valid JSON matching this schema exactly:\n"
    f"{json.dumps(_RESULT_SCHEMA, indent=2)}\n\n"
    "Input:\n"
)


def _read_image_as_base64(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _call_ollama(prompt: str, image_path: str | None = None) -> dict:
    payload: dict = {
        "model": MODEL,
        "prompt": prompt,
        "format": "json",
        "stream": False,
    }
    if image_path:
        payload["images"] = [_read_image_as_base64(image_path)]

    with httpx.Client(timeout=TIMEOUT) as client:
        response = client.post(OLLAMA_URL, json=payload)
        response.raise_for_status()

    raw = response.json().get("response", "")
    return json.loads(raw)


def parse_roster(text: str | None = None, image_path: str | None = None) -> dict:
    """
    Parse a team roster from pasted WhatsApp text or an image path.

    Returns a dict with keys: team_name, players (list of {name, surname, number}).
    Raises ValueError if neither text nor image_path is provided.
    Raises json.JSONDecodeError / httpx.HTTPError on parse/network failure.
    """
    if not text and not image_path:
        raise ValueError("Provide at least one of: text, image_path")

    prompt = _ROSTER_PROMPT + (text or "See the attached image.")
    return _call_ollama(prompt, image_path=image_path)


def parse_result(text: str | None = None, image_path: str | None = None) -> dict:
    """
    Parse a match result from pasted WhatsApp text or an image path.

    Returns a dict with keys: home_team, away_team, home_goals, away_goals,
    date, scorers (list of {name, surname, team}).
    Raises ValueError if neither text nor image_path is provided.
    Raises json.JSONDecodeError / httpx.HTTPError on parse/network failure.
    """
    if not text and not image_path:
        raise ValueError("Provide at least one of: text, image_path")

    prompt = _RESULT_PROMPT + (text or "See the attached image.")
    return _call_ollama(prompt, image_path=image_path)
