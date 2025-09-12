# cache.py
import time

# Simple in-memory cache for Vercel compatibility
_cache = {}

def cache_get(video_id: str, max_age_seconds: int = 7*24*3600):
    if video_id not in _cache:
        return None
    
    data = _cache[video_id]
    if time.time() - data.get("ts", 0) > max_age_seconds:
        del _cache[video_id]
        return None
    
    return data.get("text") or None

def cache_set(video_id: str, text: str):
    _cache[video_id] = {"ts": time.time(), "text": text}
