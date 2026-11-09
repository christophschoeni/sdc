#!/usr/bin/env bash
# SCHOENI DIGITAL CLI (`sdc`) — Vollständiger All-in-One Installer für macOS & Linux
#
# Schnelle 1-Zeiler-Installation auf jedem neuen Gerät:
#   curl -fsSL https://git.schoeni-digital.com/schoeni-digital/cli/raw/branch/main/install.sh | bash
#
set -euo pipefail

# ANSI Farben
GREEN='\033[1;32m'
CYAN='\033[1;36m'
YELLOW='\033[1;33m'
RED='\033[1;31m'
NC='\033[0m'
DIM='\033[2m'

say()  { printf "\n${GREEN}[ok]${NC} %s\n" "$1"; }
info() { printf "${CYAN}[info]${NC} %s\n" "$1"; }
warn() { printf "${YELLOW}[warn]${NC} %s\n" "$1"; }
fail() { printf "\n${RED}[fehler]${NC} %s\n" "$1" >&2; exit 1; }

printf "\n${CYAN}╭────────────────────────────────────────────────────────╮${NC}\n"
printf "${CYAN}│${NC}  ${GREEN}◆ SCHOENI DIGITAL${NC} · Arbeitsplatz & sdc Setup          ${CYAN}│${NC}\n"
printf "${CYAN}│${NC}  ${DIM}Entwickler-Tools · Docker · Orca · T3 Code${NC}             ${CYAN}│${NC}\n"
printf "${CYAN}╰────────────────────────────────────────────────────────╯${NC}\n\n"

# 1. Betriebssystem prüfen
OS="$(uname -s)"
IS_MAC=false
IS_LINUX=false
case "$OS" in
  Darwin*)  info "Plattform: macOS (Apple Darwin)"; IS_MAC=true ;;
  Linux*)   info "Plattform: Linux"; IS_LINUX=true ;;
  *)        warn "Unbekanntes System: $OS (Installation wird versucht …)" ;;
esac

# 2. uv (moderner Python-Manager) prüfen oder installieren
info "Prüfe Python-Paketmanager uv …"
UV="$(command -v uv 2>/dev/null || true)"
if [ -z "$UV" ] && [ -x "$HOME/.local/bin/uv" ]; then
  UV="$HOME/.local/bin/uv"
elif [ -z "$UV" ] && [ -x "$HOME/.cargo/bin/uv" ]; then
  UV="$HOME/.cargo/bin/uv"
fi

if [ -z "$UV" ]; then
  info "Installiere uv von https://astral.sh/uv …"
  curl -LsSf https://astral.sh/uv/install.sh | sh || fail "uv liess sich nicht installieren."
  UV="$HOME/.local/bin/uv"
fi
[ -x "$UV" ] || fail "uv ist nicht ausführbar: $UV"
say "uv ist bereit: $($UV --version)"

# 3. PATH sicherstellen
export PATH="$HOME/.local/bin:$PATH"

