# SCHOENI DIGITAL CLI (`sdc`)

Das zentrale Steuer-, Onboarding- und Sicherheits-Werkzeug für Entwickler und Administratoren bei SCHOENI DIGITAL.

Ermöglicht das schnelle Einrichten neuer Arbeitsgeräte (Notebooks) unter **macOS**, **Linux** und **Windows**, die automatische Nachinstallation von Entwickler-Tools, Container-Engines (**Docker** oder Podman), **Orca** und **T3 Code** sowie die sichere Verwaltung von Secrets mit **SOPS + age**.

---

## ⚡ Schnelle 1-Zeiler-Installation

Führe den passenden Befehl auf deinem neuen Notebook oder Entwicklungsrechner aus:

### 🍏 macOS (OSX)
```bash
curl -fsSL https://git.schoeni-digital.com/schoeni-digital/cli/raw/branch/main/install.sh | bash
```

### 🐧 Linux (Ubuntu, Debian, Fedora, Arch)
```bash
curl -fsSL https://git.schoeni-digital.com/schoeni-digital/cli/raw/branch/main/install.sh | bash
```

### 🪟 Windows (10 / 11 in PowerShell)
```powershell
irm https://git.schoeni-digital.com/schoeni-digital/cli/raw/branch/main/install.ps1 | iex
```

> **Automatische Laufzeit:** Der Installer benötigt keine manuelle Python-Vorkonfiguration. Er nutzt Astral's ultraschnellen Manager [`uv`](https://astral.sh/uv), richtet die isolierte Umgebung für `sdc` ein und prüft direkt alle Werkzeuge.

---

## 🐳 Container: Docker CLI vs. Podman

- **Docker-First:** Wenn `docker` (Docker CLI) auf Linux, macOS oder Windows installiert ist, ist das **vollkommen ausreichend**. `podman` wird in diesem Fall **nicht** benötigt und nicht installiert.
- **Podman:** Dient als schlanke, rootless Alternative, falls Docker auf einem System nicht vorhanden oder nicht erwünscht ist.
- `sdc doctor` erkennt beide Engines als vollwertige Container-Laufzeiten an.

---

## 🌐 Den PC in Orca sichtbar machen & steuern

`sdc` bindet neue Arbeitsrechner nahtlos in die **Orca** Agenten-Plattform ein:

### Auf dem neuen PC / Notebook:
Starte den Orca Runtime Server (gebunden an deine Tailscale- oder Netzwerk-IP):
```bash
sdc orca serve
```
Der Server läuft im Hintergrund und gibt den Verbindungsendpunkt und den Pairing-Code aus:
```text
✔ Orca Runtime aktiv auf 100.64.1.25:6768
Kopplungscode: orca://pair?endpoint=...
```

### Auf dem Haupt-PC (z. B. MacBook):
Kopple den neuen Rechner direkt über das Menü oder per Befehl:
```bash
sdc orca connect <pairing-code>
```
Sobald gekoppelt, erscheint der PC in der Orca-Oberfläche unter deinen verfügbaren Hosts und kann für Agenten-Sessions, Terminals und Worktrees direkt ausgewählt werden!

---

## 🚀 Das Interaktive Startmenü

Wird `sdc` ohne Argumente im Terminal gestartet, öffnet sich automatisch das interaktive Dashboard:

```bash
sdc
```

```text
╭──────────────────────────────────────────────────────────────────────────────╮
│  ◆ SCHOENI DIGITAL · Developer & Admin CLI v0.1.0                            │
│    👤 Christoph Schöni (cschoeni)  ·  💻 1 Gerät(e) registriert  ·  🔒 SOPS+age
╰──────────────────────────────────────────────────────────────────────────────╯

? Was möchtest du tun? (Pfeiltasten, Enter zum Bestätigen)
 ── GERÄTE & TEAM ─────────────────────────
 ❯ 💻 Notebook / Gerät hinzufügen (Age-Key, SSH, Secrets)
   👤 Mitarbeiter hinzufügen (Kürzel, Name, Rolle)
   👥 Team & Geräte anzeigen (Gesamtsicht)
 ── ORCA & ENTWICKLER-TOOLS ──────────────
   ⚡ System-Setup (fehlende Tools, Orca, T3 Code installieren)
   🌐 Orca verwalten (Status, Server starten, koppeln)
 ── SECRETS & SICHERHEIT ─────────────────
   🔐 Secrets verwalten (pull, check, init, rekey)
 ── PROJEKTE & VORLAGE ───────────────────
   ✨ Neues Projekt anlegen (sdc new)
   🔍 Projekt prüfen (schoeni.yaml validieren)
 ── DIAGNOSE ─────────────────────────────
   🩺 System & Werkzeuge prüfen (sdc doctor)
 ─────────────────────────────────────────
   🚪 Beenden
```

---

## 🛠️ Befehls-Übersicht

| Befehl | Zweck |
|---|---|
| `sdc` | Startet das interaktive Dashboard mit allen Funktionen |
| `sdc setup` | Installiert fehlende Tools (`git`, `uv`, `node`, `docker`, `sops`, `age`, `t3-code`, `orca`) |
| `sdc orca serve` | Startet den Orca-Server auf diesem Rechner für Remote-Steuerung |
| `sdc orca connect` | Verbindet das Haupt-Orca mit einem Remote-PC via Pairing-Code |
| `sdc orca status` | Prüft Orca Runtime und bekannte Hosts |
| `sdc device add` | Neues Notebook erfassen: age- & SSH-Key erzeugen, für Secrets berechtigen |
| `sdc member add` | Neuen Mitarbeiter mit Name, Rolle und E-Mail erfassen |
| `sdc team` | Übersicht über alle Teammitglieder und deren registrierte Geräte |
| `sdc secrets pull` | Entschlüsselt Secrets aus SOPS und schreibt lokale `.env` |
| `sdc secrets rekey` | Verschlüsselt alle Projekt-Secrets für neu hinzugefügte Geräte neu |
| `sdc doctor` | Umfassende System- und Werkzeugdiagnose |

---

## 🧪 Tests

```bash
uv run --directory template/cli pytest
```
12 automatisierte Tests stellen sicher, dass alle Workflows zuverlässig funktionieren.
