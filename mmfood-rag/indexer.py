import os, re, json, hashlib, argparse
from typing import List
import numpy as np
import pandas as pd
import faiss
from sentence_transformers import SentenceTransformer
from adapters import ADAPTERS

OUT_DIR = "artifacts"
META_FILE = "recipes_meta.parquet"
INDEX_FILE = "recipes.faiss"
MODEL_FILE = "embedding_model.txt"
MANIFEST = "manifest.json"

EMB_MODEL_DEFAULT = "sentence-transformers/all-MiniLM-L6-v2"


def _norm_title(t: str) -> str:
    t = (t or "").lower()
    t = re.sub(r"[^a-z0-9\s-]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def make_dupe_key(dish_name: str, ingredients: List[str]) -> str:
    title = _norm_title(dish_name)
    ings = ",".join(sorted([str(x).strip().lower() for x in (ingredients or []) if str(x).strip()]))
    return f"{title}|{ings}"


def make_cluster_id(dupe_key: str) -> str:
    return hashlib.sha1(dupe_key.encode()).hexdigest()[:16]


def corpus_text(row: pd.Series) -> str:
    parts = [row.get("dish_name") or ""]
    ings = row.get("ingredients") or []
    if ings:
        parts.append("ingredients: " + ", ".join(ings))
    if row.get("cooking_method"):
        parts.append("method: " + str(row.get("cooking_method")))
    if row.get("cuisine"):
        parts.append("cuisine: " + str(row.get("cuisine")))
    if row.get("directions"):
        parts.append("directions: " + " ".join(row.get("directions")))
    parts.append("source: " + str(row.get("source_dataset") or ""))
    return " | ".join([p for p in parts if p])


def load_existing(out_dir: str):
    meta_path = os.path.join(out_dir, META_FILE)
    index_path = os.path.join(out_dir, INDEX_FILE)
    model_path = os.path.join(out_dir, MODEL_FILE)

    if not (os.path.exists(meta_path) and os.path.exists(index_path) and os.path.exists(model_path)):
        return None, None, None

    meta = pd.read_parquet(meta_path)
    index = faiss.read_index(index_path)
    with open(model_path, "r") as f:
        emb_model = f.read().strip()
    return meta, index, emb_model


def save_all(out_dir: str, meta: pd.DataFrame, index: faiss.Index, emb_model: str, manifest: dict):
    os.makedirs(out_dir, exist_ok=True)
    faiss.write_index(index, os.path.join(out_dir, INDEX_FILE))
    meta.to_parquet(os.path.join(out_dir, META_FILE))
    with open(os.path.join(out_dir, MODEL_FILE), "w") as f:
        f.write(emb_model)
    with open(os.path.join(out_dir, MANIFEST), "w") as f:
        json.dump(manifest, f, indent=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", type=str, default="mmfood,gurumurthy",
                    help="comma-separated adapter keys (see adapters/__init__.py)")
    ap.add_argument("--max_rows_per", type=int, default=150000,
                    help="dev cap per dataset; raise/remove for full builds")
    ap.add_argument("--out_dir", type=str, default=OUT_DIR)
    ap.add_argument("--emb_model", type=str, default=EMB_MODEL_DEFAULT)
    ap.add_argument("--append", action="store_true", help="append to existing index if present")
    args = ap.parse_args()

    ds_keys = [s.strip() for s in args.datasets.split(",") if s.strip()]

    # Load existing index if append mode
    existing_meta, existing_index, existing_model = load_existing(args.out_dir)

    # Validate model match for append
    if args.append and existing_model and existing_model != args.emb_model:
        raise SystemExit(f"Embedding model mismatch: existing={existing_model} new={args.emb_model}")

    # Prepare embedder & index
    model_name = existing_model or args.emb_model
    print("Loading embedding model:", model_name)
    embedder = SentenceTransformer(model_name)

    if existing_index is None:
        index = faiss.IndexFlatIP(embedder.get_sentence_embedding_dimension())
        meta = pd.DataFrame(columns=[
            "id","dish_name","ingredients","cooking_method","cuisine","language","image_url",
            "source_dataset","dupe_key","cluster_id","source_datasets","directions"
        ])
        manifest = {"datasets": {}, "vectors": 0}
    else:
        index = existing_index
        meta = existing_meta.copy()
        try:
            with open(os.path.join(args.out_dir, MANIFEST), "r") as f:
                manifest = json.load(f)
        except Exception:
            manifest = {"datasets": {}, "vectors": len(meta)}

    # Build a set for fast duplicate checks
    seen_dupes = set(meta["dupe_key"]) if len(meta) else set()
    seen_clusters = set(meta["cluster_id"]) if len(meta) else set()

    new_rows: List[pd.Series] = []

    for key in ds_keys:
        if key not in ADAPTERS:
            raise SystemExit(f"Unknown dataset key: {key}")
        print(f"Loading dataset: {key}")
        df = ADAPTERS[key](max_rows=args.max_rows_per)
        df["dupe_key"] = [make_dupe_key(r["dish_name"], r["ingredients"]) for _, r in df.iterrows()]
        df["cluster_id"] = [make_cluster_id(k) for k in df["dupe_key"]]
        df["source_datasets"] = [[r["source_dataset"]] for _, r in df.iterrows()]

        added = 0
        updated = 0
        for _, row in df.iterrows():
            dk = row["dupe_key"]
            cid = row["cluster_id"]
            if dk in seen_dupes or cid in seen_clusters:
                # update existing record's source_datasets (union)
                idxs = meta.index[meta["cluster_id"] == cid].tolist()
                if idxs:
                    i0 = idxs[0]
                    cur = set(meta.at[i0, "source_datasets"]) if isinstance(meta.at[i0, "source_datasets"], list) else set()
                    cur.add(row["source_dataset"])  # union
                    meta.at[i0, "source_datasets"] = sorted(cur)
                    updated += 1
                continue
            # new canonical row for this cluster
            new_rows.append(row)
            seen_dupes.add(dk)
            seen_clusters.add(cid)
            added += 1
        manifest["datasets"][key] = manifest["datasets"].get(key, 0) + added
        print(f"{key}: added={added}, updated_sources={updated}")

    if new_rows:
        new_meta = pd.DataFrame(new_rows)
        texts = [corpus_text(r) for _, r in new_meta.iterrows()]
        vecs = embedder.encode(texts, batch_size=512, show_progress_bar=True, normalize_embeddings=True).astype("float32")
        index.add(vecs)
        meta = pd.concat([meta, new_meta], ignore_index=True)
    else:
        print("No new vectors to add.")

    manifest["vectors"] = len(meta)
    save_all(args.out_dir, meta, index, model_name, manifest)
    print(f"Done. Total vectors: {len(meta):,}")

if __name__ == "__main__":
    main()