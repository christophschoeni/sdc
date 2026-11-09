#!/usr/bin/env bash
# SCHOENI DIGITAL CLI (`sdc`) — Installations-Skript für macOS & Linux
#
# Schnelle 1-Zeiler-Installation auf jedem neuen Gerät:
#   curl -fsSL https://git.schoeni-digital.com/schoeni-digital/cli/raw/branch/main/install.sh | bash
# oder lokal im Repo:
#   ./install.sh
#
set -euo pipefail

# ANSI Farben
GREEN='\033[1;32m'
CYAN='\033[1;36m'
YELLOW='\033[1;33m'
RED='\033[1;31m'
NC='\033[0m' # No Color
DIM='\033[2m'

say()  { printf "\n${GREEN}✔${NC} %s\n" "$1"; }
info() { printf "${CYAN}ℹ${NC} %s\n" "$1"; }
warn() { printf "${YELLOW}▲${NC} %s\n" "$1"; }
fail() { printf "\n${RED}✖ FEHLER:${NC} %s\n" "$1" >&2; exit 1; }

printf "\n${CYAN}╭────────────────────────────────────────────────────────╮${NC}\n"
printf "${CYAN}│${NC}  ${GREEN}◆ SCHOENI DIGITAL${NC} · sdc Installations-Assistent       ${CYAN}│${NC}\n"
printf "${CYAN}│${NC}  ${DIM}Unterstützt: macOS (OSX) und Linux (alle Distros)${NC}      ${CYAN}│${NC}\n"
printf "${CYAN}╰────────────────────────────────────────────────────────╯${NC}\n\n"

# 1. Betriebssystem prüfen
OS="$(uname -s)"
case "$OS" in
  Darwin*)  info "Betriebssystem erkannt: macOS (Apple Darwin)" ;;
  Linux*)   info "Betriebssystem erkannt: Linux" ;;
  *)        warn "Unbekanntes Betriebssystem: $OS (Installation wird versucht …)" ;;
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
  curl -LsSf https://astral.sh/uv/install.sh | sh || fail "uv liess sich nicht installieren (Internetverbindung prüfen)."
  UV="$HOME/.local/bin/uv"
fi

[ -x "$UV" ] || fail "uv ist nicht ausführbar: $UV"
say "uv ist bereit: $($UV --version)"

# 3. Pfad ~/.local/bin in PATH sicherstellen
export PATH="$HOME/.local/bin:$PATH"

# 4. sdc installieren
info "Installiere 'sdc' Werkzeug via uv tool …"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd || true)"

if [ -f "$SCRIPT_DIR/pyproject.toml" ]; then
  # Lokale Installation aus aktuellem Verzeichnis
  "$UV" tool install --force --editable "$SCRIPT_DIR" || "$UV" tool install --force "$SCRIPT_DIR"
else
  # Remote Installation aus Forgejo
  REPO_URL="ssh://git@git.schoeni-digital.com:2222/schoeni-digital/cli.git"
  "$UV" tool install --force "git+$REPO_URL" || {
    warn "SSH-Klonen fehlgeschlagen — versuche HTTPS …"
    "$UV" tool install --force "git+https://git.schoeni-digital.com/schoeni-digital/cli.git"
  }
fi

SDC="$(command -v sdc 2>/dev/null || true)"
[ -z "$SDC" ] && [ -x "$HOME/.local/bin/sdc" ] && SDC="$HOME/.local/bin/sdc"

if [ -z "$SDC" ]; then
  fail "'sdc' wurde installiert, liegt aber nicht in deinem PATH. Ergänze in deiner ~/.zshrc oder ~/.bashrc:\n  export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

say "sdc wurde erfolgreich installiert: $SDC"

# 5. Schlüssel-Prüfung (age & SSH)
info "Prüfe lokale Schlüssel auf diesem Gerät …"
"$SDC" device add --help >/dev/null 2>&1 || true

# 6. Systemdiagnose ausführen
printf "\n"
"$SDC" doctor || true

printf "\n${GREEN}╭────────────────────────────────────────────────────────╮${NC}\n"
printf "${GREEN}│${NC}  ${GREEN}✔ Bereit! Starte sdc jetzt mit:${NC}                       ${GREEN}│${NC}\n"
printf "${GREEN}│${NC}     ${CYAN}sdc${NC}                                                ${GREEN}│${NC}\n"
printf "${GREEN}│${NC}  ${DIM}Oder Notebook registrieren mit:${NC}                       ${GREEN}│${NC}\n"
printf "${GREEN}│${NC}     ${CYAN}sdc device add${NC}                                     ${GREEN}│${NC}\n"
printf "${GREEN}╰────────────────────────────────────────────────────────╯${NC}\n\n"
