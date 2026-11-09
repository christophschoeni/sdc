from pathlib import Path


def core_root() -> Path:
    """core/ is two levels above this package: core/template/cli/sdc."""
    return Path(__file__).resolve().parents[3]


def workspace_root() -> Path:
    """~/Projekte/SCHOENI-DIGITAL (parent of core/)."""
    return core_root().parent


def schema_path() -> Path:
    return core_root() / "template" / "schemas" / "schoeni.schema.json"


def template_root() -> Path:
    return core_root() / "template" / "schoeni_template"


def team_config_path() -> Path:
    return core_root() / "config" / "team.yml"

