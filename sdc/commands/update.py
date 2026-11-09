"""sdc update: Aktualisiert die SCHOENI DIGITAL CLI und Entwickler-Tools."""
from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from .. import __version__, ui
from ..paths import core_root

HELP = "sdc CLI und Entwickler-Tools auf den neuesten Stand aktualisieren"

REPO_SSH = "git+ssh://git@git.sd/schoeni-digital/cli.git"
REPO_SSH_PORT = "git+ssh://git@git.schoeni-digital.com:2222/schoeni-digital/cli.git"
REPO_HTTPS = "git+https://git.schoeni-digital.com/schoeni-digital/cli.git"
REPO_GITHUB = "git+https://github.com/christophschoeni/sdc.git"


def register(p: argparse.ArgumentParser) -> None:
    p.add_argument("--tools", action="store_true", help="Auch Basis-Tools (uv, Homebrew) aktualisieren")
    p.add_argument("--force", action="store_true", help="Erzwingt eine Neuinstallation aus dem Forgejo-Repository")
    p.add_argument("--check", action="store_true", help="Nur auf Updates prüfen, ohne zu installieren")


def _find_git_repo_for_cli() -> Path | None:
    """Sucht nach einem lokalen Git-Repository für die CLI."""
    # 1. template/cli direkt
    pkg_dir = Path(__file__).resolve().parent.parent.parent
    if (pkg_dir / ".git").exists():
        return pkg_dir

    # 2. Workspace-Ebene (z. B. CLI-Tool/.git oder core/.git)
    cur = pkg_dir
    for _ in range(4):
        if (cur / ".git").exists():
            return cur
        cur = cur.parent

    # 3. Standard-Pfad im Firmen-Workspace
    std_path = Path.home() / "Projekte" / "SCHOENI-DIGITAL" / "internal" / "cli"
    if (std_path / ".git").exists():
        return std_path

    return None


def _get_remote_head() -> str | None:
    """Ermittelt den aktuellen Commit-Hash auf dem Forgejo-Server."""
    for remote in ("git@git.sd:schoeni-digital/cli.git", "ssh://git@git.schoeni-digital.com:2222/schoeni-digital/cli.git"):
        try:
            res = subprocess.run(["git", "ls-remote", remote, "HEAD"], capture_output=True, text=True, timeout=6)
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip().split()[0]
        except Exception:
            continue
    return None


def _update_via_git(repo_dir: Path) -> bool:
    ui.info(f"Lokales Repository erkannt: [dim]{repo_dir}[/dim]")
    try:
        res = subprocess.run(["git", "pull", "--ff-only"], cwd=repo_dir, capture_output=True, text=True, timeout=20)
        if res.returncode == 0:
            msg = res.stdout.strip()
            ui.info(f"Git-Status: {msg if msg else 'Bereits aktuell'}")
            return True
        else:
            ui.warn(f"git pull nicht möglich ({res.stderr.strip()}). Versuche direkten Abgleich ...")
            return False
    except Exception as exc:
        ui.warn(f"Git-Fehler: {exc}")
        return False


