"""
Mutation operators for v1 (blueprint):
- Numeric local: learning_rate, critique_threshold, warmup_ratio, dropout, synthetic_data_ratio
- Discrete swap: filter_strategy, curriculum_strategy, prompt_template_id, target_modules
- Ordinal step: adapter_rank, adapter_alpha, train_steps, batch_size, grad_accum, temperature, top_p
- Boolean toggle: critique_enabled
- Constraint repair: applied in repair_genome via search_space
"""

import random
from dataclasses import asdict
from typing import Any

from .genome import Genome, repair_genome
from .baseline_genome import get_baseline_genome

# Mutatable field groups (must exist on Genome and in search_space)
NUMERIC_FIELDS = ["learning_rate", "critique_threshold", "warmup_ratio", "adapter_dropout", "synthetic_data_ratio", "weight_decay"]
DISCRETE_FIELDS = ["filter_strategy", "curriculum_strategy", "prompt_template_id", "target_modules"]
ORDINAL_FIELDS = ["adapter_rank", "adapter_alpha", "train_steps", "batch_size", "grad_accum", "temperature", "top_p", "max_new_tokens"]
BOOLEAN_FIELDS = ["critique_enabled"]


def _get_parsed_search_space() -> dict:
    from research_evolver.src.utils.config_loader import load_search_space
    from research_evolver.src.utils.search_space import parse_search_space
    return parse_search_space(load_search_space())


def mutate_numeric(g: Genome, field: str, rng: random.Random, scale: float = 0.2) -> Genome:
    """Perturb numeric field: multiply by (1 ± scale) or add small noise, then repair."""
    parsed = _get_parsed_search_space()
    spec = parsed.get(field)
    if not spec or spec.get("kind") != "float":
        return repair_genome(g, parsed)
    d = asdict(g)
    val = d[field]
    try:
        v = float(val)
    except (TypeError, ValueError):
        return repair_genome(g, parsed)
    if rng.random() < 0.5:
        v *= rng.uniform(1 - scale, 1 + scale)
    else:
        v += rng.gauss(0, (spec["max"] - spec["min"]) * 0.05)
    d[field] = v
    return repair_genome(Genome(**d), parsed)


def mutate_discrete(g: Genome, field: str, rng: random.Random) -> Genome:
    """Swap to a different value from choices (exclude current)."""
    parsed = _get_parsed_search_space()
    spec = parsed.get(field)
    choices = spec.get("values", []) if spec and spec.get("kind") == "choices" else []
    if not choices:
        return repair_genome(g, parsed)
    d = asdict(g)
    current = d.get(field)
    others = [c for c in choices if c != current]
    if not others:
        return g
    d[field] = rng.choice(others)
    return repair_genome(Genome(**d), parsed)


def mutate_ordinal_step(g: Genome, field: str, rng: random.Random, step: int = 1) -> Genome:
    """Move to previous/next value in ordered choices."""
    parsed = _get_parsed_search_space()
    spec = parsed.get(field)
    choices = spec.get("values", []) if spec and spec.get("kind") == "choices" else []
    if not choices:
        return repair_genome(g, parsed)
    d = asdict(g)
    current = d.get(field)
    try:
        i = choices.index(current)
    except (ValueError, TypeError):
        d[field] = rng.choice(choices)
        return repair_genome(Genome(**d), parsed)
    direction = rng.choice([-1, 1])
    ni = max(0, min(len(choices) - 1, i + direction * step))
    d[field] = choices[ni]
    return repair_genome(Genome(**d), parsed)


def mutate_boolean(g: Genome, field: str) -> Genome:
    """Toggle boolean field."""
    parsed = _get_parsed_search_space()
    d = asdict(g)
    d[field] = not d[field]
    return repair_genome(Genome(**d), parsed)


def spawn_mutant(parent: Genome, rng: random.Random) -> Genome:
    """Apply one random mutation (numeric, discrete, ordinal, or boolean); return repaired child."""
    parsed = _get_parsed_search_space()
    candidates: list[tuple[str, callable]] = []
    for f in NUMERIC_FIELDS:
        if f in parsed and parsed[f].get("kind") == "float":
            candidates.append((f, lambda g, r, fn=f: mutate_numeric(g, fn, r)))
    for f in DISCRETE_FIELDS:
        if f in parsed and parsed[f].get("kind") == "choices":
            candidates.append((f, lambda g, r, fn=f: mutate_discrete(g, fn, r)))
    for f in ORDINAL_FIELDS:
        if f in parsed and parsed[f].get("kind") == "choices":
            candidates.append((f, lambda g, r, fn=f: mutate_ordinal_step(g, fn, r)))
    for f in BOOLEAN_FIELDS:
        if f in parsed:
            candidates.append((f, lambda g, r, fn=f: mutate_boolean(g, fn)))
    if not candidates:
        return parent
    field, mut_fn = rng.choice(candidates)
    return mut_fn(parent, rng)


