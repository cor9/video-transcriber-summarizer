#!/usr/bin/env python3
"""
Web Interface for VidScribe2AI
Simple web interface that triggers the make workflow
"""

from flask import Flask, render_template_string, request, jsonify, send_file
import os
import subprocess
import tempfile
import uuid
from datetime import datetime
import logging

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

# HTML Template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VidScribe2AI - Video Transcription & Summarization</title>
    <link rel="icon" type="image/x-icon" href="/favicon.ico">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            padding: 0;
            margin: 0;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 20px;
        }

        .header {
            background: transparent;
            color: white;
            padding: 60px 0;
            text-align: center;
        }

        .logo {
            width: 500px;
            height: 300px;
            margin: 0 auto 40px;
            display: flex;
            justify-content: center;
            align-items: center;
        }

        .logo img {
            width: 100%;
            height: 100%;
            object-fit: contain;
        }

        .header p {
            font-size: 1.6em;
            opacity: 0.9;
            color: #b8d4f0;
            font-weight: 300;
            letter-spacing: 1px;
        }

        .form-container {
            padding: 60px 40px;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            box-shadow: 0 25px 50px rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }

        .form-group {
            margin-bottom: 25px;
        }

        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #2c3e50;
        }

        input[type="url"], select {
            width: 100%;
            padding: 15px;
            border: 2px solid #e1e8ed;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s ease;
        }

        input[type="url"]:focus, select:focus {
            outline: none;
            border-color: #3498db;
            box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.1);
        }

        .submit-btn {
            width: 100%;
            padding: 20px;
            background: linear-gradient(135deg, #00b4d8 0%, #0077b6 100%);
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 18px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-top: 20px;
        }

        .submit-btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 15px 35px rgba(0, 180, 216, 0.4);
        }

        .submit-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }

        .results {
            display: none;
            margin-top: 30px;
            padding: 30px;
            background: #f8f9fa;
            border-radius: 8px;
            border-left: 4px solid #27ae60;
        }

        .error {
            display: none;
            background: #e74c3c;
            color: white;
            padding: 15px;
            border-radius: 8px;
            margin-top: 20px;
        }

        .progress {
            display: none;
            margin-top: 20px;
            padding: 20px;
            background: #e8f4fd;
            border-radius: 8px;
            border-left: 4px solid #3498db;
        }

        .download-links {
            margin-top: 20px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            border: 2px solid #28a745;
        }

        .download-links a {
            display: inline-block;
            padding: 10px 20px;
            margin: 5px;
            background: #007bff;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-weight: bold;
        }

        .download-links a:hover {
            background: #0056b3;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">
                <img src="/sitelogo.svg" alt="VidScribe2AI Logo">
            </div>
            <p>Transform any video into structured summaries with AI-powered transcription</p>
        </div>

        <div class="form-container">
            <form id="transcribeForm">
                <div class="form-group">
                    <label>Input Method</label>
                    <div style="margin-bottom: 15px;">
                        <label style="display: inline-block; margin-right: 20px; cursor: pointer;">
                            <input type="radio" name="inputMethod" value="url" checked style="margin-right: 5px;">
                            📹 Video URL
                        </label>
                        <label style="display: inline-block; margin-right: 20px; cursor: pointer;">
                            <input type="radio" name="inputMethod" value="file" style="margin-right: 5px;">
                            📁 Upload File
                        </label>
                        <label style="display: inline-block; margin-right: 20px; cursor: pointer;">
                            <input type="radio" name="inputMethod" value="paste" style="margin-right: 5px;">
                            📝 Paste Text
                        </label>
                        <label style="display: inline-block; cursor: pointer;">
                            <input type="radio" name="inputMethod" value="demo" style="margin-right: 5px;">
                            🚀 Try Demo
                        </label>
                    </div>
                </div>

                <div class="form-group" id="urlGroup">
                    <label for="videoUrl">Video/Audio URL</label>
                    <input type="url" id="videoUrl" name="videoUrl" placeholder="https://youtube.com/watch?v=... or https://example.com/video.mp4">
                    <small style="color: #666; font-size: 0.9em; margin-top: 5px; display: block;">
                        🎥 <strong>Supported Input Types:</strong><br>
                        ✅ <strong>Direct media URLs:</strong> MP4, MP3, WAV, M4A, WebM, OGG, FLAC, AAC<br>
                        ⚠️ <strong>YouTube URLs:</strong> Limited support due to restrictions<br>
                        💡 <em>For best results: Use direct media URLs or download YouTube videos manually</em>
                    </small>
                </div>

                <div class="form-group" id="fileGroup" style="display: none;">
                    <label for="subtitleFile">Upload File</label>
                    <input type="file" id="subtitleFile" name="subtitleFile" accept=".srt,.vtt,.txt,.mp4,.mp3,.wav,.m4a,.webm,.ogg,.flac,.aac">
                    <small style="color: #666; font-size: 0.9em; margin-top: 5px; display: block;">
                        📁 <strong>Supported File Types:</strong><br>
                        📝 <strong>Text files:</strong> SRT, VTT, TXT (transcripts/subtitles)<br>
                        🎵 <strong>Media files:</strong> MP4, MP3, WAV, M4A, WebM, OGG, FLAC, AAC<br>
                        💡 <em>Upload subtitle files when YouTube is rate-limited, or media files for transcription</em>
                    </small>
                </div>

                <div class="form-group" id="pasteGroup" style="display: none;">
                    <label for="pastedText">Paste Transcript</label>
                    <textarea id="pastedText" name="pastedText" rows="8" placeholder="Paste your transcript text here..."></textarea>
                    <small style="color: #666; font-size: 0.9em; margin-top: 5px; display: block;">
                        📝 <strong>Paste any transcript text</strong> - we'll clean it up and summarize it instantly
                    </small>
                </div>

                <div class="form-group" id="demoGroup" style="display: none;">
                    <label>Demo Transcript</label>
                    <div style="padding: 15px; background: #e8f4fd; border-radius: 8px; border-left: 4px solid #3498db;">
                        <p><strong>🚀 Try the demo!</strong> This will process a sample transcript to show you how the summarization works.</p>
                        <p style="margin-top: 10px; font-size: 0.9em; color: #666;">
                            The demo uses a sample transcript about artificial intelligence and machine learning. 
                            Click "Process Video" to see the summarization in action!
                        </p>
                    </div>
                </div>

                <div class="form-group">
                    <label for="summaryFormat">Summary Format</label>
                    <select id="summaryFormat" name="summaryFormat">
                        <option value="bullet_points">📝 Bullet Points</option>
                        <option value="key_insights">💡 Key Insights</option>
                        <option value="detailed_summary">📋 Detailed Summary</option>
                    </select>
                </div>

                <div class="form-group">
                    <label for="contextHints">Context Hints (optional)</label>
                    <textarea id="contextHints" name="contextHints" rows="3" placeholder="Audience, tone, use cases, what to emphasize (e.g., &quot;Audience: developers; tone: technical; focus on implementation details&quot;)"></textarea>
                    <small style="color: #666; font-size: 0.9em; margin-top: 5px; display: block;">
                        💡 <strong>Examples:</strong><br>
                        • "Audience: parents; tone: practical; include safety tips"<br>
                        • "Focus on business applications and ROI"<br>
                        • "Technical audience; emphasize code examples"
                    </small>
                </div>

                <button type="submit" class="submit-btn" id="submitBtn">
                    🚀 Process Video
                </button>
                
                <div style="margin-top: 20px; text-align: center;">
                    <button type="button" id="healthCheckBtn" style="padding: 10px 20px; background: #28a745; color: white; border: none; border-radius: 5px; cursor: pointer;">
                        🔍 Check System Health
                    </button>
                    <div id="healthStatus" style="margin-top: 10px; font-size: 14px;"></div>
                </div>
            </form>

            <div class="progress" id="progress">
                <h3>🔄 Processing Video...</h3>
                <p id="progressText">Initializing...</p>
            </div>

            <div class="error" id="error"></div>

            <div class="results" id="results">
                <h3>✅ Processing Complete!</h3>
                <div id="transcriptContent"></div>
                <div class="download-links" id="downloadLinks"></div>
                
                <!-- Feedback Section -->
                <div id="feedbackSection" style="margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 8px; border: 1px solid #e9ecef;">
                    <h4 style="margin-bottom: 15px; color: #2c3e50;">Was this summary helpful?</h4>
                    <div style="display: flex; gap: 15px; margin-bottom: 15px;">
                        <button id="thumbsUp" style="padding: 10px 20px; background: #28a745; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px;">
                            👍 Yes, helpful
                        </button>
                        <button id="thumbsDown" style="padding: 10px 20px; background: #dc3545; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px;">
                            👎 Not helpful
                        </button>
                    </div>
                    <div id="feedbackForm" style="display: none;">
                        <textarea id="feedbackNotes" placeholder="Tell us what could be improved..." rows="3" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; margin-bottom: 10px;"></textarea>
                        <button id="submitFeedback" style="padding: 8px 16px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer;">
                            Submit Feedback
                        </button>
                    </div>
                    <div id="feedbackThanks" style="display: none; color: #28a745; font-weight: bold;">
                        Thank you for your feedback! 🙏
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Handle input method switching
        document.querySelectorAll("input[name=\"inputMethod\"]").forEach(radio => {
            radio.addEventListener("change", function() {
                const method = this.value;
                document.getElementById("urlGroup").style.display = method === "url" ? "block" : "none";
                document.getElementById("fileGroup").style.display = method === "file" ? "block" : "none";
                document.getElementById("pasteGroup").style.display = method === "paste" ? "block" : "none";
                document.getElementById("demoGroup").style.display = method === "demo" ? "block" : "none";
            });
        });

        document.getElementById("transcribeForm").addEventListener("submit", async function(e) {
            e.preventDefault();
            
            const inputMethod = document.querySelector("input[name=\"inputMethod\"]:checked").value;
            const summaryFormat = document.getElementById('summaryFormat').value;
            const contextHints = document.getElementById('contextHints').value
                .split('\n')
                .map(s => s.trim())
                .filter(Boolean);
            
            // Show progress, hide other elements
            document.getElementById('submitBtn').disabled = true;
            document.getElementById("submitBtn").textContent = "🔄 Processing...";
            document.getElementById('results').style.display = 'none';
            document.getElementById('error').style.display = 'none';
            document.getElementById('progress').style.display = 'block';
            document.getElementById('progressText').textContent = 'Processing video...';
            
            try {
                let response;
                
                if (inputMethod === 'file') {
                    const fileInput = document.getElementById('subtitleFile');
                    if (!fileInput.files[0]) {
                        throw new Error('Please select a file to upload');
                    }
                    
                    const formData = new FormData();
                    formData.append('file', fileInput.files[0]);
                    formData.append('summary_format', summaryFormat);
                    formData.append('context_hints', JSON.stringify(contextHints));
                    
                    response = await fetch('/api/submit', {
                        method: 'POST',
                        body: formData
                    });
                } else if (inputMethod === 'paste') {
                    const pastedText = document.getElementById('pastedText').value.trim();
                    if (!pastedText) {
                        throw new Error('Please paste some text to summarize');
                    }
                    
                    response = await fetch('/api/submit', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            pasted_text: pastedText,
                            summary_format: summaryFormat,
                            context_hints: contextHints
                        })
                    });
                } else if (inputMethod === 'demo') {
                    // Demo transcript about AI and machine learning
                    const demoText = `Welcome to this comprehensive overview of artificial intelligence and machine learning. Today we'll explore the fundamental concepts that are shaping our digital future.

Artificial intelligence, or AI, refers to the simulation of human intelligence in machines that are programmed to think and learn like humans. The term may also be applied to any machine that exhibits traits associated with a human mind such as learning and problem-solving.

Machine learning is a subset of artificial intelligence that focuses on the development of algorithms and statistical models that enable computer systems to improve their performance on a specific task through experience. Instead of being explicitly programmed to perform every task, machine learning algorithms build mathematical models based on training data to make predictions or decisions.

There are three main types of machine learning: supervised learning, unsupervised learning, and reinforcement learning. Supervised learning uses labeled training data to learn a mapping function from inputs to outputs. Unsupervised learning finds hidden patterns in data without labeled examples. Reinforcement learning learns through interaction with an environment using a system of rewards and penalties.

Deep learning is a subset of machine learning that uses artificial neural networks with multiple layers to model and understand complex patterns in data. These networks are inspired by the structure and function of the human brain, with interconnected nodes that process information.

The applications of AI and machine learning are vast and growing rapidly. They include natural language processing, computer vision, speech recognition, recommendation systems, autonomous vehicles, medical diagnosis, financial trading, and many more.

However, with these powerful capabilities come important considerations about ethics, bias, privacy, and the future of work. As AI systems become more sophisticated, we must ensure they are developed and deployed responsibly.

The field continues to evolve rapidly, with new breakthroughs in areas like large language models, computer vision, and robotics. Understanding these technologies is crucial for anyone looking to navigate our increasingly digital world.`;
                    
                    response = await fetch('/api/submit', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            pasted_text: demoText,
                            summary_format: summaryFormat,
                            context_hints: contextHints
                        })
                    });
                } else {
                    // URL method
                    const videoUrl = document.getElementById('videoUrl').value;
                    if (!videoUrl) {
                        throw new Error('Please enter a video URL');
                    }
                    
                    response = await fetch('/api/submit', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            video_url: videoUrl,
                            summary_format: summaryFormat,
                            context_hints: contextHints
                        })
                    });
                }
                
                const data = await response.json();
                
                if (data.success) {
                    showResults(data);
                } else {
                    throw new Error(data.error || 'Processing failed');
                }
            } catch (error) {
                document.getElementById('error').innerHTML = 'Error: ' + error.message;
                document.getElementById('error').style.display = 'block';
            } finally {
                document.getElementById('submitBtn').disabled = false;
                document.getElementById("submitBtn").textContent = "🚀 Process Video";
                document.getElementById('progress').style.display = 'none';
            }
        });

        function showResults(data) {
            // Store video data for feedback
            currentVideoData = {
                video_url: document.getElementById('videoUrl').value,
                summary_format: document.getElementById('summaryFormat').value,
                meta: data.meta
            };
            
            // Create download links
            let linksHtml = '';
            if (data.transcript) {
                linksHtml += `<a href="data:text/plain;charset=utf-8,${encodeURIComponent(data.transcript)}" download="transcript.txt" class="download-link">📄 Download Transcript</a>`;
            }
            if (data.summary_md) {
                linksHtml += `<a href="data:text/markdown;charset=utf-8,${encodeURIComponent(data.summary_md)}" download="summary.md" class="download-link">📝 Download Summary</a>`;
            }
            
            document.getElementById('downloadLinks').innerHTML = linksHtml;
            
            // Show results
            const transcriptText = data.transcript || 'No transcript available';
            const summaryText = data.summary_html || data.summary_md || 'No summary available';
            const summaryFormat = data.summary_format ? data.summary_format.replace(/_/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase()) : 'Bullet Points';
            const metaHtml = data.meta ? `
                <div style="margin-top: 20px; padding: 10px; background: #f8f9fa; border-radius: 5px; font-size: 12px; color: #666;">
                    <strong>Source:</strong> ${data.meta.captions_source || 'Unknown'} | 
                    <strong>Processing:</strong> Direct Cloud Run
                </div>
            ` : '';
            
            document.getElementById('transcriptContent').innerHTML = 
                '<div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">' +
                    '<h3 style="color: #2c3e50; margin-bottom: 20px;">📝 Full Transcript</h3>' +
                    '<div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px; white-space: pre-wrap; max-height: 300px; overflow-y: auto;">' +
                        transcriptText +
                    '</div>' +
                    '<h3 style="color: #2c3e50; margin-bottom: 20px;">🎯 AI Summary (' + summaryFormat + ')</h3>' +
                    '<div style="background: #e8f4fd; padding: 15px; border-radius: 8px; border-left: 4px solid #3498db;">' +
                        summaryText +
                    '</div>' +
                    metaHtml +
                '</div>';
            document.getElementById('results').style.display = 'block';
        }

        // Health check functionality
        document.getElementById('healthCheckBtn').addEventListener('click', async function() {
            const btn = document.getElementById('healthCheckBtn');
            const status = document.getElementById('healthStatus');
            
            btn.disabled = true;
            btn.textContent = '🔄 Checking...';
            status.textContent = 'Checking system health...';
            
            try {
                const response = await fetch('/api/submit', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        video_url: 'https://youtube.com/watch?v=dQw4w9WgXcQ',
                        summary_format: 'bullet_points',
                        context_hints: ['Health check test']
                    })
                });
                
                if (response.ok) {
                    status.innerHTML = '<span style="color: #28a745;">✅ System healthy - Cloud Run worker responding</span>';
                } else {
                    status.innerHTML = '<span style="color: #dc3545;">❌ System unhealthy - Worker not responding</span>';
                }
            } catch (error) {
                status.innerHTML = '<span style="color: #dc3545;">❌ System unhealthy - ' + error.message + '</span>';
            } finally {
                btn.disabled = false;
                btn.textContent = '🔍 Check System Health';
            }
        });

        // Feedback functionality
        let currentVideoData = null;
        
        document.getElementById('thumbsUp').addEventListener('click', function() {
            submitFeedback(true);
        });
        
        document.getElementById('thumbsDown').addEventListener('click', function() {
            document.getElementById('feedbackForm').style.display = 'block';
        });
        
        document.getElementById('submitFeedback').addEventListener('click', function() {
            const notes = document.getElementById('feedbackNotes').value;
            submitFeedback(false, notes);
        });
        
        async function submitFeedback(helpful, notes = '') {
            if (!currentVideoData) return;
            
            try {
                const response = await fetch('/api/feedback', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        video_url: currentVideoData.video_url,
                        summary_format: currentVideoData.summary_format,
                        helpful: helpful,
                        notes: notes,
                        meta: currentVideoData.meta || {}
                    })
                });
                
                if (response.ok) {
                    // Hide feedback buttons and show thanks
                    document.getElementById('thumbsUp').style.display = 'none';
                    document.getElementById('thumbsDown').style.display = 'none';
                    document.getElementById('feedbackForm').style.display = 'none';
                    document.getElementById('feedbackThanks').style.display = 'block';
                }
            } catch (error) {
                console.error('Failed to submit feedback:', error);
            }
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return HTML_TEMPLATE

