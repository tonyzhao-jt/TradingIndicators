#!/bin/bash

# Test if the compare app can be imported and basic checks

echo "Testing Model Comparison App..."
echo "================================"

# Check Python version
echo "Python version:"
python --version

# Check required packages
echo ""
echo "Checking required packages..."
python -c "
import sys
try:
    import streamlit
    print(f'✅ streamlit: {streamlit.__version__}')
except ImportError:
    print('❌ streamlit not found')
    sys.exit(1)

try:
    import torch
    print(f'✅ torch: {torch.__version__}')
    print(f'   CUDA available: {torch.cuda.is_available()}')
    if torch.cuda.is_available():
        print(f'   CUDA devices: {torch.cuda.device_count()}')
        for i in range(torch.cuda.device_count()):
            print(f'   GPU {i}: {torch.cuda.get_device_name(i)}')
except ImportError:
    print('❌ torch not found')
    sys.exit(1)

try:
    import transformers
    print(f'✅ transformers: {transformers.__version__}')
except ImportError:
    print('❌ transformers not found')
    sys.exit(1)

try:
    import accelerate
    print(f'✅ accelerate: {accelerate.__version__}')
except ImportError:
    print('⚠️ accelerate not found (optional)')

try:
    import bitsandbytes
    print(f'✅ bitsandbytes: {bitsandbytes.__version__}')
except ImportError:
    print('⚠️ bitsandbytes not found (needed for quantization)')

print('')
print('✅ All critical packages found!')
"

# Check if the app file exists and can be imported
echo ""
echo "Checking app file..."
if [ -f "compare_models_app.py" ]; then
    echo "✅ compare_models_app.py exists"
    
    # Try to parse the Python file
    python -c "import ast; ast.parse(open('compare_models_app.py').read())" && echo "✅ Python syntax is valid" || echo "❌ Python syntax error"
else
    echo "❌ compare_models_app.py not found"
    exit 1
fi

echo ""
echo "================================"
echo "Test complete! Ready to run:"
echo "  bash run_compare_app.sh"
echo "================================"
