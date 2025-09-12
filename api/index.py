from flask import Flask, jsonify, request, send_file
import os
import markdown
import assemblyai as aai
import anthropic
import uuid
import re
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

def is_youtube_url(url: str) -> bool:
    y = ("youtube.com" in url) or ("youtu.be" in url)
    return y

def fetch_youtube_transcript_text(video_url: str, languages=("en", "en-US", "en-GB")) -> str | None:
    vid = extract_video_id(video_url)
    if not vid:
        return None
    try:
        # Fetch transcript entries (list of dicts with 'text', 'start', 'duration')
        transcript_list = YouTubeTranscriptApi.get_transcript(vid, languages=list(languages))
        # Join lines
        return "\n".join([item["text"] for item in transcript_list if item.get("text")]).strip() or None
    except (TranscriptsDisabled, NoTranscriptFound):
        return None
    except Exception:
        return None

def transcribe_direct_media_url(media_url: str) -> str:
    if not ASSEMBLYAI_API_KEY:
        raise RuntimeError("ASSEMBLYAI_API_KEY not set")
    tx = aai.Transcriber().transcribe(media_url)
    while tx.status not in (aai.TranscriptStatus.completed, aai.TranscriptStatus.error):
        tx = aai.Transcriber().get_transcript(tx.id)
    if tx.status == aai.TranscriptStatus.error:
        raise RuntimeError(f"Transcription failed: {tx.error}")
    return tx.text or ""

