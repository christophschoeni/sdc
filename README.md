# SCHOENI DIGITAL CLI (`sdc`)

Das zentrale Steuer-, Onboarding- und Sicherheits-Werkzeug für Entwickler und Administratoren bei **SCHÖNI DIGITAL**.

Ermöglicht das schnelle Einrichten neuer Arbeitsgeräte (Notebooks) unter **macOS**, **Linux** und **Windows**, die automatische Nachinstallation von Entwickler-Tools, Container-Engines (**Docker** oder Podman), **Orca** und **T3 Code** sowie die sichere Verwaltung von Secrets mit **SOPS + age**.

---

## 1-Zeiler-Installation

Führe den passenden Befehl auf deinem neuen Notebook oder Entwicklungsrechner aus:

### macOS (OSX) & Linux
```bash
curl -fsSL https://raw.githubusercontent.com/christophschoeni/sdc/main/install.sh | bash
```

### Windows (10 / 11 in PowerShell)
```powershell
irm https://raw.githubusercontent.com/christophschoeni/sdc/main/install.ps1 | iex
```

> **Automatische Laufzeit:** Der Installer benötigt keine manuelle Python-Vorkonfiguration. Er nutzt Astral's Manager [`uv`](https://astral.sh/uv), richtet die isolierte Umgebung für `sdc` ein und prüft direkt alle Werkzeuge.

---

## Container: Docker CLI vs. Podman

- **Docker-First:** Wenn `docker` (Docker CLI) auf Linux, macOS oder Windows installiert ist, ist das **vollkommen ausreichend**. `podman` wird in diesem Fall **nicht** benötigt und nicht installiert.
- **Podman:** Dient als schlanke, rootless Alternative, falls Docker auf einem System nicht vorhanden oder nicht erwünscht ist.
- `sdc doctor` erkennt beide Engines als vollwertige Container-Laufzeiten an.

---

## Den PC in Orca sichtbar machen & steuern

`sdc` bindet neue Arbeitsrechner nahtlos in die **Orca** Agenten-Plattform ein:

### 1. Auf dem neuen PC / Notebook:
Starte den Orca Runtime Server (gebunden an deine Tailscale- oder Netzwerk-IP):
```bash
sdc orca serve
```
Der Server läuft im Hintergrund und gibt den Verbindungsendpunkt und den Pairing-Code aus:
```text
[ok] Orca Server aktiv auf 100.100.123.12:6768
Kopplungscode: orca://pair?endpoint=100.100.123.12:6768&token=...
```

### 2. Auf dem Haupt-PC (z. B. MacBook):
Kopple den neuen Rechner direkt über das Menü oder per Befehl:
```bash
sdc orca connect <pairing-code>
```
Sobald gekoppelt, erscheint der PC in der Orca-Oberfläche unter deinen verfügbaren Hosts und kann für Agenten-Sessions, Terminals und Worktrees direkt ausgewählt werden!

---

## Das Interaktive Startmenü

Wird `sdc` ohne Argumente im Terminal gestartet, öffnet sich automatisch das interaktive Dashboard mit dem Firmenlogo:

```bash
sdc
```

```text
   ____ _____ _   _  ___  _   _ ___    ____ ___ ____ ___ _____ _   _     
  / ___/ ____| | | |/ _ \| \ | |_ _|  |  _ \_ _/ ___|_ _|_   _/ \ | |    
  \___ \ |   | |_| | | | |  \| || |   | | | | | |  _ | |  | |/ _ \| |    
   ___) | |__|  _  | |_| | |\  || |   | |_| | | |_| || |  | / ___ \ |___ 
  |____/ \_____| |_|\___/|_| \_|___|  |____/___\____|___| |_/_/   \_\_____|
SCHÖNI DIGITAL · Entwickler- & Administrations-Zentrale · v0.1.0
Benutzer: Christoph Schöni (cschoeni) · Gerät: 1 Gerät(e) registriert · Secrets: SOPS+age
──────────────────────────────────────────────────────────────────────────────

Aktion auswählen:
 ── GERÄTE & TEAM ──────────────────────────────────────
 › device    ›  Gerät registrieren (Notebook, age-Key, SSH, Secrets)
   member    ›  Mitarbeiter anlegen (Kürzel, Name, Rolle, E-Mail)
   team      ›  Team- und Geräte-Übersicht anzeigen
 ── ORCA & ENTWICKLER-TOOLS ────────────────────────────
   setup     ›  System-Setup (fehlende Tools, Orca, T3 Code nachinstallieren)
   orca      ›  Orca-Laufzeit (Status, Server starten, Remote-PC koppeln)
   update    ›  CLI & Entwickler-Tools auf den neuesten Stand bringen
 ── SECRETS & SICHERHEIT ───────────────────────────────
   secrets   ›  Secrets verwalten (pull, check, init, rekey, edit)
 ── PROJEKTE & VORLAGE ─────────────────────────────────
   new       ›  Neues Projekt anlegen (sdc new)
   check     ›  Projekt prüfen (schoeni.yaml validieren)
 ── SYSTEM & DIAGNOSE ──────────────────────────────────
   info      ›  System- und Umgebungs-Info (sdc info)
   doctor    ›  System- und Werkzeugdiagnose (sdc doctor)
 ──────────────────────────────────────────────────────
   exit      ›  Beenden
```

---

## Befehls-Übersicht

| Befehl | Zweck |
|---|---|
| `sdc` | Startet das interaktive Dashboard mit allen Funktionen |
| `sdc info` | Vollständige System-, Organisations- und Toolübersicht |
| `sdc update` | Aktualisiert die `sdc` CLI und Entwickler-Tools auf den neuesten Stand |
| `sdc doctor` | Umfassende Diagnose für Werkzeuge, Container, Orca, T3 Code, Netz und Schlüssel |
| `sdc setup` | Installiert fehlende Tools (`git`, `uv`, `node`, `docker`, `sops`, `age`, `t3-code`, `orca`) |
| `sdc orca serve` | Startet den Orca-Server auf diesem Rechner für Remote-Steuerung |
| `sdc orca connect` | Verbindet das Haupt-Orca mit einem Remote-PC via Pairing-Code |
| `sdc orca status` | Prüft Orca Runtime und bekannte Hosts |
| `sdc device add` | Neues Notebook erfassen: age- & SSH-Key erzeugen, für Secrets berechtigen |
| `sdc member add` | Neuen Mitarbeiter mit Name, Rolle und E-Mail erfassen |
| `sdc team` | Übersicht über alle Teammitglieder und deren registrierte Geräte |
| `sdc secrets pull` | Entschlüsselt Secrets aus SOPS und schreibt lokale `.env` |
| `sdc secrets rekey` | Verschlüsselt alle Projekt-Secrets für neu hinzugefügte Geräte neu |
| `sdc new <name>` | Neues SCHÖNI DIGITAL Projekt nach Vorlage erzeugen |
| `sdc check` | Projekt-Manifest `schoeni.yaml` gegen das Schema validieren |

---

## CLI Aktualisieren (`sdc update`)

Mit `sdc update` wird die CLI direkt aus dem zentralen Forgejo-Repository auf den neuesten Stand gebracht:

```bash
# sdc CLI aktualisieren
sdc update

# sdc CLI und Entwickler-Tools (uv, Homebrew) aktualisieren
sdc update --tools

# Nur prüfen, ob auf dem Server neuere Versionen vorliegen
sdc update --check
```

---

## Lizenz & Vertraulichkeit

(c) 2026 SCHÖNI DIGITAL. Alle Rechte vorbehalten. Nur für den internen Gebrauch.
