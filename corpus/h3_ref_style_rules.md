# H3 reference-mode (Ref2VA) prompt rules

Condensed from MiniMax's `VIDEO_PROMPT_WRITING_GUIDE_ref_en.md`. Reference mode
is a **different checkpoint and a different output schema** from T2VA/FL2VA — do
not mix the two formats.

## Output shape

Six labelled sections, in this order, each label on its own line with the
content starting on the next line, and a blank line between sections:

```
subject_definitions:
<Subject 1> is …

summary:
[reference generation] …

retention_analysis:
<Subject 1> (appears in [Shot 1]): fully_preserved - …

detailed_description:
[Shot 1] …

overall_soundscape:
…

non_diegetic_music:
…
```

Note the body field is `detailed_description`, **not**
`integrated_multimodal_description`. No preamble, no markdown, no commentary.

## Reference labels

| Label | Meaning |
| --- | --- |
| `<Subject N>` | reusable visible content — a person, animal, object, outfit, scene or style |
| `<Picture N>` | an image used as a literal frame or composition anchor |

`<Subject N>` is the one that matters here. An attached photo becomes
`<Picture N>`, and the person or thing *in* it becomes `<Subject N>`. Do not
create a standalone `<Picture N>` entry when the image only defines a
character — cite it inside the subject definition instead:

> `<Subject 1>` is the bearded man in `<Picture 1>`, with a shaved head, a
> weathered canvas jacket and a chipped enamel mug.

Give every subject three or four concrete, checkable visual attributes. Those
attributes are what identity retention is scored against, so vague definitions
("a man in casual clothes") produce vague likeness.

## summary

One short paragraph, opening with a bracketed task type. For photo references
that are not literal frames, the type is `[reference generation]`. Use the
labels already defined; introduce no new ones.

## retention_analysis

One line per label, saying where it appears and how faithfully it is kept. The
relationship markers are fixed literals:

`fully_preserved` · `partially_preserved` · `attribute_transfer` ·
`weak_reference`

> `<Subject 1>` (appears in [Shot 1], [Shot 2]): fully_preserved - the long dark
> hair, blue cardigan and silver necklace are retained.

Use `fully_preserved` when the subject should look like the photo. Adding new
actions or backgrounds is not a loss of fidelity — do not downgrade the marker
for that.

## detailed_description

Same shot, camera, speaker and dialogue grammar as the base guide: `[Shot 1]`
untimestamped, later cuts with strictly increasing times, the controlled camera
vocabulary, `(S1)` speaker IDs, `<d>[Language] …</d>` for spoken words.

The difference is that subjects are referred to **by label and description
together** on each appearance:

> `<Subject 1>` (S1), the young woman with long dark hair and a blue cardigan,
> leans toward the window.

Repeating the attributes at each appearance is deliberate, not redundant — it is
what holds identity across shots.

An optional style line may precede `[Shot 1]` on its own line.

## overall_soundscape and non_diegetic_music

Unchanged from the base guide. Ambient and physical sound in the first, score
only the audience hears in the second, `N/A` where there is none. Never repeat
dialogue from `detailed_description` in either.

## Framing note

Fine facial detail is limited by how many latent cells the face occupies. The
video VAE plus patchification gives an effective 32x spatial reduction, so a
face in a wide shot lands on a couple of cells and renders as mush. When the
brief is about a person's likeness, prefer medium shots and close-ups over wide
establishing shots — it is the single cheapest way to make a subject reference
actually look like the reference.
