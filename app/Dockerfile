##### Stage: Local Flask service (development) #####
FROM python:3.11-slim AS local_service

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install dependencies (context expected to be ./app for this stage)
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


##### Stage: AWS Lambda development service (container image) #####
FROM public.ecr.aws/lambda/python:3.11 AS aws_dev_service

# Lambda looks for the handler in /var/task
WORKDIR /var/task

# Install dependencies (context expected to be repository root for this stage)
COPY app/requirements.txt ./
RUN python -m pip install --upgrade pip wheel setuptools \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir serverless-wsgi

# Copy application code and artifacts
COPY app ./app
COPY mmfood-rag ./mmfood-rag

# Copy static Lambda handler
COPY app/lambda_handler.py ./lambda_handler.py

# Runtime environment
ENV PYTHONPATH=/var/task
ENV UPLOAD_DIR=/tmp/uploads
RUN mkdir -p /tmp/uploads

# Set the Lambda handler (module.function)
CMD ["lambda_handler.handler"]
