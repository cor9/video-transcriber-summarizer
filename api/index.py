import os, re, uuid, requests, markdown
from flask import Flask, request, jsonify
from googleapiclient.discovery import build
import google.generativeai as genai

# --- ENV
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

app = Flask(__name__)

# --- Gemini init (lazy-safe)
def get_gemini(model="gemini-1.5-flash"):
    if not GOOGLE_API_KEY:
        return None
    genai.configure(api_key=GOOGLE_API_KEY)
    return genai.GenerativeModel(model)


# --- YouTube utils
_YT_ID_RE = re.compile(r'(?:v=|/)([0-9A-Za-z_-]{11})')

def extract_video_id(url: str) -> str | None:
    m = _YT_ID_RE.search(url)
    if m:
        return m.group(1)
    if "youtu.be/" in url:
        return url.rstrip('/').split('/')[-1][:11]
    return None

def is_youtube_url(url: str) -> bool:
    return "youtube.com" in url or "youtu.be" in url

def fetch_youtube_captions_text(youtube_url: str, lang_priority=("en","en-US","en-GB")) -> str | None:
    """Official YouTube Data API: pick best caption track, download SRT, strip to plain text."""
    if not YOUTUBE_API_KEY:
        return None
    vid = extract_video_id(youtube_url)
    if not vid:
        return None

    service = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    tracks = service.captions().list(part="id,snippet", videoId=vid).execute()
    items = tracks.get("items", [])
    if not items:
        return None

    # choose a track by language priority
    def score(it):
        lang = (it["snippet"].get("language") or "").lower()
        try: return lang_priority.index(lang)
        except ValueError: return len(lang_priority)+1
    items.sort(key=score)
    caption_id = items[0]["id"]

    # download SRT
    dl = f"https://www.googleapis.com/youtube/v3/captions/{caption_id}?tfmt=srt&key={YOUTUBE_API_KEY}"
    r = requests.get(dl, timeout=30)
    if r.status_code != 200 or not r.text.strip():
        return None

    # strip SRT → text
    lines = []
    for line in r.text.splitlines():
        line = line.strip()
        if not line:       continue
        if line.isdigit(): continue
        if "-->" in line:  continue
        lines.append(line)
    return "\n".join(lines).strip() or None

# --- Summarization (Gemini with graceful fallback)
def summarize_with_gemini(text: str, summary_format: str="bullet_points") -> str:
    model = get_gemini("gemini-1.5-flash")
    if not model:
        return local_summary(text, summary_format)

    prompts = {
        "bullet_points": """Summarize the transcript in crisp bullet points. Focus on key ideas and actionable takeaways.

Transcript:
{t}""",
        "key_insights": """Extract the most important insights, lessons, and actionable takeaways using short sections with clear headings.

Transcript:
{t}""",
        "detailed_summary": """Write a clear, well-structured detailed summary covering:
1) Topic & purpose
2) Key points
3) Notable examples/details
4) Conclusions or next steps

Transcript:
{t}""",
    }
    prompt = prompts.get(summary_format, prompts["bullet_points"]).format(t=text[:200_000])
    resp = model.generate_content(prompt)
    return (resp.text or "").strip()

# dumb but serviceable local fallback
from collections import Counter
def local_summary(text: str, summary_format: str="bullet_points") -> str:
    import re
    sents = re.split(r'(?<=[.!?])\s+', text)
    words = re.findall(r"[A-Za-z][A-Za-z'\-]+", text.lower())
    stop = set("""a an the and or but if to of in on for with as by at from is are was were be been being you your i we they he she it this that those these not can will just""".split())
    freq = Counter(w for w in words if w not in stop and len(w) > 2)
    def score(sent):
        sw = re.findall(r"[A-Za-z][A-Za-z'\-]+", sent.lower())
        return sum(freq.get(w, 0) for w in sw) / (len(sw) + 1)
    top = [s.strip() for s in sorted(sents, key=score, reverse=True)[:10] if s.strip()]
    if summary_format == "detailed_summary":
        return "\n\n".join(top)
    return "\n".join(f"- {t}" for t in top[:8])

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
        'youtube_api_configured': bool(os.getenv("YOUTUBE_API_KEY")),
        'version': '4.0.0-google-ecosystem'
    })


@app.route('/process', methods=['POST'])
def process_video():
    try:
        data = request.get_json(force=True) or {}
        mode = (data.get('mode') or 'youtube').strip()
        video_url = (data.get('video_url') or '').strip()
        raw_transcript = (data.get('raw_transcript') or '').strip()
        summary_format = data.get('summary_format', 'bullet_points')

        # 1) Paste mode (no external calls)
        if mode == 'paste' or raw_transcript:
            if len(raw_transcript) < 20:
                return jsonify({'success': False, 'error': 'Please paste a transcript (≥ 20 chars).'}), 400
            base_id = str(uuid.uuid4())[:8]
            summary_md = summarize_with_gemini(raw_transcript, summary_format)
            download_content = generate_download_content(base_id, raw_transcript, summary_md)

            # Generate download links with data URLs for serverless environment
            transcript_data = f"data:text/plain;charset=utf-8,{requests.utils.quote(raw_transcript)}"
            markdown_data = f"data:text/markdown;charset=utf-8,{requests.utils.quote(summary_md)}"
            html_data = f"data:text/html;charset=utf-8,{requests.utils.quote(download_content['html'])}"
            
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

        # 2) YouTube + captions path
        if not video_url or not video_url.startswith(('http://','https://')):
            return jsonify({'success': False, 'error': 'Provide a valid http(s) URL'}), 400
        if not is_youtube_url(video_url):
            return jsonify({
                'success': False,
                'error': 'This instance supports YouTube links (captions) or Paste mode.',
                'suggestions': ['Switch to Paste mode and drop your transcript text.']
            }), 400

        base_id = extract_video_id(video_url) or str(uuid.uuid4())[:8]
        text = fetch_youtube_captions_text(video_url)
        if not text:
            return jsonify({
                'success': False,
                'error': 'No captions found for this video.',
                'why': 'Captions disabled, private/members-only, age-restricted, or not generated yet.',
                'fixes': ['Try a different video with captions', 'Use Paste mode with your own transcript']
            }), 404

        summary_md = summarize_with_gemini(text, summary_format)
        download_content = generate_download_content(base_id, text, summary_md)

        # Generate download links with data URLs for serverless environment
        transcript_data = f"data:text/plain;charset=utf-8,{requests.utils.quote(text)}"
        markdown_data = f"data:text/markdown;charset=utf-8,{requests.utils.quote(summary_md)}"
        html_data = f"data:text/html;charset=utf-8,{requests.utils.quote(download_content['html'])}"
        
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