def _update_cli(force: bool = False) -> bool:
    uv = shutil.which("uv")
    if not uv:
        ui.error("uv ist nicht installiert. Bitte zuerst 'sdc setup' ausführen.")
        return False

    git_repo = _find_git_repo_for_cli()
    if git_repo and not force:
        ui.step("1. Lokales Git-Repository abgleichen")
        _update_via_git(git_repo)

        # Wenn pyproject.toml im Repository liegt:
        cli_sub = git_repo if (git_repo / "pyproject.toml").exists() else (git_repo / "template" / "cli")
        if (cli_sub / "pyproject.toml").exists():
            ui.step("2. sdc via uv tool neu verknüpfen")
            res = subprocess.run([uv, "tool", "install", "--editable", str(cli_sub), "--force"], capture_output=True, text=True)
            if res.returncode == 0:
                ui.success("sdc CLI erfolgreich aus dem lokalen Repository aktualisiert.")
                return True
            else:
                ui.warn(f"Lokale Installation fehlgeschlagen: {res.stderr.strip()}")

    # Remote-Upgrade via uv tool
    ui.step("sdc CLI via uv tool aktualisieren")
    if not force:
        res = subprocess.run([uv, "tool", "upgrade", "sdc"], capture_output=True, text=True)
        if res.returncode == 0:
            out = res.stdout.strip() or res.stderr.strip()
            if "Nothing to upgrade" not in out:
                ui.success(f"sdc aktualisiert: {out}")
                return True
            else:
                ui.info("sdc ist laut uv bereits auf dem neuesten Stand.")

    # Neuinstallation von Forgejo / GitHub erzwingen
    ui.info("Lade neueste Version (Forgejo / GitHub) ...")
    for repo_url in (REPO_SSH, REPO_SSH_PORT, REPO_GITHUB, REPO_HTTPS):
        res = subprocess.run([uv, "tool", "install", "--force", repo_url], capture_output=True, text=True, timeout=45)
        if res.returncode == 0:
            source_label = "GitHub" if "github.com" in repo_url else "Forgejo"
            ui.success(f"sdc erfolgreich von {source_label} aktualisiert.")
            return True

    ui.error("Konnte sdc nicht automatisch aktualisieren.")
    return False


def _update_tools() -> None:
    ui.step("Zusätzliche Entwickler-Tools aktualisieren")

    # 1. uv selbst aktualisieren
    uv = shutil.which("uv")
    if uv:
        try:
            res = subprocess.run([uv, "self", "update"], capture_output=True, text=True, timeout=30)
            if res.returncode == 0:
                out = res.stdout.strip() or res.stderr.strip()
                ui.success(f"uv: {out if out else 'auf neuestem Stand'}")
            else:
                ui.warn(f"uv self update: {res.stderr.strip()}")
        except Exception as exc:
            ui.warn(f"uv self update Fehler: {exc}")

    # 2. Homebrew auf macOS
    if platform.system() == "Darwin" and shutil.which("brew"):
        try:
            ui.info("Aktualisiere Homebrew-Formeln (brew update) ...")
            subprocess.run(["brew", "update"], capture_output=True, text=True, timeout=60)
            ui.success("Homebrew-Formeln sind aktuell.")
        except Exception:
            pass


def run(args: argparse.Namespace) -> int:
    ui.banner()

    ui.table(
        "SCHOENI DIGITAL — Update-Zentrale",
        [("Bereich", {"style": "cyan bold", "width": 24}), ("Status / Information", {"style": "white"})],
        [
            ["Installierte Version", f"sdc v{__version__}"],
            ["Forgejo-Repository", "https://git.schoeni-digital.com/schoeni-digital/cli"],
            ["Modus", "Nur Prüfung (--check)" if getattr(args, "check", False) else "Aktualisierung durchführen"],
        ],
    )

    if getattr(args, "check", False):
        ui.step("Prüfe Forgejo-Server auf neuere Versionen")
        remote_head = _get_remote_head()
        if remote_head:
            ui.info(f"Neuester Commit auf origin/main: [bold cyan]{remote_head[:10]}[/bold cyan]")
            git_repo = _find_git_repo_for_cli()
            if git_repo:
                try:
                    res = subprocess.run(["git", "rev-parse", "HEAD"], cwd=git_repo, capture_output=True, text=True)
                    local_head = res.stdout.strip()
                    if local_head == remote_head:
                        ui.success("Lokales System ist exakt auf dem Stand des Forgejo-Servers.")
                    else:
                        ui.warn(f"Update verfügbar! Lokaler Stand ist {local_head[:10]}, Server hat {remote_head[:10]}. Führe 'sdc update' aus.")
                except Exception:
                    pass
        else:
            ui.info("Server konnte nicht abgefragt werden. Prüfe Netzwerk oder SSH-Verbindung.")
        return 0

    ok = _update_cli(force=getattr(args, "force", False))

    if getattr(args, "tools", False):
        _update_tools()

    if ok:
        ui.console.print()
        ui.success("Update erfolgreich abgeschlossen. 'sdc' ist auf dem neuesten Stand.")
        return 0
    return 1
