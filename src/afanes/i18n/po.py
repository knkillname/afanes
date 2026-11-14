# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Parse gettext ``.po`` catalogs and write the standard binary ``.mo`` format.

The runtime always loads catalogs through the standard library :mod:`gettext`.
This module only supplies an offline compiler so the project does not depend on
a GNU gettext installation. The written format is the documented GNU ``.mo``
layout, and the tests load every compiled file with
:class:`gettext.GNUTranslations`.
"""

import ast
import dataclasses
import struct
from pathlib import Path
from typing import Self

_MO_MAGIC = 0x950412DE
_MO_REVISION = 0
_HEADER_SIZE = 28
_CONTEXT_SEPARATOR = "\x04"

# Public default source tree for ``hatch run i18n-compile``.
CATALOG_DIRECTORY = Path("src") / "afanes" / "i18n" / "locales"


class PoError(Exception):
    """Raised when a gettext source catalog is malformed."""


@dataclasses.dataclass(frozen=True, slots=True)
class PoEntry:
    """One message in a gettext source catalog.

    Attributes
    ----------
    context : str | None
        Gettext context, or ``None`` when the entry has none.
    msgid : str
        English source message.
    msgstr : str
        Spanish translation.
    """

    context: str | None
    msgid: str
    msgstr: str

    @property
    def key(self) -> bytes:
        """Return the binary catalog key for this entry.

        Returns
        -------
        bytes
            UTF-8 key with the gettext context separator when a context is
            present.
        """
        if self.context is None:
            return self.msgid.encode()
        return f"{self.context}{_CONTEXT_SEPARATOR}{self.msgid}".encode()


@dataclasses.dataclass(slots=True)
class _EntryBuilder:
    """Accumulate one gettext entry from source directives."""

    line_number: int
    context: str | None = None
    msgid: str | None = None
    msgstr: str | None = None
    field: str | None = None

    def apply(self, line: str, line_number: int) -> None:
        """Apply one source directive to this builder.

        Parameters
        ----------
        line : str
            Stripped source line.
        line_number : int
            Source line used in failure messages.

        Raises
        ------
        PoError
            If the directive is malformed or unsupported.
        """
        if line.startswith("#"):
            return
        if line.startswith("msgctxt "):
            self._start_context(line, line_number)
        elif line.startswith(("msgid_plural ", "msgstr[")):
            message = f"Line {line_number}: plural forms are not supported"
            raise PoError(message)
        elif line.startswith("msgid "):
            self._start_msgid(line, line_number)
        elif line.startswith("msgstr "):
            self._start_msgstr(line, line_number)
        elif line.startswith('"'):
            self._append(line, line_number)
        else:
            message = f"Line {line_number}: unrecognized directive {line!r}"
            raise PoError(message)

    def build(self) -> PoEntry | None:
        """Return the completed entry, or ``None`` for a comment block.

        Returns
        -------
        PoEntry | None
            Parsed entry, or ``None`` when the block declares no msgid.

        Raises
        ------
        PoError
            If a declared entry has no msgstr.
        """
        if self.msgid is None:
            if self.context is not None or self.msgstr is not None:
                message = f"Line {self.line_number}: entry has no msgid"
                raise PoError(message)
            return None
        if self.msgstr is None:
            message = f"Line {self.line_number}: entry has no msgstr"
            raise PoError(message)
        return PoEntry(context=self.context, msgid=self.msgid, msgstr=self.msgstr)

    def _start_context(self, line: str, line_number: int) -> None:
        """Start a context directive."""
        if self.msgid is not None:
            message = f"Line {line_number}: msgctxt after msgid"
            raise PoError(message)
        self.context = self._literal(line, "msgctxt", line_number)
        self.field = "context"

    def _start_msgid(self, line: str, line_number: int) -> None:
        """Start a msgid directive."""
        if self.msgid is not None:
            message = f"Line {line_number}: duplicate msgid in one entry"
            raise PoError(message)
        self.msgid = self._literal(line, "msgid", line_number)
        self.field = "msgid"

    def _start_msgstr(self, line: str, line_number: int) -> None:
        """Start a msgstr directive."""
        if self.msgid is None:
            message = f"Line {line_number}: msgstr before msgid"
            raise PoError(message)
        if self.msgstr is not None:
            message = f"Line {line_number}: duplicate msgstr in one entry"
            raise PoError(message)
        self.msgstr = self._literal(line, "msgstr", line_number)
        self.field = "msgstr"

    def _append(self, line: str, line_number: int) -> None:
        """Append one continuation string to the active field."""
        if self.field is None:
            message = f"Line {line_number}: continuation without a field"
            raise PoError(message)
        value = self._decode(line, line_number)
        if self.field == "context":
            self.context = f"{self.context or ''}{value}"
        elif self.field == "msgid":
            self.msgid = f"{self.msgid or ''}{value}"
        else:
            self.msgstr = f"{self.msgstr or ''}{value}"

    @classmethod
    def _literal(cls, line: str, directive: str, line_number: int) -> str:
        """Decode the quoted value of one directive.

        Parameters
        ----------
        line : str
            Full directive line.
        directive : str
            Directive name.
        line_number : int
            Line used in the failure message.

        Returns
        -------
        str
            Decoded value.

        Raises
        ------
        PoError
            If the directive carries no quoted value.
        """
        value = line[len(directive) :].strip()
        if not value:
            message = f"Line {line_number}: {directive} has no value"
            raise PoError(message)
        return cls._decode(value, line_number)

    @classmethod
    def _decode(cls, value: str, line_number: int) -> str:
        """Decode one quoted gettext string.

        Parameters
        ----------
        value : str
            Quoted string, including its delimiters.
        line_number : int
            Line used in the failure message.

        Returns
        -------
        str
            Decoded string.

        Raises
        ------
        PoError
            If the value is not a valid quoted string literal.
        """
        try:
            decoded = ast.literal_eval(value)
        except (SyntaxError, ValueError) as exc:
            message = f"Line {line_number}: invalid string literal {value!r}"
            raise PoError(message) from exc
        if not isinstance(decoded, str):
            message = f"Line {line_number}: value is not text"
            raise PoError(message)
        return decoded


@dataclasses.dataclass(frozen=True, slots=True)
class PoCatalog:
    """A parsed gettext source catalog.

    Attributes
    ----------
    entries : tuple[PoEntry, ...]
        Entries in source order, including the header entry when present.
    """

    entries: tuple[PoEntry, ...]

    @classmethod
    def parse(cls, text: str) -> Self:
        """Parse gettext source text.

        Parameters
        ----------
        text : str
            Complete ``.po`` file contents.

        Returns
        -------
        PoCatalog
            Parsed entries in source order.

        Raises
        ------
        PoError
            If a block is malformed, uses plural forms, or repeats a key.
        """
        entries: list[PoEntry] = []
        builder = _EntryBuilder(line_number=1)
        for line_number, raw_line in enumerate(text.splitlines(), start=1):
            line = raw_line.strip()
            if not line:
                entry = builder.build()
                if entry is not None:
                    entries.append(entry)
                builder = _EntryBuilder(line_number=line_number + 1)
                continue
            builder.apply(line, line_number)
        entry = builder.build()
        if entry is not None:
            entries.append(entry)
        seen: set[bytes] = set()
        for entry in entries:
            if entry.key in seen:
                message = f"Duplicate catalog key: {entry.key!r}"
                raise PoError(message)
            seen.add(entry.key)
        return cls(entries=tuple(entries))

    @classmethod
    def from_path(cls, path: Path) -> Self:
        """Read and parse one ``.po`` file.

        Parameters
        ----------
        path : pathlib.Path
            Source catalog path.

        Returns
        -------
        PoCatalog
            Parsed catalog.

        Raises
        ------
        OSError
            If the file cannot be read.
        PoError
            If the catalog is malformed.
        """
        return cls.parse(path.read_text(encoding="utf-8"))

    @property
    def header(self) -> PoEntry | None:
        """Return the header entry.

        Returns
        -------
        PoEntry | None
            Entry with an empty context and empty msgid, or ``None``.
        """
        return next(
            (entry for entry in self.entries if entry.context is None and entry.msgid == ""),
            None,
        )

    @property
    def messages(self) -> tuple[PoEntry, ...]:
        """Return every translatable entry without the header.

        Returns
        -------
        tuple[PoEntry, ...]
            Entries with a non-empty msgid.
        """
        return tuple(entry for entry in self.entries if entry.msgid != "")

    def to_mo(self) -> bytes:
        """Write this catalog as a standard binary ``.mo`` file.

        Returns
        -------
        bytes
            Complete little-endian ``.mo`` contents. Entries are sorted by key
            for a deterministic result, with the header first.
        """
        header = self.header
        header_entry = PoEntry(context=None, msgid="", msgstr="" if header is None else header.msgstr)
        messages = sorted(
            (entry for entry in self.entries if not (entry.context is None and entry.msgid == "")),
            key=lambda entry: entry.key,
        )
        ordered = (header_entry, *messages)
        encoded = [(entry.key, entry.msgstr.encode("utf-8")) for entry in ordered]
        count = len(encoded)
        master_offset = _HEADER_SIZE
        trans_offset = master_offset + count * 8
        string_offset = trans_offset + count * 8
        header_bytes = struct.pack(
            "<7I",
            _MO_MAGIC,
            _MO_REVISION,
            count,
            master_offset,
            trans_offset,
            0,
            0,
        )
        master_table: list[bytes] = []
        trans_table: list[bytes] = []
        strings: list[bytes] = []
        offset = string_offset
        for key, translation in encoded:
            master_table.append(struct.pack("<2I", len(key), offset))
            strings.append(key + b"\x00")
            offset += len(key) + 1
            trans_table.append(struct.pack("<2I", len(translation), offset))
            strings.append(translation + b"\x00")
            offset += len(translation) + 1
        return b"".join((header_bytes, *master_table, *trans_table, *strings))

    def write_mo(self, path: Path) -> None:
        """Write the compiled catalog to a file.

        Parameters
        ----------
        path : pathlib.Path
            Destination ``.mo`` path.
        """
        path.write_bytes(self.to_mo())


@dataclasses.dataclass(frozen=True, slots=True)
class CatalogCompiler:
    """Compile every gettext source catalog under one localedir.

    Attributes
    ----------
    localedir : pathlib.Path
        Directory holding ``<language>/LC_MESSAGES/*.po`` sources.
    """

    localedir: Path = CATALOG_DIRECTORY

    def compile(self) -> tuple[Path, ...]:
        """Compile every source catalog.

        Returns
        -------
        tuple[pathlib.Path, ...]
            Compiled ``.mo`` paths, in source order.
        """
        compiled: list[Path] = []
        for source in sorted(self.localedir.rglob("*.po")):
            catalog = PoCatalog.from_path(source)
            destination = source.with_suffix(".mo")
            catalog.write_mo(destination)
            compiled.append(destination)
        return tuple(compiled)
