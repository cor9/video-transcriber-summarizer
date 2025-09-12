from flask import Flask, jsonify, request, send_file
import os
import time
import markdown
import assemblyai as aai
import anthropic
import uuid
import re
import httpx
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

app = Flask(__name__)

# API Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY", "")

anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None
if ASSEMBLYAI_API_KEY:
    aai.settings.api_key = ASSEMBLYAI_API_KEY

# YouTube ID extraction regex
YOUTUBE_ID_RE = re.compile(
    r'(?:v=|\/)([0-9A-Za-z_-]{11}).*'
)

def extract_video_id(url: str) -> str | None:
    """Extract YouTube video ID from various URL formats"""
    # Handles standard and youtu.be forms
    m = YOUTUBE_ID_RE.search(url)
    if m:
        return m.group(1)
    # youtu.be short form
    if "youtu.be/" in url:
        return url.rstrip('/').split('/')[-1][:11]
    return None

def ensure_dirs():
    os.makedirs("transcripts", exist_ok=True)
    os.makedirs("summaries", exist_ok=True)

def safe_id_from(url_or_id: str) -> str:
    base = (url_or_id or "").strip() or str(uuid.uuid4())
    base = base.split("?")[0].split("#")[0]
    return (base[-64:] or str(uuid.uuid4())).replace("/", "_")

def transcribe_via_url(media_url: str, poll_secs: float = 2.5, max_wait: int = 600):
    """Submit the remote URL directly to AAI. Returns (text, err)."""
    if not ASSEMBLYAI_API_KEY:
        return None, "ASSEMBLYAI_API_KEY not set"
    try:
        tx = aai.Transcriber().transcribe(media_url)
        job_id = getattr(tx, "id", None)
        print(f"[AAI:url] submitted id={job_id} url={media_url}")
    except Exception as e:
        return None, f"AssemblyAI submit error (url): {e}"

    waited = 0.0
    while True:
        try:
            tx = aai.Transcript.get_by_id(job_id)
        except Exception as e:
            return None, f"AssemblyAI poll error: {e}"
        status, err, text = getattr(tx, "status", None), getattr(tx, "error", None), getattr(tx, "text", None)
        print(f"[AAI:url] poll id={job_id} status={status} waited={waited:.1f}s err={err!r}")
        if status in (aai.TranscriptStatus.completed, aai.TranscriptStatus.error):
            break
        time.sleep(poll_secs); waited += poll_secs
        if waited > max_wait:
            return None, "AssemblyAI timed out while polling"
    if status == aai.TranscriptStatus.error:
        return None, f"AssemblyAI transcription failed: {err or 'unknown error'}"
    return (text or "").strip(), None

def upload_to_aai(source_url: str, chunk_size=5 * 1024 * 1024):
    """Streams bytes from source_url -> AAI /upload. Returns (upload_url, err)."""
    if not ASSEMBLYAI_API_KEY:
        return None, "ASSEMBLYAI_API_KEY not set"
    headers = {"authorization": ASSEMBLYAI_API_KEY}
    try:
        with httpx.stream("GET", source_url, follow_redirects=True, timeout=60) as r:
            if r.status_code >= 400:
                return None, f"Source GET {r.status_code} from upstream"
            last = None
            with httpx.Client(timeout=60) as client:
                for chunk in r.iter_bytes(chunk_size):
                    last = client.post("https://api.assemblyai.com/v2/upload",
                                       headers=headers, content=chunk)
                    if last.status_code >= 400:
                        return None, f"AAI upload error {last.status_code}: {last.text[:200]}"
            return last.json().get("upload_url"), None
    except Exception as e:
        return None, f"Upload pipeline error: {e}"

def transcribe_via_upload(source_url: str, poll_secs: float = 2.5, max_wait: int = 600):
    """Use AAI upload endpoint, then transcribe the returned upload_url."""
    up_url, up_err = upload_to_aai(source_url)
    if up_err: 
        return None, f"AssemblyAI upload pipeline failed: {up_err}"
    try:
        tx = aai.Transcriber().transcribe(up_url)
        job_id = getattr(tx, "id", None)
        print(f"[AAI:upload] submitted id={job_id}")
    except Exception as e:
        return None, f"AssemblyAI submit error (upload): {e}"
    waited = 0.0
    while True:
        try:
            tx = aai.Transcript.get_by_id(job_id)
        except Exception as e:
            return None, f"AssemblyAI poll error: {e}"
        status, err, text = getattr(tx, "status", None), getattr(tx, "error", None), getattr(tx, "text", None)
        print(f"[AAI:upload] poll id={job_id} status={status} waited={waited:.1f}s err={err!r}")
        if status in (aai.TranscriptStatus.completed, aai.TranscriptStatus.error):
            break
        time.sleep(poll_secs); waited += poll_secs
        if waited > max_wait:
            return None, "AssemblyAI timed out while polling"
    if status == aai.TranscriptStatus.error:
        return None, f"AssemblyAI transcription failed after upload: {err or 'unknown error'}"
    return (text or "").strip(), None

