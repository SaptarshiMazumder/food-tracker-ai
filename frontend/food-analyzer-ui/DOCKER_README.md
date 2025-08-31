# Frontend Docker Setup

This directory contains Docker configuration for the Food Analyzer frontend application.

## Files

- `Dockerfile` - Multi-stage Docker build for the Angular application
- `nginx.conf` - Nginx configuration optimized for Angular apps
- `docker-compose.yml` - Docker Compose configuration for easy deployment
- `.dockerignore` - Files to exclude from Docker build context

## Quick Start

### Using Docker Compose (Recommended)

1. Build and run the container:

   ```bash
   docker-compose up --build
   ```

2. Access the application at: http://localhost:3000

3. Stop the container:
   ```bash
   docker-compose down
   ```

### Using Docker directly

1. Build the image:

   ```bash
   docker build -t food-analyzer-frontend .
   ```

2. Run the container:

   ```bash
   docker run -p 3000:80 food-analyzer-frontend
   ```

3. Access the application at: http://localhost:3000

## Development

For development, you can still use the standard Angular CLI commands:

```bash
npm install
npm start
```

This will run the development server on http://localhost:4200 with hot reload.

## Production Build

The Dockerfile uses a multi-stage build:

1. **Build stage**: Uses Node.js to install dependencies and build the Angular application
2. **Production stage**: Uses nginx to serve the built static files

## Configuration

### Nginx Configuration

The `nginx.conf` file includes:

- Gzip compression for better performance
- Security headers
- Proper handling of Angular routing (SPA fallback)
- Static asset caching
- Health check endpoint at `/health`

### Environment Variables

You can customize the build by setting environment variables:

- `NODE_ENV` - Set to `production` for optimized builds

## Troubleshooting

### Build Issues

If you encounter build issues:

1. Clear Docker cache:

   ```bash
   docker system prune -a
   ```

2. Rebuild without cache:
   ```bash
   docker-compose build --no-cache
   ```

### Port Conflicts

If port 3000 is already in use, modify the `docker-compose.yml` file:

```yaml
ports:
  - "8080:80" # Change 3000 to any available port
```

### Health Check

The container includes a health check that verifies the application is running:

```bash
docker ps  # Check container status
```

## Deployment

For production deployment:

1. Build the image:

   ```bash
   docker build -t food-analyzer-frontend:latest .
   ```

2. Push to your registry:

   ```bash
   docker tag food-analyzer-frontend:latest your-registry/food-analyzer-frontend:latest
   docker push your-registry/food-analyzer-frontend:latest
   ```

3. Deploy using your preferred orchestration tool (Kubernetes, Docker Swarm, etc.)



