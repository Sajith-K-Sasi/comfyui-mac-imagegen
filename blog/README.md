# I Ran Two Image Models on a Fanless MacBook Air for a Week. Here's What It Can Actually Do.

*No GPU. No subscription. No uploads. 24 GB of unified memory and a laptop with no fan.*

![pipeline](images/BLOG_pipeline.png)

That coffee shop was generated, edited, and upscaled to 2048×2048 on an M5 MacBook Air in **9 minutes 16 seconds** — three different steps, two different models, nothing leaving the machine.

I set out to answer a narrow question: **Z-Image Turbo or FLUX.2 Klein — which one should I keep?** I had both installed and 24 GB of RAM that didn't want to hold both.

I got the wrong answer twice before landing on a better question.

---

## The setup

Everything is GGUF-quantised, running in ComfyUI on MPS.

| Component | File | Size |
|---|---|---|
| FLUX.2 Klein 4B (distilled) | `flux-2-klein-4b-Q8_0.gguf` | 4.3 GB |
| Z-Image Turbo | `z-image-turbo-Q6_K.gguf` | 5.9 GB |
| Text encoder (**shared**) | Qwen3-4B, Q6_K | 3.3 GB |
| VAEs | one each | ~336 MB each |
| RealESRGAN (upscaling) | `RealESRGAN_x4plus.safetensors` | 67 MB |
| Z-Image Fun ControlNet Union | model patch | 2.9 GB |

A detail that surprised me: **both models use the same text encoder architecture.** Z-Image and Klein 4B both condition on Qwen3-4B. In ComfyUI the only thing that changes is the tokenizer template — `comfy/sd.py` routes to a Klein tokenizer for `flux2`, and a Z-Image tokenizer for everything else.

I assumed the encoder I had (a community "uncensored" Qwen3-4B finetune shipped for Klein) was handicapping Z-Image. So I downloaded the official one and re-ran all six benchmarks.

**Mean pixel difference: RMSE 21. No change in quality, prompt adherence, or grain.** A 3 GB download to disprove my own hypothesis.

Then I ran the same swap on the Klein side: **mean RMSE 18, again no quality change.** Text still spelled perfectly; every failure mode Klein had before, it still had after.

So across two models and twelve prompts: **which Qwen3-4B you feed these models doesn't measurably matter.** Detail shifts a little, quality doesn't. Use the stock encoder — but don't expect the swap to fix anything. Worth publishing, because it saves you the download.

---

## The thing I got wrong: step count

My model is the **distilled** 4B — Klein's equivalent of "Turbo." I was running it at 20 steps. My inpainting workflow was at 25.

The correct value is **4**.

Distilled models are trained to converge in a fixed number of steps. Past that, they don't refine — they over-cook. Black Forest Labs' own docs warn output becomes "overcooked, waxy, or deep-fried."

I measured it. Image noise, sampled across step counts:

| Steps | Noise σ (dense scene) | Time |
|---|---|---|
| **4** | **5.08** | **32s** |
| 8 | 5.18 | 85s |
| 20 | 5.59 | 107s |
| 32 | 5.76 | 265s |

Grain rises *monotonically* with steps. Backwards from the usual intuition, and it held across every sampler I tried.

Dropping 20 → 4 made images **cleaner and 3.3× faster** (85s → 26s). That single change was worth more than every other tweak combined.

### The failure the metric couldn't see

I nearly published "8 steps is ~7% grainier" and moved on. Then I looked at the actual images.

![why 4 steps](images/BLOG_why4steps.png)

At 8 steps, on a sticker sheet, Klein **invented caption text under three of four stickers** — "2/ cndo", "3", "16cooo". Nothing in the prompt asked for text.

On a UI mockup at 8 steps: ghost text bleeding outside the phone frame, duplicated cards, **two stacked tab bars**.

At 4 steps, both are clean.

My noise metric rated the difference between these images at **+0.0%**. Flat graphic art has almost no high-frequency energy, so a noise estimator has nothing to measure. It was structurally blind to the exact failure that matters most for design work.

**Over-cooking a distilled model doesn't just add noise. It fabricates content that isn't in your prompt.** Automated metrics caught the photographic story — text +92%, anime +35%, food +27% — and missed the graphic story completely. You need both passes.

---

## Speed: the number nobody publishes

Most local-gen posts quote one warm generation time. On a fanless chassis that's misleading.

24 back-to-back generations, identical settings, different seeds:

![sustained load](images/BLOG_sustained_load.png)

| Phase | Time/image |
|---|---|
| Cold start (model load) | 36.8s |
| **Cool burst** (runs 2–5) | **20.9s** |
| Ramp (runs 6–20) | 22 → 29s |
| **Sustained plateau** (runs 21–24) | **30.2s** |

**+45% from burst to sustained** — then it flattens and stays flat. Four consecutive runs at exactly 30.2s. It throttles, but it doesn't spiral.

