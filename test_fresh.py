#!/usr/bin/env python3
"""Test with fresh request to avoid caching"""

import requests
import json
import time

# Test data that mimics Tactiq output
test_text = """# tactiq.io free youtube transcript
# No title found
No text

00:00:00.000 --> 00:00:03.000
I learned how to use Perplexity for you. So, here's the Cliffnotes version to save you the hours and hours that I've spent digging into this tool, which I have realized has become one of my top three AI tools that I use literally multiple times a day.

00:00:03.000 --> 00:00:06.000
People usually like to describe Perplexity as like chatbt plus search, but it is actually so much more than that.

00:00:06.000 --> 00:00:09.000
So, in this video, I'm going to show you guys the core features of Perplexity, including its intelligent search capabilities.

https://youtube.com/watch?v=test123
"""

url = "https://vidscribe2ai.site/process"
data = {
    "mode": "paste",
    "raw_transcript": test_text,
    "summary_format": "bullet_points"
}

print("Testing paste functionality with fresh request...")
print("Original text length:", len(test_text))
print("First 200 chars:", repr(test_text[:200]))

try:
    # Add timestamp to avoid caching
    response = requests.post(url, json=data, timeout=30, headers={'Cache-Control': 'no-cache'})
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("Success!")
        print("Response keys:", list(result.keys()))
        if 'metrics' in result:
            print("Metrics:", result['metrics'])
        if 'transcript' in result:
            # Extract just the cleaned text part
            transcript_html = result['transcript']
            print("Transcript HTML length:", len(transcript_html))
            print("First 800 chars of transcript HTML:")
            print(transcript_html[:800])
    else:
        print("Error response:")
        print(response.text)
        
except Exception as e:
    print(f"Error: {e}")
