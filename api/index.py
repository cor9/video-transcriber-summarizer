import os, re, uuid, markdown, tempfile, json
from flask import Flask, request, jsonify
import google.generativeai as genai
from urllib.parse import urlparse, parse_qs, quote
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
    CouldNotRetrieveTranscript,
    VideoUnavailable,
    TooManyRequests
)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

app = Flask(__name__)

def get_gemini(model="gemini-1.5-flash"):
    if not GOOGLE_API_KEY:
        return None
    genai.configure(api_key=GOOGLE_API_KEY)
    return genai.GenerativeModel(model)

# ---- robust video-id extraction
def extract_video_id(url: str) -> str | None:
    try:
        u = urlparse(url)
        host = (u.netloc or "").lower()
        path = u.path or ""
        qs = parse_qs(u.query)

        # Standard watch
        if "v" in qs and qs["v"]:
            return qs["v"][0][:11]

        # youtu.be short links
        if "youtu.be" in host:
            seg = path.strip("/").split("/")[0]
            return seg[:11] if seg else None

        # /embed/VIDEOID or /v/VIDEOID
        m = re.search(r"/(?:embed|v)/([0-9A-Za-z_-]{11})", path)
        if m:
            return m.group(1)

        # /shorts/VIDEOID
        m = re.search(r"/shorts/([0-9A-Za-z_-]{11})", path)
        if m:
            return m.group(1)

        # Fallback: any 11-char ID in path
        m = re.search(r"([0-9A-Za-z_-]{11})", path)
        if m:
            return m.group(1)
    except Exception:
        pass
    return None

def is_youtube_url(url: str) -> bool:
    return "youtube.com" in url.lower() or "youtu.be" in url.lower()

# ---------- PRIMARY: robust youtube-transcript-api pull ----------
def fetch_captions_primary(video_url: str,
                           prefer_langs=("en","en-US","en-GB"),
                           fallback_translate_to="en"):
    vid = extract_video_id(video_url)
    diag = {"video_id": vid, "step": None, "chosen": None, "langs_found": [], "generated": None, "translated": False}
    if not vid:
        return None, {**diag, "reason":"no_video_id"}

    # Step 1: direct preferred
    try:
        diag["step"] = "direct_preferred"
        entries = YouTubeTranscriptApi.get_transcript(vid, languages=list(prefer_langs))
        text = "\n".join(e.get("text","") for e in entries if e.get("text")).strip() or None
        if text:
            diag["chosen"] = "preferred_direct"
            return text, diag
    except (NoTranscriptFound, TranscriptsDisabled):
        pass
    except Exception as e:
        diag["direct_error"] = str(e)

    # Step 2: list & choose
    try:
        diag["step"] = "list_transcripts"
        tlist = YouTubeTranscriptApi.list_transcripts(vid)
        for t in tlist:
            diag["langs_found"].append({
                "language": t.language_code,
                "is_generated": t.is_generated,
                "is_translatable": t.is_translatable
            })

        def rank(t):
            try:
                pref_index = list(prefer_langs).index(t.language_code)
            except ValueError:
                pref_index = len(prefer_langs) + 1
            manual_bonus = 0 if not t.is_generated else 1
            return (pref_index, manual_bonus)

        cands = sorted(list(tlist), key=rank)

        # 2a) same-language
        for c in cands:
            if c.language_code in prefer_langs:
                txt = "\n".join(x.get("text","") for x in c.fetch() if x.get("text")).strip() or None
                if txt:
                    diag["chosen"] = {"language": c.language_code, "is_generated": c.is_generated}
                    diag["generated"] = c.is_generated
                    return txt, diag

        # 2b) translate if allowed
        if fallback_translate_to:
            for c in cands:
                if getattr(c, "is_translatable", False):
                    try:
                        t = c.translate(fallback_translate_to).fetch()
                        txt = "\n".join(x.get("text","") for x in t if x.get("text")).strip() or None
                        if txt:
                            diag["chosen"] = {"language": c.language_code, "is_generated": c.is_generated}
                            diag["generated"] = c.is_generated
                            diag["translated"] = True
                            return txt, diag
                    except Exception as te:
                        diag.setdefault("translate_errors", []).append(str(te))

        # 2c) any manual → any generated
        any_manual = [t for t in tlist if not t.is_generated]
        any_generated = [t for t in tlist if t.is_generated]
        for bucket in (any_manual, any_generated):
            for c in bucket:
                try:
                    txt = "\n".join(x.get("text","") for x in c.fetch() if x.get("text")).strip() or None
                    if txt:
                        diag["chosen"] = {"language": c.language_code, "is_generated": c.is_generated}
                        diag["generated"] = c.is_generated
                        return txt, diag
                except Exception as fe:
                    diag.setdefault("fetch_errors", []).append(str(fe))

        return None, {**diag, "reason":"no_working_track"}

    except TranscriptsDisabled:
        return None, {**diag, "reason":"captions_disabled"}
    except NoTranscriptFound:
        return None, {**diag, "reason":"no_transcripts"}
    except TooManyRequests:
        return None, {**diag, "reason":"rate_limited"}
    except VideoUnavailable:
        return None, {**diag, "reason":"video_unavailable"}
    except CouldNotRetrieveTranscript:
        return None, {**diag, "reason":"retrieve_failed"}
    except Exception as e:
        return None, {**diag, "reason":f"unexpected:{e}"}

