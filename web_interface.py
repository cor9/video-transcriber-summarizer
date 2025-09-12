#!/usr/bin/env python3
"""
Web Interface for VidScribe2AI
Simple web interface that triggers the make workflow
"""

from flask import Flask, render_template_string, request, jsonify, send_file
import os
import subprocess
import tempfile
import uuid
from datetime import datetime

app = Flask(__name__)

# HTML Template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VidScribe2AI - Video Transcription & Summarization</title>
    <link rel="icon" type="image/x-icon" href="/favicon.ico">
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
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 20px;
        }

        .header {
            background: transparent;
            color: white;
            padding: 60px 0;
            text-align: center;
        }

        .logo {
            width: 500px;
            height: 300px;
            margin: 0 auto 40px;
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
        }

        .form-container {
            padding: 60px 40px;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            box-shadow: 0 25px 50px rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
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

        input[type="url"], select {
            width: 100%;
            padding: 15px;
            border: 2px solid #e1e8ed;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s ease;
        }

        input[type="url"]:focus, select:focus {
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
        }

        .submit-btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 15px 35px rgba(0, 180, 216, 0.4);
        }

        .submit-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
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
        }

        .progress {
            display: none;
            margin-top: 20px;
            padding: 20px;
            background: #e8f4fd;
            border-radius: 8px;
            border-left: 4px solid #3498db;
        }

        .download-links {
            margin-top: 20px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            border: 2px solid #28a745;
        }

        .download-links a {
            display: inline-block;
            padding: 10px 20px;
            margin: 5px;
            background: #007bff;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-weight: bold;
        }

        .download-links a:hover {
            background: #0056b3;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">
                <img src="/sitelogo.svg" alt="VidScribe2AI Logo">
            </div>
            <p>Transform any video into structured summaries with AI-powered transcription</p>
        </div>

        <div class="form-container">
            <form id="transcribeForm">
                <div class="form-group">
                    <label for="videoUrl">Video/Audio URL</label>
                    <input type="url" id="videoUrl" name="videoUrl" placeholder="https://youtube.com/watch?v=... or https://example.com/video.mp4" required>
                    <small style="color: #666; font-size: 0.9em; margin-top: 5px; display: block;">
                        🎥 <strong>Supported Input Types:</strong><br>
                        ✅ <strong>Direct media URLs:</strong> MP4, MP3, WAV, M4A, WebM, OGG, FLAC, AAC<br>
                        ⚠️ <strong>YouTube URLs:</strong> Limited support due to restrictions<br>
                        💡 <em>For best results: Use direct media URLs or download YouTube videos manually</em>
                    </small>
                </div>

                <div class="form-group">
                    <label for="summaryFormat">Summary Format</label>
                    <select id="summaryFormat" name="summaryFormat">
                        <option value="bullet_points">📝 Bullet Points</option>
                        <option value="key_insights">💡 Key Insights</option>
                        <option value="detailed_summary">📋 Detailed Summary</option>
                    </select>
                </div>

                <button type="submit" class="submit-btn" id="submitBtn">
                    🚀 Process Video
                </button>
            </form>

            <div class="progress" id="progress">
                <h3>🔄 Processing Video...</h3>
                <p id="progressText">Initializing...</p>
            </div>

            <div class="error" id="error"></div>

            <div class="results" id="results">
                <h3>✅ Processing Complete!</h3>
                <div id="transcriptContent"></div>
                <div class="download-links" id="downloadLinks"></div>
            </div>
        </div>
    </div>

    <script>
        document.getElementById('transcribeForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const videoUrl = document.getElementById('videoUrl').value;
            const summaryFormat = document.getElementById('summaryFormat').value;
            
            // Show progress, hide other elements
            document.getElementById('submitBtn').disabled = true;
            document.getElementById('submitBtn').textContent = '🔄 Processing...';
            document.getElementById('results').style.display = 'none';
            document.getElementById('error').style.display = 'none';
            document.getElementById('progress').style.display = 'block';
            
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
                    document.getElementById('downloadLinks').innerHTML = data.download_links;
                    document.getElementById('results').style.display = 'block';
                } else {
                    throw new Error(data.error || 'Processing failed');
                }
            } catch (error) {
                document.getElementById('error').innerHTML = 'Error: ' + error.message;
                document.getElementById('error').style.display = 'block';
            } finally {
                document.getElementById('submitBtn').disabled = false;
                document.getElementById('submitBtn').textContent = '🚀 Process Video';
                document.getElementById('progress').style.display = 'none';
            }
        });
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return HTML_TEMPLATE

