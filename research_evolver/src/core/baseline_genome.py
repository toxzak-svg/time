"""
Locked baseline genome for v1. All improvement is measured against this.
Single canonical baseline so the evolution loop has a fixed reference.
"""

from .genome import Genome


def get_baseline_genome() -> Genome:
    """Return the locked baseline experiment recipe (v1)."""
    return Genome(
        task_family="small_model_reasoning",
        base_model="Qwen/Qwen2.5-1.5B-Instruct",
        synthetic_data_ratio=0.8,
        prompt_template_id="default",
        filter_strategy="none",
        critique_enabled=False,
        critique_threshold=0.7,
        curriculum_strategy="uniform",
        adapter_rank=8,
        adapter_alpha=16,
        adapter_dropout=0.05,
        target_modules="q_proj,v_proj,k_proj,o_proj",
        learning_rate=2e-5,
        batch_size=8,
        grad_accum=2,
        train_steps=400,
        warmup_ratio=0.06,
        weight_decay=0.01,
        temperature=0.7,
        top_p=0.95,
        max_new_tokens=512,
        proxy_eval_size=200,
        confirmation_eval_size=500,
        seed=42,
    )
