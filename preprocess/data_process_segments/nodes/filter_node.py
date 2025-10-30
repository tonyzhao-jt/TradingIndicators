"""
Filter Node - Filter small code snippets and duplicate content
"""

import re
from typing import List, Dict, Set
from collections import defaultdict


class FilterNode:
    def __init__(self):
        self.name = "filter_node"
        self.min_code_length = 10  # Minimum code length
        self.min_description_length = 20  # Minimum description length
    
    def process(self, segments: List[Dict]) -> List[Dict]:
        """Process segments and apply filters"""
        print(f"FilterNode: Processing {len(segments)} segments")
        
        # Step 1: Remove small/no code snippets
        valid_segments = self.filter_small_code(segments)
        print(f"FilterNode: After removing small code: {len(valid_segments)} segments")
        
        # Step 2: Remove duplicates
        unique_segments = self.filter_duplicates(valid_segments)
        print(f"FilterNode: After removing duplicates: {len(unique_segments)} segments")
        
        return unique_segments
    
    def filter_small_code(self, segments: List[Dict]) -> List[Dict]:
        """Filter out segments with small or no code"""
        valid_segments = []
        
        for segment in segments:
            # Handle both string and list outputs
            output = segment.get('output', '')
            if isinstance(output, list):
                # Join list items into a single string
                code = '\n'.join(str(item) for item in output).strip()
            elif isinstance(output, str):
                code = output.strip()
            else:
                # Skip segments with unexpected output types
                continue
            
            description = segment.get('input', '').strip()
            
            # Check if code is too small or contains only comments/notes
            if not self.is_valid_code(code):
                continue
            
            # Check if description is meaningful
            if len(description) < self.min_description_length:
                continue
            
            valid_segments.append(segment)
        
        return valid_segments
    
    def is_valid_code(self, code: str) -> bool:
        """Check if code is valid and substantial"""
        if not code or len(code.strip()) < self.min_code_length:
            return False
        
        # Remove comments and whitespace to check actual code content
        code_lines = []
        for line in code.split('\n'):
            line = line.strip()
            if line and not line.startswith('//') and not line.startswith('#'):
                # Remove inline comments
                if '//' in line:
                    line = line.split('//')[0].strip()
                if '#' in line and not line.startswith('#'):
                    line = line.split('#')[0].strip()
                if line:
                    code_lines.append(line)
        
        actual_code = '\n'.join(code_lines).strip()
        
        # Check for note-only content
        if any(keyword in code.lower() for keyword in ['note:', 'note that', 'if the price of', 'deleverage', 'protect yourself']):
            return False
        
        # Must have some actual code-like content
        if len(actual_code) < self.min_code_length:
            return False
        
        # Should contain some programming constructs
        programming_indicators = ['=', '(', ')', '.', 'ta.', 'close', 'open', 'high', 'low', 'sma', 'ema', 'rsi']
        has_programming_content = any(indicator in actual_code for indicator in programming_indicators)
        
        return has_programming_content
    
    def filter_duplicates(self, segments: List[Dict]) -> List[Dict]:
        """Filter out duplicate segments, keeping the best one from each group"""
        # Group by normalized code
        code_groups = defaultdict(list)
        
        for segment in segments:
            # Handle both string and list outputs for normalization
            output = segment.get('output', '')
            if isinstance(output, list):
                code = '\n'.join(str(item) for item in output)
            elif isinstance(output, str):
                code = output
            else:
                code = str(output)
            
            normalized_code = self.normalize_code(code)
            code_groups[normalized_code].append(segment)
        
        # Keep one representative from each group
        unique_segments = []
        for code_group in code_groups.values():
            if len(code_group) == 1:
                unique_segments.append(code_group[0])
            else:
                # Keep the one with the best description (longest and most detailed)
                best_segment = max(code_group, key=lambda s: len(s['input']))
                unique_segments.append(best_segment)
        
        return unique_segments
    
    def normalize_code(self, code: str) -> str:
        """Normalize code for duplicate detection"""
        # Remove whitespace, comments, and normalize variable names
        normalized = re.sub(r'\s+', ' ', code.strip())
        normalized = re.sub(r'//.*?\n', '', normalized)
        normalized = re.sub(r'#.*?\n', '', normalized)
        
        return normalized.lower()