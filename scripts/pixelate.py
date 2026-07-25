#!/usr/bin/env python3
"""Snap a diffusion 'pixel-art-style' image onto a REAL pixel grid + fixed palette.

  pixelate.py in.png [-s 64] [-c 24] [-u 8] [-o out.png]
    -s  target pixel-grid size (longest side), e.g. 64 = 64px sprite
    -c  palette colours (0 = keep full colour)
    -u  upscale factor for viewing (nearest-neighbour, keeps hard edges)
"""
import argparse, os
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("-s","--size",type=int,default=64)
ap.add_argument("-c","--colors",type=int,default=24)
ap.add_argument("-u","--upscale",type=int,default=8)
ap.add_argument("-o","--out",default=None)
a = ap.parse_args()

im = Image.open(a.src).convert("RGB")
w,h = im.size
scale = a.size/max(w,h)
tw,th = max(1,round(w*scale)), max(1,round(h*scale))

# 1) downscale with BOX (area-average) — averaging suppresses grain before quantising
small = im.resize((tw,th), Image.BOX)

# 2) quantise to a fixed palette. dither=NONE is essential: dithering re-introduces
#    the speckle we just removed and is exactly what ruins AI pixel art.
if a.colors > 0:
    small = small.quantize(colors=a.colors, method=Image.MEDIANCUT,
                           dither=Image.Dither.NONE).convert("RGB")

# 3) upscale with NEAREST so pixels stay hard-edged
big = small.resize((tw*a.upscale, th*a.upscale), Image.NEAREST)

out = a.out or os.path.splitext(a.src)[0] + f"_px{a.size}c{a.colors}.png"
big.save(out)
small.save(out.replace(".png","_raw.png"))   # true 1:1 sprite, game-ready
print(f"  grid {tw}x{th}  colours {a.colors or 'full'}")
print(f"  view  -> {out}")
print(f"  sprite-> {out.replace('.png','_raw.png')}  (actual {tw}x{th} asset)")
