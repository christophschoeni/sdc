from sdc.main import main


def test_orca_status_command():
    # orca status aufrufen
    rc = main(["orca", "status"])
    assert rc in (0, 1)


def test_doctor_with_docker_and_orca(capsys):
    rc = main(["doctor"])
    out = capsys.readouterr().out
    assert "Orca Agent" in out
    assert "T3 Code" in out
    assert "Container:" in out or "Container-Laufzeit" in out
