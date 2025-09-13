#!/usr/bin/env python3
"""
Simple VidScribe2AI - Direct approach without complex architecture
Just two steps: Get transcript -> Get summary
"""

from flask import Flask, request, jsonify, render_template_string
import os
import re
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import google.generativeai as genai
import logging

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

# Configure Gemini
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    model = None

# Simple HTML template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VidScribe2AI - Simple Version</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .form-group { margin-bottom: 20px; }
        input, select, textarea { width: 100%; padding: 10px; margin: 5px 0; }
        button { background: #007bff; color: white; padding: 15px 30px; border: none; cursor: pointer; }
        .results { margin-top: 20px; padding: 20px; background: #f8f9fa; border-radius: 8px; }
        .error { color: red; }
        .loading { color: blue; }
    </style>
</head>
<body>
    <h1>🚀 VidScribe2AI - Simple Version</h1>
    <p>Paste a YouTube URL or any text to get an AI summary!</p>
    
    <form id="form">
        <div class="form-group">
            <label>Input Type:</label>
            <select id="inputType">
                <option value="youtube">YouTube URL</option>
                <option value="text">Paste Text</option>
            </select>
        </div>
        
        <div class="form-group" id="youtubeGroup">
            <label>YouTube URL:</label>
            <input type="url" id="youtubeUrl" placeholder="https://youtube.com/watch?v=...">
        </div>
        
        <div class="form-group" id="textGroup" style="display:none;">
            <label>Text to Summarize:</label>
            <textarea id="textInput" rows="10" placeholder="Paste any text here..."></textarea>
        </div>
        
        <div class="form-group">
            <label>Summary Style:</label>
            <select id="summaryStyle">
                <option value="bullet_points">📝 Bullet Points</option>
                <option value="key_insights">💡 Key Insights</option>
                <option value="detailed_summary">📋 Detailed Summary</option>
            </select>
        </div>
        
        <button type="submit">🚀 Get Summary</button>
    </form>
    
    <div id="status"></div>
    <div id="results"></div>

    <script>
        document.getElementById('inputType').addEventListener('change', function() {
            const type = this.value;
            document.getElementById('youtubeGroup').style.display = type === 'youtube' ? 'block' : 'none';
            document.getElementById('textGroup').style.display = type === 'text' ? 'block' : 'none';
        });

        document.getElementById('form').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const inputType = document.getElementById('inputType').value;
            const summaryStyle = document.getElementById('summaryStyle').value;
            
            document.getElementById('status').innerHTML = '<div class="loading">🔄 Processing...</div>';
            document.getElementById('results').innerHTML = '';
            
            try {
                let response;
                
                if (inputType === 'youtube') {
                    const url = document.getElementById('youtubeUrl').value;
                    if (!url) throw new Error('Please enter a YouTube URL');
                    
                    response = await fetch('/api/summarize', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ youtube_url: url, summary_style: summaryStyle })
                    });
                } else {
                    const text = document.getElementById('textInput').value;
                    if (!text.trim()) throw new Error('Please enter some text');
                    
                    response = await fetch('/api/summarize', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ text: text, summary_style: summaryStyle })
                    });
                }
                
                const data = await response.json();
                
                if (data.success) {
                    document.getElementById('status').innerHTML = '<div style="color: green;">✅ Success!</div>';
                    document.getElementById('results').innerHTML = `
                        <h3>📝 Transcript:</h3>
                        <div style="background: white; padding: 15px; border-radius: 5px; margin-bottom: 20px; max-height: 200px; overflow-y: auto;">
                            ${data.transcript}
                        </div>
                        <h3>🎯 Summary:</h3>
                        <div style="background: white; padding: 15px; border-radius: 5px;">
                            ${data.summary}
                        </div>
                    `;
                } else {
                    throw new Error(data.error);
                }
            } catch (error) {
                document.getElementById('status').innerHTML = `<div class="error">❌ Error: ${error.message}</div>`;
            }
        });
    </script>
</body>
</html>
'''

def extract_video_id(url):
    """Extract YouTube video ID from URL"""
    patterns = [
        r'(?:v=|youtu\.be/|/embed/|/shorts/)([A-Za-z0-9_-]{11})',
        r'youtube\.com/watch\?v=([A-Za-z0-9_-]{11})',
        r'youtu\.be/([A-Za-z0-9_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_youtube_transcript(video_id):
    """Get transcript from YouTube - Step 1"""
    try:
        # Try different language preferences
        for langs in (['en'], ['en-US', 'en-GB'], ['en'], []):
            try:
                transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=langs or None)
                # Clean up the transcript
                text = ' '.join([item['text'] for item in transcript if item['text'].strip()])
                return text
            except (TranscriptsDisabled, NoTranscriptFound):
                continue
        
        raise RuntimeError(f"No transcript available for video {video_id}")
        
    except Exception as e:
        app.logger.error(f"Failed to get transcript: {e}")
        raise

def get_ai_summary(text, style):
    """Get AI summary from Gemini - Step 2"""
    if not model:
        return "⚠️ Gemini API key not configured. Please set GEMINI_API_KEY environment variable."
    
    try:
        # Create prompt based on style
        prompts = {
            'bullet_points': "Summarize this text into clear bullet points:",
            'key_insights': "Extract the key insights and main takeaways from this text:",
            'detailed_summary': "Provide a detailed summary of this text:"
        }
        
        prompt = f"{prompts.get(style, prompts['bullet_points'])}\n\n{text}"
        
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        app.logger.error(f"Failed to get AI summary: {e}")
        return f"⚠️ AI summary failed: {str(e)}"

@app.route('/')
def index():
    return HTML_TEMPLATE

@app.route('/api/summarize', methods=['POST'])
def summarize():
    """The main endpoint - just two steps!"""
    try:
        data = request.get_json()
        youtube_url = data.get('youtube_url')
        text = data.get('text')
        summary_style = data.get('summary_style', 'bullet_points')
        
        # Step 1: Get transcript
        if youtube_url:
            video_id = extract_video_id(youtube_url)
            if not video_id:
                return jsonify({'success': False, 'error': 'Invalid YouTube URL'})
            
            transcript = get_youtube_transcript(video_id)
            if not transcript.strip():
                return jsonify({'success': False, 'error': 'No transcript found for this video'})
        elif text:
            transcript = text.strip()
        else:
            return jsonify({'success': False, 'error': 'Either YouTube URL or text is required'})
        
        # Step 2: Get AI summary
        summary = get_ai_summary(transcript, summary_style)
        
        return jsonify({
            'success': True,
            'transcript': transcript,
            'summary': summary
        })
        
    except Exception as e:
        app.logger.error(f"Summarization failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
