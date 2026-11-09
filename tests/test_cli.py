from pathlib import Path

from sdc.commands.check import validate
from sdc.commands.new import build_manifest
from sdc.main import main
from sdc.paths import template_root


def test_template_manifest_is_valid():
    import yaml
    m = yaml.safe_load((template_root() / "schoeni.yaml").read_text())
    assert validate(m) == []


def test_customer_requires_customer_field():
    m = build_manifest("shop", "customer", "acme", "coolify", "cs")
    assert m["customer"] == "acme" and m["project"] == "acme_shop"
    del m["customer"]
    assert any("customer" in e for e in validate(m))


def test_production_requires_slo():
    m = build_manifest("core_app", "internal", None, "coolify", "cs")
    m["stage"] = "production"
    del m["slo"]
    assert any("slo" in e for e in validate(m))


def test_check_command_on_template(capsys):
    assert main(["check", str(template_root())]) == 0
    assert "gültig" in capsys.readouterr().out


def test_new_dry_run(capsys):
    assert main(["new", "probe", "--kind", "internal", "--dry-run"]) == 0
    assert "würde anlegen" in capsys.readouterr().out
