"""sdc device: Notebooks und Entwicklungsgeräte in SCHOENI DIGITAL verwalten."""
from __future__ import annotations

import argparse
from pathlib import Path
import yaml

from .. import keys, team_data, ui
from . import secrets

HELP = "Notebooks/Geräte hinzufügen, Schlüssel generieren und für Secrets berechtigen"


def register(p: argparse.ArgumentParser) -> None:
    sub = p.add_subparsers(dest="action", required=False)

    p_add = sub.add_parser("add", help="Neues Notebook / Gerät hinzufügen und für Secrets einrichten")
    p_add.add_argument("--member", help="Kürzel des Mitarbeiters (z. B. cschoeni)")
    p_add.add_argument("--id", help="Eindeutige Geräte-ID (z. B. cs_mac, an_notebook)")
    p_add.add_argument("--name", help="Anzeigename des Geräts (Standard: automatischer Rechnername)")
    p_add.add_argument("--age", help="Öffentlicher age-Schlüssel (Standard: lokaler Schlüssel)")
    p_add.add_argument("--ssh", help="Öffentlicher SSH-Schlüssel (Standard: lokaler Schlüssel)")
    p_add.add_argument("--app", help="Pfad zu einer Schoeni-App zur direkten Secrets-Freischaltung")
    p_add.add_argument("--no-rekey", action="store_true", help="Kein automatisches sdc secrets rekey ausführen")

    sub.add_parser("list", help="Alle registrierten Geräte auflisten")


def _find_current_app(explicit_path: str | None = None) -> Path | None:
    if explicit_path:
        p = Path(explicit_path).resolve()
        if (p / "schoeni.yaml").exists() and (p / "secrets" / "recipients.yml").exists():
            return p
        return None
    cwd = Path.cwd().resolve()
    if (cwd / "schoeni.yaml").exists() and (cwd / "secrets" / "recipients.yml").exists():
        return cwd
    return None


def _update_app_recipients(app_path: Path, device_id: str, age_pub: str, role: str = "developer", rekey: bool = True) -> bool:
    rec_file = app_path / "secrets" / "recipients.yml"
    if not rec_file.exists():
        return False

    try:
        content = yaml.safe_load(rec_file.read_text(encoding="utf-8")) or {}
        recs = content.get("recipients", [])

        # Prüfen, ob schon vorhanden
        for r in recs:
            if r.get("age") == age_pub:
                ui.info(f"Schlüssel ist in {rec_file.name} bereits als '{r.get('name')}' hinterlegt.")
                return True

        recs.append({
            "name": device_id,
            "role": role,
            "age": age_pub,
        })
        content["recipients"] = recs
        rec_file.write_text(yaml.safe_dump(content, sort_keys=False, allow_unicode=True), encoding="utf-8")
        ui.success(f"Empfänger '[bold]{device_id}[/bold]' zu {app_path.name}/secrets/recipients.yml hinzugefügt")

        # sdc secrets init ausführen
        secrets.do_init(app_path)

        if rekey:
            with ui.spinner("Verschlüssele Secrets neu (sdc secrets rekey) …"):
                secrets.do_rekey(app_path)
            ui.success(f"Secrets in [bold]{app_path.name}[/bold] für neues Notebook freigeschaltet!")

        return True
    except Exception as exc:
        ui.error(f"Fehler bei Secrets-Aktualisierung in {app_path}: {exc}")
        return False


