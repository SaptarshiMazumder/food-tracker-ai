from typing import List, Tuple
import numpy as np
import pandas as pd
import faiss
from sentence_transformers import SentenceTransformer
from rapidfuzz import fuzz
import os

OUT_DIR = "artifacts"
META_FILE = "recipes_meta.parquet"
INDEX_FILE = "recipes.faiss"
MODEL_FILE = "embedding_model.txt"


def _norm(xs: List[str]) -> List[str]:
    out = []
    for x in xs:
        t = str(x).strip().lower()
        if not t:
            continue
        if t.endswith("es") and t[:-2] + "o" in ["tomato"]:
            t = "tomato"
        if t.endswith("s") and len(t) > 3:
            t = t[:-1]
        out.append(t)
    return sorted(set(out))


def _overlap_score(q: List[str], d: List[str]) -> float:
    qn, dn = set(_norm(q)), set(_norm(d))
    if not qn or not dn:
        return 0.0
    hits = 0.0
    for qi in qn:
        best = max([fuzz.partial_ratio(qi, dj)/100.0 for dj in dn] or [0.0])
        hits += best
    return hits / max(len(qn), len(dn))


class RecipeIndex:
    def __init__(self, out_dir: str = OUT_DIR):
        self.meta = pd.read_parquet(os.path.join(out_dir, META_FILE))
        self.index = faiss.read_index(os.path.join(out_dir, INDEX_FILE))
        with open(os.path.join(out_dir, MODEL_FILE), "r") as f:
            self.model_name = f.read().strip()
        self.embedder = SentenceTransformer(self.model_name)

    def _embed_query(self, ingredients: List[str]) -> np.ndarray:
        qtext = "ingredients: " + ", ".join(_norm(ingredients))
        v = self.embedder.encode([qtext], normalize_embeddings=True)
        return np.asarray(v, dtype="float32")

    def search(self, ingredients: List[str], k: int = 20, dedupe: bool = True) -> pd.DataFrame:
        qv = self._embed_query(ingredients)
        D, I = self.index.search(qv, k)
        cand = self.meta.iloc[I[0]].copy().reset_index(drop=True)
        cand["embed_score"] = D[0]
        cand["overlap"] = [
            _overlap_score(ingredients, row) for row in cand["ingredients"]
        ]
        cand["score"] = 0.65*cand["embed_score"] + 0.35*cand["overlap"]
        cand = cand.sort_values("score", ascending=False)
        if dedupe and "cluster_id" in cand.columns:
            cand = cand.drop_duplicates(subset=["cluster_id"])  # collapse dupes across datasets
        return cand.reset_index(drop=True)