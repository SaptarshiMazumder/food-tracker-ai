# app.py
import os, uuid, json, re, time, threading
from datetime import datetime
from typing import List, Dict, Any, Generator
from flask import Flask, request, jsonify, render_template_string, Response
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from flask_cors import CORS

from graph_llm_ingredients import run_pipeline
from gemini_recognize import gemini_recognize_dish
from gemini_ingredients import ingredients_from_image
from gemini_calories import calories_from_ingredients

# Import RAG components
import sys
sys.path.append('./mmfood-rag')
try:
    from retriever import RecipeIndex
    from schema import DishHit, QueryResult
except ImportError:
    print("Warning: mmfood-rag components not available. RAG query functionality will be disabled.")
    RecipeIndex = None
    DishHit = None
    QueryResult = None

# --- config ---
load_dotenv()
# Also load .env from mmfood-rag directory
load_dotenv('./mmfood-rag/.env')
UPLOAD_DIR = os.path.abspath(os.getenv("UPLOAD_DIR", "./uploads"))
ALLOWED_EXT = {"jpg", "jpeg", "png", "webp"}

os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25MB per request
CORS(app)

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

def fnum(x, default=0.0) -> float:
    if isinstance(x, (int, float)): return float(x)
    if isinstance(x, str):
        s = x.replace(",", "").strip()
        m = re.search(r"[-+]?\d+(\.\d+)?", s)
        if m:
            try: return float(m.group(0))
            except Exception: pass
    return float(default)

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT

@app.get("/")
def index():
    return render_template_string(INDEX_HTML)

@app.get("/health")
def health():
    return {"ok": True}, 200

def _gather_images() -> List:
    if "images[]" in request.files:
        imgs = request.files.getlist("images[]")
    else:
        imgs = request.files.getlist("image")
    return [f for f in imgs if f and f.filename]

def _save_uploads(files_in) -> List[str]:
    save_paths: List[str] = []
    for f in files_in:
        if not allowed_file(f.filename):
            raise ValueError(f"bad_extension:{f.filename}")
        ext = f.filename.rsplit(".", 1)[1].lower()
        base = secure_filename(os.path.splitext(f.filename)[0]) or "upload"
        unique = f"{base}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}.{ext}"
        path = os.path.join(UPLOAD_DIR, unique)
        f.save(path)
        save_paths.append(path)
    return save_paths

# ------------------------------
# Classic non-streaming endpoint
# ------------------------------
@app.post("/analyze")
def analyze():
    files_in = _gather_images()
    if not files_in:
        return jsonify({"error": "missing_file", "msg": "form field 'image' or 'images[]' required"}), 400
    try:
        save_paths = _save_uploads(files_in)
    except ValueError as ve:
        return jsonify({"error": "bad_extension", "msg": str(ve)}), 400

    project  = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "global")
    model    = request.form.get("model") or request.args.get("model") or "gemini-2.5-pro"

    # Get use_logmeal parameter (default to None to use environment variable)
    use_logmeal_param = request.form.get("use_logmeal") or request.args.get("use_logmeal")
    use_logmeal = None
    if use_logmeal_param is not None:
        use_logmeal = use_logmeal_param.lower() in ("true", "1", "yes", "on")
    
    try:
        res = run_pipeline(save_paths, project, location, model, use_logmeal)
    except Exception as e:
        return jsonify({"error": "pipeline_exception", "msg": str(e)}), 500

    if res.get("error"):
        return jsonify({"error": res["error"], "dish": res.get("dish")}), 400

    data = _finalize_payload(res, save_paths)
    _persist_history(data, save_paths[0])
    print(f"[api] ⏱ total {data.get('total_ms')} ms  → timings: {data.get('timings')}")
    return jsonify(data), 200

