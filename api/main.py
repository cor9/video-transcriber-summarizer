#!/usr/bin/env python3
"""
Minimal Hello World Flask app for Vercel deployment testing
"""
from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/")
def health():
    return jsonify({"ok": True, "message": "Hello World from Vercel!"})

@app.route("/summarize", methods=["POST"])
def summarize():
    return jsonify({"success": True, "message": "Summarize endpoint working"})

# Local dev only
if __name__ == "__main__":
    app.run(debug=True, port=5001)