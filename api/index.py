from flask import Flask, jsonify, request
import os
import assemblyai as aai
import anthropic

app = Flask(__name__)

# API Configuration
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Initialize API clients only if keys are available
if ASSEMBLYAI_API_KEY:
    aai.settings.api_key = ASSEMBLYAI_API_KEY
if ANTHROPIC_API_KEY:
    anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

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
                    <input type="url" id="videoUrl" name="videoUrl" placeholder="https://youtu.be/VIDEO_ID or https://example.com/video.mp4" required>
                    <small style="color: #666; font-size: 0.9em; margin-top: 5px; display: block;">
                        ✅ <strong>YouTube URLs supported!</strong> Try pasting a YouTube link<br>
                        Also supports: MP4, MP3, WAV, M4A, WebM, OGG, FLAC, AAC<br>
                        <em>Note: Some YouTube videos may not work due to restrictions</em>
                    </small>
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
                        prompt_choice: 'bullet_points',
                        output_format: 'html'
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    // Show results
                    document.getElementById('transcriptContent').innerHTML = '<h4>Transcript:</h4><p>' + data.transcript + '</p>';
                    document.getElementById('results').style.display = 'block';
                } else {
                    throw new Error(data.error || 'An error occurred');
                }
            } catch (error) {
                document.getElementById('error').textContent = 'Error: ' + error.message;
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

@app.route('/transcribe', methods=['POST'])
def transcribe():
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
        
        # Transcribe with AssemblyAI
        print(f"Starting transcription for URL: {video_url}")
        transcript = aai.Transcriber().transcribe(video_url)
        
        if transcript.status == aai.TranscriptStatus.error:
            return jsonify({'error': f'Transcription failed: {transcript.error}'}), 500
        
        # Wait for transcription to complete
        while transcript.status not in [aai.TranscriptStatus.completed, aai.TranscriptStatus.error]:
            transcript = aai.Transcriber().get_transcript(transcript.id)
        
        if transcript.status == aai.TranscriptStatus.error:
            return jsonify({'error': f'Transcription failed: {transcript.error}'}), 500
        
        transcript_text = transcript.text
        
        # Generate summary with Anthropic
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
        
        print("Generating summary with Anthropic...")
        response = anthropic_client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        summary = response.content[0].text
        
        # Format response based on output format
        if output_format == 'html':
            formatted_summary = f"""
            <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h3 style="color: #2c3e50; margin-bottom: 20px;">📝 Full Transcript</h3>
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px; white-space: pre-wrap;">{transcript_text}</div>
                
                <h3 style="color: #2c3e50; margin-bottom: 20px;">🎯 AI Summary</h3>
                <div style="background: #e8f4fd; padding: 15px; border-radius: 8px; border-left: 4px solid #3498db;">{summary}</div>
            </div>
            """
        else:
            formatted_summary = summary
        
        return jsonify({
            'success': True,
            'transcript': formatted_summary,
            'raw_transcript': transcript_text,
            'summary': summary,
            'message': 'Transcription and summarization completed successfully!'
        })
        
    except Exception as e:
        print(f"Error in transcribe: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)