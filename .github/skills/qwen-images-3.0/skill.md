---
name: qwen-images-3.0
description: Generate images through Alibaba Bailian using the Qwen-Images-3.0 model.
---

# Qwen Images 3.0 Skill

Use this skill when the user asks to generate images from text prompts using the Alibaba Bailian platform.

## Purpose

Generate visual content by sending a text prompt to the Bailian image model and returning the image URL, file, or generated result.

## Required environment variables

```bash
export BAILIAN_API_KEY="your_api_key"
export BAILIAN_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
export BAILIAN_MODEL="qwen-image"
```

If your account uses a custom deployment alias, replace `BAILIAN_MODEL` with the actual model name or deployment ID.

## Typical request

Use the OpenAI-compatible or Bailian-compatible image generation endpoint.

```bash
curl -sS -X POST "$BAILIAN_BASE_URL/images/generations" \
  -H "Authorization: Bearer $BAILIAN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-image",
    "prompt": "A cinematic mountain lake at sunset, ultra detailed, realistic reflections, soft golden light",
    "size": "1024x1024",
    "n": 1
  }'
```

Some deployments expose the same capability under different routes, for example:

- `/images/generations`
- `/v1/images/generations`
- `/api/v1/images/generations`

Use the documented endpoint from your Bailian account if it differs.

## Response handling

After the request succeeds, parse the returned JSON payload and return either:

- `data[0].url` if the API returns image URLs
- `data[0].b64_json` if the API returns base64 image data
- `data[0].image` or another model-specific field if required by the deployment

If the API returns a binary file or a signed download URL, handle that appropriately and return it to the user.

## Prompt construction

Good prompts usually include:

- subject
- style
- composition
- lighting
- color palette
- camera angle or mood

Example:

```json
{
  "model": "qwen-image",
  "prompt": "A modern luxury watch product shot on a white background, soft studio lighting, high detail, premium advertising style",
  "size": "1024x1024",
  "n": 1
}
```

## Error handling

If the request fails, inspect and report:

- invalid or expired API key
- wrong `BAILIAN_BASE_URL`
- unsupported model alias
- insufficient account permissions
- rate limiting or quota exhaustion
- mismatch between payload schema and platform contract

## Example final answer to the user

"已为你生成图片，链接如下：<image_url>。如果需要，我可以继续调整为更写实、更商业海报风格或更适合社媒尺寸。"

## Behavior

When a user asks for image generation, assume they want one or more images created with the Bailian Qwen model. Do not ask unnecessary questions unless the prompt is incomplete or ambiguous.

## Recommended default behavior

- default size: `1024x1024`
- default count: `1`
- default style: use the user's wording directly, with minor cleanup for clarity
- if the user mentions aspect ratio, respect it when supported
