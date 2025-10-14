"""Backtrader backend converter: convert Pine Script to Backtrader strategy code."""
from typing import Dict, Any
from llm_client import get_llm


"""Backtrader backend converter: convert Pine Script strategy to Backtrader Python.

This converter uses LLM to transform Pine Script strategy code into a complete
Backtrader strategy class with proper imports, parameter handling, and signal logic.
"""
from typing import Dict, Any, Optional
import os
import re
from llm_client import get_llm
from config import DEBUG_NODE_OUTPUT


def _load_backtrader_template() -> str:
    """Load backtrader conversion template/examples if available."""
    base = os.path.dirname(__file__)
    template_path = os.path.join(base, "backtrader_template.md")
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        # Return basic template if file not found
        return """
# Backtrader Strategy Template

```python
import backtrader as bt
import pandas as pd
from datetime import datetime

class PineStrategy(bt.Strategy):
    params = (
        ('period', 14),
        ('multiplier', 2.0),
    )
    
    def __init__(self):
        # Initialize indicators
        self.sma = bt.indicators.SimpleMovingAverage(self.data.close, period=self.params.period)
        
    def next(self):
        # Strategy logic
        if not self.position:
            if self.data.close[0] > self.sma[0]:
                self.buy()
        else:
            if self.data.close[0] < self.sma[0]:
                self.sell()

# Backtest runner
if __name__ == '__main__':
    cerebro = bt.Cerebro()
    cerebro.addstrategy(PineStrategy)
    
    # Add data (example with CSV)
    data = bt.feeds.YahooFinanceCSVData(dataname='data.csv')
    cerebro.adddata(data)
    
    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.001)
    
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
    cerebro.run()
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())
```
"""


def _extract_code_from_response(text: str) -> str:
    """Extract the first Python fenced code block or return the raw text."""
    # Try python fence first
    m = re.search(r"```python\s+(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    # Try generic fence
    m2 = re.search(r"```\s*(.*?)```", text, re.DOTALL)
    if m2:
        return m2.group(1).strip()
    # No fences found; return text
    return text.strip()


def convert(source_code: str, node_name: str = "code_converter", feedback: Optional[str] = None) -> Dict[str, Any]:
    """Convert Pine Script strategy to Backtrader Python strategy using LLM.

    Args:
        source_code: Original Pine Script strategy source text.
        node_name: Node name to look up model config.
        feedback: Optional validator feedback to help the LLM improve conversion.

    Returns:
        Dict with keys: converted_code (str) on success, or error (str) on failure.
    """
    template = _load_backtrader_template()

    # Build conversion prompt
    prompt_parts = [
        "You are an expert converter that transforms TradingView Pine Script strategies to Backtrader Python strategies.",
        "Convert the Pine Script strategy to a complete, runnable Backtrader strategy.",
        "Return ONLY a Python code block (triple-backticks with python) containing the converted strategy.",
        "",
        "Requirements:",
        "1. Create a class inheriting from bt.Strategy",
        "2. Convert Pine Script inputs to Backtrader params",
        "3. Convert Pine Script indicators to Backtrader indicators in __init__",
        "4. Convert strategy.entry/exit calls to self.buy/sell/close in next() method", 
        "5. Include a complete runnable example with Cerebro setup",
        "6. Handle position sizing and risk management",
        "7. Add proper imports (backtrader, pandas, datetime, etc.)",
        "",
        "Backtrader template and examples:",
        template[:3000],  # Include template guidance
        "",
        "Original Pine Script Strategy:",
        source_code[:4000],  # Limit input size
    ]

    if feedback:
        prompt_parts.extend([
            "",
            "Validator Feedback (fix these issues):",
            feedback[:2000]
        ])

    prompt = "\n".join(prompt_parts)

    try:
        llm = get_llm(node_name=node_name)
        resp = llm.invoke(prompt)
        text = getattr(resp, "content", str(resp))

        converted = _extract_code_from_response(text)

        if not converted:
            return {"converted_code": None, "error": "LLM returned empty conversion"}

        # Basic validation - check for required Backtrader elements
        required_elements = ["import backtrader", "bt.Strategy", "def __init__", "def next"]
        missing = [elem for elem in required_elements if elem not in converted]
        
        if missing:
            return {
                "converted_code": None, 
                "error": f"Converted code missing required elements: {', '.join(missing)}"
            }

        if DEBUG_NODE_OUTPUT:
            print(f"  [DEBUG] Backtrader converter: Generated {len(converted)} chars")

        return {"converted_code": converted, "llm_response": text[:1000]}

    except Exception as e:
        return {"converted_code": None, "error": str(e)}
    llm = get_llm(node_name=node_name)
    prompt = f"Convert the following Pine Script to a Backtrader strategy (Python):\n\n{source_code[:2000]}"
    try:
        resp = llm.invoke(prompt)
        return {"converted_code": resp.content, "metadata": {}}
    except Exception as e:
        return {"converted_code": None, "error": str(e)}
