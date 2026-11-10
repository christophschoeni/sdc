"""sdc access: who may decrypt an app's secrets (age recipients). list · grant · revoke.

Edits secrets/recipients.yml, regenerates .sops.yaml and re-encrypts every vault file,
so the change is real, not just declared (decision 0015).
"""
import re
from pathlib import Path

import yaml

from .secrets import AGE_PUB, do_init, do_rekey, load_recipients

HELP = "Zugriff auf den Tresor: list · grant <name> <age1…> · revoke <name>"


def register(p):
    p.add_argument("action", choices=["list", "grant", "revoke"])
    p.add_argument("name", nargs="?", help="Name der Person/des Geräts, z.B. cs_lenovo")
    p.add_argument("age_key", nargs="?", help="öffentlicher age-Schlüssel (age1…)")
    p.add_argument("--role", default="member", help="owner | member | recovery | ci (Standard: member)")
    p.add_argument("--path", default=".", help="App-Ordner (Standard: .)")


def _save(app: Path, recs: list[dict]) -> None:
    f = app / "secrets" / "recipients.yml"
    f.write_text("# Binding list of who may decrypt this app's secrets. Managed by `sdc access`.\n"
                 "# .sops.yaml is generated from this file (sdc secrets init); after changes: sdc secrets rekey.\n"
                 + yaml.safe_dump({"recipients": recs}, sort_keys=False))


def run(args) -> int:
    app = Path(args.path).resolve()
    recs = load_recipients(app)
    if args.action == "list":
        print(f"Empfänger für {app.name}:")
        for r in recs:
            key = str(r.get("age", ""))
            state = "ok" if AGE_PUB.match(key) else "PLATZHALTER"
            print(f"  {r['name']:20} {r.get('role','?'):9} {key[:14]}…  {state}")
        return 0
    if not args.name or not re.match(r"^[a-z][a-z0-9_-]{1,30}$", args.name):
        raise ValueError("Name fehlt oder ungültig (klein, a-z 0-9 _ -)")
    if args.action == "grant":
        if not args.age_key or not AGE_PUB.match(args.age_key):
            raise ValueError("öffentlicher age-Schlüssel fehlt oder ungültig (age1… mit 62 Zeichen)")
        if any(r.get("age") == args.age_key for r in recs):
            print("Schlüssel ist schon Empfänger"); return 0
        recs = [r for r in recs if r["name"] != args.name]
        recs.append({"name": args.name, "role": args.role, "age": args.age_key})
        _save(app, recs)
        print(f"{args.name} eingetragen ({args.role})")
    else:
        if not any(r["name"] == args.name for r in recs):
            raise ValueError(f"kein Empfänger namens {args.name}")
        recs = [r for r in recs if r["name"] != args.name]
        if len(recs) < 2:
            raise ValueError("mindestens zwei Empfänger müssen bleiben (Bus-Faktor, Entscheid 0015)")
        _save(app, recs)
        print(f"{args.name} entfernt — der Schlüssel kann neue Stände nicht mehr lesen; alte Git-Stände bleiben lesbar, Secrets bei Verdacht rotieren")
    do_init(app)
    return do_rekey(app)
