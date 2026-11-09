"""sdc team: Gesamtsicht über Team und zugewiesene Geräte."""
from __future__ import annotations

import argparse
from .. import team_data, ui

HELP = "Team-Übersicht: Mitarbeiter, Rollen und deren registrierte Geräte"


def register(p: argparse.ArgumentParser) -> None:
    pass


def run(args: argparse.Namespace) -> int:
    members = team_data.list_members()
    if not members:
        ui.warn("Noch kein Team erfasst. Beginne mit 'sdc member add'.")
        return 0

    cols = [
        ("Mitarbeiter", {"style": "white bold"}),
        ("Rolle", {"style": "green"}),
        ("E-Mail", {"style": "dim"}),
        ("Geräte-ID", {"style": "cyan bold"}),
        ("Gerätename", {"style": "white"}),
        ("age-Schlüssel", {"style": "dim"}),
    ]
    rows = []
    for m in members:
        devs = m.get("devices", [])
        if not devs:
            rows.append([f"{m.get('name')} ({m.get('id')})", m.get("role", ""), m.get("email") or "–", "–", "–", "–"])
        else:
            for i, d in enumerate(devs):
                age_str = d.get("age", "")
                age_short = f"{age_str[:12]}…{age_str[-6:]}" if len(age_str) > 18 else age_str
                m_label = f"{m.get('name')} ({m.get('id')})" if i == 0 else ""
                r_label = m.get("role", "") if i == 0 else ""
                e_label = (m.get("email") or "–") if i == 0 else ""
                rows.append([m_label, r_label, e_label, d.get("id", ""), d.get("name", ""), age_short])

    ui.table("SCHOENI DIGITAL — Team & Geräte", cols, rows)
    return 0
