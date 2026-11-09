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


def main(argv: list[str] | None = None) -> int:
    args_list = sys.argv[1:] if argv is None else argv

    # Ohne Unterbefehl: IMMER das interaktive Menü aufbieten
    if not args_list:
        try:
            from . import menu
            return menu.run_menu()
        except Exception:
            # Fallback wenn kein TTY verfügbar ist: Übersichtliche Navigation ausgeben
            from . import ui
            ui.banner()
            ui.info("Verfügbare Befehle:")
            for cmd_name, mod in COMMANDS.items():
                ui.console.print(f"  [cyan]{cmd_name:10}[/cyan] [dim]{mod.HELP}[/dim]")
            ui.console.print("\n[dim]Aufruf mit: sdc <befehl> (z. B. 'sdc info' oder 'sdc doctor')[/dim]\n")
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
