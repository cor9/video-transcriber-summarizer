#!/usr/bin/env python3
"""Simple test to isolate the issue"""

import requests
import json

# Test with minimal text
url = "https://vidscribe2ai.site/process"
data = {
    "mode": "paste",
    "raw_transcript": "This is a simple test transcript with enough text to be processed by Gemini.",
    "summary_format": "bullet_points"
}

print("Testing simple paste...")

try:
    response = requests.post(url, json=data, timeout=30)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("Success!")
        print("Response keys:", list(result.keys()))
        if 'metrics' in result:
            print("Metrics:", result['metrics'])
    else:
        print("Error response:")
        print(response.text)
        
except Exception as e:
    print(f"Error: {e}")
