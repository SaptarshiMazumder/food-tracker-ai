# Dynamic Gemini Model Management

This document explains how to dynamically manage Gemini models in your Food Analyzer application, especially useful for production deployments on AWS.

## Overview

The system now supports:

- **Environment Variable Configuration**: Set models via `GEMINI_MODEL` environment variable
- **Runtime Model Switching**: Change models via HTTP API endpoints
- **Automatic Model Switching**: Auto-switch models based on failure patterns
- **Command Line Tools**: Manage models from scripts or automation

## Quick Start

### 1. Environment Variable (Recommended for Docker)

Set the model when starting your container:

```bash
# Set model via environment variable
export GEMINI_MODEL="gemini-1.5-flash"
docker run -e GEMINI_MODEL="gemini-1.5-flash" your-app

# Or in docker-compose
environment:
  GEMINI_MODEL: "gemini-1.5-flash"
```

### 2. Runtime API Endpoints

#### Get Current Model

```bash
curl http://localhost:5000/model
```

#### Change Model

```bash
curl -X POST http://localhost:5000/model \
  -H "Content-Type: application/json" \
  -d '{"model": "gemini-1.5-flash"}'
```

#### Get Model Status

```bash
curl http://localhost:5000/model-status
```

## Available Models

| Model                  | Priority | Use Case    | Reliability           |
| ---------------------- | -------- | ----------- | --------------------- |
| `gemini-2.5-pro`       | 1        | Primary     | High (when available) |
| `gemini-1.5-pro`       | 2        | Secondary   | High                  |
| `gemini-1.5-flash`     | 3        | Fallback    | Very High             |
| `gemini-2.0-flash-exp` | 4        | Last Resort | High                  |

## Command Line Tools

### Model Manager Script

```bash
# Get current model
python app/scripts/model_manager.py --get

# Set new model
python app/scripts/model_manager.py --set gemini-1.5-flash

# List available models
python app/scripts/model_manager.py --list

# Check service health
python app/scripts/model_manager.py --health

# Use with custom URL
python app/scripts/model_manager.py --url http://your-aws-instance:5000 --get
```

### Auto Model Switcher

Automatically switches models based on failure patterns:

```bash
# Start monitoring (switches models automatically)
python app/scripts/auto_model_switcher.py --monitor

# Show configuration
python app/scripts/auto_model_switcher.py --config

# Simulate a failure for testing
python app/scripts/auto_model_switcher.py --test-failure

# Monitor with custom interval
python app/scripts/auto_model_switcher.py --monitor --interval 30
```

## AWS Deployment

### EC2 Deployment

1. **Launch EC2 Instance**

   ```bash
   # Install Docker
   sudo yum update -y
   sudo yum install -y docker
   sudo service docker start
   sudo usermod -a -G docker ec2-user
   ```

2. **Deploy with Docker Compose**

   ```bash
   # Copy your code
   git clone your-repo
   cd your-repo

   # Set environment variables
   export GEMINI_MODEL="gemini-1.5-flash"
   export GOOGLE_API_KEY="your-key"

   # Start services
   docker-compose -f docker-compose.production.yml up -d
   ```

3. **Set Model via Environment**
   ```bash
   # In docker-compose.production.yml
   environment:
     GEMINI_MODEL: "gemini-1.5-flash"
   ```

### ECS/Fargate Deployment

```yaml
# task-definition.json
{
  "containerDefinitions":
    [{ "name": "food-analyzer", "environment": [{ "name": "GEMINI_MODEL", "value": "gemini-1.5-flash" }] }],
}
```

## Production Monitoring

### 1. Health Checks

```bash
# Check service health
curl http://your-instance:5000/health

# Check model status
curl http://your-instance:5000/model-status
```

### 2. Automatic Model Switching

Run the auto-switcher as a service:

```bash
# Create systemd service
sudo nano /etc/systemd/system/auto-model-switcher.service
```

```ini
[Unit]
Description=Auto Model Switcher
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/path/to/your/app
ExecStart=/usr/bin/python3 app/scripts/auto_model_switcher.py --monitor --url http://localhost:5000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl enable auto-model-switcher
sudo systemctl start auto-model-switcher
```

### 3. Logging

Monitor logs:

```bash
# Application logs
docker logs food-analyzer

# Auto-switcher logs
tail -f auto_model_switcher.log

# System service logs
sudo journalctl -u auto-model-switcher -f
```

## Failure Handling Strategy

### Automatic Fallback Logic

1. **Primary Model** (`gemini-2.5-pro`): 3 failures → switch
2. **Secondary Model** (`gemini-1.5-pro`): 5 failures → switch
3. **Fallback Model** (`gemini-1.5-flash`): 10 failures → switch
4. **Last Resort** (`gemini-2.0-flash-exp`): 15 failures → alert

### Cooldown Periods

- **gemini-2.5-pro**: 30 minutes before retry
- **gemini-1.5-pro**: 15 minutes before retry
- **gemini-1.5-flash**: 10 minutes before retry
- **gemini-2.0-flash-exp**: 5 minutes before retry

## Best Practices

### 1. Start with Reliable Models

```bash
# For production, start with stable models
export GEMINI_MODEL="gemini-1.5-flash"
```

### 2. Monitor and Adjust

```bash
# Check model performance
python app/scripts/auto_model_switcher.py --config

# Adjust thresholds if needed
# Edit MODEL_CONFIGS in auto_model_switcher.py
```

### 3. Use Environment Variables

```bash
# Always use environment variables in production
# Avoid hardcoding model names
```

### 4. Regular Health Checks

```bash
# Set up cron job for health checks
*/5 * * * * curl -f http://localhost:5000/health || echo "Service down"
```

## Troubleshooting

### Common Issues

1. **Model Not Changing**

   ```bash
   # Check if endpoint is working
   curl http://localhost:5000/model

   # Check logs
   docker logs food-analyzer
   ```

2. **Auto-switcher Not Working**

   ```bash
   # Check service status
   sudo systemctl status auto-model-switcher

   # Check logs
   sudo journalctl -u auto-model-switcher -f
   ```

3. **Environment Variable Not Working**

   ```bash
   # Verify in container
   docker exec food-analyzer env | grep GEMINI_MODEL

   # Check docker-compose
   docker-compose config
   ```

### Debug Mode

```bash
# Enable debug logging
export FLASK_ENV=development
export FLASK_DEBUG=1

# Check configuration
python -c "from app.config.settings import Config; print(Config.DEFAULT_MODEL)"
```

## Security Considerations

1. **API Endpoints**: Consider adding authentication for model switching
2. **Environment Variables**: Use AWS Secrets Manager for sensitive values
3. **Network Security**: Restrict access to model management endpoints
4. **Logging**: Monitor for unauthorized model changes

## Cost Optimization

- **gemini-1.5-flash**: Most cost-effective for basic tasks
- **gemini-2.5-pro**: Best quality but higher cost
- **Auto-switching**: Prevents wasting API calls on failing models

## Support

For issues or questions:

1. Check logs first
2. Verify environment variables
3. Test endpoints manually
4. Check AWS service status
5. Review model availability


