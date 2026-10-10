import json
import os
from urllib import request, error


def call_bailian_image_generation(prompt: str, size: str = "1024x1024", count: int = 1):
    api_key = os.getenv("BAILIAN_API_KEY")
    base_url = os.getenv("BAILIAN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    model = os.getenv("BAILIAN_MODEL", "qwen-image")

    if not api_key:
        raise RuntimeError("BAILIAN_API_KEY is missing")

    url = f"{base_url.rstrip('/')}/images/generations"
    payload = {
        "model": model,
        "prompt": prompt,
        "size": size,
        "n": count,
    }

    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=120) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Bailian API request failed: {detail}") from exc


if __name__ == "__main__":
    prompt = "A futuristic city skyline at night, neon reflections, cinematic lighting, ultra detailed"
    result = call_bailian_image_generation(prompt)
    print(json.dumps(result, ensure_ascii=False, indent=2))
