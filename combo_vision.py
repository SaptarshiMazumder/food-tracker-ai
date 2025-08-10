# combo_vision.py
import base64, io, math
from typing import List, Dict, Any, Tuple
import numpy as np
from PIL import Image

import torch
import open_clip
from transformers import BlipProcessor, BlipForConditionalGeneration

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# ---------- Load models once ----------
_CLIP_MODEL, _CLIP_PREP = open_clip.create_model_from_pretrained(
    "ViT-B-32", pretrained="laion2b_s34b_b79k"
)
_CLIP_TOK = open_clip.get_tokenizer("ViT-B-32")
_CLIP_MODEL.eval().to(DEVICE)

_BLIP_PROC = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
_BLIP = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base").to(DEVICE).eval()

# ---------- Labels (start with Food-101; extend over time) ----------
FOOD_LABELS = [
    "apple pie","baby back ribs","baklava","beef carpaccio","beef tartare","beet salad",
    "beignets","breakfast burrito","bruschetta","caesar salad","cannoli","caprese salad",
    "carrot cake","ceviche","cheesecake","cheese plate","chicken curry","chicken quesadilla",
    "chicken wings","chocolate cake","chocolate mousse","churros","clam chowder","club sandwich",
    "crab cakes","creme brulee","croque madame","cup cakes","deviled eggs","donuts","dumplings",
    "edamame","eggs benedict","escargots","falafel","filet mignon","fish and chips","foie gras",
    "french fries","french onion soup","french toast","fried calamari","fried rice","frozen yogurt",
    "garlic bread","gnocchi","greek salad","grilled cheese sandwich","grilled salmon","guacamole",
    "gyoza","hamburger","hot and sour soup","hot dog","huevos rancheros","hummus","ice cream",
    "lasagna","lobster bisque","lobster roll sandwich","macaroni and cheese","macarons","miso soup",
    "mussels","nachos","omelette","onion rings","oysters","pad thai","paella","pancakes","panna cotta",
    "peking duck","pho","pizza","pork chop","poutine","prime rib","pulled pork sandwich","ramen","ravioli",
    "red velvet cake","risotto","samosa","sashimi","scallops","seaweed salad","shrimp and grits",
    "spaghetti bolognese","spaghetti carbonara","spring rolls","steak","strawberry shortcake","sushi",
    "tacos","takoyaki","tiramisu","tuna tartare","waffles"
]

# optional synonym → canonical
SYN_CANON = {
    "margherita pizza": "pizza",
    "cheese pizza": "pizza",
    "pepperoni pizza": "pizza",
    "carbonara": "spaghetti carbonara",
    "bolognese": "spaghetti bolognese",
}

# lightweight ingredient lexicon (fallback)
ING_LEXICON = {
    "pizza": ["tomato","mozzarella","basil","olive oil","flour","yeast"],
    "ramen": ["noodles","broth","pork","egg","nori","scallions"],
    "tacos": ["tortilla","beef","chicken","salsa","onion","cilantro","cheese"],
    "sushi": ["rice","nori","salmon","tuna","soy sauce","wasabi"],
}

_TEXT_EMB = None
_LBL_CACHE = None

def _ensure_label_index(labels: List[str]):
    global _TEXT_EMB, _LBL_CACHE
    if _TEXT_EMB is not None and _LBL_CACHE == labels:
        return
    with torch.no_grad():
        tok = _CLIP_TOK(labels)
        txt = _CLIP_MODEL.encode_text(tok.to(DEVICE))
        txt /= txt.norm(dim=-1, keepdim=True)
    _TEXT_EMB = txt.float().cpu().numpy()
    _LBL_CACHE = labels

def _b64_to_image(b64: str) -> Image.Image:
    return Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")

def _clip_topk(image: Image.Image, labels: List[str], k: int = 5) -> Tuple[List[str], List[float]]:
    _ensure_label_index(labels)
    with torch.no_grad():
        img = _CLIP_PREP(image).unsqueeze(0).to(DEVICE)
        v = _CLIP_MODEL.encode_image(img)
        v /= v.norm(dim=-1, keepdim=True)
        v = v.float().cpu().numpy()[0]
    sims = _TEXT_EMB @ v  # cosine since normalized
    idx = np.argsort(-sims)[:k]
    labs = [labels[i] for i in idx]
    # normalize to [0,1] but keep relative spacing
    s = sims[idx]
    if np.ptp(s) == 0:
        conf = np.ones_like(s) * 0.5
    else:
        conf = (s - s.min()) / (s.max() - s.min())
    return labs, conf.tolist()

