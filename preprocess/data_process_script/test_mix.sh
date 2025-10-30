#!/bin/bash
# Test mix_dataset.py with sample data

set -e  # Exit on error

echo "Testing Dataset Mixer..."
echo ""

# Create test directory
TEST_DIR="./test_outputs/mix_test"
mkdir -p "$TEST_DIR"

# Create sample script dataset
cat > "$TEST_DIR/sample_script.json" << 'EOF'
[
  {
    "input": "This is a script description 1",
    "output": "// Script code 1\nstrategy(\"Test 1\")"
  },
  {
    "input": "This is a script description 2",
    "output": "// Script code 2\nstrategy(\"Test 2\")"
  },
  {
    "input": "This is a script description 3",
    "output": "// Script code 3\nstrategy(\"Test 3\")"
  },
  {
    "input": "This is a script description 4",
    "output": "// Script code 4\nstrategy(\"Test 4\")"
  }
]
EOF

# Create sample segment dataset
cat > "$TEST_DIR/sample_segment.json" << 'EOF'
[
  {
    "input": "This is a segment description 1",
    "output": "// Segment code 1\nvar x = 1"
  },
  {
    "input": "This is a segment description 2",
    "output": "// Segment code 2\nvar x = 2"
  },
  {
    "input": "This is a segment description 3",
    "output": "// Segment code 3\nvar x = 3"
  },
  {
    "input": "This is a segment description 4",
    "output": "// Segment code 4\nvar x = 4"
  },
  {
    "input": "This is a segment description 5",
    "output": "// Segment code 5\nvar x = 5"
  },
  {
    "input": "This is a segment description 6",
    "output": "// Segment code 6\nvar x = 6"
  }
]
EOF

echo "Created sample datasets:"
echo "  Script: $TEST_DIR/sample_script.json (4 samples)"
echo "  Segment: $TEST_DIR/sample_segment.json (6 samples)"
echo ""

# Test 1: 50-50 mix (default)
echo "================================"
echo "Test 1: 50-50 Mix (Default)"
echo "================================"
python mix_dataset.py \
    --script "$TEST_DIR/sample_script.json" \
    --segment "$TEST_DIR/sample_segment.json" \
    --ratio 0.5 \
    --output "$TEST_DIR" \
    --seed 42

echo ""

# Test 2: 30-70 mix
echo "================================"
echo "Test 2: 30-70 Mix"
echo "================================"
python mix_dataset.py \
    --script "$TEST_DIR/sample_script.json" \
    --segment "$TEST_DIR/sample_segment.json" \
    --ratio 0.3 \
    --output "$TEST_DIR" \
    --seed 42

echo ""

# Test 3: 80-20 mix, no shuffle
echo "================================"
echo "Test 3: 80-20 Mix (No Shuffle)"
echo "================================"
python mix_dataset.py \
    --script "$TEST_DIR/sample_script.json" \
    --segment "$TEST_DIR/sample_segment.json" \
    --ratio 0.8 \
    --output "$TEST_DIR" \
    --no-shuffle \
    --seed 42

echo ""

# Test 4: 100% script
echo "================================"
echo "Test 4: 100% Script"
echo "================================"
python mix_dataset.py \
    --script "$TEST_DIR/sample_script.json" \
    --segment "$TEST_DIR/sample_segment.json" \
    --ratio 1.0 \
    --output "$TEST_DIR" \
    --seed 42

echo ""

# Test 5: 0% script (100% segment)
echo "================================"
echo "Test 5: 100% Segment"
echo "================================"
python mix_dataset.py \
    --script "$TEST_DIR/sample_script.json" \
    --segment "$TEST_DIR/sample_segment.json" \
    --ratio 0.0 \
    --output "$TEST_DIR" \
    --seed 42

echo ""
echo "================================"
echo "All Tests Completed!"
echo "================================"
echo "Check output files in: $TEST_DIR"
echo ""
ls -lh "$TEST_DIR"/*.json | grep mixed
