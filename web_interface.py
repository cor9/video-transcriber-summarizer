#!/usr/bin/env python3
"""
A simple, self-contained YouTube summarizer using Flask and the Gemini API.
"""
import os
import time
import random
from flask import Flask, request, render_template_string
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai
from urllib.parse import urlparse, parse_qs

# --- 1. SETUP ---
app = Flask(__name__)

def get_video_id(url):
    """Extracts the YouTube video ID from a URL."""
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
            
    return None # Return None if no ID is found

def get_transcript_with_retry(video_id, max_retries=3):
    """Get transcript with retry logic and rate limiting"""
    for attempt in range(max_retries):
        try:
            # Add random delay to avoid rate limiting
            if attempt > 0:
                delay = random.uniform(2, 5) * (attempt + 1)
                time.sleep(delay)
            
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            return transcript_list
        except Exception as e:
            if "Too Many Requests" in str(e) or "429" in str(e):
                if attempt < max_retries - 1:
                    app.logger.warning(f"Rate limited, retrying in {delay:.1f}s (attempt {attempt + 1})")
                    continue
                else:
                    raise Exception("YouTube rate limit exceeded. Please try again in a few minutes.")
            else:
                raise e
    return None

# Configure the Gemini API
# IMPORTANT: You must set this environment variable in your terminal
# before running the script. Example:
# export GEMINI_API_KEY='YOUR_API_KEY_HERE'
try:
    api_key = os.environ["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-pro')
except KeyError:
    print("FATAL: Please set the GEMINI_API_KEY environment variable.")
    model = None

# --- 2. HTML TEMPLATES (for simplicity, we keep them in the Python file) ---

# This is the main page with the input form
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

# This page displays the results
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
    # Show the main form
    return render_template_string(HTML_FORM)

@app.route('/summarize', methods=['POST'])
def summarize():
    youtube_url = request.form['youtube_url']

    # --- Step 1: Get the transcript ---
    try:
        # Extract video ID from URL using robust function
        video_id = get_video_id(youtube_url)
        if not video_id:
            return render_template_string(HTML_FORM, error="Invalid YouTube URL format")
        
        # Debug: Check if the library is available
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            app.logger.info("YouTubeTranscriptApi imported successfully")
        except ImportError as import_error:
            return render_template_string(HTML_FORM, error=f"Library import error: {import_error}")
        
        # Fetch the transcript with retry logic
        transcript_list = get_transcript_with_retry(video_id)
        # Combine the transcript text into a single string
        transcript_text = " ".join([item['text'] for item in transcript_list])
    except Exception as e:
        # Handle errors (e.g., invalid URL, no transcript available)
        app.logger.error(f"Transcript error: {e}")
        return render_template_string(HTML_FORM, error=f"Could not get transcript: {e}")

    # --- Step 2: Get the summary ---
    if not model:
        return render_template_string(HTML_FORM, error="AI Model is not configured. Did you set your API key?")
    
    try:
        # Create a prompt for the AI
        prompt = f"Please provide a concise, easy-to-read, bullet-point summary of the following video transcript:\n\n---\n{transcript_text}\n---"
        # Call the AI model
        response = model.generate_content(prompt)
        summary_text = response.text
    except Exception as e:
        # Handle errors from the AI API
        return render_template_string(HTML_FORM, error=f"Could not generate summary: {e}")

    # Display the results
    return render_template_string(HTML_RESULT, summary=summary_text, transcript=transcript_text)

# --- 4. RUN THE APP ---
if __name__ == '__main__':
    # Use port 5001 to avoid conflicts with other common ports
    app.run(debug=True, port=5001)