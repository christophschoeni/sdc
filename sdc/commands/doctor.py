"""sdc doctor: checks the tools a SCHOENI DIGITAL device needs."""
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

from ..paths import schema_path, workspace_root
from .. import ui

HELP = "Werkzeuge, Netz und Schlüssel auf diesem Gerät prüfen"

TOOLS = [
    ("git", "Git (Versionsverwaltung)"),
    ("uv", "Python-Paketmanager uv"),
    ("node", "Node.js (Laufzeitumgebung)"),
    ("podman", "Podman (lokale Container)"),
    ("sops", "SOPS (Secrets-Verschlüsselung)"),
    ("age", "age (Verschlüsselungs-Tool)"),
    ("tailscale", "Tailscale (Mesh-Netzwerk)"),
    ("hcloud", "Hetzner CLI hcloud"),
]


def register(p: argparse.ArgumentParser) -> None:
    p.add_argument("--quiet", action="store_true", help="nur Fehler ausgeben")


def _tailscale_up() -> bool | None:
    exe = shutil.which("tailscale")
    if not exe:
        return None
    try:
        out = subprocess.run([exe, "status", "--peers=false"], capture_output=True, text=True, timeout=5)
        return out.returncode == 0 and "Logged out" not in out.stdout
    except (subprocess.TimeoutExpired, OSError):
        return False


def run(args: argparse.Namespace) -> int:
    problems = 0
    rows: list[list[str]] = []

    for exe, label in TOOLS:
        found = shutil.which(exe)
        status = "[bold green]✔ OK[/bold green]" if found else "[bold red]✖ FEHLT[/bold red]"
        detail = f"[dim]{found}[/dim]" if found else f"[yellow]installieren: {exe}[/yellow]"
        rows.append([status, label, detail])
        if not found:
            problems += 1

    ts = _tailscale_up()
    if ts is not None:
        status = "[bold green]✔ OK[/bold green]" if ts else "[bold yellow]▲ AUS[/bold yellow]"
        detail = "[dim]verbunden[/dim]" if ts else "[yellow]tailscale up[/yellow]"
        rows.append([status, "Tailscale Netzwerk", detail])
        if not ts:
            problems += 1

    age_key = Path.home() / ".config" / "sops" / "age" / "keys.txt"
    has_age = age_key.exists()
    status = "[bold green]✔ OK[/bold green]" if has_age else "[bold red]✖ FEHLT[/bold red]"
    detail = f"[dim]{age_key}[/dim]" if has_age else "[yellow]mit 'sdc device add' erzeugen[/yellow]"
    rows.append([status, "age-Schlüssel (SOPS)", detail])
    if not has_age:
        problems += 1

    has_schema = schema_path().exists()
    status = "[bold green]✔ OK[/bold green]" if has_schema else "[bold red]✖ FEHLT[/bold red]"
    detail = f"[dim]{schema_path()}[/dim]" if has_schema else "[red]Schema-Datei fehlt[/red]"
    rows.append([status, "Manifest-Schema (schoeni.yaml)", detail])
    if not has_schema:
        problems += 1

    for d in ("core", "internal", "customers"):
        ok = (workspace_root() / d).is_dir()
        status = "[bold green]✔ OK[/bold green]" if ok else "[bold yellow]▲ FEHLT[/bold yellow]"
        detail = f"[dim]{workspace_root() / d}[/dim]" if ok else f"[yellow]Ordner {d}/ anlegen[/yellow]"
        rows.append([status, f"Projekt-Bereich {d}/", detail])
        if not ok:
            problems += 1

    cols = [
        ("Status", {"width": 10}),
        ("Komponente", {"style": "white bold", "width": 32}),
        ("Details / Pfad", {"style": "dim"}),
    ]

    ui.table("SCHOENI DIGITAL — System- & Werkzeugdiagnose", cols, rows)

    if problems == 0:
        ui.success("Dieses Gerät ist vollständig eingerichtet und einsatzbereit.")
    else:
        ui.warn(f"{problems} Punkt(e) offen oder noch nicht konfiguriert.")

    return 0 if problems == 0 else 1
