from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
import time
import random

# A simple in-memory cache to store recent transcripts
transcript_cache = {}

def get_video_id(url):
    """Extracts the YouTube video ID from a URL."""
    if not url:
        return None
    
    query = urlparse(url)
    if "youtu.be" in query.hostname:
        return query.path[1:]
    if "youtube.com" in query.hostname:
        if query.path == '/watch':
            return parse_qs(query.query).get('v', [None])[0]
        if query.path.startswith(('/embed/', '/v/')):
            return query.path.split('/')[2]
    return None

def fetch_transcript(video_url, language_codes=None):
    """
    Fetches a transcript, using a cache to avoid redundant requests.
    Enhanced with MCP-style functionality and better error handling.
    """
    video_id = get_video_id(video_url)
    if not video_id:
        raise ValueError("Invalid YouTube URL provided.")

    # Check the cache first
    cache_key = f"{video_id}_{language_codes or 'auto'}"
    if cache_key in transcript_cache:
        print(f"✅ Returning cached transcript for video ID: {video_id}")
        return {
            "success": True,
            "transcript": transcript_cache[cache_key]["transcript"],
            "language": transcript_cache[cache_key]["language"],
            "text": transcript_cache[cache_key]["text"],
            "cached": True
        }

    # If not in cache, fetch it with retry logic
    print(f"🔎 Fetching new transcript for video ID: {video_id}")
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            # Add delay between attempts
            if attempt > 0:
                delay = random.uniform(1, 3)
                time.sleep(delay)
            
            # Try specific languages first if provided
            if language_codes:
                for lang in language_codes:
                    try:
                        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang])
                        result = {
                            "success": True,
                            "transcript": transcript_list,
                            "language": lang,
                            "text": " ".join([item['text'] for item in transcript_list]),
                            "cached": False
                        }
                        # Store in cache
                        transcript_cache[cache_key] = result
                        return result
                    except:
                        continue
            
            # Fallback to auto-generated or any available
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            result = {
                "success": True,
                "transcript": transcript_list,
                "language": "auto",
                "text": " ".join([item['text'] for item in transcript_list]),
                "cached": False
            }
            # Store in cache
            transcript_cache[cache_key] = result
            return result
            
        except Exception as e:
            error_msg = str(e)
            if attempt == max_retries - 1:
                # Provide better error messages
                if "no element found" in error_msg or "XML" in error_msg:
                    raise Exception("YouTube is temporarily blocking transcript access for this video. This video has captions, but YouTube is blocking API access. Try again in a few minutes or use a different video.")
                elif "Subtitles are disabled" in error_msg:
                    raise Exception("Captions are disabled for this video by the creator. Try a different video with captions enabled.")
                elif "Video unavailable" in error_msg:
                    raise Exception("This video is unavailable or has been removed. Check if the video URL is correct.")
                else:
                    raise Exception(f"Could not get transcript: {error_msg}")
            continue
    
    return None

def get_video_info(video_url):
    """
    Get video information and metadata
    """
    video_id = get_video_id(video_url)
    if not video_id:
        raise ValueError("Invalid YouTube URL provided.")
    
    try:
        # Get transcript to verify video exists and get basic info
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        
        return {
            "success": True,
            "video_id": video_id,
            "has_transcript": True,
            "transcript_length": len(transcript_list),
            "duration": transcript_list[-1]['start'] + transcript_list[-1]['duration'] if transcript_list else 0
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "video_id": video_id,
            "has_transcript": False
        }
