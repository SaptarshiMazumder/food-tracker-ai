import json
import pandas as pd
from datasets import load_dataset

# Codatta/MM-Food-100K adapter

def _as_list(x):
    if isinstance(x, list):
        return x
    if x is None:
        return []
    try:
        v = json.loads(x)
        return v if isinstance(v, list) else []
    except Exception:
        return []

def _as_dict(x):
    if isinstance(x, dict):
        return x
    if x is None:
        return {}
    try:
        v = json.loads(x)
        return v if isinstance(v, dict) else {}
    except Exception:
        return {}


def load(max_rows=None, split="train") -> pd.DataFrame:
    ds = load_dataset("Codatta/MM-Food-100K", split=split)
    if max_rows:
        ds = ds.select(range(min(max_rows, len(ds))))
    df = ds.to_pandas()

    rows = []
    for i, r in df.iterrows():
        rows.append({
            "id": f"mmfood_{i}",
            "dish_name": (r.get("dish_name") or "").strip(),
            "ingredients": [str(s).strip().lower() for s in _as_list(r.get("ingredients")) if str(s).strip()],
            "cooking_method": (r.get("cooking_method") or "").strip(),
            "cuisine": (r.get("food_type") or "").strip(),
            "language": "",
            "image_url": (r.get("image_url") or "").strip(),
            "source_dataset": "Codatta/MM-Food-100K",
        })
    return pd.DataFrame(rows)