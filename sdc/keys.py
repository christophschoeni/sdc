"""Schlüssel- und Geräte-Erkennung für SCHOENI DIGITAL (age, SSH, Hostname)."""
from __future__ import annotations

import os
import platform
import re
from pathlib import Path
import shutil
import socket
import subprocess

AGE_PUB_REGEX = re.compile(r"^age1[0-9a-z]{58}$")


def default_age_key_file() -> Path:
    env = os.environ.get("SOPS_AGE_KEY_FILE")
    if env:
        return Path(env).expanduser().resolve()
    return Path.home() / ".config" / "sops" / "age" / "keys.txt"


def read_age_public_key(key_file: Path | None = None) -> str | None:
    f = key_file or default_age_key_file()
    if not f.exists():
        return None
    for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line.startswith("# public key: "):
            pub = line.split(": ", 1)[1].strip()
            if AGE_PUB_REGEX.match(pub):
                return pub
        elif AGE_PUB_REGEX.match(line):
            return line
    return None


def ensure_age_key(key_file: Path | None = None) -> tuple[str, bool]:
    """Prüft oder generiert den lokalen age-Schlüssel.
    
    Gibt (public_key, created) zurück.
    Regel gemäss Entscheid 0015: Rechte 600.
    """
    f = key_file or default_age_key_file()
    pub = read_age_public_key(f)
    if pub:
        # Berechtigungen prüfen/korrigieren
        if f.exists() and (f.stat().st_mode & 0o077):
            f.chmod(0o600)
        return pub, False

    f.parent.mkdir(parents=True, exist_ok=True)
    exe = shutil.which("age-keygen")
    if not exe:
        raise RuntimeError("age-keygen ist nicht installiert (z. B. 'brew install age')")

    res = subprocess.run([exe, "-o", str(f)], capture_output=True, text=True, check=True)
    f.chmod(0o600)
    # age-keygen gibt den öffentlichen Schlüssel auf stderr aus
    for line in res.stderr.splitlines():
        if "public key:" in line.lower():
            pub = line.split(":", 1)[1].strip()
            if AGE_PUB_REGEX.match(pub):
                return pub, True

    # Fallback: Datei neu lesen
    pub = read_age_public_key(f)
    if pub:
        return pub, True
    raise RuntimeError(f"Konnte öffentlichen age-Schlüssel aus {f} nicht ermitteln")


def default_ssh_key_file() -> Path:
    return Path.home() / ".ssh" / "id_ed25519"


def read_ssh_public_key(pub_file: Path | None = None) -> str | None:
    f = pub_file or Path(f"{default_ssh_key_file()}.pub")
    if f.exists():
        return f.read_text(encoding="utf-8", errors="replace").strip()
    return None


def ensure_ssh_key(key_file: Path | None = None, comment: str | None = None) -> tuple[str, bool]:
    """Liest oder generiert einen ed25519 SSH-Schlüssel."""
    priv = key_file or default_ssh_key_file()
    pub_file = Path(f"{priv}.pub")
    if pub_file.exists():
        return pub_file.read_text(encoding="utf-8", errors="replace").strip(), False

    priv.parent.mkdir(parents=True, exist_ok=True)
    exe = shutil.which("ssh-keygen")
    if not exe:
        raise RuntimeError("ssh-keygen ist nicht verfügbar")

    comm = comment or f"{os.environ.get('USER', 'dev')}@{socket.gethostname()}"
    subprocess.run([exe, "-t", "ed25519", "-N", "", "-C", comm, "-f", str(priv)],
                   capture_output=True, text=True, check=True)
    priv.chmod(0o600)
    pub_file.chmod(0o644)
    return pub_file.read_text(encoding="utf-8", errors="replace").strip(), True


def detect_os() -> str:
    s = platform.system().lower()
    if "darwin" in s:
        return "mac"
    if "windows" in s:
        return "windows"
    return "linux"


def detect_device_name() -> str:
    """Ermittelt den Rechnernamen (unter macOS den Computernamen)."""
    os_name = detect_os()
    if os_name == "mac":
        try:
            res = subprocess.run(["scutil", "--get", "ComputerName"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0 and res.stdout.strip():
                return f"{res.stdout.strip()} (mac)"
        except (subprocess.TimeoutExpired, OSError):
            pass
    return f"{socket.gethostname()} ({os_name})"
