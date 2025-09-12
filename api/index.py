from flask import Flask, jsonify, request, send_file
import os
import tempfile
import assemblyai as aai
import anthropic
import yt_dlp
import markdown
import uuid
import re
import io
import requests
from youtube_transcript_api import YouTubeTranscriptApi
from googleapiclient.discovery import build

app = Flask(__name__)

# API Configuration
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# Create output directory for generated files
OUTPUT_DIR = "/tmp/vidscribe_outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Initialize API clients only if keys are available
if ASSEMBLYAI_API_KEY:
    aai.settings.api_key = ASSEMBLYAI_API_KEY

# Initialize Anthropic client lazily to avoid import issues
anthropic_client = None

# YouTube ID extraction regex
YOUTUBE_ID_RE = re.compile(
    r'(?:v=|\/)([0-9A-Za-z_-]{11}).*'
)

def extract_youtube_video_id(url: str) -> str | None:
    """Extract YouTube video ID from various URL formats"""
    # Handles standard and youtu.be forms
    m = YOUTUBE_ID_RE.search(url)
    if m:
        return m.group(1)
    # youtu.be short form
    if "youtu.be/" in url:
        return url.rstrip('/').split('/')[-1][:11]
    return None

def fetch_youtube_captions_text(youtube_url: str, lang_priority=("en", "en-US", "en-GB")) -> str | None:
    """
    Tries to fetch captions for a YouTube video using youtube-transcript-api.
    Returns plain text if found; otherwise None.
    """
    vid = extract_youtube_video_id(youtube_url)
    if not vid:
        print(f"No video ID found for: {youtube_url}")
        return None

    try:
        print(f"Attempting to fetch captions for video ID: {vid}")
        # Use youtube-transcript-api which doesn't require OAuth2
        api = YouTubeTranscriptApi()
        transcript_list = api.list(vid)
        print(f"Found transcript list with {len(list(transcript_list))} transcripts")
        
        # Try to get transcript in preferred language order
        for lang in lang_priority:
            try:
                transcript = transcript_list.find_transcript([lang])
                transcript_data = transcript.fetch()
                # Convert to plain text
                text = ' '.join([snippet.text for snippet in transcript_data.snippets])
                print(f"Successfully fetched captions for language: {lang}, length: {len(text)}")
                return text.strip() if text.strip() else None
            except:
                continue
        
        # If no preferred language found, try generated transcripts
        try:
            transcript = transcript_list.find_generated_transcript(['en'])
            transcript_data = transcript.fetch()
            text = ' '.join([snippet.text for snippet in transcript_data.snippets])
            return text.strip() if text.strip() else None
        except:
            pass
        
        # If still no luck, try any available transcript
        try:
            available_transcripts = list(transcript_list)
            if available_transcripts:
                transcript = available_transcripts[0]
                transcript_data = transcript.fetch()
                text = ' '.join([snippet.text for snippet in transcript_data.snippets])
                return text.strip() if text.strip() else None
        except:
            pass
            
        return None
        
    except Exception as e:
        print(f"Error fetching YouTube captions: {str(e)}")
        return None

def get_youtube_transcript(video_id):
    """Get transcript directly from YouTube captions"""
    try:
        print(f"Attempting to get transcript for video ID: {video_id}")
        
        # Try to get transcript in different languages
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        print(f"Found transcript list: {list(transcript_list)}")
        
        # Try to get English transcript first
        try:
            transcript = transcript_list.find_transcript(['en'])
            print("Found English transcript")
            transcript_data = transcript.fetch()
        except Exception as e:
            print(f"English transcript not available: {str(e)}")
            # If English not available, get the first available transcript
            try:
                transcript = transcript_list.find_generated_transcripts(['en'])
                print("Found generated English transcript")
                transcript_data = transcript[0].fetch()
            except Exception as e2:
                print(f"Generated English transcript not available: {str(e2)}")
                # Try any available transcript
                try:
                    available_transcripts = list(transcript_list)
                    if available_transcripts:
                        transcript = available_transcripts[0]
                        print(f"Using first available transcript: {transcript}")
                        transcript_data = transcript.fetch()
                    else:
                        raise Exception("No transcripts available")
                except Exception as e3:
                    raise Exception(f"No transcripts available: {str(e3)}")
        
        # Convert transcript data to plain text
        transcript_text = ' '.join([item['text'] for item in transcript_data])
        print(f"Successfully extracted transcript with {len(transcript_data)} segments")
        
        return transcript_text
        
    except Exception as e:
        print(f"Error getting YouTube transcript: {str(e)}")
        # Provide more specific error messages
        error_str = str(e).lower()
        if 'video unavailable' in error_str or 'private video' in error_str:
            raise Exception("Video is private, unavailable, or has restricted access")
        elif 'no transcript' in error_str or 'transcript not found' in error_str:
            raise Exception("This video does not have captions available")
        elif 'bot' in error_str or 'sign in' in error_str:
            raise Exception("YouTube is blocking automated access to this video")
        else:
            raise Exception(f"Failed to get YouTube transcript: {str(e)}")

