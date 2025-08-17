import re, ast
import pandas as pd
from datasets import load_dataset

UNITS = r"(cups?|c\\.?|tbsp\\.?|tablespoons?|tsp\\.?|teaspoons?|oz|ounce?s?|lb?s?|pounds?|g|kg|ml|l|lit(er|re)s?)"


def _parse_list(s):
    if isinstance(s, list):
        return s
    if s is None:
        return []
    s = str(s)
    try:
        v = ast.literal_eval(s)
        if isinstance(v, list):
            return v
    except Exception:
        pass
    # fallback: split on commas/bullets
    return [x.strip() for x in re.split(r"\s*[-•]\s+|,\s*", s) if x.strip()]


def _clean_item(x: str) -> str:
    x = re.sub(r"\(.*?\)", "", str(x))                    # drop parentheses
    x = re.sub(r"\d+[\d/\.]*\s*(%s)?" % UNITS, "", x, flags=re.I)  # drop qty+unit
    x = re.sub(r"[^a-zA-Z\s-]", " ", x)
    x = re.sub(r"\s+", " ", x).strip().lower()
    if x.endswith("es") and x[:-2] + "o" in ["tomato"]:
        x = "tomato"
    if x.endswith("s") and len(x) > 3:
        x = x[:-1]
    return x

METHOD_HINTS = [
    ("bake", ["bake", "preheat oven", "oven"]),
    ("roast", ["roast"]),
    ("fry", ["fry", "stir fry", "stir-fry", "saute", "sauté", "pan fry"]),
    ("boil", ["boil", "parboil"]),
    ("simmer", ["simmer", "stew", "braise"]),
    ("grill", ["grill", "broil"]),
    ("steam", ["steam"]),
]


def _infer_method(steps):
    text = " ".join([str(s) for s in steps]).lower()
    for name, keys in METHOD_HINTS:
        if any(k in text for k in keys):
            return name
    return ""


def load(max_rows=None, split="train") -> pd.DataFrame:
    ds = load_dataset("gurumurthy3/cooking-recipe", split=split)
    if max_rows:
        ds = ds.select(range(min(max_rows, len(ds))))
    df = ds.to_pandas()

    rows = []
    for i, r in df.iterrows():
        title = (r.get("title") or "").strip()
        ingredients = [_clean_item(s) for s in _parse_list(r.get("ingredients"))]
        ingredients = sorted({s for s in ingredients if s})
        directions = _parse_list(r.get("directions"))

        rows.append({
            "id": f"gurumurthy_{i}",
            "dish_name": title,
            "ingredients": ingredients,
            "cooking_method": _infer_method(directions),
            "cuisine": "",
            "language": "",
            "image_url": "",
            "source_dataset": "gurumurthy3/cooking-recipe",
            "directions": directions,  # Add directions to the output
        })
    return pd.DataFrame(rows)