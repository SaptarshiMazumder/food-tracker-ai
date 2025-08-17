# run_llm_ingredients.py
import os, sys, argparse
from dotenv import load_dotenv
from graph_llm_ingredients import run_pipeline

def main():
    ap = argparse.ArgumentParser("LLM-only: ingredients (grams) → calories")
    ap.add_argument("image", help="path to image")
    ap.add_argument("--env", type=str, default=None)
    ap.add_argument("--project", type=str, default=None)
    ap.add_argument("--location", type=str, default=None)
    ap.add_argument("--model", type=str, default="gemini-2.5-pro")
    args = ap.parse_args()

    if args.env: load_dotenv(args.env)
    else: load_dotenv()

    project  = args.project or os.getenv("GOOGLE_CLOUD_PROJECT")  # optional in API-key mode
    location = args.location or os.getenv("GOOGLE_CLOUD_LOCATION","global")

    res = run_pipeline(args.image, project, location, args.model)

    if res.get("error"):
        print("\n[ERROR]", res["error"])
        if res.get("debug"):
            if res["debug"].get("rec_raw"):        print("\n[rec_raw]\n", res["debug"]["rec_raw"])
            if res["debug"].get("ingredients_raw"):print("\n[ingredients_raw]\n", res["debug"]["ingredients_raw"])
            if res["debug"].get("calories_raw"):   print("\n[calories_raw]\n", res["debug"]["calories_raw"])
        sys.exit(1)

    print("\n==== RESULTS (LLM: ingredients → calories) ====")
    print(f"dish         : {res.get('dish','')}  (conf: {res.get('gemini_conf',0.0):.2f})")
    print("ingredients  : " + (", ".join(res.get("ingredients") or []) or "(unknown)"))

    print("items (grams):")
    for it in (res.get("items") or []):
        line = f"  - {it['name']}: {it['grams']:.0f} g"
        if it.get("note"): line += f" ({it['note']})"
        print(line)

    print(f"total grams  : {res.get('total_grams',0):.0f} g (conf: {res.get('ing_conf',0.0):.2f})")

    if res.get("kcal_items"):
        print("items (kcal) :")
        for it in res["kcal_items"]:
            line = f"  - {it['name']}: {it['kcal']:.0f} kcal"
            if it.get("method"): line += f" [{it['method']}]"
            print(line)
        print(f"total kcal   : {res['total_kcal']:.0f} kcal (conf: {res.get('kcal_conf',0.0):.2f})")
        if res.get("kcal_notes"):
            print(f"notes        : {res['kcal_notes']}")
    else:
        print("calories     : (LLM calorie estimation failed)")

    print(f"overlay_path : {res.get('overlay_path')}")

if __name__ == "__main__":
    main()
