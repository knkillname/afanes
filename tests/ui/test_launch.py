"""Tests for the graphical entry point and its launch options."""

import builtins
import importlib
import importlib.util
import tomllib
from collections.abc import Mapping, Sequence
from pathlib import Path

import flet as ft
import pytest

import afanes.__main__
import afanes.core.settings
import afanes.core.vault.schema
import afanes.core.vault.service
import afanes.i18n.cli
import afanes.i18n.cli.en
from afanes.core.preferences import Preferences, PreferencesStore
from tests.support import access_readable, constant

USAGE_EXIT_CODE = 2
TEST_PORT = 8765
PROJECT_ROOT = Path(__file__).parents[2]
_ENGLISH_COPY = afanes.i18n.cli.CliCopy.english()


@pytest.fixture(autouse=True)
def _isolate_launch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LANG", "en_US.UTF-8")
    monkeypatch.delenv("LC_ALL", raising=False)
    monkeypatch.delenv("LC_MESSAGES", raising=False)
    _use_settings_file(monkeypatch, tmp_path / "launch-settings.json")


class TestConsoleEntryPoint:
    def test_console_script_targets_the_launch_function(self) -> None:
        scripts = _project_scripts()

        assert scripts["afanes"] == "afanes.__main__:entrypoint"

    def test_console_script_target_resolves_to_a_callable(self) -> None:
        target = _project_scripts()["afanes"]

        assert callable(_resolve_target(target))


class TestLaunchOptions:
    def test_defaults_to_the_desktop_presentation(self) -> None:
        options = afanes.__main__.LaunchOptions.parse([], _ENGLISH_COPY)

        assert options.web is False
        assert options.vault is None
        assert options.port == 0

    def test_web_option_selects_the_browser_presentation(self) -> None:
        options = afanes.__main__.LaunchOptions.parse(["--web"], _ENGLISH_COPY)

        assert options.web is True

    def test_port_option_is_read(self) -> None:
        options = afanes.__main__.LaunchOptions.parse(["--web", "--port", str(TEST_PORT)], _ENGLISH_COPY)

        assert options.port == TEST_PORT

    def test_vault_option_is_read(self, tmp_path: Path) -> None:
        options = afanes.__main__.LaunchOptions.parse(["--vault", str(tmp_path)], _ENGLISH_COPY)

        assert options.vault == tmp_path

    def test_unknown_option_is_a_usage_error(self) -> None:
        with pytest.raises(SystemExit) as excinfo:
            afanes.__main__.LaunchOptions.parse(["--unknown"], _ENGLISH_COPY)

        assert excinfo.value.code == USAGE_EXIT_CODE

    def test_out_of_range_port_is_a_usage_error(self) -> None:
        with pytest.raises(SystemExit) as excinfo:
            afanes.__main__.LaunchOptions.parse(["--port", "70000"], _ENGLISH_COPY)

        assert excinfo.value.code == USAGE_EXIT_CODE


