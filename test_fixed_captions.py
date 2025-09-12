#!/usr/bin/env python3
"""
Test the fixed YouTube captions function using youtube-transcript-api
"""

import os
import re
from youtube_transcript_api import YouTubeTranscriptApi

# YouTube ID extraction regex
YOUTUBE_ID_RE = re.compile(
    r'(?:v=|\/)([0-9A-Za-z_-]{11}).*'
)

def extract_youtube_video_id(url: str) -> str | None:
    """Extract YouTube video ID from various URL formats"""
    # Handles standard and youtu.be forms
    m = YOUTUBE_ID_RE.search(url)
    if m:
        return m.group(1)
    # youtu.be short form
    if "youtu.be/" in url:
        return url.rstrip('/').split('/')[-1][:11]
    return None

def fetch_youtube_captions_text(youtube_url: str, lang_priority=("en", "en-US", "en-GB")) -> str | None:
    """
    Tries to fetch captions for a YouTube video using youtube-transcript-api.
    Returns plain text if found; otherwise None.
    """
    vid = extract_youtube_video_id(youtube_url)
    if not vid:
        return None

    try:
        # Use youtube-transcript-api which doesn't require OAuth2
        api = YouTubeTranscriptApi()
        transcript_list = api.list(vid)
        
        # Try to get transcript in preferred language order
        for lang in lang_priority:
            try:
                transcript = transcript_list.find_transcript([lang])
                transcript_data = transcript.fetch()
                # Convert to plain text
                text = ' '.join([item['text'] for item in transcript_data])
                return text.strip() if text.strip() else None
            except:
                continue
        
        # If no preferred language found, try generated transcripts
        try:
            transcript = transcript_list.find_generated_transcripts(['en'])
            transcript_data = transcript[0].fetch()
            text = ' '.join([item['text'] for item in transcript_data])
            return text.strip() if text.strip() else None
        except:
            pass
        
        # If still no luck, try any available transcript
        try:
            available_transcripts = list(transcript_list)
            if available_transcripts:
                transcript = available_transcripts[0]
                transcript_data = transcript.fetch()
                text = ' '.join([item['text'] for item in transcript_data])
                return text.strip() if text.strip() else None
        except:
            pass
            
        return None
        
    except Exception as e:
        print(f"Error fetching YouTube captions: {str(e)}")
        return None

def test_fixed_captions():
    """Test the fixed captions function"""
    
    test_urls = [
        "https://youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    ]
    
    print("🧪 Testing Fixed YouTube Captions Function")
    print("=" * 50)
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n{i}. Testing: {url}")
        
        try:
            result = fetch_youtube_captions_text(url)
            
            if result:
                print("   ✅ SUCCESS!")
                print(f"   📝 Captions length: {len(result)}")
                print(f"   📖 Preview: {result[:200]}...")
            else:
                print("   ❌ FAILED - No captions returned")
                
        except Exception as e:
            print(f"   💥 EXCEPTION: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_fixed_captions()
