"""Tests that the scan benchmark generator writes a valid vault."""

import importlib.util
import sys
import types
from pathlib import Path

import afanes.core.vault.service

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "scan_benchmark.py"
FIFTY_NOTES = 50
TWENTY_REFERENCES = 20


def _load_script() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("scan_benchmark", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class TestScanBenchmarkGenerator:
    def test_generated_vault_scans_without_failures(self, tmp_path: Path) -> None:
        benchmark = _load_script()
        root = tmp_path / "vault"

        generated = benchmark.generate_vault(root, notes=FIFTY_NOTES)
        snapshot = afanes.core.vault.service.Vault.open(root).scan()

        assert generated.total == FIFTY_NOTES
        assert generated.references == TWENTY_REFERENCES
        assert len(snapshot.notes) == FIFTY_NOTES
        assert snapshot.failures == ()

    def test_generated_tree_contains_the_expected_kinds(self, tmp_path: Path) -> None:
        benchmark = _load_script()
        root = tmp_path / "vault"

        generated = benchmark.generate_vault(root, notes=FIFTY_NOTES)

        assert len(list((root / "inbox").glob("*.md"))) == generated.captures
        assert len(list((root / "reference").rglob("*.md"))) == generated.references
        assert len(list((root / "projects").glob("*.md"))) == generated.projects
