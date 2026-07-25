# Local image generation on Apple Silicon — ComfyUI workflows for Z-Image + FLUX.2 Klein

Six working ComfyUI workflows, four CLI scripts, and a one-command model downloader for
running **Z-Image Turbo** and **FLUX.2 Klein 4B** locally on a Mac. No GPU, no API key,
nothing uploaded.

Developed and measured on an **M5 MacBook Air, 24 GB, ComfyUI 0.28.0, PyTorch 2.13, MPS**.
Every setting here was verified by running it, not copied from a model card.

| Task | Model | Time (this machine) |
|---|---|---|
| Text-to-image | Klein 4 steps | ~30s |
| Text-to-image | Z-Image 8 steps | ~110s |
| Reference-guided edit | Klein | ~66s |
| 2K upscale | Z-Image + RealESRGAN | ~7 min |

---

## Requirements

- Apple Silicon Mac, **24 GB unified memory recommended** (16 GB will thrash — free memory
  bottomed at 1.99 GB during upscaling here)
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) with the
  [ComfyUI-GGUF](https://github.com/city96/ComfyUI-GGUF) custom node (all models here are GGUF)
- ~20 GB free disk

## Install

```bash
git clone <this-repo> && cd comfyui-mac-imagegen

# downloads ~20 GB into your ComfyUI install; resumable, safe to re-run
./download-models.sh /path/to/ComfyUI

# or skip the 2.9 GB ControlNet
./download-models.sh /path/to/ComfyUI --core-only

cp workflows/*.json /path/to/ComfyUI/user/default/workflows/
```

Restart ComfyUI and refresh the browser tab (it caches the workflow list).

## What gets downloaded

| File | Size | Goes in | Used by |
|---|---|---|---|
| `flux-2-klein-4b-Q8_0.gguf` | 4.3 GB | `models/diffusion_models/` | Klein workflows |
| `z-image-turbo-Q6_K.gguf` | 5.9 GB | `models/diffusion_models/` | Z-Image workflows |
| `Qwen_3_4b-Q6_K.gguf` | 3.3 GB | `models/text_encoders/` | **both** |
| `flux2-vae.safetensors` | 0.3 GB | `models/vae/` | Klein |
| `z_image_ae.safetensors` | 0.3 GB | `models/vae/` | Z-Image |
| `RealESRGAN_x4plus.safetensors` | 67 MB | `models/upscale_models/` | upscaler |
| `Z-Image-Turbo-Fun-Controlnet-Union.safetensors` | 2.9 GB | `models/model_patches/` | ControlNet (optional) |

**One text encoder serves both models.** Z-Image and Klein 4B both condition on Qwen3-4B;
ComfyUI only swaps the tokenizer template (`type: flux2` vs `type: lumina2`). I A/B'd two
different Qwen3-4B builds on both models — mean RMSE 18–21, no quality difference. Don't
bother hunting for a "better" encoder.

The VAEs are **not** interchangeable — different latent formats.

---

## Workflows

| File | What it does |
|---|---|
| `FLUX2-Klein-Q8.json` | Fast text-to-image |
| `FLUX2-Klein-Edit.json` | Reference-guided edit — keeps a scene, changes one thing |
| `FLUX2-Klein-Inpaint.json` | Masked inpainting |
| `Z-Image-Turbo-T2I.json` | Text-to-image, cleaner output |
| `Z-Image-PixelArt.json` | Sprites (expects a pixel-art LoRA, see below) |
| `Z-Image-2K-Upscaler.json` | 1024 → 2048 |

`Z-Image-PixelArt.json` references `pixel_art_style_z_image_turbo.safetensors` — not
included (third-party LoRA). Grab any Z-Image pixel-art LoRA into `models/loras/` and point
the node at it, or delete the LoRA node to run the base model.

## CLI

The scripts drive ComfyUI over its HTTP API — useful for batching, and for letting a coding
agent generate its own assets.

```bash
cd scripts

./gen.py "a red ceramic teapot on a wooden table, soft window light"
./gen.py "same teapot, side view" --ref teapot.png     # reference-guided edit
./gen.py "..." --lora my-style:0.8                     # optional LoRA
./gen.py "..." --steps 20 --cfg 5                      # if you load klein-4b-BASE

./upscale.py ../output/teapot_00001_.png -o teapot_2k  # 1024 -> 2048

./pixelate.py image.png -s 64 -c 16                    # snap to a real pixel grid
./spritesheet.py f1.png f2.png f3.png -s 64 -c 16      # sheet with ONE shared palette
```

`gen.py` and `upscale.py` need ComfyUI running. The other two are offline Pillow scripts.

`tools/` holds the measurement scripts used for the write-up: `grain.py` (high-frequency
noise estimate) and `gridfit.py` (how close an image is to a true pixel grid).

---

## Settings that matter

These are the non-obvious ones. Getting the first one wrong costs you 3× the time **and**
worse images.

### Klein 4B distilled: 4 steps, cfg 1.0, euler

It's **step-distilled to 4**. More steps don't refine — they over-cook. Measured on a dense
scene:

| Steps | Noise σ | Time |
|---|---|---|
| **4** | **5.08** | **32s** |
| 8 | 5.18 | 85s |
| 20 | 5.59 | 107s |
| 32 | 5.76 | 265s |

Worse, past 4 steps it starts **fabricating content that isn't in your prompt** — invented
caption text under stickers, duplicated cards and doubled tab bars in UI mockups. Grain
metrics rate that difference at +0.0% because flat graphic art has no high-frequency energy
to measure. Look at the images, not just the numbers.

Don't wire up `FluxGuidance`: the distilled checkpoint has no guidance tensors, so it's a
byte-for-byte no-op.

**If you load `flux-2-klein-base-4b` instead** — a different model — it needs **20 steps,
cfg 5**.

### Z-Image Turbo: 8 steps, cfg 1.0, simple scheduler

euler or `res_multistep` both work; euler was faster here for equal quality. Keep cfg at 1.0
— it's distilled, and raising it degrades output.

`ModelSamplingAuraFlow(3.0)` appears in the official templates but is **redundant** — the
model config already applies shift 3.0. Verified: byte-identical output with and without.

### ControlNet: strength 0.3–0.5, not the default 1.0

| Strength | Behaviour |
|---|---|
| 1.0 | Traces every edge — content locked, effectively a recolour tool |
| 0.7 | Hybrid |
| **0.5** | **Layout kept, content free** — the useful setting |
| 0.3 | Loose structural influence |

The template ships 1.0, which is the setting least suited to what most people want.

### `VAEDecodeTiled` is mandatory above ~1500px

Plain `VAEDecode` dies on MPS at 2048²:
`MPSGraph does not support tensor dims larger than INT_MAX`. The upscaler workflow already
uses tiled decode.

### Prompt length differs between the models

Klein wants **descriptive** prompts — BFL recommends 100–400 words. Given "a photorealistic
hamster" it produced a rat. Z-Image is accurate from a handful of words. If Klein gives you
the wrong animal, add detail rather than blaming the model.

---

## Thermals

A fanless Air throttles under sustained load, then plateaus. 24 back-to-back generations:

| Phase | Time/image |
|---|---|
| Cold start (model load) | 36.8s |
| Cool burst (runs 2–5) | 20.9s |
| **Sustained plateau (runs 21–24)** | **30.2s** |

**+45% from burst to sustained**, then flat — it throttles but doesn't spiral. Plan batches
around ~30s/image, not the ~21s a quick two-image test suggests.

## Which model for which job

- **Z-Image** — cleaner output (~2.3× less grain, verified across 4 seeds), single-subject
  anatomy, short prompts, UI mockups
- **Klein** — 3.5× faster, multi-person scenes, product shots, and **the only one that can
  edit**

Z-Image *cannot* edit images. Z-Image Omni and Z-Image Edit are not publicly released —
Tongyi-MAI publishes only `Z-Image` and `Z-Image-Turbo`, both text-to-image. ComfyUI ships
the nodes; the weights don't exist yet.

The models are complementary, so the useful pattern is a pipeline:
**create with Z-Image → edit with Klein → upscale with Z-Image.**

## A note on outputs

ComfyUI embeds the full workflow JSON in every PNG it writes — prompt, models, sampler,
seed. Your output folder is a searchable experiment log:

```python
import json
from PIL import Image
workflow = json.loads(Image.open("output/foo.png").info["prompt"])
```

Drag any output back into ComfyUI and the workflow reconstitutes.

## Licences

Both models are Apache 2.0 (Z-Image Turbo; FLUX.2 Klein **4B** — note the 9B is not).
The workflows and scripts here are MIT. Model licences govern the weights and are not
altered by this repo.

Local generation is unmoderated — nothing here inspects prompts or filters output. That
also means responsibility sits entirely with you.
