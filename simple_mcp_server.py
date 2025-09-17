#!/usr/bin/env python3
"""
Simple MCP YouTube Transcript Server
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
import time
import random

app = Flask(__name__)
CORS(app)

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

@app.route('/api/transcript', methods=['POST'])
def get_transcript():
    """Get YouTube transcript"""
    try:
        data = request.get_json()
        video_url = data.get('video_url')
        
        if not video_url:
            return jsonify({"success": False, "error": "video_url is required"}), 400
        
        video_id = get_video_id(video_url)
        if not video_id:
            return jsonify({"success": False, "error": "Invalid YouTube URL"}), 400
        
        # Try multiple transcript sources
        transcript_sources = [None, ['en'], ['en-US'], ['en-GB']]
        
        for source in transcript_sources:
            try:
                if source:
                    transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=source)
                else:
                    transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
                
                transcript_text = " ".join([item['text'] for item in transcript_list])
                return jsonify({
                    "success": True, 
                    "transcript": transcript_text,
                    "language": source[0] if source else "auto"
                })
                
            except Exception as e:
                continue
        
        return jsonify({"success": False, "error": "No transcripts available for this video"}), 404
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({"status": "healthy", "service": "MCP YouTube Transcript Server"})

@app.route('/', methods=['GET'])
def root():
    """Root endpoint"""
    return jsonify({
        "service": "MCP YouTube Transcript Server",
        "endpoints": {
            "POST /api/transcript": "Get YouTube transcript",
            "GET /health": "Health check"
        }
    })

if __name__ == '__main__':
    print("🚀 Starting MCP YouTube Transcript Server...")
    app.run(debug=True, port=8080)
