import sys, traceback, os, json
sys.path.insert(0, r'C:\Users\Zwmar\.openclaw\workspace\projects\time')
from research_evolver.src.core.baseline_genome import get_baseline_genome
from research_evolver.src.execution.data_loader import load_train
from pathlib import Path
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer
from peft import LoraConfig, get_peft_model, TaskType
from datasets import Dataset

ROOT = Path(r'C:\Users\Zwmar\.openclaw\workspace\projects\time')
data_dir = ROOT / 'research_evolver' / 'data'
train_data = load_train(data_dir)
genome = get_baseline_genome()
out_dir = ROOT / 'test_train2'
out_dir.mkdir(parents=True, exist_ok=True)

try:
    # Minimal training test
    tokenizer = AutoTokenizer.from_pretrained(genome.base_model, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        genome.base_model,
        trust_remote_code=True,
        torch_dtype=torch.float32,
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
    
    # Prepare dataset
    def build_prompt(q):
        return f"<|im_start|>user\n{q}<|im_end|>\n<|im_start|>assistant\n"
    
    texts = [build_prompt(item['question']) + item['answer'] for item in train_data]
    ds = Dataset.from_dict({"text": texts})
    
    def tokenize(examples):
        out = tokenizer(examples["text"], truncation=True, max_length=512, padding="max_length", return_tensors=None)
        out["labels"] = out["input_ids"].copy()
        return out
    
    tokenized = ds.map(tokenize, batched=True, remove_columns=ds.column_names)
    
    training_args = TrainingArguments(
        output_dir=str(out_dir),
        max_steps=2,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=1,
        learning_rate=genome.learning_rate,
        warmup_ratio=genome.warmup_ratio,
        weight_decay=genome.weight_decay,
        logging_steps=1,
        save_steps=1,
        bf16=False,
        fp16=False,
        report_to="none",
        seed=genome.seed,
        disable_tqdm=True,
    )
    
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized,
    )
    
    print("Starting training...")
    trainer.train()
    print("Training complete!")
    
    with open(ROOT / 'train_result.json', 'w') as f:
        json.dump({'success': True, 'result': trainer.state.log_history[-1] if trainer.state.log_history else {}}, f)
    print('SUCCESS')
except Exception as e:
    err_file = ROOT / 'train_error.txt'
    with open(err_file, 'w') as f:
        f.write(str(e) + '\n')
        traceback.print_exc(file=f)
    print('ERROR:', e)
    sys.exit(1)
