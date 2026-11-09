"""sdc orca: Steuerung des Orca Agenten-Runtimes und Remote-Kopplung."""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import socket
import subprocess
import time
from pathlib import Path
from typing import Any

from .. import keys, team_data, ui
from ..pairing import (
    BEACON_PORT,
    ORCA_PORT,
    BeaconServer,
    notify_paired,
    probe_beacon,
    scan_beacons,
)
from . import secrets

HELP = "Orca Agenten-Laufzeit verwalten und Arbeitsrechner miteinander koppeln"


def register(p: argparse.ArgumentParser) -> None:
    sub = p.add_subparsers(dest="action", required=False)

    # status
    sub.add_parser("status", help="Status der lokalen Orca-Instanz und verbundene Umgebungen prüfen")

    # init (auf dem neuen Rechner, z.B. Omarchy)
    p_init = sub.add_parser("init", help="Dieses Notebook für Orca initialisieren & zur automatischen Kopplung freigeben")
    p_init.add_argument("--name", help="Anzeigename für dieses Notebook (Standard: Hostname)")
    p_init.add_argument("--beacon-port", type=int, default=BEACON_PORT, help=f"Port für den Pairing-Beacon (Standard: {BEACON_PORT})")
    p_init.add_argument("--orca-port", type=int, default=ORCA_PORT, help=f"Port für Orca (Standard: {ORCA_PORT})")

    # serve (auf dem Ziel-Rechner)
    p_serve = sub.add_parser("serve", help="Orca-Server starten, damit dieser PC im Haupt-Orca gesteuert werden kann")
    p_serve.add_argument("--bind", default="0.0.0.0", help="IP-Adresse zum Binden (z. B. 0.0.0.0 oder Tailscale-IP)")
    p_serve.add_argument("--port", type=int, default=ORCA_PORT, help=f"Port (Standard: {ORCA_PORT})")
    p_serve.add_argument("--mobile", action="store_true", help="Mobile Pairing-Link erzeugen")

    # connect (auf dem Haupt-Rechner, z.B. MacBook)
    p_conn = sub.add_parser("connect", help="Diesen Rechner mit einem Remote-PC via automatischer Erkennung oder Code koppeln")
    p_conn.add_argument("code", nargs="?", help="IP-Adresse, Hostname oder orca://pair?... Code")
    p_conn.add_argument("--name", help="Name für die gespeicherte Orca-Umgebung")
    p_conn.add_argument("--scan", action="store_true", help="Automatischen Scan im Tailnet & Netzwerk erzwingen")


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


def _get_local_ip() -> str:
    """Ermittelt eine erreichbare lokale IP-Adresse."""
    ts_ip = _get_tailscale_ip()
    if ts_ip:
        return ts_ip
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


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

    # Gespeicherte Remote-Environments anzeigen
    try:
        res_env = subprocess.run([orca_bin, "environment", "list", "--json"], capture_output=True, text=True, timeout=5)
        if res_env.returncode == 0:
            envs = json.loads(res_env.stdout).get("result", {}).get("environments", [])
            if envs:
                cols = [
                    ("Name", {"style": "cyan bold", "width": 20}),
                    ("Typ / Status", {"style": "green"}),
                    ("Endpunkt / Info", {"style": "dim"}),
                ]
                rows = []
                for e in envs:
                    name = e.get("name") or e.get("id", "–")
                    st = "[green]verbunden[/green]" if e.get("connected", True) else "[yellow]bereit[/yellow]"
                    ep = e.get("endpoint") or e.get("id") or "–"
                    rows.append([name, st, ep])
                ui.table("Orca — Gespeicherte Remote-Umgebungen", cols, rows)
    except Exception:
        pass

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


def _get_pairing_data(orca_bin: str, address: str) -> dict[str, Any] | None:
    """Holt die Pairing-Daten aus einer laufenden Orca-Instanz."""
    try:
        res = subprocess.run(
            [orca_bin, "pair", "--address", address, "--json"],
            capture_output=True,
            text=True,
            timeout=6,
        )
        if res.returncode == 0 and res.stdout.strip():
            data = json.loads(res.stdout)
            result = data.get("result", {})
            if result.get("pairingUrl"):
                return result
    except Exception:
        pass
    return None


