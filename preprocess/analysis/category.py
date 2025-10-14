import json
import re
from pathlib import Path
from typing import List, Dict, Any

PLOT_PATTERNS = re.compile(r"\b(plot|plotshape|plotchar|plotarrow|hline|bgcolor|barcolor|fill|line\.new|box\.new|label\.new)\s*\(", re.I)
ORDER_PATTERNS = re.compile(r"\b(strategy\.entry|strategy\.order|strategy\.exit|strategy\.close|strategy\s*\()", re.I)


def classify_item(item: Dict[str, Any]) -> Dict[str, Any]:
    code = (item.get('source_code') or '')
    desc = (item.get('description') or '')
    name = item.get('name') or item.get('preview_title') or item.get('id')

    typ = 'unknown'
    if re.search(r"\bstrategy\s*\(", code, re.I) or re.search(r"@strategy", code, re.I):
        typ = 'strategy'
    elif re.search(r"\bindicator\s*\(", code, re.I) or re.search(r"@indicator", code, re.I):
        typ = 'indicator'
    else:
        if re.search(r"strategy\.entry|strategy\.order|strategy\.exit|strategy\.close", code, re.I):
            typ = 'strategy'
        elif PLOT_PATTERNS.search(code):
            typ = 'indicator'

    has_plots = bool(PLOT_PATTERNS.search(code))
    has_orders = bool(ORDER_PATTERNS.search(code))

    return {
        'id': item.get('id'),
        'name': name,
        'type': typ,
        'has_plots': has_plots,
        'has_orders': has_orders,
        'desc_words': len(desc.split()),
    }


def analyze_file(json_path: str, out_json: str = None) -> Dict[str, Any]:
    p = Path(json_path)
    data = json.loads(p.read_text(encoding='utf-8'))

    results = [classify_item(it) for it in data]

    summary = {
        'total': len(results),
        'strategy': sum(1 for r in results if r['type'] == 'strategy'),
        'indicator': sum(1 for r in results if r['type'] == 'indicator'),
        'unknown': sum(1 for r in results if r['type'] == 'unknown'),
        'with_plots': sum(1 for r in results if r['has_plots']),
        'with_orders': sum(1 for r in results if r['has_orders']),
    }

    out = {'summary': summary, 'items': results}

    if out_json:
        Path(out_json).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')

    return out
