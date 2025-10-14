"""Node: classify

Classifies incoming raw items as 'strategy' or 'indicator' and sets
state['rejected']=True with reason when it's an indicator (current policy).
"""
from typing import Dict, Any
import os
import sys
import re
from pathlib import Path

# Add the analysis module to the path
analysis_dir = Path(__file__).parent.parent.parent / "analysis"
if str(analysis_dir) not in sys.path:
    sys.path.insert(0, str(analysis_dir))

from category import classify_item


def run(state: Dict[str, Any]) -> Dict[str, Any]:
    # Extract raw data from state
    item = state.get('raw_data', {})
    cls = classify_item(item)

    # Policy: only keep strategies, reject indicators and unknown
    if cls['type'] == 'strategy':
        return {
            'classification': cls,
            'status': 'passed_classification'
        }
    else:
        reject_reason = f"Detected {cls['type']} — policy: only process strategies"
        return {
            'classification': cls,
            'status': 'rejected_by_classifier',
            'error_message': reject_reason
        }
