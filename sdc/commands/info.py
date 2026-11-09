"""sdc info: Übersicht über SCHÖNI DIGITAL, CLI-Stand, Umgebung und Werkzeuge."""
from __future__ import annotations

import argparse
import os
import platform
import shutil
import socket
from pathlib import Path

from .. import __version__, keys, team_data, ui
from ..paths import core_root, schema_path, template_root

HELP = "Übersicht über SCHÖNI DIGITAL, System, Schlüssel und Projektstand"


def register(p: argparse.ArgumentParser) -> None:
    p.add_argument("--json", action="store_true", help="Maschinenlesbare Ausgabe als JSON")


def _get_tailscale_ip() -> str:
    exe = shutil.which("tailscale")
    if not exe:
        return "nicht installiert"
    import subprocess
    try:
        res = subprocess.run([exe, "ip", "-4"], capture_output=True, text=True, timeout=2)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip().splitlines()[0]
    except Exception:
        pass
    return "getrennt"


def _container_status() -> str:
    if shutil.which("docker"):
        return f"Docker CLI ({shutil.which('docker')})"
    if shutil.which("podman"):
        return f"Podman ({shutil.which('podman')})"
    return "keine (weder Docker noch Podman)"


def _orca_status() -> str:
    exe = shutil.which("orca")
    if exe:
        return f"Orca CLI ({exe})"
    if platform.system() == "Darwin" and Path("/Applications/Orca.app").exists():
        return "Orca.app (/Applications/Orca.app)"
    return "nicht installiert"


def _t3_status() -> str:
    exe = shutil.which("t3")
    if exe:
        return f"T3 Code CLI ({exe})"
    if platform.system() == "Darwin":
        for p in ("/Applications/T3 Code.app", "/Applications/T3 Code (Beta).app"):
            if Path(p).exists():
                return f"T3 Code ({p})"
    return "nicht installiert"


def run(args: argparse.Namespace) -> int:
    if getattr(args, "json", False):
        import json
        data = {
            "version": __version__,
            "organisation": "SCHOENI DIGITAL",
            "forgejo": "https://git.schoeni-digital.com",
            "hostname": socket.gethostname(),
            "os": platform.system(),
            "container": _container_status(),
            "orca": _orca_status(),
            "t3": _t3_status(),
            "tailscale_ip": _get_tailscale_ip(),
        }
        print(json.dumps(data, indent=2))
        return 0

    ui.banner()

    members = team_data.list_members()
    owner = next((m for m in members if m.get("role") == "owner"), None)
    owner_str = f"{owner['name']} ({owner['id']})" if owner else "–"

    age_pub = keys.read_age_public_key()
    age_str = f"{age_pub[:14]}...{age_pub[-6:]}" if age_pub else "kein Schlüssel vorhanden"

    ssh_pub = keys.read_ssh_public_key()
    ssh_str = f"{ssh_pub.split()[0]} {ssh_pub.split()[1][:12]}..." if ssh_pub and len(ssh_pub.split()) > 1 else ("vorhanden" if ssh_pub else "–")

    cols = [
        ("Bereich", {"style": "cyan bold", "width": 24}),
        ("Status / Information", {"style": "white"}),
    ]

    rows = [
        ["Organisation", "SCHOENI DIGITAL"],
        ["CLI-Version", f"sdc v{__version__}"],
        ["Git-Hosting", "https://git.schoeni-digital.com (Forgejo v15.0 LTS)"],
        ["Verantwortlich", owner_str],
        ["Gerätename", f"{socket.gethostname()} ({platform.system().lower()})"],
        ["Tailscale-IP", _get_tailscale_ip()],
        ["Secrets-Verschlüsselung", f"SOPS + age ({age_str})"],
        ["SSH-Schlüssel", ssh_str],
        ["Container-Laufzeit", _container_status()],
        ["Orca Agenten-Laufzeit", _orca_status()],
        ["T3 Code GUI", _t3_status()],
        ["Vorlage & Schema", f"{template_root().name} (Schema: {schema_path().name})"],
        ["Registrierte Geräte", f"{len(team_data.list_all_devices())} Gerät(e) in config/team.yml"],
    ]

    ui.table("SCHOENI DIGITAL — System- & Umgebungs-Info", cols, rows)
    return 0
