#!/usr/bin/env python3
"""
Debug script to find segments with actual content
"""

import json
from nodes.pack_node import PackNode

# Load the data
with open('../../outputs/segments_20251014.json', 'r') as f:
    data = json.load(f)

# Use PackNode to process the data
pack_node = PackNode()
segments = pack_node.process(data)

print(f"Generated {len(segments)} segments")

# Find segments with actual content
content_segments = []
list_segments = []

for i, segment in enumerate(segments):
    if isinstance(segment, dict):
        output = segment.get('output', '')
        if isinstance(output, list):
            list_segments.append((i, segment))
            print(f"Found LIST segment at index {i}: {output}")
        elif isinstance(output, str) and len(output.strip()) > 0:
            content_segments.append((i, segment))

print(f"\nFound {len(content_segments)} segments with actual string content")
print(f"Found {len(list_segments)} segments with list content")

if content_segments:
    print(f"\nFirst content segment (index {content_segments[0][0]}):")
    seg = content_segments[0][1]
    print(f"  Input: {seg['input'][:100]}...")
    print(f"  Output type: {type(seg['output'])}")
    print(f"  Output: {seg['output'][:200]}...")

if list_segments:
    print(f"\nFirst list segment (index {list_segments[0][0]}):")
    seg = list_segments[0][1]
    print(f"  Input: {seg['input'][:100]}...")
    print(f"  Output type: {type(seg['output'])}")
    print(f"  Output: {seg['output']}")