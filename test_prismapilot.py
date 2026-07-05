"""PRISMA-Pilot — a systematic-review screening assistant.

Handles the mechanical, error-prone parts of the screening pipeline:
loading records from RIS/CSV/JSON, deduplicating across databases,
applying transparent keyword-based inclusion/exclusion rules, and
emitting a PRISMA-style flow count for the methods section.
"""

__version__ = "0.1.0"

from prismapilot.records import Record, load_records
from prismapilot.dedup import Deduplicator, DedupResult
from prismapilot.screen import Screener, ScreenConfig, ScreenDecision
from prismapilot.flow import PrismaFlow

__all__ = [
    "Record",
    "load_records",
    "Deduplicator",
    "DedupResult",
    "Screener",
    "ScreenConfig",
    "ScreenDecision",
    "PrismaFlow",
    "__version__",
]
