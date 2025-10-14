"""Backtrader backend validator: validate converted Backtrader strategy by running backtest.

This validator attempts to execute the converted Backtrader strategy with sample data
to verify it runs without errors and produces reasonable results.
"""
from typing import Dict, Any
import tempfile
import os
import subprocess
import sys
import pandas as pd
from datetime import datetime, timedelta
from llm_client import get_llm
from config import USE_LLM_VALIDATION, DEBUG_NODE_OUTPUT


def _generate_sample_data() -> str:
    """Generate sample OHLCV data for backtesting."""
    # Generate 100 days of sample data
    dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
    
    # Simple random walk for prices
    import numpy as np
    np.random.seed(42)  # Reproducible data
    
    base_price = 100.0
    returns = np.random.normal(0.001, 0.02, 100)  # 0.1% daily return, 2% volatility
    prices = [base_price]
    
    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))
    
    # Generate OHLCV from close prices
    data = []
    for i, (date, close) in enumerate(zip(dates, prices)):
        high = close * (1 + abs(np.random.normal(0, 0.01)))
        low = close * (1 - abs(np.random.normal(0, 0.01)))
        open_price = close * (1 + np.random.normal(0, 0.005))
        volume = int(np.random.normal(1000000, 200000))
        
        data.append({
            'Date': date.strftime('%Y-%m-%d'),
            'Open': round(open_price, 2),
            'High': round(high, 2),
            'Low': round(low, 2),
            'Close': round(close, 2),
            'Volume': volume
        })
    
    df = pd.DataFrame(data)
    return df.to_csv(index=False)


def _create_backtest_wrapper(strategy_code: str) -> str:
    """Wrap strategy code with backtest runner that captures results."""
    # Indent the strategy code properly
    indented_code = '\n'.join('    ' + line for line in strategy_code.split('\n') if line.strip())
    
    wrapper = f"""
import sys
import io
import traceback
import backtrader as bt
import pandas as pd
from datetime import datetime
from io import StringIO

# Redirect stdout to capture results
original_stdout = sys.stdout
sys.stdout = StringIO()

try:
    # Strategy code (properly indented)
{indented_code}

    # Backtest execution
    cerebro = bt.Cerebro()
    
    # Find strategy class in the code
    import inspect
    strategy_class = None
    local_vars = dict(locals())  # Create a snapshot to avoid "dictionary changed" error
    for name, obj in local_vars.items():
        if (inspect.isclass(obj) and 
            issubclass(obj, bt.Strategy) and 
            obj != bt.Strategy):
            strategy_class = obj
            break
    
    if not strategy_class:
        raise Exception("No Strategy class found")
        
    cerebro.addstrategy(strategy_class)
    
    # Add sample data - create a simple data feed with enough data for indicators
    import numpy as np
    dates = pd.date_range('2023-01-01', periods=50, freq='D')  # More data for indicators
    np.random.seed(42)
    prices = 100 + np.cumsum(np.random.randn(50) * 0.1)
    
    data_df = pd.DataFrame({{
        'open': prices,
        'high': prices * 1.01,
        'low': prices * 0.99,
        'close': prices,
        'volume': [1000000] * 50
    }}, index=dates)
    
    try:
        data = bt.feeds.PandasData(dataname=data_df)
        cerebro.adddata(data)
        
        cerebro.broker.setcash(100000.0)
        cerebro.broker.setcommission(commission=0.001)
        
        start_value = cerebro.broker.getvalue()
        result = cerebro.run()
        end_value = cerebro.broker.getvalue()
        
        # Data cleanup not needed for pandas data
        
        print(f"BACKTEST_SUCCESS: Start={{start_value:.2f}}, End={{end_value:.2f}}, Return={{(end_value/start_value-1)*100:.2f}}%")
        
    except Exception as e:
        print(f"BACKTEST_ERROR: {{str(e)}}")
        
except Exception as e:
    print(f"STRATEGY_ERROR: {{str(e)}}")
    traceback.print_exc()

# Get captured output
captured_output = sys.stdout.getvalue()
sys.stdout = original_stdout
print(captured_output)
"""
    return wrapper


def validate(original_code: str, converted_code: str, node_name: str = "code_validator") -> Dict[str, Any]:
    """Validate Backtrader strategy by running a backtest.

    Args:
        original_code: Original Pine Script strategy source.
        converted_code: Converted Backtrader strategy code.
        node_name: Node name for LLM config.

    Returns:
        Dict with validation result and reason.
    """
    
    # First, basic syntax check
    try:
        compile(converted_code, '<strategy>', 'exec')
    except SyntaxError as e:
        return {"valid": False, "reason": f"Syntax error: {str(e)}"}
    except Exception as e:
        return {"valid": False, "reason": f"Compilation error: {str(e)}"}

    # Create wrapped backtest code
    test_code = _create_backtest_wrapper(converted_code)
    
    # Run backtest in subprocess
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_code)
            test_file = f.name
        
        try:
            # Run with timeout
            result = subprocess.run(
                [sys.executable, test_file],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=os.getcwd()
            )
            
            output = result.stdout + result.stderr
            
            if DEBUG_NODE_OUTPUT:
                print(f"  [DEBUG] Backtest output: {output[:500]}...")
            
            # Check for success indicators
            if "BACKTEST_SUCCESS" in output:
                # Extract return information
                success_match = None
                for line in output.split('\n'):
                    if "BACKTEST_SUCCESS" in line:
                        success_match = line
                        break
                
                return {
                    "valid": True, 
                    "reason": f"Backtest completed successfully. {success_match if success_match else ''}"
                }
            
            elif "BACKTEST_ERROR" in output or "STRATEGY_ERROR" in output:
                # Extract error message
                error_lines = [line for line in output.split('\n') 
                             if 'ERROR:' in line or 'Traceback' in line]
                error_msg = ' '.join(error_lines[:3]) if error_lines else output[:200]
                return {"valid": False, "reason": f"Backtest failed: {error_msg}"}
            
            elif result.returncode != 0:
                return {"valid": False, "reason": f"Execution failed with code {result.returncode}: {output[:200]}"}
            
            else:
                return {"valid": False, "reason": f"Backtest did not complete properly: {output[:200]}"}
                
        finally:
            # Clean up temp file
            os.unlink(test_file)
            
    except subprocess.TimeoutExpired:
        return {"valid": False, "reason": "Backtest timeout (>30s) - strategy may have infinite loop"}
    except Exception as e:
        return {"valid": False, "reason": f"Validation execution error: {str(e)}"}
    
    # Fallback to LLM validation if enabled
    if USE_LLM_VALIDATION:
        try:
            llm = get_llm(node_name=node_name)
            prompt = (
                "Validate if the converted Backtrader strategy is semantically equivalent to the original Pine Script.\n\n"
                f"Original Pine (truncated):\n{original_code[:1000]}\n\n"
                f"Converted Backtrader (truncated):\n{converted_code[:1000]}\n\n"
                "Answer YES/NO and provide brief reasoning."
            )
            resp = llm.invoke(prompt)
            text = resp.content.upper()
            valid = "YES" in text
            return {"valid": valid, "reason": f"LLM validation: {resp.content}"}
        except Exception as e:
            return {"valid": False, "reason": f"LLM validation failed: {str(e)}"}
    
    return {"valid": False, "reason": "No validation method succeeded"}
