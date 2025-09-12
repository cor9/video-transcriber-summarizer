# captions.py
import os, re, tempfile, json
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import (
    YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound,
    CouldNotRetrieveTranscript, VideoUnavailable, TooManyRequests
)
from backoff import backoff
from cache import cache_get, cache_set

COOKIES_TXT = os.getenv("YOUTUBE_COOKIES_TXT")  # optional path to cookies.txt
USE_YTDLP = os.getenv("ENABLE_YTDLP_FALLBACK", "1") == "1"
YTDLP_SLEEP = float(os.getenv("YTDLP_SLEEP_INTERVAL_REQUESTS", "1.5"))  # seconds between requests
YTDLP_MAXSLEEP = float(os.getenv("YTDLP_MAX_SLEEP", "3.5"))
YTDLP_RATE = os.getenv("YTDLP_RATE_LIMIT", None)  # e.g. "200K" to cap transfer rate (polite)

def extract_video_id(url: str) -> str | None:
    try:
        u = urlparse(url); host = (u.netloc or "").lower(); path = u.path or ""; qs = parse_qs(u.query)
        if "v" in qs and qs["v"]: return qs["v"][0][:11]
        if "youtu.be" in host:    return path.strip("/").split("/")[0][:11]
        m = re.search(r"/(?:embed|v|shorts)/([0-9A-Za-z_-]{11})", path);  return m.group(1) if m else None
    except Exception:
        return None

def _join(entries):
    return "\n".join(e.get("text","") for e in entries if e.get("text")).strip() or None

@backoff(on_exceptions=(TooManyRequests, CouldNotRetrieveTranscript), tries=5, base=0.8, cap=6.0, jitter=0.7)
def fetch_primary(video_id: str, prefer=("en","en-US","en-GB"), translate_to="en"):
    # 1) fast path
    try:
        entries = (YouTubeTranscriptApi.get_transcript(video_id, languages=list(prefer), cookies=COOKIES_TXT)
                   if COOKIES_TXT else
                   YouTubeTranscriptApi.get_transcript(video_id, languages=list(prefer)))
        text = _join(entries)
        if text: return text, {"path": "primary_direct"}
    except (NoTranscriptFound, TranscriptsDisabled):
        pass

    # 2) list & pick
    tlist = (YouTubeTranscriptApi.list_transcripts(video_id, cookies=COOKIES_TXT)
             if COOKIES_TXT else YouTubeTranscriptApi.list_transcripts(video_id))

    def rank(t):
        try: pref = list(prefer).index(t.language_code)
        except ValueError: pref = len(prefer) + 1
        manual_bonus = 0 if not t.is_generated else 1
        return (pref, manual_bonus)

    cands = sorted(list(tlist), key=rank)

    # same-language first
    for c in cands:
        if c.language_code in prefer:
            text = _join(c.fetch())
            if text: return text, {"path": "primary_list", "lang": c.language_code, "generated": c.is_generated}

    # translate if allowed
    for c in cands:
        if getattr(c, "is_translatable", False):
            try:
                text = _join(c.translate(translate_to).fetch())
                if text: return text, {"path": "primary_translated", "from": c.language_code, "generated": c.is_generated}
            except Exception:
                continue

    # any manual then any generated
    for bucket in ([t for t in tlist if not t.is_generated], [t for t in tlist if t.is_generated]):
        for c in bucket:
            try:
                text = _join(c.fetch())
                if text: return text, {"path": "primary_any", "lang": c.language_code, "generated": c.is_generated}
            except Exception:
                continue

    raise NoTranscriptFound("no_working_track")

def fetch_fallback_ytdlp(video_url: str):
    if not USE_YTDLP:
        return None, {"path": "disabled"}
    try:
        import yt_dlp
    except Exception as e:
        return None, {"path": "yt_dlp", "reason": f"import_failed:{e}"}

    tmp = tempfile.mkdtemp(prefix="subs_")
    out = os.path.join(tmp, "%(id)s.%(ext)s")
    opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitlesformat": "srt",
        "subtitleslangs": ["en,en.*,en-US,en-GB"],  # include auto
        "paths": {"home": tmp, "temp": tmp},
        "outtmpl": out,
        "quiet": True,
        "no_warnings": True,
        "sleep_interval_requests": YTDLP_SLEEP,
        "max_sleep_interval_requests": YTDLP_MAXSLEEP,
    }
    if YTDLP_RATE:
        opts["ratelimit"] = YTDLP_RATE  # e.g. "200K" being polite

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            ydl.download([video_url])
    except Exception as e:
        return None, {"path": "yt_dlp", "reason": f"extract_or_download:{e}"}

    # read SRT
    vid = extract_video_id(video_url) or ""
    text = None
    try:
        for fn in os.listdir(tmp):
            if fn.endswith(".srt") and (vid in fn or fn.count(".srt")):
                with open(os.path.join(tmp, fn), "r", encoding="utf-8", errors="ignore") as f:
                    lines = []
                    for line in f:
                        line = line.strip()
                        if not line: continue
                        if line.isdigit(): continue
                        if "-->" in line: continue
                        lines.append(line)
                    text = "\n".join(lines).strip() or None
                    if text: break
    except Exception as e:
        return None, {"path": "yt_dlp", "reason": f"read_srt:{e}"}

    return (text, {"path": "yt_dlp"}) if text else (None, {"path": "yt_dlp", "reason": "no_srt"})

def get_captions(video_url: str):
    vid = extract_video_id(video_url)
    if not vid:
        return None, {"reason": "no_video_id"}

    # 0) cache
    cached = cache_get(vid)
    if cached:
        return cached, {"path": "cache"}

    # 1) primary with retries/backoff
    try:
        text, meta = fetch_primary(vid)
        cache_set(vid, text)
        return text, meta
    except (TooManyRequests, CouldNotRetrieveTranscript):
        pass
    except (NoTranscriptFound, TranscriptsDisabled, VideoUnavailable):
        return None, {"reason": "unavailable"}

    # 2) fallback via yt-dlp (with built-in sleeps)
    text, meta = fetch_fallback_ytdlp(video_url)
    if text:
        cache_set(vid, text)
        return text, meta

    return None, {"reason": "rate_limited_or_blocked"}
