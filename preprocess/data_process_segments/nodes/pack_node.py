"""
Pack Node - 提取restructured_data下的segments，转换为input-output格式
"""

import json
from typing import List, Dict, Any


class PackNode:
    def __init__(self):
        self.name = "pack_node"
    
    def process(self, data_list: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Process data list and extract segments"""
        print(f"PackNode: Processing {len(data_list)} items")
        
        segments = self.pack_segments(data_list)
        
        print(f"PackNode: Generated {len(segments)} segments")
        return segments
    
    def pack_segments(self, data_list):
        """Pack restructured_data into segment-wise samples"""
        segments = []
        
        # Handle both direct data list and data with metadata/results structure
        items_to_process = []
        
        if isinstance(data_list, dict) and 'results' in data_list:
            # If data has metadata/results structure
            items_to_process = data_list['results']
        elif isinstance(data_list, list):
            items_to_process = data_list
        else:
            print("Warning: Unknown data format")
            return segments
        
        for item in items_to_process:
            if 'restructured_data' not in item:
                continue
                
            restructured_data = item['restructured_data']
            item_id = item.get('id', item.get('raw_data', {}).get('preview_title', 'unknown'))
            
            for key, segment in restructured_data.items():
                if isinstance(segment, dict) and 'description' in segment and 'code' in segment:
                    segment_sample = {
                        'source_id': item_id,
                        'segment_key': key,
                        'input': segment['description'],
                        'output': segment['code']
                    }
                    segments.append(segment_sample)
        
        return segments