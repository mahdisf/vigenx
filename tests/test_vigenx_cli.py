import json

import engine.plan_cli
from vigenx import cli


def test_doctor_report_groups_capabilities(monkeypatch):
    monkeypatch.setattr(cli, "_module_available", lambda _name: True)
    monkeypatch.setattr(cli.shutil, "which", lambda name: f"/bin/{name}")

    report = cli.doctor_report()

    assert report["core_ready"] is True
    assert report["render_ready"] is True
    assert report["ai_ready"] is True
    assert report["full_ready"] is True
    assert {item["group"] for item in report["checks"]} == {"core", "render", "ai"}


def test_doctor_json_reports_missing_core(monkeypatch, capsys):
    monkeypatch.setattr(cli, "_module_available", lambda name: name != "flask")
    monkeypatch.setattr(cli.shutil, "which", lambda name: f"/bin/{name}")

    assert cli.main(["doctor", "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["core_ready"] is False
    assert next(item for item in payload["checks"] if item["name"] == "Flask")["ok"] is False


def test_doctor_strict_requires_ai_provider_sdks(monkeypatch, capsys):
    monkeypatch.setattr(cli, "_module_available", lambda name: name != "openai")
    monkeypatch.setattr(cli.shutil, "which", lambda name: f"/bin/{name}")

    assert cli.main(["doctor", "--strict", "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["core_ready"] is True
    assert payload["render_ready"] is True
    assert payload["ai_ready"] is False
    assert payload["full_ready"] is False


def test_plan_forwards_arguments(monkeypatch):
    captured = []
    monkeypatch.setattr(engine.plan_cli, "main", lambda argv: captured.extend(argv) or 0)

    assert cli.main(["plan", "Make three clips", "--mode", "local"]) == 0
    assert captured == ["Make three clips", "--mode", "local"]


def test_no_command_prints_help(capsys):
    assert cli.main([]) == 0
    assert "doctor" in capsys.readouterr().out