def summarize_with_anthropic(text: str, summary_format: str = "bullet_points"):
    if not anthropic_client:
        return None, "ANTHROPIC_API_KEY not set"
    if not text:
        return None, "Empty transcript text; cannot summarize"

    templates = {
        "bullet_points": "Summarize in crisp bullet points focusing on key ideas and actionable takeaways.\n\nTranscript:\n{t}",
        "key_insights": "Extract the most important insights with short headings and brief explanations.\n\nTranscript:\n{t}",
        "detailed_summary": "Write a detailed, organized summary: topic, key points, examples, conclusions/next steps.\n\nTranscript:\n{t}",
    }
    prompt = templates.get(summary_format, templates["bullet_points"]).format(t=text[:200000])  # trim huge inputs

    try:
        resp = anthropic_client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=2500,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text.strip(), None
    except Exception as e:
        return None, f"Anthropic error: {e}"

def is_youtube_url(u: str) -> bool:
    return "youtube.com" in u or "youtu.be" in u

def fetch_youtube_captions_text(url: str, languages=("en","en-US","en-GB")) -> str | None:
    vid = extract_video_id(url)
    if not vid: 
        return None
    try:
        items = YouTubeTranscriptApi.get_transcript(vid, languages=list(languages))
        return "\n".join([i.get("text","") for i in items]).strip() or None
    except (TranscriptsDisabled, NoTranscriptFound):
        return None
    except Exception:
        return None

def write_outputs(base_id: str, transcript_text: str, summary_md: str):
    try:
        ensure_dirs()
        tx_path = os.path.join("transcripts", f"{base_id}.txt")
        md_path = os.path.join("summaries", f"{base_id}.md")
        html_path = os.path.join("summaries", f"{base_id}.html")

        with open(tx_path, "w", encoding="utf-8") as f:
            f.write(transcript_text or "")

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(summary_md or "")

        html_body = markdown.markdown(summary_md or "")
        full_html = f"""<!doctype html><html><head><meta charset="utf-8"><title>{base_id} Summary</title>
<style>body{{font-family:Arial,sans-serif;line-height:1.6;max-width:900px;margin:40px auto;color:#333}}</style>
</head><body><h1>Summary</h1><div>{html_body}</div></body></html>"""

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(full_html)

        return tx_path, md_path, html_path, None
    except Exception as e:
        return None, None, None, f"Write error: {e}"

@app.route('/')
def index():
    # Return the HTML directly instead of using templates
    return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VidScribe2AI - AI Video Transcription & Summarization</title>
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
            <p>Transform any video into structured summaries with AI-powered transcription</p>
        </div>

        <div class="form-container">
            <form id="transcribeForm">
                <div class="form-group">
                    <label for="videoUrl">Video/Audio URL</label>
                    <input type="url" id="videoUrl" name="videoUrl" placeholder="https://youtube.com/watch?v=... or https://example.com/video.mp4" required>
                    <small style="color: #666; font-size: 0.9em; margin-top: 5px; display: block;">
                        ✅ <strong>Direct media:</strong> MP4, MP3, WAV, M4A, WebM, OGG, FLAC, AAC<br>
                        ✅ <strong>YouTube:</strong> If the video has captions, we'll use them (fast & free)<br>
                        💡 <em>If no captions, paste a direct media URL or upload audio to your cloud and paste the link</em>
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

                <button type="submit" class="submit-btn" id="submitBtn">
                    🚀 Transcribe & Summarize
                </button>
            </form>

            <div class="error" id="error"></div>

            <div class="results" id="results">
                <h3>✅ Processing Complete!</h3>
                <div id="transcriptContent"></div>
            </div>
        </div>
    </div>

    <script>
        document.getElementById('transcribeForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const videoUrl = document.getElementById('videoUrl').value;
            const summaryFormat = document.getElementById('summaryFormat').value;
            
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
                        video_url: videoUrl,
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
                        if (data.supported_formats) {
                            errorMessage += '<br><strong>Supported formats:</strong> ' + data.supported_formats;
                        }
                        if (data.example_urls) {
                            errorMessage += '<br><strong>Example URLs:</strong><ul>';
                            data.example_urls.forEach(url => {
                                errorMessage += '<li>' + url + '</li>';
                            });
                            errorMessage += '</ul>';
                        }
                    }
                    throw new Error(errorMessage);
                }
            } catch (error) {
                document.getElementById('error').innerHTML = 'Error: ' + error.message;
                document.getElementById('error').style.display = 'block';
            } finally {
                document.getElementById('submitBtn').disabled = false;
                document.getElementById('submitBtn').textContent = '🚀 Transcribe & Summarize';
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
        'assemblyai_configured': bool(os.getenv("ASSEMBLYAI_API_KEY")),
        'anthropic_configured': bool(os.getenv("ANTHROPIC_API_KEY")),
        'youtube_api_configured': bool(os.getenv("YOUTUBE_API_KEY")),
        'version': '2.4.0-bulletproof-fallback'
    })

