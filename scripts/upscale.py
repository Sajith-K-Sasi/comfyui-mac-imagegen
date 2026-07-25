#!/usr/bin/env python3
"""2K upscale an image with Z-Image Turbo + RealESRGAN (official ComfyUI recipe).

  upscale.py output/foo.png                 # -> ~2048x2048
  upscale.py foo.png --megapixels 0.5       # smaller intermediate = faster
  upscale.py foo.png --denoise 0.2          # less re-imagining, more faithful

Pipeline: normalise to N megapixels -> RealESRGAN 4x -> lanczos 0.5x -> VAE encode
-> KSampler 5 steps / dpmpp_2m_sde / beta / denoise 0.33 -> tiled VAE decode.

denoise 0.33 is the official value: high enough for Z-Image to synthesise real
detail, low enough that it doesn't redraw the picture.

VAEDecodeTiled is REQUIRED on Apple Silicon — a plain VAEDecode at 2048x2048 dies
with "MPSGraph does not support tensor dims larger than INT_MAX".

Takes ~7 min for 1024->2048 on an M5. Uses Z-Image, not Klein: Klein's VAE has no
tiled-decode advantage here and Z-Image renders cleaner flat areas at low denoise.
"""
import argparse, json, os, shutil, sys, time, urllib.request, urllib.error

API = os.environ.get("COMFY_API", "http://127.0.0.1:8188")
COMFY = os.path.dirname(os.path.abspath(__file__))
UNET = "z-image-turbo-Q6_K.gguf"
CLIP = "Qwen_3_4b-Q6_K.gguf"
VAE = "z_image_ae.safetensors"
UPSCALER = "RealESRGAN_x4plus.safetensors"


def api(path, payload=None):
    url = API + path
    if payload is None:
        return json.loads(urllib.request.urlopen(url, timeout=30).read())
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())


def build(a, image_name):
    return {
        "1": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": UNET}},
        "2": {"class_type": "CLIPLoaderGGUF", "inputs": {"clip_name": CLIP, "type": "lumina2"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": VAE}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": a.prompt}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": ""}},
        "30": {"class_type": "LoadImage", "inputs": {"image": image_name}},
        "31": {"class_type": "ImageScaleToTotalPixels",
               "inputs": {"image": ["30", 0], "upscale_method": "lanczos",
                          "megapixels": a.megapixels, "resolution_steps": 1}},
        "32": {"class_type": "UpscaleModelLoader", "inputs": {"model_name": UPSCALER}},
        "33": {"class_type": "ImageUpscaleWithModel",
               "inputs": {"upscale_model": ["32", 0], "image": ["31", 0]}},
        "34": {"class_type": "ImageScaleBy",
               "inputs": {"image": ["33", 0], "upscale_method": "lanczos", "scale_by": a.scale_by}},
        "35": {"class_type": "VAEEncode", "inputs": {"pixels": ["34", 0], "vae": ["3", 0]}},
        "10": {"class_type": "KSampler",
               "inputs": {"model": ["1", 0], "positive": ["4", 0], "negative": ["5", 0],
                          "latent_image": ["35", 0], "seed": a.seed, "steps": a.steps,
                          "cfg": 1.0, "sampler_name": "dpmpp_2m_sde", "scheduler": "beta",
                          "denoise": a.denoise}},
        "11": {"class_type": "VAEDecodeTiled",
               "inputs": {"samples": ["10", 0], "vae": ["3", 0], "tile_size": a.tile,
                          "overlap": 64, "temporal_size": 64, "temporal_overlap": 8}},
        "12": {"class_type": "SaveImage", "inputs": {"images": ["11", 0], "filename_prefix": a.out}},
    }


def main():
    p = argparse.ArgumentParser(description="Z-Image 2K upscaler")
    p.add_argument("src", help="path to an image (copied into ComfyUI/input/ if needed)")
    p.add_argument("-o", "--out", default="upscaled", help="output filename prefix")
    p.add_argument("--megapixels", type=float, default=1.0, help="intermediate size before 4x")
    p.add_argument("--scale-by", dest="scale_by", type=float, default=0.5,
                   help="post-ESRGAN rescale; 0.5 of a 4x = net 2x")
    p.add_argument("--denoise", type=float, default=0.33, help="official value")
    p.add_argument("-n", "--steps", type=int, default=5)
    p.add_argument("--tile", type=int, default=512, help="VAE decode tile size")
    p.add_argument("--prompt", default="masterpiece, 8k", help="official template prompt")
    p.add_argument("--seed", type=int, default=0, help="0 = time-based")
    a = p.parse_args()
    if a.seed == 0:
        a.seed = int(time.time() * 1000) % (2 ** 31)

    if not os.path.exists(a.src):
        sys.exit(f"no such file: {a.src}")
    name = os.path.basename(a.src)
    dest = os.path.join(COMFY, "input", name)
    if os.path.abspath(a.src) != os.path.abspath(dest):
        shutil.copyfile(a.src, dest)

    try:
        api("/system_stats")
    except urllib.error.URLError:
        sys.exit(f"ComfyUI not reachable at {API} — start it with ./start-comfy.sh")

    t0 = time.time()
    pid = api("/prompt", {"prompt": build(a, name)})["prompt_id"]
    print(f"  queued {pid[:8]}  denoise {a.denoise}  {a.steps} steps  (this takes a few minutes)",
          flush=True)
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
                for o in h[pid].get("outputs", {}).values():
                    for i in o.get("images", []):
                        print(f"  {time.time()-t0:.0f}s  -> output/{i['filename']}")
                return
        time.sleep(2.0)


if __name__ == "__main__":
    main()
