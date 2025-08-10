import argparse, base64, io, os
from typing import List, Dict, Any, Tuple
import numpy as np
from PIL import Image

import torch
import open_clip
from transformers import BlipProcessor, BlipForConditionalGeneration

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# ---------- CLIP (always on) ----------
_CLIP_MODEL, _CLIP_PREP = open_clip.create_model_from_pretrained(
    "ViT-B-32", pretrained="laion2b_s34b_b79k"
)
_CLIP_TOK = open_clip.get_tokenizer("ViT-B-32")
_CLIP_MODEL.eval().to(DEVICE)

# ---------- BLIP (optional; load lazily if used) ----------
_BLIP = None
_BLIP_PROC = None

def load_blip():
    global _BLIP, _BLIP_PROC
    if _BLIP is None or _BLIP_PROC is None:
        _BLIP_PROC = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
        _BLIP = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base").to(DEVICE).eval()

# ---------- Label space (start simple; add more names anytime) ----------
FOOD_LABELS = [
    "pizza","ramen","tacos","sushi","hamburger","hot dog","fried rice","pancakes","waffles",
    "gyoza","dumplings","pho","pad thai","fried chicken","sandwich","burrito","steak","salad",
    "spaghetti bolognese","spaghetti carbonara","lasagna","noodle soup","curry","butter chicken",
    "french fries","onion rings","ice cream","chocolate cake","cheesecake","apple pie","donuts",
    "caprese salad","bruschetta","grilled cheese sandwich","macaroni and cheese","omelette",
    "sashimi","spring rolls","takoyaki","tiramisu","paella","ravioli","risotto", "mayo sandwich", "tuna sandwich"
]

SYN_CANON = {
    "cheese pizza": "pizza",
    "margherita pizza": "pizza",
    "pepperoni pizza": "pizza",
    "noodles": "noodle soup",
    "burger": "hamburger",
}

_TEXT_EMB = None
_LBL_CACHE = None

def _ensure_label_index(labels: List[str]):
    global _TEXT_EMB, _LBL_CACHE
    if _TEXT_EMB is not None and _LBL_CACHE == labels:
        return
    with torch.no_grad():
        tokens = _CLIP_TOK(labels)
        txt = _CLIP_MODEL.encode_text(tokens.to(DEVICE))
        txt /= txt.norm(dim=-1, keepdim=True)
    _TEXT_EMB = txt.float().cpu().numpy()
    _LBL_CACHE = labels

def _b64_image(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def _b64_to_image(b64: str) -> Image.Image:
    return Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")

def _clip_topk(image: Image.Image, labels: List[str], k: int = 5) -> Tuple[List[str], List[float]]:
    _ensure_label_index(labels)
    with torch.no_grad():
        img = _CLIP_PREP(image).unsqueeze(0).to(DEVICE)
        v = _CLIP_MODEL.encode_image(img)
        v /= v.norm(dim=-1, keepdim=True)
        v = v.float().cpu().numpy()[0]
    sims = _TEXT_EMB @ v
    idx = np.argsort(-sims)[:k]
    labs = [labels[i] for i in idx]
    s = sims[idx]
    if np.ptp(s) == 0:
        conf = np.ones_like(s) * 0.5
    else:
        conf = (s - s.min()) / (s.max() - s.min())
    return labs, conf.tolist()

def _softmax(x: np.ndarray, t: float = 1.0) -> np.ndarray:
    x = x / max(1e-9, t)
    x = x - x.max()
    e = np.exp(x)
    return e / e.sum()

def _score_by_caption(labels: List[str], caption: str) -> np.ndarray:
    cap = caption.lower()
    scores = []
    for lbl in labels:
        l = lbl.lower()
        score = 0.0
        if l in cap:
            score += 1.0
        ltoks = set(l.split())
        ctoks = set([w.strip(",.!?") for w in cap.split()])
        score += 0.15 * len(ltoks & ctoks)
        scores.append(score)
    arr = np.asarray(scores, dtype=np.float32)
    return (arr / arr.max()) if arr.max() > 0 else np.zeros_like(arr)

def _fuse(clip_labels: List[str], clip_conf: List[float], caption: str,
          w_clip: float = 0.65, w_cap: float = 0.35) -> Tuple[List[str], List[float]]:
    clip_scores = _softmax(np.asarray(clip_conf, dtype=np.float32), t=0.7)
    cap_scores = _score_by_caption(clip_labels, caption)
    fused = w_clip * clip_scores + w_cap * cap_scores
    fused = fused / max(1e-6, fused.max())
    return clip_labels, fused.tolist()

def _canonicalize(name: str) -> str:
    return SYN_CANON.get(name.lower(), name.lower())

def recognize_image(image_path: str, topk: int = 5, clip_only: bool = False) -> Dict[str, Any]:
    b64 = _b64_image(image_path)
    img = _b64_to_image(b64)

    # 1) CLIP labels
    labs, clip_conf = _clip_topk(img, FOOD_LABELS, k=topk)

    # 2) Optional caption (BLIP)
    caption = ""
    if not clip_only:
        load_blip()
        inputs = _BLIP_PROC(images=img, return_tensors="pt").to(DEVICE)
        with torch.no_grad():
            out = _BLIP.generate(**inputs, max_new_tokens=40)
        caption = _BLIP_PROC.decode(out[0], skip_special_tokens=True).strip()

    # 3) Fuse if caption present
    if caption:
        labs, conf = _fuse(labs, clip_conf, caption)
    else:
        conf = clip_conf

    # 4) Pick best
    best_idx = int(np.argmax(conf)) if conf else 0
    dish_raw = labs[best_idx] if labs else ""
    dish = _canonicalize(dish_raw)
    confidence = float(conf[best_idx]) if conf else 0.0

    return {
        "image": os.path.basename(image_path),
        "dish_guess": dish,
        "confidence": round(confidence, 4),
        "labels_topk": labs,
        "conf_topk": [float(round(c, 4)) for c in conf],
        "caption": caption
    }

def main():
    ap = argparse.ArgumentParser(description="Recognize food from an image")
    ap.add_argument("images", nargs="+", help="Path(s) to image files")
    ap.add_argument("--topk", type=int, default=5, help="Top-K labels to consider")
    ap.add_argument("--clip-only", action="store_true", help="Skip BLIP caption (no big model download)")
    args = ap.parse_args()

    for p in args.images:
        res = recognize_image(p, topk=args.topk, clip_only=args.clip_only)
        print("====", p)
        print(f"dish_guess: {res['dish_guess']}  (confidence: {res['confidence']})")
        if res["caption"]:
            print(f"caption   : {res['caption']}")
        print("topk:")
        for lbl, c in zip(res["labels_topk"], res["conf_topk"]):
            print(f"  - {lbl:24s}  {c:.3f}")

if __name__ == "__main__":
    main()