# 4. sdc CLI installieren
info "Installiere 'sdc' Werkzeug via uv tool …"
SCRIPT_DIR=""
if [ -n "${BASH_SOURCE:-}" ] && [ ${#BASH_SOURCE[@]} -gt 0 ]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd || true)"
fi

if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/pyproject.toml" ]; then
  "$UV" tool install --force --editable "$SCRIPT_DIR" || "$UV" tool install --force "$SCRIPT_DIR"
else
  INSTALLED=false
  for url in "https://github.com/christophschoeni/sdc.git" "ssh://git@git.schoeni-digital.com:2222/schoeni-digital/cli.git" "ssh://git@git.sd/schoeni-digital/cli.git" "https://git.schoeni-digital.com/schoeni-digital/cli.git"; do
    if "$UV" tool install --force "git+$url" 2>/dev/null; then
      INSTALLED=true
      break
    fi
  done
  [ "$INSTALLED" = true ] || "$UV" tool install --force "git+https://github.com/christophschoeni/sdc.git"
fi

SDC="$(command -v sdc 2>/dev/null || true)"
[ -z "$SDC" ] && [ -x "$HOME/.local/bin/sdc" ] && SDC="$HOME/.local/bin/sdc"

if [ -z "$SDC" ]; then
  fail "'sdc' wurde installiert, liegt aber nicht im PATH (~/.local/bin)."
fi
say "sdc ist einsatzbereit!"

# 5. Entwickler-Tools (git, age, sops, tailscale)
info "Prüfe Entwickler-Tools (git, age, sops, tailscale) …"
if [ "$IS_LINUX" = true ]; then
  if ! command -v git >/dev/null 2>&1 || ! command -v age >/dev/null 2>&1; then
    info "Installiere Basis-Tools (git, age) …"
    if command -v apt-get >/dev/null 2>&1; then
      sudo apt-get update -qq && sudo apt-get install -y -qq git age || true
    elif command -v dnf >/dev/null 2>&1; then
      sudo dnf install -y git age || true
    elif command -v pacman >/dev/null 2>&1; then
      sudo pacman -S --noconfirm git age || true
    fi
  fi
  if ! command -v sops >/dev/null 2>&1; then
    info "Installiere sops …"
    SOPS_ARCH="amd64"
    ARCH="$(uname -m)"
    [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ] && SOPS_ARCH="arm64"
    mkdir -p "$HOME/.local/bin"
    curl -fsSL -o "$HOME/.local/bin/sops" "https://github.com/getsops/sops/releases/latest/download/sops-v3.13.3.linux.${SOPS_ARCH}" 2>/dev/null && chmod +x "$HOME/.local/bin/sops" || true
  fi
  if ! command -v tailscale >/dev/null 2>&1; then
    info "Installiere Tailscale …"
    curl -fsSL https://tailscale.com/install.sh | sh 2>/dev/null || true
  fi
elif [ "$IS_MAC" = true ] && command -v brew >/dev/null 2>&1; then
  for pkg in git age sops tailscale; do
    if ! command -v "$pkg" >/dev/null 2>&1; then
      info "Installiere $pkg via brew …"
      brew install "$pkg" || true
    fi
  done
fi

# 6. Container-Laufzeit (Docker-First, Podman nur bei Bedarf)
info "Prüfe Container-Laufzeit …"
if command -v docker >/dev/null 2>&1; then
  say "Docker CLI ist vorhanden (vollkommen ausreichend — Podman wird nicht benötigt)."
elif command -v podman >/dev/null 2>&1; then
  say "Podman ist vorhanden."
else
  if [ "$IS_LINUX" = true ]; then
    info "Weder Docker noch Podman gefunden. Installiere Docker CLI …"
    if command -v apt-get >/dev/null 2>&1; then
      sudo apt-get update -qq && sudo apt-get install -y -qq docker.io || curl -fsSL https://get.docker.com | sh || true
    elif command -v dnf >/dev/null 2>&1; then
      sudo dnf install -y docker || true
    elif command -v pacman >/dev/null 2>&1; then
      sudo pacman -S --noconfirm docker || true
    else
      curl -fsSL https://get.docker.com | sh || true
    fi
    sudo usermod -aG docker "$USER" 2>/dev/null || true
    say "Docker CLI installiert."
  elif [ "$IS_MAC" = true ]; then
    if command -v brew >/dev/null 2>&1; then
      info "Installiere Docker via Homebrew …"
      brew install --cask docker || true
    else
      warn "Keine Container-Laufzeit gefunden. Bitte Docker Desktop installieren."
    fi
  fi
fi

# 7. T3 Code prüfen / installieren
info "Prüfe T3 Code …"
if command -v t3 >/dev/null 2>&1 || [ -d "/Applications/T3 Code.app" ] || [ -d "/Applications/T3 Code (Beta).app" ]; then
  say "T3 Code ist bereits installiert."
else
  info "Installiere T3 Code …"
  if [ "$IS_MAC" = true ] && command -v brew >/dev/null 2>&1; then
    brew install --cask t3-code || true
  elif [ "$IS_LINUX" = true ]; then
    curl -fsSL https://t3.codes/install.sh | bash 2>/dev/null || curl -fsSL https://t3.codes/install.sh | sh 2>/dev/null || true
  fi
  if command -v t3 >/dev/null 2>&1 || [ -d "/Applications/T3 Code.app" ] || [ -d "/Applications/T3 Code (Beta).app" ]; then
    say "T3 Code erfolgreich installiert."
  fi
fi

# 8. Orca prüfen / installieren
info "Prüfe Orca …"
if command -v orca >/dev/null 2>&1 || [ -d "/Applications/Orca.app" ]; then
  say "Orca ist bereits installiert."
else
  info "Installiere Orca …"
  mkdir -p "$HOME/.local/bin"
  ARCH="$(uname -m)"

  if [ "$IS_MAC" = true ]; then
    DMG_URL="https://github.com/stablyai/orca/releases/latest/download/orca-macos-arm64.dmg"
    [ "$ARCH" != "arm64" ] && DMG_URL="https://github.com/stablyai/orca/releases/latest/download/orca-macos-x64.dmg"
    TMP_DMG="/tmp/orca-installer.dmg"
    if curl -fsSL -o "$TMP_DMG" "$DMG_URL"; then
      hdiutil attach "$TMP_DMG" -nobrowse -quiet 2>/dev/null || true
      if [ -d "/Volumes/Orca/Orca.app" ]; then
        cp -R "/Volumes/Orca/Orca.app" /Applications/
        say "Orca.app nach /Applications installiert."
      fi
      hdiutil detach "/Volumes/Orca" -quiet 2>/dev/null || true
      rm -f "$TMP_DMG"
    fi
    if [ -x "/Applications/Orca.app/Contents/Resources/bin/orca" ]; then
      ln -sf "/Applications/Orca.app/Contents/Resources/bin/orca" "$HOME/.local/bin/orca"
    fi
  elif [ "$IS_LINUX" = true ]; then
    APPIMAGE_URL="https://github.com/stablyai/orca/releases/latest/download/orca-linux.AppImage"
    [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ] && APPIMAGE_URL="https://github.com/stablyai/orca/releases/latest/download/orca-linux-arm64.AppImage"

    # 1. Option: AppImage direkt als ~/.local/bin/orca
    if curl -fsSL -o "$HOME/.local/bin/orca" "$APPIMAGE_URL"; then
      chmod +x "$HOME/.local/bin/orca"
      say "Orca AppImage erfolgreich in ~/.local/bin/orca installiert."
    fi
  fi

  if command -v orca >/dev/null 2>&1 || [ -x "$HOME/.local/bin/orca" ] || [ -d "/Applications/Orca.app" ]; then
    say "Orca ist einsatzbereit."
  fi
fi

# 9. sdc doctor Diagnose
printf "\n"
"$SDC" doctor || true

# 10. Geräte-Onboarding & Orca-Verbindung
printf "\n${GREEN}╭────────────────────────────────────────────────────────╮${NC}\n"
printf "${GREEN}│${NC}  ${GREEN}[ok] Installation erfolgreich abgeschlossen!${NC}          ${GREEN}│${NC}\n"
printf "${GREEN}│${NC}                                                         ${GREEN}│${NC}\n"
printf "${GREEN}│${NC}  1. Registriere dieses Notebook mit:                    ${GREEN}│${NC}\n"
printf "${GREEN}│${NC}     ${CYAN}sdc device add${NC}                                     ${GREEN}│${NC}\n"
printf "${GREEN}│${NC}                                                         ${GREEN}│${NC}\n"
printf "${GREEN}│${NC}  2. Mache diesen PC in Orca sichtbar mit:               ${GREEN}│${NC}\n"
printf "${GREEN}│${NC}     ${CYAN}sdc orca serve${NC}                                     ${GREEN}│${NC}\n"
printf "${GREEN}│${NC}                                                         ${GREEN}│${NC}\n"
printf "${GREEN}│${NC}  3. Starte das Dashboard mit:                           ${GREEN}│${NC}\n"
printf "${GREEN}│${NC}     ${CYAN}sdc${NC}                                                ${GREEN}│${NC}\n"
printf "${GREEN}╰────────────────────────────────────────────────────────╯${NC}\n\n"
