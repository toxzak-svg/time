"""
Architectural diagnosis of retrieval pipelines.

Surfaces redundancy, mixed concerns, and composability issues so that
learning can target structural improvements, not only correctness fixes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Concern(Enum):
    """Architectural concerns that should be separated or unified intentionally."""
    VALIDITY = "validity"           # Is fact valid at query time?
    RANKING = "ranking"             # How to order valid candidates?
    DECAY = "decay"                 # Time-based downweighting
    TIEBREAK = "tiebreak"           # Breaking ties among equally valid facts
    FILTER = "filter"               # Candidate set (domain, subject, etc.)


@dataclass
class RetrievalArchitecture:
    """
    Description of how a retrieval system composes concerns.
    Used by diagnoser to detect redundancy and mixed responsibilities.
    """
    name: str
    uses_validity: bool = False
    uses_decay: bool = False
    uses_recency_in_ranking: bool = False
    uses_confidence_tiebreak: bool = False
    validity_before_ranking: bool = True   # Ideal: filter then rank
    decay_affects_ranking: bool = False   # If true, decay is part of score (can duplicate validity role)
    notes: str = ""

    def concerns(self) -> list[Concern]:
        out = [Concern.FILTER]
        if self.uses_validity:
            out.append(Concern.VALIDITY)
        if self.uses_decay:
            out.append(Concern.DECAY)
        if self.uses_recency_in_ranking or self.uses_confidence_tiebreak:
            out.append(Concern.RANKING)
        if self.uses_confidence_tiebreak:
            out.append(Concern.TIEBREAK)
        return out


@dataclass
class Diagnosis:
    """Single architectural finding: not a bug, but an efficiency or clarity issue."""
    kind: str   # "redundancy" | "mixed_concern" | "duplication" | "composability"
    component: str
    message: str
    suggestion: str
    severity: str = "medium"  # low | medium | high
    evidence: dict[str, Any] = field(default_factory=dict)


def diagnose_redundancy(architectures: list[RetrievalArchitecture]) -> list[Diagnosis]:
    """
    Find redundant concerns across systems (e.g. validity checked in both filter and score).
    Learning target: one canonical place per concern.
    """
    out: list[Diagnosis] = []
    for a in architectures:
        if a.uses_validity and a.decay_affects_ranking:
            # Validity already gates candidates; decay then re-weights by time.
            # On overlapping facts, decay can override "all valid" by preferring newer.
            out.append(Diagnosis(
                kind="redundancy",
                component=a.name,
                message="Validity and decay both affect outcome: validity filters, decay re-ranks. "
                        "For overlapping facts, decay effectively overrides equal validity.",
                suggestion="Use validity as the only temporal gate; use confidence/recency only for tiebreak.",
                severity="high",
                evidence={"uses_validity": True, "decay_affects_ranking": True},
            ))
    return out


def diagnose_separation(architectures: list[RetrievalArchitecture]) -> list[Diagnosis]:
    """
    Find mixed concerns (e.g. one function doing filter + validity + decay + tiebreak).
    Learning target: separate filter → validity → rank → tiebreak.
    """
    out: list[Diagnosis] = []
    for a in architectures:
        concerns = a.concerns()
        if Concern.DECAY in concerns and Concern.TIEBREAK not in concerns and a.uses_decay:
            out.append(Diagnosis(
                kind="mixed_concern",
                component=a.name,
                message="Decay is used for ranking but tiebreak is not explicit. "
                        "Decay conflates 'validity' with 'preference among valid'.",
                suggestion="Separate: (1) validity window filter, (2) tiebreak policy (e.g. confidence, recency).",
                severity="medium",
                evidence={"concerns": [c.value for c in concerns]},
            ))
        if a.decay_affects_ranking and a.uses_validity:
            out.append(Diagnosis(
                kind="mixed_concern",
                component=a.name,
                message="Ranking uses both validity (hard filter) and decay (soft score). "
                        "Two sources of temporal truth can conflict on overlapping facts.",
                suggestion="Single source of temporal truth: validity only; no decay inside ranking.",
                severity="high",
                evidence={"validity_before_ranking": a.validity_before_ranking},
            ))
    return out


def diagnose_composability(architectures: list[RetrievalArchitecture]) -> list[Diagnosis]:
    """
    Find duplicated logic across systems (e.g. half_life, is_valid_as_of repeated).
    Learning target: shared building blocks, pluggable policies.
    """
    # Heuristic: many systems with same concern but no shared descriptor
    decay_users = [a for a in architectures if a.uses_decay]
    if len(decay_users) > 1:
        return [Diagnosis(
            kind="composability",
            component="multiple",
            message=f"Decay logic duplicated across {len(decay_users)} systems (e.g. half_life, score formula).",
            suggestion="Extract one ValidityPolicy and one TiebreakPolicy; compose in each system.",
            severity="medium",
            evidence={"systems_with_decay": [a.name for a in decay_users]},
        )]
    return []


def architectural_report(architectures: list[RetrievalArchitecture]) -> list[Diagnosis]:
    """Run all architectural diagnoses and return a single list (deduplicated by message)."""
    seen: set[str] = set()
    out: list[Diagnosis] = []
    for d in (
        diagnose_redundancy(architectures)
        + diagnose_separation(architectures)
        + diagnose_composability(architectures)
    ):
        if d.message not in seen:
            seen.add(d.message)
            out.append(d)
    return out
