#!/bin/bash

# Deploy Cloud Run worker for VidScribe2AI
set -e

PROJECT_ID="video-transcriber-456789"
SERVICE_NAME="vidscribe-worker"
REGION="us-central1"

echo "🚀 Deploying VidScribe2AI Cloud Run worker..."

# Build and deploy
gcloud run deploy $SERVICE_NAME \
  --source . \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 900 \
  --concurrency 10 \
  --max-instances 5 \
  --project $PROJECT_ID

echo "✅ Deployment complete!"
echo "🌐 Service URL: https://$SERVICE_NAME-$REGION-$PROJECT_ID.a.run.app"
