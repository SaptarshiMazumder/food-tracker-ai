# gemini_ping.py
import os, base64, argparse
from dotenv import load_dotenv
from google import genai
from google.genai import types

def make_client(project: str | None, location: str):
    """
    Prefers Vertex (ADC) when project is set; falls back to API key if available.
    Environment variables are loaded via dotenv in main().
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if project:
        try:
            print(f"[auth] Using Vertex (project={project}, location={location})")
            return genai.Client(vertexai=True, project=project, location=location)
        except Exception as e:
            if api_key:
                print("[auth] Vertex ADC failed; falling back to API key mode.")
                return genai.Client(api_key=api_key)
            raise
    if not api_key:
        raise RuntimeError("No auth found. Set GOOGLE_CLOUD_PROJECT (Vertex) or GOOGLE_API_KEY in .env.")
    print("[auth] Using API key mode")
    return genai.Client(api_key=api_key)

def extract_text(resp) -> str:
    # pull text from candidates; also handle inline_data payloads
    try:
        for cand in (getattr(resp, "candidates", []) or []):
            content = getattr(cand, "content", None)
            if not content: continue
            for part in (getattr(content, "parts", []) or []):
                t = getattr(part, "text", None)
                if isinstance(t, str) and t.strip():
                    return t
                inline = getattr(part, "inline_data", None)
                if inline:
                    data = getattr(inline, "data", None)
                    if isinstance(data, (bytes, bytearray)):
                        return data.decode("utf-8", "ignore")
                    if isinstance(data, str):
                        try:
                            return base64.b64decode(data).decode("utf-8", "ignore")
                        except Exception:
                            return data
        top = getattr(resp, "text", None)
        return top if isinstance(top, str) else ""
    except Exception:
        return ""

def main():
    ap = argparse.ArgumentParser("Quick Gemini ping (dotenv)")
    ap.add_argument("--env", type=str, default=None, help="path to .env (defaults to ./.env)")
    ap.add_argument("--project", type=str, default=None, help="override GOOGLE_CLOUD_PROJECT from .env")
    ap.add_argument("--location", type=str, default=None, help="override GOOGLE_CLOUD_LOCATION from .env")
    ap.add_argument("--model", type=str, default="gemini-2.5-flash")
    ap.add_argument("--ask", type=str,
        default="Give me Triple H's pro wrestling stats (real name, billed height, billed weight, signature finisher). Keep it brief.")
    args = ap.parse_args()

    # load .env (inside your venv/project)
    if args.env:
        load_dotenv(args.env)
    else:
        load_dotenv()  # loads ./.env if present

    project  = args.project  or os.getenv("GOOGLE_CLOUD_PROJECT")
    location = args.location or os.getenv("GOOGLE_CLOUD_LOCATION", "global")

    client = make_client(project, location)
    resp = client.models.generate_content(
        model=args.model,
        contents=[types.Content(role="user", parts=[types.Part.from_text(text=args.ask)])],
        config=types.GenerateContentConfig(temperature=0.2, max_output_tokens=256)
    )
    text = extract_text(resp)

    print("\n=== GEMINI RESPONSE ===\n")
    print(text if text else "(empty response)")

if __name__ == "__main__":
    main()
