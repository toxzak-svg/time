"""
Fitness from blueprint:
  fitness = 1.5 * delta_proxy_acc + 3.0 * delta_holdout_acc
          + 1.0 * stability_score + 0.5 * novelty_score
          - 0.75 * runtime_penalty - 0.75 * gpu_penalty
Holdout term dominates; novelty for exploration only.
"""

from typing import Any


def compute_fitness(
    delta_proxy_acc: float,
    delta_holdout_acc: float,
    stability_score: float,
    novelty_score: float,
    runtime_penalty: float,
    gpu_penalty: float,
) -> float:
    return (
        1.5 * delta_proxy_acc
        + 3.0 * delta_holdout_acc
        + 1.0 * stability_score
        + 0.5 * novelty_score
        - 0.75 * runtime_penalty
        - 0.75 * gpu_penalty
    )
