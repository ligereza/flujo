# Certified identity: what it bought, and the two things I got wrong

Stage record for the work that removed `hash_state='pending'` as the upstream
cause of weak evidence in the project reconstruction. Written after the
measurements, including the ones that went against the design.

## The fact that was missing, named by the code that needed it

Two consumers had stopped at the same place and both said so in their own words.

`project_reconstruction.cross_root_relations`:

> a sample is not an identity: two files can agree on a sample and differ in
> full content. Therefore a shared sample hash never decides project identity
> here; it produces an explicit tie with both alternatives preserved.
>
> `tie_breaker_needed`: compute full_sha256 for the overlapping assets

`show_asset_usage`, in its declared limits:

> full_sha256 existe para 112 de 45536 assets del indice, asi que la
> verificacion por contenido no esta disponible para el 99,75 %

The index carried `hash_state='pending'` for 45424 of 45536 assets. Everything
downstream was compensating for one absent fact with a path heuristic:

```python
library_signature = bool(feature.uuid_token) and feature.assets_kind is not None
```

## What was measured

| | before | after |
| --- | --- | --- |
| assets with real content identity | 112 | 4216 |
| sample-hash ties left undecided | 1348 groups / 4104 assets | 1 group |
| certified duplication | not provable | 56.85 GiB |
| root pairs with proven shared content | 0 | 126 |
| operator questions | 8273 raw rows | 6 |

The 6 questions cover 93.2% of the disputed bytes. The other 44 are deferred with
a `reopen_when` that fires on a query naming either root, so a deferred question
is distinguishable from an answered one.

Only 4104 files were hashed, not 45536. The dispute was over those 4104; opening
the rest would have read 776 GiB to learn nothing that any question needed.

### The 7 that were not duplicates

Seven assets shared a sample hash and differed in full content, all of them
consecutive frames in `LYON/3/123_flip_fluid_cache/bakefiles/`. A numbered
simulation cache writes identical headers into every frame, which is exactly
where a prefix sample lies. The index's refusal to decide was conservative and
correct 0.17% of the time.

### Where the saving actually landed

24 classes are a copy loose at the top of the disk while the same bytes sit
inside a folder. 21 of those are safe proposals; **3 are held because the
Resolume composition `sampier` names `2.mov`, `3.mov` and `4.mov` by path**.
Removing them would have broken a show that has already been played.

The check is by basename, so it can produce a false HOLD but never a false SAFE.
That direction is not a detail: it is the only direction in which a cheap check
is allowed to decide anything.

## Error 1: the escalation bought nothing, and I can say why

The design read a 64 KiB tail before paying for the whole file, on the reasoning
that a cheap disagreement certifies difference. Predicted saving: large.

Measured: **stage 1 resolved zero distinctions.** It read 197 MB and the run
still paid the full 107.8 GiB. Read amplification avoided: 1.0x. The escalation
cost 0.2% and returned nothing.

The reason is a property of this corpus that the design did not anticipate: video
containers and simulation caches have structured, often identical, tails. Even
the 7 genuinely different fluid-cache frames had matching tails and had to go to
stage 2. The right cheap discriminator here would have been a block from the
middle, where content actually varies.

Kept in the tool rather than removed, because on a corpus of documents or images
the tail is where content ends and the saving would be real. What is recorded is
that it is not free and that here it was not worth it.

## Error 2: I inflated ownership evidence with basename matching

The `.blend` reader extracts what a file declares it opens. 873 of 928 files were
readable; 63638 declarations, 7516 of them images.

A first pass classified 135 of 873 as "integrated into this disk" because a file
with the declared basename existed somewhere in the corpus. That produced 213
apparent refutations of the existing path heuristic.

The refutations were mine, not the heuristic's. Measured:

```
51 blends declare  fbd.png
29 blends declare  normal.jpg
25 blends declare  defaultmaterial_roughness.jpg
```

Dozens of separately purchased materials ship a file with the same generic name.
Under strict resolution -- a `//` path checked against the .blend's own directory
-- the counts are:

| | strict path check |
| --- | --- |
| all declarations point elsewhere | 771 (83.1%) |
| self-contained purchased asset | 77 (8.3%) |
| unreadable, DECODER_LIMIT | 55 (5.9%) |
| no external dependencies | 14 (1.5%) |
| **declares something OUTSIDE its own folder** | **11 (1.2%)** |

The measurement had to be corrected three times, and each correction reduced my
claim:

1. **basename anywhere in the corpus** -> 135 integrated. Wrong: generic names
   resolve against other people's purchased materials.
2. **relative path exists on disk** -> 88 integrated, 3 apparent refutations of
   the path heuristic. Still wrong: the 3 were `SCD/assets/models/...` folders
   whose `//caches/*.vdb` resolves because the VENDOR shipped the cache inside
   the asset. A self-contained purchase has resolving relative paths too.
3. **relative path resolves OUTSIDE the .blend's own folder** -> 11 files.

Only the third is integration. So:

| | |
| --- | --- |
| rows where heuristic and evidence agree | 725 |
| rows that gain a verdict the heuristic had none for | 40 |
| rows where the evidence contradicts the heuristic | **0** |

The path heuristic was not refuted anywhere. Put in tension against an
independent authority, it won.

### What the .blend reader actually bought

Not ownership. **57 proven dependency edges from 11 files**, and they are edges
nothing else on this disk can find, because they are not copies:

```
SUERTE/TREBOL.blend        -> DREFMOVISTAR/textures/leather_red_02_*
SCD/cityhigh.blend         -> MARLONLOLLA/LT26/dedia.png
cloth/CLOTH1.blend         -> KHELL/12.png
LYON/1/CIUDAD/SCENE DEMO 2K.blend -> LYON/1/GALAXIA/Aurora 8k.hdr
                                  -> LYON/1/nissan-skyline.../Textures/*
```

Three of those cross container roots. `cross_root_relations` could not have
found them: they are dependency, not identity, and the lexical gate would not
have compared `SCD` with `MARLONLOLLA` anyway. `LYON/1/GALAXIA/Galaxies 8k.hdr`
is opened by two different .blend files in two different folders, which makes it
a shared library item **by who references it** rather than by having a uuid in
its path.

They also became a second veto on the safe actions, and this one is exact rather
than by basename: a `//` declaration resolves against a known directory. It
vetoed nothing here -- 0 of 21 proposals clash -- which is itself the result.

## The asymmetry, for the sixth time

Rejection propagates, acceptance does not. It has now appeared in six unrelated
places:

1. containment bounds in the ray-tracing experiment
2. conservative summaries in the certified engine
3. folding under indistinction
4. coarse answers in refinement
5. a cheap digest that may refute identity but never confirm it
6. a foreign Windows account in a `.blend`'s save path, which rejects sole
   authorship while the operator's own account would not establish it

The sixth is why ownership was measured by whether declared paths resolve rather
than by whose account name appears. 127 distinct accounts appear across 362
files; none of them is evidence of authorship on its own.

## What is still unknown

- Ownership for the 231 blends whose declarations resolve only by basename. The
  remedy is strict resolution against sibling directories, not more names.
- Whether the 55 unreadable `.blend` files declare anything. 37 carry a header
  this reader rejects; that is DECODER_LIMIT, not absence.
- The two readings of a shared output. Content cannot separate "one work filed
  twice" from "an output reused in a second commission", and it should not try.
  Six questions, sorted by leverage, are the whole ask.
- Whether a source to export chain exists for 3D. `.blend` declares its inputs;
  nothing measured here follows a render forward to a delivered file.
