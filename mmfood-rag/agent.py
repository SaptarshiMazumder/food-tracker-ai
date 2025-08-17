# agent.py
import os, json, math, statistics
import numpy as np
import pandas as pd
from typing import List, Tuple
from rapidfuzz import fuzz
import faiss
import json
from schema import Recipe, Ingredient

ART_DIR = "artifacts"

def _load_artifacts():
    meta = pd.read_parquet(f"{ART_DIR}/mm_food_meta.parquet")
    index = faiss.read_index(f"{ART_DIR}/mm_food.faiss")
    with open(f"{ART_DIR}/embedding_model.txt") as f:
        model_name = f.read().strip()
    # lazy import to keep start time quick
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(model_name)
    return meta, index, model

def _norm_tokens(xs: List[str]) -> List[str]:
    out = []
    for x in xs:
        t = x.strip().lower()
        if not t:
            continue
        # super-tiny normalization
        t = t.replace("bell pepper", "bell peppers").replace("chili pepper","chili")
        if t.endswith("es") and t[:-2] + "o" in ["tomato"]:  # tomato(es) case
            t = "tomato"
        if t.endswith("s") and len(t) > 3:
            t = t[:-1]
        out.append(t)
    return sorted(set(out))

def _embed(model, text: str) -> np.ndarray:
    v = model.encode([text], normalize_embeddings=True)
    return np.asarray(v, dtype="float32")

def _ingredients_text(ings: List[str]) -> str:
    return "ingredients: " + ", ".join(_norm_tokens(ings))

def _ingredient_overlap_score(query_ings: List[str], doc_ings: List[str]) -> float:
    # soft fuzzy Jaccard-ish overlap
    q = set(_norm_tokens(query_ings))
    d = set(_norm_tokens(doc_ings))
    if not q or not d:
        return 0.0
    hits = 0
    for qi in q:
        best = max([fuzz.partial_ratio(qi, dj)/100.0 for dj in d] or [0.0])
        hits += best
    return hits / max(len(q), len(d))

def retrieve(meta: pd.DataFrame, index, model, query_ings: List[str], k=12) -> pd.DataFrame:
    qtext = _ingredients_text(query_ings)
    qvec = _embed(model, qtext)
    D, I = index.search(qvec, k)  # cosine-sim on normalized (IP)
    cand = meta.iloc[I[0]].copy()
    cand["embed_score"] = D[0]
    # compute overlap bonus
    overlaps = []
    for _, r in cand.iterrows():
        overlaps.append(_ingredient_overlap_score(query_ings, r["ingredients"]))
    cand["overlap"] = overlaps
    cand["score"] = 0.75*cand["embed_score"] + 0.25*cand["overlap"]
    return cand.sort_values("score", ascending=False).reset_index(drop=True)

def synthesize_recipe(query_ings: List[str], hits: pd.DataFrame) -> Recipe:
    # Pick a dominant method from top hits
    top = hits.head(5)
    methods = [m for m in top["cooking_method"].tolist() if m]
    method = max(set(methods), key=methods.count) if methods else "stir-fry"

    # Build ingredient list: prefer items appearing across top hits + user query
    base_ings = list({_ for row in top["ingredients"] for _ in row})
    # keep only ingredients related to user query or standard aromatics
    aromatics = {"garlic","onion","ginger","salt","pepper","oil","soy sauce"}
    wanted = set(_norm_tokens(query_ings)) | (set(base_ings) & aromatics)
    ingredients = [Ingredient(name=i) for i in sorted(wanted)]

    # Nutrition estimate = mean of top-5 nutritional profiles if available
    nutri_keys = ["calories_kcal","protein_g","fat_g","carbohydrate_g"]
    estimates = {}
    for key in nutri_keys:
        vals = []
        for n in top["nutritional_profile"]:
            if isinstance(n, dict) and key in n:
                vals.append(float(n[key]))
        if vals:
            estimates[key] = round(statistics.mean(vals), 1)

    # Steps (rule-based template grounded by method + typical flow)
    steps = []
    if "boil" in method.lower():
        steps = [
            "Prep: rinse and cut veggies/proteins bite-size; mince aromatics.",
            "Boil: bring a pot to a rolling boil; salt lightly.",
            "Cook: add harder items first (e.g., potatoes), then proteins, then quick-cook veg/noodles.",
            "Season: adjust with salt/pepper/soy; finish with herbs.",
        ]
    elif "bake" in method.lower() or "roast" in method.lower():
        steps = [
            "Prep: preheat oven to 200°C. Line a tray.",
            "Season: toss ingredients with oil, salt, pepper, and spices.",
            "Bake/Roast: spread on tray and cook until browned and tender.",
            "Finish: rest 5 minutes; adjust seasoning.",
        ]
    elif "fry" in method.lower():
        steps = [
            "Prep: slice proteins/veg evenly; pat dry.",
            "Aromatics: heat pan, add oil, sauté aromatics till fragrant.",
            "Stir-fry: add proteins, then vegetables; keep heat high.",
            "Sauce: splash in soy/oyster/chili as you like; toss 30–60s.",
        ]
    else:
        steps = [
            "Prep ingredients; mince aromatics.",
            "Cook base: heat oil; sauté aromatics.",
            "Add main ingredients and cook through.",
            "Season to taste and serve.",
        ]

    refs = [f"{r['dish_name']} ({r['cooking_method']})" for _, r in top.iterrows()]
    imgs = [r for r in top["image_url"].tolist() if r]

    title = f"{method.title()} with " + ", ".join(_norm_tokens(query_ings))[:60]
    return Recipe(
        title=title,
        ingredients=ingredients,
        method=method,
        steps=steps,
        nutrition_estimate=estimates,
        references=refs,
        images=imgs[:3],
    )

def run_query(ingredients: List[str], k=12):
    meta, index, model = _load_artifacts()
    hits = retrieve(meta, index, model, ingredients, k=k)
    recipe = synthesize_recipe(ingredients, hits)
    return recipe, hits[["dish_name","ingredients","cooking_method","score"]].head(10)

if __name__ == "__main__":
    # tiny CLI
    import argparse, pprint
    ap = argparse.ArgumentParser()
    ap.add_argument("--ingredients", "-i", type=str, required=True,
                    help="Comma-separated ingredients, e.g. 'chicken, rice, onion'")
    args = ap.parse_args()
    ings = [s.strip() for s in args.ingredients.split(",") if s.strip()]
    recipe, top = run_query(ings)
    print("\n=== GROUNDED RECIPE ===")
    print(json.dumps(recipe.model_dump(), indent=2, ensure_ascii=False))
    print("\n=== TOP MATCHES ===")
    print(top.to_string(index=False))
