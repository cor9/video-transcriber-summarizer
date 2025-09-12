import os, json, time, hashlib
CACHE_DIR = os.getenv("CAPTIONS_CACHE_DIR", "/tmp/captions_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

def _key(video_id: str) -> str:
    return os.path.join(CACHE_DIR, f"{hashlib.sha1(video_id.encode()).hexdigest()}.json")

def cache_get(video_id: str, max_age_seconds: int = 30*24*3600):
    path = _key(video_id)
    if not os.path.exists(path): return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if time.time() - data.get("ts", 0) > max_age_seconds: return None
        return data.get("text") or None
    except Exception:
        return None

def cache_set(video_id: str, text: str):
    try:
        with open(_key(video_id), "w", encoding="utf-8") as f:
            json.dump({"ts": time.time(), "text": text}, f)
    except Exception:
        pass