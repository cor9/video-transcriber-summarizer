#!/usr/bin/env python3
"""
A simple, self-contained YouTube summarizer using Flask and the Gemini API.
This version calls a dedicated MCP server for transcripts.
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

# --- MCP Server Client ---
# Configuration for the dedicated MCP server
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "https://mcp-server-youtube-transcript-flax.vercel.app")

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

def get_transcript_simple(video_id):
    """Get transcript using YouTube's transcript API with retry logic"""
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            # Add delay between attempts
            if attempt > 0:
                delay = random.uniform(1, 3)
                time.sleep(delay)
            
            # Try multiple transcript sources
            transcript_sources = [None, ['en'], ['en-US'], ['en-GB']]
            
            for source in transcript_sources:
                try:
                    if source:
                        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=source)
                    else:
                        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
                    
                    transcript_text = " ".join([item['text'] for item in transcript_list])
                    return transcript_text
                    
                except Exception as e:
                    continue
            
            raise Exception("No transcripts available for this video")
            
        except Exception as e:
            if attempt == max_retries - 1:
                raise Exception(f"Could not get transcript: {str(e)}")
            continue
    
    return None

def get_transcript_from_mcp_server(video_url):
    """
    Calls the dedicated MCP transcript server to get the transcript.
    Falls back to local transcript fetching if MCP server is unavailable.
    """
    if not MCP_SERVER_URL:
        return {"success": False, "error": "MCP_SERVER_URL is not configured."}
        
    print(f"📞 Calling MCP Server at: {MCP_SERVER_URL} for URL: {video_url}")
    try:
        payload = {"video_url": video_url}
        response = requests.post(
            f"{MCP_SERVER_URL}/api/transcript",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                return {"success": True, "transcript": result.get("transcript"), "source": "MCP Server"}
            else:
                return {"success": False, "error": result.get("error", "Unknown error from MCP server")}
        else:
            return {"success": False, "error": f"MCP server returned status {response.status_code}: {response.text}"}
            
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Could not connect to MCP server: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"An unexpected error occurred: {str(e)}"}

def get_transcript_with_fallback(video_url):
    """
    Try MCP server first, fall back to local transcript fetching if unavailable.
    """
    # First try MCP server
    mcp_result = get_transcript_from_mcp_server(video_url)
    
    if mcp_result["success"]:
        return mcp_result
    
    # If MCP server fails, try local transcript fetching
    print(f"🔄 MCP server unavailable, falling back to local transcript fetching...")
    try:
        video_id = get_video_id(video_url)
        if not video_id:
            return {"success": False, "error": "Invalid YouTube URL format"}
        
        transcript_text = get_transcript_simple(video_id)
        return {"success": True, "transcript": transcript_text, "source": "Local API"}
        
    except Exception as e:
        return {"success": False, "error": f"Local transcript fetching failed: {str(e)}"}

# --- Gemini API Setup ---
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
    <p style="color: #666; margin-bottom: 20px;">Uses MCP server for transcripts with automatic fallback to local API.</p>
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

    # --- Step 1: Get transcript (try MCP server first, fallback to local) ---
    transcript_response = get_transcript_with_fallback(youtube_url)

    # Check if the call was successful. If not, show the error.
    if not transcript_response["success"]:
        error_message = transcript_response["error"]
        return render_template_string(HTML_FORM, error=f"Could not get transcript: {error_message}")
    
    transcript_text = transcript_response["transcript"]
    transcript_source = transcript_response.get("source", "Unknown")

    # --- Step 2: Get the summary from Gemini AI ---
    if not model:
        return render_template_string(HTML_FORM, error="AI Model is not configured. Did you set your API key?")
    
    try:
        prompt = f"Please provide a concise, easy-to-read, bullet-point summary of the following video transcript:\n\n---\n{transcript_text}\n---"
        response = model.generate_content(prompt)
        summary_text = response.text
    except Exception as e:
        return render_template_string(HTML_FORM, error=f"Could not generate summary: {e}")

    # Display the results with source information
    return render_template_string(HTML_RESULT, summary=summary_text, transcript=transcript_text)

# --- 4. RUN THE APP ---
if __name__ == '__main__':
    # Use port 5001 to avoid conflicts with other common ports
    app.run(debug=True, port=5001)