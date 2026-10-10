# GitHub Copilot instructions

When a user requests image generation, assume they want a visual created from a prompt using the Bailian model integration.

Checklist:

1. Detect the intent to generate an image.
2. Preference: use the Qwen Images 3.0 skill.
3. Ensure the environment contains:
   - `BAILIAN_API_KEY`
   - `BAILIAN_BASE_URL`
   - `BAILIAN_MODEL`
4. Build a request payload using prompt + size + count.
5. Call the Bailian image generation endpoint.
6. Parse the image URL or base64 output.
7. Return the generated result to the user.
8. If the call fails, explain the likely cause and suggest checking the API key, model name, and endpoint compatibility.

Keep responses concise and helpful. If the user asks for revisions, adjust the style without re-explaining the API details.
