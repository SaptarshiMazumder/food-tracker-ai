import argparse, json
from retriever import RecipeIndex
from source_finder import SourceFinder
from recipe_extractor import RecipeExtractor
from schema import DishHit, WebSource, QueryResult


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ingredients", "-i", type=str, required=True,
                    help="comma-separated ingredients e.g. 'chicken, rice, onion, garlic'")
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--extract_recipes", action="store_true", 
                    help="extract recipe content from websites")
    args = ap.parse_args()

    ings = [s.strip() for s in args.ingredients.split(",") if s.strip()]

    idx = RecipeIndex()
    df = idx.search(ings, k=max(25, args.top*5), dedupe=True).head(args.top)

    hits = []
    for _, r in df.iterrows():
        hits.append(DishHit(
            dish_name=r.get("dish_name", ""),
            ingredients=list(r.get("ingredients", [])),
            cooking_method=str(r.get("cooking_method", "")),
            cuisine=str(r.get("cuisine", "")),
            image_url=str(r.get("image_url", "")),
            source_datasets=list(r.get("source_datasets", [])),
            cluster_id=str(r.get("cluster_id", "")),
            score=float(r.get("score", 0.0)),
            directions=list(r.get("directions", [])),  # Add directions
        ))

    # find trustworthy web sources per dish
    sf = SourceFinder()
    re = RecipeExtractor() if args.extract_recipes else None
    sources = {}
    
    for h in hits:
        try:
            srcs = sf.search(h.dish_name, h.ingredients, num=5)
            
            # Process sources with recipe extractor if enabled
            if re and args.extract_recipes:
                enhanced_srcs = re.process_recipe_sources(srcs, h.dish_name, h.ingredients)
                sources[h.dish_name] = [WebSource(**s) for s in enhanced_srcs]
            else:
                sources[h.dish_name] = [WebSource(**s) for s in srcs]
                
        except Exception as e:
            print(f"Warning: Failed to get sources for {h.dish_name}: {e}")
            sources[h.dish_name] = []

    result = QueryResult(query_ingredients=ings, hits=hits, sources=sources)
    print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()