from flask import Flask, request, jsonify
from flask_cors import CORS  # Import the CORS library
import transcript_fetcher

app = Flask(__name__)
# Enable CORS for all routes, allowing your frontend to access this API
CORS(app) 

@app.route('/api/transcript', methods=['POST'])
def get_transcript():
    """Main transcript endpoint - MCP server style"""
    data = request.get_json()
    video_url = data.get('video_url')
    language_codes = data.get('language_codes', ['en'])

    if not video_url:
        return jsonify({"success": False, "error": "video_url is required"}), 400

    try:
        # Call the function from your other file
        result = transcript_fetcher.fetch_transcript(video_url, language_codes)
        return jsonify(result)
    except Exception as e:
        # Return a specific error message if fetching fails
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/video-info', methods=['POST'])
def get_video_info():
    """Video information endpoint"""
    data = request.get_json()
    video_url = data.get('video_url')

    if not video_url:
        return jsonify({"success": False, "error": "video_url is required"}), 400

    try:
        result = transcript_fetcher.get_video_info(video_url)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "MCP YouTube Transcript Server"})

@app.route('/', methods=['GET'])
def root():
    """Root endpoint with API documentation"""
    return jsonify({
        "service": "MCP YouTube Transcript Server",
        "version": "1.0.0",
        "endpoints": {
            "POST /api/transcript": "Get YouTube transcript with language support",
            "POST /api/video-info": "Get video information and metadata",
            "GET /health": "Health check endpoint"
        },
        "example_request": {
            "url": "POST /api/transcript",
            "body": {
                "video_url": "https://www.youtube.com/watch?v=VIDEO_ID",
                "language_codes": ["en", "es", "fr"]
            }
        }
    })

if __name__ == '__main__':
    print("🚀 Starting MCP YouTube Transcript Server...")
    print("📡 Server will be available at: http://localhost:8080")
    print("🔗 API endpoint: http://localhost:8080/api/transcript")
    app.run(debug=True, port=8080)
