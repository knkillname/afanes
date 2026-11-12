import re
import unicodedata
from pathlib import Path

import markdown_it

ROOT = Path(__file__).resolve().parents[2]
DOCS_ROOT = ROOT / "docs"
STATIC_ROOT = DOCS_ROOT / "_static"
README_PATH = ROOT / "README.md"
SUMMARY_PATTERN = re.compile(r"(?m)^:{3,}\{admonition\}\s+tl;dr\s*$")
RUNTIME_PATTERN = re.compile(r'(?m)^mermaid_use_local = "([^"]*)"\s*$')
BOX_ART_PATTERN = re.compile(r"\+-{3,}\+")
ACCESS_TITLE_PATTERN = re.compile(r"(?m)^\s*accTitle:\s*\S")
ACCESS_DESC_PATTERN = re.compile(r"(?m)^\s*accDescr:\s*\S")
BARE_AUTOMODULE_PATTERN = re.compile(r"(?m)^\s*(?:```|:{3,})\{automodule\}")


def _docs_pages() -> list[Path]:
    return sorted(
        path for path in DOCS_ROOT.rglob("*.md") if "_build" not in path.parts and "_static" not in path.parts
    )


def _headings(text: str) -> list[str]:
    tokens = markdown_it.MarkdownIt().parse(text)
    headings: list[str] = []
    for index, token in enumerate(tokens):
        if token.type == "heading_open" and index + 1 < len(tokens):
            headings.append(tokens[index + 1].content)
    return headings


def _starts_with_emoji(text: str) -> bool:
    stripped = text.strip()
    return bool(stripped) and unicodedata.category(stripped[0]) == "So"


def _mermaid_runtime() -> str:
    text = (DOCS_ROOT / "conf.py").read_text(encoding="utf-8")
    match = RUNTIME_PATTERN.search(text)
    assert match is not None
    return match.group(1)


def _fences(text: str) -> list[tuple[str, str]]:
    tokens = markdown_it.MarkdownIt().parse(text)
    return [(token.info.strip(), token.content) for token in tokens if token.type == "fence"]


class TestDocumentationStyle:
    def test_every_heading_starts_with_an_emoji(self) -> None:
        offenders: list[str] = []
        for path in [README_PATH, *_docs_pages()]:
            offenders.extend(
                f"{path.relative_to(ROOT)}: {heading}"
                for heading in _headings(path.read_text(encoding="utf-8"))
                if not _starts_with_emoji(heading)
            )
        assert offenders == []

    def test_guide_and_reference_pages_start_with_a_summary(self) -> None:
        offenders: list[str] = []
        for path in _docs_pages():
            if path.parent.name not in {"guide", "reference"}:
                continue
            if SUMMARY_PATTERN.search(path.read_text(encoding="utf-8")) is None:
                offenders.append(str(path.relative_to(ROOT)))
        assert offenders == []


class TestDiagramRuntime:
    def test_configured_mermaid_runtime_is_local(self) -> None:
        assert not _mermaid_runtime().startswith(("http://", "https://", "//", "/"))

    def test_vendored_mermaid_tree_is_complete(self) -> None:
        entry = STATIC_ROOT / _mermaid_runtime()
        chunk_dir = entry.parent / "chunks" / "mermaid.esm.min"
        assert entry.is_file()
        assert sorted(chunk_dir.glob("*.mjs")) != []


class TestDiagramAuthoring:
    def test_no_ascii_box_art_in_fenced_blocks(self) -> None:
        offenders: list[str] = []
        for path in _docs_pages():
            for info, content in _fences(path.read_text(encoding="utf-8")):
                if BOX_ART_PATTERN.search(content) is not None:
                    offenders.append(f"{path.relative_to(ROOT)}: {info or 'plain'} fence")
        assert offenders == []

    def test_every_mermaid_fence_has_accessibility_metadata(self) -> None:
        offenders: list[str] = []
        for path in _docs_pages():
            for info, content in _fences(path.read_text(encoding="utf-8")):
                if info != "mermaid":
                    continue
                if ACCESS_TITLE_PATTERN.search(content) is None or ACCESS_DESC_PATTERN.search(content) is None:
                    offenders.append(str(path.relative_to(ROOT)))
        assert offenders == []


class TestApiReferenceAuthoring:
    def test_automodule_directives_use_an_rst_fence(self) -> None:
        offenders = [
            str(path.relative_to(ROOT))
            for path in sorted((DOCS_ROOT / "api").glob("*.md"))
            if BARE_AUTOMODULE_PATTERN.search(path.read_text(encoding="utf-8"))
        ]
        assert offenders == []
