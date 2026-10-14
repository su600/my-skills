---
name: openrouter-image-generator
description: Create images from natural-language requests with OpenRouter's OpenAI `openai/gpt-image-2.5-flare` model. Use this skill whenever the user asks to generate, draw, or create an image or illustration. First expand their idea into a concrete, detailed prompt, show the exact prompt and proposed aspect ratio, and wait for explicit confirmation before generating; never skip confirmation or silently choose an aspect ratio.
---

# OpenRouter Image Generator

Turn an image idea into a clear, detailed prompt, let the user approve both the prompt and canvas ratio, then generate the image with OpenRouter model `openai/gpt-image-2.5-flare`.

## Workflow

1. **Understand the image request.** Preserve the user's subject, intent, and any specified style or constraints. Fill in useful visual specifics that are implied but missing: composition and subject placement, setting/background, lighting, palette, materials/textures, viewpoint, and mood. Include legible text only when requested, and quote the exact text. Avoid adding story details that would change the user's idea. Ask a focused follow-up only if an essential ambiguity cannot be handled by a reasonable draft.
2. **Propose an aspect ratio.** If the user specified one, use that. Otherwise recommend a ratio that suits the intended use and composition; common choices are `1:1` (square), `4:5` (portrait post), `3:2` or `4:3` (landscape), `9:16` (phone/vertical story), and `16:9` (wide screen). Make the recommendation explicit; do not treat a guess as confirmed.
3. **Present the exact generation prompt and ratio, then wait.** Show the complete prompt in a clearly marked block and the proposed ratio. Explicitly ask the user to confirm the ratio as well as the prompt; for example: “建议比例：`16:9`。确认使用下面这段提示词和 `16:9` 比例生成吗？回复‘确认’即可；也可以告诉我想改的提示词或比例。” Do not call the image model until the user explicitly approves the prompt and ratio. If they request edits, update the proposal and ask again. A clear “确认” after both the complete prompt and a specific ratio have been shown approves both; if either is undecided, ask rather than generating.
4. **Generate only after approval.** Prefer an available, already-authorized OpenRouter image-generation integration if the current environment exposes one. Select exactly `openai/gpt-image-2.5-flare`; pass the approved prompt verbatim and the approved `aspect_ratio`. If no image-generation integration is available, use the bundled helper `scripts/generate.mjs` with a configured `OPENROUTER_API_KEY` (see below). Never claim an image was generated unless the request succeeded and an output image was saved. Never ask the user to paste a secret into chat; if no authorized route or key is configured, explain the setup blocker without exposing credential values.
5. **Return the result.** Provide the generated image as an attachment/inline image if the host supports it; otherwise give the exact saved file path. Mention the model and aspect ratio. If generation fails, report the actionable error without implying success.

## Calling the bundled OpenRouter helper

The helper sends a single-image request to `POST https://openrouter.ai/api/v1/images`, with model `openai/gpt-image-2.5-flare`, the approved `prompt`, `aspect_ratio`, and PNG output. It reads the prompt from stdin so long or multilingual prompts do not need shell escaping.

Use an already-authorized OpenRouter integration if the current environment provides one. Otherwise, the helper looks first for `OPENROUTER_API_KEY` in its process environment, then falls back to the existing Pi credential at `~/.pi/agent/auth.json` under `openrouter.key`. The credential is read only inside the local helper process. Never print, log, copy into chat, or place the key in command arguments. If neither credential source is available, explain that OpenRouter authorization needs to be configured; do not ask the user to paste a secret into chat.

Run using the absolute helper path (the default output is `~/Pictures/GeneratedImages`); substitute the approved ratio:

```bash
node "$SKILL_DIR/scripts/generate.mjs" --aspect-ratio 16:9 <<'IMAGE_PROMPT'
Paste the exact user-approved prompt here.
IMAGE_PROMPT
```

The helper prints the saved image path on success. Use the returned path to show or attach the image. The model name is intentionally fixed in the helper so a different model is not selected by accident. OpenRouter may normalize or clamp aspect ratios to the provider-supported subset; report the requested ratio, and do not claim exact pixel dimensions unless the response provides them.
