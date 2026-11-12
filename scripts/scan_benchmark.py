# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Generate synthetic vaults and measure the cost of a read-only scan.

Run the benchmark with ``hatch run python scripts/scan_benchmark.py``. The
script writes only under a temporary directory, so it cannot scan or modify a
real vault. The generator is importable by the test suite through its file
path.
"""

import argparse
import dataclasses
import functools
import os
import platform
import statistics
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

import afanes.core.connections
import afanes.core.vault.schema
import afanes.core.vault.service
import afanes.core.vault.snapshot

DEFAULT_NOTES = (1_000, 5_000, 10_000)
DEFAULT_REPEAT = 5
DEFAULT_BODY_PARAGRAPHS = 3
DEFAULT_STEPS_PER_PROJECT = 4
DEFAULT_REFERENCE_RATIO = 0.4
MOUNT_FIELD_COUNT = 3


@dataclasses.dataclass(frozen=True, slots=True)
class GeneratedVault:
    """Counts written by one synthetic vault generation.

    Attributes
    ----------
    root : Path
        Directory that received the notes.
    captures : int
        Number of ``type: note`` captures written under ``inbox/``.
    references : int
        Number of ``type: reference`` notes written under ``reference/``.
    projects : int
        Number of ``type: project`` notes written under ``projects/``.
    """

    root: Path
    captures: int
    references: int
    projects: int

    @property
    def total(self) -> int:
        """Return the number of note files written.

        Returns
        -------
        int
            Sum of captures, references, and projects.
        """
        return self.captures + self.references + self.projects


def _paragraphs(index: int, count: int) -> str:
    """Return deterministic prose paragraphs for one note."""
    lines = [
        f"Paragraph {paragraph} of note {index}: the quick brown fox writes a line of ordinary prose "
        "so the parser has a realistic body to read."
        for paragraph in range(count)
    ]
    return "\n\n".join(lines)


def _write_capture(root: Path, index: int, body_paragraphs: int) -> None:
    """Write one unclassified capture into ``inbox/``."""
    path = root / "inbox" / f"Capture {index}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    body = f"# Capture {index}\n\n{_paragraphs(index, body_paragraphs)}\n"
    path.write_text(f"---\ntype: note\n---\n\n{body}", encoding="utf-8", newline="\n")


def _write_reference(root: Path, index: int, body_paragraphs: int, *, categorized: bool) -> None:
    """Write one reference note, optionally under a category folder."""
    folder = root / "reference" / ("person" if categorized else "")
    path = folder / f"Reference {index}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    category = "category: person\n" if categorized else ""
    target = index + 1
    body = (
        f"# Reference {index}\n\n{_paragraphs(index, body_paragraphs)}\n\n"
        f"See [Reference {target}](<note:Reference {target}>) and "
        f"[Project {index}](<project:Project {index}>).\n"
    )
    path.write_text(f"---\ntype: reference\n{category}---\n\n{body}", encoding="utf-8", newline="\n")


def _write_project(root: Path, index: int, body_paragraphs: int, steps: int) -> None:
    """Write one project with task-list steps and metadata comments."""
    path = root / "projects" / f"Project {index}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    step_lines = [
        f"- [ ] Step {step} of project {index} <!-- "
        f"{{owners: [Person {index}], plan: 2026-11-{20 + step % 5:02d}, tags: [benchmark]}} -->"
        for step in range(steps)
    ]
    body = "\n".join(
        [
            f"# Project {index}",
            "",
            _paragraphs(index, body_paragraphs),
            "",
            *step_lines,
            "",
            f"Reference: [Reference {index}](<note:Reference {index}>).",
        ]
    )
    path.write_text(f"---\ntype: project\nstatus: active\n---\n\n{body}\n", encoding="utf-8", newline="\n")


def generate_vault(
    root: Path,
    *,
    notes: int,
    body_paragraphs: int = DEFAULT_BODY_PARAGRAPHS,
    steps_per_project: int = DEFAULT_STEPS_PER_PROJECT,
    reference_ratio: float = DEFAULT_REFERENCE_RATIO,
) -> GeneratedVault:
    """Generate a synthetic vault with captures, references, and projects.

    Parameters
    ----------
    root : Path
        Empty directory that receives the generated tree.
    notes : int
        Total number of note files to write.
    body_paragraphs : int
        Prose paragraphs per note.
    steps_per_project : int
        Task-list steps per project note.
    reference_ratio : float
        Fraction of the notes that are references, between zero and one.

    Returns
    -------
    GeneratedVault
        Directory and per-kind counts that were written.

    Raises
    ------
    ValueError
        If ``notes`` is negative or ``reference_ratio`` is outside zero to one.
    """
    if notes < 0:
        message = "notes must not be negative"
        raise ValueError(message)
    if not 0.0 <= reference_ratio <= 1.0:
        message = "reference_ratio must be between zero and one"
        raise ValueError(message)

    root.mkdir(parents=True, exist_ok=True)
    settings = root / afanes.core.vault.schema.SCHEMA_FILENAME
    settings.write_text(
        f"schema_version: {afanes.core.vault.schema.CURRENT_SCHEMA_VERSION}\n",
        encoding="utf-8",
    )
    references = round(notes * reference_ratio)
    remaining = notes - references
    captures = remaining // 2
    projects = remaining - captures
    for index in range(captures):
        _write_capture(root, index, body_paragraphs)
    for index in range(references):
        _write_reference(root, index, body_paragraphs, categorized=index % 2 == 0)
    for index in range(projects):
        _write_project(root, index, body_paragraphs, steps_per_project)
    return GeneratedVault(root=root, captures=captures, references=references, projects=projects)


def _filesystem_type(path: Path) -> str:
    """Return a best-effort filesystem name for the directory holding ``path``."""
    mounts = Path("/proc/mounts")
    if not mounts.is_file():
        return platform.system()
    resolved = path.resolve()
    best_mount = Path("/")
    best_type = "unknown"
    try:
        lines = mounts.read_text(encoding="utf-8").splitlines()
    except OSError:
        return platform.system()
    for line in lines:
        parts = line.split()
        if len(parts) < MOUNT_FIELD_COUNT:
            continue
        mount = Path(parts[1].replace("\\040", " "))
        if resolved.is_relative_to(mount) and len(mount.parts) >= len(best_mount.parts):
            best_mount = mount
            best_type = parts[2]
    return best_type


def _current_commit(repo_root: Path) -> str:
    """Read the current commit from the repository metadata without a subprocess."""
    head = repo_root / ".git" / "HEAD"
    try:
        text = head.read_text(encoding="utf-8").strip()
    except OSError:
        return "unknown"
    if not text.startswith("ref: "):
        return text[:12]
    ref = repo_root / ".git" / text.removeprefix("ref: ")
    try:
        return ref.read_text(encoding="utf-8").strip()[:12]
    except OSError:
        return "unknown"


def _environment_block(root: Path) -> list[str]:
    """Return the environment lines printed before the timing table."""
    return [
        f"python: {platform.python_version()}",
        f"platform: {platform.platform()}",
        f"filesystem: {_filesystem_type(root)}",
        f"cpu_count: {os.cpu_count() or 0}",
        f"commit: {_current_commit(Path(__file__).resolve().parents[1])}",
    ]


def _timed(callable_: Callable[[], object], repeat: int) -> list[float]:
    """Run one callable once as a warm-up, then return ``repeat`` sample seconds."""
    callable_()
    samples: list[float] = []
    for _ in range(repeat):
        start = time.perf_counter()
        callable_()
        samples.append(time.perf_counter() - start)
    return samples


def _first_page_connections(snapshot: afanes.core.vault.snapshot.VaultSnapshot, path: Path) -> None:
    """Build the connection index and query one page.

    Parameters
    ----------
    snapshot : afanes.core.vault.snapshot.VaultSnapshot
        Scanned vault to index.
    path : Path
        Note whose connections the first page shows.
    """
    afanes.core.connections.Connections(snapshot).for_note(path)


def _format_samples(samples: list[float]) -> str:
    """Format min, median, and max milliseconds for one phase."""
    return f"{min(samples) * 1000:8.2f} {statistics.median(samples) * 1000:8.2f} {max(samples) * 1000:8.2f}"


def benchmark(
    *,
    sizes: tuple[int, ...],
    repeat: int,
    body_paragraphs: int,
    steps_per_project: int,
    reference_ratio: float,
) -> None:
    """Generate each size and print the timing table to standard output.

    Parameters
    ----------
    sizes : tuple[int, ...]
        Note counts to measure.
    repeat : int
        Timed samples per phase after the warm-up.
    body_paragraphs : int
        Prose paragraphs per note.
    steps_per_project : int
        Task-list steps per project note.
    reference_ratio : float
        Fraction of the notes that are references.
    """
    with tempfile.TemporaryDirectory(prefix="afanes-benchmark-") as temporary:
        base = Path(temporary)
        lines = _environment_block(base)
        heading = f"{'notes':>6}  {'phase':<16} {'min ms':>8} {'median ms':>9} {'max ms':>8}"
        lines.extend(["", heading, "-" * len(heading)])
        for size in sizes:
            root = base / f"vault-{size}"
            generate_vault(
                root,
                notes=size,
                body_paragraphs=body_paragraphs,
                steps_per_project=steps_per_project,
                reference_ratio=reference_ratio,
            )
            vault = afanes.core.vault.service.Vault.open(root)
            scan_samples = _timed(vault.scan, repeat)
            fingerprint_samples = _timed(vault.scan_fingerprint, repeat)
            open_samples = _timed(functools.partial(afanes.core.vault.service.Vault.open, root), repeat)
            snapshot = vault.scan()
            first_note = snapshot.notes[0].path if snapshot.notes else root
            connection_samples = _timed(functools.partial(_first_page_connections, snapshot, first_note), repeat)
            lines.append(f"{size:>6}  {'open':<16} {_format_samples(open_samples)}")
            lines.append(f"{size:>6}  {'scan':<16} {_format_samples(scan_samples)}")
            lines.append(f"{size:>6}  {'scan_fingerprint':<16} {_format_samples(fingerprint_samples)}")
            lines.append(f"{size:>6}  {'connections':<16} {_format_samples(connection_samples)}")
        sys.stdout.write("\n".join(lines) + "\n")


def _parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command")
    generate = subparsers.add_parser("generate", help="write a generated vault and exit")
    generate.add_argument("output", type=Path)
    generate.add_argument("--notes", type=int, default=50)
    generate.add_argument("--body-paragraphs", type=int, default=DEFAULT_BODY_PARAGRAPHS)
    generate.add_argument("--steps-per-project", type=int, default=DEFAULT_STEPS_PER_PROJECT)
    generate.add_argument("--reference-ratio", type=float, default=DEFAULT_REFERENCE_RATIO)
    parser.add_argument("--notes", type=int, nargs="+", default=list(DEFAULT_NOTES))
    parser.add_argument("--repeat", type=int, default=DEFAULT_REPEAT)
    parser.add_argument("--body-paragraphs", type=int, default=DEFAULT_BODY_PARAGRAPHS)
    parser.add_argument("--steps-per-project", type=int, default=DEFAULT_STEPS_PER_PROJECT)
    parser.add_argument("--reference-ratio", type=float, default=DEFAULT_REFERENCE_RATIO)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the generator or the benchmark.

    Parameters
    ----------
    argv : list[str] | None
        Arguments to parse, or ``None`` to use :data:`sys.argv`.

    Returns
    -------
    int
        Process exit status.
    """
    arguments = _parser().parse_args(argv)
    if arguments.command == "generate":
        generated = generate_vault(
            arguments.output,
            notes=arguments.notes,
            body_paragraphs=arguments.body_paragraphs,
            steps_per_project=arguments.steps_per_project,
            reference_ratio=arguments.reference_ratio,
        )
        sys.stdout.write(f"wrote {generated.total} notes under {generated.root}\n")
        sys.stdout.write(
            f"captures={generated.captures} references={generated.references} projects={generated.projects}\n"
        )
        return 0
    benchmark(
        sizes=tuple(arguments.notes),
        repeat=arguments.repeat,
        body_paragraphs=arguments.body_paragraphs,
        steps_per_project=arguments.steps_per_project,
        reference_ratio=arguments.reference_ratio,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
