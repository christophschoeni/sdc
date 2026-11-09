from pathlib import Path
from sdc.commands.sync import discover_apps, AppInfo
from sdc.main import main
from sdc.paths import workspace_root


def test_workspace_root_resolves_to_projekte():
    ws = workspace_root()
    assert ws.exists()
    assert "SCHOENI" in ws.name
    assert ws.parent.name == "Projekte" or "Projekte" in str(ws)


def test_discover_apps_includes_known_apps():
    apps = discover_apps()
    app_names = {a.name for a in apps}
    assert "core" in app_names
    assert "cli" in app_names
    assert "billflow-site" in app_names
    assert "bootstrap" in app_names
    assert "ops" in app_names
    assert "vacation_app" in app_names


def test_sync_status_command(capsys):
    rc = main(["sync", "--status"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "SCHOENI DIGITAL Applikationen" in out
    assert "core" in out
    assert "cli" in out


def test_sync_unknown_app(capsys):
    rc = main(["sync", "non_existent_app_xyz"])
    assert rc == 1
    out = capsys.readouterr().out
    assert "nicht im Katalog gefunden" in out


def test_help_grouped_includes_sync(capsys):
    try:
        main(["--help"])
    except SystemExit:
        pass
    out = capsys.readouterr().out
    assert "sync" in out
    assert "PROJEKTE & VORLAGE" in out
