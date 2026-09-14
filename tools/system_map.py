"""
SYSTEM MAP: Architecture Blueprint
Ecosystem: Tapiz ↔ Psicosis ↔ Fungi
Version: 1.0.0
"""

API_CONTRACT_SCHEMA: dict = {
    "meta": {
        "_doc": "Ecosystem fingerprint",
        "ecosystem_version": "str",
        "compilation_timestamp": "float",
        "integrity_sigil": "str | SHA-256",
        "embedding_target": "str"
    },
    "luminous_mesh_densities": {
        "_doc": "Token pressure → UI throttle",
        "global_pressure": "float [0.0, 1.0]",
        "css_variables": {
            "--mesh-luminosity": "float",
            "--mesh-density-throttle": "float",
            "--mesh-glitch-frequency": "float"
        },
        "throttle_ratio": "float",
        "status": "str | OVERLOADED | STABLE"
    },
    "chromatic_frequency_masks": {
        "_doc": "Risk → visual filters",
        "max_risk_score": "float [0.0, 100.0]",
        "css_filter_string": "str",
        "mask_intensity": "str | CLEAR | CAUTION | CRITICAL",
        "triggered_categories": "list[str]"
    },
    "chronological_collision_buffers": {
        "_doc": "Race conditions → animations",
        "collision_count": "int",
        "css_keyframes_payload": "str",
        "animation_class": "str",
        "status": "str | SYNCHRONIZED | TEMPORAL_DEGRADED"
    },
    "encoded_asset_payloads": {
        "_doc": "Encoded decaying assets for deferred loading",
        "total_payloads": "int",
        "payloads": {
            "<asset_id>": {
                "name": "str",
                "intent": "str",
                "data_chunks": "list[str] | Base64+Shift42",
                "chunk_count": "int",
                "decode_shift_key": "int"
            }
        },
        "embedding_target": "str",
        "encoding_protocol": "str"
    }
}

VISUAL_ARCHITECTURE_MAP: dict = {
    "luminous_mesh_densities": {
        "engineering_concept": "Token consumption → UI quality",
        "spatial_metaphor": "Bioluminescent grid dims under pressure",
        "rendering_directive": "Bind CSS variables to grid opacity/resolution"
    },
    "chromatic_frequency_masks": {
        "engineering_concept": "Risk scoring → visual distortion",
        "spatial_metaphor": "Chromatic veil obscures content",
        "rendering_directive": "Apply CSS filters to main wrapper"
    },
    "chronological_collision_buffers": {
        "engineering_concept": "State conflicts → glitch animations",
        "spatial_metaphor": "Temporal tears in spacetime",
        "rendering_directive": "Inject keyframes, apply to affected elements"
    },
    "encoded_asset_payloads": {
        "engineering_concept": "Encoded assets for deferred loading",
        "spatial_metaphor": "Hidden data embedded in document",
        "rendering_directive": "Decode on interaction, render as overlay"
    }
}

FRONTEND_RENDERING_DIRECTIVES: str = """
1. Fetch dist/system_status.json
2. Render layers: void → mesh → content → animations → encoded payloads → sigil
3. Poll every 30s, re-render on sigil change
4. Respect prefers-reduced-motion
"""

CHUNK_DECODING_PROTOCOL_JS: str = """
function decodeChunk(chunks, shiftKey = 42) {
    const combined = chunks.join('');
    const shiftedBytes = Uint8Array.from(atob(combined), c => c.charCodeAt(0));
    let b64 = '';
    for (const b of shiftedBytes) b64 += String.fromCharCode((b - shiftKey + 256) % 256);
    const utf8 = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
    return new TextDecoder('utf-8').decode(utf8);
}
"""


# ---------------------------------------------------------------------------
# Validator: structural check of a system_status.json dict against the
# API_CONTRACT_SCHEMA above. Stdlib only.
# ---------------------------------------------------------------------------

