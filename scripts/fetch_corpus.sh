#!/usr/bin/env bash
# Fetch MiniMax's own H3 prompt-writing guides and build the few-shot corpus.
#
# These files are NOT redistributed with this repo — MiniMax ships H3 under a
# custom community licence, so we pull them from the source at setup time.
# Nothing here is required for H3 Studio to run; without a corpus the prompt
# assistant still works, it just has fewer examples to imitate.
set -euo pipefail

REPO="https://huggingface.co/MiniMaxAI/MiniMax-H3/resolve/main"
DEST="$(cd "$(dirname "$0")/.." && pwd)/corpus"
mkdir -p "$DEST/minimax_scripts"

echo "Fetching MiniMax prompt guides into $DEST"
for f in docs/VIDEO_PROMPT_WRITING_GUIDE_base_en.md \
         docs/VIDEO_PROMPT_WRITING_GUIDE_ref_en.md; do
    curl -fsSL "$REPO/$f" -o "$DEST/$(basename "$f")"
    echo "  $(basename "$f")"
done

curl -fsSL "$REPO/README.md" -o "$DEST/MiniMax-H3-README.md"
echo "  MiniMax-H3-README.md"

# The reproducible request scripts carry the raw user briefs that produced the
# published examples — the only known (brief -> expanded prompt) pairs.
for f in full-2k-t2va-h3-context-ir full-2k-i2va-h3-context-ir \
         full-2k-ref2va-h3-context-ir; do
    curl -fsSL "$REPO/scripts/readme/$f.sh" \
         -o "$DEST/minimax_scripts/$f.sh" || echo "  (skipped $f)"
done
echo "  reproducible scripts"

echo
echo "Building corpus…"
python3 "$(dirname "$0")/build_corpus.py"
