"""
Composable retrieval policies: validity (single gate) + tiebreak (preference).

Architectural efficiency: one place for "is this fact valid at query time?"
and one place for "among valid facts, how do we choose?"—no decay in ranking.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Optional


def is_valid_as_of(fact: dict, day: int) -> bool:
    """Canonical validity check: fact's interval contains query day."""
    t_from = fact.get("t_valid_from")
    t_until = fact.get("t_valid_until")
    if t_from is None:
        return False
    if t_until is None:
        return int(t_from) <= day
    return int(t_from) <= day <= int(t_until)


@dataclass
class ValidityPolicy(ABC):
    """Single responsibility: decide if a fact is valid at query time."""

    @abstractmethod
    def valid(self, fact: dict, as_of_day: int) -> bool:
        pass


class IntervalValidityPolicy(ValidityPolicy):
    """Use truth intervals only; no decay or extra rules."""

    def valid(self, fact: dict, as_of_day: int) -> bool:
        return is_valid_as_of(fact, as_of_day)


@dataclass
class TiebreakPolicy(ABC):
    """Single responsibility: order valid candidates (no temporal correctness here)."""

    @abstractmethod
    def key(self, fact: dict) -> tuple:
        """Return a sort key (larger = preferred). For max(), we use this directly."""
        pass


class RecencyTiebreakPolicy(TiebreakPolicy):
    """Prefer more recent valid fact (by t_valid_from)."""

    def key(self, fact: dict) -> tuple:
        return (int(fact.get("t_valid_from", 0)),)


class ConfidenceTiebreakPolicy(TiebreakPolicy):
    """Prefer higher confidence; then recency."""

    def key(self, fact: dict) -> tuple:
        return (float(fact.get("confidence", 0)), int(fact.get("t_valid_from", 0)))


@dataclass
class RetrievalPolicy:
    """
    Composed policy: validity (filter) then tiebreak (rank).
    Architecturally efficient: no decay in ranking; one gate, one preference.
    """
    validity: ValidityPolicy
    tiebreak: TiebreakPolicy

    def filter_and_rank(
        self,
        candidates: list[dict],
        as_of_day: int,
    ) -> list[dict]:
        """Return valid candidates ordered by tiebreak (best first)."""
        valid = [f for f in candidates if self.validity.valid(f, as_of_day)]
        return sorted(valid, key=self.tiebreak.key, reverse=True)

    def pick(self, candidates: list[dict], as_of_day: int) -> Optional[dict]:
        """Return the single best fact content, or None."""
        ranked = self.filter_and_rank(candidates, as_of_day)
        return ranked[0] if ranked else None


def validity_only_tiebreak_policy(
    use_confidence: bool = True,
) -> RetrievalPolicy:
    """
    Recommended architecture from learning: validity as sole temporal gate,
    tiebreak by confidence then recency. No decay.
    """
    validity = IntervalValidityPolicy()
    tiebreak = ConfidenceTiebreakPolicy() if use_confidence else RecencyTiebreakPolicy()
    return RetrievalPolicy(validity=validity, tiebreak=tiebreak)


def retrieval_fn_from_policy(
    policy: RetrievalPolicy,
    get_candidates: Callable[[list[dict], str, str], list[dict]],
) -> Callable[..., Optional[str]]:
    """
    Build a retrieval function (signature compatible with run_benchmark resolvers)
    from a composed policy. Encapsulates filter → rank → pick.
    """
    def retrieve(
        facts: list[dict],
        domain: str,
        subject: str,
        as_of_day: int,
        **kwargs: object,
    ) -> Optional[str]:
        cands = get_candidates(facts, domain, subject)
        if not cands:
            return None
        picked = policy.pick(cands, as_of_day)
        return picked["content"] if picked else None
    return retrieve
