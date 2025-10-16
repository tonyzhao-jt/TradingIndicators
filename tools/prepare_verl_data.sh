#!/bin/bash

# Complete Data Preparation Script for VERL Training
# This script merges parquet files and splits them into train/val sets

echo "=== VERL Data Preparation Script ==="

# Set directories and files
PROCESSED_DIR="/workspace/trading_indicators/outputs/processed"
TOOLS_DIR="/workspace/trading_indicators/preprocess/tools"
MERGED_FILE="/workspace/trading_indicators/outputs/merged_processed_data.parquet"
SPLITS_DIR="/workspace/trading_indicators/outputs/data_splits"

# Check dependencies
echo "1. Checking dependencies..."
cd "$TOOLS_DIR"

# Install required packages if not available
python -c "import sklearn" 2>/dev/null || {
    echo "Installing scikit-learn..."
    pip install scikit-learn
}

# Step 1: Merge parquet files
echo ""
echo "2. Merging parquet files..."
if [ ! -f "$MERGED_FILE" ]; then
    echo "Merging processed batch files..."
    python main.py merge "$PROCESSED_DIR" \
        --pattern "processed_batch_*.parquet" \
        --output "$MERGED_FILE"
    
    if [ $? -ne 0 ]; then
        echo "Error: Failed to merge files!"
        exit 1
    fi
else
    echo "Merged file already exists: $MERGED_FILE"
fi

# Step 2: Check merged data
echo ""
echo "3. Inspecting merged data..."
python main.py inspect "$MERGED_FILE" --head 2

# Step 3: Split data into train/val
echo ""
echo "4. Splitting data into train/validation sets..."

# For small datasets (< 10 samples), use 1 sample for validation
# For medium datasets (10-50 samples), use 20% for validation  
# For larger datasets, use 20% for validation

TOTAL_ROWS=$(python -c "import pandas as pd; df = pd.read_parquet('$MERGED_FILE'); print(len(df))")
echo "Total samples: $TOTAL_ROWS"

if [ "$TOTAL_ROWS" -lt 10 ]; then
    TRAIN_RATIO=0.9
    echo "Small dataset detected, using 90% for training"
elif [ "$TOTAL_ROWS" -lt 50 ]; then
    TRAIN_RATIO=0.8
    echo "Medium dataset detected, using 80% for training"
else
    TRAIN_RATIO=0.8
    echo "Using 80% for training"
fi

python split_data.py "$MERGED_FILE" \
    --output-dir "$SPLITS_DIR" \
    --train-ratio "$TRAIN_RATIO" \
    --seed 42

if [ $? -ne 0 ]; then
    echo "Error: Failed to split data!"
    exit 1
fi

# Step 4: Convert to VERL format
echo ""
echo "5. Converting to VERL format..."
VERL_FILE="/workspace/trading_indicators/outputs/verl_formatted_data.parquet"

python convert_to_verl.py "$MERGED_FILE" --output "$VERL_FILE"

if [ $? -ne 0 ]; then
    echo "Error: Failed to convert to VERL format!"
    exit 1
fi

# Step 5: Split VERL formatted data
echo ""
echo "6. Splitting VERL formatted data..."
python split_data.py "$VERL_FILE" \
    --output-dir "$SPLITS_DIR" \
    --train-ratio "$TRAIN_RATIO" \
    --seed 42

if [ $? -ne 0 ]; then
    echo "Error: Failed to split VERL data!"
    exit 1
fi

# Step 6: Verify splits
echo ""
echo "7. Verifying VERL data splits..."
TRAIN_FILE="$SPLITS_DIR/train.parquet"
VAL_FILE="$SPLITS_DIR/val.parquet"

if [ -f "$TRAIN_FILE" ] && [ -f "$VAL_FILE" ]; then
    echo "✓ Train file: $TRAIN_FILE"
    python main.py inspect "$TRAIN_FILE" --head 1
    
    echo ""
    echo "✓ Validation file: $VAL_FILE"  
    python main.py inspect "$VAL_FILE" --head 1
else
    echo "Error: Split files not found!"
    exit 1
fi

# Step 7: Update VERL script paths
echo ""
echo "8. Updating VERL training script paths..."
VERL_SCRIPT="/workspace/trading_indicators/posttrain/pt_verl.sh"

if [ -f "$VERL_SCRIPT" ]; then
    # Update paths in VERL script
    sed -i "s|data.train_files=.*|data.train_files=$TRAIN_FILE \\\\|g" "$VERL_SCRIPT"
    sed -i "s|data.val_files=.*|data.val_files=$VAL_FILE \\\\|g" "$VERL_SCRIPT"
    echo "✓ Updated VERL script with new data paths"
else
    echo "Warning: VERL script not found at $VERL_SCRIPT"
fi

echo ""
echo "=== Data Preparation Complete ==="
echo "Summary:"
echo "  - Merged file: $MERGED_FILE"
echo "  - Train file: $TRAIN_FILE"
echo "  - Val file: $VAL_FILE"
echo "  - Total samples: $TOTAL_ROWS"
echo ""
echo "You can now run VERL training with:"
echo "  cd /workspace/trading_indicators/posttrain"
echo "  ./pt_verl.sh"