def do_init(args: argparse.Namespace) -> int:
    """Initialisiert das Gerät für Orca und startet den automatischen Pairing-Beacon."""
    orca_bin = shutil.which("orca")
    if not orca_bin:
        ui.error("Orca CLI ('orca') nicht gefunden.")
        ui.info("Tipp: Führe zuerst 'sdc setup' aus, um Orca automatisch zu installieren.")
        return 1

    hostname = socket.gethostname().split(".")[0]
    dev_name = getattr(args, "name", None) or hostname
    ts_ip = _get_tailscale_ip()
    local_ip = _get_local_ip()
    bind_address = ts_ip or local_ip
    beacon_port = getattr(args, "beacon_port", BEACON_PORT)
    orca_port = getattr(args, "orca_port", ORCA_PORT)

    ui.banner()
    ui.step(f"Orca Initialisierung für Gerät: {dev_name}")

    # 1. Schlüssel ermitteln / generieren
    with ui.spinner("Prüfe Geräteschlüssel (age & SSH) …"):
        age_pub, _ = keys.ensure_age_key()
        ssh_pub, _ = keys.ensure_ssh_key()

    ui.success(f"age-Schlüssel bereit: [dim]{age_pub[:14]}…{age_pub[-6:]}[/dim]")
    ui.success(f"SSH-Schlüssel bereit: [dim]{ssh_pub.split()[-1] if ' ' in ssh_pub else 'vorhanden'}[/dim]")

    # 2. Orca Pairing-Code beschaffen
    with ui.spinner("Ermittle Orca Pairing-Code …"):
        pairing_data = _get_pairing_data(orca_bin, bind_address)

    # Falls Orca noch nicht lief: im Hintergrund starten
    orca_proc = None
    if not pairing_data:
        ui.info("Orca Runtime ist noch nicht aktiv. Starte Server im Hintergrund …")
        cmd = [orca_bin, "serve", "--port", str(orca_port), "--bind", "0.0.0.0"]
        if ts_ip:
            cmd.extend(["--pairing-address", ts_ip])

        try:
            orca_proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(2.0)
            pairing_data = _get_pairing_data(orca_bin, bind_address)
        except Exception as exc:
            ui.error(f"Konnte Orca-Server nicht starten: {exc}")
            return 1

    if not pairing_data or not pairing_data.get("pairingUrl"):
        ui.error("Konnte keinen Pairing-Code von Orca erhalten.")
        ui.info("Prüfe, ob Orca auf diesem Gerät geöffnet ist oder starte mit 'sdc orca serve'.")
        return 1

    pairing_url = pairing_data["pairingUrl"]
    web_url = pairing_data.get("webClientUrl", "")

    # 3. Beacon-Server mit Geräteinformationen starten
    device_payload = {
        "ok": True,
        "device_name": dev_name,
        "hostname": hostname,
        "platform": platform.system().lower(),
        "tailscale_ip": ts_ip,
        "local_ip": local_ip,
        "orca_port": orca_port,
        "pairing_code": pairing_url,
        "web_client_url": web_url,
        "age_pubkey": age_pub,
        "ssh_pubkey": ssh_pub,
    }

    try:
        beacon = BeaconServer(device_payload, port=beacon_port, host="0.0.0.0")
        beacon.start()
    except Exception as exc:
        ui.error(f"Konnte Pairing-Beacon auf Port {beacon_port} nicht starten: {exc}")
        return 1

    # 4. Statusanzeige und Anleitung für das Hauptgerät (MacBook)
    ui.console.print()
    ui.panel(
        "Bereit zur automatischen Kopplung",
        [
            f"Gerätename: [bold cyan]{dev_name}[/bold cyan] ({platform.system().lower()})",
            f"Tailscale-IP: [cyan]{ts_ip or 'nicht aktiv'}[/cyan] · Lokale IP: [dim]{local_ip}[/dim]",
            f"Pairing-Beacon aktiv auf: [bold green]Port {beacon_port}[/bold green]",
            "",
            "[bold white]Auf deinem MacBook (oder Arbeitsrechner):[/bold white]",
            "  1. Öffne das Terminal und starte einfach:",
            "     [bold #00d2ff]sdc orca connect[/bold #00d2ff]   [dim](oder wähle 'orca' im sdc Menü)[/dim]",
            "",
            "  2. Das MacBook erkennt dieses Notebook [bold green]automatisch[/bold green] im Tailnet.",
            "     Du musst [bold white]weder Links noch Schlüssel abtippen[/bold white]!",
        ],
        style="green",
    )

    ui.info("Warte auf Kopplungs-Anfrage vom MacBook … (Drücke [bold]Strg+C[/bold] zum Beenden)\n")

    try:
        while True:
            if beacon.wait_for_paired(timeout=1.0):
                ui.console.print()
                ui.success(f"Kopplungs-Anfrage erhalten von: [bold cyan]{beacon.paired_by}[/bold cyan]!")
                ui.success("Orca-Pairing und Geräteschlüssel wurden erfolgreich übermittelt.")
                ui.panel(
                    "Kopplung abgeschlossen",
                    [
                        f"Dieses Gerät ('{dev_name}') ist nun mit deinem Hauptrechner verbunden.",
                        "Du kannst dieses Fenster mit [bold]Strg+C[/bold] schliessen.",
                    ],
                    style="green",
                )
                break
            time.sleep(0.5)

        # Warten, bis der Benutzer das Fenster schliesst
        while True:
            time.sleep(1.0)

    except KeyboardInterrupt:
        ui.info("\nPairing-Beacon beendet.")
    finally:
        beacon.stop()
        if orca_proc:
            try:
                orca_proc.terminate()
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
    port = getattr(args, "port", ORCA_PORT)

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

    target = getattr(args, "code", None)
    explicit_name = getattr(args, "name", None)
    force_scan = getattr(args, "scan", False)

    pairing_code: str | None = None
    env_name: str | None = explicit_name
    discovered_payload: dict[str, Any] | None = None
    discovered_ip: str | None = None

    # Fall 1: Direkt als orca://pair?... übergeben
    if target and target.startswith("orca://pair"):
        pairing_code = target

    # Fall 2: Direkt als IP oder Hostname übergeben
    elif target and not target.startswith("orca://"):
        target_ip = target.strip()
        with ui.spinner(f"Prüfe Gerät unter {target_ip} …"):
            payload = probe_beacon(target_ip)
        if payload:
            discovered_payload = payload
            discovered_ip = target_ip
            pairing_code = payload.get("pairing_code")
            env_name = env_name or payload.get("device_name")
            ui.success(f"Gerät '{payload.get('device_name')}' unter {target_ip} gefunden!")
        else:
            ui.warn(f"Kein aktiver Pairing-Beacon unter {target_ip} gefunden.")

    # Fall 3: Automatischer Netzwerk-/Tailnet-Scan
    if not pairing_code:
        with ui.spinner("Suche nach SCHÖNI DIGITAL Geräten im Tailnet/Netzwerk …"):
            beacons = scan_beacons(timeout=1.2)

        if beacons:
            ui.success(f"{len(beacons)} gerätebereite(s) Gerät(e) im Tailnet gefunden:")
            choices = []
            for b in beacons:
                d_name = b.get("device_name", "unbekannt")
                ip = b.get("discovered_ip", b.get("tailscale_ip", "–"))
                plat = b.get("platform", "linux")
                choices.append(
                    ui.choice_item(
                        d_name,
                        f"[{plat}] IP: {ip} (Orca Port {b.get('orca_port', 6768)})",
                        b,
                        pad=14,
                    )
                )

            choices.append(ui.choice_item("manual", "Anderen Pairing-Code manuell eingeben", "manual", pad=14))
            choices.append(ui.choice_item("cancel", "Abbrechen", "cancel", pad=14))

            selected = ui.select("Welches Gerät möchtest du koppeln?", choices=choices)
            if not selected or selected == "cancel":
                ui.info("Vorgang abgebrochen.")
                return 0

            if selected != "manual":
                discovered_payload = selected
                discovered_ip = selected.get("discovered_ip") or selected.get("tailscale_ip")
                pairing_code = selected.get("pairing_code")
                env_name = env_name or selected.get("device_name")

        else:
            ui.info("Kein automatischer Pairing-Beacon im Tailnet/Netzwerk gefunden.")
            ui.console.print(
                "[dim]Tipp: Starte auf dem Ziel-Notebook (z. B. Omarchy) zuerst:[/dim]\n"
                "  [bold #00d2ff]sdc orca init[/bold #00d2ff]\n"
                "[dim]Dadurch wird das Gerät im Netzwerk sichtbar und kann ohne Abtippen gekoppelt werden.[/dim]\n"
            )

    # Fall 4: Manuelle Eingabe als Fallback
    if not pairing_code:
        code_input = ui.text("Pairing-Code (orca://pair?...):")
        if not code_input:
            ui.error("Kein Pairing-Code angegeben.")
            return 1
        pairing_code = code_input.strip()

    # Umgebungsname festlegen
    if not env_name:
        default_env = (discovered_payload.get("device_name") if discovered_payload else "remote-notebook")
        env_name = ui.text("Name für dieses Orca Environment:", default=default_env) or default_env

    # Orca Environment hinzufügen
    with ui.spinner(f"Kopple Orca Environment '{env_name}' …"):
        res = subprocess.run(
            [orca_bin, "environment", "add", "--name", env_name, "--pairing-code", pairing_code, "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )

    if res.returncode != 0:
        err = res.stderr.strip() or res.stdout.strip()
        ui.error(f"Kopplung im Orca fehlgeschlagen: {err}")
        return 1

    ui.success(f"Orca Environment '[bold cyan]{env_name}[/bold cyan]' erfolgreich hinzugefügt!")

    # Bestätigung an den Beacon senden
    if discovered_ip:
        client_hostname = socket.gethostname().split(".")[0]
        notify_paired(discovered_ip, client_name=f"{client_hostname} (MacBook)")

    # Optionale automatische Aufnahme in SCHOENI DIGITAL (team.yml & Secrets)
    if discovered_payload and discovered_payload.get("age_pubkey"):
        ui.console.print()
        add_to_team = ui.confirm(
            f"Möchtest du '{env_name}' auch als Arbeitsgerät in SCHÖNI DIGITAL registrieren (team.yml & Secrets)?",
            default=True,
        )
        if add_to_team:
            _register_device_in_team(env_name, discovered_payload)

    return 0


def _register_device_in_team(device_name: str, payload: dict[str, Any]) -> None:
    """Registriert das neu gekoppelte Gerät direkt in config/team.yml und schaltet Secrets frei."""
    members = team_data.list_members()
    if not members:
        ui.warn("Noch keine Mitarbeiter in team.yml erfasst. Registrierung übersprungen.")
        return

    # Standard: Owner (Christoph Schöni)
    owner = next((m for m in members if m.get("role") == "owner"), members[0])
    member_id = owner["id"]

    age_pub = payload.get("age_pubkey")
    ssh_pub = payload.get("ssh_pubkey")
    dev_id = f"{member_id}_{device_name.lower().replace('-', '_')}"

    try:
        team_data.add_device(
            member_id=member_id,
            device_id=dev_id,
            name=f"{device_name} ({payload.get('platform', 'linux')})",
            age_key=age_pub,
            ssh_key=ssh_pub,
        )
        ui.success(f"Gerät '{dev_id}' in config/team.yml für '{owner['name']}' eingetragen.")

        # Secrets-Rekey anbieten
        rekey_confirm = ui.confirm("Secrets sofort für dieses neue Gerät neu verschlüsseln (sdc secrets rekey)?", default=True)
        if rekey_confirm:
            from ..paths import workspace_root
            ws = workspace_root()
            # In allen Apps mit schoeni.yaml rekeyen
            for app_dir in ws.glob("internal/*"):
                if (app_dir / "schoeni.yaml").exists() and (app_dir / "secrets" / "recipients.yml").exists():
                    secrets.do_rekey(app_dir)
            ui.success("Secrets wurden erfolgreich für das neue Notebook freigeschaltet!")

    except Exception as exc:
        ui.warn(f"Geräteregistrierung nicht abgeschlossen: {exc}")


def run(args: argparse.Namespace) -> int:
    action = getattr(args, "action", None)
    if action == "init":
        return do_init(args)
    if action == "serve":
        return do_serve(args)
    if action == "connect":
        return do_connect(args)
    if action == "status" or not action:
        return do_status()
    ui.error(f"Unbekannte Aktion: {action}")
    return 1
