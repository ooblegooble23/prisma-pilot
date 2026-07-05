"""Title/abstract screening against transparent, auditable keyword rules.

A ScreenConfig is a small, declarative specification:
  - include_any: at least one of these terms must appear (population/topic)
  - include_all: every one of these groups must appear (each group is an
    OR-set, so you can require concept A AND concept B)
  - exclude_any: any of these terms triggers exclusion (e.g. animal studies,
    editorials) unless overridden

Every decision records exactly which terms fired, so screening is
reproducible and explainable rather than a black-box classifier. This does
NOT replace human screening — it flags obvious excludes and surfaces the
reasoning so a human reviewer can move faster on the ambiguous middle.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from prismapilot.records import Record


@dataclass
class ScreenConfig:
    include_any: list[str] = field(default_factory=list)
    include_all: list[list[str]] = field(default_factory=list)
    exclude_any: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> "ScreenConfig":
        include_all = []
        for group in d.get("include_all", []):
            include_all.append(group if isinstance(group, list) else [group])
        return cls(
            include_any=[t.lower() for t in d.get("include_any", [])],
            include_all=[[t.lower() for t in g] for g in include_all],
            exclude_any=[t.lower() for t in d.get("exclude_any", [])],
        )


DECISION_INCLUDE = "include"
DECISION_EXCLUDE = "exclude"


@dataclass
class ScreenDecision:
    record: Record
    decision: str
    reason: str
    matched_include: list[str] = field(default_factory=list)
    matched_exclude: list[str] = field(default_factory=list)


def _term_present(term: str, text: str) -> bool:
    """Whole-word-ish containment: word boundaries around alphanumeric terms."""
    if not term:
        return False
    pattern = r"\b" + re.escape(term) + r"\b"
    return re.search(pattern, text) is not None


class Screener:
    def __init__(self, config: ScreenConfig):
        self.config = config

    def evaluate(self, record: Record) -> ScreenDecision:
        text = record.searchable_text()

        # 1. exclusion terms take precedence
        fired_excludes = [t for t in self.config.exclude_any if _term_present(t, text)]
        if fired_excludes:
            return ScreenDecision(
                record=record,
                decision=DECISION_EXCLUDE,
                reason="exclusion term(s): " + ", ".join(fired_excludes),
                matched_exclude=fired_excludes,
            )

        matched_include: list[str] = []

        # 2. include_any: need at least one, if the list is non-empty
        if self.config.include_any:
            hits = [t for t in self.config.include_any if _term_present(t, text)]
            if not hits:
                return ScreenDecision(
                    record=record,
                    decision=DECISION_EXCLUDE,
                    reason="no required topic term present",
                )
            matched_include.extend(hits)

        # 3. include_all: each group needs at least one hit
        for group in self.config.include_all:
            hits = [t for t in group if _term_present(t, text)]
            if not hits:
                return ScreenDecision(
                    record=record,
                    decision=DECISION_EXCLUDE,
                    reason=f"missing required concept: one of {group}",
                    matched_include=matched_include,
                )
            matched_include.extend(hits)

        return ScreenDecision(
            record=record,
            decision=DECISION_INCLUDE,
            reason="passed all inclusion rules",
            matched_include=matched_include,
        )

    def screen_all(self, records: list[Record]) -> list[ScreenDecision]:
        return [self.evaluate(r) for r in records]
