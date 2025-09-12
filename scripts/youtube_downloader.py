#!/usr/bin/env python3
"""
YouTube Audio Downloader
Downloads audio from YouTube URLs using yt-dlp with multiple fallback strategies
"""

import sys
import os
import tempfile
import yt_dlp
import re

def extract_video_id(url):
    """Extract YouTube video ID from URL"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
        r'youtube\.com\/v\/([^&\n?#]+)',
        r'youtube\.com\/watch\?.*v=([^&\n?#]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def download_audio(youtube_url, output_file):
    """Download audio from YouTube with multiple strategies"""
    
    # Create output directory
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Multiple download strategies
    strategies = [
        # Strategy 1: Desktop Chrome
        {
            'format': 'bestaudio/best',
            'outtmpl': output_file,
            'extractaudio': True,
            'audioformat': 'mp4',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
            },
            'extractor_retries': 5,
            'fragment_retries': 5,
            'retries': 5,
            'socket_timeout': 60,
            'sleep_interval': 2,
            'max_sleep_interval': 10,
        },
        # Strategy 2: Mobile Safari
        {
            'format': 'bestaudio/best',
            'outtmpl': output_file,
            'extractaudio': True,
            'audioformat': 'mp4',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
            },
            'extractor_retries': 3,
            'fragment_retries': 3,
            'retries': 3,
            'socket_timeout': 30,
        },
        # Strategy 3: Minimal
        {
            'format': 'bestaudio/best',
            'outtmpl': output_file,
            'extractaudio': True,
            'audioformat': 'mp4',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'extractor_retries': 2,
            'fragment_retries': 2,
            'retries': 2,
        }
    ]
    
    last_error = None
    for i, ydl_opts in enumerate(strategies):
        try:
            print(f"Trying download strategy {i+1}...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([youtube_url])
            
            # Check if file was created and has content
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                print(f"Download successful with strategy {i+1}")
                return True
            else:
                print(f"Strategy {i+1} failed - no content downloaded")
                
        except Exception as e:
            print(f"Strategy {i+1} failed: {str(e)}")
            last_error = e
            continue
    
    # All strategies failed
    raise last_error or Exception("All download strategies failed")

def main():
    if len(sys.argv) != 3:
        print("Usage: python youtube_downloader.py <youtube_url> <output_file>")
        sys.exit(1)
    
    youtube_url = sys.argv[1]
    output_file = sys.argv[2]
    
    # Extract video ID for validation
    video_id = extract_video_id(youtube_url)
    if not video_id:
        print(f"Error: Invalid YouTube URL format: {youtube_url}")
        sys.exit(1)
    
    print(f"Downloading audio from YouTube video: {video_id}")
    
    try:
        success = download_audio(youtube_url, output_file)
        if success:
            print(f"Audio downloaded successfully: {output_file}")
        else:
            print("Download failed")
            sys.exit(1)
    except Exception as e:
        print(f"Error downloading audio: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
