"""
Diagnoser: architectural diagnosis for temporal retrieval systems.

Learning here is about *architectural efficiency*: redundancy, separation of concerns,
composability, and scaling—not merely bug detection. Diagnoses inform how to change
the architecture, not just which assertion failed.
"""

from .architecture import (
    RetrievalArchitecture,
    diagnose_redundancy,
    diagnose_separation,
    diagnose_composability,
    architectural_report,
)
from .signals import (
    result_to_signals,
    signals_to_diagnoses,
    BenchmarkSignals,
)

__all__ = [
    "RetrievalArchitecture",
    "diagnose_redundancy",
    "diagnose_separation",
    "diagnose_composability",
    "architectural_report",
    "result_to_signals",
    "signals_to_diagnoses",
    "BenchmarkSignals",
]
