from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from tenacity import retry, wait_exponential_jitter, stop_after_attempt
import subprocess, json, re

_YT_ID = re.compile(r'(?:v=|youtu\.be/|/embed/|/shorts/)([A-Za-z0-9_-]{11})')

def extract_video_id(url: str) -> str | None:
    m = _YT_ID.search(url)
    return m.group(1) if m else None

@retry(wait=wait_exponential_jitter(2, 10), stop=stop_after_attempt(5))
def _captions_via_api(video_id: str) -> str:
    # Prefer English, then autogen
    for langs in (['en'], ['en-US','en-GB'], ['en', 'en-US', 'en-GB'], ['en'], []):
        try:
            s = YouTubeTranscriptApi.get_transcript(video_id, languages=langs or None)
            return "\n".join([i['text'] for i in s if i['text'].strip() != '[Music]'])
        except (TranscriptsDisabled, NoTranscriptFound):
            continue
    raise NoTranscriptFound(video_id)

@retry(wait=wait_exponential_jitter(2, 10), stop=stop_after_attempt(5))
def _captions_via_ytdlp(video_url: str) -> str:
    # Try pulling timedtext XML or JSON via yt-dlp; no media download.
    # --write-auto-sub allows auto-generated captions.
    cmd = [
        "yt-dlp", "--skip-download",
        "--write-auto-sub", "--write-sub",
        "--sub-langs", "en.*",
        "--sub-format", "vtt",
        "--print", "subtitles",
        video_url
    ]
    out = subprocess.check_output(cmd, text=True)
    # yt-dlp --print subtitles returns JSON when available on newer builds, else path hints.
    try:
        data = json.loads(out)
        # Grab first English track URL and curl it
        for k, tracks in data.items():
            for t in tracks:
                if t.get('ext') in ('vtt','srv1','srv2','srv3') and t.get('url'):
                    import urllib.request
                    return urllib.request.urlopen(t['url']).read().decode('utf-8', errors='ignore')
    except Exception:
        pass
    # Fallback: nothing found
    raise RuntimeError("No captions via yt-dlp")

def get_captions_text(video_url: str) -> tuple[str, str]:
    """Returns (transcript_text, source)"""
    vid = extract_video_id(video_url)
    if not vid:
        raise ValueError("Could not extract YouTube ID")
    try:
        txt = _captions_via_api(vid)
        return (txt, "youtube-transcript-api")
    except Exception:
        pass
    # Try yt-dlp subtitles
    vtt = _captions_via_ytdlp(video_url)
    # naive VTT to text
    lines = []
    for line in vtt.splitlines():
        if not line.strip() or "-->" in line or line.strip().isdigit():
            continue
        lines.append(line)
    return ("\n".join(lines), "yt-dlp")
