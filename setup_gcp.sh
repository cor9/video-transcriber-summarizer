#!/bin/bash
# GCP Setup Script for VidScribe2AI Hybrid Architecture

set -e

PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project)}
BUCKET_NAME="vidscribe-artifacts"
TOPIC_NAME="transcribe-jobs"
SERVICE_NAME="vidscribe-worker"
REGION="us-central1"

echo "🚀 Setting up GCP resources for VidScribe2AI"
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"

# Check if gcloud is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ Please authenticate with gcloud first:"
    echo "   gcloud auth login"
    exit 1
fi

# Set the project
gcloud config set project $PROJECT_ID

echo "📦 Creating Cloud Storage bucket..."
gsutil mb -l $REGION gs://$BUCKET_NAME || echo "Bucket already exists"

echo "📢 Creating Pub/Sub topic..."
gcloud pubsub topics create $TOPIC_NAME || echo "Topic already exists"

echo "🔧 Building and deploying Cloud Run service..."
# Build the container
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

# Deploy to Cloud Run
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --cpu 2 \
  --memory 2Gi \
  --timeout 900 \
  --set-env-vars "BUCKET_NAME=$BUCKET_NAME,GOOGLE_CLOUD_PROJECT=$PROJECT_ID"

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --format='value(status.url)')

echo "🔗 Creating Pub/Sub subscription..."
gcloud pubsub subscriptions create ${TOPIC_NAME}-sub \
  --topic $TOPIC_NAME \
  --push-endpoint=$SERVICE_URL/jobs \
  --push-auth-service-account=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')-compute@developer.gserviceaccount.com || echo "Subscription already exists"

echo "🔑 Setting up IAM permissions..."
# Enable required APIs
gcloud services enable pubsub.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable firestore.googleapis.com
gcloud services enable cloudbuild.googleapis.com

# Create Firestore database if it doesn't exist
gcloud firestore databases create --region=$REGION || echo "Firestore database already exists"

echo "✅ GCP setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Set environment variables in Vercel:"
echo "   - GOOGLE_CLOUD_PROJECT=$PROJECT_ID"
echo "   - PUBSUB_TOPIC=$TOPIC_NAME"
echo "   - GOOGLE_APPLICATION_CREDENTIALS (service account key)"
echo ""
echo "2. Set environment variables in Cloud Run:"
echo "   - GEMINI_API_KEY=your_gemini_key"
echo "   - BUCKET_NAME=$BUCKET_NAME"
echo "   - GOOGLE_CLOUD_PROJECT=$PROJECT_ID"
echo ""
echo "3. Test the deployment:"
echo "   curl -X POST $SERVICE_URL/enqueue \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"video_url\":\"https://youtube.com/watch?v=dQw4w9WgXcQ\",\"summary_format\":\"bullet_points\"}'"
echo ""
echo "🌐 Cloud Run Service URL: $SERVICE_URL"
