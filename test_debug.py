#!/usr/bin/env python3
"""Debug the current deployment issues"""

import requests
import json
import time

# Test with clean text first
clean_text = """I learned how to use Perplexity for you. So, here's the Cliffnotes version to save you the hours and hours that I've spent digging into this tool, which I have realized has become one of my top three AI tools that I use literally multiple times a day.

People usually like to describe Perplexity as like chatbt plus search, but it is actually so much more than that.

So, in this video, I'm going to show you guys the core features of Perplexity, including its intelligent search capabilities."""

# Test with Tactiq-style text
tactiq_text = """# tactiq.io free youtube transcript
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

def test_paste(text, label):
    print(f"\n=== Testing {label} ===")
    data = {
        "mode": "paste",
        "raw_transcript": text,
        "summary_format": "bullet_points"
    }
    
    try:
        response = requests.post(url, json=data, timeout=30)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("Success!")
            print("Response keys:", list(result.keys()))
            if 'metrics' in result:
                print("Metrics:", result['metrics'])
            if 'transcript' in result:
                transcript_html = result['transcript']
                print("Transcript HTML length:", len(transcript_html))
                # Extract the cleaned text from the HTML
                import re
                cleaned_match = re.search(r'<div[^>]*>([^<]+)</div>', transcript_html)
                if cleaned_match:
                    cleaned_text = cleaned_match.group(1)
                    print("Cleaned text preview:", repr(cleaned_text[:200]))
        else:
            print("Error response:")
            print(response.text)
            
    except Exception as e:
        print(f"Error: {e}")

# Test both
test_paste(clean_text, "Clean Text")
test_paste(tactiq_text, "Tactiq Text")
