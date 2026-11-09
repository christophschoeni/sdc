"""sdc setup: Vollständiges Einrichten und Nachinstallieren aller Arbeitsplatz-Tools."""
from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
from pathlib import Path

from .. import ui

HELP = "Alle benötigten Entwickler-Tools, Orca und T3 Code auf diesem Gerät installieren"


def register(p: argparse.ArgumentParser) -> None:
    p.add_argument("-y", "--yes", action="store_true", help="Ohne Rückfragen installieren")
    p.add_argument("--skip-orca", action="store_true", help="Orca-Installation überspringen")
    p.add_argument("--skip-t3", action="store_true", help="T3 Code-Installation überspringen")
    p.add_argument("--skip-docker", action="store_true", help="Container-Installation überspringen")


def _is_tool_installed(name: str) -> bool:
    return shutil.which(name) is not None


def _detect_system() -> str:
    s = platform.system().lower()
    if "darwin" in s:
        return "mac"
    if "windows" in s:
        return "windows"
    return "linux"


def _install_mac_tool(name: str, brew_pkg: str, is_cask: bool = False) -> bool:
    brew = shutil.which("brew")
    if not brew:
        ui.warn(f"Homebrew nicht gefunden — bitte manuell installieren: {brew_pkg}")
        return False

    with ui.spinner(f"Installiere {name} via brew …"):
        cmd = [brew, "install"]
        if is_cask:
            cmd.append("--cask")
        cmd.append(brew_pkg)
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            ui.success(f"{name} erfolgreich installiert.")
            return True
        else:
            ui.error(f"Installation von {name} fehlgeschlagen: {res.stderr.strip()}")
            return False


def _install_linux_package(pkg_name: str) -> bool:
    managers = [
        ("apt-get", ["sudo", "apt-get", "install", "-y", pkg_name]),
        ("dnf", ["sudo", "dnf", "install", "-y", pkg_name]),
        ("pacman", ["sudo", "pacman", "-S", "--noconfirm", pkg_name]),
    ]
    for mgr, cmd in managers:
        if shutil.which(mgr):
            with ui.spinner(f"Installiere {pkg_name} via {mgr} …"):
                res = subprocess.run(cmd, capture_output=True, text=True)
                return res.returncode == 0
    return False


def _install_sops(system: str) -> bool:
    if system == "mac":
        return _install_mac_tool("sops", "sops")
    elif system == "linux":
        arch = platform.machine().lower()
        sops_arch = "arm64" if "arm" in arch or "aarch" in arch else "amd64"
        url = f"https://github.com/getsops/sops/releases/latest/download/sops-v3.13.3.linux.{sops_arch}"
        local_bin = Path.home() / ".local" / "bin"
        local_bin.mkdir(parents=True, exist_ok=True)
        dest = local_bin / "sops"
        with ui.spinner("Lade sops von GitHub herunter …"):
            res = subprocess.run(["curl", "-fsSL", "-o", str(dest), url], capture_output=True)
        if res.returncode == 0 and dest.exists():
            dest.chmod(0o755)
            ui.success(f"sops erfolgreich in {dest} installiert.")
            return True
    return False


def _install_t3(system: str) -> bool:
    if system == "mac":
        return _install_mac_tool("T3 Code", "t3-code", is_cask=True)
    elif system == "linux":
        with ui.spinner("Installiere T3 Code via https://t3.codes/install.sh …"):
            res = subprocess.run("curl -fsSL https://t3.codes/install.sh | bash", shell=True, capture_output=True)
            if res.returncode == 0 or shutil.which("t3"):
                ui.success("T3 Code erfolgreich installiert.")
                return True
    return False


def _install_orca(system: str) -> bool:
    arch = platform.machine().lower()
    if system == "mac":
        dmg_name = "orca-macos-arm64.dmg" if "arm" in arch or "aarch" in arch else "orca-macos-x64.dmg"
        dmg_url = f"https://github.com/stablyai/orca/releases/latest/download/{dmg_name}"
        tmp_dmg = Path("/tmp/orca-installer.dmg")
        with ui.spinner("Lade Orca für macOS herunter …"):
            res = subprocess.run(["curl", "-fsSL", "-o", str(tmp_dmg), dmg_url], capture_output=True)
        if res.returncode == 0 and tmp_dmg.exists():
            with ui.spinner("Installiere Orca.app nach /Applications …"):
                subprocess.run(["hdiutil", "attach", str(tmp_dmg), "-nobrowse", "-quiet"])
                vol = Path("/Volumes/Orca")
                if vol.exists() and (vol / "Orca.app").exists():
                    subprocess.run(["cp", "-R", str(vol / "Orca.app"), "/Applications/"])
                subprocess.run(["hdiutil", "detach", "/Volumes/Orca", "-quiet"])
                tmp_dmg.unlink(missing_ok=True)
            cli_bin = Path("/Applications/Orca.app/Contents/Resources/bin/orca")
            if cli_bin.exists():
                local_bin = Path.home() / ".local" / "bin"
                local_bin.mkdir(parents=True, exist_ok=True)
                target = local_bin / "orca"
                target.unlink(missing_ok=True)
                target.symlink_to(cli_bin)
            ui.success("Orca.app erfolgreich nach /Applications installiert.")
            return True
    elif system == "linux":
        appimage_name = "orca-linux-arm64.AppImage" if "arm" in arch or "aarch" in arch else "orca-linux.AppImage"
        appimage_url = f"https://github.com/stablyai/orca/releases/latest/download/{appimage_name}"
        local_bin = Path.home() / ".local" / "bin"
        local_bin.mkdir(parents=True, exist_ok=True)
        dest = local_bin / "orca"
        with ui.spinner("Lade Orca AppImage für Linux herunter …"):
            res = subprocess.run(["curl", "-fsSL", "-o", str(dest), appimage_url], capture_output=True)
        if res.returncode == 0 and dest.exists():
            dest.chmod(0o755)
            ui.success(f"Orca AppImage erfolgreich in {dest} installiert.")
            return True
    return False


