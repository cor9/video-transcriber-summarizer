from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS
import os, time, random, requests
from urllib.parse import urlparse, parse_qs

# Optional libs
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    HAS_YT = True
except Exception:
    HAS_YT = False

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

# Config / env
MCP_SERVER_URL = (os.environ.get("MCP_SERVER_URL") or "").rstrip("/")
MCP_API_KEY    = os.environ.get("MCP_API_KEY")
MAX_TRANSCRIPT_CHARS = int(os.environ.get("MAX_TRANSCRIPT_CHARS", "160000"))
CHUNK_CHARS           = int(os.environ.get("CHUNK_CHARS", "12000"))
SUMMARY_BULLETS       = int(os.environ.get("SUMMARY_BULLETS", "8"))
USE_STT               = (os.environ.get("USE_STT_FALLBACK", "false").lower() == "true")
DEEPGRAM_API_KEY      = os.environ.get("DEEPGRAM_API_KEY")

app = Flask(__name__)
CORS(app)

HTML_FORM = """<!doctype html><meta charset="utf-8"><title>VidScribe2AI</title>
<body style="font-family:system-ui;max-width:760px;margin:40px auto;padding:20px;background:#fafafa">
<h1>VidScribe2AI</h1><p style="color:#666">Paste a YouTube URL. Transcripts via MCP → local fallback → optional STT. Summaries via Gemini.</p>
<form method="post" action="/summarize">
<input name="youtube_url" type="url" placeholder="https://www.youtube.com/watch?v=..." required style="width:100%;padding:10px;border:1px solid #ddd;border-radius:6px">
<button style="margin-top:10px;padding:10px 14px;border:0;border-radius:6px;background:#0b5fff;color:#fff">Summarize</button>
</form></body>"""

def wants_json() -> bool:
    return "application/json" in (request.headers.get("accept",""))

@app.get("/")
def home():
    return jsonify(ok=True, runtime="python3.11") if wants_json() else render_template_string(HTML_FORM)

@app.get("/health")
def health():
    return jsonify(ok=True, runtime="python3.11")

@app.get("/diag")
def diag():
    return jsonify(
        mcp_server_url=bool(MCP_SERVER_URL),
        mcp_api_key_set=bool(MCP_API_KEY),
        gemini_key_set=bool(GENAI_API_KEY),
        deepgram_key_set=bool(DEEPGRAM_API_KEY),
        has_local_yt=HAS_YT,
        use_stt=USE_STT
    )

# ------------ transcript helpers ------------
def get_video_id(url: str):
    if not url: return None
    q = urlparse(url); host = (q.hostname or "").lower() if q.hostname else ""
    if "youtu.be" in host: return q.path.lstrip("/")
    if "youtube.com" in host:
        if q.path == "/watch": return parse_qs(q.query).get("v", [None])[0]
        if q.path.startswith(("/embed/", "/v/")):
            parts = q.path.split("/")
            return parts[2] if len(parts) > 2 else None
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
            return False, None, f"MCP status {r.status_code}: {r.text[:200]}"
        data = r.json()
        if not data.get("success"):
            return False, None, f"MCP error: {data.get('error','unknown')}"
        return True, data.get("transcript",""), "MCP"
    except requests.RequestException as e:
        return False, None, f"MCP network error: {e}"

def fetch_transcript_local(video_url: str):
    if not HAS_YT:
        return False, None, "Local API unavailable"
    vid = get_video_id(video_url)
    if not vid:
        return False, None, "Invalid YouTube URL"
    try:
        # broader, smarter fallback: native en -> generated en -> translate any -> any
        transcripts = YouTubeTranscriptApi.list_transcripts(vid)

        for lang in ("en","en-US","en-GB"):
            try:
                t = transcripts.find_manually_created_transcript([lang]).fetch()
                return True, " ".join(x.get("text","") for x in t), "Local API"
            except Exception: pass
            try:
                t = transcripts.find_generated_transcript([lang]).fetch()
                return True, " ".join(x.get("text","") for x in t), "Local API"
            except Exception: pass

        for tr in transcripts:
            try:
                t = tr.translate('en').fetch()
                return True, " ".join(x.get("text","") for x in t), "Local API (translated)"
            except Exception: continue

        for tr in transcripts:
            try:
                t = tr.fetch()
                return True, " ".join(x.get("text","") for x in t), f"Local API ({tr.language_code})"
            except Exception: continue

        return False, None, "No captions found on YouTube"
    except Exception as e:
        return False, None, f"Captions unavailable: {e}"

