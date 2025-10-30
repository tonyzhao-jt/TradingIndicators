"""
FSDP Training Script with Accelerate for Pine Script Code Generation
Uses Fully Sharded Data Parallel for efficient multi-GPU training
"""

from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments
from trl import SFTTrainer
from datasets import Dataset
import json
import argparse
import torch
from formatter import FormatterFactory


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Train Pine Script Code Generation Model with FSDP")
    
    # Data arguments
    parser.add_argument(
        "--data_path",
        type=str,
        default="/workspace/trading_indicators/outputs/segments_20251014.json",
        help="Path to the training data JSON file"
    )
    
    # Model arguments
    parser.add_argument(
        "--model_name",
        type=str,
        default="Qwen/Qwen2.5-Coder-7B",
        help="Model name or path for training"
    )
    parser.add_argument(
        "--max_seq_length",
        type=int,
        default=4096,
        help="Maximum sequence length"
    )
    
    # Formatter arguments
    parser.add_argument(
        "--formatter_type",
        type=str,
        default="instruction",
        choices=["instruction", "conversation", "chatml", "alpaca", "simple"],
        help="Type of formatter to use"
    )
    parser.add_argument(
        "--instruction_text",
        type=str,
        default="Generate Pine Script v6 code based on the following trading strategy description.",
        help="Instruction text for formatter (instruction type only)"
    )
    
    # Training arguments
    parser.add_argument("--output_dir", type=str, default="./pine-coder-fsdp", help="Output directory")
    parser.add_argument("--batch_size", type=int, default=2, help="Batch size per device")
    parser.add_argument("--gradient_accumulation_steps", type=int, default=4, help="Gradient accumulation steps")
    parser.add_argument("--learning_rate", type=float, default=1e-5, help="Learning rate")
    parser.add_argument("--num_epochs", type=int, default=3, help="Number of training epochs")
    parser.add_argument("--warmup_steps", type=int, default=100, help="Number of warmup steps")
    parser.add_argument("--logging_steps", type=int, default=10, help="Logging frequency")
    parser.add_argument("--save_steps", type=int, default=500, help="Save checkpoint frequency")
    parser.add_argument("--bf16", action="store_true", help="Use bfloat16 precision")
    parser.add_argument("--fp16", action="store_true", help="Use float16 precision")
    parser.add_argument("--gradient_checkpointing", action="store_true", help="Enable gradient checkpointing")
    
    return parser.parse_args()


