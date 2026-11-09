import argparse
import sys

from . import __version__
from .commands import check, device, doctor, member, new, secrets, team

COMMANDS = {
    "doctor": doctor,
    "new": new,
    "check": check,
    "secrets": secrets,
    "member": member,
    "device": device,
    "team": team,
}


def main(argv: list[str] | None = None) -> int:
    # Wenn keine Argumente übergeben werden und ein interaktives Terminal da ist: Menü starten
    if argv is None and len(sys.argv) <= 1:
        if sys.stdin.isatty():
            from . import menu
            return menu.run_menu()

    parser = argparse.ArgumentParser(prog="sdc", description="SCHOENI DIGITAL CLI — Entwickler- & Admin-Zentrale")
    parser.add_argument("--version", action="version", version=f"sdc {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, mod in COMMANDS.items():
        mod.register(sub.add_parser(name, help=mod.HELP))
    
    # Auch wenn argv übergeben wird, aber leer ist: Hilfe anzeigen
    if argv == []:
        parser.print_help()
        return 0

    args = parser.parse_args(argv)
    try:
        return COMMANDS[args.command].run(args)
    except KeyboardInterrupt:
        return 130
    except Exception as exc:  # soft-fail: one broken command never crashes the CLI
        print(f"sdc {args.command}: Fehler: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
