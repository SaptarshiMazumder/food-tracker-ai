import os
import serverless_wsgi

# Ensure uploads are writable in Lambda
os.environ.setdefault("UPLOAD_DIR", "/tmp/uploads")

from app import create_app

app = create_app()

def handler(event, context):
    return serverless_wsgi.handle_request(app, event, context)

