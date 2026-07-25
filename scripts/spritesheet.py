#!/usr/bin/env python3
"""Assemble pixel-art frames into a real sprite sheet with a SHARED palette.

  spritesheet.py f1.png f2.png ... [-s 64] [-c 16] [-u 6] [--cols N] [-o sheet.png]

Why shared palette: quantising each frame separately gives each its own colour set,
so the character subtly shifts hue between frames. A sprite sheet needs ONE palette.
"""
import argparse, os
from PIL import Image

ap=argparse.ArgumentParser()
ap.add_argument("frames",nargs="+")
ap.add_argument("-s","--size",type=int,default=64)
ap.add_argument("-c","--colors",type=int,default=16)
ap.add_argument("-u","--upscale",type=int,default=6)
ap.add_argument("--cols",type=int,default=0)
ap.add_argument("-o","--out",default=None)
a=ap.parse_args()

# 1) downscale every frame to the same cell size (BOX = area-average, kills grain)
cells=[]
for f in a.frames:
    im=Image.open(f).convert("RGB"); w,h=im.size
    sc=a.size/max(w,h)
    cells.append(im.resize((max(1,round(w*sc)),max(1,round(h*sc))), Image.BOX))
cw,ch=cells[0].size

# 2) derive ONE palette from all frames stacked together
strip=Image.new("RGB",(cw*len(cells),ch))
for i,c in enumerate(cells): strip.paste(c,(i*cw,0))
pal_src=strip.quantize(colors=a.colors, method=Image.MEDIANCUT, dither=Image.Dither.NONE)

# 3) apply that shared palette to each frame (no dithering)
cells=[c.quantize(palette=pal_src, dither=Image.Dither.NONE).convert("RGB") for c in cells]

# 4) lay out the grid
cols=a.cols or len(cells)
rows=(len(cells)+cols-1)//cols
sheet=Image.new("RGB",(cw*cols, ch*rows), cells[0].getpixel((0,0)))
for i,c in enumerate(cells):
    sheet.paste(c, ((i%cols)*cw, (i//cols)*ch))

out=a.out or "spritesheet.png"
sheet.resize((sheet.width*a.upscale, sheet.height*a.upscale), Image.NEAREST).save(out)
sheet.save(out.replace(".png","_raw.png"))
print(f"  {len(cells)} frames, cell {cw}x{ch}, grid {cols}x{rows}, {a.colors} shared colours")
print(f"  view   -> {out}")
print(f"  sheet  -> {out.replace('.png','_raw.png')}  ({sheet.width}x{sheet.height} game-ready)")
