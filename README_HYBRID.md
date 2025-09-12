# VidScribe2AI - Hybrid Architecture

A robust video transcription and summarization service using **Vercel** for the frontend and **Google Cloud** for heavy processing.

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Vercel        │    │   Google Cloud  │    │   Google Cloud  │
│   Frontend      │───▶│   Pub/Sub        │───▶│   Cloud Run     │
│   (Job Submit)  │    │   (Queue)       │    │   (Processing)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                                               │
         │                                               ▼
         │                                      ┌─────────────────┐
         │                                      │   Cloud        │
         │                                      │   Storage      │
         │                                      │   (Artifacts)  │
         │                                      └─────────────────┘
         │                                               │
         ▼                                               │
┌─────────────────┐    ┌─────────────────┐              │
│   Vercel        │    │   Google Cloud  │              │
│   Frontend      │◀───│   Firestore     │◀─────────────┘
│   (Status Poll) │    │   (Job Status)  │
└─────────────────┘    └─────────────────┘
```

## 🚀 Why This Architecture?

### Vercel Strengths
- ✅ **Blazing fast frontend** with instant previews
- ✅ **Custom domains** and CDN
- ✅ **Perfect for short API routes** (<10s, stateless)
- ✅ **Great DX** for React/Next.js

### Google Cloud Strengths  
- ✅ **Cloud Run** runs Python containers with proper CPU/RAM
- ✅ **Pub/Sub** handles job queuing with retries/backoff
- ✅ **Cloud Storage** for artifact storage with signed URLs
- ✅ **Firestore** for job status tracking
- ✅ **First-class Gemini integration**

### Problems Solved
- ❌ **No more Vercel timeout issues** (moved heavy work to Cloud Run)
- ❌ **No more "ModuleNotFoundError"** (proper container with all deps)
- ❌ **No more YouTube rate limiting drama** (proper retry/backoff in Cloud Run)
- ❌ **No more fake instant summaries** (real Gemini calls with proper blocking)

## 📁 Project Structure

```
video-transcriber/
├── api/                          # Vercel API routes
│   ├── submit.js                 # Job submission endpoint
│   └── status.js                 # Job status checking endpoint
├── cloud_run_app.py              # Cloud Run worker (heavy lifting)
├── Dockerfile                    # Container for Cloud Run
├── web_interface.py              # Vercel frontend (lightweight)
├── gemini_summarize.py           # Gemini integration
├── api/                          # Existing caption fetching modules
│   ├── captions.py
│   ├── cache.py
│   ├── backoff.py
│   └── limiter.py
├── setup_gcp.sh                  # GCP setup script
├── package.json                  # Vercel dependencies
└── requirements.txt              # Python dependencies
```

## 🛠️ Setup Instructions

### 1. Google Cloud Setup

```bash
# Authenticate with Google Cloud
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Run the setup script
./setup_gcp.sh
```

This creates:
- Cloud Storage bucket (`vidscribe-artifacts`)
- Pub/Sub topic (`transcribe-jobs`)
- Cloud Run service (`vidscribe-worker`)
- Firestore database
- All necessary IAM permissions

### 2. Environment Variables

#### Vercel Environment Variables
```bash
vercel env add GOOGLE_CLOUD_PROJECT
vercel env add PUBSUB_TOPIC
vercel env add GOOGLE_APPLICATION_CREDENTIALS  # Service account key JSON
```

#### Cloud Run Environment Variables
```bash
gcloud run services update vidscribe-worker \
  --set-env-vars GEMINI_API_KEY=your_gemini_key \
  --region us-central1
```

### 3. Deploy

```bash
# Deploy Vercel frontend
vercel --prod

# Deploy Cloud Run worker (already done by setup script)
# But you can redeploy with:
gcloud builds submit --tag gcr.io/YOUR_PROJECT/vidscribe-worker
gcloud run deploy vidscribe-worker --image gcr.io/YOUR_PROJECT/vidscribe-worker
```

## 🔄 Data Flow

### 1. Job Submission
```
User submits video URL
    ↓
Vercel /api/submit
    ↓
Publishes to Pub/Sub topic
    ↓
Returns job_id to frontend
```

### 2. Job Processing
```
Pub/Sub delivers message to Cloud Run
    ↓
Cloud Run worker processes video:
    - Extract captions (YouTube API → transcript API → yt-dlp)
    - Clean transcript (remove "No text", URLs)
    - Summarize with Gemini
    - Save artifacts to Cloud Storage
    ↓
Updates job status in Firestore
```

### 3. Status Polling
```
Frontend polls /api/status every 2s
    ↓
Vercel /api/status queries Firestore
    ↓
Returns job status and download links
    ↓
Frontend shows progress/results
```

## 🧪 Testing

### Test Cloud Run Worker Directly
```bash
curl -X POST https://your-cloud-run-url/enqueue \
  -H 'Content-Type: application/json' \
  -d '{
    "video_url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
    "summary_format": "bullet_points"
  }'
```

### Test Job Status
```bash
curl "https://your-cloud-run-url/status/JOB_ID"
```

### Test Vercel Integration
```bash
curl -X POST https://your-vercel-app.vercel.app/api/submit \
  -H 'Content-Type: application/json' \
  -d '{
    "video_url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
    "summary_format": "bullet_points"
  }'
```

## 💰 Cost Estimation

### Monthly Costs (estimated)
- **Cloud Run**: $5-15 (processing ~500 videos/month)
- **Cloud Storage**: $1-3 (transcripts/summaries are small)
- **Pub/Sub**: $0.50-2 (message volume)
- **Firestore**: $1-5 (job status queries)
- **Vercel**: Unchanged (keep current plan)

**Total**: ~$10-25/month for moderate usage

## 🔧 Troubleshooting

### Common Issues

1. **"ModuleNotFoundError" in Cloud Run**
   - Check Dockerfile includes all dependencies
   - Verify PYTHONPATH is set correctly

2. **Pub/Sub messages not delivered**
   - Check subscription push endpoint URL
   - Verify service account permissions
   - Check Cloud Run service is running

3. **Firestore permission errors**
   - Ensure Firestore API is enabled
   - Check service account has Firestore permissions
   - Verify database exists in correct region

4. **YouTube rate limiting**
   - Check yt-dlp sleep intervals in captions.py
   - Verify cookies are properly set
   - Consider using multiple regions

### Logs
```bash
# Cloud Run logs
gcloud logs read --service=vidscribe-worker --limit=50

# Pub/Sub logs
gcloud logs read --resource-type=pubsub_subscription --limit=50
```

## 🚀 Next Steps

1. **Add authentication** (optional)
2. **Implement user quotas** with Cloud Tasks
3. **Add more video sources** (Vimeo, etc.)
4. **Implement webhook notifications** instead of polling
5. **Add batch processing** for multiple videos
6. **Implement caching** for repeated requests

## 📚 Resources

- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Pub/Sub Documentation](https://cloud.google.com/pubsub/docs)
- [Vercel API Routes](https://vercel.com/docs/concepts/functions/serverless-functions)
- [Gemini API Documentation](https://ai.google.dev/docs)
