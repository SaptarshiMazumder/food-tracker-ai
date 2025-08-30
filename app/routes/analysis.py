import uuid
import os
from flask import Blueprint, request, jsonify, Response, current_app
from werkzeug.utils import secure_filename

from ..services.analysis_service import AnalysisService
from ..utils.helpers import (
    gather_images, save_uploads, load_job_paths, save_job_manifest, 
    persist_history, parse_use_logmeal_param
)

analysis_bp = Blueprint('analysis', __name__)

@analysis_bp.post("/analyze")
def analyze():
    """Classic non-streaming analysis endpoint"""
    files_in = gather_images(request.files)
    if not files_in:
        return jsonify({"error": "missing_file", "msg": "form field 'image' or 'images[]' required"}), 400
    
    try:
        save_paths = save_uploads(files_in)
    except ValueError as ve:
        return jsonify({"error": "bad_extension", "msg": str(ve)}), 400

    model = request.form.get("model") or request.args.get("model") or current_app.config['DEFAULT_MODEL']
    use_logmeal = parse_use_logmeal_param(
        request.form.get("use_logmeal") or request.args.get("use_logmeal")
    )
    
    service = AnalysisService()
    res = service.run_full_analysis(save_paths, model, use_logmeal)
    
    if res.get("error"):
        return jsonify({"error": res["error"], "dish": res.get("dish")}), 400

    data = service.finalize_payload(res, save_paths)
    persist_history(data, save_paths[0])
    print(f"[api] ⏱ total {data.get('total_ms')} ms  → timings: {data.get('timings')}")
    return jsonify(data), 200

@analysis_bp.post("/upload")
def upload_only():
    """Upload files and return job ID for streaming analysis"""
    files_in = gather_images(request.files)
    if not files_in:
        return jsonify({"error": "missing_file", "msg": "form field 'image' or 'images[]' required"}), 400
    
    try:
        save_paths = save_uploads(files_in)
    except ValueError as ve:
        return jsonify({"error": "bad_extension", "msg": str(ve)}), 400

    job_id = uuid.uuid4().hex
    save_job_manifest(job_id, save_paths)
    return jsonify({"job_id": job_id}), 200

@analysis_bp.get("/analyze_sse")
def analyze_sse():
    """SSE stream for analysis results"""
    job_id = request.args.get("job_id", "")
    if not job_id:
        return jsonify({"error": "missing_job_id"}), 400
    
    image_paths = load_job_paths(job_id)
    if not image_paths:
        return jsonify({"error": "invalid_job_id"}), 404

    model = request.args.get("model") or current_app.config['DEFAULT_MODEL']
    use_logmeal = parse_use_logmeal_param(request.args.get("use_logmeal"))

    service = AnalysisService()
    
    def event_stream():
        for event in service.stream_analysis(image_paths, model, use_logmeal):
            yield event
        # Persist the final result
        # Note: This would need to be handled differently in the streaming context
        # For now, we'll let the frontend handle persistence

    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
        "Access-Control-Allow-Origin": "*",
    }
    return Response(event_stream(), headers=headers)

@analysis_bp.get("/history")
def history():
    """Get analysis history"""
    limit = int(request.args.get("limit", 20))
    upload_dir = current_app.config['UPLOAD_DIR']
    
    files = [f for f in os.listdir(upload_dir) if f.lower().endswith(".json")]
    files.sort(reverse=True)
    items = []
    
    for fname in files[:limit]:
        try:
            with open(os.path.join(upload_dir, fname), "r", encoding="utf-8") as f:
                import json
                rec = json.load(f)
            items.append({
                "id": fname,
                "dish": rec.get("dish"),
                "dish_confidence": rec.get("dish_confidence"),
                "total_kcal": rec.get("total_kcal"),
                "total_protein_g": rec.get("total_protein_g"),
                "total_carbs_g": rec.get("total_carbs_g"),
                "total_fat_g": rec.get("total_fat_g"),
                "created_at": rec.get("created_at"),
                "total_ms": rec.get("total_ms"),
            })
        except Exception:
            continue
    
    return jsonify({"items": items})
