# Running Backend Locally with Docker

This guide will help you run the Flask backend locally using Docker.

## Prerequisites

- Docker and Docker Compose installed on your system
- Google API key and project configuration

## Quick Start

### 1. Set up Environment Variables

Create a `.env` file in the root directory with the following variables:

```bash
# Flask Configuration
SECRET_KEY=your-secret-key-here
FLASK_ENV=development
FLASK_DEBUG=1

# Google Cloud Configuration
GOOGLE_API_KEY=your-google-api-key-here
GOOGLE_CLOUD_PROJECT=your-google-cloud-project-id
GOOGLE_CLOUD_LOCATION=global
GOOGLE_CSE_ID=your-custom-search-engine-id

# Upload Configuration
UPLOAD_DIR=./uploads

# Model Configuration
DEFAULT_MODEL=gemini-2.5-pro

# RAG Configuration
RAG_ARTIFACTS_DIR=./mmfood-rag/artifacts
```

### 2. Run the Backend

#### Option A: Using the provided scripts

**On Windows (PowerShell):**

```powershell
.\run-local.ps1
```

**On Linux/Mac:**

```bash
chmod +x run-local.sh
./run-local.sh
```

#### Option B: Manual Docker commands

```bash
# Build and run using docker-compose
docker-compose -f docker-compose.local.yml up --build

# Or build and run manually
docker build -f Dockerfile.local -t food-analyzer-backend .
docker run -p 5000:5000 --env-file .env food-analyzer-backend
```

### 3. Access the API

Once running, the backend will be available at:

- **Base URL**: http://localhost:5000
- **Health Check**: http://localhost:5000/health
- **Analysis Endpoint**: http://localhost:5000/analysis
- **RAG Endpoint**: http://localhost:5000/rag

## Development Features

The local Docker setup includes:

- **Hot Reloading**: Flask development server with debug mode enabled
- **Volume Mounting**: Uploads and RAG artifacts are persisted on your local machine
- **Environment Variables**: Easy configuration through `.env` file
- **Debug Mode**: Full Flask debugging capabilities

## Stopping the Container

```bash
# If using docker-compose
docker-compose -f docker-compose.local.yml down

# If running manually
docker stop <container_id>
```

## Troubleshooting

### Build Failures (File Permission Issues)

If you encounter build failures related to file permissions (common on Windows), run the cleanup script first:

**Windows:**

```powershell
.\clean-docker.ps1
```

**Linux/Mac:**

```bash
chmod +x clean-docker.sh
./clean-docker.sh
```

Then try running the backend again.

### Port Already in Use

If port 5000 is already in use, you can modify the port in `docker-compose.local.yml`:

```yaml
ports:
  - "5001:5000" # Change 5001 to any available port
```

### Permission Issues

On Linux/Mac, you might need to run the script with sudo or adjust file permissions:

```bash
chmod +x run-local.sh
```

### Environment Variables Not Loading

Make sure your `.env` file is in the root directory and has the correct format (no spaces around `=`).

### Large Build Context

The `.dockerignore` file has been configured to exclude unnecessary files. If the build is still slow, check that large files are being excluded.

## File Structure

```
├── Dockerfile.local          # Local development Dockerfile
├── docker-compose.local.yml  # Docker Compose for local development
├── .dockerignore            # Files to exclude from Docker build
├── run-local.sh             # Linux/Mac startup script
├── run-local.ps1            # Windows PowerShell startup script
├── clean-docker.sh          # Linux/Mac cleanup script
├── clean-docker.ps1         # Windows cleanup script
├── .env                     # Environment variables (create this)
└── README_LOCAL_DOCKER.md   # This file
```
