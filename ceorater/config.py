"""API key storage and retrieval."""

import json
import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".ceorater"
CONFIG_FILE = CONFIG_DIR / "config.json"

ENV_VAR = "CEORATER_API_KEY"


def save_key(api_key: str) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(
        json.dumps({"api_key": api_key}, indent=2),
        encoding="utf-8",
    )


def load_key() -> str | None:
    key = os.environ.get(ENV_VAR)
    if key:
        return key
    if not CONFIG_FILE.exists():
        return None
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return data.get("api_key") or None
    except (json.JSONDecodeError, OSError):
        return None