@app.route('/process', methods=['POST'])
def process_video():
    try:
        from gemini_summarize import (
            summarize_with_gemini,
            cleanup_transcript,
            baseline_summary
        )
        
        data = request.get_json()
        video_url = data.get('video_url')
        summary_format = data.get('summary_format', 'bullet_points')

        if not video_url:
            return jsonify({'error': 'Video URL is required'}), 400

        session_id = str(uuid.uuid4())[:8]

        # prepare env for the make workflow (if you still need Assembly/Anthropic there)
        env = os.environ.copy()
        env['ASSEMBLYAI_API_KEY'] = os.getenv('ASSEMBLYAI_API_KEY', '')
        env['ANTHROPIC_API_KEY']   = os.getenv('ANTHROPIC_API_KEY', '')

        # Run your existing pipeline to produce transcript/summary files
        cmd = ['make', f'YOUTUBE_URL={video_url}', f'SUMMARY_TYPE={summary_format}']
        app.logger.info("Running: %s", " ".join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=os.getcwd())

        if result.returncode != 0:
            # We'll still try to proceed if a transcript file happens to exist (e.g., prior run),
            # but otherwise report the error.
            app.logger.error("make failed rc=%s stdout=%s stderr=%s",
                             result.returncode, result.stdout, result.stderr)

        video_id = extract_video_id(video_url)
        if not video_id:
            return jsonify({'error': 'Could not extract video ID from URL'}), 400

        transcript_file = f'transcripts/{video_id}.txt'
        summary_file    = f'summaries/{video_id}.md'
        html_file       = f'summaries/{video_id}.html'

        # Load transcript (if produced)
        raw_transcript = ""
        if os.path.exists(transcript_file):
            with open(transcript_file, 'r', encoding='utf-8') as f:
                raw_transcript = f.read()
        else:
            app.logger.warning("Transcript file missing: %s", transcript_file)

        # Clean "No text" noise etc.
        cleaned_transcript = cleanup_transcript(raw_transcript)

        # Decide summary source:
        # - Prefer Gemini if key present and we actually have text
        # - Else fall back to file summary if it exists
        # - Else baseline fallback
        summary_content = ""
        if os.getenv("GEMINI_API_KEY") and cleaned_transcript.strip():
            app.logger.info("Using Gemini for summary (format=%s)", summary_format)
            try:
                summary_content = summarize_with_gemini(
                    os.environ["GEMINI_API_KEY"], cleaned_transcript, summary_format
                )
            except Exception as e:
                app.logger.exception("Gemini summarization failed; falling back. %s", e)
                # try file summary or baseline
                if os.path.exists(summary_file):
                    with open(summary_file, 'r', encoding='utf-8') as f:
                        summary_content = f.read().strip()
                else:
                    summary_content = baseline_summary(cleaned_transcript, summary_format)
        else:
            if os.path.exists(summary_file):
                with open(summary_file, 'r', encoding='utf-8') as f:
                    summary_content = f.read().strip()
                if not summary_content:
                    summary_content = baseline_summary(cleaned_transcript, summary_format)
            else:
                summary_content = baseline_summary(cleaned_transcript, summary_format)

        # Build download links if artifacts exist
        links = []
        if os.path.exists(html_file):
            links.append(f'<a href="/download/{video_id}.html" target="_blank">📄 Download HTML</a>')
        if os.path.exists(summary_file):
            links.append(f'<a href="/download/{video_id}.md" target="_blank">📝 Download Markdown</a>')
        if os.path.exists(transcript_file):
            links.append(f'<a href="/download/{video_id}.txt" target="_blank">📄 Download Transcript</a>')
        download_links = "".join(links)

        # Render formatted content
        formatted_content = f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h3 style="color: #2c3e50; margin-bottom: 20px;">📝 Full Transcript</h3>
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px; white-space: pre-wrap;">
{cleaned_transcript}
            </div>
            <h3 style="color: #2c3e50; margin-bottom: 20px;">🎯 AI Summary ({summary_format.replace('_', ' ').title()})</h3>
            <div style="background: #e8f4fd; padding: 15px; border-radius: 8px; border-left: 4px solid #3498db; white-space: pre-wrap;">
{summary_content}
            </div>
        </div>
        """

        return jsonify({
            'success': True,
            'transcript': formatted_content,
            'download_links': download_links,
            'message': 'Video processed successfully!'
        })

    except Exception as e:
        app.logger.exception("Unhandled error in /process")
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    """Download generated files"""
    try:
        # Try different possible locations
        possible_paths = [
            f'summaries/{filename}',
            f'transcripts/{filename}',
            f'downloads/{filename}',
            filename
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return send_file(path, as_attachment=True)
        
        return jsonify({'error': 'File not found'}), 404
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def extract_video_id(url):
    """Extract YouTube video ID from URL using robust urllib.parse"""
    from urllib.parse import urlparse, parse_qs
    
    u = urlparse(url)
    host = (u.netloc or "").lower()
    
    if host in ("youtu.be", "www.youtu.be"):
        return u.path.lstrip("/") or None
    
    if "youtube.com" in host or "youtube-nocookie.com" in host:
        qs = parse_qs(u.query or "")
        if "v" in qs and qs["v"]:
            return qs["v"][0]
        
        parts = [p for p in (u.path or "").split("/") if p]
        # /embed/{id}, /v/{id}
        if parts and parts[0] in ("embed", "v"):
            return parts[1] if len(parts) > 1 else None
    
    return None

def canonical_watch_url(video_id: str) -> str:
    """Generate canonical YouTube watch URL"""
    return f"https://www.youtube.com/watch?v={video_id}"

# Static file serving routes
@app.route('/favicon.ico')
def favicon():
    return send_file('favicon.ico')

@app.route('/sitelogo.svg')
def sitelogo():
    return send_file('sitelogo.svg')

@app.route('/logoimage.svg')
def logoimage():
    return send_file('logoimage.svg')

@app.route('/title.svg')
def title():
    return send_file('title.svg')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
