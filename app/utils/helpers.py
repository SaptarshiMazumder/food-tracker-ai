import os
import re
import json
import uuid
import time
import threading
from datetime import datetime
from typing import List, Dict, Any, Generator
from werkzeug.utils import secure_filename
from flask import current_app

def fnum(x, default=0.0) -> float:
    """Convert various formats to float, with regex extraction for strings"""
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        s = x.replace(",", "").strip()
        m = re.search(r"[-+]?\d+(\.\d+)?", s)
        if m:
            try:
                return float(m.group(0))
            except Exception:
                pass
    return float(default)

def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def gather_images(request_files) -> List:
    """Gather image files from request"""
    if "images[]" in request_files:
        imgs = request_files.getlist("images[]")
    else:
        imgs = request_files.getlist("image")
    return [f for f in imgs if f and f.filename]

def save_uploads(files_in: List) -> List[str]:
    """Save uploaded files and return their paths"""
    save_paths: List[str] = []
    upload_dir = current_app.config['UPLOAD_DIR']
    
    for f in files_in:
        if not allowed_file(f.filename):
            raise ValueError(f"bad_extension:{f.filename}")
        
        ext = f.filename.rsplit(".", 1)[1].lower()
        base = secure_filename(os.path.splitext(f.filename)[0]) or "upload"
        unique = f"{base}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}.{ext}"
        path = os.path.join(upload_dir, unique)
        f.save(path)
        save_paths.append(path)
    
    return save_paths

def load_job_paths(job_id: str) -> List[str]:
    """Load job paths from job file"""
    upload_dir = current_app.config['UPLOAD_DIR']
    p = os.path.join(upload_dir, f"{job_id}.job.json")
    if not os.path.exists(p):
        return []
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("paths", [])

def save_job_manifest(job_id: str, save_paths: List[str]):
    """Save job manifest to file"""
    upload_dir = current_app.config['UPLOAD_DIR']
    manifest = {"paths": save_paths, "created_at": datetime.utcnow().isoformat()}
    with open(os.path.join(upload_dir, f"{job_id}.job.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f)

def persist_history(data: Dict[str, Any], first_path: str):
    """Persist analysis history to file"""
    upload_dir = current_app.config['UPLOAD_DIR']
    hist_path = os.path.join(upload_dir, os.path.basename(first_path) + ".json")
    with open(hist_path, "w", encoding="utf-8") as hf:
        json.dump({**data, "created_at": datetime.utcnow().isoformat()}, hf, ensure_ascii=False)

def normalize_name(name: str) -> str:
    """Normalize ingredient name for matching"""
    n = (name or "").lower().strip()
    for tag in ["(cooked)", "(fried)", "(grilled)"]:
        n = n.replace(tag, "")
    if "oil" in n:
        return "cooking oil"
    return n.strip()



# SSE (Server-Sent Events) helpers
def sse_pack(event: str, obj: Dict[str, Any]) -> str:
    """Pack data for SSE"""
    return f"event: {event}\n" + "data: " + json.dumps(obj, ensure_ascii=False) + "\n\n"

def hb_line(txt: str = "hb") -> str:
    """Create heartbeat line for SSE"""
    return f": {txt}\n\n"

def call_with_heartbeat(fn, *args, interval: float = 15.0):
    """
    Run a blocking function in a thread, yielding heartbeat comments every `interval` seconds.
    Usage inside a generator: res = yield from call_with_heartbeat(lambda: fn(...))
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
        yield hb_line("open")

        last = 0.0
        while not box["done"]:
            now = time.time()
            if now - last >= interval:
                yield hb_line()  # keepalive
                last = now
            time.sleep(0.25)

        if box["err"]:
            raise box["err"]
        return box["res"]  # captured by 'yield from'

    return _gen()
