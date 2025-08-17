# build_index.py
import os, json, math
from datasets import load_dataset
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
import faiss

DATASET_NAME = "Codatta/MM-Food-100K"   # public on Hugging Face
OUT_DIR = "artifacts"
EMB_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # 384-dim, fast & small

os.makedirs(OUT_DIR, exist_ok=True)

def _as_list(x):
    if isinstance(x, list): 
        return x
    if x is None: 
        return []
    try:
        v = json.loads(x)
        return v if isinstance(v, list) else [str(v)]
    except Exception:
        return [str(x)] if str(x).strip() else []

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

def load_mm_food(split="train"):
    # If your environment needs auth, run: `huggingface-cli login`
    ds = load_dataset(DATASET_NAME, split=split)  # 100k rows
    # Convert to pandas for convenience
    df = ds.to_pandas()
    # Normalize columns we care about
    norm_rows = []
    for i, r in df.iterrows():
        dish = (r.get("dish_name") or "").strip()
        ingredients = _as_list(r.get("ingredients"))
        method = (r.get("cooking_method") or "").strip()
        portions = _as_list(r.get("portion_size"))
        nutrition = _as_dict(r.get("nutritional_profile"))
        img = (r.get("image_url") or "").strip()
        food_type = (r.get("food_type") or "").strip()

        norm_rows.append({
            "id": i,
            "dish_name": dish,
            "ingredients": [s.strip().lower() for s in ingredients],
            "cooking_method": method,
            "portion_size": portions,
            "nutritional_profile": nutrition,
            "food_type": food_type,
            "image_url": img,
        })
    return pd.DataFrame(norm_rows)

def make_corpus_row(row):
    # Text used for embedding-based retrieval
    ing = ", ".join(row["ingredients"])
    portions = ", ".join(row["portion_size"])
    nutr = row["nutritional_profile"]
    nutr_txt = ", ".join([f"{k}:{v}" for k, v in nutr.items()]) if nutr else ""
    parts = [
        row["dish_name"],
        f"ingredients: {ing}" if ing else "",
        f"method: {row['cooking_method']}" if row["cooking_method"] else "",
        f"portions: {portions}" if portions else "",
        f"nutrition: {nutr_txt}" if nutr_txt else "",
        f"type: {row['food_type']}" if row["food_type"] else "",
    ]
    return " | ".join([p for p in parts if p])

def main():
    print("Loading dataset…")
    df = load_mm_food()

    print("Preparing corpus texts…")
    texts = [make_corpus_row(r) for _, r in df.iterrows()]

    print("Loading embedding model:", EMB_MODEL)
    model = SentenceTransformer(EMB_MODEL)
    emb = model.encode(texts, batch_size=512, show_progress_bar=True, normalize_embeddings=True)
    emb = np.asarray(emb).astype("float32")  # shape: (N, 384)

    print("Building FAISS index (IP on normalized vectors)…")
    index = faiss.IndexFlatIP(emb.shape[1])
    index.add(emb)

    # Persist
    faiss.write_index(index, os.path.join(OUT_DIR, "mm_food.faiss"))
    df.to_parquet(os.path.join(OUT_DIR, "mm_food_meta.parquet"))
    with open(os.path.join(OUT_DIR, "embedding_model.txt"), "w") as f:
        f.write(EMB_MODEL)

    print("Done. Artifacts in:", OUT_DIR)

if __name__ == "__main__":
    main()
