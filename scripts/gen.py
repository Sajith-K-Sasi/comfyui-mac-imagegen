#!/usr/bin/env python3
"""Generate sprites with FLUX.2 Klein 4B — the one model this setup is standardised on.

  gen.py "pixel art fox, front facing"                    # txt2img
  gen.py "same fox, side view facing right" --ref fox.png # reference-guided (keeps the character)
  gen.py "..." --lora flux2-klein-spritesheet:0.8         # optional style/layout lora

Pairs with pixelate.py (snap to pixel grid) and spritesheet.py (shared-palette sheet):
  ./gen.py "..." -o fox_front && ./pixelate.py output/fox_front_00001_.png -s 64 -c 16

4 steps is the default on purpose: klein-4b *distilled* is step-distilled to 4, and
more steps make it worse, not better. Beyond grain, 8 steps starts fabricating content
that was never prompted — invented caption text under stickers, duplicated cards and
doubled tab bars in UI mockups. 4 steps is cleanest AND ~3x faster.
"""
import argparse, json, os, sys, time, urllib.request, urllib.error

API = os.environ.get("COMFY_API", "http://127.0.0.1:8188")
UNET = "flux-2-klein-4b-Q8_0.gguf"
CLIP = "Qwen_3_4b-Q6_K.gguf"   # stock Qwen3-4B; A/B vs the uncensored finetune showed no quality change (mean RMSE 18)
VAE  = "flux2-vae.safetensors"


def api(path, payload=None):
    url = API + path
    if payload is None:
        return json.loads(urllib.request.urlopen(url, timeout=30).read())
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())


def build(a):
    g = {
        "1": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": UNET}},
        "2": {"class_type": "CLIPLoaderGGUF", "inputs": {"clip_name": CLIP, "type": "flux2"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": VAE}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": a.prompt}},
        "5": {"class_type": "EmptyFlux2LatentImage",
              "inputs": {"width": a.size, "height": a.size, "batch_size": a.batch}},
        "6": {"class_type": "Flux2Scheduler",
              "inputs": {"steps": a.steps, "width": a.size, "height": a.size}},
        "7": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": a.sampler}},
        "8": {"class_type": "RandomNoise", "inputs": {"noise_seed": a.seed}},
        "9": {"class_type": "CFGGuider", "inputs": {"model": ["1", 0], "positive": ["4", 0],
                                                    "negative": ["13", 0], "cfg": a.cfg}},
        "13": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": a.negative}},
        "10": {"class_type": "SamplerCustomAdvanced",
               "inputs": {"noise": ["8", 0], "guider": ["9", 0], "sampler": ["7", 0],
                          "sigmas": ["6", 0], "latent_image": ["5", 0]}},
        "11": {"class_type": "VAEDecode", "inputs": {"samples": ["10", 0], "vae": ["3", 0]}},
        "12": {"class_type": "SaveImage", "inputs": {"images": ["11", 0], "filename_prefix": a.out}},
    }

    model_src = ["1", 0]
    if a.lora:
        name, _, strength = a.lora.partition(":")
        if not name.endswith(".safetensors"):
            name += ".safetensors"
        g["20"] = {"class_type": "LoraLoaderModelOnly",
                   "inputs": {"model": ["1", 0], "lora_name": name,
                              "strength_model": float(strength or 1.0)}}
        model_src = ["20", 0]
    g["9"]["inputs"]["model"] = model_src

    # Reference image: keeps character identity across angles/poses (Kontext-style).
    if a.ref:
        g["30"] = {"class_type": "LoadImage", "inputs": {"image": a.ref}}
        g["31"] = {"class_type": "FluxKontextImageScale", "inputs": {"image": ["30", 0]}}
        g["32"] = {"class_type": "VAEEncode", "inputs": {"pixels": ["31", 0], "vae": ["3", 0]}}
        g["33"] = {"class_type": "ReferenceLatent",
                   "inputs": {"conditioning": ["4", 0], "latent": ["32", 0]}}
        g["9"]["inputs"]["conditioning"] = ["33", 0]
    return g


def main():
    p = argparse.ArgumentParser(description="FLUX.2 Klein 4B sprite generator")
    p.add_argument("prompt")
    p.add_argument("-o", "--out", default="klein", help="output filename prefix")
    p.add_argument("-s", "--size", type=int, default=1024)
    # 4 steps + euler + cfg 1.0 is the OFFICIAL config for klein-4b *distilled*
    # (ComfyUI template image_flux2_klein_text_to_image.json; BFL docs). The model is
    # step-distilled to 4 — more steps "deep-fry" it. Measured flat-region grain on a
    # portrait: 4st=1.607, 8st=1.879, 20st=2.728, 32st=6.091. 4 steps is both the
    # cleanest AND ~3x faster (26s vs 85s).
    # If you ever load klein-4b-BASE instead, use --steps 20 --cfg 5.
    p.add_argument("-n", "--steps", type=int, default=4, help="4 for distilled, 20 for base")
    p.add_argument("--cfg", type=float, default=1.0, help="1.0 for distilled, 5.0 for base")
    p.add_argument("--negative", default="", help="only meaningful with --cfg > 1")
    p.add_argument("--seed", type=int, default=0, help="0 = time-based")
    p.add_argument("-b", "--batch", type=int, default=1)
    p.add_argument("--sampler", default="euler")
    p.add_argument("--lora", help="name[:strength], e.g. flux2-klein-spritesheet:0.8")
    p.add_argument("--ref", help="filename in ComfyUI/input/ to keep character consistent")
    a = p.parse_args()
    if a.seed == 0:
        a.seed = int(time.time() * 1000) % (2**31)

    try:
        api("/system_stats")
    except urllib.error.URLError:
        sys.exit(f"ComfyUI not reachable at {API} — start it with ./start-comfy.sh")

    t0 = time.time()
    pid = api("/prompt", {"prompt": build(a)})["prompt_id"]
    print(f"  queued {pid[:8]}  seed {a.seed}  {a.steps} steps  {a.size}px", flush=True)

    while True:
        h = api(f"/history/{pid}")
        if pid in h:
            st = h[pid].get("status", {})
            if st.get("status_str") == "error":
                for kind, m in st.get("messages", []):
                    if kind == "execution_error":
                        sys.exit(f"  failed in {m.get('node_type')}: {m.get('exception_message')}")
                sys.exit("  failed")
            if st.get("completed") or st.get("status_str") == "success":
                files = [i["filename"] for o in h[pid].get("outputs", {}).values()
                         for i in o.get("images", [])]
                for f in files:
                    print(f"  {time.time()-t0:.0f}s  -> output/{f}")
                return
        time.sleep(1.0)


if __name__ == "__main__":
    main()