def check_youtube_video_accessibility(video_id):
    """Check if a YouTube video is accessible and has captions"""
    try:
        # Try to get transcript list to check accessibility
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        available_transcripts = list(transcript_list)
        
        return {
            'accessible': True,
            'has_captions': len(available_transcripts) > 0,
            'transcript_count': len(available_transcripts),
            'transcript_languages': [str(t) for t in available_transcripts]
        }
    except Exception as e:
        error_str = str(e).lower()
        if 'video unavailable' in error_str or 'private video' in error_str:
            return {
                'accessible': False,
                'has_captions': False,
                'error': 'Video is private, unavailable, or has restricted access'
            }
        elif 'bot' in error_str or 'sign in' in error_str:
            return {
                'accessible': False,
                'has_captions': False,
                'error': 'YouTube is blocking automated access to this video'
            }
        else:
            return {
                'accessible': False,
                'has_captions': False,
                'error': f'Unknown error: {str(e)}'
            }

def download_audio_from_youtube(youtube_url):
    """Download audio from YouTube URL using yt-dlp with advanced bot detection bypass"""
    try:
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        temp_file.close()
        
        # Try multiple strategies to bypass bot detection
        strategies = [
            # Strategy 1: Standard bypass
            {
                'format': 'bestaudio/best',
                'outtmpl': temp_file.name,
                'extractaudio': True,
                'audioformat': 'mp4',
                'noplaylist': True,
                'quiet': True,
                'no_warnings': True,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Upgrade-Insecure-Requests': '1',
                },
                'extractor_retries': 5,
                'fragment_retries': 5,
                'retries': 5,
                'socket_timeout': 60,
                'sleep_interval': 2,
                'max_sleep_interval': 10,
            },
            # Strategy 2: Mobile user agent
            {
                'format': 'bestaudio/best',
                'outtmpl': temp_file.name,
                'extractaudio': True,
                'audioformat': 'mp4',
                'noplaylist': True,
                'quiet': True,
                'no_warnings': True,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                },
                'extractor_retries': 3,
                'fragment_retries': 3,
                'retries': 3,
                'socket_timeout': 30,
            },
            # Strategy 3: Minimal approach
            {
                'format': 'bestaudio/best',
                'outtmpl': temp_file.name,
                'extractaudio': True,
                'audioformat': 'mp4',
                'noplaylist': True,
                'quiet': True,
                'no_warnings': True,
                'extractor_retries': 2,
                'fragment_retries': 2,
                'retries': 2,
            }
        ]
        
        last_error = None
        for i, ydl_opts in enumerate(strategies):
            try:
                print(f"Trying download strategy {i+1}...")
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([youtube_url])
                
                # Check if file was created and has content
                if os.path.exists(temp_file.name) and os.path.getsize(temp_file.name) > 0:
                    print(f"Download successful with strategy {i+1}")
                    return temp_file.name
                else:
                    print(f"Strategy {i+1} failed - no content downloaded")
                    
            except Exception as e:
                print(f"Strategy {i+1} failed: {str(e)}")
                last_error = e
                continue
        
        # All strategies failed
        raise last_error or Exception("All download strategies failed")
        
    except Exception as e:
        # If YouTube blocks the download, provide helpful error message
        if "Sign in to confirm you're not a bot" in str(e) or "bot" in str(e).lower():
            raise Exception("YouTube is blocking automated downloads. Please try a different video or use a direct media URL instead. You can also try downloading the video manually and uploading it to a cloud storage service.")
        else:
            raise Exception(f"Failed to download YouTube audio: {str(e)}")

