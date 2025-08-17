# run_llm_only.py
import os, sys, argparse
from dotenv import load_dotenv
from graph_llm_only import run_pipeline

def main():
    ap = argparse.ArgumentParser("LLM-only food grams + calories")
    ap.add_argument("image", help="path to image")
    ap.add_argument("--env", type=str, default=None)
    ap.add_argument("--project", type=str, default=None)
    ap.add_argument("--location", type=str, default=None)
    ap.add_argument("--model", type=str, default="gemini-2.5-pro")  # pro is better for structured multimodal
    args = ap.parse_args()

    if args.env: load_dotenv(args.env)
    else: load_dotenv()

    project = args.project or os.getenv("GOOGLE_CLOUD_PROJECT")  # optional in API-key mode
    location = args.location or os.getenv("GOOGLE_CLOUD_LOCATION","global")

    res = run_pipeline(args.image, project, location, args.model)

    if res.get("error"):
        print("\n[ERROR]", res["error"])
        if res.get("debug"):
            if res["debug"].get("rec_raw"):   print("\n[rec_raw]\n", res["debug"]["rec_raw"])
            if res["debug"].get("mass_raw"):  print("\n[mass_raw]\n", res["debug"]["mass_raw"])
            if res["debug"].get("nutrition_error"): print("\n[nutrition_debug]\n", res["debug"]["nutrition_error"])
        sys.exit(1)

    print("\n==== RESULTS (LLM-only) ====")
    print(f"dish         : {res.get('dish','')}  (gemini_conf: {res.get('gemini_conf',0.0):.2f})")
    print(f"ingredients  : {', '.join(res.get('ingredients') or []) or '(unknown)'}")
    print(f"grams_range  : {res['grams_low']:.0f}–{res['grams_high']:.0f} g  (llm_conf: {res.get('llm_conf',0.0):.2f})")
    if res.get("kcal_low") is not None:
        desc = res.get("picked_food_desc") or ""
        print(f"calories     : {res['kcal_low']:.0f}–{res['kcal_high']:.0f} kcal  (per 100g: {res['kcal_per_100g']:.0f}; match: {desc})")
    else:
        print("calories     : (nutrition lookup failed)")
    if (res.get('llm_notes')): print(f"notes        : {res['llm_notes']}")
    print(f"overlay_path : {res.get('overlay_path')}")

if __name__ == "__main__":
    main()
