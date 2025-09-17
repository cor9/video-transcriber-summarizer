#!/usr/bin/env python3
"""
A simple, self-contained YouTube summarizer using Flask and the Gemini API.
Enhanced with better transcript fetching and error handling.
"""
import os
import time
import random
import json
import requests
from flask import Flask, request, render_template_string, jsonify
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs

# --- 1. SETUP ---
app = Flask(__name__)

# --- Enhanced Transcript Fetching ---
def get_video_id(url):
    """Extract YouTube video ID from URL"""
    if not url:
        return None
    
    query = urlparse(url)
    if "youtu.be" in query.hostname:
        return query.path[1:]
    if "youtube.com" in query.hostname:
        if query.path == '/watch':
            return parse_qs(query.query).get('v', [None])[0]
        if query.path.startswith(('/embed/', '/v/')):
            return query.path.split('/')[2]
    return None

def get_transcript_enhanced(video_id):
    """
    Enhanced transcript fetching with comprehensive fallback strategy
    """
    max_retries = 3
    
    # List of transcript sources to try in order
    transcript_sources = [
        None,  # Try any available transcript first
        ['en'],  # Try English auto-generated
        ['en-US'],  # Try US English
        ['en-GB'],  # Try British English
    ]
    
    for attempt in range(max_retries):
        for source in transcript_sources:
            try:
                # Add delay between attempts
                if attempt > 0:
                    delay = random.uniform(1, 3)
                    time.sleep(delay)
                
                # Try to get transcript from this source
                if source:
                    transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=source)
                else:
                    transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
                
                transcript_text = " ".join([item['text'] for item in transcript_list])
                return {"success": True, "transcript": transcript_text}
                
            except Exception as e:
                error_msg = str(e)
                # If we get XML parsing errors, YouTube is blocking access
                if "no element found" in error_msg or "XML" in error_msg:
                    return {"success": False, "error": "YouTube is currently blocking transcript access. This is a temporary issue on YouTube's side. Please try again in a few minutes, or try a different video."}
                # If this source fails, try the next one
                continue
        
        # If all sources failed on this attempt, continue to next retry
        if attempt < max_retries - 1:
            continue
    
    # If all attempts failed, provide helpful error message
    return {"success": False, "error": "This video has no captions or auto-generated transcripts available. Try a different video that has spoken content."}

# --- Gemini API Setup ---
try:
    api_key = os.environ["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-pro')
except KeyError:
    print("FATAL: Please set the GEMINI_API_KEY environment variable.")
    model = None

# --- 2. HTML TEMPLATES ---
HTML_FORM = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Simple YouTube Summarizer</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; background-color: #f9f9f9; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
        h1 { color: #333; }
        form { margin-top: 20px; }
        input[type=url] { width: 100%; padding: 12px; font-size: 16px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
        button { width: 100%; padding: 12px; margin-top: 10px; font-size: 16px; background-color: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
        button:hover { background-color: #0056b3; }
        .error { color: #d93025; font-weight: bold; margin-top: 10px; }
    </style>
</head>
<body>
    <h1>Simple YouTube Summarizer</h1>
    <p style="color: #666; margin-bottom: 20px;">Enhanced YouTube summarizer with better transcript fetching and error handling.</p>
    <form action="/summarize" method="post">
        <label for="youtube_url">Enter YouTube Video URL:</label>
        <input type="url" id="youtube_url" name="youtube_url" required placeholder="https://www.youtube.com/watch?v=...">
        <button type="submit">Summarize</button>
    </form>
    {% if error %}
        <p class="error">Error: {{ error }}</p>
    {% endif %}
</body>
</html>
"""

HTML_RESULT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Summary Result</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; background-color: #f9f9f9; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
        h2 { border-bottom: 2px solid #eee; padding-bottom: 10px; }
        div { background-color: #fff; padding: 15px; border-radius: 4px; margin-bottom: 20px; }
        pre { white-space: pre-wrap; word-wrap: break-word; font-size: 14px; line-height: 1.6; }
        a { color: #007bff; }
    </style>
</head>
<body>
    <h1>Summary Result</h1>
    <a href="/">Summarize another video</a>
    <h2>✨ AI Summary</h2>
    <div><pre>{{ summary }}</pre></div>
    <h2>📜 Full Transcript</h2>
    <div><pre>{{ transcript }}</pre></div>
</body>
</html>
"""

# --- 3. FLASK ROUTES ---

@app.route('/')
def index():
    return render_template_string(HTML_FORM)

@app.route('/summarize', methods=['POST'])
def summarize():
    youtube_url = request.form['youtube_url']

    # --- Step 1: Get transcript using enhanced fetching ---
    video_id = get_video_id(youtube_url)
    if not video_id:
        return render_template_string(HTML_FORM, error="Invalid YouTube URL format")
    
    transcript_response = get_transcript_enhanced(video_id)

    # Check if the call was successful. If not, show the error.
    if not transcript_response["success"]:
        error_message = transcript_response["error"]
        return render_template_string(HTML_FORM, error=f"Could not get transcript: {error_message}")
    
    transcript_text = transcript_response["transcript"]

    # --- Step 2: Get the summary from Gemini AI ---
    if not model:
        return render_template_string(HTML_FORM, error="AI Model is not configured. Did you set your API key?")
    
    try:
        prompt = f"Please provide a concise, easy-to-read, bullet-point summary of the following video transcript:\n\n---\n{transcript_text}\n---"
        response = model.generate_content(prompt)
        summary_text = response.text
    except Exception as e:
        return render_template_string(HTML_FORM, error=f"Could not generate summary: {e}")

    # Display the results
    return render_template_string(HTML_RESULT, summary=summary_text, transcript=transcript_text)

# --- 4. RUN THE APP ---
if __name__ == '__main__':
    app.run(debug=True, port=5001)
