# TAPIZ -> Resolume Arena OSC mapping spec

Status: spec only, no code. Translates every field of the `system_status.json`
contract (source of truth: `tools/system_map.py::API_CONTRACT_SCHEMA`) into
Resolume Arena/Avenue 7 OSC addresses, value ranges, curves and a layer plan.
Written for a VJ operator building a Resolume composition by hand; an
external script (the "Tapiz bridge", not covered here -- any OSC-capable
tool: Python `python-osc`, Max/MSP, TouchDesigner, Pd) reads
`system_status.json` and sends the OSC messages described below.

## Who this is for / what you need

You are a VJ operator with Resolume Arena or Avenue 7 open, comfortable
adding layers, clips and video effects, and comfortable enabling OSC input
in Preferences. You do NOT need to read Python or JSON by hand -- this spec
gives you the exact addresses and formulas to wire a controller to. You DO
need to build the 5-layer composition described below once, and re-confirm
each OSC address in your own composition (effect slot numbers depend on the
order you add effects -- see "OSC input setup").

## OSC input setup (Resolume 7)

1. Open **Preferences > OSC**.
2. Enable **OSC Input**. Default input port: **7000**. Note the machine's
   IP if the bridge script runs on another computer on the LAN; use
   `127.0.0.1` / `localhost` if it runs on the same machine as Resolume.
3. Enable **OSC Output** too (default port **7001**). This makes Resolume
   echo back current parameter values, which you will use as a monitor
   while confirming addresses in step 4.
4. **Address discovery (do this before wiring anything):** right-click any
   parameter in the Resolume UI -- a layer's Opacity fader, an effect's
   Amount knob, a clip's trigger button -- and choose **Show OSC**. This
   reveals the exact address string for that parameter in YOUR composition,
   plus the value range Resolume expects over OSC (almost always normalized
   `0.0..1.0`, even when the UI shows a different unit -- e.g. a Rotation
   knob showing `-180..180 deg` is usually `0.0..1.0` over OSC with `0.5`
   = 0 degrees). Confirm every address in the tables below this way before
   pointing the bridge at it.
5. **Live monitor:** point an external OSC listener (Protokol by Hexler,
   OSCMonitor, or any UDP/OSC dump tool) at Resolume's OSC Output port
   (7001) while you move each parameter once by hand in the UI. You will
   see the exact address and the value it sends -- use this to sanity-check
   the formulas in this spec against your own composition before the
   automated feed takes over.
6. Effect slot numbers (`{E}` below, e.g. `effects/1`, `effects/2`) are
   positional: the first effect you drop on a layer's Video FX chain is
   slot 1, the second is slot 2, etc. If you reorder or delete effects, the
   addresses shift. Build the chains in the order given in the layer plan
   below and they will match the tables.
7. Layer numbers (`{L}`) and clip numbers (`{C}`) are whatever position you
   build them at in the Composition. This spec assumes the 5-layer order
   given below (Layer 1 = mesh ... Layer 5 = spores). If your composition
   uses different layer positions, substitute your own numbers everywhere.

## Layer plan

| Layer | Contract section | Role | Build |
|---|---|---|---|
| 1 | `luminous_mesh_densities` | Generative background mesh | One looping generative/particle/grid source clip (e.g. a plasma, cell or grid generator, or a slow-loop grid video). Video FX chain in this order: (1) **Transform** (Scale, Position), (2) **RGB Noise** or **Grain** (Amount), (3) **Strobe** or **Flicker** (Rate). Add a second clip on the same layer preloaded as an "overloaded" look (harsher color/texture) for the status trigger. |
| 2 | `chromatic_frequency_masks` | Censoring veil, full-frame overlay | One full-frame fog/vignette/solid-color source clip, blend mode **Add** or **Screen**, stacked above Layer 1. Video FX chain: (1) **Blur** (Amount), (2) **Hue, Saturation, Brightness** (Hue sub-param). Bypassed by default. |
| 3 | `chronological_collision_buffers` | Main content, jitters under collision | Your primary content/footage layer. Video FX chain: (1) **Transform** (Position X/Y, Rotation/Skew), (2) **Wobble** or an LFO-capable effect (Speed/Rate). Bypassed (effects off) when synchronized. |
| 4 | `meta` (sigil) | Always-on HUD label | One **Text** source clip, small, corner-anchored via its own Transform, blend **Normal**, opacity low-to-medium, always playing, top-most or on a dedicated always-visible layer. |
| 5 | `encoded_asset_payloads` | Spores, one clip per decoded asset | A bank of N clips, one per `asset_id` present in `payloads` (prep at least as many clip slots as `total_payloads` reports; add more as new assets appear). Each clip is a **Text** source, initially blank/idle. Optionally map each clip's Column to a matching Column-level trigger if you want a spore to also flash Layers 1-3 when exhumed. |

