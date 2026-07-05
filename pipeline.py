"""Deduplicate records across database exports.

Strategy (in priority order):
  1. Exact DOI match (after normalization) — highest confidence.
  2. Normalized-title exact match.
  3. Fuzzy title match above a similarity threshold, guarded by year
     agreement to avoid collapsing distinct-but-similarly-titled papers.

The first occurrence of a duplicate group is kept; later ones are recorded
as removed, with the reason, so the PRISMA count is fully auditable.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field

from prismapilot.records import Record


@dataclass
class RemovedRecord:
    record: Record
    duplicate_of: str  # id of the kept record
    reason: str


@dataclass
class DedupResult:
    unique: list[Record]
    removed: list[RemovedRecord]

    @property
    def n_in(self) -> int:
        return len(self.unique) + len(self.removed)

    @property
    def n_unique(self) -> int:
        return len(self.unique)

    @property
    def n_removed(self) -> int:
        return len(self.removed)


class Deduplicator:
    def __init__(self, title_threshold: float = 0.92):
        self.title_threshold = title_threshold

    def deduplicate(self, records: list[Record]) -> DedupResult:
        unique: list[Record] = []
        removed: list[RemovedRecord] = []
        seen_doi: dict[str, Record] = {}
        seen_title: dict[str, Record] = {}

        for rec in records:
            doi = rec.normalized_doi
            if doi and doi in seen_doi:
                kept = seen_doi[doi]
                removed.append(RemovedRecord(rec, kept.id, "exact DOI match"))
                continue

            ntitle = rec.normalized_title
            if ntitle and ntitle in seen_title:
                kept = seen_title[ntitle]
                removed.append(RemovedRecord(rec, kept.id, "exact title match"))
                if doi:
                    seen_doi.setdefault(doi, kept)
                continue

            fuzzy_match = self._fuzzy_title_match(rec, unique)
            if fuzzy_match is not None:
                kept, score = fuzzy_match
                removed.append(
                    RemovedRecord(rec, kept.id, f"fuzzy title match ({score:.2f})")
                )
                continue

            unique.append(rec)
            if doi:
                seen_doi[doi] = rec
            if ntitle:
                seen_title[ntitle] = rec

        return DedupResult(unique=unique, removed=removed)

    def _fuzzy_title_match(self, rec: Record, pool: list[Record]):
        if not rec.normalized_title:
            return None
        best = None
        best_score = 0.0
        for other in pool:
            if not other.normalized_title:
                continue
            # year guard: if both have years and they differ, don't merge
            if rec.year and other.year and rec.year != other.year:
                continue
            score = difflib.SequenceMatcher(
                None, rec.normalized_title, other.normalized_title
            ).ratio()
            if score > best_score:
                best_score = score
                best = other
        if best is not None and best_score >= self.title_threshold:
            return best, best_score
        return None