def main():
    # Parse arguments
    args = parse_args()
    
    print("="*80)
    print("FSDP TRAINING CONFIGURATION")
    print("="*80)
    print(f"Data path: {args.data_path}")
    print(f"Model: {args.model_name}")
    print(f"Max sequence length: {args.max_seq_length}")
    print(f"Formatter type: {args.formatter_type}")
    print(f"Output directory: {args.output_dir}")
    print(f"Batch size per device: {args.batch_size}")
    print(f"Gradient accumulation: {args.gradient_accumulation_steps}")
    print(f"Learning rate: {args.learning_rate}")
    print(f"Number of epochs: {args.num_epochs}")
    print(f"Mixed precision: {'bf16' if args.bf16 else 'fp16' if args.fp16 else 'fp32'}")
    print("="*80 + "\n")
    
    # 1. Load data
    print("Loading training data...")
    with open(args.data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"Loaded {len(data)} training samples\n")
    
    # 2. Create formatter
    print("Creating formatter...")
    if args.formatter_type == "instruction":
        formatter = FormatterFactory.create_formatter(
            "instruction",
            instruction_text=args.instruction_text,
            description_header="Description:",
            code_header="Code:"
        )
    else:
        formatter = FormatterFactory.create_formatter(args.formatter_type)
    
    # 3. Format dataset
    print("Formatting training data...")
    formatted_data = formatter.format_dataset(data)
    train_dataset = Dataset.from_list(formatted_data)
    
    # 4. Validate format
    print("\n" + "="*80)
    print("SAMPLE FORMAT VALIDATION")
    print("="*80)
    sample_text = formatted_data[0]["text"]
    print(sample_text[:500] + "..." if len(sample_text) > 500 else sample_text)
    print("="*80 + "\n")
    
    # 5. Load tokenizer
    print(f"Loading tokenizer: {args.model_name}")
    tokenizer = AutoTokenizer.from_pretrained(
        args.model_name,
        model_max_length=args.max_seq_length,
        padding_side="right",
        truncation_side="right",
        trust_remote_code=True,
    )
    
    # Set padding token BEFORE loading model
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    print(f"Tokenizer loaded. Vocab size: {len(tokenizer)}")
    print(f"PAD token: {tokenizer.pad_token} (ID: {tokenizer.pad_token_id})")
    print(f"EOS token: {tokenizer.eos_token} (ID: {tokenizer.eos_token_id})")
    print(f"BOS token: {tokenizer.bos_token} (ID: {tokenizer.bos_token_id})\n")
    
    # 6. Load model
    print(f"Loading model: {args.model_name}")
    model = AutoModelForCausalLM.from_pretrained(
        args.model_name,
        trust_remote_code=True,
        torch_dtype=torch.bfloat16 if args.bf16 else (torch.float16 if args.fp16 else torch.float32),
    )
    
    # Sync tokenizer config with model
    model.config.pad_token_id = tokenizer.pad_token_id
    if hasattr(model, 'generation_config'):
        model.generation_config.pad_token_id = tokenizer.pad_token_id
    
    print(f"Model loaded. Parameters: {model.num_parameters():,}")
    print(f"Model dtype: {model.dtype}\n")
    
    # 7. Setup training arguments with FSDP
    print("Setting up training arguments with FSDP...")
    training_args = TrainingArguments(
        # Basic settings
        output_dir=args.output_dir,
        num_train_epochs=args.num_epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        
        # Optimization
        learning_rate=args.learning_rate,
        warmup_steps=args.warmup_steps,
        lr_scheduler_type="cosine",
        weight_decay=0.01,
        max_grad_norm=1.0,
        
        # Mixed precision
        bf16=args.bf16,
        fp16=args.fp16,
        
        # Memory optimization
        gradient_checkpointing=args.gradient_checkpointing,
        gradient_checkpointing_kwargs={"use_reentrant": False} if args.gradient_checkpointing else None,
        
        # Logging and saving
        logging_steps=args.logging_steps,
        save_steps=args.save_steps,
        save_total_limit=3,
        logging_first_step=True,
        report_to=["tensorboard"],
        
        # Data loading
        dataloader_drop_last=True,
        dataloader_num_workers=4,
        dataloader_pin_memory=True,
        
        # Distributed training (FSDP will be configured via accelerate config)
        ddp_find_unused_parameters=False,
        
        # Other
        seed=42,
        remove_unused_columns=False,
    )
    
    # 8. Create SFT Trainer
    print("Creating SFT Trainer...")
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        processing_class=tokenizer,
    )
    
    # 9. Train
    print("\n" + "="*80)
    print("STARTING FSDP TRAINING")
    print("="*80)
    print(f"Total steps: {len(train_dataset) // (args.batch_size * args.gradient_accumulation_steps * torch.cuda.device_count()) * args.num_epochs}")
    print(f"Effective batch size: {args.batch_size * args.gradient_accumulation_steps * torch.cuda.device_count()}")
    print("="*80 + "\n")
    
    trainer.train()
    
    # 10. Save final model
    print("\n" + "="*80)
    print("SAVING FINAL MODEL")
    print("="*80)
    trainer.save_model(args.output_dir + "/final")
    tokenizer.save_pretrained(args.output_dir + "/final")
    
    print(f"\nTraining completed!")
    print(f"Model saved to: {args.output_dir}/final")
    print("="*80)


if __name__ == "__main__":
    main()