# ------------------------------
# Streaming flow (SSE)
# 1) POST /upload  -> {job_id}
# 2) GET  /analyze_sse?job_id=...&model=...
# ------------------------------
@app.post("/upload")
def upload_only():
    files_in = _gather_images()
    if not files_in:
        return jsonify({"error": "missing_file", "msg": "form field 'image' or 'images[]' required"}), 400
    try:
        save_paths = _save_uploads(files_in)
    except ValueError as ve:
        return jsonify({"error": "bad_extension", "msg": str(ve)}), 400

    job_id = uuid.uuid4().hex
    manifest = {"paths": save_paths, "created_at": datetime.utcnow().isoformat()}
    with open(os.path.join(UPLOAD_DIR, f"{job_id}.job.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f)
    return jsonify({"job_id": job_id}), 200

def _load_job_paths(job_id: str) -> List[str]:
    p = os.path.join(UPLOAD_DIR, f"{job_id}.job.json")
    if not os.path.exists(p):
        return []
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("paths", [])

# ---------- SSE helpers (heartbeats keep Cloudflared happy) ----------
def _sse_pack(event: str, obj: Dict[str, Any]) -> str:
    return f"event: {event}\n" + "data: " + json.dumps(obj, ensure_ascii=False) + "\n\n"

def _hb_line(txt: str = "hb") -> str:
    # Comment line per SSE spec; browsers ignore, proxies keep the TCP alive.
    return f": {txt}\n\n"

def _call_with_heartbeat(fn, *args, interval: float = 15.0):
    """
    Run a blocking function in a thread, yielding heartbeat comments every `interval` seconds.
    Usage inside a generator:   res = yield from _call_with_heartbeat(lambda: fn(...))
    """
    def _gen():
        box = {"done": False, "res": None, "err": None}

        def worker():
            try:
                box["res"] = fn(*args)
            except Exception as e:
                box["err"] = e
            finally:
                box["done"] = True

        t = threading.Thread(target=worker, daemon=True)
        t.start()

        # Opening padding so intermediaries start streaming immediately
        yield _hb_line("open")

        last = 0.0
        while not box["done"]:
            now = time.time()
            if now - last >= interval:
                yield _hb_line()  # keepalive
                last = now
            time.sleep(0.25)

        if box["err"]:
            raise box["err"]
        return box["res"]  # captured by 'yield from'

    return _gen()

def _finalize_payload(res: Dict[str, Any], save_paths: List[str]) -> Dict[str, Any]:
    # normalize grams
    grams_items = []
    for it in (res.get("items") or []):
        grams_items.append({
            "name": it.get("name"),
            "grams": fnum(it.get("grams")),
            **({"note": it["note"]} if it.get("note") else {})
        })

    nutr_items = (res.get("nutr_items") or [])

    def norm_name(name: str) -> str:
        n = (name or "").lower().strip()
        for tag in ["(cooked)", "(fried)", "(grilled)"]:
            n = n.replace(tag, "")
        if "oil" in n:
            return "cooking oil"
        return n.strip()

    nutr_map = {norm_name(it.get("name", "")): it for it in nutr_items}
    ordered_nutrition = []
    for g in grams_items:
        key = norm_name(g["name"])
        ni = nutr_map.get(key, {})
        ordered_nutrition.append({
            "name": g["name"],
            "kcal": fnum(ni.get("kcal")),
            "protein_g": fnum(ni.get("protein_g")),
            "carbs_g": fnum(ni.get("carbs_g")),
            "fat_g": fnum(ni.get("fat_g")),
            **({"method": ni["method"]} if ni.get("method") else {})
        })

    # densities
    densities = []
    for g, n in zip(grams_items, ordered_nutrition):
        grams_val = g["grams"] or 0.0
        if grams_val > 0:
            densities.append({
                "name": g["name"],
                "kcal_per_g": round(n["kcal"] / grams_val, 4),
                "protein_per_g": round(n["protein_g"] / grams_val, 4),
                "carbs_per_g": round(n["carbs_g"] / grams_val, 4),
                "fat_per_g": round(n["fat_g"] / grams_val, 4),
            })
        else:
            densities.append({"name": g["name"], "kcal_per_g": 0, "protein_per_g": 0, "carbs_per_g": 0, "fat_per_g": 0})

    return {
        "dish": res.get("dish"),
        "dish_confidence": round(fnum(res.get("gemini_conf")), 2),
        "ingredients_detected": res.get("ingredients", []),

        "items_grams": grams_items,
        "total_grams": fnum(res.get("total_grams")),
        "grams_confidence": round(fnum(res.get("ing_conf")), 2),

        "items_nutrition": ordered_nutrition,
        "items_kcal": [{"name": it["name"], "kcal": fnum(it["kcal"]), **({"method": it["method"]} if it.get("method") else {})}
                       for it in ordered_nutrition],
        "items_density": densities,

        "total_kcal": fnum(res.get("total_kcal")),
        "total_protein_g": fnum(res.get("total_protein_g")),
        "total_carbs_g": fnum(res.get("total_carbs_g")),
        "total_fat_g": fnum(res.get("total_fat_g")),
        "kcal_confidence": round(fnum(res.get("kcal_conf")), 2),

        "notes": res.get("kcal_notes") or res.get("ing_notes"),
        "angles_used": len(save_paths),

        "timings": res.get("timings", {}),
        "total_ms": res.get("total_ms", 0.0),
    }

def _persist_history(data: Dict[str, Any], first_path: str):
    hist_path = os.path.join(UPLOAD_DIR, os.path.basename(first_path) + ".json")
    with open(hist_path, "w", encoding="utf-8") as hf:
        json.dump({**data, "created_at": datetime.utcnow().isoformat()}, hf, ensure_ascii=False)

@app.get("/analyze_sse")
def analyze_sse():
    """
    SSE stream: emits events 'recognize', 'ing_quant', 'calories', 'done' (and possibly 'error').
    Query: job_id, model(optional)
    """
    job_id = request.args.get("job_id", "")
    if not job_id:
        return jsonify({"error": "missing_job_id"}), 400
    image_paths = _load_job_paths(job_id)
    if not image_paths:
        return jsonify({"error": "invalid_job_id"}), 404

    project  = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "global")
    model    = request.args.get("model") or "gemini-2.5-pro"
    
    # Get use_logmeal parameter for streaming (capture it before the generator)
    use_logmeal_param = request.args.get("use_logmeal")
    use_logmeal = None
    if use_logmeal_param is not None:
        use_logmeal = use_logmeal_param.lower() in ("true", "1", "yes", "on")

    def event_stream() -> Generator[str, None, None]:
        timings: Dict[str, float] = {}
        state: Dict[str, Any] = {"timings": timings}
        t_total = time.perf_counter()

        # -------- recognize --------
        t0 = time.perf_counter()
        rec = yield from _call_with_heartbeat(
            lambda: gemini_recognize_dish(project, location, model, image_paths)
        )
        timings["recognize_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)

        if "error" in rec:
            yield _sse_pack("error", {"stage": "recognize", "msg": rec.get("error")})
            yield _sse_pack("done", {"error": "recognition_failed"})
            return

        state["dish"] = rec.get("dish","")
        state["ingredients_detected"] = [str(x) for x in (rec.get("ingredients") or [])]
        state["dish_confidence"] = round(fnum(rec.get("confidence")), 2)
        yield _sse_pack("recognize", {
            "dish": state["dish"],
            "dish_confidence": state["dish_confidence"],
            "ingredients_detected": state["ingredients_detected"],
            "timings": timings
        })

        # -------- ing_quant --------
        t0 = time.perf_counter()
        
        if use_logmeal:
            # Use LogMeal for ingredient detection
            from logmeal_ingredients import ingredients_from_logmeal
            ing = yield from _call_with_heartbeat(
                lambda: ingredients_from_logmeal(image_paths)
            )
        else:
            # Use Gemini for ingredient detection
            ing = yield from _call_with_heartbeat(
                lambda: ingredients_from_image(
                    project, location, model, image_paths,
                    dish_hint=state["dish"], ing_hint=state["ingredients_detected"]
                )
            )
        timings["ing_quant_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)

        if "error" in ing:
            yield _sse_pack("error", {"stage": "ing_quant", "msg": ing.get("error")})
            yield _sse_pack("done", {"error": "ingredients_failed"})
            return

        items_grams = []
        for it in (ing.get("items") or []):
            items_grams.append({
                "name": it.get("name"),
                "grams": fnum(it.get("grams")),
                **({"note": it["note"]} if it.get("note") else {})
            })
        state["items"] = items_grams
        state["total_grams"] = fnum(ing.get("total_grams"))
        state["grams_confidence"] = round(fnum(ing.get("confidence")), 2)
        state["ing_notes"] = ing.get("notes")

        yield _sse_pack("ing_quant", {
            "items_grams": items_grams,
            "total_grams": state["total_grams"],
            "grams_confidence": state["grams_confidence"],
            "notes": state["ing_notes"],
            "timings": timings
        })

        # -------- calories --------
        t0 = time.perf_counter()
        cal = yield from _call_with_heartbeat(
            lambda: calories_from_ingredients(project, location, model, state["dish"], state["items"])
        )
        timings["calories_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)

        if "error" in cal:
            yield _sse_pack("error", {"stage": "calories", "msg": cal.get("error")})
            yield _sse_pack("done", {"error": "calories_failed"})
            return

        # fold calories into a final payload identical to /analyze
        state.update({
            "nutr_items": cal.get("items", []),
            "total_kcal": fnum(cal.get("total_kcal")),
            "total_protein_g": fnum(cal.get("total_protein_g")),
            "total_carbs_g": fnum(cal.get("total_carbs_g")),
            "total_fat_g": fnum(cal.get("total_fat_g")),
            "kcal_conf": fnum(cal.get("confidence")),
            "kcal_notes": cal.get("notes"),
            "gemini_conf": state.get("dish_confidence", 0.0),
            "ingredients": state.get("ingredients_detected", []),
        })
        total_ms = round((time.perf_counter() - t_total) * 1000.0, 2)

        # build full API payload
        final_payload = _finalize_payload(
            {
                "dish": state["dish"],
                "ingredients": state["ingredients"],
                "gemini_conf": state.get("gemini_conf"),
                "items": state["items"],
                "total_grams": state.get("total_grams"),
                "ing_conf": state.get("grams_confidence"),
                "ing_notes": state.get("ing_notes"),
                "nutr_items": state["nutr_items"],
                "total_kcal": state["total_kcal"],
                "total_protein_g": state["total_protein_g"],
                "total_carbs_g": state["total_carbs_g"],
                "total_fat_g": state["total_fat_g"],
                "kcal_conf": state["kcal_conf"],
                "kcal_notes": state["kcal_notes"],
                "timings": timings,
                "total_ms": total_ms,
            },
            image_paths,
        )

        # emit the calories event (useful if UI wants to update before 'done')
        yield _sse_pack("calories", {
            "items_nutrition": final_payload["items_nutrition"],
            "items_kcal": final_payload["items_kcal"],
            "items_density": final_payload["items_density"],
            "total_kcal": final_payload["total_kcal"],
            "total_protein_g": final_payload["total_protein_g"],
            "total_carbs_g": final_payload["total_carbs_g"],
            "total_fat_g": final_payload["total_fat_g"],
            "kcal_confidence": final_payload["kcal_confidence"],
            "notes": final_payload.get("notes"),
            "timings": timings,
        })

        # persist + final done
        _persist_history(final_payload, image_paths[0])
        yield _sse_pack("done", final_payload)

    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",  # critical for Cloudflare/proxies
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
        "Access-Control-Allow-Origin": "*",
    }
    return Response(event_stream(), headers=headers)

@app.get("/history")
def history():
    limit = int(request.args.get("limit", 20))
    files = [f for f in os.listdir(UPLOAD_DIR) if f.lower().endswith(".json")]
    files.sort(reverse=True)
    items = []
    for fname in files[:limit]:
        try:
            with open(os.path.join(UPLOAD_DIR, fname), "r", encoding="utf-8") as f:
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

# ------------------------------
# RAG Query endpoint
# ------------------------------
@app.get("/query")
def query():
    if RecipeIndex is None:
        return jsonify({"error": "rag_not_available", "msg": "RAG components not available"}), 503
    
    ingredients = request.args.get("i", "")
    top = int(request.args.get("top", 5))
    mode = request.args.get("mode", "flexible")  # Default to flexible mode
    
    if not ingredients:
        return jsonify({"error": "missing_ingredients", "msg": "parameter 'i' required"}), 400
    
    try:
        # Parse ingredients
        ings = [s.strip() for s in ingredients.split(",") if s.strip()]
        
        # Initialize recipe index with correct path
        idx = RecipeIndex(out_dir="./mmfood-rag/artifacts")
        df = idx.search(ings, k=max(25, top*5), dedupe=True).head(top)
        
        # Build hits with additional deduplication
        hits = []
        seen_dish_names = set()
        
        for _, r in df.iterrows():
            dish_name = r.get("dish_name", "").strip().lower()
            
            # Skip if we've already seen this dish name (case-insensitive deduplication)
            if dish_name in seen_dish_names:
                continue
                
            seen_dish_names.add(dish_name)
            
            hits.append(DishHit(
                dish_name=r.get("dish_name", ""),
                ingredients=list(r.get("ingredients", [])),
                cooking_method=str(r.get("cooking_method", "")),
                cuisine=str(r.get("cuisine", "")),
                image_url=str(r.get("image_url", "")),
                source_datasets=list(r.get("source_datasets", [])),
                cluster_id=str(r.get("cluster_id", "")),
                score=float(r.get("score", 0.0)),
                directions=list(r.get("directions", [])),  # Add directions
            ))
        
        # Get Google search sources for each dish (only in flexible mode)
        sources = {}
        if mode == "flexible":
            try:
                from source_finder import SourceFinder
                from recipe_extractor import RecipeExtractor
                
                # Check if required environment variables are set
                google_api_key = os.getenv("GOOGLE_API_KEY")
                google_cse_id = os.getenv("GOOGLE_CSE_ID")
                
                if not google_api_key or not google_cse_id:
                    print("Warning: Google API keys not configured. Enhanced recipe extraction disabled.")
                    print("To enable enhanced recipe extraction, set GOOGLE_API_KEY and GOOGLE_CSE_ID environment variables.")
                    sources = {h.dish_name: [] for h in hits}
                else:
                    sf = SourceFinder()
                    re = RecipeExtractor()
                    
                    for h in hits:
                        try:
                            # Use enhanced search with fallback (reduced to 2 sources for speed)
                            srcs = sf.search_with_fallback(h.dish_name, h.ingredients, num=2)
                            
                            # Process sources with recipe extractor
                            enhanced_srcs = re.process_recipe_sources(srcs, h.dish_name, h.ingredients)
                            
                            sources[h.dish_name] = [{
                                "title": s.get("title", ""), 
                                "link": s.get("link", ""), 
                                "snippet": s.get("snippet", ""), 
                                "displayLink": s.get("displayLink", ""),
                                "directions": s.get("directions", []),
                                "content_preview": s.get("content_preview", ""),
                                "extraction_method": s.get("extraction_method", ""),
                                "recipe_info": s.get("recipe_info", {})
                            } for s in enhanced_srcs]
                            
                        except Exception as e:
                            print(f"Warning: Failed to get sources for {h.dish_name}: {e}")
                            sources[h.dish_name] = []
            except Exception as e:
                print(f"Warning: SourceFinder or RecipeExtractor not available: {e}")
                sources = {h.dish_name: [] for h in hits}
        else:
            # In strict mode, initialize empty sources
            sources = {h.dish_name: [] for h in hits}
        
        # Return response in the format frontend expects
        return jsonify({
            "query_ingredients": ings,
            "hits": [hit.model_dump() for hit in hits],
            "sources": sources
        })
        
    except Exception as e:
        return jsonify({"error": "query_failed", "msg": str(e)}), 500

# ------------------------------
# Recipe Details endpoint (for strict mode)
# ------------------------------
@app.get("/recipe_details")
def recipe_details():
    if RecipeIndex is None:
        return jsonify({"error": "rag_not_available", "msg": "RAG components not available"}), 503
    
    dish_name = request.args.get("dish_name", "")
    ingredients = request.args.get("ingredients", "")
    
    if not dish_name:
        return jsonify({"error": "missing_dish_name", "msg": "parameter 'dish_name' required"}), 400
    
    try:
        # Parse ingredients
        ings = [s.strip() for s in ingredients.split(",") if s.strip()] if ingredients else []
        
        # Get Google search sources for the specific dish
        sources = []
        try:
            from source_finder import SourceFinder
            from recipe_extractor import RecipeExtractor
            
            # Check if required environment variables are set
            google_api_key = os.getenv("GOOGLE_API_KEY")
            google_cse_id = os.getenv("GOOGLE_CSE_ID")
            
            if google_api_key and google_cse_id:
                sf = SourceFinder()
                re = RecipeExtractor()
                
                # Use enhanced search with fallback
                srcs = sf.search_with_fallback(dish_name, ings, num=3)
                
                # Process sources with recipe extractor
                enhanced_srcs = re.process_recipe_sources(srcs, dish_name, ings)
                
                sources = [{
                    "title": s.get("title", ""), 
                    "link": s.get("link", ""), 
                    "snippet": s.get("snippet", ""), 
                    "displayLink": s.get("displayLink", ""),
                    "directions": s.get("directions", []),
                    "content_preview": s.get("content_preview", ""),
                    "extraction_method": s.get("extraction_method", ""),
                    "recipe_info": s.get("recipe_info", {})
                } for s in enhanced_srcs]
                
        except Exception as e:
            print(f"Warning: Failed to get sources for {dish_name}: {e}")
        
        return jsonify({
            "dish_name": dish_name,
            "ingredients": ings,
            "sources": sources
        })
        
    except Exception as e:
        return jsonify({"error": "details_failed", "msg": str(e)}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True, threaded=True)
