"""Tests for the read-only connection indexes."""

from pathlib import Path

from afanes.core.connections import Connections
from afanes.core.vault.service import Vault


def _write_note(
    root: Path,
    relative: str,
    note_type: str,
    body: str = "",
    *,
    category: str | None = None,
    status: str | None = None,
    asked_by: str | None = None,
) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---", f"type: {note_type}"]
    if category is not None:
        lines.append(f"category: {category}")
    if status is not None:
        lines.append(f"status: {status}")
    if asked_by is not None:
        lines.append(f"asked_by: {asked_by}")
    lines.extend(["---", "", body])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _connections(root: Path) -> Connections:
    return Connections(Vault(root).scan())


class TestConnectionsService:
    def test_unknown_note_has_no_connections(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root, "notes/Ada.md", "note", "# Ada\n")

        connections = _connections(root).for_note(note)

        assert connections.has_connections is False
        assert connections.linked_from == ()
        assert connections.owned_projects == ()
        assert connections.requested_projects == ()
        assert connections.finished_projects == ()

    def test_relative_note_path_finds_its_connections(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root, "reference/Ada.md", "reference", "# Ada\n")
        _write_note(root, "notes/Call.md", "note", "[Ada](<note:Ada>)\n")

        connections = _connections(root).for_note(Path("reference/Ada.md"))

        assert [note.name for note in connections.linked_from] == ["Call"]


