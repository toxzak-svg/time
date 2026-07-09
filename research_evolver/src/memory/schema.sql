-- Research Evolution v1 — SQLite schema (blueprint)

-- One row per experiment instance
CREATE TABLE IF NOT EXISTS experiments (
  experiment_id TEXT PRIMARY KEY,
  generation INTEGER NOT NULL,
  lineage_id TEXT,
  stage TEXT,
  status TEXT,
  genome_json TEXT NOT NULL,
  fitness REAL,
  created_at TEXT DEFAULT (datetime('now'))
);

-- All stage metrics and per-seed results
CREATE TABLE IF NOT EXISTS metrics (
  experiment_id TEXT NOT NULL,
  split TEXT,
  metric_name TEXT,
  metric_value REAL,
  seed INTEGER,
  PRIMARY KEY (experiment_id, split, metric_name, seed),
  FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id)
);

-- Field-level child changes vs parents
CREATE TABLE IF NOT EXISTS mutations (
  child_id TEXT NOT NULL,
  parent_id TEXT NOT NULL,
  mutation_type TEXT,
  field_name TEXT,
  old_value TEXT,
  new_value TEXT,
  delta_fitness REAL,
  PRIMARY KEY (child_id, parent_id, field_name),
  FOREIGN KEY (child_id) REFERENCES experiments(experiment_id),
  FOREIGN KEY (parent_id) REFERENCES experiments(experiment_id)
);

-- Lineage ancestry and improvement slope
CREATE TABLE IF NOT EXISTS lineages (
  lineage_id TEXT PRIMARY KEY,
  founder_id TEXT NOT NULL,
  best_experiment_id TEXT,
  generations_alive INTEGER DEFAULT 0,
  stagnation_count INTEGER DEFAULT 0,
  FOREIGN KEY (founder_id) REFERENCES experiments(experiment_id),
  FOREIGN KEY (best_experiment_id) REFERENCES experiments(experiment_id)
);

-- Index logs, adapters, reports on disk
CREATE TABLE IF NOT EXISTS artifacts (
  experiment_id TEXT NOT NULL,
  artifact_type TEXT,
  path TEXT NOT NULL,
  sha256 TEXT,
  PRIMARY KEY (experiment_id, artifact_type),
  FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id)
);

-- Roll-up for dashboard and reporting
CREATE TABLE IF NOT EXISTS generation_summary (
  generation INTEGER PRIMARY KEY,
  population_size INTEGER,
  stage1_pass_count INTEGER,
  stage2_pass_count INTEGER,
  stage3_pass_count INTEGER,
  best_fitness REAL,
  total_cost REAL,
  created_at TEXT DEFAULT (datetime('now'))
);
