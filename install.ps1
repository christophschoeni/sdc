# SCHOENI DIGITAL CLI (`sdc`) — Vollständiger All-in-One Installer für Windows
#
# Schnelle 1-Zeiler-Installation in PowerShell:
#   irm https://git.schoeni-digital.com/schoeni-digital/cli/raw/branch/main/install.ps1 | iex
#
$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "╭────────────────────────────────────────────────────────╮" -ForegroundColor Cyan
Write-Host "│  ◆ SCHOENI DIGITAL · Arbeitsplatz & sdc Setup          │" -ForegroundColor Cyan
Write-Host "│  Entwickler-Tools · Docker · Orca · T3 Code            │" -ForegroundColor Gray
Write-Host "│  Plattform: Microsoft Windows (PowerShell)             │" -ForegroundColor Gray
Write-Host "╰────────────────────────────────────────────────────────╯" -ForegroundColor Cyan
Write-Host ""

# 1. uv prüfen oder installieren
Write-Host "ℹ Prüfe Python-Paketmanager uv …" -ForegroundColor Cyan
$uv = Get-Command uv -ErrorAction SilentlyContinue

if (-not $uv) {
    $uvLocal = Join-Path $HOME ".local\bin\uv.exe"
    $uvCargo = Join-Path $HOME ".cargo\bin\uv.exe"
    if (Test-Path $uvLocal) {
        $uv = $uvLocal
    } elseif (Test-Path $uvCargo) {
        $uv = $uvCargo
    } else {
        Write-Host "ℹ Installiere uv von https://astral.sh/uv …" -ForegroundColor Cyan
        try {
            irm https://astral.sh/uv/install.ps1 | iex
            $uv = Join-Path $HOME ".local\bin\uv.exe"
        } catch {
            Write-Error "[fehler] uv liess sich nicht installieren: $_"
            exit 1
        }
    }
}
Write-Host "[ok] uv ist bereit: & $uv --version" -ForegroundColor Green

# 2. PATH aktualisieren
$localBin = Join-Path $HOME ".local\bin"
if ($env:Path -notlike "*$localBin*") {
    $env:Path = "$localBin;" + $env:Path
    [Environment]::SetEnvironmentVariable("Path", $env:Path, [EnvironmentVariableTarget]::User)
}

# 3. sdc installieren
Write-Host "[info] Installiere 'sdc' via uv tool …" -ForegroundColor Cyan
$scriptDir = $PSScriptRoot

if ($scriptDir -and (Test-Path (Join-Path $scriptDir "pyproject.toml"))) {
    & $uv tool install --force --editable $scriptDir
} else {
    $repoUrl = "ssh://git@git.schoeni-digital.com:2222/schoeni-digital/cli.git"
    try {
        & $uv tool install --force "git+$repoUrl"
    } catch {
        Write-Host "[warn] SSH fehlgeschlagen, versuche HTTPS …" -ForegroundColor Yellow
        & $uv tool install --force "git+https://git.schoeni-digital.com/schoeni-digital/cli.git"
    }
}

$sdc = Get-Command sdc -ErrorAction SilentlyContinue
if (-not $sdc) {
    $sdcPath = Join-Path $localBin "sdc.exe"
    if (Test-Path $sdcPath) {
        $sdc = $sdcPath
    }
}

if (-not $sdc) {
    Write-Warning "[warn] 'sdc' liegt in $localBin, bitte neues PowerShell-Fenster öffnen falls der Befehl noch nicht erkannt wird."
} else {
    Write-Host "[ok] sdc erfolgreich installiert!" -ForegroundColor Green
}

# 4. Container-Prüfung (Docker Desktop vor Podman)
Write-Host "[info] Prüfe Container-Laufzeit …" -ForegroundColor Cyan
$docker = Get-Command docker -ErrorAction SilentlyContinue
$podman = Get-Command podman -ErrorAction SilentlyContinue

if ($docker) {
    Write-Host "[ok] Docker CLI ist vorhanden (vollkommen ausreichend)." -ForegroundColor Green
} elseif ($podman) {
    Write-Host "[ok] Podman ist vorhanden." -ForegroundColor Green
} else {
    Write-Host "[warn] Keine Container-Laufzeit gefunden. Docker Desktop wird empfohlen: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
}

# 5. T3 Code & Orca
Write-Host "[info] Prüfe T3 Code und Orca …" -ForegroundColor Cyan
$t3 = Get-Command t3 -ErrorAction SilentlyContinue
if (-not $t3) {
    Write-Host "[info] T3 Code für Windows: https://t3.codes/" -ForegroundColor Cyan
} else {
    Write-Host "[ok] T3 Code ist vorhanden." -ForegroundColor Green
}

$orca = Get-Command orca -ErrorAction SilentlyContinue
if (-not $orca) {
    Write-Host "[info] Orca für Windows: https://www.onorca.dev/download" -ForegroundColor Cyan
} else {
    Write-Host "[ok] Orca ist vorhanden." -ForegroundColor Green
}

# 6. Diagnose ausführen
if ($sdc) {
    Write-Host ""
    try {
        & $sdc doctor
    } catch {
        # ignore error in doctor during first install
    }
}

Write-Host ""
Write-Host "╭────────────────────────────────────────────────────────╮" -ForegroundColor Green
Write-Host "│  [ok] Bereit! Starte sdc jetzt mit:                    │" -ForegroundColor Green
Write-Host "│     sdc                                                │" -ForegroundColor Cyan
Write-Host "│                                                        │" -ForegroundColor Green
Write-Host "│  Notebook registrieren mit:                            │" -ForegroundColor Gray
Write-Host "│     sdc device add                                     │" -ForegroundColor Cyan
Write-Host "│                                                        │" -ForegroundColor Green
Write-Host "│  Diesen PC in Orca sichtbar machen mit:                │" -ForegroundColor Gray
Write-Host "│     sdc orca serve                                     │" -ForegroundColor Cyan
Write-Host "╰────────────────────────────────────────────────────────╯" -ForegroundColor Green
Write-Host ""
