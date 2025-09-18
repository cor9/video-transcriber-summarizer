#!/usr/bin/env python3
"""
A simple, self-contained YouTube summarizer using Flask and the Gemini API.
This version calls a dedicated MCP server for transcripts.
"""
import os, time, random, json, math, requests
from flask import Flask, request, render_template_string
from flask_cors import CORS
from urllib.parse import urlparse, parse_qs

# --- Google Gen AI SDK (new) ---
# pip install -U google-genai
from google import genai
from google.genai import types as gtypes

# Optional: local fallback (pip install youtube-transcript-api)
try:
    from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
    HAS_YT = True
except Exception:
    HAS_YT = False

# --- 1. SETUP ---
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # simple, permissive CORS

# Config
MCP_SERVER_URL = os.environ.get(
    "MCP_SERVER_URL",
    "https://video-transcriber-qmcpuy1e6-cor9s-projects.vercel.app"
)
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")  # or gemini-2.5-pro
GENAI_API_KEY = os.environ.get("GEMINI_API_KEY")
SUMMARY_BULLET_COUNT = int(os.environ.get("SUMMARY_BULLETS", "10"))
MAX_TRANSCRIPT_CHARS = int(os.environ.get("MAX_TRANSCRIPT_CHARS", "160000"))  # hard ceiling
CHUNK_CHARS = int(os.environ.get("CHUNK_CHARS", "12000"))  # ~2-3k tokens rough

def get_video_id(url: str) -> str | None:
    if not url: return None
    q = urlparse(url)
    host = (q.hostname or "").lower()
    if "youtu.be" in host:
        return q.path.lstrip("/")
    if "youtube.com" in host:
        if q.path == "/watch":
            return parse_qs(q.query).get("v", [None])[0]
        if q.path.startswith(("/embed/", "/v/")):
            parts = q.path.split("/")
            return parts[2] if len(parts) > 2 else None
    return None


def call_mcp_transcript(video_url: str, timeout=30):
    """HTTP wrapper around your MCP server (not the raw MCP protocol)."""
    payload = {"video_url": video_url}
    try:
        r = requests.post(f"{MCP_SERVER_URL}/api/transcript", json=payload, timeout=timeout)
        if r.status_code == 200:
            data = r.json()
            if data.get("success") and data.get("transcript"):
                return True, data["transcript"], "MCP Server"
            return False, None, f"MCP error: {data.get('error','unknown')}"
        return False, None, f"MCP status {r.status_code}: {r.text[:200]}"
    except requests.exceptions.RequestException as e:
        return False, None, f"MCP network error: {e}"

def local_transcript(video_id: str):
    """Fallback using youtube-transcript-api with language probing."""
    if not HAS_YT:
        return False, None, "Local API unavailable - youtube-transcript-api not installed"
    
    probes = [None, ['en'], ['en-US'], ['en-GB']]
    last_error = None
    
    for probe in probes:
        try:
            lst = (YouTubeTranscriptApi.get_transcript(video_id, languages=probe) if probe
                   else YouTubeTranscriptApi.get_transcript(video_id))
            text = " ".join(item.get("text","") for item in lst)
            if text.strip():  # Make sure we got actual content
                return True, text, "Local API"
        except TranscriptsDisabled:
            last_error = "Subtitles are disabled for this video"
            continue
        except NoTranscriptFound:
            last_error = "No transcripts found for this video"
            continue
        except VideoUnavailable:
            last_error = "Video is unavailable or private"
            continue
        except Exception as e:
            last_error = f"Transcript API error: {str(e)}"
            time.sleep(random.uniform(0.5, 1.5))
            continue
    
    return False, None, last_error or "No transcripts available"

def safe_cut(s: str, limit: int) -> str:
    return s if len(s) <= limit else s[:limit]

def chunk_text(s: str, size: int):
    for i in range(0, len(s), size):
        yield s[i:i+size]

def summarize_chunks(chunks: list[str], bullets: int) -> str:
    """Map-reduce: per-chunk bullets → final merge."""
    # 1) per-chunk
    partials = []
    cfg = gtypes.GenerateContentConfig(temperature=0.2)
    for idx, ch in enumerate(chunks, 1):
        prompt = (
            f"You will write ultra-concise bullet points (max {max(4, bullets//2)} bullets) "
            f"capturing only **new** facts from this transcript segment {idx}/{len(chunks)}.\n\n"
            f"Transcript segment:\n{ch}"
        )
        resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt, config=cfg)
        partials.append(resp.text.strip())

    # 2) merge
    merge_prompt = (
        f"Merge and deduplicate these notes into ~{bullets} crisp bullets for busy parents.\n"
        f"Keep names, numbers, steps, and takeaways. No fluff.\n\n{'\\n\\n'.join(partials)}"
    )
    final = client.models.generate_content(model=GEMINI_MODEL, contents=merge_prompt, config=cfg)
    return final.text.strip()

