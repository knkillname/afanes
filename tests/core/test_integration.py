"""End-to-end test for creation, linking, moving, and renaming notes."""

from pathlib import Path

import afanes.core.vault
from afanes.core.links import ResolutionOutcome
from afanes.models.link import NoteReference, ReferenceScheme
from afanes.models.note import NoteType

ONE_REFERENCE = 1


class TestReferenceLifecycle:
    def test_link_survives_a_move_and_follows_a_rename(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        ada = afanes.core.vault.create_note(root, "Ada Lovelace", NoteType.PERSON, directory=Path("people"))
        note = afanes.core.vault.create_note(
            root,
            "Prepare report",
            NoteType.NOTE,
            directory=Path("inbox"),
            body="Ask [Ada Lovelace](<person:Ada Lovelace>).\n",
        )

        reference = NoteReference(scheme=ReferenceScheme.PERSON, name="Ada Lovelace")
        before = afanes.core.vault.scan_vault(root)
        resolved = before.catalog.resolve(reference)
        assert resolved.outcome is ResolutionOutcome.RESOLVED
        assert resolved.targets == (ada,)

        moved = afanes.core.vault.move_note(root, ada, Path("work"), confirm=True)
        after_move = afanes.core.vault.scan_vault(root)
        resolved_after_move = after_move.catalog.resolve(reference)
        assert resolved_after_move.outcome is ResolutionOutcome.RESOLVED
        assert resolved_after_move.targets == (moved,)

        preview = afanes.core.vault.plan_rename(root, moved, "Ada King")
        assert preview.reference_count == ONE_REFERENCE
        report = afanes.core.vault.apply_rename(root, preview, confirm=True)
        assert report.failed == ()
        assert "[Ada King](<person:Ada King>)" in note.read_text(encoding="utf-8")

        after_rename = afanes.core.vault.scan_vault(root)
        renamed = after_rename.catalog.resolve(NoteReference(scheme=ReferenceScheme.PERSON, name="Ada King"))
        assert renamed.outcome is ResolutionOutcome.RESOLVED
        assert renamed.targets[0].parent.name == "work"
