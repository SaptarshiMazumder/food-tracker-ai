import base64, io
from PIL import Image
from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
oai = OpenAI(api_key=OPENAI_API_KEY)

PROMPT = (
    "You are a food recognizer. Look at the image and reply as compact JSON with keys: "
    "dish_guess (short canonical name), ingredients_guess (list of 3-8 likely ingredients). "
    "No extra text."
)

def vision_node_openai(image_b64: str) -> Dict[str, Any]:
    img_url = f"data:image/jpeg;base64,{image_b64}"
    resp = oai.chat.completions.create(
        model="gpt-4o-mini",  # or gpt-4.1-mini
        messages=[{
            "role":"user",
            "content":[
                {"type":"text","text":PROMPT},
                {"type":"image_url","image_url":{"url":img_url}}
            ]
        }],
        temperature=0.2,
        max_tokens=200
    )
    import json
    payload = json.loads(resp.choices[0].message.content)
    # align schema
    return {
        "dish_guess": payload.get("dish_guess","").lower(),
        "ingredients_guess": [i.lower() for i in payload.get("ingredients_guess", [])],
        "labels_topk": [payload.get("dish_guess","")],   # we don’t have topk here
        "conf_topk": [1.0]
    }
