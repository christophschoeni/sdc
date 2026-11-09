import os
from pathlib import Path


def workspace_root() -> Path:
    """Ermittelt das SCHOENI DIGITAL Workspace-Wurzelverzeichnis (~/Projekte/SCHOENI_DIGITAL bzw. SCHOENI-DIGITAL)."""
    # 1. Explizit gesetzte Umgebungsvariable
    env_ws = os.environ.get("SCHOENI_WORKSPACE")
    if env_ws:
        p = Path(env_ws).expanduser().resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    home_projekte = Path.home() / "Projekte"

    # 2. SCHOENI_DIGITAL oder SCHOENI-DIGITAL unter ~/Projekte
    for candidate_name in ("SCHOENI_DIGITAL", "SCHOENI-DIGITAL"):
        candidate = home_projekte / candidate_name
        if candidate.exists():
            return candidate

    # 3. Relative Ermittlung aus Paketstruktur falls im Workspace
    pkg_parents = Path(__file__).resolve().parents
    if len(pkg_parents) >= 4 and (pkg_parents[3] / "core").exists():
        return pkg_parents[3]

    # 4. Standardmässig ~/Projekte/SCHOENI-DIGITAL anlegen & Symlink SCHOENI_DIGITAL bereitstellen
    target = home_projekte / "SCHOENI-DIGITAL"
    target.mkdir(parents=True, exist_ok=True)
    symlink_target = home_projekte / "SCHOENI_DIGITAL"
    if not symlink_target.exists():
        try:
            symlink_target.symlink_to("SCHOENI-DIGITAL")
        except OSError:
            pass
    return target


def core_root() -> Path:
    """Pfad zum core-Repository (relativ zum Workspace oder zum Paket)."""
    # 1. Lokale Paketstruktur (falls Entwicklungs-Workspace)
    candidate = Path(__file__).resolve().parents[3]
    if (candidate / "template" / "schemas" / "schoeni.schema.json").exists():
        return candidate

    # 2. Im definierten Workspace
    ws_core = workspace_root() / "core"
    if (ws_core / "template" / "schemas" / "schoeni.schema.json").exists():
        return ws_core

    return candidate


def schema_path() -> Path:
    return core_root() / "template" / "schemas" / "schoeni.schema.json"


def template_root() -> Path:
    return core_root() / "template" / "schoeni_template"


def team_config_path() -> Path:
    return core_root() / "config" / "team.yml"

