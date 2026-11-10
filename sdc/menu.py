"""Interaktives Hauptmenü für sdc (wenn ohne Argumente gestartet)."""
from __future__ import annotations

import argparse
import socket
import questionary

from . import team_data, ui
from .commands import check, device, doctor, info, member, new, orca_cmd, secrets, setup_cmd, sync, team, update


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
        ui.choice_item("pull", "Secrets entschlüsseln (.env für lokale Entwicklung schreiben)", "pull", pad=8),
        ui.choice_item("check", "Prüfen, ob alle Empfänger und Pflicht-Secrets vorliegen", "check", pad=8),
        ui.choice_item("init", ".sops.yaml aus secrets/recipients.yml neu generieren", "init", pad=8),
        ui.choice_item("rekey", "Alle verschlüsselten Dateien für neue Empfänger aktualisieren", "rekey", pad=8),
        ui.choice_item("edit", "Verschlüsselte Datei im Editor öffnen", "edit", pad=8),
        questionary.Separator(),
        ui.choice_item("back", "Zurück zum Hauptmenü", "back", pad=8),
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

        # Schneller Tailnet-Scan nach Geräten, die auf Kopplung warten
        from .pairing import scan_beacons
        detected_beacons = scan_beacons(timeout=0.4)

        choices = []

        if detected_beacons:
            choices.append(questionary.Separator("── BEREIT ZUR KOPPLUNG (1-KLICK) ─────────────────────"))
            for b in detected_beacons:
                d_name = b.get("device_name", "unbekannt")
                ip = b.get("discovered_ip", "–")
                plat = b.get("platform", "linux")
                choices.append(
                    ui.choice_item(
                        "koppeln",
                        f"Neues Gerät '{d_name}' [{plat} · {ip}] sofort verbinden & berechtigen",
                        ("pair_auto", b),
                        pad=10,
                    )
                )

        choices.extend([
            questionary.Separator("── GERÄTE & TEAM ──────────────────────────────────────"),
            ui.choice_item("device", "Gerät registrieren (Notebook, age-Key, SSH, Secrets)", "device_add", pad=10),
            ui.choice_item("member", "Mitarbeiter anlegen (Kürzel, Name, Rolle, E-Mail)", "member_add", pad=10),
            ui.choice_item("team", "Team- und Geräte-Übersicht anzeigen", "team_list", pad=10),

            questionary.Separator("── ORCA & ENTWICKLER-TOOLS ────────────────────────────"),
            ui.choice_item("setup", "System-Setup (fehlende Tools, Orca, T3 Code nachinstallieren)", "setup", pad=10),
            ui.choice_item("orca", "Orca-Laufzeit (Status, Server starten, Remote-PC koppeln)", "orca", pad=10),
            ui.choice_item("update", "CLI & Entwickler-Tools auf den neuesten Stand bringen", "update", pad=10),

            questionary.Separator("── SECRETS & SICHERHEIT ───────────────────────────────"),
            ui.choice_item("secrets", "Secrets verwalten (pull, check, init, rekey, edit)", "secrets", pad=10),

            questionary.Separator("── PROJEKTE & VORLAGE ──────────────────────────────────"),
            ui.choice_item("sync", "Apps synchronisieren (alle oder einzelne klonen & pullen)", "sync", pad=10),
            ui.choice_item("new", "Neues Projekt anlegen (sdc new)", "new", pad=10),
            ui.choice_item("check", "Projekt prüfen (schoeni.yaml validieren)", "check", pad=10),

            questionary.Separator("── SYSTEM & DIAGNOSE ───────────────────────────────────"),
            ui.choice_item("info", "System- und Umgebungs-Info (sdc info)", "info", pad=10),
            ui.choice_item("doctor", "System- und Werkzeugdiagnose (sdc doctor)", "doctor", pad=10),

            questionary.Separator("──────────────────────────────────────────────────────"),
            ui.choice_item("exit", "Beenden", "exit", pad=10),
        ])

        choice = ui.select("Aktion auswählen:", choices=choices)

        if choice is None or choice == "exit":
            ui.console.print("\n[dim]Auf Wiedersehen.[/dim]\n")
            return 0

        ui.console.print()
        if isinstance(choice, tuple) and choice[0] == "pair_auto":
            b = choice[1]
            orca_cmd.do_connect(argparse.Namespace(code=b.get("discovered_ip"), name=b.get("device_name"), scan=False))
        elif choice == "device_add":
            device.run(argparse.Namespace(action="add"))
        elif choice == "member_add":
            member.run(argparse.Namespace(action="add"))
        elif choice == "team_list":
            team.run(argparse.Namespace())
        elif choice == "setup":
            setup_cmd.run(argparse.Namespace(yes=False, skip_orca=False, skip_t3=False, skip_docker=False))
        elif choice == "orca":
            orca_action = ui.select("Orca-Aktion wählen:", choices=[
                ui.choice_item("connect", "Remote-Notebook koppeln (automatischer Scan im Tailnet)", "connect", pad=10),
                ui.choice_item("init", "Dieses Notebook initialisieren & zur Kopplung freigeben", "init", pad=10),
                ui.choice_item("status", "Status, verbundene Runtimes & Umgebungen prüfen", "status", pad=10),
                ui.choice_item("serve", "Server starten (orca serve) - diesen PC für Orca freigeben", "serve", pad=10),
                questionary.Separator(),
                ui.choice_item("back", "Zurück zum Hauptmenü", "back", pad=10),
            ])
            if orca_action and orca_action != "back":
                orca_cmd.run(argparse.Namespace(action=orca_action, bind="0.0.0.0", port=6768, mobile=False, code=None, name=None, scan=False))
        elif choice == "secrets":
            _handle_secrets_menu()
        elif choice == "info":
            info.run(argparse.Namespace(json=False))
        elif choice == "doctor":
            doctor.run(argparse.Namespace(quiet=False))
        elif choice == "sync":
            sync.run(argparse.Namespace(app=None, all=False, status=False, clone_only=False, pull_only=False))
        elif choice == "new":
            app_name = ui.text("Name der neuen App / des Projekts:")
            if app_name:
                ns = argparse.Namespace(name=app_name, path=None, internal=True, customer=None, force=False)
                new.run(ns)
        elif choice == "check":
            check.run(argparse.Namespace(path="."))
        elif choice == "update":
            upd_choice = ui.select("Update-Aktion wählen:", choices=[
                ui.choice_item("cli", "sdc CLI jetzt aktualisieren (Forgejo / GitHub / lokal)", "cli", pad=8),
                ui.choice_item("tools", "sdc CLI und Basis-Tools (uv, Homebrew) aktualisieren", "all", pad=8),
                ui.choice_item("check", "Nur prüfen, ob Updates vorhanden sind (--check)", "check", pad=8),
                questionary.Separator(),
                ui.choice_item("back", "Zurück zum Hauptmenü", "back", pad=8),
            ])
            if upd_choice == "cli":
                update.run(argparse.Namespace(tools=False, force=False, check=False))
            elif upd_choice == "all":
                update.run(argparse.Namespace(tools=True, force=False, check=False))
            elif upd_choice == "check":
                update.run(argparse.Namespace(tools=False, force=False, check=True))

        ui.console.print()
        ui.pause("Enter drücken - zurück zum Hauptmenü ...")
