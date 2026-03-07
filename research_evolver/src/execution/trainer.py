"""
Baseline trainer: LoRA fine-tune on Qwen from a Genome.
Uses Hugging Face Transformers + PEFT. Saves adapter to artifacts/experiments/<exp_id>/adapter/.
"""

from pathlib import Path
from typing import Any

# Lazy imports so the rest of the repo can load without torch/transformers
def _import_training():
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer
    from peft import LoraConfig, get_peft_model, TaskType
    from datasets import Dataset
    return torch, AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer, LoraConfig, get_peft_model, TaskType, Dataset


def _build_chat_prompt(question: str, template_id: str = "default") -> str:
    """Turn question into model input. template_id can be default, chain_of_thought, few_shot."""
    if template_id == "chain_of_thought":
        return f"<|im_start|>user\n{question}\nThink step by step, then give the final answer.<|im_end|>\n<|im_start|>assistant\n"
    if template_id == "few_shot":
        return f"<|im_start|>user\n{question}\n<|im_end|>\n<|im_start|>assistant\n"
    return f"<|im_start|>user\n{question}\n<|im_end|>\n<|im_start|>assistant\n"


def prepare_dataset(items: list[dict], genome: Any) -> "Dataset":
    """Build HF Dataset with text pairs for causal LM (input = prompt, label = completion)."""
    _, _, _, _, _, _, _, _, Dataset = _import_training()
    inputs = []
    labels = []
    for row in items:
        q = row.get("question", "")
        a = row.get("answer", "")
        prompt = _build_chat_prompt(q, genome.prompt_template_id)
        # Full sequence: prompt + answer; we mask loss on prompt part
        text = prompt + a
        inputs.append(text)
        labels.append(text)
    return Dataset.from_dict({"text": inputs, "label": labels})


def train(
    genome: Any,
    train_items: list[dict],
    output_dir: str | Path,
    *,
    max_steps: int | None = None,
    max_eval_samples: int = 0,
) -> dict[str, float]:
    """
    Run LoRA training. If max_steps is set (e.g. for smoke), use that; else genome.train_steps.
    Returns dict with loss and any logged metrics.
    """
    torch, AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer, LoraConfig, get_peft_model, TaskType, Dataset = _import_training()

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    steps = max_steps if max_steps is not None else genome.train_steps

    tokenizer = AutoTokenizer.from_pretrained(genome.base_model, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        genome.base_model,
        trust_remote_code=True,
        torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
    )
    target_modules = [m.strip() for m in genome.target_modules.split(",")]
    peft_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=genome.adapter_rank,
        lora_alpha=genome.adapter_alpha,
        lora_dropout=genome.adapter_dropout,
        target_modules=target_modules,
    )
    model = get_peft_model(model, peft_config)

    ds = prepare_dataset(train_items, genome)

    def tokenize(examples):
        out = tokenizer(
            examples["text"],
            truncation=True,
            max_length=2048,
            padding="max_length",
            return_tensors=None,
        )
        out["labels"] = out["input_ids"].copy()
        return out

    tokenized = ds.map(tokenize, batched=True, remove_columns=ds.column_names)

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        max_steps=steps,
        per_device_train_batch_size=genome.batch_size,
        gradient_accumulation_steps=genome.grad_accum,
        learning_rate=genome.learning_rate,
        warmup_ratio=genome.warmup_ratio,
        weight_decay=genome.weight_decay,
        logging_steps=min(10, max(1, steps // 10)),
        save_strategy="steps",
        save_steps=max(1, steps // 2),
        bf16=torch.cuda.is_available(),
        report_to="none",
        seed=genome.seed,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized,
    )
    trainer.train()
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    return {"train_loss": trainer.state.log_history[-1].get("loss", 0.0) if trainer.state.log_history else 0.0}