@app.route('/download/<filename>')
def download_file(filename):
    """Download generated HTML, MD, or TXT files"""
    try:
        # Check in both transcripts and summaries directories
        possible_paths = [
            os.path.join("transcripts", filename),
            os.path.join("summaries", filename)
        ]
        
        file_path = None
        for path in possible_paths:
            if os.path.exists(path):
                file_path = path
                break
        
        if not file_path:
            return jsonify({'error': 'File not found'}), 404
        
        # Determine MIME type based on file extension
        if filename.endswith('.html'):
            mimetype = 'text/html'
        elif filename.endswith('.md'):
            mimetype = 'text/markdown'
        elif filename.endswith('.txt'):
            mimetype = 'text/plain'
        else:
            mimetype = 'application/octet-stream'
        
        return send_file(file_path, as_attachment=True, download_name=filename, mimetype=mimetype)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/process', methods=['POST'])
def process_video():
    try:
        data = request.get_json(force=True) or {}
        video_url = (data.get('video_url') or '').strip()
        summary_format = data.get('summary_format', 'bullet_points')

        if not video_url or not video_url.startswith(('http://', 'https://')):
            return jsonify({'success': False, 'error': 'Provide a valid http(s) Video/Audio URL'}), 400

        base_id = extract_video_id(video_url) or safe_id_from(video_url)

        # YouTube captions path (fastest, no downloads)
        if is_youtube_url(video_url):
            captions = fetch_youtube_captions_text(video_url)
            if captions:
                transcript_text = captions
            else:
                return jsonify({
                    'success': False,
                    'stage': 'transcribe',
                    'error': 'YouTube captions failed: No captions available for this video',
                    'suggestions': [
                        'Use a direct media URL (MP4/MP3/WAV/etc.)',
                        'Or upload the audio/video to your cloud storage and paste the direct link',
                        'Or use a different video with captions enabled'
                    ],
                    'supported_formats': 'MP4, MP3, WAV, M4A, WebM, OGG, FLAC, AAC'
                }), 400
        else:
            # Direct media URL path with upload fallback
            text, err = transcribe_via_url(video_url)
            if err:
                # Only fallback on retrieval-ish errors
                hints = ("retrieve", "403", "404", "redirect", "forbidden", "not accessible", "timeout", "unsupported")
                if any(h in err.lower() for h in hints):
                    print(f"[FALLBACK] Direct URL failed with: {err}")
                    print(f"[FALLBACK] Attempting upload fallback for: {video_url}")
                    text, err = transcribe_via_upload(video_url)
                    if err:
                        print(f"[FALLBACK] Upload fallback also failed: {err}")
                    else:
                        print(f"[FALLBACK] Upload fallback succeeded!")
            
            if err:
                return jsonify({'success': False, 'stage': 'transcribe', 'error': err}), 502
            
            transcript_text = text

        # Summarize
        summary_md, sum_err = summarize_with_anthropic(transcript_text, summary_format)
        if sum_err:
            return jsonify({'success': False, 'stage': 'summarize', 'error': sum_err}), 502

        # Persist
        tx_path, md_path, html_path, w_err = write_outputs(base_id, transcript_text, summary_md)
        if w_err:
            return jsonify({'success': False, 'stage': 'write', 'error': w_err}), 500

        links = ""
        if html_path and os.path.exists(html_path):
            links += f'<a href="/download/{os.path.basename(html_path)}" target="_blank">📄 Download HTML</a>'
        if md_path and os.path.exists(md_path):
            links += f'<a href="/download/{os.path.basename(md_path)}" target="_blank">📝 Download Markdown</a>'
        if tx_path and os.path.exists(tx_path):
            links += f'<a href="/download/{os.path.basename(tx_path)}" target="_blank">📄 Download Transcript</a>'

        preview_html = f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h3 style="color:#2c3e50;margin-bottom:12px;">Transcript</h3>
            <div style="background:#f8f9fa;padding:12px;border-radius:8px;white-space:pre-wrap;max-height:420px;overflow:auto;">{(transcript_text or '')}</div>
            <h3 style="color:#2c3e50;margin:20px 0 12px;">AI Summary ({summary_format.replace('_',' ').title()})</h3>
            <div style="background:#e8f4fd;padding:12px;border-radius:8px;border-left:4px solid #3498db;">{markdown.markdown(summary_md or '')}</div>
        </div>
        """

        return jsonify({
            'success': True,
            'transcript': preview_html,
            'download_links': links,
            'message': 'Processed.'
        })

    except Exception as e:
        return jsonify({'success': False, 'stage': 'unknown', 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)