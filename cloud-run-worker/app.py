from flask import Flask, request, jsonify
from captions import get_captions_text
from summarize import summarize
from markupsafe import escape
import time
import logging

app = Flask(__name__)

@app.get("/health")
def health():
    return jsonify({"ok": True})

@app.post("/summarize")
def summarize_handler():
    data = request.get_json(force=True)
    url = data.get("url")
    transcript_text = data.get("transcript_text")
    summary_format = data.get("summary_format", "bullet_points")
    context_hints = data.get("context_hints", [])
    
    # Either URL or transcript_text must be provided
    if not url and not transcript_text:
        return jsonify({"error": "url or transcript_text required"}), 400
    
    try:
        if transcript_text:
            # Direct transcript text (from file upload or paste)
            transcript = transcript_text
            source = "direct_input"
            captions_ms = 0
        else:
            # Fetch captions from URL
            t0 = time.time()
            transcript, source = get_captions_text(url)
            t1 = time.time()
            captions_ms = int((t1-t0)*1000)
        
        # Time the Gemini call
        t0 = time.time()
        summary_md = summarize(transcript, summary_format, context_hints)
        t1 = time.time()
        gemini_ms = int((t1-t0)*1000)
        
        # Log timing metrics
        logging.info({
            "evt": "timings",
            "captions_ms": captions_ms,
            "gemini_ms": gemini_ms,
            "source": source,
            "transcript_length": len(transcript),
            "summary_length": len(summary_md)
        })
        
        return jsonify({
            "success": True,
            "meta": {"captions_source": source},
            "transcript_text": transcript[:500000],  # safety
            "summary_md": summary_md,
            "summary_html": f"<article>{escape(summary_md)}</article>"
        })
    except Exception as e:
        logging.error(f"Summarization failed: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 502