def fetch_transcript_stt(video_url: str, timeout=60):
    # Optional Deepgram fallback. Only runs if USE_STT is true and key is set.
    if not (USE_STT and DEEPGRAM_API_KEY):
        return False, None, "STT disabled"
    try:
        import yt_dlp
        ydl_opts = {"skip_download": True, "quiet": True, "format": "bestaudio/best"}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            audio_url = next((f["url"] for f in info["formats"] if f.get("acodec") != "none"), None)
        if not audio_url:
            return False, None, "No audio URL"
    except Exception as e:
        return False, None, f"yt-dlp error: {e}"
    try:
        r = requests.post(
            "https://api.deepgram.com/v1/listen?model=nova-2-general&smart_format=true&language=en",
            headers={"Authorization": f"Token {DEEPGRAM_API_KEY}", "Content-Type": "application/json"},
            json={"url": audio_url}, timeout=timeout
        )
        if r.status_code != 200:
            return False, None, f"Deepgram {r.status_code}: {r.text[:200]}"
        d = r.json()
        try:
            alts = d["results"]["channels"][0]["alternatives"]
            if alts and "paragraphs" in alts[0]:
                paras = alts[0]["paragraphs"]["paragraphs"]
                text = " ".join(seg["text"] for p in paras for seg in p["sentences"]).strip()
            else:
                text = alts[0].get("transcript","").strip()
        except Exception:
            text = ""
        return (True, text, "Deepgram") if text else (False, None, "Deepgram returned empty text")
    except Exception as e:
        return False, None, f"Deepgram error: {e}"

# ------------ summary helpers ------------
def safe_cut(s: str, limit: int) -> str:
    return s if len(s) <= limit else s[:limit]

def chunk_text(s: str, size: int):
    for i in range(0, len(s), size):
        yield s[i:i+size]

def summarize_text(text: str, bullets=8):
    if not client:
        return False, "Model not configured (set GEMINI_API_KEY)"
    cfg = gtypes.GenerateContentConfig(temperature=0.2)
    if len(text) <= CHUNK_CHARS:
        prompt = f"Write ~{bullets} crisp, actionable bullets for parents of young actors. Keep names, steps, and numbers.\n\n{text}"
        resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt, config=cfg)
        return True, resp.text.strip()
    parts = []
    chunks = list(chunk_text(text, CHUNK_CHARS))
    for i, ch in enumerate(chunks, 1):
        p = f"Segment {i}/{len(chunks)}. Extract up to {max(4, bullets//2)} tight bullets. Only new info.\n\n{ch}"
        parts.append(client.models.generate_content(model=GEMINI_MODEL, contents=p, config=cfg).text.strip())
    m = "Merge and deduplicate into ~{bullets} tight bullets, concrete and useful:\n\n" + "\n\n".join(parts)
    final = client.models.generate_content(model=GEMINI_MODEL, contents=m, config=cfg)
    return True, final.text.strip()

# ------------ main route ------------
def fail(http, where, detail):
    return jsonify(ok=False, where=where, error=str(detail)), http

@app.post("/summarize")
def summarize():
    # accept form or JSON
    youtube_url = request.form.get("youtube_url") if request.form else None
    if not youtube_url:
        body = request.get_json(silent=True) or {}
        youtube_url = body.get("youtube_url")
    if not youtube_url:
        return fail(400, "input", "Missing youtube_url")

    # MCP first (with jittered retry)
    ok, transcript, source = fetch_transcript_mcp(youtube_url)
    if not ok:
        time.sleep(random.uniform(0.3, 0.9))
        ok, transcript, source = fetch_transcript_mcp(youtube_url)

    # Local captions fallback
    if not ok:
        ok, transcript, source = fetch_transcript_local(youtube_url)

    # Optional STT last resort
    if not ok:
        ok, transcript, source = fetch_transcript_stt(youtube_url)

    if not ok or not transcript:
        return fail(422, "transcript", source)

    transcript = safe_cut(transcript, MAX_TRANSCRIPT_CHARS)

    # Summarize if model configured; else return snippet
    if client:
        sok, summary = summarize_text(transcript, bullets=SUMMARY_BULLETS)
        if not sok:
            return fail(502, "summary", summary)
        return jsonify(ok=True, source=source, summary=summary, chars=len(transcript))
    snippet = transcript[:1200] + ("..." if len(transcript) > 1200 else "")
    return jsonify(ok=True, source=source, transcript=snippet, note="Set GEMINI_API_KEY for summaries")

if __name__ == "__main__":
    app.run(debug=True, port=5001)