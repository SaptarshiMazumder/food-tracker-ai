# Food Analyzer Deployment Guide

This guide will help you deploy your Food Analyzer application to Google Cloud Platform so you can share it with your friends!

## Prerequisites

1. **Google Cloud Account**: You need a Google Cloud account with billing enabled
2. **Google Cloud CLI**: Install the gcloud CLI tool
3. **Node.js**: For building the Angular frontend
4. **Python**: For the Flask backend

## Quick Deployment

### 1. Install Google Cloud CLI

Download and install from: https://cloud.google.com/sdk/docs/install

### 2. Authenticate with Google Cloud

```bash
gcloud auth login
gcloud config set project alert-arbor-468516-g5
```

### 3. Run the Deployment Script

```bash
# Make the script executable (on Unix-like systems)
chmod +x deploy.sh

# Run the deployment
./deploy.sh
```

## Manual Deployment Steps

If you prefer to deploy manually, follow these steps:

### Backend Deployment

1. **Navigate to the project root**:

   ```bash
   cd /path/to/your/Langchain_2
   ```

2. **Deploy the Flask backend**:
   ```bash
   gcloud app deploy app.yaml
   ```

### Frontend Deployment

1. **Navigate to the frontend directory**:

   ```bash
   cd frontend/food-analyzer-ui
   ```

2. **Install dependencies**:

   ```bash
   npm install
   ```

3. **Build for production**:

   ```bash
   npm run build -- --configuration=production
   ```

4. **Deploy the frontend**:
   ```bash
   gcloud app deploy app.yaml
   ```

## Environment Variables Setup

After deployment, you need to set up environment variables in Google Cloud Console:

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Navigate to App Engine > Settings > Environment Variables
3. Add the following variables:

### Required Variables:

- `LOGMEAL_TOKEN`: Your LogMeal API token (if using LogMeal)
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to your Google service account key

### Optional Variables:

- `GOOGLE_CLOUD_PROJECT`: alert-arbor-468516-g5
- `GOOGLE_CLOUD_LOCATION`: asia-northeast1
- `UPLOAD_DIR`: /tmp/uploads

## Setting up Google Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Navigate to IAM & Admin > Service Accounts
3. Create a new service account or use existing one
4. Grant the following roles:
   - App Engine Deployer
   - Cloud Build Editor
   - Vertex AI User
5. Create and download a JSON key file
6. Set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to point to this file

## Your Application URLs

After successful deployment, your application will be available at:

- **Frontend**: https://food-analyzer-frontend-dot-alert-arbor-468516-g5.asia-northeast1.r.appspot.com
- **Backend API**: https://food-analyzer-backend-dot-alert-arbor-468516-g5.asia-northeast1.r.appspot.com

## Monitoring and Logs

- **View logs**: `gcloud app logs tail`
- **Monitor app**: https://console.cloud.google.com/appengine
- **Check status**: `gcloud app describe`

## Troubleshooting

### Common Issues:

1. **Authentication Error**: Run `gcloud auth login`
2. **Permission Denied**: Make sure your account has the necessary roles
3. **Build Failures**: Check that all dependencies are in requirements.txt
4. **API Errors**: Ensure required APIs are enabled in your project

### Enable Required APIs:

```bash
gcloud services enable appengine.googleapis.com
gcloud services enable aiplatform.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

## Cost Optimization

- The app is configured to scale down to 0 instances when not in use
- You can adjust the scaling settings in `app.yaml` files
- Monitor your usage in the Google Cloud Console

## Security Notes

- All traffic is served over HTTPS
- Environment variables are encrypted at rest
- Consider setting up a custom domain for production use

## Next Steps

1. Test your deployed application
2. Share the frontend URL with your friends
3. Monitor usage and performance
4. Consider setting up a custom domain
5. Implement additional security measures if needed

## Support

If you encounter any issues:

1. Check the deployment logs
2. Verify environment variables are set correctly
3. Ensure all APIs are enabled
4. Check your Google Cloud billing status
