#!/usr/bin/env python3
"""Extract verbatim H3 prompt examples into corpus/examples.json.

Sources are MiniMax's own docs, kept alongside in corpus/: the two prompt
writing guides and the model README. Everything here is quoted exactly — these
become few-shot examples, so paraphrasing would teach the wrong format.
"""
import html
import json
import re
from pathlib import Path

CORPUS = Path(__file__).resolve().parents[1] / "corpus"
examples = []


def add(mode, note, text, source):
    examples.append({"mode": mode, "note": note,
                     "prompt": text.strip(), "source": source})


# --- the four worked cases in the base guide ---------------------------
base = (CORPUS / "VIDEO_PROMPT_WRITING_GUIDE_base_en.md").read_text()
case_meta = {
    "Case 1": ("T2VA", "Text only: two shots, dialogue carrying across the cut"),
    "Case 2": ("I2VA", "First frame anchor, then forward development"),
    "Case 3": ("FL2VA", "Single shot interpolating first to last frame; music N/A"),
    "Case 4": ("L2VA", "Infers an earlier state that lands on the final frame"),
}
for header, (mode, note) in case_meta.items():
    m = re.search(rf"### {header}:.*?```text\n(.*?)```", base, re.S)
    if m:
        add(mode, note, m.group(1), "VIDEO_PROMPT_WRITING_GUIDE_base_en.md")

# --- production prompts embedded in the README shell examples ----------
readme = html.unescape((CORPUS / "MiniMax-H3-README.md").read_text())
readme_notes = [
    ("Long-form cinematic T2VA: dense visual detail, strong camera work"),
    ("Long-form I2VA: static shot with a focus pull, layered soundscape"),
    ("Reference-to-video using the labelled reference schema"),
]
found = re.findall(r'"prompt":\s*"((?:[^"\\]|\\.)*integrated_multimodal_description.*?)"\s*[,\n}]',
                   readme, re.S)
for i, raw in enumerate(found):
    text = raw.encode().decode("unicode_escape")
    mode = "T2VA"
    if "<Picture 1>" in text or "reference picture" in text.lower():
        mode = "I2VA"
    if "subject_definitions" in text or "retention_analysis" in text:
        mode = "Ref2VA"
    note = readme_notes[i] if i < len(readme_notes) else "README production example"
    add(mode, note, text, "MiniMax-H3 README.md")

# --- (raw brief -> expanded prompt) pairs -------------------------------
# MiniMax ships the user brief that produced each published example. These are
# the only known input/output pairs, so they are the best few-shot data we have:
# they teach the transformation, not just the output shape.
SCRIPTS = CORPUS / "minimax_scripts"
pairs = []


def brief_from(script):
    """Pull the raw user prompt out of a context-ir request script."""
    src = (SCRIPTS / script).read_text()
    hits = re.findall(r'"(?:prompt|user_prompt|text)"\s*:\s*"((?:[^"\\]|\\.)*)"', src)
    return hits[0].encode().decode("unicode_escape").strip() if hits else None


brief = brief_from("full-2k-t2va-h3-context-ir.sh")
target = next((e for e in examples
               if e["mode"] == "T2VA" and "starship" in e["prompt"]), None)
if brief and target:
    pairs.append({"mode": "T2VA", "seconds": 10,
                  "brief": brief, "prompt": target["prompt"],
                  "source": "MiniMax reproducible scripts + README"})

(CORPUS / "pairs.json").write_text(json.dumps(pairs, indent=2, ensure_ascii=False))
print(f"wrote pairs.json — {len(pairs)} brief->prompt pairs")
for p in pairs:
    print(f"  {p['mode']}: {len(p['brief'].split())}w brief -> {len(p['prompt'].split())}w prompt")

out = CORPUS / "examples.json"
out.write_text(json.dumps(examples, indent=2, ensure_ascii=False))

print(f"wrote {out} — {len(examples)} examples")
for e in examples:
    words = len(e["prompt"].split())
    print(f"  {e['mode']:<7} {words:>4}w  {e['note'][:58]}")
