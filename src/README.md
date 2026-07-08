# TTA core: diagnoser & integrator

Learning here is **architectural efficiency**, not just bug fixing.

## Diagnoser (`src/diagnoser`)

- **architecture.py**: Describes retrieval systems in terms of *concerns* (validity, ranking, decay, tiebreak). Diagnoses **redundancy** (e.g. validity + decay both affecting outcome), **mixed concerns** (decay conflated with tiebreak), and **composability** (duplicated logic across systems).
- **signals.py**: Turns benchmark results (e.g. C > D on v3/v4, ablation drops) into **architectural signals** (simpler_beats_full, staleness_eliminated_by_validity, etc.) and then into diagnoses. So learning is driven by *what the metrics say about design*, not only “this run failed.”

## Integrator (`src/integrator`)

- **policy.py**: Composable **ValidityPolicy** (single gate: is fact valid at query time?) and **TiebreakPolicy** (how to choose among valid facts). **RetrievalPolicy** composes them: filter then rank. No decay in ranking—architecturally efficient.
- **learning.py**: Maps diagnoser output to **ArchitecturalChange** (replace_policy, extract_shared, separate_concern). Produces the recommended **validity-only + tiebreak** policy so the system can adopt it (e.g. D_revised) instead of one-off bug fixes.

## Usage

- Run the pipeline on existing results:
  ```bash
  python scripts/architectural_learning.py
  ```
- In code: use `result_to_signals()` and `signals_to_diagnoses()` on your result rows; then `integrate_diagnoses()` to get `ArchitecturalChange` list and optional `validity_only_tiebreak_policy()` for retrieval.