def _blip_caption(image: Image.Image, max_new_tokens: int = 40) -> str:
    inputs = _BLIP_PROC(images=image, return_tensors="pt").to(DEVICE)
    with torch.no_grad():
        out = _BLIP.generate(**inputs, max_new_tokens=max_new_tokens)
    return _BLIP_PROC.decode(out[0], skip_special_tokens=True).strip()

def _softmax(x: np.ndarray, t: float = 1.0) -> np.ndarray:
    x = x / max(1e-9, t)
    x = x - x.max()
    e = np.exp(x)
    return e / e.sum()

def _score_labels_by_caption(labels: List[str], caption: str) -> np.ndarray:
    # simple semantic overlap: unigram overlap + phrase containment
    cap = caption.lower()
    scores = []
    for lbl in labels:
        l = lbl.lower()
        score = 0.0
        if l in cap:
            score += 1.0
        # token overlap
        ltoks = set(l.split())
        ctoks = set([w.strip(",.!?") for w in cap.split()])
        inter = len(ltoks & ctoks)
        score += 0.15 * inter
        scores.append(score)
    arr = np.asarray(scores, dtype=np.float32)
    if arr.max() == 0:
        return np.zeros_like(arr)
    return arr / arr.max()

def _fuse_confidences(clip_labels: List[str], clip_conf: List[float], cap: str,
                      w_clip: float = 0.65, w_cap: float = 0.35) -> Tuple[List[str], List[float]]:
    # build alignment over same ordering (clip top-k ordering)
    cap_scores = _score_labels_by_caption(clip_labels, cap)  # 0..1
    clip_scores = np.asarray(clip_conf, dtype=np.float32)
    # bring clip to softmax for nicer tails
    clip_scores = _softmax(clip_scores, t=0.7)
    fused = w_clip * clip_scores + w_cap * cap_scores
    # normalize to [0,1]
    fused = fused / max(1e-6, fused.max())
    return clip_labels, fused.tolist()

def _canonicalize(name: str) -> str:
    return SYN_CANON.get(name.lower(), name.lower())

def _guess_ingredients_from_caption(caption: str, fallback_dish: str) -> List[str]:
    # very light heuristic noun-pick; expand later
    cap = caption.lower()
    known = set(sum(ING_LEXICON.values(), []))
    found = [w for w in known if w in cap]
    if found:
        return found[:8]
    # fallback by dish lexicon
    for k, v in ING_LEXICON.items():
        if k in fallback_dish:
            return v[:8]
    return []

def vision_detect_combo(image_b64: str, labels: List[str] = FOOD_LABELS, topk: int = 5) -> Dict[str, Any]:
    """
    Returns:
    {
      dish_guess: str,
      ingredients_guess: List[str],
      labels_topk: List[str],
      conf_topk: List[float],
      caption: str,
      confidence: float   # fused confidence for dish_guess (0..1)
    }
    """
    img = _b64_to_image(image_b64)

    # 1) CLIP labels
    labs, clip_conf = _clip_topk(img, labels, k=topk)

    # 2) BLIP caption
    cap = _blip_caption(img)

    # 3) Fuse
    labs_fused, conf_fused = _fuse_confidences(labs, clip_conf, cap)

    # 4) Pick best & canonicalize
    best_idx = int(np.argmax(conf_fused)) if conf_fused else 0
    dish_raw = labs_fused[best_idx] if labs_fused else ""
    dish = _canonicalize(dish_raw)

    # 5) Ingredient guess (caption-first → lexicon fallback)
    ingredients = _guess_ingredients_from_caption(cap, dish)

    # 6) Confidence scalar for UI
    confidence = float(conf_fused[best_idx]) if conf_fused else 0.0

    return {
        "dish_guess": dish,
        "ingredients_guess": ingredients,
        "labels_topk": labs_fused,
        "conf_topk": [float(round(c, 4)) for c in conf_fused],
        "caption": cap,
        "confidence": round(confidence, 4)
    }
