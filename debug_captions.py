#!/usr/bin/env python3
"""
Debug YouTube captions function step by step
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

def debug_captions(youtube_url: str):
    """Debug the captions function step by step"""
    
    print(f"🔍 Debugging captions for: {youtube_url}")
    print("=" * 50)
    
    # Step 1: Extract video ID
    vid = extract_youtube_video_id(youtube_url)
    print(f"1. Video ID: {vid}")
    
    if not vid:
        print("   ❌ Failed to extract video ID")
        return
    
    # Step 2: Build service
    try:
        service = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        print("2. ✅ YouTube service built successfully")
    except Exception as e:
        print(f"   ❌ Failed to build service: {e}")
        return
    
    # Step 3: List caption tracks
    try:
        tracks = service.captions().list(part="id,snippet", videoId=vid).execute()
        items = tracks.get("items", [])
        print(f"3. Found {len(items)} caption tracks")
        
        if not items:
            print("   ❌ No caption tracks found")
            return
            
        # Show available tracks
        for i, item in enumerate(items):
            lang = item["snippet"].get("language", "unknown")
            name = item["snippet"].get("name", "unknown")
            track_id = item["id"]
            print(f"   📝 Track {i+1}: {lang} - {name} (ID: {track_id})")
            
    except Exception as e:
        print(f"   ❌ Failed to list tracks: {e}")
        return
    
    # Step 4: Choose best track
    def score(item):
        lang = (item["snippet"].get("language") or "").lower()
        lang_priority = ("en", "en-us", "en-gb")
        try:
            return lang_priority.index(lang)
        except ValueError:
            return len(lang_priority) + 1

    items.sort(key=score)
    chosen = items[0]
    caption_id = chosen["id"]
    chosen_lang = chosen["snippet"].get("language", "unknown")
    
    print(f"4. ✅ Chosen track: {chosen_lang} (ID: {caption_id})")
    
    # Step 5: Download SRT
    try:
        download_url = f"https://www.googleapis.com/youtube/v3/captions/{caption_id}?tfmt=srt&key={YOUTUBE_API_KEY}"
        print(f"5. Downloading from: {download_url}")
        
        r = requests.get(download_url, timeout=30)
        print(f"   Status code: {r.status_code}")
        
        if r.status_code != 200:
            print(f"   ❌ Download failed: {r.text}")
            return
            
        if not r.text.strip():
            print("   ❌ Empty response")
            return
            
        print(f"   ✅ Downloaded {len(r.text)} characters")
        
        # Show first few lines of SRT
        lines = r.text.splitlines()[:10]
        print("   📖 SRT preview:")
        for line in lines:
            print(f"      {line}")
            
    except Exception as e:
        print(f"   ❌ Download failed: {e}")
        return
    
    # Step 6: Convert to plain text
    try:
        srt_text = r.text
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
        
        result = "\n".join(lines).strip()
        print(f"6. ✅ Converted to plain text: {len(result)} characters")
        print(f"   📖 Text preview: {result[:200]}...")
        
    except Exception as e:
        print(f"   ❌ Conversion failed: {e}")

if __name__ == "__main__":
    debug_captions("https://youtube.com/watch?v=dQw4w9WgXcQ")