class TestRuntimeGuards:
    def test_missing_desktop_runtime_exits_with_an_install_hint(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _block_runtime(monkeypatch, afanes.__main__.DESKTOP_RUNTIME_MODULE)
        calls = _record_run(monkeypatch)

        with pytest.raises(SystemExit) as excinfo:
            afanes.__main__.Launcher.main(*[])

        assert excinfo.value.code == 1
        assert "afanes[desktop]" in capsys.readouterr().err
        assert calls == []

    def test_missing_web_runtime_exits_with_an_install_hint(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _block_runtime(monkeypatch, afanes.__main__.WEB_RUNTIME_MODULE)
        calls = _record_run(monkeypatch)

        with pytest.raises(SystemExit) as excinfo:
            afanes.__main__.Launcher.main(*["--web"])

        assert excinfo.value.code == 1
        assert "afanes[web]" in capsys.readouterr().err
        assert calls == []

    def test_missing_sdk_reports_one_message(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _ = ft.run
        real_import = builtins.__import__

        def fake_import(
            name: str,
            globals_: Mapping[str, object] | None = None,
            locals_: Mapping[str, object] | None = None,
            fromlist: Sequence[str] | None = None,
            level: int = 0,
        ) -> object:
            if name == "flet" or name.startswith("flet."):
                message = f"No module named {name!r}"
                raise ModuleNotFoundError(message, name=name)
            return real_import(name, globals_, locals_, fromlist, level)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        _allow_runtime(monkeypatch, afanes.__main__.DESKTOP_RUNTIME_MODULE)
        calls = _record_run(monkeypatch)

        with pytest.raises(SystemExit) as excinfo:
            afanes.__main__.Launcher.main(*[])

        assert excinfo.value.code == 1
        assert afanes.i18n.cli.en.LAUNCH_MISSING_SDK in capsys.readouterr().err
        assert calls == []


class TestSpanishLaunch:
    def test_spanish_help_is_printed(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        PreferencesStore(tmp_path / "preferences.json").save(Preferences(language="es"))

        with pytest.raises(SystemExit) as excinfo:
            afanes.__main__.Launcher.main("--help")

        assert excinfo.value.code == 0
        output = capsys.readouterr().out
        assert "Abre Afanes" in output
        assert "Open Afanes" not in output

    def test_missing_runtime_is_reported_in_spanish(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        PreferencesStore(tmp_path / "preferences.json").save(Preferences(language="es"))
        _block_runtime(monkeypatch, afanes.__main__.DESKTOP_RUNTIME_MODULE)
        calls = _record_run(monkeypatch)

        with pytest.raises(SystemExit) as excinfo:
            afanes.__main__.Launcher.main(*[])

        assert excinfo.value.code == 1
        assert "El entorno de escritorio no está instalado" in capsys.readouterr().err
        assert calls == []


class TestLaunchDispatch:
    def test_desktop_launch_uses_the_default_view(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _allow_runtime(monkeypatch, afanes.__main__.DESKTOP_RUNTIME_MODULE)
        calls = _record_run(monkeypatch)

        afanes.__main__.Launcher.main(*[])

        assert len(calls) == 1
        assert calls[0][1] == {}

    def test_web_launch_binds_loopback_and_serves_local_assets(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _allow_runtime(monkeypatch, afanes.__main__.WEB_RUNTIME_MODULE)
        calls = _record_run(monkeypatch)

        afanes.__main__.Launcher.main(*["--web", "--port", str(TEST_PORT)])

        assert len(calls) == 1
        kwargs = calls[0][1]
        assert kwargs["view"] is ft.AppView.WEB_BROWSER
        assert kwargs["host"] == "127.0.0.1"
        assert kwargs["port"] == TEST_PORT
        assert kwargs["no_cdn"] is True

    def test_desktop_failure_names_the_web_presentation(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        def blocked(*_args: object, **_kwargs: object) -> None:
            message = "desktop client blocked"
            raise OSError(message)

        _allow_runtime(monkeypatch, afanes.__main__.DESKTOP_RUNTIME_MODULE)
        monkeypatch.setattr(ft, "run", blocked)

        with pytest.raises(SystemExit) as excinfo:
            afanes.__main__.Launcher.main(*[])

        assert excinfo.value.code == 1
        stderr = capsys.readouterr().err
        assert "desktop client blocked" in stderr
        assert "--web" in stderr

    def test_invalid_launch_vault_exits_before_starting(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        missing = tmp_path / "missing"
        _allow_runtime(monkeypatch, afanes.__main__.DESKTOP_RUNTIME_MODULE)
        calls = _record_run(monkeypatch)

        with pytest.raises(SystemExit) as excinfo:
            afanes.__main__.Launcher.main(*["--vault", str(missing)])

        assert excinfo.value.code == 1
        assert str(missing) in capsys.readouterr().err
        assert calls == []

    def test_an_unversioned_adoptable_launch_vault_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        vault = _adoptable(tmp_path / "vault")
        _allow_runtime(monkeypatch, afanes.__main__.DESKTOP_RUNTIME_MODULE)
        calls = _record_run(monkeypatch)

        with pytest.raises(SystemExit) as excinfo:
            afanes.__main__.Launcher.main(*["--vault", str(vault)])

        assert excinfo.value.code == 1
        assert "afanes.yaml" in capsys.readouterr().err
        assert calls == []
        assert not (vault / "afanes.yaml").exists()

    def test_an_unversioned_incompatible_launch_vault_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _allow_runtime(monkeypatch, afanes.__main__.DESKTOP_RUNTIME_MODULE)
        calls = _record_run(monkeypatch)

        with pytest.raises(SystemExit) as excinfo:
            afanes.__main__.Launcher.main(*["--vault", str(vault)])

        assert excinfo.value.code == 1
        assert "afanes.yaml" in capsys.readouterr().err
        assert calls == []
        assert list(vault.iterdir()) == []

    def test_an_invalid_launch_vault_schema_is_refused_and_preserved(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = vault / "afanes.yaml"
        path.write_text("schema_version: 1\nextra: true\n", encoding="utf-8")
        before = path.read_bytes()
        _allow_runtime(monkeypatch, afanes.__main__.DESKTOP_RUNTIME_MODULE)
        calls = _record_run(monkeypatch)

        with pytest.raises(SystemExit) as excinfo:
            afanes.__main__.Launcher.main(*["--vault", str(vault)])

        assert excinfo.value.code == 1
        assert "afanes.yaml" in capsys.readouterr().err
        assert calls == []
        assert path.read_bytes() == before

    def test_a_read_only_versioned_launch_vault_opens(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "afanes.yaml").write_text("schema_version: 1\n", encoding="utf-8")
        _allow_runtime(monkeypatch, afanes.__main__.DESKTOP_RUNTIME_MODULE)
        calls = _record_run(monkeypatch)
        monkeypatch.setattr(
            afanes.core.vault.service.os,
            "access",
            access_readable,
        )

        afanes.__main__.Launcher.main(*["--vault", str(vault)])

        assert len(calls) == 1


class TestSubcommandDispatch:
    def test_launch_options_are_not_subcommands(self, tmp_path: Path) -> None:
        assert afanes.__main__.Launcher.dispatch([]) is None
        assert afanes.__main__.Launcher.dispatch(["--web"]) is None
        assert afanes.__main__.Launcher.dispatch(["--vault", str(tmp_path / "vault")]) is None

    def test_subcommand_creates_a_vault_without_the_runtime_check(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")

        def unexpected(*_args: object, **_kwargs: object) -> None:
            message = "the runtime check must not run for a subcommand"
            raise AssertionError(message)

        monkeypatch.setattr(afanes.__main__.Launcher, "require_runtime", unexpected)
        target = tmp_path / "vault"

        status = afanes.__main__.Launcher.main("vault", "create", str(target))

        assert status == 0
        assert (target / "inbox").is_dir()
        assert "Created vault" in capsys.readouterr().out


def _use_settings_file(monkeypatch: pytest.MonkeyPatch, path: Path) -> None:
    monkeypatch.setattr(afanes.core.settings.SettingsStore, "settings_path", classmethod(constant(path)))


def _adoptable(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for folder in afanes.core.vault.schema.DEFAULT_FOLDERS:
        (root / folder).mkdir()
    return root


def _project_scripts() -> dict[str, str]:
    document = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    scripts = document["project"]["scripts"]
    return {name: str(target) for name, target in scripts.items()}


def _resolve_target(target: str) -> object:
    module_name, _, attribute = target.partition(":")
    return getattr(importlib.import_module(module_name), attribute)


def _block_runtime(monkeypatch: pytest.MonkeyPatch, blocked: str) -> None:
    real_find_spec = importlib.util.find_spec

    def find_spec(name: str, package: str | None = None) -> object:
        if name == blocked:
            return None
        return real_find_spec(name, package)

    monkeypatch.setattr(importlib.util, "find_spec", find_spec)


def _allow_runtime(monkeypatch: pytest.MonkeyPatch, allowed: str) -> None:
    real_find_spec = importlib.util.find_spec

    def find_spec(name: str, package: str | None = None) -> object:
        if name == allowed:
            return object()
        return real_find_spec(name, package)

    monkeypatch.setattr(importlib.util, "find_spec", find_spec)


def _record_run(monkeypatch: pytest.MonkeyPatch) -> list[tuple[tuple[object, ...], dict[str, object]]]:
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def record(*args: object, **kwargs: object) -> None:
        calls.append((args, kwargs))

    monkeypatch.setattr(ft, "run", record)
    return calls
