"""sdc glass: remote desktop for your own devices (Glassdesk, open source, over Tailscale).

install · link · account · remote on|off · status. Thin wrapper around the `glass` CLI
(https://github.com/Ntarasiuk/glass). Hosts: macOS 13+, Linux (Wayland, beta).
"""
import shutil
import subprocess
import sys

HELP = "Fernzugriff auf eigene Geräte (Glassdesk über Tailscale): install · link · account · remote · status"


def register(p):
    p.add_argument("action", choices=["install", "link", "account", "remote", "status"])
    p.add_argument("rest", nargs="*", help="weitere Argumente, z.B. `remote on`, `link --anywhere`, `account add`")
    p.add_argument("--yes", action="store_true", help="install: ohne Rückfrage")


def run(args) -> int:
    if args.action == "install":
        if shutil.which("glass"):
            print("glass ist installiert:", shutil.which("glass")); return 0
        if sys.platform not in ("darwin", "linux"):
            raise RuntimeError("Glass-Host gibt es nur für macOS und Linux")
        print("Installiert Glassdesk (open source, MIT) mit dem offiziellen Skript von glassdesk.dev.")
        if sys.platform == "linux":
            print("Linux ist Beta und braucht Wayland; vorher z.B. unter Ubuntu: sudo apt-get install pipewire xdg-desktop-portal-gnome wl-clipboard")
        if not args.yes:
            ok = input("Fortfahren? [ja/nein] ").strip().lower()
            if ok != "ja":
                return 1
        return subprocess.run("curl -fsSL glassdesk.dev | sh", shell=True).returncode
    exe = shutil.which("glass")
    if not exe:
        raise RuntimeError("glass nicht installiert: sdc glass install")
    argv = {"link": ["link"], "account": ["account"], "remote": ["remote"], "status": ["status"]}[args.action] + list(args.rest)
    return subprocess.run([exe, *argv]).returncode