def spawn_random_immigrant(rng: random.Random) -> Genome:
    """Sample a random genome around the baseline (small random mutations or baseline with varied seed)."""
    baseline = get_baseline_genome()
    # 1–3 mutations from baseline
    n_mutations = rng.randint(1, 3)
    g = baseline
    for _ in range(n_mutations):
        g = spawn_mutant(g, rng)
    # Vary seed
    parsed = _get_parsed_search_space()
    if "seed" in parsed and parsed["seed"].get("kind") == "choices":
        d = asdict(g)
        d["seed"] = rng.choice(parsed["seed"].get("values", [42, 43, 44]))
        g = repair_genome(Genome(**d), parsed)
    return g


def spawn_children(
    parents: list[Genome],
    n_children: int,
    n_random_immigrants: int,
    rng: random.Random,
) -> list[Genome]:
    """Spawn n_children via mutation from parents, plus n_random_immigrants. Total = n_children + n_random_immigrants."""
    children: list[Genome] = []
    for _ in range(n_children):
        parent = rng.choice(parents)
        children.append(spawn_mutant(parent, rng))
    for _ in range(n_random_immigrants):
        children.append(spawn_random_immigrant(rng))
    return children


def spawn_children_with_parent_indices(
    parents: list[Genome],
    n_children: int,
    n_random_immigrants: int,
    rng: random.Random,
) -> list[tuple[Genome, int | None]]:
    """Like spawn_children but returns (genome, parent_index). parent_index is None for random immigrants."""
    out: list[tuple[Genome, int]] = []
    for _ in range(n_children):
        idx = rng.randint(0, len(parents) - 1) if parents else 0
        parent = parents[idx] if parents else get_baseline_genome()
        out.append((spawn_mutant(parent, rng), idx))
    for _ in range(n_random_immigrants):
        out.append((spawn_random_immigrant(rng), None))
    return out


def crossover(a: Genome, b: Genome, rng: random.Random) -> Genome:
    """Uniform crossover: each field from a or b at random; then repair."""
    from dataclasses import asdict
    from .genome import repair_genome
    parsed = _get_parsed_search_space()
    da = asdict(a)
    db = asdict(b)
    dc = {}
    for k in da:
        dc[k] = db[k] if k in db and rng.random() < 0.5 else da[k]
    return repair_genome(Genome(**dc), parsed)


def spawn_children_with_crossover(
    parents: list[Genome],
    n_children: int,
    n_random_immigrants: int,
    rng: random.Random,
    crossover_fraction: float = 0.2,
) -> list[tuple[Genome, int | None]]:
    """Spawn children: crossover_fraction via crossover of two parents, rest via mutation. Returns (genome, parent_index). parent_index for crossover is first parent index."""
    out: list[tuple[Genome, int | None]] = []
    n_crossover = int(n_children * crossover_fraction)
    n_mutant = n_children - n_crossover
    for _ in range(n_crossover):
        if len(parents) >= 2:
            i, j = rng.sample(range(len(parents)), 2)
            out.append((crossover(parents[i], parents[j], rng), i))
        else:
            idx = rng.randint(0, len(parents) - 1) if parents else 0
            parent = parents[idx] if parents else get_baseline_genome()
            out.append((spawn_mutant(parent, rng), idx))
    for _ in range(n_mutant):
        idx = rng.randint(0, len(parents) - 1) if parents else 0
        parent = parents[idx] if parents else get_baseline_genome()
        out.append((spawn_mutant(parent, rng), idx))
    for _ in range(n_random_immigrants):
        out.append((spawn_random_immigrant(rng), None))
    return out


def novelty_score(genome: Genome, archive: list[Genome]) -> float:
    """
    Placeholder: behavioral/genome novelty vs archive. Returns 0.0 (no archive) or simple distance.
    Can be extended to use proxy eval outcomes or embedding distance.
    """
    if not archive:
        return 0.0
    from dataclasses import asdict
    d = asdict(genome)
    best = 0.0
    for other in archive:
        do = asdict(other)
        diff = sum(1 for k in d if do.get(k) != d.get(k))
        best = max(best, diff / max(1, len(d)))
    return best
