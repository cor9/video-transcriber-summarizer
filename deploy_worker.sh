#!/bin/bash
# Deploy Cloud Run Worker for VidScribe2AI

set -e

PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project)}
SERVICE_NAME="vidscribe-worker"
REGION="us-central1"

echo "🚀 Deploying VidScribe2AI Cloud Run Worker"
echo "Project: $PROJECT_ID"
echo "Service: $SERVICE_NAME"
echo "Region: $REGION"

# Check if authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ Please authenticate with gcloud first:"
    echo "   gcloud auth login"
    exit 1
fi

# Set project
gcloud config set project $PROJECT_ID

# Deploy to Cloud Run
echo "📦 Building and deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --source cloud-run-worker \
  --region $REGION \
  --allow-unauthenticated \
  --cpu 1 \
  --memory 512Mi \
  --max-instances 20 \
  --set-env-vars GEMINI_API_KEY=$GEMINI_API_KEY,GEMINI_MODEL=gemini-1.5-pro-latest

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format='value(status.url)')

echo "✅ Deployment complete!"
echo "🌐 Service URL: $SERVICE_URL"
echo ""
echo "📋 Next steps:"
echo "1. Set WORKER_URL in Vercel:"
echo "   vercel env add WORKER_URL"
echo "   (Enter: $SERVICE_URL)"
echo ""
echo "2. Test the worker:"
echo "   curl -X POST $SERVICE_URL/summarize \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"url\":\"https://youtube.com/watch?v=dQw4w9WgXcQ\",\"summary_format\":\"bullet_points\"}'"
echo ""
echo "3. Deploy Vercel frontend:"
echo "   vercel --prod"
