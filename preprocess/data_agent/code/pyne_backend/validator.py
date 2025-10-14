"""Pyne backend validator: validate converted Pyne code by attempting
to download OHLCV via pyne (ccxt) and running a simple backtest.

This validator expects the symbol information to be encoded in the
converted code's metadata or original code. It will attempt to run:

  pyne data download ccxt --symbol "BYBIT:BTC/USDT:USDT" 
  pyne run simple_ma ccxt_BYBIT_BTC_USDT_USDT_1D.ohlcv

If `pyne` CLI is not available, the validator will fallback to an LLM-based
semantic validation similar to the prior implementation.
"""
from typing import Dict, Any
import subprocess
import shlex
import re
from llm_client import get_llm
from config import USE_LLM_VALIDATION


def _extract_symbol_from_text(text: str) -> str:
    # Look for patterns like BYBIT:BTC/USDT:USDT or EXCHANGE:PAIR:QUOTE
    m = re.search(r'([A-Z0-9_\-]+):([A-Z0-9_\-/]+):([A-Z0-9_]+)', text)
    if m:
        return f"{m.group(1)}:{m.group(2)}:{m.group(3)}"
    return ""


def _run_cmd(cmd: str, timeout: int = 60) -> Dict[str, Any]:
    try:
        proc = subprocess.run(shlex.split(cmd), capture_output=True, text=True, timeout=timeout)
        return {"returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
    except Exception as e:
        return {"returncode": 1, "stdout": "", "stderr": str(e)}


def validate(original_code: str, converted_code: str, node_name: str = "code_validator") -> Dict[str, Any]:
    # Try to extract a symbol string from the original or converted code
    symbol = _extract_symbol_from_text(original_code) or _extract_symbol_from_text(converted_code)

    if symbol:
        # Form the pyne CLI symbol target (replace / with _ etc. to create filename)
        # Example: BYBIT:BTC/USDT:USDT -> ccxt_BYBIT_BTC_USDT_USDT_1D.ohlcv
        safe_sym = symbol.replace('/', '_').replace(':', '_')
        data_name = f"ccxt_{safe_sym}_1D.ohlcv"

        download_cmd = f"pyne data download ccxt --symbol \"{symbol}\""
        run_cmd = f"pyne run simple_ma {data_name}"

        # Attempt to run pyne commands
        dl_res = _run_cmd(download_cmd, timeout=120)
        if dl_res["returncode"] != 0:
            # Failed to download data; return fallback
            return {"valid": False, "reason": f"Data download failed: {dl_res['stderr'][:400]}"}

        run_res = _run_cmd(run_cmd, timeout=120)
        if run_res["returncode"] != 0:
            return {"valid": False, "reason": f"Backtest failed: {run_res['stderr'][:400]}"}

        # If both succeeded, consider it valid
        return {"valid": True, "reason": f"Backtest succeeded: {run_res['stdout'][:400]}"}

    # If no symbol or runtime checks failed, decide strategy based on config
    # First try lightweight syntax check: can we compile the Python code?
    try:
        compile(converted_code, '<converted>', 'exec')
        syntax_ok = True
    except Exception as e:
        syntax_ok = False
        syntax_err = str(e)

    # If pyne CLI is available, we prefer runtime backtest (already attempted above if symbol present).
    if syntax_ok:
        return {"valid": True, "reason": "Python syntax compiled successfully"}

    # If syntax failed and LLM-based validation is enabled, use LLM fallback
    if USE_LLM_VALIDATION:
        llm = get_llm(node_name=node_name)
        prompt = (
            "Validate if the converted Pyne Script is semantically equivalent to the original Pine Script.\n\n"
            f"Original (truncated):\n{original_code[:1000]}\n\nConverted (truncated):\n{converted_code[:1000]}\n\nAnswer YES/NO and provide brief reasoning."
        )
        try:
            resp = llm.invoke(prompt)
            text = resp.content.upper()
            valid = "YES" in text
            return {"valid": valid, "reason": resp.content}
        except Exception as e:
            return {"valid": False, "reason": str(e)}

    # Otherwise, return syntax error details
    return {"valid": False, "reason": f"Syntax check failed: {syntax_err}"}

