#!/usr/bin/env python3
"""
Direct test of YouTube captions function
"""

import os
import requests
import re
from googleapiclient.discovery import build

# Set the API key
YOUTUBE_API_KEY = "AIzaSyAR0iZ7-3QwCbyQ5vXFCzL6HZUvt5YXAks"

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
    Tries to fetch captions for a YouTube video via the official API.
    Returns plain text if found; otherwise None.
    """
    if not YOUTUBE_API_KEY:
        return None  # captions path disabled without API key

    vid = extract_youtube_video_id(youtube_url)
    if not vid:
        return None

    service = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

    # 1) List caption tracks
    tracks = service.captions().list(part="id,snippet", videoId=vid).execute()
    items = tracks.get("items", [])
    if not items:
        return None

    # 2) Choose a track that matches our language priority (fallback to first)
    def score(item):
        lang = (item["snippet"].get("language") or "").lower()
        try:
            return lang_priority.index(lang)
        except ValueError:
            return len(lang_priority) + 1

    items.sort(key=score)
    chosen = items[0]
    caption_id = chosen["id"]

    # 3) Download SRT (best for plain text)
    download_url = f"https://www.googleapis.com/youtube/v3/captions/{caption_id}?tfmt=srt&key={YOUTUBE_API_KEY}"
    r = requests.get(download_url, timeout=30)
    if r.status_code != 200 or not r.text.strip():
        return None

    srt_text = r.text
    # 4) Strip SRT timestamps/indexes to plain text
    lines = []
    for line in srt_text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.isdigit():
            continue
        if "-->" in line:
            continue
        lines.append(line)
    return "\n".join(lines).strip() or None

def test_captions():
    """Test the captions function directly"""
    
    test_urls = [
        "https://youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    ]
    
    print("🧪 Testing YouTube Captions Function Directly")
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
    test_captions()
