"""
Enhanced YouTube Transcript Module
Inspired by jkawamoto/mcp-youtube-transcript with pagination and robust error handling
"""
import os
import time
import random
import json
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urlparse, parse_qs
import re

from youtube_transcript_api import (
    YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound,
    CouldNotRetrieveTranscript, VideoUnavailable, TooManyRequests
)
from .backoff import backoff
from .cache import cache_get, cache_set


class EnhancedYouTubeTranscript:
    """
    Enhanced YouTube transcript fetcher with pagination, better error handling,
    and proxy support inspired by jkawamoto/mcp-youtube-transcript
    """
    
    def __init__(self, cookies_path: str = "/tmp/youtube_cookies.txt"):
        self.cookies_path = cookies_path
        self.max_chunk_size = 15000  # Characters per chunk
        self.preferred_languages = ["en", "en-US", "en-GB"]
        
    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from various YouTube URL formats"""
        if not url:
            return None
            
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname.lower()
            path = parsed.path
            query_params = parse_qs(parsed.query)
            
            # Standard YouTube URLs
            if "youtube.com" in hostname:
                if path == "/watch" and "v" in query_params:
                    return query_params["v"][0][:11]
                # Shorts, embed, etc.
                match = re.search(r"/(?:embed|v|shorts)/([0-9A-Za-z_-]{11})", path)
                if match:
                    return match.group(1)
                    
            # youtu.be URLs
            elif "youtu.be" in hostname:
                return path.strip("/").split("/")[0][:11]
                
            # Generic fallback for any 11-character video ID
            match = re.search(r"([0-9A-Za-z_-]{11})", url)
            return match.group(1) if match else None
            
        except Exception:
            return None
    
    def get_video_info(self, video_id: str) -> Dict[str, Any]:
        """Get basic video information"""
        try:
            # This is a simplified version - in a real implementation,
            # you might want to use the YouTube Data API for more detailed info
            return {
                "video_id": video_id,
                "title": "Video Title",  # Would need YouTube Data API
                "duration": "Unknown",   # Would need YouTube Data API
                "has_transcripts": True   # We'll determine this when fetching
            }
        except Exception:
            return {"video_id": video_id, "error": "Could not fetch video info"}
    
    @backoff(on_exceptions=(TooManyRequests, CouldNotRetrieveTranscript), tries=7, base=1.2, cap=12.0, jitter=1.0)
    def get_transcript_chunked(self, video_id: str, language: str = "en", 
                             next_cursor: Optional[str] = None) -> Dict[str, Any]:
        """
        Get transcript with pagination support
        Returns: {
            "text": str,
            "next_cursor": str or None,
            "metadata": dict,
            "total_chars": int
        }
        """
        try:
            # Check cache first
            cache_key = f"{video_id}_{language}_{next_cursor or 'initial'}"
            cached = cache_get(cache_key)
            if cached:
                return cached
            
            # Prepare request parameters
            kwargs = {}
            if os.path.exists(self.cookies_path):
                kwargs["cookies"] = self.cookies_path
            
            # Get transcript list to find available languages
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id, **kwargs)
            
            # Try to get transcript in preferred language
            transcript = None
            metadata = {"method": "direct", "language": language}
            
            try:
                # Try direct fetch first
                transcript_data = YouTubeTranscriptApi.get_transcript(
                    video_id, 
                    languages=[language], 
                    **kwargs
                )
                transcript = transcript_data
                metadata["method"] = "direct"
                
            except (NoTranscriptFound, TranscriptsDisabled):
                # Try to find best available transcript
                available_transcripts = list(transcript_list)
                
                # Sort by preference
                def rank_transcript(t):
                    try:
                        pref_index = self.preferred_languages.index(t.language_code)
                    except ValueError:
                        pref_index = len(self.preferred_languages)
                    
                    # Prefer manual over generated
                    manual_bonus = 0 if t.is_generated else 1
                    return (pref_index, manual_bonus)
                
                sorted_transcripts = sorted(available_transcripts, key=rank_transcript)
                
                for t in sorted_transcripts:
                    try:
                        if t.language_code in self.preferred_languages:
                            transcript = t.fetch()
                            metadata.update({
                                "method": "preferred",
                                "language": t.language_code,
                                "generated": t.is_generated
                            })
                            break
                    except Exception:
                        continue
                
                # Try translation if no preferred language found
                if not transcript:
                    for t in sorted_transcripts:
                        if hasattr(t, 'is_translatable') and t.is_translatable:
                            try:
                                transcript = t.translate(language).fetch()
                                metadata.update({
                                    "method": "translated",
                                    "original_language": t.language_code,
                                    "generated": t.is_generated
                                })
                                break
                            except Exception:
                                continue
            
            if not transcript:
                raise NoTranscriptFound("No suitable transcript found")
            
            # Convert transcript to text
            full_text = " ".join([item.get("text", "") for item in transcript if item.get("text")])
            
            # Implement pagination logic
            start_pos = 0
            if next_cursor:
                try:
                    start_pos = int(next_cursor)
                except ValueError:
                    start_pos = 0
            
            # Calculate chunk boundaries
            end_pos = min(start_pos + self.max_chunk_size, len(full_text))
            chunk_text = full_text[start_pos:end_pos]
            
            # Determine if there's more content
            has_more = end_pos < len(full_text)
            next_cursor_result = str(end_pos) if has_more else None
            
            result = {
                "text": chunk_text,
                "next_cursor": next_cursor_result,
                "metadata": metadata,
                "total_chars": len(full_text),
                "chunk_start": start_pos,
                "chunk_end": end_pos,
                "is_complete": not has_more
            }
            
            # Cache the result
            cache_set(cache_key, result)
            
            return result
            
        except TooManyRequests:
            return {
                "error": "YouTube is temporarily rate-limiting our requests. Please try again in a few minutes.",
                "retry_after": 60,
                "metadata": {"error_type": "rate_limited"},
                "suggestions": [
                    "Wait a few minutes and try again",
                    "Switch to 'Paste Transcript' mode if you have the transcript",
                    "Upload an SRT/VTT file using the file upload option"
                ]
            }
        except (NoTranscriptFound, TranscriptsDisabled):
            return {
                "error": "This video doesn't have captions or subtitles available.",
                "metadata": {"error_type": "no_transcript"},
                "suggestions": [
                    "Check if the video has captions enabled (look for CC button)",
                    "Try a different video that has captions",
                    "Use 'Paste Transcript' mode if you have the transcript text",
                    "Upload an SRT/VTT file if you have subtitle files"
                ],
                "common_causes": [
                    "Video creator disabled captions",
                    "Video is too new (captions may not be processed yet)",
                    "Video is age-restricted or private",
                    "Video is in a language without auto-generated captions"
                ]
            }
        except VideoUnavailable:
            return {
                "error": "This video is unavailable, private, or has been removed.",
                "metadata": {"error_type": "video_unavailable"},
                "suggestions": [
                    "Check if the video URL is correct",
                    "Try a different video",
                    "Use 'Paste Transcript' mode if you have the transcript"
                ]
            }
        except Exception as e:
            error_msg = str(e)
            # Provide more specific error messages for common issues
            if "Subtitles are disabled" in error_msg:
                return {
                    "error": "Captions are disabled for this video by the creator.",
                    "metadata": {"error_type": "subtitles_disabled"},
                    "suggestions": [
                        "Try a different video with captions enabled",
                        "Use 'Paste Transcript' mode if you have the transcript",
                        "Upload an SRT/VTT file if you have subtitle files"
                    ]
                }
            elif "Video unavailable" in error_msg:
                return {
                    "error": "This video is unavailable or has been removed.",
                    "metadata": {"error_type": "video_unavailable"},
                    "suggestions": [
                        "Check if the video URL is correct",
                        "Try a different video"
                    ]
                }
            elif "no element found" in error_msg or "XML" in error_msg:
                return {
                    "error": "YouTube is temporarily blocking transcript access for this video.",
                    "metadata": {"error_type": "xml_parse_error", "details": error_msg},
                    "suggestions": [
                        "This video has captions, but YouTube is blocking API access",
                        "Try again in a few minutes (temporary blocking)",
                        "Use 'Paste Transcript' mode if you can copy the captions from YouTube",
                        "Upload an SRT/VTT file if you have subtitle files",
                        "Try a different video with similar content"
                    ],
                    "common_causes": [
                        "YouTube rate limiting or bot detection",
                        "Temporary API access restrictions",
                        "Video has captions but API access is blocked",
                        "Regional restrictions on transcript access"
                    ]
                }
            else:
                return {
                    "error": f"Unable to get transcript: {error_msg}",
                    "metadata": {"error_type": "unknown", "details": error_msg},
                    "suggestions": [
                        "Try a different video",
                        "Use 'Paste Transcript' mode if you have the transcript",
                        "Upload an SRT/VTT file if you have subtitle files"
                    ]
                }
    
    def get_full_transcript(self, video_id: str, language: str = "en") -> Dict[str, Any]:
        """
        Get complete transcript by fetching all chunks
        """
        full_text = ""
        chunks = []
        next_cursor = None
        total_chars = 0
        
        while True:
            result = self.get_transcript_chunked(video_id, language, next_cursor)
            
            if "error" in result:
                return result
            
            full_text += result["text"]
            chunks.append(result)
            total_chars = result["total_chars"]
            
            if not result["next_cursor"]:
                break
                
            next_cursor = result["next_cursor"]
            
            # Add small delay between chunks to be respectful
            time.sleep(0.1)
        
        return {
            "text": full_text,
            "total_chars": total_chars,
            "chunks": len(chunks),
            "metadata": chunks[0]["metadata"] if chunks else {},
            "is_complete": True
        }
    
    def get_transcript_from_url(self, url: str, language: str = "en") -> Dict[str, Any]:
        """
        Get transcript from YouTube URL
        """
        video_id = self.extract_video_id(url)
        if not video_id:
            return {
                "error": "Invalid YouTube URL",
                "metadata": {"error_type": "invalid_url"}
            }
        
        return self.get_full_transcript(video_id, language)


# Convenience functions for backward compatibility
def get_enhanced_transcript(url: str, language: str = "en") -> Dict[str, Any]:
    """Get enhanced transcript from URL"""
    fetcher = EnhancedYouTubeTranscript()
    return fetcher.get_transcript_from_url(url, language)


def get_transcript_chunked(url: str, language: str = "en", next_cursor: Optional[str] = None) -> Dict[str, Any]:
    """Get transcript with pagination"""
    fetcher = EnhancedYouTubeTranscript()
    video_id = fetcher.extract_video_id(url)
    if not video_id:
        return {"error": "Invalid YouTube URL"}
    
    return fetcher.get_transcript_chunked(video_id, language, next_cursor)


def get_video_info(url: str) -> Dict[str, Any]:
    """Get video information"""
    fetcher = EnhancedYouTubeTranscript()
    video_id = fetcher.extract_video_id(url)
    if not video_id:
        return {"error": "Invalid YouTube URL"}
    
    return fetcher.get_video_info(video_id)
