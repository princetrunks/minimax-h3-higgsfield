#!/usr/bin/env bash
# Integrity check for MiniMax H3 weights.
#
# Some community quantisation repos ship .safetensors with bytes appended past
# the end of the declared tensor data. ComfyUI's loader rejects those files, and
# their presence means the file was modified after it was built. Run this on
# anything you download from a third-party repo.
#
# Usage: verify_models.sh [/path/to/ComfyUI]
set -euo pipefail
COMFY="${1:-$(cd "$(dirname "$0")/.." && pwd)/ComfyUI}"

if [ ! -d "$COMFY/models" ]; then
    echo "No models directory under $COMFY"
    echo "Usage: verify_models.sh /path/to/ComfyUI"
    exit 1
fi

COMFY="$COMFY" python3 - <<'PY'
import glob, json, os, struct

root = os.environ['COMFY']
files = sorted(glob.glob(os.path.join(root, 'models', '*', '*.safetensors')))
if not files:
    print('No .safetensors found.')

for f in files:
    name = os.path.basename(f)
    size = os.path.getsize(f)
    try:
        with open(f, 'rb') as fh:
            n = struct.unpack('<Q', fh.read(8))[0]
            hdr = json.loads(fh.read(n))
            fh.seek(-80, 2)
            tail = fh.read()
    except Exception as e:
        print(f'FAIL     {name}: {e!r:.80}')
        continue

    end = max(v['data_offsets'][1] for k, v in hdr.items() if k != '__metadata__')
    extra = size - (8 + n + end)
    marker = b'bypass' in tail

    if extra < 0:
        pct = 100.0 * size / (8 + n + end)
        print(f'PARTIAL  {name}: {pct:.1f}% downloaded')
    elif marker or extra > 0:
        print(f'TAMPERED {name}: {extra} trailing bytes past the tensor data')
    else:
        print(f'OK       {name}: {len(hdr)} tensors, clean')
PY
