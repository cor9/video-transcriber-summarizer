from flask import Flask, jsonify, request, send_file
import os
import tempfile
import assemblyai as aai
import anthropic
import yt_dlp
import markdown
import uuid

app = Flask(__name__)

# API Configuration
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Create output directory for generated files
OUTPUT_DIR = "/tmp/vidscribe_outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Initialize API clients only if keys are available
if ASSEMBLYAI_API_KEY:
    aai.settings.api_key = ASSEMBLYAI_API_KEY

# Initialize Anthropic client lazily to avoid import issues
anthropic_client = None

def download_audio_from_youtube(youtube_url):
    """Download audio from YouTube URL using yt-dlp"""
    try:
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        temp_file.close()
        
        # Configure yt-dlp options
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': temp_file.name,
            'extractaudio': True,
            'audioformat': 'mp4',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
        }
        
        # Download audio
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])
        
        # Check if file was created and has content
        if not os.path.exists(temp_file.name) or os.path.getsize(temp_file.name) == 0:
            raise Exception("No audio stream found for this video")
        
        return temp_file.name
        
    except Exception as e:
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
                        🎥 <strong>YouTube URLs now supported!</strong><br>
                        ✅ Direct media: MP4, MP3, WAV, M4A, WebM, OGG, FLAC, AAC<br>
                        ✅ YouTube: Any public YouTube video URL<br>
                        💡 <em>Processing may take longer for YouTube videos due to download time</em>
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
        'anthropic_configured': bool(os.getenv("ANTHROPIC_API_KEY"))
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

@app.route('/transcribe', methods=['POST'])
def transcribe():
    """Main transcription endpoint implementing the schema workflow"""
    temp_audio_file = None
    temp_md_file = None
    temp_html_file = None
    
    try:
        # Check if API keys are available
        if not os.getenv("ASSEMBLYAI_API_KEY"):
            return jsonify({'error': 'ASSEMBLYAI_API_KEY environment variable is not set.'}), 500
        
        if not os.getenv("ANTHROPIC_API_KEY"):
            return jsonify({'error': 'ANTHROPIC_API_KEY environment variable is not set.'}), 500
        
        data = request.get_json()
        video_url = data.get('video_url')
        prompt_choice = data.get('prompt_choice', 'bullet_points')
        output_format = data.get('output_format', 'html')
        
        if not video_url:
            return jsonify({'error': 'Video URL is required'}), 400
        
        # Validate video URL
        if not video_url.startswith(('http://', 'https://')):
            return jsonify({'error': 'Invalid URL format'}), 400
        
        # Check if it's a YouTube URL
        youtube_domains = ['youtube.com', 'youtu.be', 'www.youtube.com', 'm.youtube.com']
        is_youtube = any(domain in video_url for domain in youtube_domains)
        
        transcript_text = ""
        
        if is_youtube:
            # YouTube workflow: Download → Transcribe → Summarize
            print(f"Processing YouTube URL: {video_url}")
            
            # Step 1: Download audio from YouTube
            temp_audio_file = download_audio_from_youtube(video_url)
            print(f"Downloaded audio to: {temp_audio_file}")
            
            # Step 2: Transcribe local audio file
            transcript_text = transcribe_audio_with_assemblyai(temp_audio_file)
            print("Transcription completed")
            
        else:
            # Direct URL workflow: Transcribe directly
            print(f"Processing direct URL: {video_url}")
            transcript = aai.Transcriber().transcribe(video_url)
            
            # Wait for transcription to complete
            while transcript.status not in [aai.TranscriptStatus.completed, aai.TranscriptStatus.error]:
                transcript = aai.Transcriber().get_transcript(transcript.id)
            
            if transcript.status == aai.TranscriptStatus.error:
                return jsonify({'error': f'Transcription failed: {transcript.error}'}), 500
            
            transcript_text = transcript.text
            print("Transcription completed")
        
        # Step 3: Generate summary with Anthropic
        print("Generating summary with Anthropic...")
        summary = summarize_with_anthropic(transcript_text, prompt_choice)
        print("Summary generated")
        
        # Step 4: Generate output files for download
        md_file_path = None
        html_file_path = None
        base_filename = None
        
        try:
            md_file_path, html_file_path, base_filename = generate_output_files(summary, transcript_text, "transcript")
            print(f"Generated files: {md_file_path}, {html_file_path}")
        except Exception as e:
            print(f"File generation failed (non-critical): {str(e)}")
        
        # Format response based on output format
        if output_format == 'html':
            formatted_summary = f"""
            <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h3 style="color: #2c3e50; margin-bottom: 20px;">📝 Full Transcript</h3>
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px; white-space: pre-wrap;">{transcript_text}</div>
                
                <h3 style="color: #2c3e50; margin-bottom: 20px;">🎯 AI Summary ({prompt_choice.replace('_', ' ').title()})</h3>
                <div style="background: #e8f4fd; padding: 15px; border-radius: 8px; border-left: 4px solid #3498db;">{summary}</div>
                
                <div style="margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 8px; border: 2px solid #28a745;">
                    <h4 style="color: #28a745; margin-bottom: 15px;">📁 Download Files</h4>
                    <p style="margin-bottom: 10px;">Your transcript and summary are ready for download:</p>
                    <div style="display: flex; gap: 15px; flex-wrap: wrap;">
                        <a href="/download/{base_filename}.html" style="display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">📄 Download HTML</a>
                        <a href="/download/{base_filename}.md" style="display: inline-block; padding: 10px 20px; background: #6c757d; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">📝 Download Markdown</a>
                    </div>
                </div>
            </div>
            """
        else:
            formatted_summary = summary
        
        response_data = {
            'success': True,
            'transcript': formatted_summary,
            'raw_transcript': transcript_text,
            'summary': summary,
            'message': 'Transcription and summarization completed successfully!',
            'source_type': 'YouTube' if is_youtube else 'Direct URL'
        }
        
        # Add download links if files were generated
        if base_filename:
            response_data['download_links'] = {
                'html': f"/download/{base_filename}.html",
                'markdown': f"/download/{base_filename}.md"
            }
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error in transcribe: {str(e)}")
        return jsonify({'error': str(e)}), 500
    
    finally:
        # Clean up only the temporary audio file (keep output files for download)
        if temp_audio_file and os.path.exists(temp_audio_file):
            try:
                os.unlink(temp_audio_file)
                print(f"Cleaned up audio file: {temp_audio_file}")
            except Exception as e:
                print(f"Failed to clean up audio file {temp_audio_file}: {str(e)}")

if __name__ == '__main__':
    app.run(debug=True)