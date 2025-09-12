#!/usr/bin/env python3
"""Test YouTube URL to debug 500 error"""

import requests
import json

# Test with a simple YouTube URL
url = "https://vidscribe2ai.site/process"
data = {
    "mode": "youtube",
    "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Rick Roll - should have captions
    "summary_format": "bullet_points"
}

print("Testing YouTube URL to debug 500 error...")

try:
    response = requests.post(url, json=data, timeout=30)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("Success!")
        print("Response keys:", list(result.keys()))
        if 'metrics' in result:
            print("Metrics:", result['metrics'])
    elif response.status_code == 429:
        print("Rate limited - this is expected")
        error_data = response.json()
        print("Error:", error_data.get('error', 'Unknown'))
        print("Fixes:", error_data.get('fixes', []))
    else:
        print("Error response:")
        print(response.text)
        
except Exception as e:
    print(f"Error: {e}")
