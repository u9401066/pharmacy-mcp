"""Safe text extraction for configured local pharmaceutical files."""

from __future__ import annotations

import csv
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SUPPORTED_EXTENSIONS = frozenset(
    {".csv", ".doc", ".docx", ".md", ".pdf", ".txt", ".xls", ".xlsx"}
)


@dataclass(frozen=True)
class DocumentMatch:
    path: str
    title: str
    extension: str
    snippet: str


class DocumentStore:
    """Search files under administrator-configured roots only."""

    def __init__(
        self,
        roots: tuple[Path, ...],
        *,
        max_bytes: int,
        max_files: int,
    ) -> None:
        self.roots = tuple(root.resolve() for root in roots)
        self.max_bytes = max_bytes
        self.max_files = max_files

    def search(
        self,
        query: str,
        limit: int,
    ) -> tuple[list[DocumentMatch], list[str], int]:
        """Extract configured files and return bounded matching snippets."""

        matches: list[DocumentMatch] = []
        warnings: list[str] = []
        scanned = 0
        for path in self._files():
            if scanned >= self.max_files or len(matches) >= limit:
                break
            scanned += 1
            try:
                text = self.read(path)
            except (OSError, ValueError, RuntimeError) as exc:
                warnings.append(f"{path.name}: {exc}")
                continue
            snippet = _matching_snippet(text, query)
            if snippet is None:
                continue
            matches.append(
                DocumentMatch(
                    path=str(path),
                    title=path.stem,
                    extension=path.suffix.lower(),
                    snippet=snippet,
                )
            )
        return matches, warnings, scanned

    def read(self, path: Path) -> str:
        """Extract text after enforcing root, file type, symlink, and size policy."""

        resolved = path.resolve()
        if path.is_symlink() or not self._inside_root(resolved):
            raise ValueError("path is outside an allowed root or is a symlink")
        if resolved.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError("unsupported file extension")
        if resolved.stat().st_size > self.max_bytes:
            raise ValueError(f"file exceeds {self.max_bytes} byte limit")

        extension = resolved.suffix.lower()
        if extension in {".md", ".txt"}:
            return resolved.read_text(encoding="utf-8", errors="replace")
        if extension == ".csv":
            return _read_csv(resolved)
        if extension == ".pdf":
            return _read_pdf(resolved)
        if extension == ".docx":
            return _read_docx(resolved)
        if extension == ".xlsx":
            return _read_xlsx(resolved)
        if extension == ".xls":
            return _read_xls(resolved)
        return _read_legacy_doc(resolved)

    def _files(self) -> list[Path]:
        files: set[Path] = set()
        for root in self.roots:
            if not root.is_dir():
                continue
            files.update(
                path
                for path in root.rglob("*")
                if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
            )
        return sorted(files)

    def _inside_root(self, path: Path) -> bool:
        return any(path.is_relative_to(root) for root in self.roots)


def _read_csv(path: Path) -> str:
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as file:
        return "\n".join(" | ".join(row) for row in csv.reader(file))


def _read_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _read_docx(path: Path) -> str:
    from docx import Document

    document = Document(str(path))
    paragraphs = [paragraph.text for paragraph in document.paragraphs]
    table_rows = [
        " | ".join(cell.text for cell in row.cells)
        for table in document.tables
        for row in table.rows
    ]
    return "\n".join([*paragraphs, *table_rows])


def _read_xlsx(path: Path) -> str:
    from openpyxl import load_workbook

    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        rows = []
        for sheet in workbook.worksheets:
            rows.append(f"[{sheet.title}]")
            rows.extend(
                _stringify_row(row) for row in sheet.iter_rows(values_only=True)
            )
        return "\n".join(rows)
    finally:
        workbook.close()


def _read_xls(path: Path) -> str:
    import xlrd

    workbook = xlrd.open_workbook(str(path), on_demand=True)
    try:
        rows = []
        for sheet in workbook.sheets():
            rows.append(f"[{sheet.name}]")
            rows.extend(
                _stringify_row(sheet.row_values(index)) for index in range(sheet.nrows)
            )
        return "\n".join(rows)
    finally:
        workbook.release_resources()


def _read_legacy_doc(path: Path) -> str:
    try:
        result = subprocess.run(
            ["antiword", str(path)],
            check=True,
            capture_output=True,
            timeout=20,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("legacy .doc requires the antiword executable") from exc
    except subprocess.SubprocessError as exc:
        raise RuntimeError(f"antiword extraction failed: {exc}") from exc
    return result.stdout.decode("utf-8", errors="replace")


def _stringify_row(row: Any) -> str:
    return " | ".join("" if value is None else str(value) for value in row)


def _matching_snippet(text: str, query: str, size: int = 500) -> str | None:
    haystack = text.casefold()
    needle = query.casefold().strip()
    if not needle:
        return None
    index = haystack.find(needle)
    if index < 0:
        return None
    start = max(0, index - size // 3)
    end = min(len(text), start + size)
    snippet = " ".join(text[start:end].split())
    if start:
        snippet = "…" + snippet
    if end < len(text):
        snippet += "…"
    return snippet
