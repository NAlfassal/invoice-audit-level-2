"""DATA_DIR / TEMPLATE_PATH resolution and the missing-input error."""

from pathlib import Path

import pytest

from audit import config


def test_default_paths_exist() -> None:
    paths = config.input_paths()
    assert paths.civil_applications.name == "applications.csv"
    assert paths.drilling_records_dir.is_dir()


def test_missing_data_dir_is_a_clear_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "nowhere"))
    with pytest.raises(config.ConfigError) as err:
        config.input_paths()
    message = str(err.value)
    assert "civil_applications" in message and "DATA_DIR" in message


def test_missing_template_is_reported(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("TEMPLATE_PATH", str(tmp_path / "template.csv"))
    with pytest.raises(config.ConfigError, match="template"):
        config.input_paths()


def test_cli_exits_2_on_missing_data(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from audit.cli import main

    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    assert main(["audit"]) == 2
    assert "Input data not found" in capsys.readouterr().err