## Field mapping tables

Address placeholders: `{L}` = layer number, `{C}` = clip number, `{E}` =
effect slot number as built in the layer plan above.

### `meta`

| Field | OSC address | Value range mapping | Curve | Layer/effect |
|---|---|---|---|---|
| `ecosystem_version` | `/composition/layers/4/clips/1/video/source/params/lines` (string, line 1) | text, sent verbatim, e.g. `"TAPIZ v1.0.0"` | n/a (text) | Layer 4 Text source |
| `compilation_timestamp` | same address as `ecosystem_version`, line 2 | epoch float -> bridge formats as local/UTC readable string before sending | n/a (text, formatted by bridge) | Layer 4 Text source |
| `integrity_sigil` | same address as `ecosystem_version`, line 3 | 64-char SHA-256 hex -> bridge truncates to first 16 chars for on-screen legibility, prefixed `SIGIL ` | n/a (text, truncated by bridge) | Layer 4 Text source |
| `embedding_target` | N/A | DOM selector from the web renderer, has no Resolume equivalent | n/a | not mapped, informational only |

### `luminous_mesh_densities` (Layer 1 -- mesh)

| Field | OSC address | Value range mapping | Curve | Layer/effect |
|---|---|---|---|---|
| `global_pressure` | `/composition/layers/1/video/effects/1/params/scale` | `0.0..1.0` (pressure) -> `1.0..0.4` (scale) via `scale = 1.0 - pressure*0.6` | linear, inverse | Layer 1, Transform effect (slot 1), Scale |
| `css_variables.--mesh-luminosity` | `/composition/layers/1/video/opacity` | `0.0..1.0` -> `0.0..1.0` direct pass-through | linear | Layer 1, layer Opacity |
| `css_variables.--mesh-density-throttle` | `/composition/layers/1/video/effects/2/params/amount` | `0.0..1.0` (throttle) -> `1.0..0.0` (noise amount) via `amount = 1.0 - throttle` | linear, inverse | Layer 1, RGB Noise/Grain effect (slot 2), Amount |
| `css_variables.--mesh-glitch-frequency` | `/composition/layers/1/video/effects/3/params/rate` | `0.0..5.0` (raw Hz) -> `0.0..1.0` via `rate_osc = raw/5.0` | linear | Layer 1, Strobe/Flicker effect (slot 3), Rate |
| `throttle_ratio` | `/composition/layers/1/clips/1/video/speed` | `0.0..1.0` -> `0.25..1.0` (playback speed multiplier) via `speed = 0.25 + throttle_ratio*0.75` | linear | Layer 1, active clip Speed |
| `status` | `/composition/layers/1/clips/2/connect` (bang, value `1`) | `STABLE` -> no action (stay on clip 1); `OVERLOADED` -> fire once on the STABLE->OVERLOADED edge; fire `/composition/layers/1/clips/1/connect` once on the reverse edge | threshold, edge-triggered | Layer 1, alternate "overloaded" clip (slot 2) |

### `chromatic_frequency_masks` (Layer 2 -- mask)

| Field | OSC address | Value range mapping | Curve | Layer/effect |
|---|---|---|---|---|
| `max_risk_score` | `/composition/layers/2/video/opacity` | `0.0..100.0` -> `0.0..1.0` via `opacity = max_risk_score/100.0` | linear | Layer 2, layer Opacity |
| `css_filter_string` | N/A -- do not parse the CSS string over OSC | composite/derived value; already decomposed into the three rows below (`max_risk_score`, `mask_intensity`, and the Blur/Hue effects they drive) | n/a | reference only |
| `mask_intensity` | `/composition/layers/2/bypassed` (bool); `/composition/layers/2/video/effects/1/params/blur`; `/composition/layers/2/video/effects/2/params/hue` | `CLEAR` -> bypassed=`1`(true), blur=`0.0`, hue=`0.0`. `CAUTION` -> bypassed=`0`, blur=`max_risk_score/100.0`, hue=`0.0`. `CRITICAL` -> bypassed=`0`, blur=`max_risk_score/100.0`, hue=`0.5` (180 deg out of 360) | threshold (3-state) | Layer 2, layer bypass + Blur effect (slot 1) + Hue sub-param of HSB effect (slot 2) |
| `triggered_categories` | `/composition/columns/2/connect` (bang) when `len(triggered_categories) >= 1`; text mirrored to `/composition/layers/4/clips/1/video/source/params/lines` line 4 | list length gates the bang (fire once per rising edge from 0 to >=1 items); joined string (e.g. `"category_a, category_b"`) sent as text | threshold (bang) + text | Column 2 bang (optional cross-layer flash) + Layer 4 HUD text |

