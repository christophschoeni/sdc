import time
from sdc.main import main
from sdc.pairing import BeaconServer, probe_beacon, notify_paired


def test_beacon_server_and_probing():
    test_data = {
        "ok": True,
        "device_name": "omarchy-test",
        "platform": "linux",
        "tailscale_ip": "100.92.203.41",
        "orca_port": 6768,
        "pairing_code": "orca://pair?code=test12345",
        "web_client_url": "http://100.92.203.41:6768/web-index.html",
        "age_pubkey": "age1testpubkey1234567890",
        "ssh_pubkey": "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5 test@host",
    }

    server = BeaconServer(test_data, port=6799, host="127.0.0.1")
    server.start()

    try:
        # 1. Probing testen
        res = probe_beacon("127.0.0.1", port=6799, timeout=2.0)
        assert res is not None
        assert res["ok"] is True
        assert res["device_name"] == "omarchy-test"
        assert res["pairing_code"] == "orca://pair?code=test12345"
        assert res["age_pubkey"] == "age1testpubkey1234567890"

        # 2. Notification testen
        ok = notify_paired("127.0.0.1", client_name="macbook-test", port=6799)
        assert ok is True
        assert server.wait_for_paired(timeout=1.0) is True
        assert server.paired_by == "macbook-test"

    finally:
        server.stop()


def test_orca_help_includes_init_and_connect(capsys):
    try:
        main(["orca", "--help"])
    except SystemExit:
        pass
    out = capsys.readouterr().out
    assert "init" in out
    assert "connect" in out
    assert "status" in out
