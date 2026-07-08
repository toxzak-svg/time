"""
Integrator: architectural integration of learning.

Takes diagnoses (from diagnoser) and turns them into *architectural* changes:
single sources of truth, composed policies, and clearer separation of concerns.
Learning is about efficiency and structure, not only applying bug fixes.
"""

from .policy import (
    ValidityPolicy,
    TiebreakPolicy,
    RetrievalPolicy,
    validity_only_tiebreak_policy,
)
from .learning import (
    integrate_diagnoses,
    recommended_policy_for_signals,
    ArchitecturalChange,
)

__all__ = [
    "ValidityPolicy",
    "TiebreakPolicy",
    "RetrievalPolicy",
    "validity_only_tiebreak_policy",
    "integrate_diagnoses",
    "recommended_policy_for_signals",
    "ArchitecturalChange",
]
