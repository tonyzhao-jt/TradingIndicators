#!/usr/bin/env python3
"""
Debug script to examine the structure of segments data
"""

import json
from nodes.pack_node import PackNode

# Load the data
with open('../../outputs/segments_20251014.json', 'r') as f:
    data = json.load(f)

print(f"Data type: {type(data)}")
print(f"Data keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")

# Use PackNode to process the data
pack_node = PackNode()
segments = pack_node.process(data)

print(f"\nGenerated {len(segments)} segments")

# Examine first few segments
for i, segment in enumerate(segments[:5]):
    print(f"\nSegment {i+1}:")
    print(f"  Type: {type(segment)}")
    print(f"  Keys: {list(segment.keys()) if isinstance(segment, dict) else 'N/A'}")
    
    if isinstance(segment, dict):
        output = segment.get('output', 'NOT_FOUND')
        print(f"  Output type: {type(output)}")
        print(f"  Output length: {len(output) if hasattr(output, '__len__') else 'N/A'}")
        if isinstance(output, list):
            print(f"  Output first few items: {output[:3]}")
        elif isinstance(output, str):
            print(f"  Output preview: {repr(output[:100])}")
        else:
            print(f"  Output value: {output}")