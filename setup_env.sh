#!/bin/bash

# Environment Variables Setup Script for Google App Engine
# This script helps you set up environment variables for your Food Analyzer app

set -e

PROJECT_ID="alert-arbor-468516-g5"
SERVICE_NAME="default"

echo "🔧 Setting up environment variables for Food Analyzer..."

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
echo "📋 Setting project to: $PROJECT_ID"
gcloud config set project $PROJECT_ID

echo ""
echo "📝 Please provide the following information:"
echo ""

# Get LogMeal token
read -p "Enter your LogMeal API token (or press Enter to skip): " LOGMEAL_TOKEN

# Get Google service account key path
read -p "Enter the path to your Google service account JSON key file (or press Enter to skip): " SERVICE_ACCOUNT_KEY_PATH

echo ""
echo "🔧 Setting up environment variables..."

# Create a temporary app.yaml with environment variables
cat > temp_app.yaml << EOF
runtime: python311
service: $SERVICE_NAME

env_variables:
  GOOGLE_CLOUD_PROJECT: "$PROJECT_ID"
  GOOGLE_CLOUD_LOCATION: "asia-northeast1"
  UPLOAD_DIR: "/tmp/uploads"
EOF

# Add optional environment variables if provided
if [ ! -z "$LOGMEAL_TOKEN" ]; then
    echo "  LOGMEAL_TOKEN: \"$LOGMEAL_TOKEN\"" >> temp_app.yaml
fi

if [ ! -z "$SERVICE_ACCOUNT_KEY_PATH" ] && [ -f "$SERVICE_ACCOUNT_KEY_PATH" ]; then
    echo "  GOOGLE_APPLICATION_CREDENTIALS: \"$SERVICE_ACCOUNT_KEY_PATH\"" >> temp_app.yaml
fi

cat >> temp_app.yaml << EOF

handlers:
  - url: /.*
    script: auto
    secure: always

automatic_scaling:
  target_cpu_utilization: 0.6
  min_instances: 0
  max_instances: 10
  target_throughput_utilization: 0.6

resources:
  cpu: 1
  memory_gb: 2
  disk_size_gb: 10

instance_class: F1
EOF

# Deploy with the new configuration
echo "🚀 Deploying with updated environment variables..."
gcloud app deploy temp_app.yaml --quiet

# Clean up
rm temp_app.yaml

echo ""
echo "✅ Environment variables have been set up!"
echo ""
echo "🌐 Your backend is now configured with the environment variables."
echo "   You can verify the deployment at:"
echo "   https://$PROJECT_ID.asia-northeast1.r.appspot.com"
echo ""
echo "📝 To update environment variables in the future, run this script again."
