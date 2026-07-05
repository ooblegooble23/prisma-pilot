"""Bibliographic record model and multi-format loaders (JSON, CSV, RIS)."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Record:
    """A single bibliographic record from a database export."""

    id: str
    title: str = ""
    abstract: str = ""
    authors: str = ""
    year: Optional[int] = None
    journal: str = ""
    doi: str = ""

    def searchable_text(self) -> str:
        """Concatenated lowercase title + abstract for keyword screening."""
        return f"{self.title}\n{self.abstract}".lower()

    @property
    def normalized_title(self) -> str:
        """Title reduced to alphanumeric tokens for dedup comparison."""
        return re.sub(r"[^a-z0-9]+", " ", self.title.lower()).strip()

    @property
    def normalized_doi(self) -> str:
        return re.sub(r"^https?://(dx\.)?doi\.org/", "", self.doi.strip().lower())


# ---------------------------------------------------------------- loaders

def _record_from_dict(d: dict, fallback_id: str) -> Record:
    year = d.get("year")
    if isinstance(year, str):
        m = re.search(r"\d{4}", year)
        year = int(m.group()) if m else None
    return Record(
        id=str(d.get("id") or fallback_id),
        title=str(d.get("title", "")).strip(),
        abstract=str(d.get("abstract", "")).strip(),
        authors=str(d.get("authors", "")).strip(),
        year=year,
        journal=str(d.get("journal", "")).strip(),
        doi=str(d.get("doi", "")).strip(),
    )


def load_json(path: Path) -> list[Record]:
    data = json.loads(Path(path).read_text())
    if isinstance(data, dict):
        data = data.get("records", [])
    return [_record_from_dict(d, f"J{i:04d}") for i, d in enumerate(data, 1)]


def load_csv(path: Path) -> list[Record]:
    records: list[Record] = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for i, row in enumerate(reader, 1):
            lower = {(k or "").strip().lower(): v for k, v in row.items()}
            records.append(_record_from_dict(lower, f"C{i:04d}"))
    return records


# RIS tag mapping (common subset)
_RIS_MAP = {
    "TI": "title", "T1": "title",
    "AB": "abstract", "N2": "abstract",
    "AU": "authors", "A1": "authors",
    "PY": "year", "Y1": "year",
    "JO": "journal", "JF": "journal", "T2": "journal",
    "DO": "doi",
    "ID": "id",
}


def load_ris(path: Path) -> list[Record]:
    """Minimal RIS parser covering the tags most exports actually use."""
    records: list[Record] = []
    current: dict = {}
    author_parts: list[str] = []
    counter = 0

    def flush():
        nonlocal current, author_parts, counter
        if current or author_parts:
            counter += 1
            if author_parts:
                current["authors"] = "; ".join(author_parts)
            records.append(_record_from_dict(current, f"RIS{counter:04d}"))
        current = {}
        author_parts = []

    for raw in Path(path).read_text(encoding="utf-8-sig").splitlines():
        line = raw.rstrip("\n")
        m = re.match(r"^([A-Z0-9]{2})\s{2}-\s?(.*)$", line)
        if not m:
            continue
        tag, value = m.group(1), m.group(2).strip()
        if tag == "TY":
            flush()  # new record boundary
        elif tag == "ER":
            flush()
        elif tag in ("AU", "A1"):
            if value:
                author_parts.append(value)
        elif tag in _RIS_MAP:
            field_name = _RIS_MAP[tag]
            if field_name not in current:
                current[field_name] = value
    flush()
    return records


def load_records(path: str | Path) -> list[Record]:
    """Dispatch on file extension."""
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix == ".json":
        return load_json(p)
    if suffix == ".csv":
        return load_csv(p)
    if suffix in (".ris", ".txt", ".nbib"):
        return load_ris(p)
    raise ValueError(f"Unsupported file type: {suffix!r} (expected .json/.csv/.ris)")
