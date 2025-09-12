import os
import tempfile
import time
import subprocess
import re
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
import assemblyai as aai
import anthropic
from datetime import datetime

app = Flask(__name__)

# API Configuration
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Check if API keys are provided
if not ASSEMBLYAI_API_KEY:
    raise ValueError("ASSEMBLYAI_API_KEY environment variable is required")
if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY environment variable is required")

# Initialize API clients
aai.settings.api_key = ASSEMBLYAI_API_KEY
anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Prompt templates for different summarization styles
PROMPT_TEMPLATES = {
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
""",
    
    "actionable_guide": """
Transform the following video transcript into a practical, actionable guide. Focus on:
1. Step-by-step instructions
2. Specific actions the viewer can take
3. Tools, resources, or methods mentioned
4. Key takeaways that can be implemented immediately
5. Clear, actionable advice

Format as a practical guide with numbered steps and actionable items.

Transcript:
{transcript}
"""
}

def extract_youtube_id(url):
    """
    Extract YouTube video ID from various YouTube URL formats
    """
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
        r'youtube\.com\/v\/([^&\n?#]+)',
        r'youtube\.com\/watch\?.*v=([^&\n?#]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def download_youtube_audio(youtube_url):
    """
    Download audio from YouTube URL using yt-dlp
    """
    try:
        # Extract video ID
        video_id = extract_youtube_id(youtube_url)
        if not video_id:
            raise ValueError("Invalid YouTube URL format")
        
        # Create temporary file for audio
        temp_audio = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
        temp_audio.close()
        
        # Use yt-dlp to download audio
        cmd = [
            'yt-dlp',
            '--extract-audio',
            '--audio-format', 'mp3',
            '--output', temp_audio.name,
            youtube_url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            raise Exception(f"Failed to download audio: {result.stderr}")
        
        return temp_audio.name
        
    except subprocess.TimeoutExpired:
        raise Exception("YouTube download timed out. Please try again.")
    except Exception as e:
        raise Exception(f"YouTube download error: {str(e)}")

def validate_video_url(url):
    """
    Validate that the URL is a supported video/audio source
    """
    # Check if it's a YouTube URL
    if 'youtube.com' in url or 'youtu.be' in url:
        return 'youtube'
    
    # Check if it's a direct media file
    supported_extensions = ['.mp4', '.mp3', '.wav', '.m4a', '.webm', '.ogg', '.flac', '.aac']
    if any(url.lower().endswith(ext) for ext in supported_extensions):
        return 'direct'
    
    # Check if URL contains media file patterns
    if any(pattern in url.lower() for pattern in ['/video/', '/audio/', '.mp4', '.mp3', '.wav', '.m4a']):
        return 'direct'
    
    raise ValueError("Unsupported URL format. Please provide a YouTube URL or direct link to a video/audio file.")

def handle_transcribe_request(video_url):
    """
    Transcribe video using AssemblyAI API
    """
    try:
        # Validate the URL and determine type
        url_type = validate_video_url(video_url)
        
        # Handle YouTube URLs by downloading audio first
        if url_type == 'youtube':
            # Download audio from YouTube
            audio_file = download_youtube_audio(video_url)
            
            # Upload audio file to AssemblyAI
            with open(audio_file, 'rb') as f:
                transcript = aai.Transcriber().transcribe(f)
        else:
            # Direct URL - use AssemblyAI directly
            transcript = aai.Transcriber().transcribe(video_url)
        
        # Wait for transcription to complete
        while transcript.status != aai.TranscriptStatus.completed:
            if transcript.status == aai.TranscriptStatus.error:
                raise Exception(f"Transcription failed: {transcript.error}")
            time.sleep(1)
            transcript = aai.Transcriber().get_transcript(transcript.id)
        
        # Save transcript to temporary file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
        temp_file.write(transcript.text)
        temp_file.close()
        
        # Clean up YouTube audio file if it was downloaded
        if url_type == 'youtube' and 'audio_file' in locals():
            try:
                os.unlink(audio_file)
            except:
                pass
        
        return temp_file.name, transcript.text
        
    except Exception as e:
        raise Exception(f"Transcription error: {str(e)}")

def handle_summarize_request(text_file_path, prompt_choice):
    """
    Summarize transcript using Anthropic Claude
    """
    try:
        # Read transcript from file
        with open(text_file_path, 'r', encoding='utf-8') as file:
            transcript_text = file.read()
        
        # Get the appropriate prompt template
        prompt_template = PROMPT_TEMPLATES.get(prompt_choice, PROMPT_TEMPLATES["bullet_points"])
        prompt = prompt_template.format(transcript=transcript_text)
        
        # Call Anthropic Claude API
        response = anthropic_client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=4000,
            temperature=0.7,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        summary_text = response.content[0].text
        return summary_text
        
    except Exception as e:
        raise Exception(f"Summarization error: {str(e)}")

def format_output(summary_text, format_type="html"):
    """
    Format the summary text into HTML or Markdown
    """
    try:
        if format_type == "html":
            # Convert to HTML with proper formatting
            html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VidScribe2AI - Video Summary</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
            color: #333;
            background: #f8f9fa;
        }}
        .header {{
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
            position: relative;
        }}
        .header::before {{
            content: '';
            position: absolute;
            top: 20px;
            right: 20px;
            width: 80px;
            height: 80px;
            background: url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iODAiIGhlaWdodD0iODAiIHZpZXdCb3g9IjAgMCA4MCA4MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPGNpcmNsZSBjeD0iNDAiIGN5PSI0MCIgcj0iNDAiIGZpbGw9InVybCgjZ3JhZGllbnQwX2xpbmVhcl8xXzEpIi8+CjxwYXRoIGQ9Ik0zMiA0MEw0OCAzMkw0OCA0OEwzMiA0MFoiIGZpbGw9IndoaXRlIi8+CjwvZGVmcz4KPC9zdmc+') no-repeat center;
            background-size: contain;
            opacity: 0.2;
        }}
        .logo {{
            width: 60px;
            height: 60px;
            margin: 0 auto 20px;
            background: linear-gradient(135deg, #00b4d8 0%, #0077b6 100%);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
        }}
        .logo::before {{
            content: '▶';
            color: white;
            font-size: 24px;
            font-weight: bold;
        }}
        h1 {{
            color: white;
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }}
        .subtitle {{
            color: #b8d4f0;
            margin-top: 10px;
            font-size: 1.1em;
        }}
        .content {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        h2 {{
            color: #2c3e50;
            margin-top: 30px;
            border-bottom: 2px solid #3498db;
            padding-bottom: 5px;
        }}
        ul, ol {{
            margin: 15px 0;
        }}
        li {{
            margin: 8px 0;
        }}
        .timestamp {{
            font-size: 0.9em;
            color: #7f8c8d;
            font-style: italic;
        }}
        .summary-meta {{
            background-color: #e3f2fd;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            border-left: 4px solid #3498db;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            color: #666;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="logo"></div>
        <h1>VidScribe2AI</h1>
        <div class="subtitle">AI-Powered Video Summary</div>
    </div>
    
    <div class="content">
        <div class="summary-meta">
            <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>Format:</strong> HTML Summary</p>
            <p><strong>Powered by:</strong> VidScribe2AI - Transform any video into structured summaries</p>
        </div>
        
        <div class="summary-content">
            {summary_text.replace(chr(10), '<br>').replace('•', '&bull;')}
        </div>
    </div>
    
    <div class="footer">
        <p>Generated by VidScribe2AI - AI Video Transcription & Summarization Tool</p>
    </div>
</body>
</html>
"""
            # Save to temporary HTML file
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8')
            temp_file.write(html_content)
            temp_file.close()
            
        else:  # Markdown format
            markdown_content = f"""# 🎥 VidScribe2AI - Video Summary

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Format:** Markdown Summary  
**Powered by:** VidScribe2AI - AI Video Transcription & Summarization

---

{summary_text}

---

*Generated by VidScribe2AI - Transform any video into structured summaries with AI-powered transcription*
"""
            # Save to temporary Markdown file
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8')
            temp_file.write(markdown_content)
            temp_file.close()
        
        return temp_file.name
        
    except Exception as e:
        raise Exception(f"Formatting error: {str(e)}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    if filename.endswith(('.svg', '.ico', '.png', '.jpg', '.jpeg', '.gif', '.css', '.js')):
        try:
            return send_file(filename)
        except FileNotFoundError:
            return "File not found", 404
    else:
        return "Not found", 404


@app.route('/transcribe', methods=['POST'])
def transcribe():
    try:
        data = request.get_json()
        video_url = data.get('video_url')
        prompt_choice = data.get('prompt_choice', 'bullet_points')
        output_format = data.get('output_format', 'html')
        
        if not video_url:
            return jsonify({'error': 'Video URL is required'}), 400
        
        # Step 1: Transcribe video
        transcript_file, transcript_text = handle_transcribe_request(video_url)
        
        # Step 2: Summarize transcript
        summary_text = handle_summarize_request(transcript_file, prompt_choice)
        
        # Step 3: Format output
        formatted_file = format_output(summary_text, output_format)
        
        # Clean up transcript file
        os.unlink(transcript_file)
        
        return jsonify({
            'success': True,
            'transcript': transcript_text,
            'summary': summary_text,
            'download_file': formatted_file,
            'file_extension': '.html' if output_format == 'html' else '.md'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<path:filename>')
def download_file(filename):
    try:
        return send_file(filename, as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)