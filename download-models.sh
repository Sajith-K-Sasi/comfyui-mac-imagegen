#!/usr/bin/env bash
# Download every model needed by these workflows into a ComfyUI install.
#
#   ./download-models.sh /path/to/ComfyUI
#   ./download-models.sh /path/to/ComfyUI --core-only   # skip ControlNet (2.9 GB)
#
# Resumable: re-run it after an interruption and it picks up where it stopped.
#
# NOTE on the curl invocation: there is deliberately no --retry. curl's internal
# retry restarts the transfer and TRUNCATES the -o file, which silently destroys
# progress on multi-GB downloads. The outer loop retries instead, so -C - can
# actually resume from the last byte received.
set -uo pipefail

COMFY="${1:-}"
[ -z "$COMFY" ] && { echo "usage: $0 /path/to/ComfyUI [--core-only]"; exit 1; }
[ -d "$COMFY" ] || { echo "not a directory: $COMFY"; exit 1; }
CORE_ONLY=false
[ "${2:-}" = "--core-only" ] && CORE_ONLY=true

fetch() {  # fetch <url> <dest-dir> <filename>
  local url="$1" dir="$COMFY/$2" name="$3"
  local part="$dir/$name.part" final="$dir/$name"
  mkdir -p "$dir"
  if [ -f "$final" ]; then echo "  [have] $name"; return 0; fi

  local expected
  expected=$(curl -sIL "$url" | awk 'BEGIN{IGNORECASE=1}/^content-length:/{v=$2}END{gsub(/\r/,"",v);print v}')
  [ -z "$expected" ] && { echo "  [FAIL] could not reach $name"; return 1; }
  echo "  [get ] $name ($(( expected / 1048576 )) MB)"

  for attempt in $(seq 1 100); do
    local before=0; [ -f "$part" ] && before=$(stat -f%z "$part" 2>/dev/null || stat -c%s "$part")
    curl -L -C - --connect-timeout 30 --max-time 3600 \
         --speed-limit 2048 --speed-time 120 \
         --progress-bar -o "$part" "$url" || true
    local after=0; [ -f "$part" ] && after=$(stat -f%z "$part" 2>/dev/null || stat -c%s "$part")
    if [ "$after" -ge "$expected" ]; then mv "$part" "$final"; echo "  [ok  ] $name"; return 0; fi
    [ "$after" -eq "$before" ] && { echo "         stalled, retrying (attempt $attempt)"; sleep 10; }
  done
  echo "  [FAIL] $name incomplete"; return 1
}

HF=https://huggingface.co

echo "==> diffusion models (the two image models)"
fetch "$HF/unsloth/FLUX.2-klein-4B-GGUF/resolve/main/flux-2-klein-4b-Q8_0.gguf" \
      models/diffusion_models flux-2-klein-4b-Q8_0.gguf
fetch "$HF/gguf-org/z-image-gguf/resolve/main/z-image-turbo-q6_k.gguf" \
      models/diffusion_models z-image-turbo-Q6_K.gguf

echo "==> text encoder (ONE file, shared by both models)"
fetch "$HF/worstplayer/Z-Image_Qwen_3_4b_text_encoder_GGUF/resolve/main/Qwen_3_4b-Q6_K.gguf" \
      models/text_encoders Qwen_3_4b-Q6_K.gguf

echo "==> VAEs (one per model, NOT interchangeable)"
fetch "$HF/Comfy-Org/flux2-dev/resolve/main/split_files/vae/flux2-vae.safetensors" \
      models/vae flux2-vae.safetensors
fetch "$HF/Comfy-Org/z_image_turbo/resolve/main/split_files/vae/ae.safetensors" \
      models/vae z_image_ae.safetensors

echo "==> upscaler"
fetch "$HF/Comfy-Org/Real-ESRGAN_repackaged/resolve/main/RealESRGAN_x4plus.safetensors" \
      models/upscale_models RealESRGAN_x4plus.safetensors

if [ "$CORE_ONLY" = false ]; then
  echo "==> ControlNet (optional, 2.9 GB — skip with --core-only)"
  fetch "$HF/alibaba-pai/Z-Image-Turbo-Fun-Controlnet-Union/resolve/main/Z-Image-Turbo-Fun-Controlnet-Union.safetensors" \
        models/model_patches Z-Image-Turbo-Fun-Controlnet-Union.safetensors
fi

echo
echo "Done. Copy workflows/*.json into $COMFY/user/default/workflows/ and restart ComfyUI."
