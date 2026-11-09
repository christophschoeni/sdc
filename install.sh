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
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd || true)"

if [ -f "$SCRIPT_DIR/pyproject.toml" ]; then
  "$UV" tool install --force --editable "$SCRIPT_DIR" || "$UV" tool install --force "$SCRIPT_DIR"
else
  INSTALLED=false
  for url in "ssh://git@git.schoeni-digital.com:2222/schoeni-digital/cli.git" "ssh://git@git.sd/schoeni-digital/cli.git" "https://git.schoeni-digital.com/schoeni-digital/cli.git"; do
    if "$UV" tool install --force "git+$url" 2>/dev/null; then
      INSTALLED=true
      break
    fi
  done
  [ "$INSTALLED" = true ] || "$UV" tool install --force "git+https://git.schoeni-digital.com/schoeni-digital/cli.git"
fi

SDC="$(command -v sdc 2>/dev/null || true)"
[ -z "$SDC" ] && [ -x "$HOME/.local/bin/sdc" ] && SDC="$HOME/.local/bin/sdc"

if [ -z "$SDC" ]; then
  fail "'sdc' wurde installiert, liegt aber nicht im PATH (~/.local/bin)."
fi
say "sdc ist einsatzbereit!"

# 5. Container-Laufzeit (Docker-First, Podman nur bei Bedarf)
info "Prüfe Container-Laufzeit …"
if command -v docker >/dev/null 2>&1; then
  say "Docker CLI ist vorhanden (vollkommen ausreichend — Podman wird nicht benötigt)."
elif command -v podman >/dev/null 2>&1; then
  say "Podman ist vorhanden."
else
  if [ "$IS_LINUX" = true ]; then
    info "Weder Docker noch Podman gefunden. Installiere Docker CLI …"
    if command -v apt-get >/dev/null 2>&1; then
      sudo apt-get update -qq && sudo apt-get install -y -qq docker.io || true
    elif command -v dnf >/dev/null 2>&1; then
      sudo dnf install -y docker || true
    elif command -v pacman >/dev/null 2>&1; then
      sudo pacman -S --noconfirm docker || true
    fi
  elif [ "$IS_MAC" = true ]; then
    warn "Keine Container-Laufzeit gefunden. Bitte Docker Desktop oder OrbStack installieren (z. B. 'brew install --cask docker')."
  fi
fi

# 6. T3 Code prüfen / installieren
info "Prüfe T3 Code …"
if command -v t3 >/dev/null 2>&1 || [ -d "/Applications/T3 Code.app" ] || [ -d "/Applications/T3 Code (Beta).app" ]; then
  say "T3 Code ist installiert."
else
  if [ "$IS_MAC" = true ] && command -v brew >/dev/null 2>&1; then
    info "Installiere T3 Code via brew …"
    brew install --cask t3-code || warn "T3 Code manuell von https://t3.codes/ laden."
  else
    info "T3 Code kann von https://t3.codes/ heruntergeladen werden."
  fi
fi

# 7. Orca prüfen / installieren
info "Prüfe Orca …"
if command -v orca >/dev/null 2>&1 || [ -d "/Applications/Orca.app" ]; then
  say "Orca ist installiert."
else
  if [ "$IS_MAC" = true ]; then
    DMG="$HOME/Downloads/orca-macos-arm64.dmg"
    if [ -f "$DMG" ]; then
      info "Installiere Orca aus vorhandenem Download ($DMG) …"
      hdiutil attach "$DMG" -nobrowse -quiet || true
      if [ -d "/Volumes/Orca/Orca.app" ]; then
        cp -R "/Volumes/Orca/Orca.app" /Applications/
        say "Orca.app nach /Applications installiert."
      fi
      hdiutil detach "/Volumes/Orca" -quiet 2>/dev/null || true
    else
      info "Orca kann von https://www.onorca.dev/download heruntergeladen werden."
    fi
  else
    info "Orca für Linux: https://www.onorca.dev/download"
  fi
fi

# 8. sdc doctor Diagnose
printf "\n"
"$SDC" doctor || true

# 9. Geräte-Onboarding & Orca-Verbindung
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
