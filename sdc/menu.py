"""Interaktives Startmenü für sdc (wenn ohne Argumente gestartet)."""
from __future__ import annotations

import argparse
import socket
from rich.text import Text
import questionary

from . import team_data, ui
from .commands import check, device, doctor, member, new, secrets, team


def _context_info() -> tuple[str | None, str | None]:
    """Ermittelt Kontext-Informationen für das Banner."""
    members = team_data.list_members()
    owner = next((m for m in members if m.get("role") == "owner"), None)
    user_str = f"{owner['name']} ({owner['id']})" if owner else (members[0]['name'] if members else None)

    dev_count = sum(len(m.get("devices", [])) for m in members)
    device_str = f"{dev_count} Gerät(e) registriert" if dev_count > 0 else socket.gethostname()
    return user_str, device_str


def _handle_secrets_menu() -> None:
    ui.step("Secrets-Verwaltung (SOPS + age)")
    sec_choices = [
        {"name": "📥 pull   — Secrets entschlüsseln (.env für lokale Entwicklung schreiben)", "value": "pull"},
        {"name": "🔍 check  — Prüfen, ob alle Empfänger und Pflicht-Secrets vorliegen", "value": "check"},
        {"name": "🔑 init   — .sops.yaml aus secrets/recipients.yml neu generieren", "value": "init"},
        {"name": "🔄 rekey  — Alle verschlüsselten Dateien für neue Empfänger aktualisieren", "value": "rekey"},
        {"name": "📝 edit   — Verschlüsselte Datei im Editor öffnen", "value": "edit"},
        questionary.Separator(),
        {"name": "⬅️ Zurück zum Hauptmenü", "value": "back"},
    ]
    action = ui.select("Secrets-Aktion wählen:", choices=sec_choices)
    if not action or action == "back":
        return

    ns = argparse.Namespace(path=".", env="dev", yes=False, name=None, value_from_stdin=False, action=action)
    try:
        secrets.run(ns)
    except Exception as exc:
        ui.error(f"Secrets-Fehler: {exc}")


def run_menu() -> int:
    while True:
        ui.clear()
        user_info, dev_info = _context_info()
        ui.banner(user_info=user_info, device_info=dev_info)

        choices = [
            questionary.Separator("── GERÄTE & TEAM ─────────────────────────"),
            {"name": "💻 Notebook / Gerät hinzufügen (Age-Key, SSH, Secrets)", "value": "device_add"},
            {"name": "👤 Mitarbeiter hinzufügen (Kürzel, Name, Rolle)", "value": "member_add"},
            {"name": "👥 Team & Geräte anzeigen (Gesamtsicht)", "value": "team_list"},

            questionary.Separator("── SECRETS & SICHERHEIT ─────────────────"),
            {"name": "🔐 Secrets verwalten (pull, check, init, rekey)", "value": "secrets"},

            questionary.Separator("── PROJEKTE & VORLAGE ───────────────────"),
            {"name": "✨ Neues Projekt anlegen (sdc new)", "value": "new"},
            {"name": "🔍 Projekt prüfen (schoeni.yaml validieren)", "value": "check"},

            questionary.Separator("── DIAGNOSE ─────────────────────────────"),
            {"name": "🩺 System & Werkzeuge prüfen (sdc doctor)", "value": "doctor"},

            questionary.Separator("─────────────────────────────────────────"),
            {"name": "🚪 Beenden", "value": "exit"},
        ]

        choice = ui.select("Was möchtest du tun?", choices=choices)

        if choice is None or choice == "exit":
            ui.console.print("\n[dim]Auf Wiedersehen![/dim]\n")
            return 0

        ui.console.print()
        if choice == "device_add":
            ns = argparse.Namespace(action="add")
            device.run(ns)
        elif choice == "member_add":
            ns = argparse.Namespace(action="add")
            member.run(ns)
        elif choice == "team_list":
            team.run(argparse.Namespace())
        elif choice == "secrets":
            _handle_secrets_menu()
        elif choice == "doctor":
            doctor.run(argparse.Namespace(quiet=False))
        elif choice == "new":
            app_name = ui.text("Name der neuen App / des Projekts:")
            if app_name:
                ns = argparse.Namespace(name=app_name, path=None, internal=True, customer=None, force=False)
                new.run(ns)
        elif choice == "check":
            check.run(argparse.Namespace(path="."))

        ui.console.print()
        ui.pause("Enter drücken — zurück zum Hauptmenü …")