def _base_type(annotation: str) -> str:
    """Extract the base type token from an annotation string.

    Examples: 'float [0.0, 1.0]' -> 'float'; 'str | SHA-256' -> 'str';
    'list[str] | Base64+Shift42' -> 'list[str]'.
    """
    token = annotation.split("|")[0].strip()
    # Strip range suffix like 'float [0.0, 1.0]' but keep 'list[str]'
    if " " in token:
        token = token.split(" ")[0].strip()
    return token


def _check_value(value, annotation: str, path: str, errors: list) -> None:
    base = _base_type(annotation)
    ok = True
    if base == "str":
        ok = isinstance(value, str)
    elif base == "float":
        ok = isinstance(value, (int, float)) and not isinstance(value, bool)
    elif base == "int":
        ok = isinstance(value, int) and not isinstance(value, bool)
    elif base == "list[str]":
        ok = isinstance(value, list) and all(isinstance(x, str) for x in value)
    else:
        errors.append("%s: unknown annotation '%s'" % (path, annotation))
        return
    if not ok:
        errors.append("%s: expected %s, got %s" % (path, base, type(value).__name__))


def _check_node(data, schema: dict, path: str, errors: list) -> None:
    if not isinstance(data, dict):
        errors.append("%s: expected dict, got %s" % (path, type(data).__name__))
        return
    placeholder_keys = [k for k in schema if k.startswith("<") and k.endswith(">")]
    if placeholder_keys:
        # Wildcard mapping: every value in data must match the placeholder schema
        sub_schema = schema[placeholder_keys[0]]
        for key, value in data.items():
            _check_node(value, sub_schema, "%s.%s" % (path, key), errors)
        return
    for key, spec in schema.items():
        if key == "_doc":
            continue
        child_path = "%s.%s" % (path, key)
        if key not in data:
            errors.append("%s: missing key" % child_path)
            continue
        value = data[key]
        if isinstance(spec, dict):
            _check_node(value, spec, child_path, errors)
        else:
            _check_value(value, spec, child_path, errors)


def validate(matrix: dict) -> dict:
    """Structurally validate a system_status.json dict against API_CONTRACT_SCHEMA.

    Returns a dict: section name -> list of error strings (empty list = PASS).
    """
    results = {}
    if not isinstance(matrix, dict):
        return {"<root>": ["expected dict, got %s" % type(matrix).__name__]}
    for section, schema in API_CONTRACT_SCHEMA.items():
        errors: list = []
        if section not in matrix:
            errors.append("%s: missing section" % section)
        else:
            _check_node(matrix[section], schema, section, errors)
        results[section] = errors
    return results


def _cmd_validate(json_path: str) -> int:
    import json
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            matrix = json.load(f)
    except (OSError, ValueError) as exc:
        print("ERROR: cannot load %s: %s" % (json_path, exc))
        return 2
    results = validate(matrix)
    failed = False
    for section, errors in results.items():
        status = "PASS" if not errors else "FAIL"
        print("[%s] %s" % (status, section))
        for err in errors:
            print("    - %s" % err)
        if errors:
            failed = True
    return 1 if failed else 0


def _cmd_show() -> int:
    print("FRONTEND_RENDERING_DIRECTIVES:")
    print(FRONTEND_RENDERING_DIRECTIVES.strip())
    print()
    print("VISUAL_ARCHITECTURE_MAP:")
    for section, info in VISUAL_ARCHITECTURE_MAP.items():
        print("  %s:" % section)
        for key, value in info.items():
            print("    %s: %s" % (key, value))
    print()
    print("CHUNK_DECODING_PROTOCOL_JS:")
    print(CHUNK_DECODING_PROTOCOL_JS.strip())
    return 0


def main(argv=None) -> int:
    import sys
    # Windows cp1252 console guard: contract strings contain non-ASCII glyphs
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(errors="replace")
        except (ValueError, OSError):
            pass
    args = list(sys.argv[1:] if argv is None else argv)
    usage = "usage: py tools/system_map.py {validate <path-to-json> | show}"
    if not args:
        print(usage)
        return 2
    cmd = args[0]
    if cmd == "show":
        return _cmd_show()
    if cmd == "validate":
        if len(args) < 2:
            print(usage)
            return 2
        return _cmd_validate(args[1])
    print(usage)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())