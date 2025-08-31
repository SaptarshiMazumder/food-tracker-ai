# Use lightweight Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy environment files first (if they exist)
# This ensures environment variables are available in the container
COPY .env* ./

# Copy project files
COPY . .

# Set default Google Cloud authentication environment variables
# Note: We use GOOGLE_API_KEY for authentication instead of Application Default Credentials
ENV GOOGLE_CLOUD_PROJECT=alert-arbor-468516-g5
ENV GOOGLE_CLOUD_LOCATION=global
# Ensure GOOGLE_API_KEY is available from .env file
# The gemini_client.py will use this API key for authentication

# Expose Flask port
EXPOSE 5000

# Run the app
CMD ["python", "run.py"]
