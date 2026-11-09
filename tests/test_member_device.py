from pathlib import Path
import pytest
import yaml

from sdc.main import main
from sdc import team_data, keys


def test_member_add_and_list(tmp_path, monkeypatch):
    team_file = tmp_path / "team.yml"
    monkeypatch.setattr("sdc.team_data.team_config_path", lambda: team_file)

    # 1. Member anlegen
    rc = main(["member", "add", "--id", "cschoeni", "--name", "Christoph Schöni", "--role", "owner", "--email", "chris@schoeni.digital"])
    assert rc == 0

    # Daten in Datei prüfen
    team = team_data.load_team(team_file)
    assert len(team["members"]) == 1
    m = team["members"][0]
    assert m["id"] == "cschoeni"
    assert m["name"] == "Christoph Schöni"
    assert m["role"] == "owner"
    assert m["email"] == "chris@schoeni.digital"

    # Duplikat-Schutz
    rc_dup = main(["member", "add", "--id", "cschoeni", "--name", "Doppelt"])
    assert rc_dup == 1

    # Zweiter Member
    rc2 = main(["member", "add", "--id", "mmueller", "--name", "Max Müller", "--role", "developer"])
    assert rc2 == 0

    # 2. Member auflisten
    assert main(["member", "list"]) == 0


def test_device_add_and_list(tmp_path, monkeypatch):
    team_file = tmp_path / "team.yml"
    monkeypatch.setattr("sdc.team_data.team_config_path", lambda: team_file)

    # Member anlegen
    team_data.add_member("cschoeni", "Christoph Schöni", "owner")

    dummy_age = "age1nprzf49ls9323ly2qrgxt3knmdjlmttasmwnv5xjjq0zp0azf4dsn3mva2"
    dummy_ssh = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBzH7ruor3GW0xZLW04FWoDXzip93jy4PIu7p4EysTEl chris@mac"

    # Gerät für Member anlegen
    rc = main([
        "device", "add",
        "--member", "cschoeni",
        "--id", "cs_macbook",
        "--name", "MacBook Pro M2 (mac)",
        "--age", dummy_age,
        "--ssh", dummy_ssh,
    ])
    assert rc == 0

    # Prüfen in team.yml
    team = team_data.load_team(team_file)
    m = team["members"][0]
    assert len(m["devices"]) == 1
    d = m["devices"][0]
    assert d["id"] == "cs_macbook"
    assert d["name"] == "MacBook Pro M2 (mac)"
    assert d["age"] == dummy_age

    # Gerät auflisten
    assert main(["device", "list"]) == 0
    # Team-Übersicht auflisten
    assert main(["team"]) == 0


def test_device_add_with_app_integration(tmp_path, monkeypatch):
    team_file = tmp_path / "team.yml"
    monkeypatch.setattr("sdc.team_data.team_config_path", lambda: team_file)

    # Dummy-App mit recipients.yml vorbereiten
    app_dir = tmp_path / "my_app"
    app_dir.mkdir()
    (app_dir / "schoeni.yaml").write_text("project: my_app\nstage: dev\n")
    secrets_dir = app_dir / "secrets"
    secrets_dir.mkdir()
    recipients_file = secrets_dir / "recipients.yml"
    recipients_file.write_text(yaml.safe_dump({
        "recipients": [
            {"name": "recovery_offline", "role": "recovery", "age": "age1npmmq4l2pcv7ephuzhcqsy8aju4pp5ell8max04pg4pgdvrjn9wsjdxw09"}
        ]
    }))

    team_data.add_member("anna", "Anna Muster", "developer")

    dummy_age = "age1ffp8j6n4lam7qs8lc8g5guzth7ru053vxq3wr8rhe9fysznqvarsa2fm9v"
    rc = main([
        "device", "add",
        "--member", "anna",
        "--id", "anna_thinkpad",
        "--name", "ThinkPad X1 (linux)",
        "--age", dummy_age,
        "--app", str(app_dir),
        "--no-rekey",
    ])
    assert rc == 0

    # Prüfen, ob recipients.yml und .sops.yaml aktualisiert wurden
    content = yaml.safe_load(recipients_file.read_text())
    recs = content.get("recipients", [])
    assert any(r["name"] == "anna_thinkpad" and r["age"] == dummy_age for r in recs)

    # .sops.yaml sollte nun existieren und den Schlüssel enthalten
    sops_yaml = app_dir / ".sops.yaml"
    assert sops_yaml.exists()
    assert dummy_age in sops_yaml.read_text()
