import os, re, uuid, markdown, tempfile, json, base64
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import google.generativeai as genai
from urllib.parse import urlparse, parse_qs, quote
from .captions import get_captions
from .limiter import fetch_slot

# Decode cookies at cold start for YouTube bot avoidance
COOKIES_B64 = os.getenv("YT_COOKIES_B64", "")
if COOKIES_B64:
    try:
        with open("/tmp/youtube_cookies.txt", "wb") as f:
            f.write(base64.b64decode(COOKIES_B64))
        print("Cookies decoded successfully")
    except Exception as e:
        print("Failed to write cookies:", e)

# Log cookies file status
p = "/tmp/youtube_cookies.txt"
if os.path.exists(p):
    size = os.path.getsize(p)
    print(f"cookies.txt size: {size} bytes")
    if size == 0:
        print("WARNING: cookies.txt is empty!")
else:
    print("cookies.txt not found - YouTube requests will be more likely to hit rate limits")

# API key is now handled by _get_gemini_key() function

app = Flask(__name__)

# Serve static files (images, favicon, etc.)
@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files from public directory"""
    if filename.endswith(('.ico', '.svg', '.png', '.jpg', '.jpeg', '.gif', '.css', '.js')):
        return send_from_directory('../public', filename)
    return "Not found", 404

def _get_gemini_key() -> str:
    """Get Gemini API key from either GEMINI_API_KEY or GOOGLE_API_KEY"""
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("Missing GEMINI_API_KEY (or GOOGLE_API_KEY) in server env")
    return key.strip()

def get_gemini(model_name="gemini-1.5-flash"):
    """Get configured Gemini model"""
    key = _get_gemini_key()
    genai.configure(api_key=key)
    return genai.GenerativeModel(model_name)

def is_youtube_url(url: str) -> bool:
    return "youtube.com" in url.lower() or "youtu.be" in url.lower()

def summarize_with_gemini(text: str, summary_format: str = "bullet_points"):
    """Real Gemini summarization with timing and usage tracking"""
    import time
    import random
    
    if not text or len(text) < 40:
        raise ValueError("Transcript too short after cleaning.")

    MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    genai.configure(api_key=_get_gemini_key())

    prompts = {
        "bullet_points": "Summarize in crisp bullet points with actionable takeaways.\n\nTranscript:\n{t}",
        "key_insights":  "Extract key insights with short headings + one sentence each.\n\nTranscript:\n{t}",
        "detailed_summary": "Structured summary: purpose, key points, examples, conclusions, next steps.\n\nTranscript:\n{t}",
    }
    prompt = prompts.get(summary_format, prompts["bullet_points"]).format(t=text[:200_000])

    model = genai.GenerativeModel(MODEL_NAME)
    last_err = None
    for attempt in range(1, 4):
        t0 = time.time()
        try:
            resp = model.generate_content(prompt)
            elapsed = round((time.time() - t0) * 1000)  # ms
            out = (resp.text or "").strip()
            # Log truth serum
            usage = getattr(resp, "usage_metadata", None)
            print(f"[GEMINI] attempt={attempt} model={MODEL_NAME} ms={elapsed} "
                  f"chars_out={len(out)} usage={usage}")
            if not out:
                raise RuntimeError("Empty response from Gemini")
            return out, elapsed, usage
        except Exception as e:
            last_err = e
            print(f"[GEMINI] attempt={attempt} failed: {e}")
            time.sleep(min(2 ** attempt + random.random(), 8))
    raise RuntimeError(f"Gemini summarization failed: {last_err}")

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

def srt_to_text(srt: str) -> str:
    """Extract text from SRT subtitle format"""
    out = []
    for line in srt.splitlines():
        line = line.strip()
        if not line or line.isdigit() or "-->" in line: 
            continue
        out.append(line)
    return "\n".join(out).strip()

def vtt_to_text(vtt: str) -> str:
    """Extract text from VTT subtitle format"""
    out = []
    header_skipped = False
    for line in vtt.splitlines():
        line = line.rstrip("\n")
        if not header_skipped:
            if line.strip().lower().startswith("webvtt"):  # drop header
                header_skipped = True
            continue
        l = line.strip()
        if not l or "-->" in l: 
            continue
        out.append(l)
    return "\n".join(out).strip()

def clean_paste(text: str) -> str:
    """Clean pasted text by removing Tactiq metadata and timestamps"""
    import re
    
    TACTIQ_GARBAGE = re.compile(
        r"""^(?:\s*#?\s*
            (?:tactiq\.io.*|no\stitle\sfound|https?://(?:www\.)?youtube\.com/.*|
             https?://youtu\.be/.*|No\s*text\s*$)
        )""",
        re.IGNORECASE | re.VERBOSE,
    )
    
    # Also match lines that start with # and contain tactiq garbage
    TACTIQ_HEADER = re.compile(r"^\s*#.*(?:tactiq|no\s*title\s*found)", re.IGNORECASE)

    TIME_AT_START = re.compile(r"^\s*\d{2}:\d{2}:\d{2}(?:[.,]\d{1,3})?(?:\s*-->\s*\d{2}:\d{2}:\d{2}(?:[.,]\d{1,3})?)?\s*")
    TIME_INLINE   = re.compile(r"\b\d{2}:\d{2}:\d{2}(?:[.,]\d{1,3})?\b")

    out = []
    for line in text.splitlines():
        if TACTIQ_GARBAGE.match(line) or TACTIQ_HEADER.match(line):
            continue
        # remove leading timestamps
        line = TIME_AT_START.sub("", line)
        # kill orphan timing lines and arrows
        if not line.strip() or line.strip() == "-->":
            continue
        # optional: strip inline timecodes like "at 00:03:21,"
        line = TIME_INLINE.sub("", line).strip()
        if line:
            out.append(line)
    # collapse repeated spaces created by removing times
    cleaned = re.sub(r"\s{2,}", " ", "\n".join(out)).strip()
    return cleaned

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
                    <div style="display:flex; gap:12px; align-items:center; flex-wrap:wrap;">
                        <label><input type="radio" name="mode" value="youtube" checked> YouTube URL</label>
                        <label><input type="radio" name="mode" value="paste"> Paste Transcript</label>
                        <label><input type="radio" name="mode" value="upload"> Upload SRT/VTT</label>
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

                <div class="form-group" id="uploadGroup" style="display:none;">
                    <label for="subtitleFile">Upload SRT/VTT/TXT File</label>
                    <input type="file" id="subtitleFile" name="subtitleFile" accept=".srt,.vtt,.txt" style="width:100%; padding:12px; border:2px solid #e1e8ed; border-radius:8px;">
                    <small style="color:#666;font-size:.9em;display:block;margin-top:5px;">
                        Upload subtitle files (SRT/VTT) or text files (TXT) when YouTube is rate-limited. We'll extract the text and summarize it.
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

            <div class="progress" id="progress" style="display:none; margin-top:20px; padding:15px; background:#e8f4fd; border-radius:8px; border-left:4px solid #3498db;">
                <div id="progressText">Processing...</div>
            </div>

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
        const uploadGroup = document.getElementById('uploadGroup');
        document.querySelectorAll('input[name="mode"]').forEach(r => {
            r.addEventListener('change', () => {
                const mode = document.querySelector('input[name="mode"]:checked').value;
                urlGroup.style.display = mode === 'youtube' ? 'block' : 'none';
                pasteGroup.style.display = mode === 'paste' ? 'block' : 'none';
                uploadGroup.style.display = mode === 'upload' ? 'block' : 'none';
            });
        });

        const progress = msg => document.getElementById('progressText').textContent = msg;

        document.getElementById('transcribeForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const videoUrl = document.getElementById('videoUrl').value;
            const summaryFormat = document.getElementById('summaryFormat').value;
            const mode = document.querySelector('input[name="mode"]:checked').value;
            const rawTranscript = document.getElementById('rawTranscript')?.value || '';
            const subtitleFile = document.getElementById('subtitleFile')?.files[0];
            
            // Show loading state
            document.getElementById('submitBtn').disabled = true;
            document.getElementById('submitBtn').textContent = '🔄 Processing...';
            document.getElementById('results').style.display = 'none';
            document.getElementById('error').style.display = 'none';
            document.getElementById('progress').style.display = 'block';
            progress('Preparing request...');
            
            try {
                let response;
                
                if (mode === 'upload' && subtitleFile) {
                    progress('Uploading file...');
                    const formData = new FormData();
                    formData.append('file', subtitleFile);
                    formData.append('summary_format', summaryFormat);
                    
                    response = await fetch('/upload_subs', {
                        method: 'POST',
                        body: formData
                    });
                } else if (mode === 'paste') {
                    progress('Cleaning transcript...');
                    response = await fetch('/process', {
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
                } else {
                    progress('Fetching captions...');
                    response = await fetch('/process', {
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
                }
                
                progress('Summarizing with Gemini...');
                
                if (!response.ok) {
                    const err = await response.json().catch(()=>({error:`HTTP ${response.status}`}));
                    throw new Error(err.error || `HTTP ${response.status}`);
                }
                
                const data = await response.json();
                
                if (data.success) {
                    // Small UX buffer so it never looks "instant"
                    const genMs = data?.metrics?.generation_ms || 0;
                    await new Promise(r => setTimeout(r, Math.max(0, 900 - genMs)));
                    
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
                document.getElementById('progress').style.display = 'none';
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
    """Comprehensive health check that tests Gemini API connectivity"""
    import time
    
    key_src = "GEMINI_API_KEY" if os.getenv("GEMINI_API_KEY") else ("GOOGLE_API_KEY" if os.getenv("GOOGLE_API_KEY") else None)
    detail = {"key_source": key_src or "none"}
    
    if not key_src:
        return jsonify(detail | {"status": "no_key"}), 500
    
    try:
        import google.generativeai as genai
        genai.configure(api_key=os.getenv(key_src))
        t0 = time.time()
        txt = genai.GenerativeModel("gemini-1.5-flash").generate_content("say ok").text.strip()
        return jsonify(detail | {"status": "gemini_ok", "sample": txt, "rt": round(time.time() - t0, 2)}), 200
    except Exception as e:
        return jsonify(detail | {"status": "gemini_error", "error": str(e)}), 500

@app.route('/upload_subs', methods=['POST'])
def upload_subs():
    """Upload SRT/VTT/TXT files as escape hatch when YouTube is rate-limited"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if not file.filename.lower().endswith(('.srt', '.vtt', '.txt')):
            return jsonify({'success': False, 'error': 'Only SRT, VTT, and TXT files are supported'}), 400
        
        # Read file content
        content = file.read().decode('utf-8', errors='ignore')
        
        # Parse content based on file type
        if file.filename.lower().endswith('.txt'):
            # For TXT files, just clean the text (remove Tactiq garbage if present)
            text = clean_paste(content).strip()
        else:
            # For SRT/VTT files, parse subtitle content
            # For SRT/VTT files, parse subtitle content to plain text
            lines = []
            for line in content.splitlines():
                line = line.strip()
                if not line: continue
                if line.isdigit(): continue  # subtitle number
                if '-->' in line: continue   # timestamp
                if line.startswith('WEBVTT'): continue  # VTT header
                if line.startswith('NOTE'): continue    # VTT notes
                lines.append(line)
            text = '\n'.join(lines).strip()
        
        if len(text) < 20:
            return jsonify({'success': False, 'error': 'File appears to be empty or invalid after processing'}), 400
        
        # Get summary format
        summary_format = request.form.get('summary_format', 'bullet_points')
        
        # Generate summary with timing metrics
        base_id = str(uuid.uuid4())[:8]
        summary_md, gen_ms, usage = summarize_with_gemini(text, summary_format)
        download_content = generate_download_content(base_id, text, summary_md)
        
        # Generate download links
        transcript_data = f"data:text/plain;charset=utf-8,{quote(text)}"
        markdown_data = f"data:text/markdown;charset=utf-8,{quote(summary_md)}"
        html_data = f"data:text/html;charset=utf-8,{quote(download_content['html'])}"
        
        links = f'<a href="{transcript_data}" download="{base_id}.txt" target="_blank">📄 Download Transcript</a> '
        links += f'<a href="{markdown_data}" download="{base_id}.md" target="_blank">📝 Download Markdown</a> '
        links += f'<a href="{html_data}" download="{base_id}.html" target="_blank">📄 Download HTML</a>'
        
        MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        body = f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
          <h3 style="color:#2c3e50;margin-bottom:12px;">Transcript (from {secure_filename(file.filename)})</h3>
          <div style="background:#f8f9fa;padding:12px;border-radius:8px;white-space:pre-wrap;max-height:420px;overflow:auto;">{text}</div>
          <h3 style="color:#2c3e50;margin:20px 0 12px;">Summary ({summary_format.replace('_',' ').title()})</h3>
          <div style="background:#e8f4fd;padding:12px;border-radius:8px;border-left:4px solid #3498db;">{markdown.markdown(summary_md or '')}</div>
          <div style="margin-top:10px;font-size:12px;color:#666">
            Generated by {MODEL_NAME} in ~{gen_ms} ms
          </div>
        </div>
        """
        
        return jsonify({
            'success': True, 
            'transcript': body, 
            'download_links': links, 
            'message': f'Processed uploaded {secure_filename(file.filename)} file.',
            'metrics': {"model": MODEL_NAME, "generation_ms": gen_ms}
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

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
            # Clean the pasted text to remove Tactiq metadata
            cleaned_text = clean_paste(raw_transcript)
            if len(cleaned_text) < 50:
                return jsonify({'success': False, 'error': 'Transcript paste didn\'t have usable text after cleaning.'}), 400
            base_id = str(uuid.uuid4())[:8]
            
            # Get summary with timing metrics
            summary_md, gen_ms, usage = summarize_with_gemini(cleaned_text, summary_format)
            download_content = generate_download_content(base_id, cleaned_text, summary_md)

            # Generate download links with data URLs for serverless environment
            transcript_data = f"data:text/plain;charset=utf-8,{quote(cleaned_text)}"
            markdown_data = f"data:text/markdown;charset=utf-8,{quote(summary_md)}"
            html_data = f"data:text/html;charset=utf-8,{quote(download_content['html'])}"
            
            links = f'<a href="{transcript_data}" download="{base_id}.txt" target="_blank">📄 Download Transcript</a> '
            links += f'<a href="{markdown_data}" download="{base_id}.md" target="_blank">📝 Download Markdown</a> '
            links += f'<a href="{html_data}" download="{base_id}.html" target="_blank">📄 Download HTML</a>'

            MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
            body = f"""
            <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
              <h3 style="color:#2c3e50;margin-bottom:12px;">Transcript (cleaned)</h3>
              <div style="background:#f8f9fa;padding:12px;border-radius:8px;white-space:pre-wrap;max-height:420px;overflow:auto;">{cleaned_text}</div>
              <h3 style="color:#2c3e50;margin:20px 0 12px;">Summary ({summary_format.replace('_',' ').title()})</h3>
              <div style="background:#e8f4fd;padding:12px;border-radius:8px;border-left:4px solid #3498db;">{markdown.markdown(summary_md or '')}</div>
              <div style="margin-top:10px;font-size:12px;color:#666">
                Generated by {MODEL_NAME} in ~{gen_ms} ms
              </div>
            </div>
            """
            return jsonify({
                'success': True, 
                'transcript': body, 
                'download_links': links, 
                'message': 'Processed pasted transcript.',
                'metrics': {"model": MODEL_NAME, "generation_ms": gen_ms}
            })

        # YouTube mode
        if not video_url or not video_url.startswith(('http://','https://')):
            return jsonify({'success': False, 'error': 'Provide a valid http(s) URL'}), 400
        if not is_youtube_url(video_url):
            return jsonify({'success': False, 'error': 'Use a YouTube link or switch to Paste mode.'}), 400

        # Use resilient caption fetcher with cache + backoff + concurrency gate
        with fetch_slot():
            text, diag = get_captions(video_url)
        if not text:
            # Determine appropriate error response based on diagnostics
            if diag.get("reason") == "rate_limited_or_blocked":
                return jsonify({
                    'success': False,
                    'error': 'Captions temporarily unavailable (rate-limited by YouTube).',
                    'diagnostics': diag,
                    'fixes': [
                        'Try again in a minute (we automatically retry with backoff).',
                        'Switch to Paste mode (works instantly).',
                        'Upload an SRT/VTT file using the file upload option.',
                    ]
                }), 429
            else:
                return jsonify({
                    'success': False,
                    'error': 'Captions not available or not accessible for this video.',
                    'diagnostics': diag,
                    'fixes': [
                        'Check if the video actually has captions (CC).',
                        'If they are non-English, we attempt auto-translation; if blocked, paste your own transcript.',
                        'Avoid age-restricted/private/members-only videos.',
                        'Try again later for recent uploads (captions sometimes lag).'
                    ]
                }), 404

        base_id = str(uuid.uuid4())[:8]

        # Get summary with timing metrics
        summary_md, gen_ms, usage = summarize_with_gemini(text, summary_format)
        download_content = generate_download_content(base_id, text, summary_md)

        # Generate download links with data URLs for serverless environment
        transcript_data = f"data:text/plain;charset=utf-8,{quote(text)}"
        markdown_data = f"data:text/markdown;charset=utf-8,{quote(summary_md)}"
        html_data = f"data:text/html;charset=utf-8,{quote(download_content['html'])}"
        
        links = f'<a href="{transcript_data}" download="{base_id}.txt" target="_blank">📄 Download Transcript</a> '
        links += f'<a href="{markdown_data}" download="{base_id}.md" target="_blank">📝 Download Markdown</a> '
        links += f'<a href="{html_data}" download="{base_id}.html" target="_blank">📄 Download HTML</a>'

        MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        body = f"""
            <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
          <h3 style="color:#2c3e50;margin-bottom:12px;">Transcript</h3>
          <div style="background:#f8f9fa;padding:12px;border-radius:8px;white-space:pre-wrap;max-height:420px;overflow:auto;">{text}</div>
          <h3 style="color:#2c3e50;margin:20px 0 12px;">Summary ({summary_format.replace('_',' ').title()})</h3>
          <div style="background:#e8f4fd;padding:12px;border-radius:8px;border-left:4px solid #3498db;">{markdown.markdown(summary_md or '')}</div>
          <div style="margin-top:10px;font-size:12px;color:#666">
            Generated by {MODEL_NAME} in ~{gen_ms} ms
          </div>
            </div>
            """
        return jsonify({
            'success': True,
            'transcript': body, 
            'download_links': links, 
            'message': 'Processed via YouTube captions.',
            'metrics': {"model": MODEL_NAME, "generation_ms": gen_ms}
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)