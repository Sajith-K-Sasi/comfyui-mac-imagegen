# Original generations

Full-resolution outputs behind the claims in the write-up. Renamed for clarity;
otherwise untouched.

**Each PNG contains its complete ComfyUI workflow** — prompt, model files, sampler,
scheduler, steps and seed. Drag one onto the ComfyUI canvas and the exact workflow
that produced it reconstitutes. That makes every claim here reproducible, not just
illustrated.

Read the settings without ComfyUI:

```python
import json
from PIL import Image
workflow = json.loads(Image.open("pipeline-2-edit-klein.png").info["prompt"])
```

| File | Shows |
|---|---|
| `pipeline-1-create-zimage.png` | Stage 1 — Z-Image, 8 steps, 99s |
| `pipeline-2-edit-klein.png` | Stage 2 — Klein + reference, one cat added, 66s |
| `pipeline-3-upscale-2048.png` | Stage 3 — 2048×2048, 391s |
| `steps-4-sticker-clean.png` | Klein 4 steps — four clean stickers |
| `steps-8-sticker-invented-captions.png` | Klein 8 steps — fabricated caption text |
| `steps-4-ui-clean.png` | Klein 4 steps — one frame, one tab bar |
| `steps-8-ui-duplicated-tabbars.png` | Klein 8 steps — ghost text, two tab bars |
| `controlnet-canny-map.png` | The edge map used as control input |
| `controlnet-strength-1.0.png` | Content locked — still a coffee shop |
| `controlnet-strength-0.7.png` | Hybrid — books appearing |
| `controlnet-strength-0.5.png` | Bookshop, room geometry intact |
| `controlnet-strength-0.3.png` | Bookshop, geometry loosened |
| `controlnet-sprite-pose.png` | Same pose, different character |

The sticker and UI pairs share a seed and differ only in step count, so the
artefacts are attributable to steps alone. The ControlNet set shares one control
image and seed, varying only strength.

Not included: the other ~240 generations (329 MB) from the benchmark suites. The
composite figures in `../images/` cover those.
