from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS
import os, time, random, requests
from urllib.parse import urlparse, parse_qs

# ---- Optional local fallback (will work if installed) ----
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    HAS_YT = True
except Exception:
    HAS_YT = False

# ---- Optional Gemini (enable with GEMINI_API_KEY) ----
try:
    from google import genai
    from google.genai import types as gtypes
    GENAI_API_KEY = os.environ.get("GEMINI_API_KEY")
    GEMINI_MODEL  = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    client = genai.Client(api_key=GENAI_API_KEY) if GENAI_API_KEY else None
except Exception:
    client = None
    GENAI_API_KEY = None
    GEMINI_MODEL = "gemini-2.5-flash"

app = Flask(__name__)
CORS(app)

# ---- Config ----
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "").rstrip("/")
MCP_API_KEY    = os.environ.get("MCP_API_KEY")
MAX_TRANSCRIPT_CHARS = int(os.environ.get("MAX_TRANSCRIPT_CHARS", "160000"))
CHUNK_CHARS           = int(os.environ.get("CHUNK_CHARS", "12000"))
SUMMARY_BULLETS       = int(os.environ.get("SUMMARY_BULLETS", "10"))

HTML_FORM = """<!doctype html>
<html><head><meta charset="utf-8"><title>Simple YouTube Summarizer</title>
<style>
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;max-width:800px;margin:40px auto;padding:20px;background:#fafafa}
h1{margin:0 0 8px} p.small{color:#666}
input,button{font-size:16px} input{width:100%;padding:10px;border:1px solid #ddd;border-radius:6px}
button{padding:10px 14px;margin-top:10px;border:0;border-radius:6px;background:#0b5fff;color:#fff;cursor:pointer}
button:hover{background:#0a52e0}
pre{white-space:pre-wrap;word-wrap:break-word}
.box{background:#fff;padding:16px;border-radius:8px;box-shadow:0 1px 4px rgba(0,0,0,.06)}
.err{color:#d93025;font-weight:600}
</style></head><body>
<h1>Simple YouTube Summarizer</h1>
<p class="small">Transcripts via MCP (with local fallback). Summaries via Gemini.</p>
<div class="box">
  <form method="post" action="/summarize">
    <input type="url" name="youtube_url" placeholder="https://www.youtube.com/watch?v=..." required>
    <button type="submit">Summarize</button>
  </form>
</div>
</body></html>"""

# ---------- Helpers ----------
def wants_json():
    return "application/json" in (request.headers.get("accept",""))

@app.get("/")
def home():
    return jsonify(ok=True, runtime="python3.11") if wants_json() else render_template_string(HTML_FORM)

@app.get("/health")
def health():
    return jsonify(ok=True, runtime="python3.11")

@app.get("/test-transcript")
def test_transcript():
    """Debug endpoint to test transcript fetching"""
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    vid = get_video_id(test_url)
    
    result = {
        "video_id": vid,
        "has_yt_lib": HAS_YT,
        "tests": []
    }
    
    if HAS_YT and vid:
        # Test different approaches
        probes = [None, ['en'], ['es'], ['fr']]
        for p in probes:
            try:
                lst = (YouTubeTranscriptApi.get_transcript(vid, languages=p) if p
                       else YouTubeTranscriptApi.get_transcript(vid))
                txt = " ".join(d.get("text","") for d in lst)
                result["tests"].append({
                    "lang": p or "auto",
                    "success": True,
                    "length": len(txt),
                    "preview": txt[:100] + "..." if len(txt) > 100 else txt
                })
                break  # Stop on first success
            except Exception as e:
                result["tests"].append({
                    "lang": p or "auto", 
                    "success": False,
                    "error": str(e)[:200]
                })
    
    return jsonify(result)

def get_video_id(url: str):
    if not url: return None
    q = urlparse(url); host = (q.hostname or "").lower() if q.hostname else ""
    if "youtu.be" in host: return q.path.lstrip("/")
    if "youtube.com" in host:
        if q.path == "/watch": return parse_qs(q.query).get("v", [None])[0]
        if q.path.startswith(("/embed/", "/v/")): parts = q.path.split("/"); return parts[2] if len(parts)>2 else None
    return None

def fetch_transcript_mcp(video_url: str, timeout=30):
    if not MCP_SERVER_URL:
        return False, None, "MCP_SERVER_URL unset"
    headers = {"Accept": "application/json"}
    if MCP_API_KEY:
        headers["x-api-key"] = MCP_API_KEY
    try:
        r = requests.post(f"{MCP_SERVER_URL}/api/transcript",
                          json={"video_url": video_url},
                          headers=headers, timeout=timeout)
        if r.status_code != 200:
            return False, None, f"MCP status {r.status_code}: {r.text[:160]}"
        data = r.json()
        if not data.get("success"):
            return False, None, f"MCP error: {data.get('error','unknown')}"
        return True, data.get("transcript",""), "MCP"
    except requests.exceptions.RequestException as e:
        return False, None, f"MCP network error: {e}"

