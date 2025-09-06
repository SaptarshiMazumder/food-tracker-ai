import uuid
import os
import json
from flask import Blueprint, request, jsonify, Response, current_app
from werkzeug.utils import secure_filename

from ..graphs import run_food_analysis
from ..services.food_analysis.food_analysis_formatter import FoodAnalysisFormatter
from ..services.food_analysis.food_analysis_streamer import FoodAnalysisStreamer
from ..services.food_analysis.food_analysis_config import FoodAnalysisConfig
from app.graphs.nutrition_analysis import run_nutrition_analysis
from ..utils.helpers import (
    gather_images, save_uploads, load_job_paths, save_job_manifest, 
    persist_history
)
from ..config.settings import Config
from ..services.shared.dynamodb_store import PartialStore

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
    
    config = FoodAnalysisConfig()
    try:
        res = run_food_analysis(save_paths, config.project, config.location, model)
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"[ERROR] Food analysis exception: {str(e)}")
        print(f"[ERROR] Full traceback: {error_details}")
        return jsonify({"error": "food_analysis_exception", "msg": str(e), "details": error_details}), 500
    
    if res.get("error"):
        return jsonify({"error": res["error"], "dish": res.get("dish")}), 400

    data = FoodAnalysisFormatter.create_final_payload(res, save_paths)
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

    config = FoodAnalysisConfig()
    streamer = FoodAnalysisStreamer(config)
    store = PartialStore()

    def _update_partial(phase: str, data: dict):
        # Write to DynamoDB (best-effort)
        try:
            store.put_phase(job_id, phase, data or {})
        except Exception:
            pass
        # Also write local file for dev
        try:
            upload_dir = current_app.config['UPLOAD_DIR']
            p = os.path.join(upload_dir, f"{job_id}.partial.json")
            state = {}
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    state = json.load(f)
            state.update(data or {})
            flags = state.get("flags") or {}
            flags[phase] = True
            state["flags"] = flags
            state["last_phase"] = phase
            with open(p, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False)
        except Exception:
            pass

    def event_stream():
        for event in streamer.stream_analysis(image_paths, model):
            # Parse SSE frame and persist partials
            try:
                ev_name = None
                ev_data = None
                for line in event.splitlines():
                    if line.startswith('event: '):
                        ev_name = line[len('event: '):].strip()
                    elif line.startswith('data: '):
                        ev_data = json.loads(line[len('data: '):])
                if ev_name in ("recognize", "ing_quant", "calories", "done") and isinstance(ev_data, dict):
                    _update_partial(ev_name, ev_data)
            except Exception:
                pass
            yield event

    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
        "Access-Control-Allow-Origin": "*",
    }
    return Response(event_stream(), headers=headers)

@analysis_bp.get("/status")
def analyze_status():
    """Poll the current aggregated status for a given job_id (for clients where SSE is buffered)."""
    job_id = request.args.get("job_id", "")
    if not job_id:
        return jsonify({"error": "missing_job_id"}), 400
    # Prefer DynamoDB; fallback to local file
    try:
        data = PartialStore().get_status(job_id)
        if data:
            return jsonify(data), 200
    except Exception:
        data = None
    upload_dir = current_app.config['UPLOAD_DIR']
    p = os.path.join(upload_dir, f"{job_id}.partial.json")
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            return jsonify(data), 200
        except Exception as e:
            return jsonify({"error": "status_read_failed", "msg": str(e)}), 500
    return jsonify({"error": "not_found"}), 404

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

@analysis_bp.get("/config")
def get_config():
    """Get application configuration including model settings"""
    return jsonify({
        "default_model": Config.DEFAULT_MODEL,
        "default_openai_model": Config.DEFAULT_OPENAI_MODEL,
        "ingredients_provider": Config.INGREDIENTS_PROVIDER,
        "google_cloud_project": Config.GOOGLE_CLOUD_PROJECT,
        "google_cloud_location": Config.GOOGLE_CLOUD_LOCATION
    }), 200

@analysis_bp.post("/analyze_text")
def analyze_text():
    """
    LLM-only analysis path (no image upload).
    Expects JSON: { "hint": "karaage curry", "context": { ...optional } }
    Returns the SAME structure as the vision pipeline.
    """
    print(f"[DEBUG] analyze_text - Content-Type: {request.content_type}")
    print(f"[DEBUG] analyze_text - Headers: {dict(request.headers)}")
    print(f"[DEBUG] analyze_text - Raw data: {request.get_data()}")
    print(f"[DEBUG] analyze_text - JSON data: {request.get_json(silent=True)}")
    print(f"[DEBUG] analyze_text - Form data: {request.form}")
    
    body = request.get_json(silent=True) or {}
    hint = body.get("hint")
    if not hint:
        print(f"[DEBUG] analyze_text - Missing hint, body: {body}")
        return jsonify({"error": "missing_hint", "msg": "JSON { 'hint': '<dish or description>' } required"}), 400

    try:
        res = run_nutrition_analysis(hint, context=body.get("context"))
        return jsonify(res), 200
    except Exception as e:
        import traceback
        print("[LLM_BREAKDOWN ERROR]", e)
        print(traceback.format_exc())
        return jsonify({"error": "nutrition_analysis_exception", "msg": str(e)}), 500
