"""Pyne backend converter: convert Pine Script to PyneCore-style Python by
prompting the LLM.

This converter uses the project's `convert_ref.md` guidance and asks the
configured LLM to perform the conversion. The converter accepts optional
validator feedback to improve subsequent attempts.
"""
from typing import Dict, Any, Optional
import os
import re
from llm_client import get_llm
from config import NODE_MODELS, DEBUG_NODE_OUTPUT


def _load_conversion_reference() -> str:
    """Load the local conversion reference (convert_ref.md) if available."""
    base = os.path.dirname(__file__)
    ref_path = os.path.join(base, "convert_ref.md")
    try:
        with open(ref_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""  # not fatal; prompt will still include minimal instruction


def _extract_code_from_response(text: str) -> str:
    """Extract the first Python fenced code block or return the raw text.

    The LLM is instructed to return a fenced python block; this helper
    extracts the contents between the first ```python ... ``` or ``` ... ```
    fences. If none found, return the whole text (best-effort).
    """
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
    """Convert Pine Script text to a PyneCore Python script string using the LLM.

    Args:
        source_code: Original Pine Script source text.
        node_name: Node name to look up model config.
        feedback: Optional validator feedback to help the LLM improve conversion.

    Returns:
        Dict with keys: converted_code (str) on success, or error (str) on failure.
    """
    ref = _load_conversion_reference()

    # Build a clear instruction prompt
    prompt_parts = [
        "You are an expert converter that converts TradingView Pine Script (v5/6) to PyneCore Python.",
        "Follow the guidance in the convert_ref.md examples and best-practices. Produce valid, runnable PyneCore code.",
        "Return ONLY a Python code block (triple-backticks with python) containing the converted script. Do not include any commentary outside the code block.",
        "If you cannot fully convert a construct, keep a concise commented reminder in the code and explain the limitation in a special comment at the top of the code (still inside the code block).",
        "Make sure to include the @pyne header comment, required imports, the @script.indicator or @script.strategy decorator using the original name when possible, and a def main(): with the converted body.",
    ]

    if ref:
        # Include a short excerpt of the conversion reference to guide the LLM
        prompt_parts.append("Conversion guidance (excerpt):\n" + ref[:5000])

    prompt_parts.append("Original Pine Script (do not invent missing parts):\n" + source_code[:4000])

    if feedback:
        prompt_parts.append("Validator Feedback (apply these fixes or explain why they cannot be fixed):\n" + feedback[:2000])

    prompt = "\n\n".join(prompt_parts)

    try:
        llm = get_llm(node_name=node_name)
        resp = llm.invoke(prompt)
        text = getattr(resp, "content", str(resp))

        converted = _extract_code_from_response(text)

        if not converted:
            return {"converted_code": None, "error": "LLM returned empty conversion"}

        # Post-process: remove plotting-related calls that are not desired in converted scripts
        # Remove common plotting function calls to reduce visual-only code.
        def _strip_plotting(code: str) -> str:
            # Patterns to remove: plot( ... ), hline(...), plotshape(...), plotchar(...), plotarrow(...), bgcolor(...), barcolor(...), fill(...)
            # We'll do a conservative removal by removing whole lines that invoke these functions.
            lines = []
            for ln in code.splitlines():
                if re.search(r"\b(plot|hline|plotshape|plotchar|plotarrow|bgcolor|barcolor|fill)\s*\(", ln):
                    continue
                lines.append(ln)
            return "\n".join(lines).strip()

        cleaned = _strip_plotting(converted)

        # Ensure the converted string starts with @pyne header; if not, still return the cleaned content
        return {"converted_code": cleaned, "llm_response": (text[:2000])}
    except Exception as e:
        return {"converted_code": None, "error": str(e)}