Free memory *rose* slightly while times climbed, which rules out memory pressure and points squarely at thermals.

Plan for **~30s/image sustained**, not the ~21s a quick two-image test suggests.

---

## Which model for which job

Both at their correct settings, same prompt, same seed. Klein 4 steps ≈ **31s**. Z-Image 8 steps ≈ **109s**.

![head to head](images/BLOG_headtohead.png)

![use cases](images/BLOG_usecases.png)

Findings marked ✓ were re-run across four seeds. Everything else is a **single sample** — read those as impressions, not measurements. I've kept the distinction visible because it turned out to matter.

**Z-Image wins:**
- ✓ **Cleaner output.** ~2.3× less grain, and it survived retesting: Z-Image was cleaner in **11 of 12** seed × category runs, roughly 2.5× on portraits. The most robust difference between the two.
- ✓ **Single-subject anatomy.** On "a barista's hands," Z-Image was correct **4/4**; Klein **1/4**.
- **Short prompts** (n=1). "a photorealistic hamster" → Z-Image gives a hamster; Klein gives a rat. Klein wants descriptive prompts — BFL recommends 100–400 words.
- **UI mockups** (n=1). "BALANCE" and "$36.05" render legibly; Klein's equivalent was mush.
- **Pixel-grid fidelity** for sprite work (n=1) — though a post-process erases the gap; see below.

**Klein wins:**
- ✓ **Speed.** 3.5× faster, and remarkably consistent — 30–34s across seven runs.
- **Multi-person scenes** (n=1). Five people: all faces visible, clean anatomy. Z-Image obscured two faces and multiplied hands.
- **Commercial product shots** (n=1). E-commerce-ready in 30 seconds.
- **Editing.** It's the only option — more below.

One tendency explains both anatomy results: **Klein over-populates.** Asked for one barista's two hands, it added a second person in 3 of 4 seeds — three hands, two torsos. Asked for five friends, that same instinct gave five clean faces where Z-Image struggled. Want a crowd, use Klein. Want one subject, use Z-Image.

**Both fail:** dense small text. Three words on a sign render perfectly. Twenty tiny UI labels turn to gibberish in both. If you need real interface copy, composite it afterwards.

![people](images/BLOG_people.png)

---

## The answer wasn't "pick one"

The head-to-head kept ending in "close, depends." The pipeline question had a clear answer.

**Create with Z-Image → edit with Klein → upscale with Z-Image.**

Look again at the top image. Stage 2 preserved the espresso machine, shelf jars, both plants, the grinder, window, wood grain and lighting — and added one sleeping cat, matched to the art style. **66 seconds.**

Z-Image cannot do that edit at all. Klein's own creation from a short prompt would have been worse. Each link is the best tool for its step.

Worth stating plainly, because several blog posts imply otherwise: **Z-Image cannot edit images.** Z-Image Omni and Z-Image Edit are not publicly released. I checked the Tongyi-MAI org directly — it publishes `Z-Image` and `Z-Image-Turbo`, both text-to-image only. ComfyUI ships the nodes; the weights don't exist yet.

---

## Pixel art: where the post-process beats the model

Game sprites are the case where I expected the model choice to matter most, and it mattered least.

![pixel art](images/BLOG_pixelart.png)

Straight out of the model, Z-Image is genuinely closer to a real pixel grid — I measured how far each image is from being a true 64×64 grid scaled up:

| | grid-RMSE | in-cell variance |
|---|---|---|
| Klein 4 steps | 35.65 | 10.52 |
| **Z-Image 8 steps** | **28.75** | **8.93** |

Neither is *actually* pixel art. Both are 1024px images that look pixel-ish — 23,000 and 30,000 distinct colours respectively, where a real 16-bit sprite has sixteen.

