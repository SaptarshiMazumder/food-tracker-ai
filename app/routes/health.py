from flask import Blueprint, jsonify, render_template_string, request
from werkzeug.exceptions import BadRequest
from app.services.graphs.health_score import run_health_score

health_bp = Blueprint('health', __name__)

INDEX_HTML = """<!doctype html>
<html>
  <head><meta charset="utf-8"><title>Food Analyzer</title></head>
  <body style="font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; padding: 24px; max-width: 760px; margin: auto">
    <h1>Food Analyzer (LLM-only)</h1>
    <form method="POST" action="/analyze" enctype="multipart/form-data" style="border:1px solid #eee; padding:16px; border-radius:10px">
      <div><input type="file" name="image" accept="image/*" multiple required></div>
      <div style="margin-top:8px">Model: <input name="model" value="gemini-2.5-pro" style="width:220px"></div>
      <div style="margin-top:8px"><button type="submit">Analyze (non-streaming)</button></div>
    </form>
    <p style="margin-top:16px;color:#666">For streaming UI, the Angular app uses /upload + /analyze_sse.</p>
  </body>
</html>"""

@health_bp.get("/")
def index():
    """Main index page"""
    return render_template_string(INDEX_HTML)

@health_bp.get("/health")
def health():
    """Health check endpoint"""
    return {"ok": True}, 200

@health_bp.route("/health-score", methods=["POST"])
def health_score():
    """Health score endpoint"""
    body = request.get_json(silent=True)
    if not body:
        raise BadRequest("JSON body required")

    try:
        result = run_health_score(body)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": "health_score_failed", "message": str(e)}), 500
