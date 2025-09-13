from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from tenacity import retry, wait_exponential_jitter, stop_after_attempt
import subprocess, json, re, time, random
import logging

_YT_ID = re.compile(r'(?:v=|youtu\.be/|/embed/|/shorts/)([A-Za-z0-9_-]{11})')

# Simple in-memory cache to avoid repeated API calls
_cache = {}
_cache_ttl = 3600  # 1 hour

def extract_video_id(url: str) -> str | None:
    m = _YT_ID.search(url)
    return m.group(1) if m else None

def _get_cached_transcript(video_id: str) -> str | None:
    """Check cache for existing transcript"""
    if video_id in _cache:
        cached_time, transcript = _cache[video_id]
        if time.time() - cached_time < _cache_ttl:
            logging.info(f"Using cached transcript for {video_id}")
            return transcript
        else:
            del _cache[video_id]
    return None

def _cache_transcript(video_id: str, transcript: str):
    """Cache transcript with timestamp"""
    _cache[video_id] = (time.time(), transcript)
    logging.info(f"Cached transcript for {video_id}")

@retry(wait=wait_exponential_jitter(3, 15), stop=stop_after_attempt(3))
def _captions_via_api(video_id: str) -> str:
    # Check cache first
    cached = _get_cached_transcript(video_id)
    if cached:
        return cached
    
    # Add random delay to avoid rate limiting
    time.sleep(random.uniform(1, 3))
    
    # Prefer English, then autogen
    for langs in (['en'], ['en-US','en-GB'], ['en', 'en-US', 'en-GB'], ['en'], []):
        try:
            s = YouTubeTranscriptApi.get_transcript(video_id, languages=langs or None)
            transcript = "\n".join([i['text'] for i in s if i['text'].strip() != '[Music]'])
            _cache_transcript(video_id, transcript)
            return transcript
        except (TranscriptsDisabled, NoTranscriptFound):
            continue
        except Exception as e:
            logging.warning(f"API error for {video_id}: {e}")
            # Add longer delay on API errors
            time.sleep(random.uniform(5, 10))
            raise
    raise NoTranscriptFound(video_id)

@retry(wait=wait_exponential_jitter(3, 15), stop=stop_after_attempt(3))
def _captions_via_ytdlp(video_url: str) -> str:
    # Add delay to avoid rate limiting
    time.sleep(random.uniform(2, 5))
    
    # Try multiple yt-dlp strategies
    strategies = [
        # Strategy 1: Direct subtitle extraction
        [
            "yt-dlp", "--skip-download", "--write-auto-sub", "--write-sub",
            "--sub-langs", "en.*", "--sub-format", "vtt", "--print", "subtitles",
            video_url
        ],
        # Strategy 2: Try different subtitle formats
        [
            "yt-dlp", "--skip-download", "--write-auto-sub", "--write-sub",
            "--sub-langs", "en", "--sub-format", "srv1,srv2,srv3,vtt",
            "--print", "subtitles", video_url
        ],
        # Strategy 3: Extract from info
        [
            "yt-dlp", "--skip-download", "--print", "subtitles", video_url
        ]
    ]
    
    for i, cmd in enumerate(strategies):
        try:
            logging.info(f"Trying yt-dlp strategy {i+1} for {video_url}")
            out = subprocess.check_output(cmd, text=True, timeout=30)
            
            # Try to parse JSON output
            try:
                data = json.loads(out)
                for k, tracks in data.items():
                    for t in tracks:
                        if t.get('ext') in ('vtt','srv1','srv2','srv3') and t.get('url'):
                            import urllib.request
                            subtitle_content = urllib.request.urlopen(t['url']).read().decode('utf-8', errors='ignore')
                            logging.info(f"Successfully extracted captions via yt-dlp strategy {i+1}")
                            return subtitle_content
            except json.JSONDecodeError:
                # Fallback: try to extract from text output
                lines = out.split('\n')
                for line in lines:
                    if '.vtt' in line or '.srv' in line:
                        # This might be a file path, try to read it
                        try:
                            with open(line.strip(), 'r') as f:
                                return f.read()
                        except:
                            continue
            
        except subprocess.TimeoutExpired:
            logging.warning(f"yt-dlp strategy {i+1} timed out")
            continue
        except Exception as e:
            logging.warning(f"yt-dlp strategy {i+1} failed: {e}")
            continue
    
    raise RuntimeError("No captions found via yt-dlp")

def get_captions_text(video_url: str) -> tuple[str, str]:
    """Returns (transcript_text, source)"""
    vid = extract_video_id(video_url)
    if not vid:
        raise ValueError("Could not extract YouTube ID")
    
    # Try YouTube Transcript API first (fastest when it works)
    try:
        logging.info(f"Attempting YouTube Transcript API for {vid}")
        txt = _captions_via_api(vid)
        return (txt, "youtube-transcript-api")
    except Exception as e:
        logging.warning(f"YouTube Transcript API failed for {vid}: {e}")
    
    # Try yt-dlp as fallback
    try:
        logging.info(f"Attempting yt-dlp fallback for {video_url}")
        vtt = _captions_via_ytdlp(video_url)
        # Convert VTT to text
        lines = []
        for line in vtt.splitlines():
            if not line.strip() or "-->" in line or line.strip().isdigit():
                continue
            lines.append(line)
        transcript = "\n".join(lines)
        if transcript.strip():
            return (transcript, "yt-dlp")
    except Exception as e:
        logging.warning(f"yt-dlp fallback failed for {video_url}: {e}")
    
    # If all else fails, provide helpful error message
    raise RuntimeError(
        f"Could not extract captions from {video_url}. "
        f"This might be due to rate limiting or the video not having captions. "
        f"Try again in a few minutes or use the 'Paste Transcript' option instead."
    )
