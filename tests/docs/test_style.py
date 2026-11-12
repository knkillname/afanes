import re
import unicodedata
from pathlib import Path

import markdown_it

ROOT = Path(__file__).resolve().parents[2]
DOCS_ROOT = ROOT / "docs"
README_PATH = ROOT / "README.md"
SUMMARY_PATTERN = re.compile(r"(?m)^:{3,}\{admonition\}\s+tl;dr\s*$")


def _docs_pages() -> list[Path]:
    return sorted(path for path in DOCS_ROOT.rglob("*.md") if "_build" not in path.parts)


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