def do_add(args: argparse.Namespace) -> int:
    member_id = getattr(args, "member", None)
    device_id = getattr(args, "id", None)
    device_name = getattr(args, "name", None)
    age_pub = getattr(args, "age", None)
    ssh_pub = getattr(args, "ssh", None)
    app_arg = getattr(args, "app", None)
    no_rekey = getattr(args, "no_rekey", False)

    members = team_data.list_members()

    # Interaktiver Assistent
    if not member_id or not device_id:
        ui.step("Notebook / Gerät hinzufügen")
        if not members:
            ui.warn("Noch kein Mitarbeiter erfasst. Bitte zuerst einen Mitarbeiter anlegen.")
            from . import member
            if member.do_add(argparse.Namespace()) != 0:
                return 1
            members = team_data.list_members()

        choices = [ui.choice_item(m["id"], f"{m['name']} ({m.get('role', 'developer')})", m["id"], pad=10) for m in members]
        if not member_id:
            member_id = ui.select("Zu welchem Mitarbeiter gehört dieses Notebook?", choices=choices)
            if not member_id:
                return 1

        # Prüfung, ob ein Gerät im Tailnet bereitsteht (z.B. via sdc orca init auf Omarchy)
        if not age_pub:
            from ..pairing import scan_beacons
            with ui.spinner("Prüfe auf neue Geräte im Tailnet …"):
                beacons = scan_beacons(timeout=0.8)
            if beacons:
                b_choices = [
                    ui.choice_item(
                        b.get("device_name", "unbekannt"),
                        f"[{b.get('platform', 'linux')}] IP: {b.get('discovered_ip')} – Daten aus 'sdc orca init' übernehmen",
                        b,
                        pad=14,
                    )
                    for b in beacons
                ]
                b_choices.append(ui.choice_item("local", "Lokales Gerät / manuell erfassen", None, pad=14))
                sel_beacon = ui.select("Geräte im Netzwerk/Tailnet gefunden:", choices=b_choices)
                if sel_beacon:
                    device_name = device_name or sel_beacon.get("device_name")
                    age_pub = sel_beacon.get("age_pubkey")
                    ssh_pub = sel_beacon.get("ssh_pubkey")
                    dev_plat = sel_beacon.get("platform", "linux")
                    suggested_id = f"{member_id}_{sel_beacon.get('device_name', dev_plat).lower().replace('-', '_')}"
                    device_id = ui.text("Eindeutige Geräte-ID:", default=suggested_id)

        detected_name = keys.detect_device_name()
        if not device_id:
            suggested_id = f"{member_id}_{keys.detect_os()}"
            device_id = ui.text("Eindeutige Geräte-ID:", default=suggested_id)
        if not device_name:
            device_name = ui.text("Anzeigename des Geräts:", default=detected_name)

    if not member_id or not device_id:
        ui.error("--member und --id sind erforderlich.")
        return 1

    device_id = device_id.strip().replace(" ", "_")
    device_name = (device_name or keys.detect_device_name()).strip()

    # age-Schlüssel sicherstellen
    if not age_pub:
        try:
            with ui.spinner("Prüfe lokalen age-Schlüssel …"):
                age_pub, created = keys.ensure_age_key()
            if created:
                ui.success("Neuer age-Schlüssel erzeugt: [bold]~/.config/sops/age/keys.txt[/bold] (Rechte 600)")
            else:
                ui.success(f"Lokalen age-Schlüssel gefunden: [dim]{age_pub[:14]}…{age_pub[-6:]}[/dim]")
        except Exception as exc:
            ui.error(f"Fehler beim age-Schlüssel: {exc}")
            return 1

    # SSH-Schlüssel ermitteln
    if not ssh_pub:
        try:
            ssh_pub, created_ssh = keys.ensure_ssh_key()
            if created_ssh:
                ui.success("Neuer SSH-Schlüssel erzeugt: [bold]~/.ssh/id_ed25519.pub[/bold]")
        except Exception:
            ssh_pub = ""

    # Gerät im Team eintragen
    try:
        with ui.spinner("Speichere Geräte-Registrierung …"):
            dev = team_data.add_device(member_id, device_id, device_name, age_pub, ssh_pub)
        ui.success(f"Gerät registriert: [bold white]{dev['id']}[/bold white] ({dev['name']}) bei [cyan]{member_id}[/cyan]")
    except ValueError as err:
        ui.error(f"Fehler beim Speichern: {err}")
        return 1

    # App-Secrets anbinden falls vorhanden
    app_path = _find_current_app(app_arg)
    if app_path:
        member = team_data.find_member(member_id)
        role = member.get("role", "developer") if member else "developer"
        _update_app_recipients(app_path, device_id, age_pub, role=role, rekey=not no_rekey)
    else:
        ui.info("Tipp: Führe 'sdc device add' in einem App-Verzeichnis aus, um Secrets direkt für dieses Notebook freizuschalten.")

    return 0


def do_list() -> int:
    devices = team_data.list_all_devices()
    if not devices:
        ui.warn("Noch keine Geräte registriert. Mit 'sdc device add' hinzufügen.")
        return 0

    cols = [
        ("Geräte-ID", {"style": "cyan bold"}),
        ("Gerätename", {"style": "white bold"}),
        ("Mitarbeiter", {"style": "green"}),
        ("age-Schlüssel", {"style": "dim"}),
        ("Hinzugefügt am", {"style": "dim"}),
    ]
    rows = []
    for member, dev in devices:
        age_str = dev.get("age", "")
        age_short = f"{age_str[:12]}…{age_str[-6:]}" if len(age_str) > 18 else age_str
        rows.append([
            dev.get("id", ""),
            dev.get("name", ""),
            f"{member.get('name', '')} ({member.get('id', '')})",
            age_short,
            dev.get("added", "") or "–",
        ])

    ui.table("SCHOENI DIGITAL — Registrierte Notebooks & Geräte", cols, rows)
    return 0


def run(args: argparse.Namespace) -> int:
    action = getattr(args, "action", None)
    if action == "add":
        return do_add(args)
    if action == "list" or not action:
        return do_list()
    ui.error(f"Unbekannte Aktion: {action}")
    return 1
