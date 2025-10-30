from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments
from trl import SFTTrainer
from datasets import Dataset
import json
import argparse
from formatter import FormatterFactory, load_and_format_data


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Train Pine Script Code Generation Model")
    
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
        default=2048,
        help="Maximum sequence length (run token checker to determine optimal value)"
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
    parser.add_argument(
        "--output_dir",
        type=str,
        default="./pine-coder",
        help="Output directory for trained model"
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=2,
        help="Per device train batch size"
    )
    parser.add_argument(
        "--gradient_accumulation_steps",
        type=int,
        default=4,
        help="Gradient accumulation steps"
    )
    parser.add_argument(
        "--learning_rate",
        type=float,
        default=1e-5,
        help="Learning rate"
    )
    parser.add_argument(
        "--num_epochs",
        type=int,
        default=3,
        help="Number of training epochs"
    )
    parser.add_argument(
        "--logging_steps",
        type=int,
        default=10,
        help="Logging steps"
    )
    parser.add_argument(
        "--save_steps",
        type=int,
        default=500,
        help="Save checkpoint steps"
    )
    parser.add_argument(
        "--warmup_steps",
        type=int,
        default=100,
        help="Warmup steps"
    )
    parser.add_argument(
        "--fp16",
        action="store_true",
        help="Use FP16 training"
    )
    parser.add_argument(
        "--gradient_checkpointing",
        action="store_true",
        default=True,
        help="Use gradient checkpointing"
    )
    
    return parser.parse_args()


def main():
    # Parse arguments
    args = parse_args()
    
    print("="*80)
    print("TRAINING CONFIGURATION")
    print("="*80)
    print(f"Data path: {args.data_path}")
    print(f"Model: {args.model_name}")
    print(f"Max sequence length: {args.max_seq_length}")
    print(f"Formatter type: {args.formatter_type}")
    print(f"Output directory: {args.output_dir}")
    print(f"Batch size: {args.batch_size}")
    print(f"Learning rate: {args.learning_rate}")
    print(f"Number of epochs: {args.num_epochs}")
    print("="*80 + "\n")
    
    # 1. Load your data
    print("Loading training data...")
    with open(args.data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"Loaded {len(data)} training samples\n")
    
    # 2. Create formatter instance
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
    
    # 3. Prepare training data using formatter
    print("Formatting training data...")
    formatted_data = formatter.format_dataset(data)
    train_dataset = Dataset.from_list(formatted_data)
    
    # 4. Validate data format
    print("\n" + "="*80)
    print("SAMPLE FORMAT VALIDATION")
    print("="*80)
    sample_text = formatted_data[0]["text"]
    print(sample_text[:500] + "..." if len(sample_text) > 500 else sample_text)
    print("="*80 + "\n")
    
    # 5. Load model and tokenizer
    print(f"Loading model and tokenizer: {args.model_name}")
    tokenizer = AutoTokenizer.from_pretrained(
        args.model_name,
        model_max_length=args.max_seq_length,
        padding_side="right",
        truncation_side="right",
        trust_remote_code=True,
    )
    
    # Set padding token if needed BEFORE loading model
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    model = AutoModelForCausalLM.from_pretrained(
        args.model_name,
        trust_remote_code=True,
    )
    
    # Ensure model config matches tokenizer
    model.config.pad_token_id = tokenizer.pad_token_id
    model.generation_config.pad_token_id = tokenizer.pad_token_id
    
    print("Model and tokenizer loaded successfully\n")
    
    # 6. Training parameters
    print("Setting up training parameters...")
    training_args = TrainingArguments(
        output_dir=args.output_dir,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        num_train_epochs=args.num_epochs,
        logging_steps=args.logging_steps,
        save_steps=args.save_steps,
        fp16=args.fp16,
        gradient_checkpointing=args.gradient_checkpointing,
        dataloader_drop_last=True,
        warmup_steps=args.warmup_steps,
        # FSDP Configuration for efficient multi-GPU training
        fsdp="full_shard auto_wrap",
        # Save only on main process to avoid conflicts
        save_only_model=True,
        # Distributed settings
        ddp_find_unused_parameters=False,
    )
    
    # 7. Create trainer
    print("Creating trainer...")
    # Note: Dataset already has "text" field from formatter.format_dataset()
    # SFTTrainer will automatically use the "text" field
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        processing_class=tokenizer,
    )
    
    # 8. Start training
    print("\n" + "="*80)
    print("STARTING TRAINING")
    print("="*80)
    trainer.train()
    
    # 9. Save model
    print("\n" + "="*80)
    print("SAVING MODEL")
    print("="*80)
    trainer.save_model()
    print(f"Model saved to: {args.output_dir}")
    print("\nTraining complete!")


if __name__ == "__main__":
    main()