def run(args: argparse.Namespace) -> int:
    system = _detect_system()
    assume_yes = getattr(args, "yes", False)

    ui.step("System-Setup: Werkzeuge, Container, Orca & T3 Code")
    ui.info(f"Erkanntes System: [bold white]{system.upper()}[/bold white]")

    # 1. uv (Python)
    if not _is_tool_installed("uv"):
        ui.step("1. Python-Manager uv")
        if assume_yes or ui.confirm("uv installieren?", default=True):
            with ui.spinner("Installiere uv von astral.sh …"):
                res = subprocess.run("curl -LsSf https://astral.sh/uv/install.sh | sh", shell=True)
            if res.returncode == 0:
                ui.success("uv installiert.")
    else:
        ui.success("uv ist bereits vorhanden.")

    # 2. Basis-Entwickler-Tools: Git, age, sops, tailscale
    ui.step("2. Entwickler-Tools (Git, age, sops, tailscale)")
    if system == "mac":
        for exe, pkg in [("git", "git"), ("age", "age"), ("sops", "sops"), ("tailscale", "tailscale"), ("node", "node")]:
            if not _is_tool_installed(exe):
                if assume_yes or ui.confirm(f"{exe} via Homebrew installieren?", default=True):
                    _install_mac_tool(exe, pkg)
            else:
                ui.success(f"{exe} ist vorhanden.")
    elif system == "linux":
        for exe in ["git", "age", "nodejs"]:
            if not _is_tool_installed(exe):
                if assume_yes or ui.confirm(f"{exe} via Paketmanager installieren?", default=True):
                    _install_linux_package(exe)
            else:
                ui.success(f"{exe} ist vorhanden.")
        if not _is_tool_installed("sops"):
            if assume_yes or ui.confirm("sops installieren?", default=True):
                _install_sops(system)
        else:
            ui.success("sops ist vorhanden.")
        if not _is_tool_installed("tailscale"):
            if assume_yes or ui.confirm("Tailscale installieren?", default=True):
                with ui.spinner("Installiere Tailscale …"):
                    subprocess.run("curl -fsSL https://tailscale.com/install.sh | sh", shell=True)

    # 3. Container-Laufzeit (Docker-First!)
    ui.step("3. Container-Laufzeit")
    has_docker = _is_tool_installed("docker")
    has_podman = _is_tool_installed("podman")

    if has_docker:
        ui.success("Docker CLI ist vorhanden (vollkommen ausreichend, Podman wird nicht benötigt).")
    elif has_podman:
        ui.success("Podman ist vorhanden.")
    else:
        ui.warn("Weder Docker noch Podman gefunden.")
        if not getattr(args, "skip_docker", False):
            if system == "linux":
                ui.info("Auf Linux wird Docker CLI empfohlen (Podman ist nicht zwingend notwendig).")
                if assume_yes or ui.confirm("Docker installieren?", default=True):
                    _install_linux_package("docker.io") or _install_linux_package("docker")
                    subprocess.run(f"sudo usermod -aG docker {os.environ.get('USER', 'root')}", shell=True)
            elif system == "mac":
                if assume_yes or ui.confirm("Docker via brew installieren?", default=True):
                    _install_mac_tool("Docker Desktop", "docker", is_cask=True)

    # 4. T3 Code
    ui.step("4. T3 Code (AI Code GUI)")
    has_t3 = _is_tool_installed("t3") or Path("/Applications/T3 Code.app").exists() or Path("/Applications/T3 Code (Beta).app").exists()
    if has_t3:
        ui.success("T3 Code ist bereits installiert.")
    elif not getattr(args, "skip_t3", False):
        if assume_yes or ui.confirm("T3 Code installieren?", default=True):
            _install_t3(system)

    # 5. Orca Agent & Desktop App
    ui.step("5. Orca Agenten-Plattform")
    has_orca = _is_tool_installed("orca") or Path("/Applications/Orca.app").exists()
    if has_orca:
        ui.success("Orca ist bereits installiert.")
    elif not getattr(args, "skip_orca", False):
        if assume_yes or ui.confirm("Orca jetzt automatisch herunterladen und installieren?", default=True):
            _install_orca(system)

    # 6. Rechner in Orca sichtbar machen
    ui.step("6. Rechner in Orca sichtbar machen")
    if _is_tool_installed("orca") and (assume_yes or ui.confirm("Orca Server (orca serve) jetzt starten?", default=False)):
        from . import orca_cmd
        orca_cmd.do_serve(argparse.Namespace(bind="0.0.0.0", port=6768, mobile=False))
    else:
        ui.info("Tipp: Führe jederzeit [bold cyan]sdc orca serve[/bold cyan] aus, um diesen PC im Netzwerk für Orca bereitzustellen.")

    return 0