def summarize_text(text: str, summary_format: str = "bullet_points") -> str:
    if not anthropic_client:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    templates = {
        "bullet_points": """Please summarize the following transcript in crisp bullet points focused on main ideas and actionable takeaways.

Transcript:
{transcript}
""",
        "key_insights": """Extract the most important insights, lessons, and practical takeaways from the transcript. Use short sections with clear headings.

Transcript:
{transcript}
""",
        "detailed_summary": """Write a detailed, organized summary of the transcript, including:
1) Topic & purpose
2) Key points
3) Notable examples/details
4) Conclusions or next steps

Transcript:
{transcript}
"""
    }
    prompt = templates.get(summary_format, templates["bullet_points"]).format(transcript=text)

    resp = anthropic_client.messages.create(
        model="claude-3-sonnet-20240229",
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text.strip()

def write_outputs(base_id: str, transcript_text: str, summary_md: str):
    ensure_dirs()
    transcript_path = os.path.join("transcripts", f"{base_id}.txt")
    summary_md_path = os.path.join("summaries", f"{base_id}.md")
    summary_html_path = os.path.join("summaries", f"{base_id}.html")

    # Write transcript
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(transcript_text or "")

    # Write MD
    with open(summary_md_path, "w", encoding="utf-8") as f:
        f.write(summary_md or "")

    # Convert MD to HTML
    html_body = markdown.markdown(summary_md or "")
    full_html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>{base_id} Summary</title>
  <style>
    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 900px; margin: 40px auto; padding: 0 16px; }}
    h1, h2, h3 {{ color: #2c3e50; }}
    .summary {{ background: #f8f9fa; padding: 16px; border-radius: 8px; }}
  </style>
</head>
<body>
  <h1>Summary</h1>
  <div class="summary">{html_body}</div>
</body>
</html>"""
    with open(summary_html_path, "w", encoding="utf-8") as f:
        f.write(full_html)

    return transcript_path, summary_md_path, summary_html_path

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
                const response = await fetch('/transcribe', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        video_url: videoUrl,
                        prompt_choice: summaryFormat,
                        output_format: 'html'
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    // Show results
                    document.getElementById('transcriptContent').innerHTML = data.transcript;
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
        'version': '2.0.0-captions-fix'
    })

@app.route('/download/<filename>')
def download_file(filename):
    """Download generated HTML or MD files"""
    try:
        file_path = os.path.join(OUTPUT_DIR, filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        # Determine MIME type based on file extension
        if filename.endswith('.html'):
            mimetype = 'text/html'
        elif filename.endswith('.md'):
            mimetype = 'text/markdown'
        else:
            mimetype = 'application/octet-stream'
        
        return send_file(file_path, as_attachment=True, download_name=filename, mimetype=mimetype)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/test-youtube/<video_id>')
def test_youtube_captions(video_id):
    """Test endpoint to debug YouTube captions for a specific video"""
    try:
        print(f"Testing YouTube captions for video ID: {video_id}")
        
        # Check accessibility first
        accessibility = check_youtube_video_accessibility(video_id)
        
        if not accessibility['accessible']:
            return jsonify({
                'success': False,
                'video_id': video_id,
                'accessible': False,
                'error': accessibility['error'],
                'message': 'Video is not accessible'
            }), 400
        
        if not accessibility['has_captions']:
            return jsonify({
                'success': False,
                'video_id': video_id,
                'accessible': True,
                'has_captions': False,
                'message': 'Video is accessible but has no captions'
            }), 400
        
        # Try to get transcript
        transcript_text = get_youtube_transcript(video_id)
        
        return jsonify({
            'success': True,
            'video_id': video_id,
            'accessible': True,
            'has_captions': True,
            'transcript_length': len(transcript_text),
            'transcript_preview': transcript_text[:500] + '...' if len(transcript_text) > 500 else transcript_text,
            'transcript_languages': accessibility.get('transcript_languages', []),
            'message': 'YouTube captions test successful'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'video_id': video_id,
            'error': str(e),
            'message': 'YouTube captions test failed'
        }), 400

@app.route('/process', methods=['POST'])
def process_video():
    try:
        data = request.get_json()
        video_url = (data.get('video_url') or '').strip()
        summary_format = data.get('summary_format', 'bullet_points')

        if not video_url or not video_url.startswith(('http://', 'https://')):
            return jsonify({'error': 'Provide a valid http(s) Video/Audio URL'}), 400

        # Choose an ID for file outputs
        base_id = extract_video_id(video_url) or str(uuid.uuid4())[:8]

        # 1) Get transcript
        transcript_text = None
        if is_youtube_url(video_url):
            # Try YouTube transcript (fast, no downloads)
            transcript_text = fetch_youtube_transcript_text(video_url)
            if not transcript_text:
                return jsonify({
                    'error': 'No captions/transcript available for this YouTube video.',
                    'suggestions': [
                        'Use a direct media URL (MP4/MP3/WAV/etc.)',
                        'Or upload the audio/video to your cloud storage and paste the direct link'
                    ]
                }), 400
        else:
            # Direct media URL → AssemblyAI
            if not ASSEMBLYAI_API_KEY:
                return jsonify({
                    'error': 'Direct media transcription requires ASSEMBLYAI_API_KEY.',
                    'suggestions': [
                        'Set ASSEMBLYAI_API_KEY or use a YouTube link that has captions.'
                    ]
                }), 500
            transcript_text = transcribe_direct_media_url(video_url)

        # 2) Summarize
        summary_md = summarize_text(transcript_text, summary_format=summary_format)

        # 3) Persist outputs for download links
        transcript_path, summary_md_path, summary_html_path = write_outputs(
            base_id, transcript_text, summary_md
        )

        # 4) Build download links (reuse your existing /download endpoint)
        download_links = ""
        if os.path.exists(summary_html_path):
            download_links += f'<a href="/download/{os.path.basename(summary_html_path)}" target="_blank">📄 Download HTML</a>'
        if os.path.exists(summary_md_path):
            download_links += f'<a href="/download/{os.path.basename(summary_md_path)}" target="_blank">📝 Download Markdown</a>'
        if os.path.exists(transcript_path):
            download_links += f'<a href="/download/{os.path.basename(transcript_path)}" target="_blank">📄 Download Transcript</a>'

        # 5) Inline display
        formatted_content = f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h3 style="color: #2c3e50; margin-bottom: 20px;">📝 Transcript</h3>
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px; white-space: pre-wrap;">{(transcript_text or '')}</div>

            <h3 style="color: #2c3e50; margin-bottom: 20px;">🎯 AI Summary ({summary_format.replace('_', ' ').title()})</h3>
            <div style="background: #e8f4fd; padding: 15px; border-radius: 8px; border-left: 4px solid #3498db;">{markdown.markdown(summary_md or '')}</div>
        </div>
        """

        return jsonify({
            'success': True,
            'transcript': formatted_content,
            'download_links': download_links,
            'message': 'Processed successfully.'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)