"""
Turn benchmark results into architectural signals.

Maps metrics (e.g. C > D on v3/v4, ablation drops) to *architectural* hypotheses,
so learning is about design, not only "this run failed".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BenchmarkSignals:
    """
    Structured signals from benchmark results that inform architecture.
    Not raw accuracy numbers—interpretations that suggest structural changes.
    """
    simpler_beats_full: bool = False   # e.g. C > D on hard/extreme
    staleness_eliminated_by_validity: bool = False  # B/C/D all 0% staleness
    ablation_drop_no_intervals: float = 0.0   # accuracy drop when removing intervals
    ablation_drop_no_decay: float = 0.0       # accuracy change when removing decay
    overlap_heavy_benchmarks: bool = False    # v3/v4 have many overlapping facts
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_architectural_summary(self) -> list[str]:
        out: list[str] = []
        if self.simpler_beats_full:
            out.append("Simpler system (validity-only) beats full system (validity+decay) on hard benchmarks.")
        if self.staleness_eliminated_by_validity:
            out.append("Validity filtering alone eliminates staleness; decay is not required for correctness.")
        if self.ablation_drop_no_intervals > 0.2:
            out.append("Truth intervals are critical; removing them causes large accuracy drop.")
        if self.ablation_drop_no_decay <= 0 and self.simpler_beats_full:
            out.append("Decay does not help and can hurt; prefer validity + tiebreak only.")
        if self.overlap_heavy_benchmarks and self.simpler_beats_full:
            out.append("On overlap-heavy benchmarks, decay hurts (prefers newer over older-but-valid).")
        return out


def result_to_signals(
    main_results: list[dict[str, Any]],
    ablation_results: list[dict[str, Any]] | None = None,
    benchmark_version: str = "v3",
) -> BenchmarkSignals:
    """
    Convert result tables (e.g. from run_benchmark) into BenchmarkSignals.
    main_results: list of rows with keys like system, TemporalAccuracy, StalenessErrorRate, TRS.
    ablation_results: optional rows for D, D_no_decay, D_no_intervals, D_no_rerank.
    """
    def get(row: dict, key: str, default: float = 0.0) -> float:
        v = row.get(key)
        if v is None:
            return default
        try:
            return float(v)
        except (TypeError, ValueError):
            return default

    by_system = {r["system"]: r for r in main_results if "system" in r}
    acc_c = get(by_system.get("C", {}), "TemporalAccuracy")
    acc_d = get(by_system.get("D", {}), "TemporalAccuracy")
    staleness_b = get(by_system.get("B", {}), "StalenessErrorRate")
    staleness_c = get(by_system.get("C", {}), "StalenessErrorRate")
    staleness_d = get(by_system.get("D", {}), "StalenessErrorRate")

    simpler_beats = acc_c > acc_d
    staleness_ok = staleness_b == 0 and staleness_c == 0 and staleness_d == 0
    overlap_heavy = benchmark_version in ("v3", "v4")

    ablation_drop_intervals = 0.0
    ablation_drop_decay = 0.0
    if ablation_results:
        by_abl = {r["system"]: r for r in ablation_results if "system" in r}
        acc_d_full = get(by_abl.get("D", {}), "TemporalAccuracy")
        acc_no_int = get(by_abl.get("D_no_intervals", {}), "TemporalAccuracy")
        acc_no_decay = get(by_abl.get("D_no_decay", {}), "TemporalAccuracy")
        ablation_drop_intervals = max(0.0, acc_d_full - acc_no_int)
        ablation_drop_decay = acc_d_full - acc_no_decay  # can be negative (decay hurts)

    return BenchmarkSignals(
        simpler_beats_full=simpler_beats,
        staleness_eliminated_by_validity=staleness_ok,
        ablation_drop_no_intervals=ablation_drop_intervals,
        ablation_drop_no_decay=ablation_drop_decay,
        overlap_heavy_benchmarks=overlap_heavy,
        evidence={
            "TemporalAccuracy_C": acc_c,
            "TemporalAccuracy_D": acc_d,
            "benchmark_version": benchmark_version,
        },
    )


def signals_to_diagnoses(signals: BenchmarkSignals) -> list[dict[str, str]]:
    """
    Map benchmark signals to concrete architectural diagnoses (for integrator).
    Returns list of dicts with keys: kind, component, message, suggestion.
    """
    from .architecture import Diagnosis

    diagnoses: list[Diagnosis] = []
    if signals.simpler_beats_full and signals.overlap_heavy_benchmarks:
        diagnoses.append(Diagnosis(
            kind="redundancy",
            component="D",
            message="On overlap-heavy benchmarks, decay downweights older valid facts; C (validity-only) wins.",
            suggestion="Remove decay from ranking; use validity window as single temporal gate; tiebreak by confidence/recency.",
            severity="high",
            evidence=signals.evidence,
        ))
    if signals.staleness_eliminated_by_validity:
        diagnoses.append(Diagnosis(
            kind="separation",
            component="all_temporal",
            message="Staleness is eliminated by validity filtering; decay does not add correctness.",
            suggestion="Treat decay as optional preference, not part of correctness; keep validity as sole gate.",
            severity="medium",
            evidence=signals.evidence,
        ))
    if signals.ablation_drop_no_intervals > 0.2:
        diagnoses.append(Diagnosis(
            kind="composability",
            component="D_no_intervals",
            message="Removing truth intervals causes large accuracy drop; intervals are essential.",
            suggestion="Preserve validity intervals as core primitive; do not merge with decay.",
            severity="high",
            evidence=signals.evidence,
        ))
    return [
        {"kind": d.kind, "component": d.component, "message": d.message, "suggestion": d.suggestion}
        for d in diagnoses
    ]
