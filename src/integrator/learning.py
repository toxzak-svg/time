"""
Integrate diagnoser output into architectural changes.

Maps diagnoses (redundancy, mixed concern, composability) to concrete
policy choices and refactor suggestions—efficiency, not just fixes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .policy import RetrievalPolicy, validity_only_tiebreak_policy


@dataclass
class ArchitecturalChange:
    """
    A recommended architectural change derived from learning.
    Describes what to change and why (efficiency / clarity), not only "fix bug X".
    """
    target: str          # system or component name
    change_type: str     # "replace_policy" | "extract_shared" | "separate_concern"
    description: str
    reason: str          # from diagnosis
    implementation_hint: str = ""
    policy: RetrievalPolicy | None = None  # if change_type == replace_policy
    metadata: dict[str, Any] = field(default_factory=dict)


def integrate_diagnoses(
    diagnoses: list[dict[str, str]],
    architecture_hints: dict[str, Any] | None = None,
) -> list[ArchitecturalChange]:
    """
    Turn diagnoser output into actionable architectural changes.
    diagnoses: list of dicts with kind, component, message, suggestion.
    """
    out: list[ArchitecturalChange] = []
    for d in diagnoses:
        kind = d.get("kind", "")
        component = d.get("component", "")
        suggestion = d.get("suggestion", "")
        message = d.get("message", "")

        if "validity" in suggestion.lower() and "tiebreak" in suggestion.lower():
            out.append(ArchitecturalChange(
                target=component if component != "multiple" else "D",
                change_type="replace_policy",
                description="Use validity as sole temporal gate; tiebreak by confidence/recency only.",
                reason=message,
                implementation_hint="Compose ValidityPolicy (interval only) + TiebreakPolicy (confidence, recency); remove decay from score.",
                policy=validity_only_tiebreak_policy(use_confidence=True),
                metadata={"diagnosis_kind": kind},
            ))
        elif "extract" in suggestion.lower() or "composability" in kind:
            out.append(ArchitecturalChange(
                target="retrieval_layer",
                change_type="extract_shared",
                description="Extract shared ValidityPolicy and TiebreakPolicy; compose in each system.",
                reason=message,
                implementation_hint="Use src.integrator.policy.RetrievalPolicy; pass validity_only_tiebreak_policy() for D_revised.",
                metadata={"diagnosis_kind": kind, "component": component},
            ))
        elif "separate" in suggestion.lower() or "single source" in suggestion.lower():
            out.append(ArchitecturalChange(
                target=component,
                change_type="separate_concern",
                description="Separate validity (filter) from preference (tiebreak); remove decay from ranking.",
                reason=message,
                implementation_hint="Two-step pipeline: filter by validity, then sort by tiebreak key only.",
                metadata={"diagnosis_kind": kind},
            ))
    return out


def recommended_policy_for_signals(
    simpler_beats_full: bool,
    overlap_heavy: bool,
    staleness_eliminated_by_validity: bool,
) -> RetrievalPolicy | None:
    """
    From high-level benchmark signals, recommend a single policy.
    Used when you have signals but not full diagnosis list.
    """
    if (simpler_beats_full or overlap_heavy) and staleness_eliminated_by_validity:
        return validity_only_tiebreak_policy(use_confidence=True)
    return None
