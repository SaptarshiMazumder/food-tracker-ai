# logmeal_ingredients.py
import os
import requests
from typing import List, Dict, Any

LOGMEAL_TOKEN = os.getenv("LOGMEAL_TOKEN")  # put in .env
SEGMENT_URL = "https://api.logmeal.com/v2/image/segmentation/complete"
NUTRI_URL    = "https://api.logmeal.com/v2/recipe/nutritionalInfo"

def _auth_headers() -> Dict[str, str]:
    if not LOGMEAL_TOKEN:
        raise RuntimeError("Missing LOGMEAL_TOKEN env var")
    return {"Authorization": f"Bearer {LOGMEAL_TOKEN}"}

def _pick_image(image_paths: List[str]) -> str:
    if not image_paths:
        raise ValueError("No image paths provided")
    # LogMeal accepts one image per request (use first angle for now)
    return image_paths[0]

def _safe_get(d: Dict, *path, default=None):
    cur = d
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return default
        cur = cur[p]
    return cur

def ingredients_from_logmeal(image_paths: List[str]) -> Dict[str, Any]:
    """
    Returns:
      {
        "dish": "bread with cheese + boiled egg + yogurt + tea",
        "ingredients": ["bread with cheese", ...],  # from foodName
        "items": [{"name": "...", "grams": <serving_size>}...],
        "total_grams": <sum>,
        "confidence": None,    # LogMeal response doesn’t expose a single conf, keep None
        "notes": "LogMeal v2 nutritionalInfo per item → serving_size == grams",
        # Optionally include mapped nutrition for downstream if you want
        "nutr_items": [{"name","kcal","protein_g","carbs_g","fat_g"}...]
      }
    """
    # Check if LOGMEAL_TOKEN is available
    if not LOGMEAL_TOKEN:
        print("[logmeal] Missing LOGMEAL_TOKEN environment variable")
        return {"error": "missing_logmeal_token", "detail": "LOGMEAL_TOKEN environment variable not set"}
    
    print(f"[logmeal] Starting analysis with token: {LOGMEAL_TOKEN[:10]}...")
    img_path = _pick_image(image_paths)
    print(f"[logmeal] Using image: {img_path}")
    headers = _auth_headers()

    # Check if image file exists and is readable
    if not os.path.exists(img_path):
        return {"error": "image_file_not_found", "path": img_path}
    
    # Check file size (LogMeal might have limits)
    file_size = os.path.getsize(img_path)
    print(f"[logmeal] Image file size: {round(file_size / 1024 / 1024, 2)} MB")
    if file_size > 10 * 1024 * 1024:  # 10MB limit
        print(f"[logmeal] File too large: {round(file_size / 1024 / 1024, 2)} MB")
        return {"error": "image_file_too_large", "size_mb": round(file_size / 1024 / 1024, 2)}

    # 1) upload → imageId
    try:
        with open(img_path, "rb") as f:
            seg = requests.post(SEGMENT_URL, headers=headers, files={"image": f}, timeout=30)
        seg.raise_for_status()
        seg_json = seg.json()
        print(f"[logmeal] Segmentation response: {seg_json}")
        image_id = seg_json.get("imageId")
        if not image_id:
            print("[logmeal] No imageId in response")
            return {"error": "no_imageId", "raw": seg_json}
        print(f"[logmeal] Got imageId: {image_id}")
    except requests.exceptions.HTTPError as e:
        error_detail = f"HTTP {e.response.status_code}: {e.response.text}"
        print(f"[logmeal] API error: {error_detail}")
        return {"error": "logmeal_api_error", "detail": error_detail, "status_code": e.response.status_code}
    except requests.exceptions.RequestException as e:
        print(f"[logmeal] Network error: {str(e)}")
        return {"error": "network_error", "detail": str(e)}
    except Exception as e:
        print(f"[logmeal] Unexpected error: {str(e)}")
        return {"error": "unexpected_error", "detail": str(e)}

    # 2) nutritionalInfo → per-item portions
    try:
        nut = requests.post(NUTRI_URL, headers=headers, json={"imageId": image_id}, timeout=30)
        nut.raise_for_status()
        j = nut.json()
    except requests.exceptions.HTTPError as e:
        error_detail = f"HTTP {e.response.status_code}: {e.response.text}"
        print(f"[logmeal] Nutrition API error: {error_detail}")
        return {"error": "logmeal_nutrition_api_error", "detail": error_detail, "status_code": e.response.status_code}
    except requests.exceptions.RequestException as e:
        print(f"[logmeal] Network error: {str(e)}")
        return {"error": "network_error", "detail": str(e)}
    except Exception as e:
        print(f"[logmeal] Unexpected error: {str(e)}")
        return {"error": "unexpected_error", "detail": str(e)}

    food_names = j.get("foodName") or []
    per_item   = j.get("nutritional_info_per_item") or []
    dish = " + ".join(food_names) if food_names else ""
    items = []
    nutr_items = []

    # Map each food item → grams (use serving_size) and per-item macro summary
    total_grams = 0.0
    for idx, fi in enumerate(per_item):
        name = food_names[idx] if idx < len(food_names) else f"item_{idx+1}"
        grams = float(fi.get("serving_size") or 0.0)
        total_grams += grams
        items.append({"name": name, "grams": grams})

        tn = _safe_get(fi, "nutritional_info", "totalNutrients", default={}) or {}
        kcal = _safe_get(fi, "nutritional_info", "calories", default=0.0) or 0.0
        protein_g = float((tn.get("PROCNT") or {}).get("quantity") or 0.0)
        carbs_g   = float((tn.get("CHOCDF") or {}).get("quantity") or 0.0)
        fat_g     = float((tn.get("FAT")    or {}).get("quantity") or 0.0)
        nutr_items.append({
            "name": name,
            "kcal": float(kcal),
            "protein_g": protein_g,
            "carbs_g": carbs_g,
            "fat_g": fat_g,
        })

    return {
        "dish": dish,
        "ingredients": [str(x) for x in food_names],
        "items": items,
        "total_grams": round(total_grams, 2),
        "confidence": None,
        "notes": "LogMeal v2 nutritionalInfo per item → serving_size == grams",
        "nutr_items": nutr_items,
        "raw": j,
    }
