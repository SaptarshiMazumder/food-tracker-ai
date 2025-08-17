# vision_portion.py
"""
Lightweight vision cues for portion estimation.
- Detect a utensil (fork/spoon/knife) with YOLOv8n (COCO) to infer mm/px scale.
- Compute simple color cluster areas to hint relative volumes.
- (Optional) Monocular depth if explicitly enabled via env.
Returns cues for the LLM and a small status payload for the UI.
"""

from __future__ import annotations
import os, math
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple

import numpy as np
import cv2

# ---------- Feature flags via env (all optional) ----------
_USE_YOLO  = os.getenv("VISION_ENABLE_YOLO",  "1") == "1"
_USE_DEPTH = os.getenv("VISION_ENABLE_DEPTH", "0") == "1"  # default OFF for fast startup
_DEPTH_MODEL_ID = os.getenv("DEPTH_MODEL_ID", "LiheYoung/depth-anything-v2-large")

# ---------- Optional deps (loaded only if enabled) ----------
_HAVE_YOLO = False
_YOLO = None
if _USE_YOLO:
    try:
        from ultralytics import YOLO  # pip install ultralytics
        _HAVE_YOLO = True
    except Exception:
        _HAVE_YOLO = False

_HAVE_DEPTH = False
_DEPTH_PIPE = None
if _USE_DEPTH:
    try:
        from transformers import AutoImageProcessor, AutoModelForDepthEstimation
        import torch  # noqa: F401  (used inside depth prediction)
        _HAVE_DEPTH = True
    except Exception:
        _HAVE_DEPTH = False

# ---------- Constants ----------
UTENSIL_PRIOR_MM = {
    "fork": 185.0,     # typical table fork length in mm
    "spoon": 170.0,    # typical tablespoon length in mm
    "knife": 210.0,    # table knife
}
UTENSIL_CLASSES = {"fork", "spoon", "knife"}

# ---------- Utils ----------
def _read_bgr(path: str) -> np.ndarray:
    img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise RuntimeError(f"Could not read image: {path}")
    return img

def _load_yolo():
    if not _HAVE_YOLO:
        return None
    global _YOLO
    if _YOLO is None:
        _YOLO = YOLO("yolov8n.pt")  # downloads on first run if not cached
    return _YOLO

@dataclass
class UtensilDet:
    label: str
    conf: float
    box_xyxy: Tuple[float, float, float, float]
    mm_per_px: Optional[float]
    _score: tuple = (0, 0.0)  # internal tie-break

def _detect_utensil_mm_per_px(bgr: np.ndarray) -> Optional[UtensilDet]:
    m = _load_yolo()
    if m is None:
        return None
    res = m.predict(bgr, verbose=False, conf=0.2, iou=0.45, imgsz=640)
    if not res:
        return None
    names = m.model.names if hasattr(m, "model") else getattr(m, "names", {})
    best: Optional[UtensilDet] = None
    for r in res:
        if not getattr(r, "boxes", None):
            continue
        for b in r.boxes:
            cls_idx = int(b.cls.item())
            label = str(names.get(cls_idx, cls_idx)).lower()
            if label not in UTENSIL_CLASSES:
                continue
            conf = float(b.conf.item())
            x1, y1, x2, y2 = b.xyxy[0].cpu().numpy().tolist()
            px_len = max(x2 - x1, y2 - y1)
            prior_mm = UTENSIL_PRIOR_MM.get(label)
            mm_per_px = (prior_mm / px_len) if (prior_mm and px_len > 1) else None
            det = UtensilDet(label=label, conf=conf, box_xyxy=(x1, y1, x2, y2), mm_per_px=mm_per_px)
            score = ({"fork": 3, "spoon": 2, "knife": 1}.get(label, 0), conf)
            det._score = score
            if best is None or score > best._score:
                best = det
    return best

def _kmeans_area_fractions(bgr: np.ndarray, k: int = 4) -> List[Dict[str, Any]]:
    """Cheap, fast color k-means to capture big regions."""
    h, w = bgr.shape[:2]
    target_w = min(480, w)
    small = cv2.resize(bgr, (target_w, int(h * target_w / w)), interpolation=cv2.INTER_AREA)
    z = small.reshape((-1, 3)).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
    K = max(2, min(k, 8))
    _ret, labels, centers = cv2.kmeans(z, K, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
    labels = labels.reshape((small.shape[0], small.shape[1]))
    out = []
    total = labels.size
    for i in range(K):
        count = int((labels == i).sum())
        frac = count / float(total)
        center = centers[i].tolist()
        out.append({"cluster": int(i), "area_frac": round(frac, 4), "avg_bgr": [round(x, 1) for x in center]})
    out.sort(key=lambda x: x["area_frac"], reverse=True)
    return out

def _load_depth():
    if not _HAVE_DEPTH:
        return None
    global _DEPTH_PIPE
    if _DEPTH_PIPE is not None:
        return _DEPTH_PIPE
    try:
        from transformers import AutoImageProcessor, AutoModelForDepthEstimation
        processor = AutoImageProcessor.from_pretrained(_DEPTH_MODEL_ID)
        model = AutoModelForDepthEstimation.from_pretrained(_DEPTH_MODEL_ID)
        _DEPTH_PIPE = (processor, model)
        return _DEPTH_PIPE
    except Exception:
        return None

def _predict_depth(bgr: np.ndarray) -> Optional[np.ndarray]:
    pipe = _load_depth()
    if pipe is None:
        return None
    processor, model = pipe
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    inputs = processor(images=rgb, return_tensors="pt")
    with torch.no_grad():  # type: ignore[name-defined]
        outputs = model(**inputs)
        depth = outputs.predicted_depth.squeeze().cpu().numpy()
    dmin, dmax = np.percentile(depth, (1, 99))
    depth = np.clip((depth - dmin) / (dmax - dmin + 1e-6), 0, 1)
    return depth

# ---------- Public API ----------
def analyze_angles(
    image_paths: List[str],
    dish_hint: Optional[str] = None,
    ingredients_hint: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Aggregates vision cues across angles.
    Returns:
    {
      "confidence": 0.55,
      "mm_per_px": 0.32 | null,
      "views": [
        {"path":"...", "utensil": {...} | null, "clusters":[...], "depth_used": false}
      ],
      "notes": "…"
    }
    """
    views = []
    mm_vals = []
    used_depth = False
    notes: List[str] = []

    for p in image_paths:
        bgr = _read_bgr(p)

        utensil = _detect_utensil_mm_per_px(bgr) if _USE_YOLO else None
        if utensil and utensil.mm_per_px:
            mm_vals.append(float(utensil.mm_per_px))

        clusters = _kmeans_area_fractions(bgr, k=4)

        depthmap = _predict_depth(bgr) if _USE_DEPTH else None
        used_depth = used_depth or (depthmap is not None)

        view = {
            "path": os.path.basename(p),
            "utensil": utensil.__dict__ if utensil else None,
            "clusters": clusters,
            "depth_used": bool(depthmap is not None),
        }
        views.append(view)

    mm_per_px = float(np.median(mm_vals)) if mm_vals else None
    if mm_per_px is None:
        notes.append("No utensil scale found; using relative areas only.")
    else:
        notes.append(f"Estimated scale ~ {mm_per_px:.3f} mm/px from utensil.")

    # simple confidence heuristic
    conf = 0.4 + 0.2 * min(1.0, len(mm_vals)) + (0.1 if used_depth else 0.0)
    conf = min(0.95, conf)

    return {
        "confidence": round(conf, 2),
        "mm_per_px": mm_per_px,
        "views": views,
        "notes": "; ".join(notes),
    }
