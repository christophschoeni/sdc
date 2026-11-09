# SCHOENI DIGITAL CLI (`sdc`)

Das zentrale Steuer-, Onboarding- und Sicherheits-Werkzeug für Entwickler und Administratoren bei SCHOENI DIGITAL.

Ermöglicht das schnelle Einrichten neuer Arbeitsgeräte (Notebooks) unter **macOS**, **Linux** und **Windows**, die Verwaltung von Teammitgliedern und die sichere Verschlüsselung von Projekt-Secrets mit **SOPS + age**.

---

## ⚡ Schnelle 1-Zeiler-Installation

Führe den passenden Befehl auf deinem neuen Notebook oder Entwicklungsrechner aus:

### 🍏 macOS (OSX)
```bash
curl -fsSL https://git.schoeni-digital.com/schoeni-digital/cli/raw/branch/main/install.sh | bash
```
*(Alternativ aus dem geklonten Repo: `./install.sh`)*

### 🐧 Linux (Ubuntu, Debian, Fedora, Arch)
```bash
curl -fsSL https://git.schoeni-digital.com/schoeni-digital/cli/raw/branch/main/install.sh | bash
```

### 🪟 Windows (10 / 11 in PowerShell)
```powershell
irm https://git.schoeni-digital.com/schoeni-digital/cli/raw/branch/main/install.ps1 | iex
```

> **Hinweis:** Der Installer benötigt keine manuelle Python-Vorkonfiguration. Er nutzt Astral's schnellen Manager [`uv`](https://astral.sh/uv), der die benötigte Umgebung automatisch und isoliert bereitstellt.

---

## 🚀 Das Interaktive Startmenü

Wird `sdc` ohne Argumente im Terminal gestartet, öffnet sich automatisch das interaktive Dashboard mit Statusüberblick:

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

## 📖 Befehls-Referenz & Workflows

### 1. Neues Notebook / Gerät hinzufügen (`sdc device`)

Führt ein vollständiges Onboarding des aktuellen Rechners durch:
- Erkennt Rechnernamen und Betriebssystem automatisch.
- Prüft oder generiert den lokalen **age-Schlüssel** unter `~/.config/sops/age/keys.txt` (strikte Dateiberechtigung `600`).
- Prüft oder generiert den **ed25519 SSH-Schlüssel** unter `~/.ssh/id_ed25519.pub`.
- Verknüpft das Gerät mit dem Mitarbeiter in `config/team.yml`.
- **Secrets-Freischaltung:** Wird der Befehl in einer App ausgeführt (oder `--app <pfad>` übergeben), wird der Schlüssel direkt in `secrets/recipients.yml` eingetragen, `.sops.yaml` via `sdc secrets init` generiert und mit `sdc secrets rekey` verschlüsselt.

```bash
# Interaktiv mit geführten Fragen:
sdc device add

# Direkt mit Parametern:
sdc device add --member cschoeni --id cs_macbook

# In einem Projekt-Ordner (schaltet Secrets direkt frei):
cd ~/Projekte/SCHOENI-DIGITAL/internal/core_app
sdc device add --member cschoeni --id cs_macbook

# Alle registrierten Geräte anzeigen:
sdc device list
```

---

### 2. Mitarbeiter erfassen (`sdc member`)

Verwaltet Personen und deren Rollen im Team:

```bash
# Neuer Mitarbeiter (interaktiv oder mit Flags):
sdc member add --id mmueller --name "Max Müller" --role developer --email "max@schoeni.digital"

# Teamliste anzeigen:
sdc member list
```

**Verfügbare Rollen:**
- `owner`: Inhaber / Geschäftsleitung
- `developer`: Entwickler mit vollem Zugriff auf Entwicklungs-Secrets
- `ops`: Betrieb, Server- und Deployment-Infrastruktur
- `viewer`: Lesender Zugriff

---

### 3. Team- & Geräteübersicht (`sdc team`)

Gibt eine formatierte Tabelle aller Mitarbeiter mit Rollen, E-Mail-Adressen und zugewiesenen Geräten aus:

```bash
sdc team
```

---

### 4. Secrets mit SOPS + age (`sdc secrets`)

Regeln gemäss **Entscheid 0015** (Schlüsselverwahrung):
- Keine Klartext-Secrets im Git.
- Mindestens 2 Empfänger pro App (Arbeitsgerät + Offline-Recovery-Schlüssel).
- `.sops.yaml` wird immer aus `secrets/recipients.yml` generiert, nie von Hand editiert.

```bash
# Secrets für lokale Entwicklung entschlüsseln (.env erzeugen):
sdc secrets pull dev

# Prüfen, ob alle Empfänger und Pflicht-Secrets konfiguriert sind:
sdc secrets check

# .sops.yaml aus secrets/recipients.yml neu generieren:
sdc secrets init

# Verschlüsselte Dateien für neue Empfänger aktualisieren:
sdc secrets rekey

# Verschlüsselte Datei im Editor öffnen:
sdc secrets edit dev

# Einzelnen Secret-Wert sicher setzen:
sdc secrets set DATABASE_URL
```

---

### 5. Diagnose & Werkzeugprüfung (`sdc doctor`)

Prüft, ob alle benötigten Tools auf dem Arbeitsplatz installiert und einsatzbereit sind:

```bash
sdc doctor
```

Prüft unter anderem: `git`, `uv`, `node`, `podman`, `sops`, `age`, `tailscale`, `hcloud`, age-Schlüsselrechte und die Verzeichnisstruktur.

---

### 6. Neues Projekt aus Vorlage anlegen (`sdc new`)

Erstellt eine neue Anwendung nach den Standards von SCHOENI DIGITAL:

```bash
# Interne App:
sdc new core_app --internal

# Kundenprojekt:
sdc new webshop --customer kmu
```

---

## 🛠️ Entwicklung & Tests

Tests ausführen:
```bash
uv run --directory template/cli pytest
```

CLI lokal im Entwicklungs-Modus installieren:
```bash
uv tool install --force --editable template/cli
```