class TestLinkedFrom:
    def test_lists_a_note_that_links_here(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        ada = _write_note(root, "reference/Ada.md", "reference", "# Ada\n")
        _write_note(root, "notes/Call.md", "note", "# Call\n\n[Ada](<note:Ada>)\n")

        connections = _connections(root).for_note(ada)

        assert [note.title for note in connections.linked_from] == ["Call"]

    def test_lists_a_repeated_link_once(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        ada = _write_note(root, "reference/Ada.md", "reference", "# Ada\n")
        _write_note(
            root,
            "notes/Call.md",
            "note",
            "[Ada](<note:Ada>) and [Ada again](<note:Ada>) and [Ada](<note:Ada>)\n",
        )

        connections = _connections(root).for_note(ada)

        assert len(connections.linked_from) == 1
        assert connections.linked_from[0].title == "Call"

    def test_excludes_the_note_itself(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        ada = _write_note(root, "reference/Ada.md", "reference", "# Ada\n\n[Ada](<note:Ada>)\n")

        connections = _connections(root).for_note(ada)

        assert connections.linked_from == ()

    def test_excludes_a_missing_name(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        ada = _write_note(root, "reference/Ada.md", "reference", "# Ada\n")
        _write_note(root, "notes/Call.md", "note", "[Nobody](<note:Nobody>)\n")

        connections = _connections(root).for_note(ada)

        assert connections.linked_from == ()

    def test_excludes_an_ambiguous_name(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        first = _write_note(root, "reference/one/Ada.md", "reference", "# Ada\n")
        second = _write_note(root, "reference/two/Ada.md", "reference", "# Ada\n")
        _write_note(root, "notes/Call.md", "note", "[Ada](<note:Ada>)\n")
        connections = _connections(root)

        assert connections.for_note(first).linked_from == ()
        assert connections.for_note(second).linked_from == ()

    def test_excludes_a_trashed_note(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        ada = _write_note(root, "reference/Ada.md", "reference", "# Ada\n")
        _write_note(root, "trash/Call.md", "note", "[Ada](<note:Ada>)\n")

        connections = _connections(root).for_note(ada)

        assert connections.linked_from == ()

    def test_resolves_a_body_reference_in_its_own_scheme(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        project = _write_note(root, "projects/Release 1.0.md", "project", "# Release 1.0\n")
        _write_note(root, "notes/Launch.md", "note", "[Launch](<project:Release 1.0>)\n")

        connections = _connections(root).for_note(project)

        assert [note.title for note in connections.linked_from] == ["Launch"]

    def test_orders_referrers_by_display_title(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        ada = _write_note(root, "reference/Ada.md", "reference", "# Ada\n")
        _write_note(root, "notes/Z.md", "note", "# Alpha\n\n[Ada](<note:Ada>)\n")
        _write_note(root, "notes/A.md", "note", "# Zulu\n\n[Ada](<note:Ada>)\n")

        connections = _connections(root).for_note(ada)

        assert [note.title for note in connections.linked_from] == ["Alpha", "Zulu"]

    def test_orders_equal_titles_by_identity(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        ada = _write_note(root, "reference/Ada.md", "reference", "# Ada\n")
        _write_note(root, "notes/Zulu.md", "note", "# Same\n\n[Ada](<note:Ada>)\n")
        _write_note(root, "notes/Alpha.md", "note", "# Same\n\n[Ada](<note:Ada>)\n")

        connections = _connections(root).for_note(ada)

        assert [note.name for note in connections.linked_from] == ["Alpha", "Zulu"]


class TestOwnedSteps:
    def test_lists_an_owned_step_under_its_project(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        ada = _write_note(root, "reference/Ada.md", "reference", "# Ada\n")
        _write_note(
            root,
            "projects/Home.md",
            "project",
            "# Home\n\n- [ ] Call <!-- {owners: [Ada]} -->\n",
        )

        connections = _connections(root).for_note(ada)

        assert len(connections.owned_projects) == 1
        owned = connections.owned_projects[0]
        assert owned.project.title == "Home"
        assert [step.text for step in owned.open_steps] == ["Call"]
        assert owned.completed_steps == ()

    def test_groups_steps_by_project(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        ada = _write_note(root, "reference/Ada.md", "reference", "# Ada\n")
        _write_note(root, "projects/Zulu.md", "project", "# Zulu\n\n- [ ] Write <!-- {owners: [Ada]} -->\n")
        _write_note(root, "projects/Alpha.md", "project", "# Alpha\n\n- [ ] Call <!-- {owners: [Ada]} -->\n")

        connections = _connections(root).for_note(ada)

        assert [owned.project.title for owned in connections.owned_projects] == ["Alpha", "Zulu"]

    def test_keeps_document_order_within_a_project(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        ada = _write_note(root, "reference/Ada.md", "reference", "# Ada\n")
        _write_note(
            root,
            "projects/Home.md",
            "project",
            "# Home\n\n- [ ] Call <!-- {owners: [Ada]} -->\n- [ ] Write <!-- {owners: [Ada]} -->\n",
        )

        connections = _connections(root).for_note(ada)

        assert [step.text for step in connections.owned_projects[0].open_steps] == ["Call", "Write"]

    def test_splits_completed_steps_before_the_toggle(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        ada = _write_note(root, "reference/Ada.md", "reference", "# Ada\n")
        _write_note(
            root,
            "projects/Home.md",
            "project",
            "# Home\n\n- [ ] Call <!-- {owners: [Ada]} -->\n- [x] Done <!-- {owners: [Ada]} -->\n",
        )

        connections = _connections(root).for_note(ada)

        owned = connections.owned_projects[0]
        assert [step.text for step in owned.open_steps] == ["Call"]
        assert [step.text for step in owned.completed_steps] == ["Done"]
        assert connections.has_completed_steps is True

    def test_completed_steps_alone_still_count_as_a_connection(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        ada = _write_note(root, "reference/Ada.md", "reference", "# Ada\n")
        _write_note(
            root,
            "projects/Home.md",
            "project",
            "# Home\n\n- [x] Done <!-- {owners: [Ada]} -->\n",
        )

        connections = _connections(root).for_note(ada)

        assert connections.has_connections is True
        assert connections.owned_projects[0].open_steps == ()
        assert [step.text for step in connections.owned_projects[0].completed_steps] == ["Done"]

    def test_closed_projects_do_not_contribute(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        ada = _write_note(root, "reference/Ada.md", "reference", "# Ada\n")
        _write_note(
            root,
            "projects/Home.md",
            "project",
            "# Home\n\n- [ ] Call <!-- {owners: [Ada]} -->\n",
            status="done",
        )

        connections = _connections(root).for_note(ada)

        assert connections.owned_projects == ()

    def test_excludes_missing_and_ambiguous_owners(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        first = _write_note(root, "reference/one/Ada.md", "reference", "# Ada\n")
        second = _write_note(root, "reference/two/Ada.md", "reference", "# Ada\n")
        _write_note(
            root,
            "projects/Home.md",
            "project",
            "# Home\n\n- [ ] Call <!-- {owners: [Ada]} -->\n- [ ] Write <!-- {owners: [Nobody]} -->\n",
        )
        connections = _connections(root)

        assert connections.for_note(first).owned_projects == ()
        assert connections.for_note(second).owned_projects == ()

    def test_counts_a_step_once_when_several_owners_resolve_to_it(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        ada = _write_note(root, "reference/Ada.md", "reference", "# Ada\n")
        _write_note(
            root,
            "projects/Home.md",
            "project",
            "# Home\n\n- [ ] Call <!-- {owners: [Ada, ada]} -->\n",
        )

        connections = _connections(root).for_note(ada)

        assert [step.text for step in connections.owned_projects[0].open_steps] == ["Call"]

    def test_an_owner_can_be_any_note(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        team = _write_note(root, "reference/Finance team.md", "reference", "# Finance team\n")
        _write_note(
            root,
            "projects/Home.md",
            "project",
            "# Home\n\n- [ ] Call <!-- {owners: [Finance team]} -->\n",
        )

        connections = _connections(root).for_note(team)

        assert connections.owned_projects[0].project.title == "Home"


class TestRequestedProjects:
    def test_lists_a_project_whose_requester_matches(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        ada = _write_note(root, "reference/Ada.md", "reference", "# Ada\n")
        _write_note(root, "projects/Home.md", "project", "# Home\n", asked_by="Ada")

        connections = _connections(root).for_note(ada)

        assert [note.title for note in connections.requested_projects] == ["Home"]
        assert connections.finished_projects == ()

    def test_splits_finished_projects_from_open_ones(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        ada = _write_note(root, "reference/Ada.md", "reference", "# Ada\n")
        _write_note(root, "projects/Open.md", "project", "# Open\n", asked_by="Ada")
        _write_note(root, "projects/Done.md", "project", "# Done\n", status="done", asked_by="Ada")

        connections = _connections(root).for_note(ada)

        assert [note.title for note in connections.requested_projects] == ["Open"]
        assert [note.title for note in connections.finished_projects] == ["Done"]
        assert connections.has_connections is True

    def test_orders_open_projects_by_display_title(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        ada = _write_note(root, "reference/Ada.md", "reference", "# Ada\n")
        _write_note(root, "projects/Z.md", "project", "# Zulu\n", asked_by="Ada")
        _write_note(root, "projects/A.md", "project", "# Alpha\n", asked_by="Ada")

        connections = _connections(root).for_note(ada)

        assert [note.title for note in connections.requested_projects] == ["Alpha", "Zulu"]

    def test_unmatched_requester_is_attributed_nowhere(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        ada = _write_note(root, "reference/Ada.md", "reference", "# Ada\n")
        _write_note(root, "projects/Home.md", "project", "# Home\n", asked_by="Finance team")
        snapshot = Vault(root).scan()
        connections = Connections(snapshot)
        project = next(note for note in snapshot.notes if note.name == "Home")

        assert connections.for_note(ada).requested_projects == ()
        assert connections.for_note(project.path).requested_projects == ()
        assert project.asked_by == "Finance team"

    def test_ambiguous_requester_is_attributed_nowhere(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        first = _write_note(root, "reference/one/Ada.md", "reference", "# Ada\n")
        second = _write_note(root, "reference/two/Ada.md", "reference", "# Ada\n")
        _write_note(root, "projects/Home.md", "project", "# Home\n", asked_by="Ada")
        connections = _connections(root)

        assert connections.for_note(first).requested_projects == ()
        assert connections.for_note(second).requested_projects == ()

    def test_a_requester_can_be_any_note(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        team = _write_note(root, "reference/Finance team.md", "reference", "# Finance team\n")
        _write_note(root, "projects/Home.md", "project", "# Home\n", asked_by="Finance team")

        connections = _connections(root).for_note(team)

        assert [note.title for note in connections.requested_projects] == ["Home"]


class TestReadOnly:
    def test_building_and_querying_writes_nothing(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        ada = _write_note(root, "reference/Ada.md", "reference", "# Ada\n")
        _write_note(root, "notes/Call.md", "note", "[Ada](<note:Ada>)\n")
        _write_note(root, "projects/Home.md", "project", "# Home\n\n- [ ] Call <!-- {owners: [Ada]} -->\n")
        before = {path: path.read_bytes() for path in sorted(root.rglob("*")) if path.is_file()}

        _connections(root).for_note(ada)

        after = {path: path.read_bytes() for path in sorted(root.rglob("*")) if path.is_file()}
        assert after == before
