# Qwen Images 3.0 Skill

This repository contains a GitHub Copilot skill for generating images with Alibaba Bailian using the `Qwen-Images-3.0` model.

## Structure

- `.github/copilot-instructions.md` — Copilot instruction hints
- `.github/skills/qwen-images-3.0/skill.md` — core skill definition
- `.github/skills/qwen-images-3.0/README.md` — user-facing usage docs
- `.github/skills/qwen-images-3.0/examples.md` — sample prompts
- `.github/skills/qwen-images-3.0/config.example.json` — config template
- `examples/qwen_images_client.py` — Python example for direct API calls

## Quick start

1. Copy `config.example.json` to a local config file.
2. Set your Bailian API key and endpoint.
3. Use a prompt like: "A futuristic neon city at night, cinematic lighting, ultra detailed"
4. Execute the example client or call the REST API from your toolchain.

## Notes

- Bailian APIs can differ by deployment and version.
- The exact request and response shape may change depending on your endpoint, but the workflow below remains the same.
- `Qwen-Images-3.0` is typically invoked through a model string such as `qwen-image`, `qwen-image-edit`, or a deployment-specific model alias depending on your account setup.