# --- Gemini client ---
if not GENAI_API_KEY:
    raise SystemExit("FATAL: Set GEMINI_API_KEY env var.")
client = genai.Client(api_key=GENAI_API_KEY)

# --- 2. HTML TEMPLATES (for simplicity, we keep them in the Python file) ---

# This is the main page with the input form
HTML_FORM = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Simple YouTube Summarizer</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; background-color: #f9f9f9; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
        h1 { color: #333; }
        form { margin-top: 20px; }
        input[type=url] { width: 100%; padding: 12px; font-size: 16px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
        button { width: 100%; padding: 12px; margin-top: 10px; font-size: 16px; background-color: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
        button:hover { background-color: #0056b3; }
        .error { color: #d93025; font-weight: bold; margin-top: 10px; }
    </style>
</head>
<body>
    <h1>Simple YouTube Summarizer</h1>
    <p style="color: #666; margin-bottom: 20px;">Transcripts via MCP server with automatic local fallback. Summaries via Gemini {model}.</p>
    <form action="/summarize" method="post">
        <label for="youtube_url">Enter YouTube Video URL:</label>
        <input type="url" id="youtube_url" name="youtube_url" required placeholder="https://www.youtube.com/watch?v=...">
        <button type="submit">Summarize</button>
    </form>
    {% if error %}
        <p class="error">Error: {{ error }}</p>
    {% endif %}
</body>
</html>
"""

# This page displays the results
HTML_RESULT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Summary Result</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; background-color: #f9f9f9; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
        h2 { border-bottom: 2px solid #eee; padding-bottom: 10px; }
        div { background-color: #fff; padding: 15px; border-radius: 4px; margin-bottom: 20px; }
        pre { white-space: pre-wrap; word-wrap: break-word; font-size: 14px; line-height: 1.6; }
        a { color: #007bff; }
    </style>
</head>
<body>
    <h1>Summary Result</h1>
    <a href="/">Summarize another video</a>
    <p style="color: #666;">Transcript source: {{ source }}</p>
    <h2>AI Summary</h2>
    <div><pre>{{ summary }}</pre></div>
    <h2>Full Transcript</h2>
    <div><pre>{{ transcript }}</pre></div>
</body>
</html>
"""

# --- 3. FLASK ROUTES ---

@app.route('/')
def index():
    # Show the main form
    return render_template_string(HTML_FORM.replace("{model}", GEMINI_MODEL))

@app.route('/summarize', methods=['POST'])
def summarize():
    youtube_url = request.form.get("youtube_url", "").strip()
    vid = get_video_id(youtube_url)
    if not vid:
        return render_template_string(HTML_FORM.replace("{model}", GEMINI_MODEL), error="Invalid YouTube URL.")

    # 1) Transcript (Local first → MCP fallback)
    ok, transcript, source = local_transcript(vid)
    if not ok:
        # Try MCP server as fallback
        ok, transcript, source = call_mcp_transcript(youtube_url)
        if not ok:
            # brief jittered retry
            time.sleep(random.uniform(0.4, 1.2))
            ok, transcript, source = call_mcp_transcript(youtube_url)

    if not ok or not transcript:
        return render_template_string(HTML_FORM.replace("{model}", GEMINI_MODEL), error=f"Could not get transcript: {source}")

    # 2) Guardrails
    transcript = safe_cut(transcript, MAX_TRANSCRIPT_CHARS)
    chunks = list(chunk_text(transcript, CHUNK_CHARS))

    # 3) Summarize (map-reduce)
    try:
        if len(chunks) == 1:
            cfg = gtypes.GenerateContentConfig(temperature=0.2)
            prompt = (
                f"Write ~{SUMMARY_BULLET_COUNT} crisp bullet points for parents/kids. "
                f"Keep it actionable; include concrete how-tos.\n\n{chunks[0]}"
            )
            resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt, config=cfg)
            summary = resp.text.strip()
        else:
            summary = summarize_chunks(chunks, SUMMARY_BULLET_COUNT)
    except Exception as e:
        return render_template_string(HTML_FORM.replace("{model}", GEMINI_MODEL), error=f"Could not generate summary: {e}")

    return render_template_string(HTML_RESULT, summary=summary, transcript=transcript, source=source)

# --- 4. RUN THE APP ---
if __name__ == '__main__':
    # Use port 5001 to avoid conflicts with other common ports
    app.run(debug=True, port=5001)