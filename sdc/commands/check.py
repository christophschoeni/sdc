"""sdc check: validates schoeni.yaml against the schema."""
import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from ..paths import schema_path

HELP = "schoeni.yaml gegen das Schema prüfen"


def register(p):
    p.add_argument("path", nargs="?", default=".", help="App-Ordner oder Manifest (Standard: .)")


def load_manifest(path: Path) -> dict:
    f = path / "schoeni.yaml" if path.is_dir() else path
    if not f.exists():
        raise FileNotFoundError(f"kein Manifest: {f}")
    return yaml.safe_load(f.read_text()) or {}


def validate(manifest: dict) -> list[str]:
    schema = json.loads(schema_path().read_text())
    v = Draft202012Validator(schema)
    return [f"{'/'.join(str(x) for x in e.path) or '<root>'}: {e.message}" for e in sorted(v.iter_errors(manifest), key=str)]


def run(args) -> int:
    manifest = load_manifest(Path(args.path))
    errors = validate(manifest)
    if errors:
        print("Manifest ungültig:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"Manifest gültig: {manifest.get('project')} ({manifest.get('kind')}, {manifest.get('stage')})")
    return 0
