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
from urllib.parse import urlparse, parse_qs

# --- 1. SETUP ---
app = Flask(__name__)

# --- MCP Server Client ---
# Configuration for the dedicated MCP server
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "https://mcp-server-youtube-transcript-flax.vercel.app")

def get_transcript_from_mcp_server(video_url):
    """
    Calls the dedicated MCP transcript server to get the transcript.
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
                return {"success": True, "transcript": result.get("transcript")}
            else:
                return {"success": False, "error": result.get("error", "Unknown error from MCP server")}
        else:
            return {"success": False, "error": f"MCP server returned status {response.status_code}: {response.text}"}
            
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Could not connect to MCP server: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"An unexpected error occurred: {str(e)}"}

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
    <p style="color: #666; margin-bottom: 20px;">This app now uses a dedicated MCP server to fetch transcripts.</p>
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

    # --- Step 1: Get transcript from the MCP Server ---
    # Call the function that contacts your dedicated transcript server.
    transcript_response = get_transcript_from_mcp_server(youtube_url)

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
    # Use port 5001 to avoid conflicts with other common ports
    app.run(debug=True, port=5001)