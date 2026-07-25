#!/usr/bin/env python3
"""Objective 'is this really pixel art?' metric.

A true pixel-art image at 1024px is a 64px (or 128px) image scaled up by nearest
neighbour: every 16x16 block is ONE flat colour. So downscale->upscale with NEAREST
should be near-lossless. The residual is how far the model is from real pixel art.
Also counts distinct colours, which is what a fixed sprite palette needs to be small.
"""
import sys
from PIL import Image
import numpy as np

def report(path, grid=64):
    im = Image.open(path).convert("RGB")
    a = np.asarray(im).astype(np.float32)
    small = im.resize((grid, grid), Image.NEAREST)
    back = np.asarray(small.resize(im.size, Image.NEAREST)).astype(np.float32)
    rmse = float(np.sqrt(((a - back) ** 2).mean()))

    # in-block colour variance: 0 == every cell is one flat colour
    cell = a.shape[0] // grid
    blocks = a[:grid*cell, :grid*cell].reshape(grid, cell, grid, cell, 3)
    within = float(blocks.std(axis=(1, 3)).mean())

    colors = len(im.getcolors(maxcolors=1 << 24) or [])
    # colours that survive an honest 64px downsample
    dc = len(im.resize((grid, grid), Image.BOX).getcolors(maxcolors=1 << 24) or [])
    print(f"{path.split('/')[-1]:34s} grid-RMSE {rmse:6.2f}   in-cell-std {within:5.2f}   "
          f"colours {colors:>7,}   @64px {dc:>5,}")

for p in sys.argv[1:]:
    report(p)
