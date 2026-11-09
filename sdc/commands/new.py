"""sdc new: creates an app folder from the template with its schoeni.yaml."""
import re
import shutil
from pathlib import Path

import yaml

from ..paths import template_root, workspace_root
from .check import validate

HELP = "neue App aus der Vorlage anlegen (internal oder customer)"
NAME_RE = re.compile(r"^[a-z][a-z0-9_-]{1,40}$")


def register(p):
    p.add_argument("name", help="Projektname, klein: a-z 0-9 _ -")
    p.add_argument("--kind", choices=["internal", "customer"], required=True)
    p.add_argument("--customer", help="Kundenkürzel (Pflicht bei --kind customer)")
    p.add_argument("--deploy", choices=["coolify", "kamal", "none"], default="coolify")
    p.add_argument("--owner", default="cs")
    p.add_argument("--dry-run", action="store_true")


def target_dir(name: str, kind: str, customer: str | None) -> Path:
    root = workspace_root()
    if kind == "customer":
        return root / "customers" / customer / f"{customer}_{name}"
    return root / "internal" / name


def build_manifest(name: str, kind: str, customer: str | None, deploy: str, owner: str) -> dict:
    tpl = yaml.safe_load((template_root() / "schoeni.yaml").read_text())
    project = f"{customer}_{name}" if kind == "customer" else name
    m = dict(tpl)
    m.update({"project": project, "kind": kind, "stage": "dev", "owner": owner,
              "repo": {"host": "forgejo", "path": f"schoeni-digital/{project}", "mirror": "github"},
              "deploy": {"tool": deploy}})
    if kind == "customer":
        m["customer"] = customer
    return m


def run(args) -> int:
    if not NAME_RE.match(args.name):
        raise ValueError("Name: klein, a-z 0-9 _ -, 2-41 Zeichen")
    if args.kind == "customer" and not (args.customer and NAME_RE.match(args.customer)):
        raise ValueError("--customer <kürzel> ist Pflicht bei --kind customer")
    dest = target_dir(args.name, args.kind, args.customer)
    if dest.exists():
        raise FileExistsError(f"existiert schon: {dest}")
    manifest = build_manifest(args.name, args.kind, args.customer, args.deploy, args.owner)
    errors = validate(manifest)
    if errors:
        raise ValueError("Manifest ungültig: " + "; ".join(errors))
    if args.dry_run:
        print(f"würde anlegen: {dest}")
        print(yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True))
        return 0
    shutil.copytree(template_root(), dest, ignore=shutil.ignore_patterns("schoeni.yaml", "README.md"))
    header = "# yaml-language-server: $schema=../../core/template/schemas/schoeni.schema.json\n"
    if args.kind == "customer":
        header = header.replace("../../", "../../../")
    (dest / "schoeni.yaml").write_text(header + yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True))
    (dest / "README.md").write_text(f"# {manifest['project']}\n\nAus `schoeni_template` {manifest.get('template_version')} erzeugt. Steckbrief: `schoeni.yaml`.\n")
    print(f"angelegt: {dest}")
    print("nächste Schritte: git init · Repo in Forgejo anlegen · Spiegel · sdc check")
    return 0
