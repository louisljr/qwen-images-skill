# Qwen Images 3.0 Skill

This skill lets Copilot call Alibaba Bailian and generate images using `Qwen-Images-3.0`.

## Prerequisites

You must have:

- a valid Bailian API key
- platform access to the image model
- a compatible endpoint

## Configure

```bash
export BAILIAN_API_KEY="your_api_key"
export BAILIAN_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
export BAILIAN_MODEL="qwen-image"
```

## Example request

```bash
curl -sS -X POST "$BAILIAN_BASE_URL/images/generations" \
  -H "Authorization: Bearer $BAILIAN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-image",
    "prompt": "A cozy hillside cabin with snow-covered mountains, warm morning light, cinematic composition",
    "size": "1024x1024",
    "n": 1
  }'
```

## Expected response

The response usually contains a JSON array under `data`, for example:

```json
{
  "data": [
    {
      "url": "https://example.com/generated-image.png"
    }
  ]
}
```

## Notes

- Exact field names may differ across versions of the Bailian API.
- If your endpoint is custom, replace `BAILIAN_BASE_URL` accordingly.
- If the platform does not return a direct URL, decode base64 or download from the returned field.

## Prompt ideas

- "Generate a cyberpunk city street at night with neon signs"
- "Create a luxury skincare ad banner with a glass bottle on a white background"
- "A cute mascot logo in 3D cartoon style, smooth gradients, bright colors"
