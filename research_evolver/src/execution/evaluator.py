"""
Evaluate a trained run: load base model + adapter, run on eval split, compute accuracy.
Accuracy = exact match or normalized match (strip, lower) of model answer vs expected.
"""

from pathlib import Path
from typing import Any


def _normalize_answer(s: str) -> str:
    return " ".join(s.strip().lower().split())


def _import_eval():
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel
    return torch, AutoModelForCausalLM, AutoTokenizer, PeftModel


def load_model_and_adapter(base_model: str, adapter_path: str | Path, device: str | None = None):
    """Load base model and PEFT adapter. Return model, tokenizer."""
    torch, AutoModelForCausalLM, AutoTokenizer, PeftModel = _import_eval()
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    tokenizer = AutoTokenizer.from_pretrained(adapter_path, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        trust_remote_code=True,
        torch_dtype=torch.bfloat16 if device == "cuda" else torch.float32,
    )
    model = PeftModel.from_pretrained(model, str(adapter_path))
    model = model.to(device)
    model.eval()
    return model, tokenizer, device


def _generate_one(model, tokenizer, question: str, genome: Any, device: str) -> str:
    from transformers import GenerationConfig
    torch, _, _, _ = _import_eval()
    prompt = _build_prompt(question, genome.prompt_template_id)
    inputs = tokenizer(prompt, return_tensors="pt").to(device)
    gen = model.generate(
        **inputs,
        max_new_tokens=genome.max_new_tokens,
        do_sample=True,
        temperature=genome.temperature,
        top_p=genome.top_p,
        pad_token_id=tokenizer.eos_token_id,
    )
    full = tokenizer.decode(gen[0], skip_special_tokens=True)
    # Answer is after the assistant turn
    if "<|im_start|>assistant" in full:
        answer = full.split("<|im_start|>assistant")[-1].strip()
    else:
        answer = full[len(prompt):].strip()
    return answer


def _build_prompt(question: str, template_id: str) -> str:
    if template_id == "chain_of_thought":
        return f"<|im_start|>user\n{question}\nThink step by step, then give the final answer.<|im_end|>\n<|im_start|>assistant\n"
    return f"<|im_start|>user\n{question}\n<|im_end|>\n<|im_start|>assistant\n"


def evaluate(
    genome: Any,
    adapter_path: str | Path,
    eval_items: list[dict],
    *,
    exact_match: bool = False,
    device: str | None = None,
) -> dict[str, float]:
    """
    Run inference on eval_items; compare model output to expected answer.
    Returns {"accuracy": float}. Optional "accuracy_exact" if exact_match=True.
    """
    model, tokenizer, device = load_model_and_adapter(genome.base_model, adapter_path, device)
    correct = 0
    correct_exact = 0
    n = len(eval_items)
    if n == 0:
        return {"accuracy": 0.0, "accuracy_exact": 0.0}

    for item in eval_items:
        question = item.get("question", item.get("input", ""))
        expected = item.get("answer", item.get("output", ""))
        pred = _generate_one(model, tokenizer, question, genome, device)
        if exact_match:
            if _normalize_answer(pred) == _normalize_answer(expected):
                correct += 1
            if pred.strip() == expected.strip():
                correct_exact += 1
        else:
            if _normalize_answer(pred) == _normalize_answer(expected):
                correct += 1

    out = {"accuracy": correct / n}
    if exact_match:
        out["accuracy_exact"] = correct_exact / n
    return out
