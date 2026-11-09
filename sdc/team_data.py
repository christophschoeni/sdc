"""Team- und Geräte-Verwaltung für SCHOENI DIGITAL (config/team.yml)."""
from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any
import yaml

from .paths import team_config_path

ROLES = ("owner", "developer", "ops", "viewer")


def load_team(path: Path | None = None) -> dict[str, Any]:
    f = path or team_config_path()
    if not f.exists():
        return {"version": "1", "members": []}
    content = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
    content.setdefault("version", "1")
    content.setdefault("members", [])
    return content


def save_team(data: dict[str, Any], path: Path | None = None) -> None:
    f = path or team_config_path()
    f.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "# SCHOENI DIGITAL — Team & Geräte-Verzeichnis\n"
        "# Verbindliche Erfassung aller Mitarbeiter und ihrer berechtigten Geräte.\n"
        "# Verwaltet durch `sdc member` und `sdc device`. Regeln: Entscheid 0015.\n\n"
    )
    dumped = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
    f.write_text(header + dumped, encoding="utf-8")


def find_member(member_id: str, team: dict[str, Any] | None = None, path: Path | None = None) -> dict[str, Any] | None:
    data = team if team is not None else load_team(path)
    for m in data.get("members", []):
        if m.get("id") == member_id:
            return m
    return None


def add_member(
    member_id: str,
    name: str,
    role: str = "developer",
    email: str = "",
    path: Path | None = None,
) -> dict[str, Any]:
    if role not in ROLES:
        raise ValueError(f"Ungültige Rolle '{role}'. Erlaubt: {', '.join(ROLES)}")
    
    data = load_team(path)
    existing = find_member(member_id, data)
    if existing:
        raise ValueError(f"Mitarbeiter mit ID '{member_id}' existiert bereits ({existing.get('name')})")

    member = {
        "id": member_id,
        "name": name,
        "role": role,
        "email": email,
        "created": dt.date.today().isoformat(),
        "devices": [],
    }
    data["members"].append(member)
    save_team(data, path)
    return member


def add_device(
    member_id: str,
    device_id: str,
    device_name: str,
    age_pub: str,
    ssh_pub: str = "",
    path: Path | None = None,
) -> dict[str, Any]:
    data = load_team(path)
    member = find_member(member_id, data)
    if not member:
        raise ValueError(f"Mitarbeiter '{member_id}' nicht gefunden. Zuerst mit `sdc member add` anlegen.")

    # Prüfen, ob device_id bereits vergeben ist
    for m in data.get("members", []):
        for d in m.get("devices", []):
            if d.get("id") == device_id:
                raise ValueError(f"Geräte-ID '{device_id}' existiert bereits bei Mitarbeiter '{m.get('id')}'")
            if d.get("age") == age_pub:
                raise ValueError(f"Dieser age-Schlüssel ist bereits als '{d.get('id')}' ({m.get('id')}) hinterlegt")

    device = {
        "id": device_id,
        "name": device_name,
        "age": age_pub,
        "ssh": ssh_pub,
        "added": dt.date.today().isoformat(),
    }
    member.setdefault("devices", []).append(device)
    save_team(data, path)
    return device


def list_members(path: Path | None = None) -> list[dict[str, Any]]:
    return load_team(path).get("members", [])


def list_all_devices(path: Path | None = None) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Gibt eine Liste von Paaren (member, device) zurück."""
    out = []
    for m in list_members(path):
        for d in m.get("devices", []):
            out.append((m, d))
    return out