def transcribe_audio_with_assemblyai(audio_file_path):
    """Transcribe local audio file using AssemblyAI"""
    try:
        # Upload file to AssemblyAI
        with open(audio_file_path, 'rb') as f:
            transcript = aai.Transcriber().transcribe(f)
        
        # Wait for transcription to complete
        while transcript.status not in [aai.TranscriptStatus.completed, aai.TranscriptStatus.error]:
            transcript = aai.Transcriber().get_transcript(transcript.id)
        
        if transcript.status == aai.TranscriptStatus.error:
            raise Exception(f"Transcription failed: {transcript.error}")
        
        return transcript.text
        
    except Exception as e:
        raise Exception(f"Transcription failed: {str(e)}")

def summarize_with_anthropic(transcript_text, prompt_choice):
    """Generate summary using Anthropic Claude"""
    global anthropic_client
    
    try:
        # Initialize Anthropic client if not already done
        if anthropic_client is None:
            if not ANTHROPIC_API_KEY:
                raise Exception("ANTHROPIC_API_KEY not configured")
            anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        
        prompt_templates = {
            "bullet_points": """
Please summarize the following video transcript in clear, concise bullet points. Focus on the main topics, key insights, and important takeaways. Use bullet points for easy reading.

Transcript:
{transcript}
""",
            "key_insights": """
Analyze the following video transcript and extract the most important insights, lessons, and actionable information. Present your findings in a structured format with clear headings.

Transcript:
{transcript}
""",
            "detailed_summary": """
Provide a comprehensive summary of the following video transcript. Include:
1. Main topic and purpose
2. Key points discussed
3. Important details and examples
4. Conclusions or takeaways

Transcript:
{transcript}
"""
        }
        
        prompt = prompt_templates.get(prompt_choice, prompt_templates["bullet_points"])
        prompt = prompt.format(transcript=transcript_text)
        
        response = anthropic_client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.content[0].text
        
    except Exception as e:
        raise Exception(f"Summarization failed: {str(e)}")

