"""sdc member: Mitarbeiter in SCHOENI DIGITAL verwalten."""
from __future__ import annotations

import argparse
from .. import team_data, ui

HELP = "Mitarbeiter anlegen und verwalten (Name, Rolle, E-Mail)"


def register(p: argparse.ArgumentParser) -> None:
    sub = p.add_subparsers(dest="action", required=False)

    p_add = sub.add_parser("add", help="Neuen Mitarbeiter hinzufügen")
    p_add.add_argument("--id", help="Eindeutiges Kürzel (z. B. cschoeni, mmueller)")
    p_add.add_argument("--name", help="Vollständiger Name (z. B. Christoph Schöni)")
    p_add.add_argument("--role", choices=team_data.ROLES, default="developer", help="Rolle im Team (owner, developer, ops, viewer)")
    p_add.add_argument("--email", default="", help="E-Mail-Adresse")

    sub.add_parser("list", help="Alle Mitarbeiter auflisten")


def do_add(args: argparse.Namespace) -> int:
    member_id = getattr(args, "id", None)
    name = getattr(args, "name", None)
    role = getattr(args, "role", "developer") or "developer"
    email = getattr(args, "email", "") or ""

    # Interaktiver Modus
    if not member_id or not name:
        ui.step("Neuen Mitarbeiter erfassen")
        if not member_id:
            member_id = ui.text("Kürzel des Mitarbeiters (z. B. cschoeni):")
        if not name:
            name = ui.text("Vollständiger Name (z. B. Christoph Schöni):")
        if not getattr(args, "role", None):
            role_choices = [
                {"name": "developer — Entwickler (Standard)", "value": "developer"},
                {"name": "ops       — Betrieb & Infrastruktur", "value": "ops"},
                {"name": "owner     — Eigentümer / Geschäftsleitung", "value": "owner"},
                {"name": "viewer    — Lesender Zugriff", "value": "viewer"},
            ]
            role = ui.select("Rolle im Team:", choices=role_choices, default="developer")
        if not email:
            email = ui.text("E-Mail-Adresse (optional):")

    if not member_id or not name:
        ui.error("Kürzel (--id) und Name (--name) sind erforderlich.")
        return 1

    member_id = member_id.strip().lower()
    name = name.strip()
    email = email.strip()

    try:
        with ui.spinner("Speichere Mitarbeiter …"):
            m = team_data.add_member(member_id, name, role, email)
        ui.success(f"Mitarbeiter angelegt: [bold white]{m['name']}[/bold white] ([cyan]{m['id']}[/cyan]) · Rolle: [green]{m['role']}[/green]")
        ui.info("Nächster Schritt: Ein Notebook/Gerät für diesen Mitarbeiter mit 'sdc device add' zuweisen.")
        return 0
    except ValueError as err:
        ui.error(str(err))
        return 1


def do_list() -> int:
    members = team_data.list_members()
    if not members:
        ui.warn("Noch keine Mitarbeiter erfasst. Mit 'sdc member add' anlegen.")
        return 0

    cols = [
        ("Kürzel", {"style": "cyan bold"}),
        ("Name", {"style": "white bold"}),
        ("Rolle", {"style": "green"}),
        ("E-Mail", {"style": "dim"}),
        ("Registrierte Geräte", {"style": "yellow"}),
    ]
    rows = []
    for m in members:
        devices_str = ", ".join(d.get("id", "") for d in m.get("devices", [])) or "–"
        rows.append([m.get("id", ""), m.get("name", ""), m.get("role", ""), m.get("email", "") or "–", devices_str])

    ui.table("SCHOENI DIGITAL — Teammitglieder", cols, rows)
    return 0


def run(args: argparse.Namespace) -> int:
    action = getattr(args, "action", None)
    if action == "add":
        return do_add(args)
    if action == "list" or not action:
        return do_list()
    ui.error(f"Unbekannte Aktion: {action}")
    return 1
