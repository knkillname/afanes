"""Tests for vault page capture, creation, writing, recovery, and status."""

import datetime
import os
from pathlib import Path

import pytest

import afanes.core.atomic
import afanes.core.vault.naming
import afanes.core.vault.pages
import afanes.core.vault.processing
import afanes.core.vault.service
import afanes.core.vault.steps
from afanes.core.errors import (
    VaultError,
)
from afanes.core.frontmatter import NoteDocument
from afanes.models.note import NoteType

ONE = 1
TWO = 2
THREE_REFERENCES = 3


def _write_note(
    path: Path,
    note_type: str = "note",
    body: str = "",
    *,
    category: str | None = None,
    status: str | None = None,
    due_date: str | None = None,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if note_type == "person":
        note_type = "reference"
        category = "person"
    lines = ["---", f"type: {note_type}"]
    if category is not None:
        lines.append(f"category: {category}")
    if status is not None:
        lines.append(f"status: {status}")
    if due_date is not None:
        lines.append(f"due_date: {due_date}")
    lines.extend(["---", "", body])
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return path


def _tree_state(root: Path) -> dict[str, bytes]:
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def _set_modified_ns(path: Path, modified_ns: int) -> None:
    os.utime(path, ns=(modified_ns, modified_ns))


class TestStepWrites:
    def _project(self, tmp_path: Path) -> tuple[afanes.core.vault.service.Vault, Path]:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.service.Vault(root)
        project = vault.create(
            afanes.core.vault.service.NoteDraft("Home", NoteType.PROJECT, body="# Home\n\n- [ ] One\n- [ ] Two\n")
        )
        return vault, project

    def test_tick_and_untick_rewrite_one_line(self, tmp_path: Path) -> None:
        vault, project = self._project(tmp_path)
        document = NoteDocument.from_text(project.read_text(encoding="utf-8"))
        steps = afanes.core.steps.StepDocument(document.body).steps

        afanes.core.vault.steps.VaultSteps(vault).tick_step(
            project, steps[0].line_index, datetime.date(2026, 11, 14), confirm=True
        )
        ticked = NoteDocument.from_text(project.read_text(encoding="utf-8"))

        assert "- [x] One" in ticked.body
        assert "- [ ] Two" in ticked.body
        assert "actual: 2026-11-14" in ticked.body

        afanes.core.vault.steps.VaultSteps(vault).untick_step(project, steps[0].line_index, confirm=True)
        unticked = NoteDocument.from_text(project.read_text(encoding="utf-8"))
        assert "- [ ] One" in unticked.body
        assert "actual" not in unticked.body

    def test_plan_and_owners_rewrite_one_line(self, tmp_path: Path) -> None:
        vault, project = self._project(tmp_path)
        document = NoteDocument.from_text(project.read_text(encoding="utf-8"))
        index = afanes.core.steps.StepDocument(document.body).steps[0].line_index

        afanes.core.vault.steps.VaultSteps(vault).plan_step(project, index, datetime.date(2026, 12, 1), confirm=True)
        afanes.core.vault.steps.VaultSteps(vault).set_step_owners(project, index, ("Ada",), confirm=True)
        written = NoteDocument.from_text(project.read_text(encoding="utf-8"))

        assert "plan: 2026-12-01" in written.body
        assert "owners: [Ada]" in written.body

    def test_frontmatter_bytes_survive_a_step_edit(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.service.Vault(root)
        project = root / "projects" / "Home.md"
        project.parent.mkdir()
        prefix = "---\ntype: project   # keep this alignment\nstatus: active\n---\n"
        project.write_text(f"{prefix}# Home\n\n- [ ] One\n", encoding="utf-8", newline="\n")
        index = afanes.core.steps.StepDocument("# Home\n\n- [ ] One\n").steps[0].line_index

        afanes.core.vault.steps.VaultSteps(vault).plan_step(project, index, datetime.date(2026, 12, 1), confirm=True)

        written = project.read_text(encoding="utf-8")
        assert written.startswith(prefix)
        assert "plan: 2026-12-01" in written

    def test_step_writes_require_confirmation_and_a_project(self, tmp_path: Path) -> None:
        vault, project = self._project(tmp_path)
        reference = vault.create(afanes.core.vault.service.NoteDraft("Ref", NoteType.REFERENCE))
        index = 2

        with pytest.raises(VaultError):
            afanes.core.vault.steps.VaultSteps(vault).tick_step(project, index, datetime.date(2026, 11, 14))
        with pytest.raises(VaultError):
            afanes.core.vault.steps.VaultSteps(vault).tick_step(
                reference, index, datetime.date(2026, 11, 14), confirm=True
            )
        with pytest.raises(VaultError):
            afanes.core.vault.steps.VaultSteps(vault).tick_step(project, 99, datetime.date(2026, 11, 14), confirm=True)

    def test_append_step_requires_confirmation_and_a_project(self, tmp_path: Path) -> None:
        vault, project = self._project(tmp_path)
        reference = vault.create(afanes.core.vault.service.NoteDraft("Ref", NoteType.REFERENCE))

        with pytest.raises(VaultError):
            afanes.core.vault.steps.VaultSteps(vault).append_step(project, "Three")
        with pytest.raises(VaultError):
            afanes.core.vault.steps.VaultSteps(vault).append_step(reference, "Three", confirm=True)

        afanes.core.vault.steps.VaultSteps(vault).append_step(project, "Three", "Detail", confirm=True)
        assert "- [ ] Three" in project.read_text(encoding="utf-8")
