#!/usr/bin/env python3
"""
Cloud Run Worker for VidScribe2AI
Handles heavy lifting: captions fetch, yt-dlp, summarization, file storage
"""

import os
import json
import time
import uuid
import subprocess
import logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from google.cloud import pubsub_v1, storage, firestore
from google.cloud.exceptions import NotFound
from urllib.parse import urlparse, parse_qs

# Import our existing modules
from gemini_summarize import summarize_with_gemini, cleanup_transcript, baseline_summary
from api.captions import get_captions
from api.limiter import fetch_slot

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

# Initialize GCP clients
publisher = pubsub_v1.PublisherClient()
storage_client = storage.Client()
firestore_client = firestore.Client()

# Configuration
PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT')
BUCKET_NAME = os.getenv('BUCKET_NAME', 'vidscribe-artifacts')
TOPIC_NAME = 'transcribe-jobs'

def extract_video_id(url):
    """Extract YouTube video ID from URL using robust urllib.parse"""
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

def update_job_status(job_id: str, status: str, data: dict = None):
    """Update job status in Firestore"""
    try:
        doc_ref = firestore_client.collection('jobs').document(job_id)
        update_data = {
            'status': status,
            'updated_at': datetime.utcnow(),
        }
        if data:
            update_data.update(data)
        
        doc_ref.update(update_data)
        app.logger.info(f"Updated job {job_id} status to {status}")
    except Exception as e:
        app.logger.error(f"Failed to update job status: {e}")

def save_to_gcs(file_path: str, content: str, content_type: str = 'text/plain') -> str:
    """Save content to Google Cloud Storage and return signed URL"""
    try:
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(file_path)
        
        blob.upload_from_string(content, content_type=content_type)
        
        # Generate signed URL valid for 24 hours
        url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.utcnow() + timedelta(hours=24),
            method="GET"
        )
        
        app.logger.info(f"Saved {file_path} to GCS")
        return url
    except Exception as e:
        app.logger.error(f"Failed to save to GCS: {e}")
        return None

def process_video_job(job_data: dict):
    """Process a single video job"""
    job_id = job_data.get('job_id')
    video_url = job_data.get('video_url')
    summary_format = job_data.get('summary_format', 'bullet_points')
    
    app.logger.info(f"Processing job {job_id} for URL {video_url}")
    
    try:
        # Update status to processing
        update_job_status(job_id, 'processing', {
            'video_url': video_url,
            'summary_format': summary_format
        })
        
        # Extract video ID
        video_id = extract_video_id(video_url)
        if not video_id:
            raise ValueError("Could not extract video ID from URL")
        
        # Try to get captions using our resilient system
        transcript_content = ""
        with fetch_slot():  # Use our concurrency limiter
            text, diag = get_captions(video_url)
            if text:
                transcript_content = text
                app.logger.info(f"Got captions via {diag}")
            else:
                app.logger.warning(f"No captions found: {diag}")
        
        # Clean the transcript
        cleaned_transcript = cleanup_transcript(transcript_content)
        
        if not cleaned_transcript.strip():
            raise ValueError("No transcript content available after cleaning")
        
        # Generate summary using Gemini
        summary_content = ""
        if os.getenv("GEMINI_API_KEY") and cleaned_transcript.strip():
            app.logger.info("Using Gemini for summary")
            try:
                summary_content = summarize_with_gemini(
                    os.environ["GEMINI_API_KEY"], 
                    cleaned_transcript, 
                    summary_format
                )
            except Exception as e:
                app.logger.exception("Gemini summarization failed; using fallback")
                summary_content = baseline_summary(cleaned_transcript, summary_format)
        else:
            summary_content = baseline_summary(cleaned_transcript, summary_format)
        
        # Save files to GCS
        transcript_url = save_to_gcs(
            f"transcripts/{video_id}.txt", 
            cleaned_transcript, 
            'text/plain'
        )
        
        summary_url = save_to_gcs(
            f"summaries/{video_id}.md", 
            summary_content, 
            'text/markdown'
        )
        
        # Create HTML version
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Video Summary - {video_id}</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }}
                .transcript {{ background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px; white-space: pre-wrap; }}
                .summary {{ background: #e8f4fd; padding: 15px; border-radius: 8px; border-left: 4px solid #3498db; white-space: pre-wrap; }}
                h3 {{ color: #2c3e50; margin-bottom: 20px; }}
            </style>
        </head>
        <body>
            <h1>Video Summary - {video_id}</h1>
            <h3>📝 Full Transcript</h3>
            <div class="transcript">{cleaned_transcript}</div>
            <h3>🎯 AI Summary ({summary_format.replace('_', ' ').title()})</h3>
            <div class="summary">{summary_content}</div>
        </body>
        </html>
        """
        
        html_url = save_to_gcs(
            f"summaries/{video_id}.html", 
            html_content, 
            'text/html'
        )
        
        # Update job status to completed
        update_job_status(job_id, 'completed', {
            'video_id': video_id,
            'transcript_url': transcript_url,
            'summary_url': summary_url,
            'html_url': html_url,
            'download_links': {
                'transcript': transcript_url,
                'summary': summary_url,
                'html': html_url
            }
        })
        
        app.logger.info(f"Job {job_id} completed successfully")
        
    except Exception as e:
        app.logger.exception(f"Job {job_id} failed: {e}")
        update_job_status(job_id, 'failed', {
            'error': str(e),
            'error_type': type(e).__name__
        })

@app.route('/jobs', methods=['POST'])
def handle_job():
    """Handle Pub/Sub push messages"""
    try:
        # Parse Pub/Sub message
        envelope = request.get_json()
        if not envelope:
            return jsonify({'error': 'No Pub/Sub message received'}), 400
        
        pubsub_message = envelope.get('message', {})
        data = json.loads(pubsub_message.get('data', '{}'))
        
        app.logger.info(f"Received job: {data}")
        
        # Process the job
        process_video_job(data)
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        app.logger.exception(f"Error handling job: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'project_id': PROJECT_ID,
        'bucket_name': BUCKET_NAME
    }), 200

@app.route('/enqueue', methods=['POST'])
def enqueue_job():
    """Direct enqueue endpoint for testing"""
    try:
        data = request.get_json()
        video_url = data.get('video_url')
        summary_format = data.get('summary_format', 'bullet_points')
        
        if not video_url:
            return jsonify({'error': 'video_url is required'}), 400
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Create job document in Firestore
        job_data = {
            'job_id': job_id,
            'video_url': video_url,
            'summary_format': summary_format,
            'status': 'queued',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        firestore_client.collection('jobs').document(job_id).set(job_data)
        
        # Publish to Pub/Sub
        topic_path = publisher.topic_path(PROJECT_ID, TOPIC_NAME)
        message_data = json.dumps(job_data).encode('utf-8')
        
        future = publisher.publish(topic_path, message_data)
        future.result()  # Wait for publish to complete
        
        app.logger.info(f"Enqueued job {job_id} for {video_url}")
        
        return jsonify({
            'job_id': job_id,
            'status': 'queued',
            'message': 'Job enqueued successfully'
        }), 200
        
    except Exception as e:
        app.logger.exception(f"Error enqueuing job: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/status/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """Get job status"""
    try:
        doc_ref = firestore_client.collection('jobs').document(job_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return jsonify({'error': 'Job not found'}), 404
        
        data = doc.to_dict()
        return jsonify(data), 200
        
    except Exception as e:
        app.logger.exception(f"Error getting job status: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
