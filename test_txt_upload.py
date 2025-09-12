#!/usr/bin/env python3
"""Test TXT file upload functionality"""

import requests
import io

# Create a test TXT file content
txt_content = """This is a test transcript file.

I learned how to use Perplexity for you. So, here's the Cliffnotes version to save you the hours and hours that I've spent digging into this tool, which I have realized has become one of my top three AI tools that I use literally multiple times a day.

People usually like to describe Perplexity as like chatbt plus search, but it is actually so much more than that.

So, in this video, I'm going to show you guys the core features of Perplexity, including its intelligent search capabilities, generating pages, quizzes, even dashboards and little applications.

This is a comprehensive overview of how to use Perplexity effectively for research and content creation.
"""

# Create a test TXT file with Tactiq-style content
tactiq_txt_content = """# tactiq.io free youtube transcript
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

def test_txt_upload(content, filename, label):
    print(f"\n=== Testing {label} ===")
    
    url = "https://vidscribe2ai.site/upload_subs"
    
    # Create file-like object
    file_obj = io.BytesIO(content.encode('utf-8'))
    
    files = {
        'file': (filename, file_obj, 'text/plain')
    }
    
    data = {
        'summary_format': 'bullet_points'
    }
    
    try:
        response = requests.post(url, files=files, data=data, timeout=30)
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
test_txt_upload(txt_content, "test_transcript.txt", "Clean TXT File")
test_txt_upload(tactiq_txt_content, "tactiq_transcript.txt", "Tactiq-style TXT File")
