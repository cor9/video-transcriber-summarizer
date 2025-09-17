#!/usr/bin/env python3
"""
Debug script to check what captions/transcripts are available for a specific video
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from urllib.parse import urlparse, parse_qs
import re

def extract_video_id(url):
    """Extract video ID from YouTube URL"""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname.lower()
        path = parsed.path
        query_params = parse_qs(parsed.query)
        
        if "youtube.com" in hostname:
            if path == "/watch" and "v" in query_params:
                return query_params["v"][0][:11]
            match = re.search(r"/(?:embed|v|shorts)/([0-9A-Za-z_-]{11})", path)
            if match:
                return match.group(1)
        elif "youtu.be" in hostname:
            return path.strip("/").split("/")[0][:11]
        
        match = re.search(r"([0-9A-Za-z_-]{11})", url)
        return match.group(1) if match else None
    except Exception:
        return None

def debug_video_captions(video_url):
    """Debug what captions are available for a video"""
    print(f"🔍 Debugging captions for: {video_url}")
    print("=" * 60)
    
    video_id = extract_video_id(video_url)
    if not video_id:
        print("❌ Could not extract video ID from URL")
        return
    
    print(f"📹 Video ID: {video_id}")
    print()
    
    try:
        # Check what transcripts are available
        print("📋 Checking available transcripts...")
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        print("✅ Transcripts found:")
        for transcript in transcript_list:
            print(f"  • Language: {transcript.language_code}")
            print(f"    - Name: {transcript.language}")
            print(f"    - Generated: {transcript.is_generated}")
            print(f"    - Translatable: {getattr(transcript, 'is_translatable', 'Unknown')}")
            print()
        
        # Try to get a transcript
        print("🎯 Attempting to fetch transcript...")
        try:
            # Try English first
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
            print(f"✅ Successfully got English transcript with {len(transcript)} entries")
            print("First few entries:")
            for i, entry in enumerate(transcript[:3]):
                print(f"  {i+1}. {entry['start']:.1f}s: {entry['text']}")
        except NoTranscriptFound:
            print("❌ No English transcript found")
            
            # Try any available language
            try:
                transcript = YouTubeTranscriptApi.get_transcript(video_id)
                print(f"✅ Got transcript in {transcript[0].get('language', 'unknown')} with {len(transcript)} entries")
            except Exception as e:
                print(f"❌ Could not get any transcript: {e}")
        
    except TranscriptsDisabled:
        print("❌ Transcripts are disabled for this video")
        print("This means the creator has disabled transcript access via API")
    except Exception as e:
        print(f"❌ Error accessing transcript list: {e}")
    
    print()
    print("💡 Possible explanations:")
    print("  • CC on TV might be burned-in captions (not accessible via API)")
    print("  • CC on TV might be auto-generated but API access is restricted")
    print("  • Creator disabled transcript API access but allows CC display")
    print("  • Different regions might have different caption availability")
    print("  • CC might be from a different source (broadcast, etc.)")

if __name__ == "__main__":
    test_url = "https://www.youtube.com/watch?v=s9TzkYbliO8"
    debug_video_captions(test_url)