# ---------- FALLBACK: yt-dlp subtitle pull (no video download) ----------
def fetch_captions_fallback_ytdlp(video_url: str, prefer_langs=("en","en-US","en-GB")):
    """
    Uses yt-dlp to fetch subtitles in SRT without downloading the media.
    Works on many cases where transcript API fails.
    """
    try:
        import yt_dlp
    except Exception as e:
        return None, {"reason": f"yt_dlp_missing:{e}"}

    ytid = extract_video_id(video_url) or str(uuid.uuid4())[:8]
    tmpdir = tempfile.mkdtemp(prefix="subs_")
    # allow 'en' and 'en-*', and auto subs
    sub_langs = ",".join(list(dict.fromkeys(list(prefer_langs)+["en.*","en"])))

    ydl_opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitlesformat": "srt",
        "subtitleslangs": [sub_langs],
        "paths": {"home": tmpdir, "temp": tmpdir},
        "outtmpl": os.path.join(tmpdir, "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            # Force download of only subs
            ydl.download([video_url])
    except Exception as e:
        return None, {"reason": f"yt_dlp_extract:{e}"}

    # Find an SRT in tmpdir
    srt_text = None
    try:
        for fname in os.listdir(tmpdir):
            if fname.startswith(ytid) and fname.endswith(".srt"):
                with open(os.path.join(tmpdir, fname), "r", encoding="utf-8", errors="ignore") as f:
                    srt_text = f.read()
                break
    except Exception as e:
        return None, {"reason": f"read_srt:{e}"}

    if not srt_text:
        return None, {"reason": "no_srt_output"}

    # SRT → plain text
    lines = []
    for line in srt_text.splitlines():
        line = line.strip()
        if not line: continue
        if line.isdigit(): continue
        if "-->" in line: continue
        lines.append(line)
    text = "\n".join(lines).strip() or None
    return text, {"used": "yt_dlp", "tmpdir": tmpdir}

# ---------- Wrapper: try primary, then fallback ----------
def fetch_youtube_captions_text(video_url: str):
    text, diag = fetch_captions_primary(video_url)
    if text:
        return text, {**diag, "path": "primary"}
    # Only fallback if clearly public but primary failed
    alt, ydiag = fetch_captions_fallback_ytdlp(video_url)
    if alt:
        return alt, {"path": "yt_dlp", **ydiag}
    return None, {"path": "none", "primary": diag, "fallback": ydiag}

def summarize_with_gemini(text: str, summary_format: str="bullet_points") -> str:
    model = get_gemini("gemini-1.5-flash")
    if not model:
        return text[:1200]  # minimal fallback (no key)
    prompts = {
        "bullet_points": "Summarize in crisp bullet points focusing on key ideas and actionable takeaways.\n\nTranscript:\n{t}",
        "key_insights": "Extract the most important insights with short headings and brief explanations.\n\nTranscript:\n{t}",
        "detailed_summary": "Write a clear, structured summary: topic/purpose, key points, notable examples, conclusions/next steps.\n\nTranscript:\n{t}",
    }
    prompt = prompts.get(summary_format, prompts["bullet_points"]).format(t=text[:200_000])
    resp = model.generate_content(prompt)
    return (resp.text or "").strip()

def generate_download_content(base_id: str, transcript_text: str, summary_md: str):
    """Generate download content for serverless environment (no file writing)"""
    html_body = markdown.markdown(summary_md or "")
    full_html = f"""<!doctype html><html><head><meta charset="utf-8"><title>{base_id} Summary</title>
<style>body{{font-family:Arial,sans-serif;line-height:1.6;max-width:900px;margin:40px auto;color:#333}}</style>
</head><body><h1>Summary</h1><div>{html_body}</div></body></html>"""
    
    return {
        'transcript': transcript_text or "",
        'markdown': summary_md or "",
        'html': full_html
    }

@app.route('/')
def index():
    # Return the HTML directly instead of using templates
    return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VidScribe2AI - YouTube Caption Transcription & Summarization</title>
    <link rel="icon" type="image/x-icon" href="/favicon.ico">
    <link rel="icon" type="image/svg+xml" href="/sitelogo.svg">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            padding: 0;
            margin: 0;
            position: relative;
            overflow-x: hidden;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: transparent;
            padding: 40px 20px;
            position: relative;
            z-index: 2;
        }

        .header {
            background: transparent;
            color: white;
            padding: 60px 0;
            text-align: center;
            position: relative;
            overflow: hidden;
        }

        .logo-container {
            position: relative;
            z-index: 2;
            margin-bottom: 40px;
            display: flex;
            justify-content: center;
            align-items: center;
        }

        .logo {
            width: 500px;
            height: 300px;
            position: relative;
            display: flex;
            justify-content: center;
            align-items: center;
        }

        .logo img {
            width: 100%;
            height: 100%;
            object-fit: contain;
        }

        .header p {
            font-size: 1.6em;
            opacity: 0.9;
            color: #b8d4f0;
            font-weight: 300;
            letter-spacing: 1px;
            margin-top: 20px;
        }

        .form-container {
            padding: 60px 40px;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            box-shadow: 0 25px 50px rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            margin-top: 40px;
        }

        .form-group {
            margin-bottom: 25px;
        }

        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #2c3e50;
        }

        input[type="url"] {
            width: 100%;
            padding: 15px;
            border: 2px solid #e1e8ed;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s ease;
        }

        input[type="url"]:focus {
            outline: none;
            border-color: #3498db;
            box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.1);
        }

        .submit-btn {
            width: 100%;
            padding: 20px;
            background: linear-gradient(135deg, #00b4d8 0%, #0077b6 100%);
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 18px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-top: 20px;
            position: relative;
            overflow: hidden;
            box-shadow: 0 8px 25px rgba(0, 180, 216, 0.3);
        }

        .submit-btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 15px 35px rgba(0, 180, 216, 0.4);
            background: linear-gradient(135deg, #0096c7 0%, #006494 100%);
        }

        .results {
            display: none;
            margin-top: 30px;
            padding: 30px;
            background: #f8f9fa;
            border-radius: 8px;
            border-left: 4px solid #27ae60;
        }

        .error {
            display: none;
            background: #e74c3c;
            color: white;
            padding: 15px;
            border-radius: 8px;
            margin-top: 20px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo-container">
                <div class="logo">
                    <img src="/sitelogo.svg" alt="VidScribe2AI Logo">
                </div>
            </div>
            <p>Transform YouTube videos into structured summaries using AI-powered caption transcription</p>
        </div>

        <div class="form-container">
            <form id="transcribeForm">
                <div class="form-group">
                    <label>Input Mode</label>
                    <div style="display:flex; gap:12px; align-items:center;">
                        <label><input type="radio" name="mode" value="youtube" checked> YouTube URL</label>
                        <label><input type="radio" name="mode" value="paste"> Paste Transcript</label>
                    </div>
                </div>

                <div class="form-group" id="urlGroup">
                    <label for="videoUrl">YouTube URL</label>
                    <input type="url" id="videoUrl" name="videoUrl" placeholder="https://youtube.com/watch?v=..." >
                    <small style="color:#666;font-size:.9em;display:block;margin-top:5px;">
                        Supported: YouTube links with captions (fast & free). Or switch to Paste Transcript for anything else.
                    </small>
                </div>

                <div class="form-group" id="pasteGroup" style="display:none;">
                    <label for="rawTranscript">Paste Transcript</label>
                    <textarea id="rawTranscript" name="rawTranscript" rows="12" placeholder="Paste the full transcript here…" style="width:100%; padding:12px; border:2px solid #e1e8ed; border-radius:8px; font-family:monospace;"></textarea>
                    <small style="color:#666;font-size:.9em;display:block;margin-top:5px;">
                        Tip: You can paste any text (meeting notes, article text, etc.). We'll summarize it.
                    </small>
                </div>

                <div class="form-group">
                    <label for="summaryFormat">Summary Format</label>
                    <select id="summaryFormat" name="summaryFormat" style="width: 100%; padding: 15px; border: 2px solid #e1e8ed; border-radius: 8px; font-size: 16px;">
                        <option value="bullet_points">📝 Bullet Points</option>
                        <option value="key_insights">💡 Key Insights</option>
                        <option value="detailed_summary">📋 Detailed Summary</option>
                    </select>
                </div>

                <button type="submit" class="submit-btn" id="submitBtn">🚀 Process</button>
            </form>

            <div class="error" id="error"></div>

            <div class="results" id="results">
                <h3>✅ Processing Complete!</h3>
                <div id="transcriptContent"></div>
            </div>
        </div>
    </div>

    <script>
        // mode toggle
        const urlGroup = document.getElementById('urlGroup');
        const pasteGroup = document.getElementById('pasteGroup');
        document.querySelectorAll('input[name="mode"]').forEach(r => {
            r.addEventListener('change', () => {
                const mode = document.querySelector('input[name="mode"]:checked').value;
                urlGroup.style.display = mode === 'youtube' ? 'block' : 'none';
                pasteGroup.style.display = mode === 'paste' ? 'block' : 'none';
            });
        });

        document.getElementById('transcribeForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const videoUrl = document.getElementById('videoUrl').value;
            const summaryFormat = document.getElementById('summaryFormat').value;
            const mode = document.querySelector('input[name="mode"]:checked').value;
            const rawTranscript = document.getElementById('rawTranscript')?.value || '';
            
            // Show loading state
            document.getElementById('submitBtn').disabled = true;
            document.getElementById('submitBtn').textContent = '🔄 Processing...';
            document.getElementById('results').style.display = 'none';
            document.getElementById('error').style.display = 'none';
            
            try {
                const response = await fetch('/process', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        mode,
                        video_url: videoUrl,
                        raw_transcript: rawTranscript,
                        summary_format: summaryFormat
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    // Show results
                    document.getElementById('transcriptContent').innerHTML = data.transcript;
                    // Add download links if available
                    if (data.download_links) {
                        document.getElementById('transcriptContent').innerHTML += '<div style="margin-top: 20px; text-align: center;">' + data.download_links + '</div>';
                    }
                    document.getElementById('results').style.display = 'block';
                } else {
                    // Handle structured error responses
                    let errorMessage = data.error || 'An error occurred';
                    if (data.suggestions) {
                        errorMessage += '<br><br><strong>Suggestions:</strong><ul>';
                        data.suggestions.forEach(suggestion => {
                            errorMessage += '<li>' + suggestion + '</li>';
                        });
                        errorMessage += '</ul>';
                    }
                    if (data.fixes) {
                        errorMessage += '<br><strong>Fixes:</strong><ul>';
                        data.fixes.forEach(fix => {
                            errorMessage += '<li>' + fix + '</li>';
                            });
                            errorMessage += '</ul>';
                        }
                    if (data.why) {
                        errorMessage += '<br><strong>Why:</strong> ' + data.why;
                    }
                    throw new Error(errorMessage);
                }
            } catch (error) {
                document.getElementById('error').innerHTML = 'Error: ' + error.message;
                document.getElementById('error').style.display = 'block';
            } finally {
                document.getElementById('submitBtn').disabled = false;
                document.getElementById('submitBtn').textContent = '🚀 Process';
            }
        });
    </script>
</body>
</html>
    '''

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy', 
        'google_api_configured': bool(os.getenv("GOOGLE_API_KEY")),
        'version': '4.2.1-diagnostics'
    })

@app.route('/process', methods=['POST'])
def process_video():
    try:
        data = request.get_json(force=True) or {}
        mode = (data.get('mode') or 'youtube').strip()
        video_url = (data.get('video_url') or '').strip()
        raw_transcript = (data.get('raw_transcript') or '').strip()
        summary_format = data.get('summary_format', 'bullet_points')

        # Paste mode
        if mode == 'paste' or raw_transcript:
            if len(raw_transcript) < 20:
                return jsonify({'success': False, 'error': 'Please paste a transcript (≥ 20 chars).'}), 400
            base_id = str(uuid.uuid4())[:8]
            summary_md = summarize_with_gemini(raw_transcript, summary_format)
            download_content = generate_download_content(base_id, raw_transcript, summary_md)

            # Generate download links with data URLs for serverless environment
            transcript_data = f"data:text/plain;charset=utf-8,{quote(raw_transcript)}"
            markdown_data = f"data:text/markdown;charset=utf-8,{quote(summary_md)}"
            html_data = f"data:text/html;charset=utf-8,{quote(download_content['html'])}"
            
            links = f'<a href="{transcript_data}" download="{base_id}.txt" target="_blank">📄 Download Transcript</a> '
            links += f'<a href="{markdown_data}" download="{base_id}.md" target="_blank">📝 Download Markdown</a> '
            links += f'<a href="{html_data}" download="{base_id}.html" target="_blank">📄 Download HTML</a>'

            body = f"""
            <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
              <h3 style="color:#2c3e50;margin-bottom:12px;">Transcript (pasted)</h3>
              <div style="background:#f8f9fa;padding:12px;border-radius:8px;white-space:pre-wrap;max-height:420px;overflow:auto;">{raw_transcript}</div>
              <h3 style="color:#2c3e50;margin:20px 0 12px;">Summary ({summary_format.replace('_',' ').title()})</h3>
              <div style="background:#e8f4fd;padding:12px;border-radius:8px;border-left:4px solid #3498db;">{markdown.markdown(summary_md or '')}</div>
            </div>
            """
            return jsonify({'success': True, 'transcript': body, 'download_links': links, 'message': 'Processed pasted transcript.'})

        # YouTube mode
        if not video_url or not video_url.startswith(('http://','https://')):
            return jsonify({'success': False, 'error': 'Provide a valid http(s) URL'}), 400
        if not is_youtube_url(video_url):
            return jsonify({'success': False, 'error': 'Use a YouTube link or switch to Paste mode.'}), 400

        base_id = extract_video_id(video_url) or str(uuid.uuid4())[:8]
        text, diag = fetch_youtube_captions_text(video_url)
        if not text:
            return jsonify({
                'success': False,
                'error': 'Captions not available or not accessible.',
                'diagnostics': diag,
                'fixes': [
                    'Check if the video actually has captions (CC).',
                    'If they are non-English, we attempt auto-translation; if blocked, paste your own transcript.',
                    'Avoid age-restricted/private/members-only videos.',
                    'Try again later for recent uploads (captions sometimes lag).'
                ]
            }), 404

        summary_md = summarize_with_gemini(text, summary_format)
        download_content = generate_download_content(base_id, text, summary_md)

        # Generate download links with data URLs for serverless environment
        transcript_data = f"data:text/plain;charset=utf-8,{quote(text)}"
        markdown_data = f"data:text/markdown;charset=utf-8,{quote(summary_md)}"
        html_data = f"data:text/html;charset=utf-8,{quote(download_content['html'])}"
        
        links = f'<a href="{transcript_data}" download="{base_id}.txt" target="_blank">📄 Download Transcript</a> '
        links += f'<a href="{markdown_data}" download="{base_id}.md" target="_blank">📝 Download Markdown</a> '
        links += f'<a href="{html_data}" download="{base_id}.html" target="_blank">📄 Download HTML</a>'

        body = f"""
            <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
          <h3 style="color:#2c3e50;margin-bottom:12px;">Transcript</h3>
          <div style="background:#f8f9fa;padding:12px;border-radius:8px;white-space:pre-wrap;max-height:420px;overflow:auto;">{text}</div>
          <h3 style="color:#2c3e50;margin:20px 0 12px;">Summary ({summary_format.replace('_',' ').title()})</h3>
          <div style="background:#e8f4fd;padding:12px;border-radius:8px;border-left:4px solid #3498db;">{markdown.markdown(summary_md or '')}</div>
            </div>
            """
        return jsonify({'success': True, 'transcript': body, 'download_links': links, 'message': 'Processed via YouTube captions.'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)