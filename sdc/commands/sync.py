"""sdc sync: Synchronisiert SCHOENI DIGITAL Applikationen unter ~/Projekte/SCHOENI_DIGITAL."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .. import ui
from ..paths import workspace_root

HELP = "Applikationen synchronisieren (alle oder einzelne klonen & pullen)"

# Offizieller Katalog bekannter SCHOENI DIGITAL Repositories
KNOWN_APPS: list[dict[str, str]] = [
    {
        "name": "core",
        "category": "core",
        "rel_path": "core",
        "primary_remote": "git@git.sd:schoeni-digital/core.git",
        "fallback_remote": "ssh://git@git.schoeni-digital.com:2222/schoeni-digital/core.git",
    },
    {
        "name": "cli",
        "category": "internal",
        "rel_path": "internal/cli",
        "primary_remote": "git@git.sd:schoeni-digital/cli.git",
        "fallback_remote": "https://github.com/christophschoeni/sdc.git",
    },
    {
        "name": "billflow-site",
        "category": "internal",
        "rel_path": "internal/billflow-site",
        "primary_remote": "git@git.sd:schoeni-digital/billflow-site.git",
        "fallback_remote": "ssh://git@git.schoeni-digital.com:2222/schoeni-digital/billflow-site.git",
    },
    {
        "name": "bootstrap",
        "category": "internal",
        "rel_path": "internal/bootstrap",
        "primary_remote": "git@git.sd:schoeni-digital/bootstrap.git",
        "fallback_remote": "ssh://git@git.schoeni-digital.com:2222/schoeni-digital/bootstrap.git",
    },
    {
        "name": "ops",
        "category": "internal",
        "rel_path": "internal/ops",
        "primary_remote": "git@git.sd:schoeni-digital/ops.git",
        "fallback_remote": "ssh://git@git.schoeni-digital.com:2222/schoeni-digital/ops.git",
    },
    {
        "name": "vacation_app",
        "category": "internal",
        "rel_path": "internal/vacation_app",
        "primary_remote": "git@git.sd:schoeni-digital/vacation_app.git",
        "fallback_remote": "ssh://git@git.schoeni-digital.com:2222/schoeni-digital/vacation_app.git",
    },
]


@dataclass
class AppInfo:
    name: str
    category: str
    rel_path: str
    target_path: Path
    primary_remote: str
    fallback_remote: str | None = None

    @property
    def is_cloned(self) -> bool:
        return (self.target_path / ".git").exists()

    def get_current_branch(self) -> str:
        if not self.is_cloned:
            return "-"
        try:
            res = subprocess.run(
                ["git", "-C", str(self.target_path), "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                timeout=4,
            )
            return res.stdout.strip() if res.returncode == 0 else "unknown"
        except Exception:
            return "unknown"

    def get_dirty_status(self) -> tuple[bool, str]:
        """Prüft, ob uncommittete Änderungen vorliegen."""
        if not self.is_cloned:
            return False, "[bold red]\\[fehlt][/bold red] [dim]Nicht vorhanden[/dim]"
        try:
            res = subprocess.run(
                ["git", "-C", str(self.target_path), "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res.returncode == 0:
                lines = [line for line in res.stdout.splitlines() if line.strip()]
                if not lines:
                    return False, "[bold green]\\[ok][/bold green] Sauber"
                return True, f"[bold yellow]\\[warn][/bold yellow] {len(lines)} geändert"
            return True, "[bold yellow]\\[warn][/bold yellow] Status unklar"
        except Exception:
            return True, "[bold yellow]\\[warn][/bold yellow] Fehler"

    def get_sync_status(self) -> str:
        """Prüft den Status gegenüber dem Remote (ahead / behind / up-to-date)."""
        if not self.is_cloned:
            return "[bold red]\\[fehlt][/bold red] [dim]Nicht geklont[/dim]"
        try:
            res = subprocess.run(
                ["git", "-C", str(self.target_path), "status", "-uno"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            out = res.stdout.lower()
            if "up to date" in out or "auf demselben stand" in out:
                return "[bold green]\\[ok][/bold green] Aktuell"
            elif "behind" in out or "hinter" in out:
                return "[bold yellow]\\[warn][/bold yellow] Update verfügbar"
            elif "ahead" in out or "voraus" in out:
                return "[bold cyan]\\[info][/bold cyan] Lokale Commits"
            elif "diverged" in out or "abgeweicht" in out:
                return "[bold yellow]\\[warn][/bold yellow] Divergiert"
            return "[bold green]\\[ok][/bold green] Bereit"
        except Exception:
            return "[dim]Nicht geprüft[/dim]"


def discover_apps() -> list[AppInfo]:
    """Sammelt alle bekannten und lokal im Workspace entdeckten Apps."""
    ws = workspace_root()
    apps_dict: dict[str, AppInfo] = {}

    # 1. Standard-Katalog bekannter Repositories
    for k in KNOWN_APPS:
        target = ws / k["rel_path"]
        apps_dict[k["name"]] = AppInfo(
            name=k["name"],
            category=k["category"],
            rel_path=k["rel_path"],
            target_path=target,
            primary_remote=k["primary_remote"],
            fallback_remote=k.get("fallback_remote"),
        )

    # 2. Lokale Repositories dynamisch entdecken (internal/* und customers/*)
    for category in ("internal", "customers"):
        cat_dir = ws / category
        if cat_dir.is_dir():
            for child in sorted(cat_dir.iterdir()):
                if child.is_dir() and (child / ".git").exists():
                    name = child.name
                    if name not in apps_dict:
                        # Remote aus Git-Konfiguration ermitteln
                        remote_url = ""
                        try:
                            res = subprocess.run(
                                ["git", "-C", str(child), "config", "--get", "remote.origin.url"],
                                capture_output=True,
                                text=True,
                                timeout=3,
                            )
                            if res.returncode == 0:
                                remote_url = res.stdout.strip()
                        except Exception:
                            pass

                        apps_dict[name] = AppInfo(
                            name=name,
                            category=category,
                            rel_path=f"{category}/{name}",
                            target_path=child,
                            primary_remote=remote_url or f"git@git.sd:schoeni-digital/{name}.git",
                        )

    return list(apps_dict.values())


def sync_single_app(app: AppInfo, pull_only: bool = False, clone_only: bool = False) -> bool:
    """Synchronisiert eine einzelne Applikation (Klonen oder Pullen)."""
    ws = workspace_root()
    ws_display = f"~/Projekte/{ws.name}"

    if not app.is_cloned:
        if pull_only:
            ui.warn(f"{app.name}: Nicht vorhanden (Pull übersprungen).")
            return False

        # App klonen
        app.target_path.parent.mkdir(parents=True, exist_ok=True)
        ui.step(f"Klone {app.name} nach {ws_display}/{app.rel_path} ...")

        remotes_to_try = [app.primary_remote]
        if app.fallback_remote and app.fallback_remote not in remotes_to_try:
            remotes_to_try.append(app.fallback_remote)

        cloned = False
        for remote in remotes_to_try:
            if not remote:
                continue
            with ui.spinner(f"git clone {remote} ..."):
                res = subprocess.run(
                    ["git", "clone", remote, str(app.target_path)],
                    capture_output=True,
                    text=True,
                )
            if res.returncode == 0:
                ui.success(f"{app.name}: Erfolgreich geklont.")
                cloned = True
                break

        if not cloned:
            ui.error(f"{app.name}: Klonen fehlgeschlagen.")
            return False
        return True

    # Bereits geklont: Aktualisieren
    if clone_only:
        ui.info(f"{app.name}: Bereits vorhanden.")
        return True

    is_dirty, dirty_msg = app.get_dirty_status()
    if is_dirty:
        ui.warn(f"{app.name}: {dirty_msg} \u2014 Pull übersprungen, um Konflikte zu vermeiden.")
        return False

    with ui.spinner(f"{app.name}: Aktualisiere (git fetch & pull) ..."):
        # Fetch durchführen
        subprocess.run(
            ["git", "-C", str(app.target_path), "fetch", "--all", "--prune"],
            capture_output=True,
            timeout=15,
        )
        # Fast-Forward Pull versuchen
        res = subprocess.run(
            ["git", "-C", str(app.target_path), "pull", "--ff-only"],
            capture_output=True,
            text=True,
            timeout=15,
        )

    if res.returncode == 0:
        out = res.stdout.strip()
        if "Already up to date" in out or "Bereits aktuell" in out:
            ui.success(f"{app.name}: Bereits auf dem neuesten Stand.")
        else:
            ui.success(f"{app.name}: Erfolgreich aktualisiert (Fast-Forward).")
        return True
    else:
        err = res.stderr.strip() or res.stdout.strip()
        ui.warn(f"{app.name}: Automatischer Fast-Forward-Pull nicht möglich: {err}")
        return False


def show_status(apps: Sequence[AppInfo]) -> None:
    """Zeigt eine saubere tabellarische Übersicht aller Apps und deren Synchronisationszustand."""
    ws = workspace_root()
    ws_display = f"~/Projekte/{ws.name}"

    rows = []
    for app in apps:
        branch = app.get_current_branch()
        _, dirty_msg = app.get_dirty_status()
        sync_msg = app.get_sync_status()
        rows.append([
            app.name,
            app.category,
            app.rel_path,
            branch,
            dirty_msg,
            sync_msg,
        ])

    ui.table(
        f"SCHOENI DIGITAL Applikationen ({ws_display})",
        [
            ("App", {"style": "bold cyan"}),
            ("Kategorie", {}),
            ("Relativer Pfad", {"style": "dim"}),
            ("Branch", {}),
            ("Lokaler Status", {}),
            ("Sync-Status", {}),
        ],
        rows,
    )


def register(p: argparse.ArgumentParser) -> None:
    p.add_argument("app", nargs="?", default=None, help="Name einer bestimmten Applikation (z.B. core, cli, billflow-site)")
    p.add_argument("--all", "-a", action="store_true", help="Alle Apps synchronisieren")
    p.add_argument("--status", "-s", action="store_true", help="Status aller Apps anzeigen")
    p.add_argument("--clone-only", action="store_true", help="Nur fehlende Apps klonen, bestehende nicht aktualisieren")
    p.add_argument("--pull-only", action="store_true", help="Nur bestehende Apps aktualisieren, keine fehlenden klonen")


def run(args: argparse.Namespace) -> int:
    ws = workspace_root()
    ws_display = f"~/Projekte/{ws.name}"
    apps = discover_apps()

    # 1. Reine Status-Abfrage
    if args.status:
        show_status(apps)
        return 0

    # 2. Spezifische App angegeben
    if args.app:
        app_name = args.app.strip()
        matched = [a for a in apps if a.name.lower() == app_name.lower()]
        if not matched:
            ui.error(f"App '{app_name}' nicht im Katalog gefunden.")
            ui.info(f"Verfügbare Apps: {', '.join(a.name for a in apps)}")
            return 1
        app = matched[0]
        ui.step(f"Synchronisiere App: {app.name}")
        ok = sync_single_app(app, pull_only=args.pull_only, clone_only=args.clone_only)
        return 0 if ok else 1

    # 3. Flag --all übergeben
    if args.all:
        ui.step(f"Synchronisiere alle {len(apps)} Apps unter {ws_display} ...")
        success_count = 0
        for app in apps:
            if sync_single_app(app, pull_only=args.pull_only, clone_only=args.clone_only):
                success_count += 1
        ui.console.print()
        ui.success(f"{success_count}/{len(apps)} Apps erfolgreich synchronisiert.")
        return 0

    # 4. Interaktives Menü (falls keine Flags)
    if not sys.stdin.isatty():
        # Im Non-TTY Modus: Alle synchronisieren
        ui.step(f"Synchronisiere alle Apps unter {ws_display} ...")
        for app in apps:
            sync_single_app(app, pull_only=args.pull_only, clone_only=args.clone_only)
        return 0

    # Interaktiver Dialog
    ui.panel(
        "Applikationen synchronisieren",
        [
            f"Zielverzeichnis: [cyan]{ws_display}[/cyan]",
            "Hier können alle Firmen-Repositories auf den neuesten Stand gebracht oder fehlende geklont werden.",
        ],
    )

    choices = [
        ui.choice_item("all", "Alle Apps synchronisieren (Klonen & Aktualisieren)", "all", pad=12),
        ui.choice_item("status", "Status aller Apps anzeigen", "status", pad=12),
    ]

    for app in apps:
        status_label = "vorhanden" if app.is_cloned else "fehlt"
        choices.append(
            ui.choice_item(app.name, f"[{app.category}] {app.rel_path} ({status_label})", app.name, pad=12)
        )

    choices.append(ui.choice_item("cancel", "Abbrechen", "cancel", pad=12))

    action = ui.select("Was möchtest du synchronisieren?", choices=choices)

    if not action or action == "cancel":
        ui.info("Vorgang abgebrochen.")
        return 0

    if action == "status":
        show_status(apps)
        return 0

    if action == "all":
        ui.step(f"Synchronisiere alle {len(apps)} Apps unter {ws_display} ...")
        success_count = 0
        for app in apps:
            if sync_single_app(app):
                success_count += 1
        ui.console.print()
        ui.success(f"{success_count}/{len(apps)} Apps erfolgreich synchronisiert.")
        return 0

    # Einzelne App gewählt
    matched = [a for a in apps if a.name == action]
    if matched:
        sync_single_app(matched[0])
        return 0

    return 0
