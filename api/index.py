from flask import Flask, jsonify, render_template, request
import os
import tempfile
import time
import assemblyai as aai
import anthropic
from datetime import datetime

app = Flask(__name__, template_folder='../templates')

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
    return render_template('index.html')

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy', 
        'timestamp': datetime.now().isoformat(),
        'assemblyai_configured': bool(ASSEMBLYAI_API_KEY),
        'anthropic_configured': bool(ANTHROPIC_API_KEY)
    })

@app.route('/transcribe', methods=['POST'])
def transcribe():
    try:
        # Check if API keys are available
        if not ASSEMBLYAI_API_KEY:
            return jsonify({'error': 'ASSEMBLYAI_API_KEY environment variable is not set. Please configure it in Vercel dashboard.'}), 500
        if not ANTHROPIC_API_KEY:
            return jsonify({'error': 'ANTHROPIC_API_KEY environment variable is not set. Please configure it in Vercel dashboard.'}), 500
        
        data = request.get_json()
        video_url = data.get('video_url')
        prompt_choice = data.get('prompt_choice', 'bullet_points')
        output_format = data.get('output_format', 'html')
        
        if not video_url:
            return jsonify({'error': 'Video URL is required'}), 400
        
        # Simple transcription for now
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(video_url)
        
        # Wait for transcription to complete
        while transcript.status != aai.TranscriptStatus.completed:
            if transcript.status == aai.TranscriptStatus.error:
                raise Exception(f"Transcription failed: {transcript.error}")
            time.sleep(1)
            transcript = transcriber.get_transcript(transcript.id)
        
        return jsonify({
            'success': True,
            'transcript': transcript.text,
            'summary': 'Summary functionality will be added back gradually',
            'message': 'Transcription successful!'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Vercel serverless function handler
def handler(request):
    return app(request.environ, lambda *args: None)

if __name__ == '__main__':
    app.run(debug=True)