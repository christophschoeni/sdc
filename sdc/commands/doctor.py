"""sdc doctor: checks the tools a SCHOENI DIGITAL device needs."""
from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
from pathlib import Path

from ..paths import schema_path, workspace_root
from .. import ui

HELP = "Werkzeuge, Container, Orca, T3 Code, Netz und Schlüssel prüfen"

DEV_TOOLS = [
    ("git", "Git (Versionsverwaltung)", True),
    ("uv", "Python-Paketmanager uv", True),
    ("node", "Node.js (Laufzeitumgebung)", True),
    ("sops", "SOPS (Secrets-Verschlüsselung)", True),
    ("age", "age (Verschlüsselungs-Tool)", True),
    ("tailscale", "Tailscale (Mesh-Netzwerk)", True),
    ("hcloud", "Hetzner CLI hcloud", False),
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


def _find_container_engine() -> tuple[str, str] | None:
    """Findet Docker oder Podman. Docker CLI genügt völlig (Podman nur wenn Docker fehlt)."""
    docker = shutil.which("docker")
    if docker:
        return ("Docker CLI", docker)
    podman = shutil.which("podman")
    if podman:
        return ("Podman", podman)
    return None


def _find_orca() -> tuple[str, str] | None:
    exe = shutil.which("orca")
    if exe:
        return ("Orca CLI", exe)
    if platform.system() == "Darwin":
        app = Path("/Applications/Orca.app")
        if app.exists():
            return ("Orca.app", str(app))
    return None


def _find_t3_code() -> tuple[str, str] | None:
    exe = shutil.which("t3")
    if exe:
        return ("T3 Code CLI", exe)
    if platform.system() == "Darwin":
        for p in ("/Applications/T3 Code.app", "/Applications/T3 Code (Beta).app"):
            if Path(p).exists():
                return ("T3 Code.app", p)
    return None


def run(args: argparse.Namespace) -> int:
    problems = 0
    rows: list[list[str]] = []

    # 1. Standard Developer Tools
    for exe, label, required in DEV_TOOLS:
        found = shutil.which(exe)
        if found:
            status = r"[bold green]\[ok][/bold green]"
            detail = f"[dim]{found}[/dim]"
        else:
            if required:
                status = r"[bold red]\[fehlt][/bold red]"
                detail = f"[yellow]installieren (z. B. 'sdc setup')[/yellow]"
                problems += 1
            else:
                status = r"[dim]\[optional][/dim]"
                detail = f"[dim]nicht installiert[/dim]"
        rows.append([status, label, detail])

    # 2. Container Engine (Docker CLI oder Podman)
    engine = _find_container_engine()
    if engine:
        status = r"[bold green]\[ok][/bold green]"
        rows.append([status, f"Container: {engine[0]}", f"[dim]{engine[1]}[/dim]"])
    else:
        status = r"[bold yellow]\[fehlt][/bold yellow]"
        rows.append([status, "Container-Laufzeit (Docker oder Podman)", "[yellow]Docker CLI oder Podman installieren[/yellow]"])
        problems += 1

    # 3. Orca Agenten-Umgebung
    orca_info = _find_orca()
    if orca_info:
        status = r"[bold green]\[ok][/bold green]"
        rows.append([status, f"Orca Agent ({orca_info[0]})", f"[dim]{orca_info[1]}[/dim]"])
    else:
        status = r"[bold yellow]\[fehlt][/bold yellow]"
        rows.append([status, "Orca Agent & CLI", "[yellow]installieren: 'sdc setup' oder onorca.dev[/yellow]"])
        problems += 1

    # 4. T3 Code
    t3_info = _find_t3_code()
    if t3_info:
        status = r"[bold green]\[ok][/bold green]"
        rows.append([status, f"T3 Code ({t3_info[0]})", f"[dim]{t3_info[1]}[/dim]"])
    else:
        status = r"[bold yellow]\[fehlt][/bold yellow]"
        rows.append([status, "T3 Code", "[yellow]installieren: 'sdc setup' oder t3.codes[/yellow]"])
        problems += 1

    # 5. Tailscale Mesh
    ts = _tailscale_up()
    if ts is not None:
        status = r"[bold green]\[ok][/bold green]" if ts else r"[bold yellow]\[warn][/bold yellow]"
        detail = "[dim]verbunden[/dim]" if ts else "[yellow]tailscale up ausführen[/yellow]"
        rows.append([status, "Tailscale Netzwerk", detail])
        if not ts:
            problems += 1

    # 6. age-Schlüssel (SOPS)
    age_key = Path.home() / ".config" / "sops" / "age" / "keys.txt"
    has_age = age_key.exists()
    status = r"[bold green]\[ok][/bold green]" if has_age else r"[bold red]\[fehlt][/bold red]"
    detail = f"[dim]{age_key}[/dim]" if has_age else "[yellow]mit 'sdc device add' erzeugen[/yellow]"
    rows.append([status, "age-Schlüssel (SOPS)", detail])
    if not has_age:
        problems += 1

    # 7. Manifest-Schema (schoeni.yaml)
    has_schema = schema_path().exists()
    status = r"[bold green]\[ok][/bold green]" if has_schema else r"[bold red]\[fehlt][/bold red]"
    detail = f"[dim]{schema_path()}[/dim]" if has_schema else "[red]Schema-Datei fehlt[/red]"
    rows.append([status, "Manifest-Schema (schoeni.yaml)", detail])
    if not has_schema:
        problems += 1

    cols = [
        ("Status", {"width": 12}),
        ("Komponente", {"style": "white bold", "width": 36}),
        ("Details / Pfad", {"style": "dim"}),
    ]

    ui.table("SCHOENI DIGITAL — System- & Werkzeugdiagnose", cols, rows)

    if problems == 0:
        ui.success("Dieses Gerät ist vollständig eingerichtet und einsatzbereit.")
    else:
        ui.warn(f"{problems} Punkt(e) offen oder noch nicht konfiguriert. Tipp: Führe 'sdc setup' aus.")

    return 0 if problems == 0 else 1