@app.route('/process', methods=['POST'])
def process_video():
    try:
        data = request.get_json()
        video_url = data.get('video_url')
        summary_format = data.get('summary_format', 'bullet_points')
        
        if not video_url:
            return jsonify({'error': 'Video URL is required'}), 400
        
        # Generate unique session ID
        session_id = str(uuid.uuid4())[:8]
        
        # Set environment variables for make
        env = os.environ.copy()
        env['ASSEMBLYAI_API_KEY'] = os.getenv('ASSEMBLYAI_API_KEY', '')
        env['ANTHROPIC_API_KEY'] = os.getenv('ANTHROPIC_API_KEY', '')
        
        # Run make command
        cmd = ['make', f'YOUTUBE_URL={video_url}', f'SUMMARY_TYPE={summary_format}']
        
        print(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=os.getcwd())
        
        if result.returncode != 0:
            return jsonify({
                'error': f'Processing failed: {result.stderr}',
                'stdout': result.stdout
            }), 500
        
        # Read the generated files
        video_id = extract_video_id(video_url)
        if not video_id:
            return jsonify({'error': 'Could not extract video ID from URL'}), 400
        
        transcript_file = f'transcripts/{video_id}.txt'
        summary_file = f'summaries/{video_id}.md'
        html_file = f'summaries/{video_id}.html'
        
        # Read transcript
        transcript_content = ""
        if os.path.exists(transcript_file):
            with open(transcript_file, 'r', encoding='utf-8') as f:
                transcript_content = f.read()
        
        # Read summary
        summary_content = ""
        if os.path.exists(summary_file):
            with open(summary_file, 'r', encoding='utf-8') as f:
                summary_content = f.read()
        
        # Create download links
        download_links = ""
        if os.path.exists(html_file):
            download_links += f'<a href="/download/{video_id}.html" target="_blank">📄 Download HTML</a>'
        if os.path.exists(summary_file):
            download_links += f'<a href="/download/{video_id}.md" target="_blank">📝 Download Markdown</a>'
        if os.path.exists(transcript_file):
            download_links += f'<a href="/download/{video_id}.txt" target="_blank">📄 Download Transcript</a>'
        
        # Format response
        formatted_content = f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h3 style="color: #2c3e50; margin-bottom: 20px;">📝 Full Transcript</h3>
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px; white-space: pre-wrap;">{transcript_content}</div>
            
            <h3 style="color: #2c3e50; margin-bottom: 20px;">🎯 AI Summary ({summary_format.replace('_', ' ').title()})</h3>
            <div style="background: #e8f4fd; padding: 15px; border-radius: 8px; border-left: 4px solid #3498db;">{summary_content}</div>
        </div>
        """
        
        return jsonify({
            'success': True,
            'transcript': formatted_content,
            'download_links': download_links,
            'message': 'Video processed successfully!'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    """Download generated files"""
    try:
        # Try different possible locations
        possible_paths = [
            f'summaries/{filename}',
            f'transcripts/{filename}',
            f'downloads/{filename}',
            filename
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return send_file(path, as_attachment=True)
        
        return jsonify({'error': 'File not found'}), 404
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def extract_video_id(url):
    """Extract YouTube video ID from URL"""
    import re
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