So you post-process. Area-average downsample to 64px, median-cut to a fixed palette, no dithering (dithering re-introduces exactly the speckle you're removing). After that:

| | size | colours | edge hardness |
|---|---|---|---|
| Klein | 64×64 | 16 | 12.19 |
| Z-Image | 64×64 | 16 | 12.09 |

**The 24% gap closes to under 1%.** Forty lines of Pillow erased the difference the models spent 90 seconds arguing about.

That reframes the whole task. For sprite work, model choice barely matters — Klein at 4 steps gets you there in 32s versus Z-Image's 90s, and the palette quantiser decides the actual look. Where the models *do* differ is character consistency across frames, and that's a ControlNet problem, not a model-choice one.

---

## ControlNet: the setting everyone leaves wrong

ControlNet gives you structural control — pose, depth, edges — that prompts can't provide. Z-Image has one; Klein doesn't.

The default strength in the official template is **1.0**, which is the setting *least* suited to what most people want.

![controlnet strength](images/BLOG_controlnet_strength.png)

Same control image, same seed, only strength varies:

| Strength | Result |
|---|---|
| 1.0 | Traces every edge. Content **locked** — asked for a bookshop, got the same coffee shop recoloured |
| 0.7 | Hybrid; books start appearing |
| **0.5** | **Bookshop, original room geometry intact** |
| 0.3 | Bookshop, geometry loosened, best-looking |

At 1.0, canny is a *recolour* tool, not a reimagining tool. For content changes, **0.3–0.5** is the working range.

The sprite case is where this earns its keep. My 2×2 sprite sheet kept producing four near-identical front views, because prompts don't control geometry. With ControlNet: same silhouette, same pose, different character.

![sprite pose control](images/BLOG_controlnet_sprite.png)

For pixel art, lower strength is *better* — 0.6 gave cleaner edges than 1.0 while still holding the pose.

---

## Letting Claude Code generate its own images

ComfyUI has an HTTP API, so an agent can drive it. Roughly 150 lines wraps it:

```bash
./gen.py "a red ceramic teapot on a wooden table, soft window light"
./gen.py "same teapot, side view" --ref teapot.png    # reference-guided edit
./upscale.py output/teapot_00001_.png -o teapot_2k    # 1024 → 2048
```

Placeholder art, sprites, OG images, texture tiles — generated locally, no API key, no per-image cost, nothing uploaded. The integration is genuinely this simple; that's the point.

A trick that made the whole investigation tractable: **ComfyUI embeds the full workflow JSON in every PNG it writes.** Prompt, model files, sampler, seed, everything. Twenty lines of Python turns your output folder into a searchable experiment database:

```python
d = json.loads(Image.open(path).info["prompt"])   # complete workflow
```

I recovered my original settings from a week-old image this way, and later used it to find every image matching "4 steps, seed 20260725". Once you have a few hundred outputs, query the metadata — don't trust filenames or memory.

---

## Honest limits

- **24 GB is doing real work.** Free memory bottomed at **1.99 GB** during upscaling. 16 GB would likely thrash.
- **Upscaling is slow** — ~7 min for 1024→2048. And ESRGAN is 259s of that, not the diffusion. Iterate at 1024, upscale once at the end.
- **`VAEDecodeTiled` is mandatory** on Apple Silicon above ~1500px. Plain `VAEDecode` dies at 2048² with `MPSGraph does not support tensor dims larger than INT_MAX`.
- **The thermal ceiling is real** — plan for 30s/image sustained.
- **MPS only.** None of these timings transfer to CUDA.
- **Unmoderated, but not unlimited.** Nothing here inspects prompts or filters output — no classifier, no moderation API, no logging. That's the real benefit for legitimate work: no false refusals on medical, anatomical or life-drawing prompts. But removing the filter doesn't add a capability. Both models are safety-trained at the data level and, in my testing, simply don't produce explicit imagery from direct prompts. You get a model that won't, not a system that blocks. Standard caveat applies: local generation puts the responsibility entirely on you, and some categories are illegal regardless of being synthetic.
- **Not every verdict is equally solid.** Speed, grain and the step-count artefacts held across many runs — the grain gap survived four seeds at 11/12. Individual quality calls are far shakier, and I got burned repeatedly. On the barista-hands prompt I first said Z-Image was better, then "corrected" myself to *equivalent* after looking at one more image — which happened to be the single seed where Klein succeeds. The full count is Klein 1/4, Z-Image 4/4. I made the exact error this bullet warns about, twice, while writing this post. **Treat any one-image comparison — mine or anyone's — as an anecdote.**

---

## The settings, if you want to skip the week

**FLUX.2 Klein 4B distilled** — 4 steps · cfg 1.0 · euler · Flux2Scheduler · dimensions ×16
Don't add `FluxGuidance`; the distilled checkpoint has no guidance tensors and it's a byte-for-byte no-op.
*(Klein 4B **base** is a different model: 20 steps, cfg 5.)*

**Z-Image Turbo** — 8 steps · cfg 1.0 · euler or res_multistep · simple scheduler
`ModelSamplingAuraFlow(3.0)` is redundant — the model config already applies shift 3.0. I verified: byte-identical output with and without.

**2K upscale** — RealESRGAN 4× → lanczos 0.5× → 5 steps · `dpmpp_2m_sde` · beta · **denoise 0.33** · tiled decode

**ControlNet** — strength **0.3–0.5** for content changes, not the default 1.0

---

## What I'd tell myself at the start

1. **Check the model variant before tuning anything.** Distilled and base need completely different step counts. I burned a week's worth of iterations at 5× the correct value.
2. **Look at the images.** My metrics were rigorous and blind in exactly the place that mattered.
3. **Stop trying to pick a winner.** The models are complementary. The interesting question was never "which one" — it was "which one for which step."

A fanless laptop with no GPU now creates, edits, and upscales images locally, in about the time it takes to make coffee. That's a genuinely new capability, and it's about 8 GB of downloads away.

---

*All timings measured on an M5 MacBook Air, 24 GB, ComfyUI 0.28.0, PyTorch 2.13, MPS. Every image in this post was generated on that machine.*
