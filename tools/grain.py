#!/usr/bin/env python3
"""Estimate image GRAIN (high-frequency noise), not sharpness.

Immerkaer noise estimator: convolve with a kernel that kills smooth gradients and
edges but passes pixel-level noise, then take a robust spread. Reported as sigma
in 0-255 units. Also reports 'flat-region sigma': the mean local std over the
smoothest 20% of the image, which is where grain is actually visible to the eye.
"""
import sys
import numpy as np
from PIL import Image

K = np.array([[1, -2, 1], [-2, 4, -2], [1, -2, 1]], dtype=np.float32)

def conv2(a, k):
    h, w = a.shape
    kh, kw = k.shape
    out = np.zeros((h - kh + 1, w - kw + 1), dtype=np.float32)
    for i in range(kh):
        for j in range(kw):
            out += k[i, j] * a[i:i + h - kh + 1, j:j + w - kw + 1]
    return out

def grain(path):
    im = Image.open(path).convert("RGB")
    a = np.asarray(im, dtype=np.float32)
    lum = a @ np.array([0.299, 0.587, 0.114], dtype=np.float32)

    # Immerkaer: sigma = sqrt(pi/2)/(6(W-2)(H-2)) * sum|conv|
    r = conv2(lum, K)
    sigma = float(np.sqrt(np.pi / 2) * np.abs(r).sum() / (6.0 * r.size))

    # local std over 8x8 blocks; grain shows in the FLAT blocks
    h, w = lum.shape
    bh, bw = h // 8, w // 8
    blocks = lum[:bh * 8, :bw * 8].reshape(bh, 8, bw, 8).transpose(0, 2, 1, 3).reshape(-1, 64)
    stds = blocks.std(axis=1)
    flat = float(np.sort(stds)[: max(1, len(stds) // 5)].mean())
    return sigma, flat

print(f"{'image':46s} {'noise-sigma':>11} {'flat-sigma':>10}")
for p in sys.argv[1:]:
    try:
        s, f = grain(p)
        print(f"{p.split('/')[-1]:46s} {s:11.3f} {f:10.3f}")
    except Exception as e:
        print(f"{p}: {e}")
