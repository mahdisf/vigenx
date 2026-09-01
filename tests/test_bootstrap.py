from pathlib import Path

from scripts import bootstrap


def test_build_commands_use_selected_profile(tmp_path):
    commands = bootstrap.build_commands(
        Path("/repo"),
        tmp_path / ".venv",
        "core",
        bootstrap_python="python-test",
    )

    assert commands[0][:4] == ["python-test", "-m", "venv", str(tmp_path / ".venv")]
    assert commands[-1][-1] == str(Path("/repo") / "requirements-core.txt")


def test_dry_run_does_not_execute(monkeypatch, tmp_path, capsys):
    called = []
    monkeypatch.setattr(bootstrap.subprocess, "run", lambda *args, **kwargs: called.append(args))

    result = bootstrap.main(
        ["--profile", "dev", "--venv", str(tmp_path / "env"), "--dry-run"]
    )

    assert result == 0
    assert called == []
    output = capsys.readouterr().out
    assert "requirements-dev.txt" in output
