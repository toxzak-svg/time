"""
Genome: one experimental recipe. v1 scope per research_evolution_implementation_blueprint.
Repair rules must run after every mutation; invalid combinations never reach the runner.
"""

from dataclasses import dataclass, asdict
import json
from typing import Any


@dataclass
class Genome:
    """Single experiment recipe. All fields serializable for DB and mutation."""

    # Identity (locked in v1)
    task_family: str
    base_model: str

    # Data — main source of method-level variation
    synthetic_data_ratio: float
    prompt_template_id: str
    filter_strategy: str
    critique_enabled: bool
    critique_threshold: float
    curriculum_strategy: str

    # Adapter / training
    adapter_rank: int
    adapter_alpha: int
    adapter_dropout: float
    target_modules: str
    learning_rate: float
    batch_size: int
    grad_accum: int
    train_steps: int
    warmup_ratio: float
    weight_decay: float

    # Decoding
    temperature: float
    top_p: float
    max_new_tokens: int

    # Control
    proxy_eval_size: int
    confirmation_eval_size: int
    seed: int

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Genome":
        return cls(**{k: d[k] for k in cls.__dataclass_fields__ if k in d})

    @classmethod
    def from_json(cls, s: str) -> "Genome":
        return cls.from_dict(json.loads(s))


def repair_genome(g: Genome, search_space: dict) -> Genome:
    """
    Apply repair rules so invalid genome combinations never reach the runner.
    search_space: parsed spec dict (field -> {kind, min/max or values}), from parse_search_space(raw).
    """
    from research_evolver.src.utils.search_space import clamp_float, snap_to_choice

    d = asdict(g)
    for field, spec in search_space.items():
        if field not in d:
            continue
        if spec.get("kind") == "locked":
            d[field] = spec["value"]
        elif spec.get("kind") == "float":
            try:
                d[field] = clamp_float(float(d[field]), spec)
            except (TypeError, ValueError):
                pass
        elif spec.get("kind") == "choices":
            d[field] = snap_to_choice(d[field], spec)
    return Genome(**d)