def generate_output_files(summary_text, transcript_text, filename_prefix="transcript"):
    """Generate Markdown and HTML files from summary text and save to output directory"""
    try:
        # Generate unique filename
        unique_id = str(uuid.uuid4())[:8]
        base_filename = f"{filename_prefix}_{unique_id}"
        
        # Create file paths in output directory
        md_file_path = os.path.join(OUTPUT_DIR, f"{base_filename}.md")
        html_file_path = os.path.join(OUTPUT_DIR, f"{base_filename}.html")
        
        # Write Markdown file with both transcript and summary
        with open(md_file_path, 'w', encoding='utf-8') as md_file:
            md_file.write(f"# {filename_prefix.title()} Summary\n\n")
            md_file.write(f"**Generated on:** {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            md_file.write("## Full Transcript\n\n")
            md_file.write(transcript_text)
            md_file.write("\n\n## AI Summary\n\n")
            md_file.write(summary_text)
        
        # Convert to HTML and write
        html_content = markdown.markdown(summary_text)
        transcript_html = markdown.markdown(transcript_text)
        
        with open(html_file_path, 'w', encoding='utf-8') as html_file:
            html_file.write(f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{filename_prefix.title()} Summary</title>
    <style>
        body {{ 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            line-height: 1.6; 
            color: #333; 
            max-width: 1000px; 
            margin: 0 auto; 
            padding: 20px;
            background: #f8f9fa;
        }}
        .container {{
            background: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        h1, h2, h3 {{ color: #2c3e50; }}
        .transcript {{ 
            background: #f8f9fa; 
            padding: 20px; 
            border-radius: 8px; 
            margin: 20px 0;
            border-left: 4px solid #6c757d;
        }}
        .summary {{ 
            background: #e8f4fd; 
            padding: 20px; 
            border-radius: 8px; 
            margin: 20px 0;
            border-left: 4px solid #3498db;
        }}
        .meta {{
            color: #6c757d;
            font-size: 0.9em;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 1px solid #dee2e6;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎥 {filename_prefix.title()} Summary</h1>
        <div class="meta">
            <strong>Generated on:</strong> {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
        
        <h2>📝 Full Transcript</h2>
        <div class="transcript">{transcript_html}</div>
        
        <h2>🎯 AI Summary</h2>
        <div class="summary">{html_content}</div>
    </div>
</body>
</html>
            """)
        
        return md_file_path, html_file_path, base_filename
        
    except Exception as e:
        raise Exception(f"File generation failed: {str(e)}")

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

@app.route('/transcribe', methods=['POST'])
def transcribe():
    try:
        if not os.getenv("ANTHROPIC_API_KEY"):
            return jsonify({'error': 'ANTHROPIC_API_KEY is not set'}), 500

        data = request.get_json(force=True)
        video_url = (data.get('video_url') or '').strip()
        prompt_choice = data.get('prompt_choice', 'bullet_points')
        output_format = data.get('output_format', 'html')

        if not video_url or not video_url.startswith(('http://', 'https://')):
            return jsonify({'error': 'Provide a valid http(s) URL'}), 400

        youtube_domains = ('youtube.com', 'youtu.be', 'www.youtube.com', 'm.youtube.com')
        is_youtube = any(d in video_url for d in youtube_domains)

        transcript_text = None

        if is_youtube:
            # 1) Try official captions first (legal, fast, free)
            print(f"Processing YouTube URL: {video_url}")
            transcript_text = fetch_youtube_captions_text(video_url)
            print(f"Captions result: {'SUCCESS' if transcript_text else 'FAILED'}")
            if not transcript_text:
                # No captions available
                return jsonify({
                    'error': 'No captions available for this YouTube video.',
                    'suggestions': [
                        'Use a direct media URL (MP4/MP3/WAV/etc.)',
                        'Or upload your audio/video to cloud storage and paste the direct link',
                        'Or use a different video with captions enabled'
                    ],
                    'supported_formats': 'MP4, MP3, WAV, M4A, WebM, OGG, FLAC, AAC'
                }), 400
        else:
            # 2) Direct media URL → transcribe with AssemblyAI if configured
            if not os.getenv("ASSEMBLYAI_API_KEY"):
                return jsonify({
                    'error': 'ASSEMBLYAI_API_KEY is not set and this is not a YouTube URL with captions.',
                    'suggestions': [
                        'Set ASSEMBLYAI_API_KEY to allow transcription of direct media URLs',
                        'Or provide a YouTube link that has captions enabled'
                    ]
                }), 500

            tx = aai.Transcriber().transcribe(video_url)
            while tx.status not in (aai.TranscriptStatus.completed, aai.TranscriptStatus.error):
                tx = aai.Transcriber().get_transcript(tx.id)
            if tx.status == aai.TranscriptStatus.error:
                return jsonify({'error': f'Transcription failed: {tx.error}'}), 502
            transcript_text = tx.text

        # Summarize
        summary = summarize_with_anthropic(transcript_text, prompt_choice)

        if output_format == 'html':
            formatted = f"""
            <div style="font-family: Arial, sans-serif; line-height:1.6; color:#333;">
              <h3 style="color:#2c3e50;">📝 Transcript</h3>
              <div style="background:#f8f9fa; padding:12px; border-radius:8px; white-space:pre-wrap;">{transcript_text}</div>
              <h3 style="color:#2c3e50; margin-top:24px;">🎯 AI Summary</h3>
              <div style="background:#e8f4fd; padding:12px; border-radius:8px; border-left:4px solid #3498db;">{summary}</div>
            </div>
            """
        else:
            formatted = summary

        return jsonify({
            'success': True,
            'transcript': formatted,
            'raw_transcript': transcript_text,
            'summary': summary,
            'message': 'Completed using YouTube captions.' if is_youtube else 'Completed (AssemblyAI).'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)