def fetch_transcript_local(video_url: str):
    if not HAS_YT:
        return False, None, "Local API unavailable"
    vid = get_video_id(video_url)
    if not vid:
        return False, None, "Invalid YouTube URL"
    
    # Try different approaches with better error handling
    probes = [None, ['en'], ['es'], ['fr'], ['de'], ['it'], ['pt']]
    
    for p in probes:
        try:
            lst = (YouTubeTranscriptApi.get_transcript(vid, languages=p) if p
                   else YouTubeTranscriptApi.get_transcript(vid))
            txt = " ".join(d.get("text","") for d in lst)
            if txt.strip():  # Make sure we got actual content
                return True, txt, f"Local API ({p or 'auto'})"
        except Exception as e:
            # Log the error but continue trying
            print(f"Transcript fetch failed for {p}: {str(e)[:100]}")
            continue
    
    # Last resort: try to get any available transcript using list_transcripts
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(vid)
        for transcript in transcript_list:
            try:
                data = transcript.fetch()
                txt = " ".join(d.get("text","") for d in data)
                if txt.strip():
                    return True, txt, f"Local API ({transcript.language_code})"
            except Exception as e:
                print(f"Failed to fetch {transcript.language_code}: {str(e)[:100]}")
                continue
    except Exception as e:
        print(f"List transcripts failed: {str(e)[:100]}")
        
    return False, None, f"No transcripts available for video {vid}"

def safe_cut(s: str, limit: int) -> str:
    return s if len(s) <= limit else s[:limit]

def chunk_text(s: str, size: int):
    for i in range(0, len(s), size):
        yield s[i:i+size]

def summarize_text(text: str, bullets=10):
    if not client:
        return False, "Model not configured (set GEMINI_API_KEY)"
    cfg = gtypes.GenerateContentConfig(temperature=0.2)
    # Single-shot or map-reduce depending on length
    if len(text) <= CHUNK_CHARS:
        prompt = (f"Write ~{bullets} crisp, actionable bullets for parents of young actors."
                  f" Keep names, steps, numbers.\n\n{text}")
        resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt, config=cfg)
        return True, resp.text.strip()
    # Map-reduce
    partials = []
    chunks = list(chunk_text(text, CHUNK_CHARS))
    for idx, ch in enumerate(chunks, 1):
        prompt = (f"Segment {idx}/{len(chunks)}. Extract up to {max(4, bullets//2)} bullets."
                  f" Only new info, concise.\n\n{ch}")
        partials.append(client.models.generate_content(model=GEMINI_MODEL, contents=prompt, config=cfg).text.strip())
    merge_prompt = (f"Merge and deduplicate into ~{bullets} tight bullets, concrete and useful:\n\n" +
                    "\n\n".join(partials))
    final = client.models.generate_content(model=GEMINI_MODEL, contents=merge_prompt, config=cfg)
    return True, final.text.strip()

# ---------- Main route ----------
@app.post("/summarize")
def summarize():
    # Accept both form posts and JSON posts
    youtube_url = request.form.get("youtube_url") if request.form else None
    if not youtube_url:
        body = request.get_json(silent=True) or {}
        youtube_url = body.get("youtube_url")

    if not youtube_url:
        return jsonify(ok=False, error="Missing youtube_url"), 400

    # 1) Try MCP
    ok, transcript, source = fetch_transcript_mcp(youtube_url)
    if not ok:
        # small jittered retry
        time.sleep(random.uniform(0.3, 0.9))
        ok, transcript, source = fetch_transcript_mcp(youtube_url)

    # 2) Fallback to local
    if not ok:
        ok, transcript, source = fetch_transcript_local(youtube_url)

    if not ok or not transcript:
        return jsonify(ok=False, error=source), 502

    transcript = safe_cut(transcript, MAX_TRANSCRIPT_CHARS)

    # 3) Summarize (if configured); otherwise return transcript snippet
    if client:
        sok, summary = summarize_text(transcript, bullets=SUMMARY_BULLETS)
        if not sok:
            return jsonify(ok=False, error=summary), 502
        return jsonify(ok=True, source=source, summary=summary, chars=len(transcript))

    # No Gemini key set: still return transcript snippet so UI isn't empty
    snippet = transcript[:1200] + ("..." if len(transcript) > 1200 else "")
    return jsonify(ok=True, source=source, transcript=snippet, note="Set GEMINI_API_KEY for summaries")

if __name__ == "__main__":
    app.run(debug=True, port=5001)