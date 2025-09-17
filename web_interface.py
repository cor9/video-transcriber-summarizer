#!/usr/bin/env python3
"""
A simple, self-contained YouTube summarizer using Flask and the Gemini API.
"""
import os
import time
import random
import json
from flask import Flask, request, render_template_string, jsonify
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
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

def get_transcript_simple(video_id):
    """Get transcript using YouTube's transcript API with enhanced error handling"""
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            # Add delay between attempts
            if attempt > 0:
                delay = random.uniform(1, 3)
                time.sleep(delay)
            
            # Get transcript
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            transcript_text = " ".join([item['text'] for item in transcript_list])
            return transcript_text
            
        except Exception as e:
            error_msg = str(e)
            if attempt == max_retries - 1:
                # Provide better error messages
                if "no element found" in error_msg or "XML" in error_msg:
                    raise Exception("YouTube is temporarily blocking transcript access for this video. This video has captions, but YouTube is blocking API access. Try again in a few minutes or use a different video.")
                elif "Subtitles are disabled" in error_msg:
                    raise Exception("Captions are disabled for this video by the creator. Try a different video with captions enabled.")
                elif "Video unavailable" in error_msg:
                    raise Exception("This video is unavailable or has been removed. Check if the video URL is correct.")
                else:
                    raise Exception(f"Could not get transcript: {error_msg}")
            continue
    
    return None

def get_transcript_mcp_style(video_id, language_codes=None):
    """
    Get transcript in MCP server style with enhanced functionality
    Replicates the functionality of jkawamoto/mcp-youtube-transcript
    """
    try:
        if language_codes:
            # Try specific languages first
            for lang in language_codes:
                try:
                    transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang])
                    return {
                        "success": True,
                        "transcript": transcript_list,
                        "language": lang,
                        "text": " ".join([item['text'] for item in transcript_list])
                    }
                except:
                    continue
        
        # Fallback to auto-generated or any available
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        return {
            "success": True,
            "transcript": transcript_list,
            "language": "auto",
            "text": " ".join([item['text'] for item in transcript_list])
        }
        
    except Exception as e:
        error_msg = str(e)
        return {
            "success": False,
            "error": error_msg,
            "error_type": "transcript_error"
        }

def get_video_info_mcp_style(video_id):
    """
    Get video information in MCP server style
    """
    try:
        # Get transcript to verify video exists and get basic info
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        
        return {
            "success": True,
            "video_id": video_id,
            "has_transcript": True,
            "transcript_length": len(transcript_list),
            "duration": transcript_list[-1]['start'] + transcript_list[-1]['duration'] if transcript_list else 0
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "video_id": video_id,
            "has_transcript": False
        }

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
    <script>
      window.va = window.va || function () { (window.vaq = window.vaq || []).push(arguments); };
    </script>
    <script defer src="/_vercel/insights/script.js"></script>
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
    <p style="color: #666; margin-bottom: 20px;">Gets transcripts directly from YouTube and summarizes with AI</p>
    <form action="/summarize" method="post" id="mainForm">
        <label for="youtube_url">Enter YouTube Video URL:</label>
        <input type="url" id="youtube_url" name="youtube_url" required placeholder="https://www.youtube.com/watch?v=...">
        <div style="margin: 10px 0;">
            <label>
                <input type="checkbox" id="useMcpMode" name="use_mcp_mode" style="margin-right: 8px;">
                🚀 Use MCP Server Mode (Enhanced YouTube Transcript API)
            </label>
            <small style="color:#666;font-size:.9em;display:block;margin-top:5px;">
                Uses the same functionality as the jkawamoto/mcp-youtube-transcript server with better error handling and language support.
            </small>
        </div>
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
    use_mcp_mode = request.form.get('use_mcp_mode') == 'on'

    # --- Step 1: Get the transcript ---
    try:
        # Extract video ID from URL
        video_id = get_video_id(youtube_url)
        if not video_id:
            return render_template_string(HTML_FORM, error="Invalid YouTube URL format")
        
        # Get transcript using either simple or MCP-style method
        if use_mcp_mode:
            # Use MCP-style transcript fetching
            result = get_transcript_mcp_style(video_id, ["en"])
            if not result["success"]:
                return render_template_string(HTML_FORM, error=f"MCP Error: {result['error']}")
            transcript_text = result["text"]
        else:
            # Use simple transcript fetching
            transcript_text = get_transcript_simple(video_id)
        
    except Exception as e:
        # Handle errors
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

# MCP Server Style API Endpoints
@app.route("/api/mcp/youtube/transcript", methods=["POST"])
def mcp_get_transcript():
    """MCP-style transcript endpoint"""
    try:
        data = request.get_json()
        video_url = data.get("video_url")
        language_codes = data.get("language_codes", ["en"])
        
        video_id = get_video_id(video_url)
        if not video_id:
            return jsonify({
                "success": False,
                "error": "Invalid YouTube URL",
                "error_type": "invalid_url"
            })
        
        result = get_transcript_mcp_style(video_id, language_codes)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "server_error"
        })

@app.route("/api/mcp/youtube/info", methods=["POST"])
def mcp_get_video_info():
    """MCP-style video info endpoint"""
    try:
        data = request.get_json()
        video_url = data.get("video_url")
        
        video_id = get_video_id(video_url)
        if not video_id:
            return jsonify({
                "success": False,
                "error": "Invalid YouTube URL",
                "error_type": "invalid_url"
            })
        
        result = get_video_info_mcp_style(video_id)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "server_error"
        })

# --- 4. RUN THE APP ---
if __name__ == '__main__':
    # Use port 5001 to avoid conflicts with other common ports
    app.run(debug=True, port=5001)