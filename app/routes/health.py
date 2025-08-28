from flask import Blueprint, jsonify, render_template_string

health_bp = Blueprint('health', __name__)

INDEX_HTML = """<!doctype html>
<html>
  <head><meta charset="utf-8"><title>Food Analyzer</title></head>
  <body style="font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; padding: 24px; max-width: 760px; margin: auto">
    <h1>Food Analyzer (LLM-only)</h1>
    <form method="POST" action="/analyze" enctype="multipart/form-data" style="border:1px solid #eee; padding:16px; border-radius:10px">
      <div><input type="file" name="image" accept="image/*" multiple required></div>
      <div style="margin-top:8px">Model: <input name="model" value="gemini-2.5-pro" style="width:220px"></div>
      <div style="margin-top:8px">
        <label><input type="checkbox" name="use_logmeal" value="true"> Use LogMeal for ingredient detection</label>
        <small style="color:#666; display:block; margin-top:4px">Unchecked = use Gemini, Checked = use LogMeal</small>
      </div>
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
