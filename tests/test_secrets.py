"""Integration test with the real sops and age binaries (skipped if missing)."""
import shutil
import subprocess
from pathlib import Path

import pytest

from sdc.commands import secrets
from sdc.main import main
from sdc.paths import template_root

needs_tools = pytest.mark.skipif(not (shutil.which("sops") and shutil.which("age-keygen")), reason="sops/age fehlen")


def keygen(path: Path) -> str:
    out = subprocess.run(["age-keygen", "-o", str(path)], capture_output=True, text=True, check=True)
    return out.stderr.strip().split(": ")[-1]


@pytest.fixture
def app(tmp_path, monkeypatch):
    dest = tmp_path / "app"
    shutil.copytree(template_root(), dest)
    (dest / "schoeni.yaml").write_text((dest / "schoeni.yaml").read_text().replace("schoeni_template", "probe"))
    key = tmp_path / "keys.txt"
    owner_pub = keygen(key)
    key.chmod(0o600)
    monkeypatch.setenv("SOPS_AGE_KEY_FILE", str(key))
    recovery_pub = keygen(tmp_path / "recovery.txt")
    raw_rec = (dest / "secrets" / "recipients.yml").read_text()
    import re
    rec = re.sub(r"(name:\s*recovery_offline[\s\S]*?age:\s*)\S+", r"\g<1>" + recovery_pub, raw_rec)
    (dest / "secrets" / "recipients.yml").write_text(rec)
    subprocess.run(["git", "init", "-q"], cwd=dest, check=True)
    return dest, owner_pub, recovery_pub


@needs_tools
def test_init_check_pull_roundtrip(app, capsys):
    dest, owner_pub, recovery_pub = app
    assert main(["secrets", "init", "--path", str(dest)]) == 0
    sops_yaml = (dest / ".sops.yaml").read_text()
    assert owner_pub in sops_yaml and recovery_pub in sops_yaml

    enc = dest / "secrets" / "probe" / "dev.enc.env"
    enc.parent.mkdir(parents=True)
    enc.write_text("SECRET_KEY=a\nFIELD_ENCRYPTION_KEY=b\nDATABASE_URL=c\nCORS_ALLOWED_ORIGINS=d\n")
    subprocess.run(["sops", "-e", "-i", "--input-type", "dotenv", "--output-type", "dotenv", str(enc)], cwd=dest, check=True)
    assert "ENC[" in enc.read_text() and "SECRET_KEY=a" not in enc.read_text()
    assert secrets.recipients_in_file(enc) == {owner_pub, recovery_pub}

    assert main(["secrets", "check", "--env", "dev", "--path", str(dest)]) == 0
    assert main(["secrets", "pull", "--env", "dev", "--path", str(dest)]) == 0
    assert "SECRET_KEY=a" in (dest / ".env").read_text()
    assert oct((dest / ".env").stat().st_mode & 0o777) == "0o600"


@needs_tools
def test_check_fails_on_missing_required_and_tracked_env(app, capsys):
    dest, *_ = app
    main(["secrets", "init", "--path", str(dest)])
    enc = dest / "secrets" / "probe" / "dev.enc.env"
    enc.parent.mkdir(parents=True)
    enc.write_text("SECRET_KEY=a\n")
    subprocess.run(["sops", "-e", "-i", "--input-type", "dotenv", "--output-type", "dotenv", str(enc)], cwd=dest, check=True)
    (dest / ".env").write_text("X=1\n")
    subprocess.run(["git", "add", "-f", ".env"], cwd=dest, check=True)
    assert main(["secrets", "check", "--env", "dev", "--path", str(dest)]) == 1
    out = capsys.readouterr().out
    assert "fehlt: CORS_ALLOWED_ORIGINS" in out and ".env ist im Git" in out


def test_gitignore_blocks_plaintext():
    gi = (template_root() / ".gitignore").read_text()
    assert ".env" in gi and "!secrets/**/*.enc.env" in gi


@needs_tools
def test_set_creates_file_and_stores_value(app, monkeypatch, capsys):
    import io
    dest, owner_pub, _ = app
    main(["secrets", "init", "--path", str(dest)])
    monkeypatch.setattr("sys.stdin", io.StringIO("tok-123\n"))
    assert main(["secrets", "set", "HCLOUD_TOKEN", "--env", "prod", "--value-from-stdin", "--path", str(dest)]) == 0
    enc = dest / "secrets" / "probe" / "prod.enc.env"
    text = enc.read_text()
    assert "tok-123" not in text and "HCLOUD_TOKEN=ENC[" in text
    assert "HCLOUD_TOKEN=tok-123" in secrets.decrypt(dest, enc)
