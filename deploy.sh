#!/bin/bash

# Food Analyzer Deployment Script
# This script deploys both the Flask backend and Angular frontend to Google App Engine

set -e  # Exit on any error

echo "🚀 Starting Food Analyzer deployment to Google Cloud Platform..."

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI is not installed. Please install it first:"
    echo "   https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if user is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ Not authenticated with gcloud. Please run:"
    echo "   gcloud auth login"
    exit 1
fi

# Set the project
PROJECT_ID="alert-arbor-468516-g5"
echo "📋 Setting project to: $PROJECT_ID"
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "🔧 Enabling required APIs..."
gcloud services enable appengine.googleapis.com
gcloud services enable aiplatform.googleapis.com
gcloud services enable cloudbuild.googleapis.com

# Create App Engine application if it doesn't exist
echo "🔧 Creating App Engine application..."
gcloud app create --region=asia-northeast1 --quiet || echo "App Engine application already exists"

# Deploy Backend
echo "🔧 Deploying Flask backend..."
cd "$(dirname "$0")"
gcloud app deploy app.yaml --quiet

# Deploy Frontend
echo "🔧 Building and deploying Angular frontend..."
cd frontend/food-analyzer-ui

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    npm install
fi

# Build for production
echo "🔨 Building frontend for production..."
npm run build -- --configuration=production

# Deploy frontend
echo "🚀 Deploying frontend..."
gcloud app deploy app.yaml --quiet

# Get the URLs
echo "✅ Deployment complete!"
echo ""
echo "🌐 Your application is now live at:"
echo "   Frontend: https://frontend-dot-$PROJECT_ID.asia-northeast1.r.appspot.com"
echo "   Backend API: https://$PROJECT_ID.asia-northeast1.r.appspot.com"
echo ""
echo "📝 Important notes:"
echo "   1. Make sure to set your environment variables in Google Cloud Console:"
echo "      - LOGMEAL_TOKEN (if using LogMeal)"
echo "      - GOOGLE_APPLICATION_CREDENTIALS (for Gemini API)"
echo "   2. You can view logs with: gcloud app logs tail"
echo "   3. You can monitor your app at: https://console.cloud.google.com/appengine"
