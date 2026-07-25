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

---

## Speed: the number nobody publishes

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
- **Multi-person scenes** (n=1). Five people: all faces visible, clean anatomy. Z-Image obscured two faces.
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

## ControlNet:

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

A fanless laptop with no GPU now creates, edits, and upscales images locally, in about the time it takes to make coffee. That's a genuinely new capability, and it's about 8 GB of downloads away.

---

*All timings measured on an M5 MacBook Air, 24 GB, ComfyUI 0.28.0, PyTorch 2.13, MPS. Every image in this post was generated on that machine.*
