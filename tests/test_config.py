"""Tests for speedlog.config (NST-102): constants and platform-aware path helpers."""

from pathlib import Path

import pytest

from speedlog import config


class TestConstants:
    def test_values(self) -> None:
        assert config.SAMPLE_INTERVAL == 1.0
        assert config.SMOOTH_WINDOW == 5
        assert config.BAND_TOLERANCE_PCT == 0.10
        assert config.BAND_TOLERANCE_FLOOR_BPS == 250_000
        assert config.HYSTERESIS_TICKS == 5
        assert config.MIN_SEGMENT_SECS == 5
        assert config.PAGE_SIZE == 20
        assert config.ACCENT_COLOR == "#2E7CF6"
        assert config.APP_NAME == "Speedlog"


@pytest.fixture
def fake_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    monkeypatch.delenv("APPDATA", raising=False)
    return home


def _set_platform(monkeypatch: pytest.MonkeyPatch, system: str) -> None:
    monkeypatch.setattr(config.platform, "system", lambda: system)


class TestDataDir:
    def test_macos(self, fake_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_platform(monkeypatch, "Darwin")
        assert config.data_dir() == fake_home / "Library" / "Application Support" / "Speedlog"

    def test_linux_default(self, fake_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_platform(monkeypatch, "Linux")
        assert config.data_dir() == fake_home / ".local" / "share" / "Speedlog"

    def test_linux_xdg_override(
        self, fake_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_platform(monkeypatch, "Linux")
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg-data"))
        assert config.data_dir() == tmp_path / "xdg-data" / "Speedlog"

    def test_windows_appdata(
        self, fake_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_platform(monkeypatch, "Windows")
        monkeypatch.setenv("APPDATA", str(tmp_path / "AppData" / "Roaming"))
        assert config.data_dir() == tmp_path / "AppData" / "Roaming" / "Speedlog"

    def test_windows_appdata_missing_falls_back_to_home(
        self, fake_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_platform(monkeypatch, "Windows")
        assert config.data_dir() == fake_home / "AppData" / "Roaming" / "Speedlog"

    def test_creates_directory_if_missing(
        self, fake_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_platform(monkeypatch, "Darwin")
        path = config.data_dir()
        assert path.is_dir()

    def test_idempotent_when_directory_exists(
        self, fake_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_platform(monkeypatch, "Darwin")
        assert config.data_dir() == config.data_dir()


class TestDbPath:
    def test_inside_data_dir(self, fake_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_platform(monkeypatch, "Darwin")
        assert config.db_path() == config.data_dir() / "data.db"


class TestLogDir:
    def test_macos(self, fake_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_platform(monkeypatch, "Darwin")
        assert config.log_dir() == fake_home / "Library" / "Logs" / "Speedlog"

    def test_linux_default(self, fake_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_platform(monkeypatch, "Linux")
        assert config.log_dir() == fake_home / ".local" / "state" / "Speedlog" / "logs"

    def test_linux_xdg_override(
        self, fake_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_platform(monkeypatch, "Linux")
        monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "xdg-state"))
        assert config.log_dir() == tmp_path / "xdg-state" / "Speedlog" / "logs"

    def test_windows_under_data_dir(self, fake_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_platform(monkeypatch, "Windows")
        assert config.log_dir() == config.data_dir() / "logs"

    def test_creates_directory_if_missing(
        self, fake_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_platform(monkeypatch, "Darwin")
        assert config.log_dir().is_dir()