### `chronological_collision_buffers` (Layer 3 -- collisions)

| Field | OSC address | Value range mapping | Curve | Layer/effect |
|---|---|---|---|---|
| `collision_count` | `/composition/layers/3/video/effects/1/params/positionx` and `.../positiony` | `count` -> `amplitude_px = min(15, 3 + count*2)` -> `normalized_amplitude = amplitude_px/100.0` -> bridge alternates sending `0.5 + normalized_amplitude` and `0.5 - normalized_amplitude` each jitter cycle (0.5 = centered position in Resolume's normalized OSC range) | linear amplitude, alternating square/triangle wave | Layer 3, Transform effect (slot 1), Position X/Y |
| (derived from `collision_count`, same field) | `/composition/layers/3/video/effects/2/params/speed` | `count` -> `dur_s = max(0.1, 2.0 - count*0.3)` -> `hz = 1.0/dur_s` -> `normalized_speed = min(1.0, hz/10.0)` | linear (capped) | Layer 3, Wobble/LFO effect (slot 2), Speed/Rate |
| `css_keyframes_payload` | N/A -- do not send raw CSS keyframe text over OSC | composite/derived value; already decomposed into the `collision_count` rows above (amplitude + rate) | n/a | reference only |
| `animation_class` | N/A -- do not send raw CSS class text over OSC | composite/derived value; encodes the same duration already used to compute Speed above | n/a | reference only |
| `status` | `/composition/layers/3/bypassed` (bool) | `SYNCHRONIZED` -> `1` (true, bypassed/off); `TEMPORAL_DEGRADED` -> `0` (false, effects live) | threshold | Layer 3, layer bypass |
| `affected_assets` | `/composition/layers/4/clips/1/video/source/params/lines` line 5 | joined string of asset ids (e.g. `"ART-102"`), only sent/shown while `status == TEMPORAL_DEGRADED`; cleared when it resolves | text, present only if degraded | Layer 4 HUD text |

### `encoded_asset_payloads` (Layer 5 -- spores)

| Field | OSC address | Value range mapping | Curve | Layer/effect |
|---|---|---|---|---|
| `total_payloads` | N/A -- operational count, not sent as OSC | tells the operator how many of the pre-built clip slots on Layer 5 are active this cycle (`total_payloads` clips populated, any beyond that left idle/blank) | n/a | Layer 5, clip bank sizing |
| `payloads.<asset_id>.name` | `/composition/layers/5/clips/{C}/name` (string, optional/cosmetic) | text, sent verbatim; `asset_id`s mapped to clip index `{C}` in stable sort order (alphabetical by `asset_id`) | n/a (text) | Layer 5, clip `{C}` name field |
| `payloads.<asset_id>.intent` | N/A -- no dedicated Resolume field for a clip description | kept as bridge-side metadata only (log/label in the controller UI, not sent to Resolume) | n/a | not mapped |
| `payloads.<asset_id>.data_chunks` | `/composition/layers/5/clips/{C}/video/source/params/lines` (string), sent AFTER client-side decode | raw chunks are NEVER sent over OSC; the bridge decodes them first using `decodeChunk()` (`tools/system_map.py::CHUNK_DECODING_PROTOCOL_JS`, shift key 42) and sends only the resulting plaintext | n/a (text, decoded) | Layer 5, clip `{C}` Text source, Lines param |
| `payloads.<asset_id>.chunk_count` | N/A -- decode-progress bookkeeping only | used bridge-side to know how many chunks to wait for before decoding is complete; no Resolume mapping | n/a | not mapped |
| `payloads.<asset_id>.decode_shift_key` | N/A -- decode parameter only | always `42` per protocol; consumed by the bridge's decode step, never sent to Resolume | n/a | not mapped |
| `embedding_target` | N/A | DOM selector from the web renderer, has no Resolume equivalent | n/a | not mapped, informational only |
| `encoding_protocol` | N/A | confirms `"Base64_Shift42_Chunked"` is the decode protocol in use; informational only, verify it matches `system_map.py` before trusting a decode | n/a | not mapped |

Spore trigger (exhume action): when the operator (or an automated "exhume"
rule) wants to reveal spore `{C}`, the bridge first writes the decoded text
to `/composition/layers/5/clips/{C}/video/source/params/lines`, THEN fires
`/composition/layers/5/clips/{C}/connect` with value `1` (bang) to bring the
clip on air. Sending the trigger before the text write shows a blank clip.

## Worked example

Representative stress-state values (matches the shape of
`py tools/compete_engine.py --stress` output; exact numbers will vary run
to run):

```txt
meta.ecosystem_version = "1.0.0"
meta.compilation_timestamp = 1785012345.0
meta.integrity_sigil = "9f2ab6c1d84e70538a2c..." (64 hex chars)

luminous_mesh_densities.global_pressure = 1.0
luminous_mesh_densities.css_variables["--mesh-luminosity"] = 0.0
luminous_mesh_densities.css_variables["--mesh-density-throttle"] = 0.0067
luminous_mesh_densities.css_variables["--mesh-glitch-frequency"] = 5.0
luminous_mesh_densities.throttle_ratio = 0.0067
luminous_mesh_densities.status = "OVERLOADED"

chromatic_frequency_masks.max_risk_score = 100.0
chromatic_frequency_masks.css_filter_string = "blur(12px) saturate(0%) contrast(300%) hue-rotate(180deg)"
chromatic_frequency_masks.mask_intensity = "CRITICAL"
chromatic_frequency_masks.triggered_categories = ["category_a", "category_b"]

chronological_collision_buffers.collision_count = 3
chronological_collision_buffers.status = "TEMPORAL_DEGRADED"
chronological_collision_buffers.affected_assets = ["ART-102"]

encoded_asset_payloads.total_payloads = 1
encoded_asset_payloads.payloads["ART-100"] = { name: "Saturacion",
  intent: "Context annihilation", chunk_count: 1, decode_shift_key: 42 }
```

Resulting OSC messages the bridge sends (address, value):

```txt
# meta -> Layer 4 HUD text (single multi-line send)
/composition/layers/4/clips/1/video/source/params/lines
  "TAPIZ v1.0.0\n2026-07-10 14:32:25 UTC\nSIGIL 9f2ab6c1d84e7053"

# luminous_mesh_densities -> Layer 1
/composition/layers/1/video/effects/1/params/scale        0.4      # 1.0 - 1.0*0.6
/composition/layers/1/video/opacity                        0.0      # luminosity direct
/composition/layers/1/video/effects/2/params/amount         0.9933   # 1.0 - 0.0067
/composition/layers/1/video/effects/3/params/rate           1.0      # 5.0/5.0
/composition/layers/1/clips/1/video/speed                   0.255    # 0.25 + 0.0067*0.75
/composition/layers/1/clips/2/connect                        1        # OVERLOADED edge, bang

# chromatic_frequency_masks -> Layer 2
/composition/layers/2/video/opacity                          1.0      # 100/100
/composition/layers/2/bypassed                                0        # CRITICAL -> not bypassed
/composition/layers/2/video/effects/1/params/blur             1.0      # 100/100
/composition/layers/2/video/effects/2/params/hue               0.5      # CRITICAL -> 180deg
/composition/columns/2/connect                                  1        # 2 categories >=1, bang
/composition/layers/4/clips/1/video/source/params/lines (line 4 appended)
  "category_a, category_b"

# chronological_collision_buffers -> Layer 3
/composition/layers/3/video/effects/1/params/positionx        0.59     # 0.5 + 9/100, cycle A
/composition/layers/3/video/effects/1/params/positiony        0.41     # 0.5 - 9/100, cycle A
                                                                    # (next cycle: 0.41 / 0.59)
/composition/layers/3/video/effects/2/params/speed             0.0909   # (1/1.1)/10
/composition/layers/3/bypassed                                  0        # TEMPORAL_DEGRADED
/composition/layers/4/clips/1/video/source/params/lines (line 5 appended)
  "ART-102"

# encoded_asset_payloads -> Layer 5, clip 1 (asset ART-100)
/composition/layers/5/clips/1/name                             "Saturacion"
# on exhume click, after client-side decodeChunk() of data_chunks:
/composition/layers/5/clips/1/video/source/params/lines          "<decoded plaintext>"
/composition/layers/5/clips/1/connect                             1
```

## Notes for the operator

- All addresses above assume the layer/effect order in "Layer plan". If you
  build your composition differently, re-derive every address with **Show
  OSC** (step 4 of the setup section) before wiring the bridge.
- Resolume normalizes almost all float parameters to `0.0..1.0` over OSC
  regardless of the unit shown in its UI. Where this spec gives a formula
  producing values outside `0.0..1.0` (should not happen if you follow the
  formulas as written), clamp before sending -- Resolume will otherwise
  clamp silently, which can look like a stuck parameter.
- Fields marked N/A in the tables are intentionally not sent over OSC:
  either they are composite/derived (already decomposed into other rows),
  internal to the web renderer (`embedding_target`), or decode-only
  bookkeeping (`chunk_count`, `decode_shift_key`). Sending them anyway will
  not error, but Resolume has no parameter that consumes raw CSS or JSON
  strings meaningfully.
- Re-validate `system_status.json` against the contract before wiring a new
  feed: `py tools/system_map.py validate tools/dist/system_status.json`.
  This spec assumes a PASSing file; a failing one may be missing fields
  this mapping depends on.
