# vision.py
import os, math
from typing import Optional, Tuple, Dict, Any, List
import numpy as np
import cv2
from PIL import Image
import torch
import open_clip
from ultralytics import YOLO

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# ---------- IO ----------
def imread_bgr(path: str):
    data = np.fromfile(path, dtype=np.uint8)  # windows/Unicode-safe
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None: raise RuntimeError(f"Failed to read image: {path}")
    return img

# ---------- CLIP (mask ranking) ----------
_CLIP_MODEL, _CLIP_PREP = open_clip.create_model_from_pretrained("ViT-B-32", pretrained="laion2b_s34b_b79k")
_CLIP_TOK = open_clip.get_tokenizer("ViT-B-32")
_CLIP_MODEL.eval().to(DEVICE)
_CLIP_TEXT_CACHE: Dict[str, torch.Tensor] = {}

def clip_score_mask(img_bgr: np.ndarray, mask_bin: np.ndarray, text: str) -> float:
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    bg = np.ones_like(rgb) * 255
    m3 = np.repeat(mask_bin[:, :, None], 3, axis=2).astype(np.uint8)
    comp = np.where(m3 == 1, rgb, bg)
    ys, xs = np.where(mask_bin == 1)
    if len(xs)==0 or len(ys)==0: return 0.0
    x1, x2, y1, y2 = xs.min(), xs.max(), ys.min(), ys.max()
    crop = Image.fromarray(comp[y1:y2+1, x1:x2+1])
    with torch.no_grad():
        img_in = _CLIP_PREP(crop).unsqueeze(0).to(DEVICE)
        v_img = _CLIP_MODEL.encode_image(img_in)
        v_img /= v_img.norm(dim=-1, keepdim=True)
        key = text.strip().lower()
        if key not in _CLIP_TEXT_CACHE:
            toks = _CLIP_TOK([key])
            v_txt = _CLIP_MODEL.encode_text(toks.to(DEVICE))
            v_txt /= v_txt.norm(dim=-1, keepdim=True)
            _CLIP_TEXT_CACHE[key] = v_txt
        v_txt = _CLIP_TEXT_CACHE[key]
        sim = (100.0 * v_img @ v_txt.T).softmax(dim=-1).cpu().numpy()[0,0]
    return float(sim)

# ---------- YOLO + geometry ----------
REF_CLASSES = {"fork","knife","spoon","bottle","wine glass","cup"}
CONTAINER_CLASSES = {"bowl","cup","wine glass","bottle"}  # plate not in COCO

def mask_to_contour(mask_bin: np.ndarray):
    cnts, _ = cv2.findContours((mask_bin*255).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts: return None
    return max(cnts, key=cv2.contourArea)

def contour_major_axis_len(cnt) -> float:
    rect = cv2.minAreaRect(cnt)
    (w,h) = rect[1]
    return float(max(w,h))

def yolo_predict(img_bgr):
    model = YOLO("yolov8s-seg.pt")  # auto-download once
    return model.predict(img_bgr, verbose=False)

def find_fork_scale(yres, class_names, fork_cm: float, H: int, W: int):
    r = yres[0]
    if r.masks is None: return None, None, None
    best = (0.0, None)
    for i, ci in enumerate(r.boxes.cls.cpu().numpy().astype(int).tolist()):
        if class_names[ci].lower() != "fork": continue
        mk_small = r.masks.data[i].cpu().numpy()
        mk = (mk_small > 0.5).astype(np.uint8)
        mk = cv2.resize(mk, (W, H), interpolation=cv2.INTER_NEAREST)
        cnt = mask_to_contour(mk)
        if cnt is None: continue
        px = contour_major_axis_len(cnt)
        if px > best[0]: best = (px, cnt)
    if best[1] is None or best[0] <= 1: return None, None, None
    cm_per_px = float(fork_cm) / float(best[0])
    return cm_per_px, best[1], float(best[0])

def pick_food_mask(yres, class_names, img_bgr, dish_text: Optional[str], fork_mask: Optional[np.ndarray]):
    r = yres[0]
    if r.masks is None: return None
    masks_small = r.masks.data.cpu().numpy()
    classes = r.boxes.cls.cpu().numpy().astype(int).tolist()
    confs = r.boxes.conf.cpu().numpy().tolist()
    H,W = img_bgr.shape[:2]
    reject = fork_mask.astype(np.uint8) if fork_mask is not None else None
    best = (-1.0, None)
    for mk_small, ci, cf in zip(masks_small, classes, confs):
        name = class_names[ci].lower()
        if name in REF_CLASSES: continue
        mk = (mk_small > 0.5).astype(np.uint8)
        mk = cv2.resize(mk, (W, H), interpolation=cv2.INTER_NEAREST)
        area = int(mk.sum())
        if area < 500: continue
        if reject is not None:
            inter = int((mk & reject).sum())
            if inter / max(1, area) > 0.15: continue
        s = clip_score_mask(img_bgr, mk, f"a photo of {dish_text}") if dish_text else math.log(area+1)*(0.5+0.5*cf)
        if s > best[0]: best = (s, mk)
    return best[1]

def detect_container_coverage(yres, class_names, img_bgr, food_mask):
    r = yres[0]
    if r.masks is None or food_mask is None: return None
    H,W = img_bgr.shape[:2]
    masks_small = r.masks.data.cpu().numpy()
    classes = r.boxes.cls.cpu().numpy().astype(int).tolist()
    best = None
    for mk_small, ci in zip(masks_small, classes):
        name = class_names[ci].lower()
        if name not in CONTAINER_CLASSES: continue
        mk = (mk_small > 0.5).astype(np.uint8)
        mk = cv2.resize(mk, (W, H), interpolation=cv2.INTER_NEAREST)
        cont_area = int(mk.sum())
        if cont_area < 500: continue
        inter = int((mk & food_mask).sum())
        cov = inter / max(1, cont_area)
        if (best is None) or (cov > best["coverage_ratio"]):
            best = {"container": name, "coverage_ratio": float(cov), "container_area_px": cont_area}
    return best

def save_overlay(img_path, base_bgr, fork_contour=None, food_mask=None, scale=None, area_cm2=None, grams=None):
    ov = base_bgr.copy()
    if fork_contour is not None:
        cv2.drawContours(ov, [fork_contour], -1, (0,200,255), 2)
    if food_mask is not None:
        cnts,_ = cv2.findContours((food_mask*255).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(ov, cnts, -1, (0,255,0), 2)
    lines = []
    if scale is not None: lines.append(f"scale: {scale:.4f} cm/px")
    if area_cm2 is not None: lines.append(f"area: {area_cm2:.1f} cm^2")
    if grams is not None: lines.append(f"mass: {grams['low']:.0f}-{grams['high']:.0f} g")
    if lines:
        w = max(380, 10*max(len(x) for x in lines))
        cv2.rectangle(ov, (10,10), (10+w, 10+30+22*len(lines)), (255,255,255), -1)
        y=35
        for t in lines:
            cv2.putText(ov, t, (20,y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (20,20,20), 2, cv2.LINE_AA)
            y+=22
    out = os.path.splitext(img_path)[0] + "_overlay.jpg"
    cv2.imencode(".jpg", ov)[1].tofile(out)
    return out
