"""SCHOENI DIGITAL CLI (`sdc`) — Haupteinstiegspunkt."""
from __future__ import annotations

import argparse
import sys

from . import __version__
from .commands import check, device, doctor, info, member, new, orca_cmd, secrets, setup_cmd, team, update

COMMANDS = {
    "info": info,
    "doctor": doctor,
    "setup": setup_cmd,
    "update": update,
    "orca": orca_cmd,
    "new": new,
    "check": check,
    "secrets": secrets,
    "member": member,
    "device": device,
    "team": team,
}


COMMAND_GROUPS = [
    (
        "GERÄTE & TEAM",
        [
            ("device", "Notebooks/Geräte hinzufügen, Schlüssel generieren und für Secrets berechtigen"),
            ("member", "Mitarbeiter anlegen und verwalten (Name, Rolle, E-Mail)"),
            ("team", "Team-Übersicht: Mitarbeiter, Rollen und deren registrierte Geräte"),
        ],
    ),
    (
        "ORCA & ENTWICKLER-TOOLS",
        [
            ("setup", "Alle benötigten Entwickler-Tools, Orca und T3 Code auf diesem Gerät installieren"),
            ("orca", "Orca Agenten-Laufzeit verwalten und Arbeitsrechner miteinander koppeln"),
            ("update", "sdc CLI und Entwickler-Tools auf den neuesten Stand aktualisieren"),
        ],
    ),
    (
        "SECRETS & SICHERHEIT",
        [
            ("secrets", "Secrets mit SOPS + age: init · set · edit · pull · check · rekey"),
        ],
    ),
    (
        "PROJEKTE & VORLAGE",
        [
            ("new", "Neue App aus der Vorlage anlegen (internal oder customer)"),
            ("check", "schoeni.yaml gegen das Schema prüfen"),
        ],
    ),
    (
        "SYSTEM & DIAGNOSE",
        [
            ("info", "Übersicht über SCHÖNI DIGITAL, System, Schlüssel und Projektstand"),
            ("doctor", "Werkzeuge, Container, Orca, T3 Code, Netz und Schlüssel prüfen"),
        ],
    ),
]


def print_grouped_help() -> None:
    from . import ui
    ui.banner()
    ui.console.print("[bold white]Befehlsübersicht nach Gruppen:[/bold white]\n")
    for group_name, cmds in COMMAND_GROUPS:
        ui.console.print(f"[bold cyan]── {group_name} ──────────────────────────────────────[/bold cyan]")
        for cmd_name, desc in cmds:
            ui.console.print(f"  [bold #00d2ff]{cmd_name:<10}[/bold #00d2ff] [dim]›[/dim]  [white]{desc}[/white]")
        ui.console.print()
    ui.console.print("[bold cyan]── OPTIONEN ──────────────────────────────────────────[/bold cyan]")
    ui.console.print("  [bold #00d2ff]--help    [/bold #00d2ff] [dim]›[/dim]  [white]Diese Hilfe anzeigen[/white]")
    ui.console.print("  [bold #00d2ff]--version [/bold #00d2ff] [dim]›[/dim]  [white]Installierte Version ausgeben[/white]\n")
    ui.console.print("[dim]Aufruf mit: sdc <befehl> (z. B. 'sdc update' oder 'sdc info')[/dim]\n")


def main(argv: list[str] | None = None) -> int:
    args_list = sys.argv[1:] if argv is None else argv

    # Globale Hilfe mit Gruppen und gestalteten Variablen ausgeben
    if args_list in (["-h"], ["--help"], ["help"]):
        print_grouped_help()
        return 0

    # Ohne Unterbefehl: IMMER das interaktive Menü aufbieten
    if not args_list:
        try:
            from . import menu
            return menu.run_menu()
        except Exception:
            # Fallback wenn kein TTY verfügbar ist
            print_grouped_help()
            return 0

    parser = argparse.ArgumentParser(
        prog="sdc",
        description="SCHOENI DIGITAL CLI — Entwickler- & Administrations-Zentrale",
        epilog="Ohne Argumente gestartet, öffnet sdc automatisch das interaktive Dashboard.",
    )
    parser.add_argument("--version", action="version", version=f"sdc {__version__}")
    sub = parser.add_subparsers(dest="command", required=False)
    for name, mod in COMMANDS.items():
        mod.register(sub.add_parser(name, help=mod.HELP))

    args = parser.parse_args(args_list)

    if not args.command:
        try:
            from . import menu
            return menu.run_menu()
        except Exception:
            parser.print_help()
            return 0

    try:
        return COMMANDS[args.command].run(args)
    except KeyboardInterrupt:
        return 130
    except Exception as exc:  # soft-fail: Ein Fehler crasht nie unformatiert das CLI
        print(f"sdc {args.command}: Fehler: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
