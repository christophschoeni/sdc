"""sdc orca: Steuerung des Orca Agenten-Runtimes und Remote-Kopplung."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

from .. import ui

HELP = "Orca Agenten-Laufzeit verwalten und Arbeitsrechner miteinander koppeln"


def register(p: argparse.ArgumentParser) -> None:
    sub = p.add_subparsers(dest="action", required=False)

    # status
    sub.add_parser("status", help="Status der lokalen Orca-Instanz prüfen")

    # serve (auf dem Ziel-Rechner)
    p_serve = sub.add_parser("serve", help="Orca-Server starten, damit dieser PC im Haupt-Orca gesteuert werden kann")
    p_serve.add_argument("--bind", default="0.0.0.0", help="IP-Adresse zum Binden (z. B. 0.0.0.0 oder Tailscale-IP)")
    p_serve.add_argument("--port", type=int, default=6768, help="Port (Standard: 6768)")
    p_serve.add_argument("--mobile", action="store_true", help="Mobile Pairing-Link erzeugen")

    # connect (auf dem Haupt-Rechner)
    p_conn = sub.add_parser("connect", help="Diesen Rechner mit einem Remote-PC via Orca Pairing-Code koppeln")
    p_conn.add_argument("code", nargs="?", help="Pairing-Code (orca://pair?...), den der Ziel-PC ausgegeben hat")


def _get_tailscale_ip() -> str | None:
    exe = shutil.which("tailscale")
    if not exe:
        return None
    try:
        res = subprocess.run([exe, "ip", "-4"], capture_output=True, text=True, timeout=3)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip().splitlines()[0]
    except Exception:
        pass
    return None


def do_status() -> int:
    orca_bin = shutil.which("orca")
    if not orca_bin:
        ui.warn("Orca CLI ist nicht im PATH. Ist Orca installiert?")
        return 1

    with ui.spinner("Lese Orca Status …"):
        try:
            res = subprocess.run([orca_bin, "status", "--json"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                data = json.loads(res.stdout)
                runtime_id = data.get("_meta", {}).get("runtimeId", "unbekannt")
                caller = data.get("caller", {}).get("orcaSessionId", "–")
                ui.success(f"Orca Runtime aktiv (ID: [cyan]{runtime_id}[/cyan])")
                ui.info(f"Aktuelle Session: [dim]{caller}[/dim]")
            else:
                ui.warn("Orca ist installiert, aber die Runtime antwortet derzeit nicht (App geöffnet?).")
        except Exception as exc:
            ui.error(f"Fehler beim Abrufen des Orca Status: {exc}")
            return 1

    # Verbundene Hosts anzeigen
    try:
        res_hosts = subprocess.run([orca_bin, "host", "list", "--json"], capture_output=True, text=True, timeout=5)
        if res_hosts.returncode == 0:
            hdata = json.loads(res_hosts.stdout).get("result", {}).get("hosts", [])
            cols = [
                ("Typ", {"style": "cyan bold", "width": 10}),
                ("Name / Host", {"style": "white bold", "width": 26}),
                ("Status / ID", {"style": "dim"}),
            ]
            rows = []
            for h in hdata:
                k = h.get("kind", "ssh")
                name = h.get("machineName") or h.get("name") or h.get("id")
                connected = h.get("connected")
                st = "[green]verbunden[/green]" if connected is True else ("[dim]lokal[/dim]" if k == "local" else "[yellow]bereit[/yellow]")
                rows.append([k, name, st])
            ui.table("Orca — Bekannte Hosts & Runtimes", cols, rows)
    except Exception:
        pass

    return 0


def do_serve(args: argparse.Namespace) -> int:
    orca_bin = shutil.which("orca")
    if not orca_bin:
        ui.error("Orca CLI ('orca') nicht gefunden. Bitte zuerst installieren.")
        return 1

    ts_ip = _get_tailscale_ip()
    bind_ip = getattr(args, "bind", "0.0.0.0")
    port = getattr(args, "port", 6768)

    ui.step("Orca Runtime Server starten")
    if ts_ip:
        ui.info(f"Tailscale-Adresse erkannt: [bold cyan]{ts_ip}[/bold cyan]")
        ui.info(f"Der PC wird unter [cyan]{ts_ip}:{port}[/cyan] im Tailnet erreichbar sein.")
    else:
        ui.info(f"Bindet auf [cyan]{bind_ip}:{port}[/cyan]")

    cmd = [orca_bin, "serve", "--port", str(port), "--bind", bind_ip]
    if ts_ip:
        cmd.extend(["--pairing-address", ts_ip])
    if getattr(args, "mobile", False):
        cmd.append("--mobile-pairing")

    ui.info("Starte Server … Drücke [bold]Strg+C[/bold] zum Beenden.\n")
    try:
        subprocess.run(cmd)
        return 0
    except KeyboardInterrupt:
        ui.info("\nOrca Server beendet.")
        return 0
    except Exception as exc:
        ui.error(f"Fehler: {exc}")
        return 1


def do_connect(args: argparse.Namespace) -> int:
    orca_bin = shutil.which("orca")
    if not orca_bin:
        ui.error("Orca CLI ('orca') nicht gefunden.")
        return 1

    code = getattr(args, "code", None)
    if not code:
        code = ui.text("Pairing-Code des Ziel-PCs (orca://pair?...):")

    if not code:
        ui.error("Kein Pairing-Code angegeben.")
        return 1

    with ui.spinner("Verbinde mit Remote-Orca …"):
        try:
            res = subprocess.run([orca_bin, "--pairing-code", code, "status", "--json"], capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                ui.success("Verbindung erfolgreich hergestellt! Der Remote-PC ist jetzt im Orca erreichbar.")
                return 0
            else:
                ui.error(f"Kopplung fehlgeschlagen: {res.stderr.strip() or res.stdout.strip()}")
                return 1
        except Exception as exc:
            ui.error(f"Kopplungsfehler: {exc}")
            return 1


def run(args: argparse.Namespace) -> int:
    action = getattr(args, "action", None)
    if action == "serve":
        return do_serve(args)
    if action == "connect":
        return do_connect(args)
    if action == "status" or not action:
        return do_status()
    ui.error(f"Unbekannte Aktion: {action}")
    return 1
