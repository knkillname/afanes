"""Packaging test for the bundled gettext catalogs."""

import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
LOCALES_ROOT = REPO_ROOT / "src" / "afanes" / "i18n" / "locales"


@pytest.fixture(scope="module")
def wheel(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    environment = dict(os.environ)
    environment["HATCH_ENV"] = "default"
    environment.pop("HATCH_ENV_TYPE", None)
    hatch = shutil.which("hatch")
    assert hatch is not None, "hatch is not available on PATH"
    result = subprocess.run(  # noqa: S603
        [hatch, "build", "-t", "wheel", "-c"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    assert result.returncode == 0, result.stderr
    artifacts = sorted((REPO_ROOT / "dist").glob("afanes-*.whl"))
    assert artifacts, "hatch build did not produce a wheel"
    wheel_path = artifacts[-1]
    extract_root = tmp_path_factory.mktemp("wheel")
    with zipfile.ZipFile(wheel_path) as archive:
        archive.extractall(extract_root)
    return wheel_path, extract_root


class TestBundledCatalogs:
    def test_the_wheel_contains_every_catalog_source_and_compiled_file(self, wheel: tuple[Path, Path]) -> None:
        wheel_path, _extract_root = wheel
        sources = {path.relative_to(LOCALES_ROOT).as_posix() for path in LOCALES_ROOT.rglob("*.po")}
        expected = sources | {Path(source).with_suffix(".mo").as_posix() for source in sources}

        with zipfile.ZipFile(wheel_path) as archive:
            names = {
                Path(name).relative_to("afanes/i18n/locales").as_posix()
                for name in archive.namelist()
                if name.startswith("afanes/i18n/locales/") and Path(name).suffix in {".po", ".mo"}
            }

        assert names == expected

    def test_the_wheel_contains_the_spanish_starter_content(self, wheel: tuple[Path, Path]) -> None:
        wheel_path, _extract_root = wheel
        expected = {
            "afanes/templates/_guide/es/reference/Primeros pasos.md",
            "afanes/templates/personal/es/projects/Revisión del coche.md",
            "afanes/template_cards/es/person.md",
            "afanes/template_cards/en/person.md",
        }

        with zipfile.ZipFile(wheel_path) as archive:
            names = set(archive.namelist())

        assert expected <= names

    def test_the_installed_package_loads_every_domain_without_the_source_tree(
        self,
        wheel: tuple[Path, Path],
        tmp_path: Path,
    ) -> None:
        _wheel_path, extract_root = wheel
        run_root = tmp_path / "run"
        run_root.mkdir()
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(extract_root)
        code = (
            "import afanes.core.errors\n"
            "import afanes.core.localization\n"
            "import afanes.i18n.cli\n"
            "import afanes.i18n.messages\n"
            "import afanes.i18n.ui\n"
            "es = afanes.core.localization.LocaleTag.parse('es')\n"
            "assert afanes.i18n.ui.UiCopy.for_locale(es).WELCOME_TITLE == 'Bienvenido a Afanes'\n"
            "assert afanes.i18n.cli.CliCopy.for_locale(es).CREATED_VAULT.startswith('Bóveda')\n"
            "message = afanes.core.errors.DomainMessage.of(\n"
            "    afanes.core.errors.MessageCode.SETTINGS_VERSION_UNSUPPORTED,\n"
            "    source='settings.json',\n"
            ")\n"
            "rendered = afanes.i18n.messages.MessageCatalog.for_locale(es).render(message)\n"
            "assert 'no admitida' in rendered\n"
            "print('ok')\n"
        )

        result = subprocess.run(  # noqa: S603
            [sys.executable, "-c", code],
            cwd=run_root,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )

        assert result.stdout.strip() == "ok"
