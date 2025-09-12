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
    summary_format = data.get("summary_format", "bullet_points")
    context_hints = data.get("context_hints", [])
    
    if not url:
        return jsonify({"error": "url required"}), 400
    
    try:
        # Time the caption fetch
        t0 = time.time()
        transcript, source = get_captions_text(url)
        t1 = time.time()
        
        # Time the Gemini call
        summary_md = summarize(transcript, summary_format, context_hints)
        t2 = time.time()
        
        # Log timing metrics
        logging.info({
            "evt": "timings",
            "captions_ms": int((t1-t0)*1000),
            "gemini_ms": int((t2-t1)*1000),
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
