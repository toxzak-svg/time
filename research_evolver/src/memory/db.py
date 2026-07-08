"""
SQLite experiment store, artifact index, learned success model.
Persistent history and searchable metadata.
"""

import sqlite3
from pathlib import Path
from typing import Any

# Schema path relative to this file
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def get_connection(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())
    conn.commit()


def insert_experiment(
    conn: sqlite3.Connection,
    experiment_id: str,
    generation: int,
    lineage_id: str | None,
    stage: str,
    status: str,
    genome_json: str,
    fitness: float | None = None,
) -> None:
    conn.execute(
        """INSERT INTO experiments
           (experiment_id, generation, lineage_id, stage, status, genome_json, fitness)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (experiment_id, generation, lineage_id, stage, status, genome_json, fitness),
    )
    conn.commit()


def insert_metrics(
    conn: sqlite3.Connection,
    experiment_id: str,
    split: str,
    metrics: dict[str, float],
    seed: int = 0,
) -> None:
    """Record metrics for an experiment (e.g. proxy accuracy, holdout accuracy)."""
    for name, value in metrics.items():
        conn.execute(
            """INSERT OR REPLACE INTO metrics
               (experiment_id, split, metric_name, metric_value, seed)
               VALUES (?, ?, ?, ?, ?)""",
            (experiment_id, split, name, value, seed),
        )
    conn.commit()


def get_experiments_by_generation_stage(
    conn: sqlite3.Connection,
    generation: int,
    stage: str,
    *,
    order_by_fitness_desc: bool = True,
    limit: int | None = None,
) -> list[tuple[str, str, float | None]]:
    """Return (experiment_id, genome_json, fitness) for generation+stage."""
    order = "DESC" if order_by_fitness_desc else "ASC"
    q = (
        "SELECT experiment_id, genome_json, fitness FROM experiments "
        "WHERE generation = ? AND stage = ? ORDER BY fitness " + order
    )
    if limit is not None:
        q += " LIMIT " + str(int(limit))
    cur = conn.execute(q, (generation, stage))
    return [(r[0], r[1], r[2]) for r in cur.fetchall()]


def update_experiment_stage_fitness(
    conn: sqlite3.Connection,
    experiment_id: str,
    stage: str,
    fitness: float | None,
) -> None:
    conn.execute(
        "UPDATE experiments SET stage = ?, fitness = ? WHERE experiment_id = ?",
        (stage, fitness, experiment_id),
    )
    conn.commit()


def insert_generation_summary(
    conn: sqlite3.Connection,
    generation: int,
    population_size: int,
    stage1_pass_count: int,
    stage2_pass_count: int,
    stage3_pass_count: int,
    best_fitness: float | None,
    total_cost: float = 0.0,
) -> None:
    conn.execute(
        """INSERT OR REPLACE INTO generation_summary
           (generation, population_size, stage1_pass_count, stage2_pass_count, stage3_pass_count, best_fitness, total_cost)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (generation, population_size, stage1_pass_count, stage2_pass_count, stage3_pass_count, best_fitness, total_cost),
    )
    conn.commit()


def get_best_survivors(
    conn: sqlite3.Connection,
    generation: int,
    stage: str,
    limit: int,
) -> list[tuple[str, str, float | None]]:
    """Return top experiments by fitness for use as parents of next generation."""
    return get_experiments_by_generation_stage(
        conn, generation, stage, order_by_fitness_desc=True, limit=limit
    )


def upsert_lineage(
    conn: sqlite3.Connection,
    lineage_id: str,
    founder_id: str,
    best_experiment_id: str | None,
    generations_alive: int,
    stagnation_count: int = 0,
) -> None:
    conn.execute(
        """INSERT INTO lineages (lineage_id, founder_id, best_experiment_id, generations_alive, stagnation_count)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(lineage_id) DO UPDATE SET
             best_experiment_id = excluded.best_experiment_id,
             generations_alive = excluded.generations_alive,
             stagnation_count = excluded.stagnation_count""",
        (lineage_id, founder_id, best_experiment_id, generations_alive, stagnation_count),
    )
    conn.commit()


def get_generation_summaries(conn: sqlite3.Connection) -> list[tuple]:
    """Return all generation_summary rows: (generation, population_size, s1_pass, s2_pass, s3_pass, best_fitness, total_cost)."""
    cur = conn.execute(
        "SELECT generation, population_size, stage1_pass_count, stage2_pass_count, stage3_pass_count, best_fitness, total_cost FROM generation_summary ORDER BY generation"
    )
    return cur.fetchall()


def get_all_lineages(conn: sqlite3.Connection) -> list[tuple]:
    """Return (lineage_id, founder_id, best_experiment_id, generations_alive, stagnation_count)."""
    cur = conn.execute(
        "SELECT lineage_id, founder_id, best_experiment_id, generations_alive, stagnation_count FROM lineages ORDER BY generations_alive DESC, lineage_id"
    )
    return cur.fetchall()


def get_experiment(conn: sqlite3.Connection, experiment_id: str) -> tuple | None:
    """Return (experiment_id, generation, lineage_id, stage, status, genome_json, fitness, created_at) or None."""
    cur = conn.execute(
        "SELECT experiment_id, generation, lineage_id, stage, status, genome_json, fitness, created_at FROM experiments WHERE experiment_id = ?",
        (experiment_id,),
    )
    return cur.fetchone()
