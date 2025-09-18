from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

HTML_FORM = """<!doctype html>
<html><head><meta charset="utf-8"><title>Simple YouTube Summarizer</title></head>
<body style="font-family:system-ui;max-width:720px;margin:40px auto">
  <h1>Simple YouTube Summarizer</h1>
  <p style="color:#555">Transcripts via MCP (with local fallback). Summaries via Gemini.</p>
  <form method="post" action="/summarize">
    <input type="url" name="youtube_url" placeholder="https://www.youtube.com/watch?v=..." required style="width:100%;padding:10px">
    <button type="submit" style="margin-top:10px;padding:10px 16px">Summarize</button>
  </form>
</body></html>"""

@app.get("/")
def home():                       # <-- show UI in browsers
    # If a program requests JSON explicitly, still return health JSON
    wants_json = "application/json" in (request.headers.get("accept",""))
    return jsonify(ok=True, runtime="python3.11") if wants_json else render_template_string(HTML_FORM)

@app.get("/health")               # <-- keep a stable JSON health endpoint
def health():
    return jsonify(ok=True, runtime="python3.11")

@app.post("/summarize")
def summarize():
    data = request.get_json(silent=True) or {}
    return jsonify(success=True, echo=data)

if __name__ == "__main__":
    app.run(debug=True, port=5001)