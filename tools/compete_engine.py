"""
COMPLETE ENGINE: Monolithic Pipeline
Ecosystem: Tapiz ↔ Psicosis ↔ Fungi
Version: 1.0.0
"""
import argparse
import sys, json, base64, hashlib, math, time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Optional

CONTEXT_WINDOW_LIMIT = 32000
BASE_CHARS_PER_TOKEN = 4.0
ASCII_PENALTY_MULTIPLIER = 4.5
ASCII_DENSITY_THRESHOLD = 0.30
ENCODE_SHIFT_KEY = 42
CHUNK_SIZE = 256
# Resolve output next to this script, never relative to whatever cwd the
# caller happens to be in (Windows: 'py tools\\compete_engine.py' from repo root).
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "dist"
OUTPUT_FILENAME = "system_status.json"
ECOSYSTEM_VERSION = "1.0.0"


def _harden_console():
    """Avoid UnicodeEncodeError on Windows cp1252 consoles when the pipeline
    prints asset names/content containing block glyphs or other non-ASCII."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass  # non-reconfigurable stream (pipes, test capture) -- fine

class EntityState(Enum):
    DORMANT = "dormant"
    ACTIVE = "active"
    DECAYING = "decaying"
    PURGED = "purged"

class RiskLevel(Enum):
    SAFE = "safe"
    CAUTION = "caution"
    CRITICAL = "critical"

@dataclass
class MetadataLayer:
    conceptual_intent: str
    tags: List[str]
    is_artistic_context: bool = True

@dataclass
class ArtAsset:
    asset_id: str
    name: str
    content: str
    metadata: MetadataLayer
    state: EntityState = EntityState.DORMANT
    last_modified: float = field(default_factory=time.time)

    def calculate_symbol_density(self) -> float:
        if not self.content: return 0.0
        total = len(self.content)
        if total == 0: return 0.0
        non_alnum = sum(1 for c in self.content if not c.isalnum() and not c.isspace())
        return non_alnum / total

@dataclass
class EcosystemState:
    active_assets: Dict[str, ArtAsset] = field(default_factory=dict)
    decaying_assets: Dict[str, ArtAsset] = field(default_factory=dict)
    event_log: List[Dict[str, Any]] = field(default_factory=list)

    def transition_to_fungi(self, asset_id: str) -> bool:
        """Atomically move an asset from Tapiz (active) into Fungi (decaying).

        Strips the 'active_render' tag before the move (the state-lock the
        ConcurrencyLogicAnalyzer prescribes against Decay-Render races),
        marks the asset DECAYING and logs the event. Returns False if the
        asset is not in the active set."""
        if asset_id not in self.active_assets:
            return False
        asset = self.active_assets.pop(asset_id)
        asset.metadata.tags = [t for t in asset.metadata.tags if t != "active_render"]
        asset.state = EntityState.DECAYING
        asset.last_modified = time.time()
        self.decaying_assets[asset_id] = asset
        self.event_log.append({
            "time": asset.last_modified,
            "event": "decay_initiated",
            "asset": asset_id,
        })
        return True

class TokenVolumetricAnalyzer:
    def __init__(self, context_limit=CONTEXT_WINDOW_LIMIT):
        self.context_limit = context_limit

    def analyze_asset(self, asset: ArtAsset) -> Dict[str, Any]:
        length = len(asset.content)
        density = asset.calculate_symbol_density()
        is_heavy = density > ASCII_DENSITY_THRESHOLD
        base = length / BASE_CHARS_PER_TOKEN
        tokens = int(base * ASCII_PENALTY_MULTIPLIER) if is_heavy else int(base)

        risk = "HIGH" if tokens > self.context_limit * 0.5 else "MEDIUM" if tokens > self.context_limit * 0.25 else "LOW"
        return {
            "asset_id": asset.asset_id, "raw_chars": length,
            "symbol_density": round(density, 4), "estimated_tokens": tokens,
            "context_overflow_risk": risk,
            "recommendation": "Refactor to external links" if risk == "HIGH" else "Acceptable"
        }

class GuardrailSimulationAnalyzer:
    LEXICON = {
        "violence": ["kill", "blood", "gore", "psycho", "psicosis", "murder", "weapon"],
        "decay_gross": ["trash", "basurero", "rot", "fungi", "decay", "slime", "waste", "corpse"],
        "self_harm": ["cut", "die", "suicide", "pain", "suffer"]
    }
    MITIGATION = 0.70
    WEIGHT = 15

    def analyze_asset(self, asset: ArtAsset) -> Dict[str, Any]:
        text = (asset.content + " " + " ".join(asset.metadata.tags)).lower()
        triggered, hits = [], 0
        for cat, words in self.LEXICON.items():
            if any(w in text for w in words):
                triggered.append(cat)
                hits += sum(text.count(w) for w in words)

        base = min(100.0, hits * self.WEIGHT)
        mitigation = self.MITIGATION if asset.metadata.is_artistic_context else 0.0
        final = max(0.0, base * (1.0 - mitigation))
        level = RiskLevel.CRITICAL if final > 70 else RiskLevel.CAUTION if final > 30 else RiskLevel.SAFE

        return {
            "asset_id": asset.asset_id, "triggered_categories": triggered,
            "raw_hits": hits, "artistic_context_mitigation": f"{mitigation*100:.0f}%",
            "final_risk_score": round(final, 1), "risk_level": level.value,
            "recommendation": "Add context prompts" if level != RiskLevel.SAFE else "Clear"
        }

class ConcurrencyLogicAnalyzer:
    GRACE_PERIOD = 60.0
    THRESHOLD = 10

    def analyze_ecosystem(self, state: EcosystemState) -> Dict[str, Any]:
        races, flaws = [], []
        overlap = set(state.active_assets) & set(state.decaying_assets)
        if overlap:
            flaws.append(f"State violation: {list(overlap)} in both sets")

        now = time.time()
        for aid, asset in state.decaying_assets.items():
            if now - asset.last_modified < self.GRACE_PERIOD and "active_render" in asset.metadata.tags:
                races.append({"asset_id": aid, "flaw": "Decay-Render conflict", "description": f"{asset.name} decaying but tagged active"})

        purged = sum(1 for a in state.decaying_assets.values() if a.state == EntityState.PURGED)
        if purged == 0 and len(state.decaying_assets) > self.THRESHOLD:
            flaws.append("Accumulation warning")

        return {
            "total_active": len(state.active_assets), "total_decaying": len(state.decaying_assets),
            "race_conditions": races, "logic_flaws": flaws,
            "system_health": "STABLE" if not races and not flaws else "DEGRADED"
        }

class ChunkedEncoder:
    """Encodes art assets into chunked byte arrays for progressive loading."""
    def __init__(self, shift_key=ENCODE_SHIFT_KEY):
        self.shift_key = shift_key

    def encode_asset(self, asset: ArtAsset, chunk_size=CHUNK_SIZE) -> List[str]:
        if not asset.content: return []
        b64 = base64.b64encode(asset.content.encode("utf-8"))
        shifted = bytes((b + self.shift_key) % 256 for b in b64)
        final = base64.b64encode(shifted).decode("ascii")
        return [final[i:i+chunk_size] for i in range(0, len(final), chunk_size)]

    def decode_chunks(self, chunks: List[str]) -> str:
        if not chunks: return ""
        final = "".join(chunks)
        shifted = base64.b64decode(final.encode("ascii"))
        b64 = bytes((b - self.shift_key) % 256 for b in shifted)
        return base64.b64decode(b64).decode("utf-8")

class MetamorphicBridge:
    def __init__(self, ecosystem, token_diag, guardrail_diag, concurrency_diag, output_dir=None):
        self.ecosystem = ecosystem
        self.token_diag = token_diag or []
        self.guardrail_diag = guardrail_diag or []
        self.concurrency_diag = concurrency_diag or {}
        self.output_dir = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
        self.encoder = ChunkedEncoder()

    def _compile_luminous_mesh(self):
        if not self.token_diag:
            return {"luminous_mesh_densities": {"global_pressure": 0.0, "css_variables": {"--mesh-luminosity": 1.0, "--mesh-density-throttle": 1.0, "--mesh-glitch-frequency": 0.0}, "throttle_ratio": 1.0, "status": "STABLE"}}

        max_tokens = max(e["estimated_tokens"] for e in self.token_diag)
        pressure = min(1.0, max_tokens / CONTEXT_WINDOW_LIMIT)
        throttle = 1.0 / (1.0 + math.exp(10.0 * (pressure - 0.5)))

        return {"luminous_mesh_densities": {
            "global_pressure": round(pressure, 4),
            "css_variables": {"--mesh-luminosity": round(1.0-pressure, 4), "--mesh-density-throttle": round(throttle, 4), "--mesh-glitch-frequency": round(pressure*5.0, 1)},
            "throttle_ratio": round(throttle, 4),
            "status": "OVERLOADED" if pressure > 0.8 else "STABLE"
        }}

    def _compile_chromatic_masks(self):
        if not self.guardrail_diag:
            return {"chromatic_frequency_masks": {"max_risk_score": 0.0, "css_filter_string": "none", "mask_intensity": "CLEAR", "triggered_categories": []}}

        max_risk = max(e["final_risk_score"] for e in self.guardrail_diag)
        cats = list(set(c for e in self.guardrail_diag for c in e.get("triggered_categories", [])))
        blur = int((max_risk/100.0)*12)
        sat = max(0, 100-int(max_risk*1.5))
        cont = 100+int(max_risk*2.0)

        if max_risk > 70:
            filt = f"blur({blur}px) saturate({sat}%) contrast({cont}%) hue-rotate(180deg)"
            intensity = "CRITICAL"
        elif max_risk > 30:
            filt = f"blur({blur//2}px) saturate({sat}%) contrast({cont}%)"
            intensity = "CAUTION"
        else:
            filt = "none"
            intensity = "CLEAR"

        return {"chromatic_frequency_masks": {"max_risk_score": round(max_risk, 1), "css_filter_string": filt, "mask_intensity": intensity, "triggered_categories": cats}}

    def _compile_chronological(self):
        races = self.concurrency_diag.get("race_conditions", [])
        flaws = self.concurrency_diag.get("logic_flaws", [])
        total = len(races) + len(flaws)

        if total == 0:
            return {"chronological_collision_buffers": {"collision_count": 0, "css_keyframes_payload": "", "animation_class": "", "status": "SYNCHRONIZED"}}

        dur = max(0.1, 2.0 - total*0.3)
        disp = min(15, 3 + total*2)
        skew = min(8, 1 + total)

        # Keyframe name 'temporal_tear' is public (TAPIZ.md, tapiz_renderer.html).
        kf = (
            f"@keyframes temporal_tear {{\n"
            f"  0% {{ transform: translate(0,0) skew(0deg); filter: hue-rotate(0deg); opacity: 1; }}\n"
            f"  8% {{ transform: translate(-{disp}px,{disp//2}px) skew(-{skew}deg); filter: hue-rotate(90deg); opacity: 0.85; }}\n"
            f"  16% {{ transform: translate({disp}px,-{disp//2}px) skew({skew}deg); filter: hue-rotate(180deg); opacity: 0.9; }}\n"
            f"  24% {{ transform: translate(-{disp//2}px,{disp}px) skew(-{skew//2}deg); filter: hue-rotate(270deg); opacity: 0.8; }}\n"
            f"  32% {{ transform: translate(0,0) skew(0deg); filter: hue-rotate(360deg); opacity: 1; }}\n"
            f"  100% {{ transform: translate(0,0) skew(0deg); filter: hue-rotate(0deg); opacity: 1; }}\n"
            f"}}"
        )
        anim = f"animation: temporal_tear {dur}s infinite cubic-bezier(0.25, 0.46, 0.45, 0.94);"

        return {"chronological_collision_buffers": {"collision_count": total, "css_keyframes_payload": kf, "animation_class": anim, "status": "TEMPORAL_DEGRADED", "affected_assets": [r["asset_id"] for r in races]}}

    def _compile_encoded_payloads(self):
        """Encodes decaying assets into chunked payloads for deferred loading."""
        payloads = {}
        for aid, asset in self.ecosystem.decaying_assets.items():
            if asset.state not in (EntityState.DECAYING, EntityState.PURGED): continue
            chunks = self.encoder.encode_asset(asset)
            if chunks:
                decoded = self.encoder.decode_chunks(chunks)
                if decoded != asset.content:
                    raise ValueError(f"Encoding integrity failure: {aid}")
            payloads[aid] = {"name": asset.name, "intent": asset.metadata.conceptual_intent, "data_chunks": chunks, "chunk_count": len(chunks), "decode_shift_key": self.encoder.shift_key}

        return {"encoded_asset_payloads": {"total_payloads": len(payloads), "payloads": payloads, "embedding_target": "</main>", "encoding_protocol": "Base64_Shift42_Chunked"}}

    def _forge_sigil(self):
        hasher = hashlib.sha256()
        all_assets = {**self.ecosystem.active_assets, **self.ecosystem.decaying_assets}
        for aid in sorted(all_assets):
            a = all_assets[aid]
            ch = hashlib.sha256(a.content.encode("utf-8")).hexdigest()[:16]
            hasher.update(f"{aid}|{a.state.value}|{a.last_modified}|{ch}|{a.metadata.conceptual_intent}".encode("utf-8"))
        hasher.update(f"{len(self.token_diag)}|{len(self.guardrail_diag)}|{self.concurrency_diag.get('system_health', 'UNKNOWN')}".encode("utf-8"))
        return hasher.hexdigest()

    def compile_and_export(self):
        print("Compiling pipeline...")
        luminous = self._compile_luminous_mesh()
        chromatic = self._compile_chromatic_masks()
        chronological = self._compile_chronological()
        encoded = self._compile_encoded_payloads()
        sigil = self._forge_sigil()

        matrix = {"meta": {"ecosystem_version": ECOSYSTEM_VERSION, "compilation_timestamp": time.time(), "integrity_sigil": sigil, "embedding_target": "</main>"}, **luminous, **chromatic, **chronological, **encoded}

        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / OUTPUT_FILENAME
        with open(path, "w", encoding="utf-8") as f:
            json.dump(matrix, f, indent=4, ensure_ascii=False)

        print(f"Exported to {path}")
        print(f"Sigil: {sigil[:16]}...")
        return str(path.resolve())

def build_mock_ecosystem():
    state = EcosystemState()
    ascii_art = "█"*1500 + "\n" + "▓"*1500 + "\n" + "░"*1500 + "\n╔═══╗\n║PSI║\n╚═══╝\n"

    a1 = ArtAsset("ART-001", "Psicosis", ascii_art, MetadataLayer("Entropy exploration", ["ascii", "psicosis", "active_render"], True), EntityState.DECAYING, time.time()-10)
    a2 = ArtAsset("ART-002", "Tapiz", "// Three.js code", MetadataLayer("Geometric space", ["3d", "tapiz"], True), EntityState.ACTIVE, time.time()-3600)
    a3 = ArtAsset("ART-003", "Fungi", "[Decay log]", MetadataLayer("Decomposition", ["fungi", "decay"], True), EntityState.DECAYING, time.time()-120)

    state.active_assets[a2.asset_id] = a2
    state.decaying_assets[a1.asset_id] = a1
    state.decaying_assets[a3.asset_id] = a3
    return state

def build_stress_ecosystem():
    """Hostile ecosystem: pushes every diagnostic past its ugly threshold so the
    renderer's degraded states (OVERLOADED mesh, CRITICAL mask, violent
    temporal tears, spore accumulation) are actually visible."""
    state = EcosystemState()
    now = time.time()

    # Token bomb: dense glyph wall, ~33k estimated tokens -> pressure 1.0.
    glyph_wall = ("█▓░▒" * 7500) + "\n╔══════╗\n║OVRLD ║\n╚══════╝\n"
    bomb = ArtAsset("ART-100", "Saturacion", glyph_wall,
                    MetadataLayer("Context annihilation", ["ascii", "overload", "active_render"], True),
                    EntityState.DECAYING, now - 5)

    # Guardrail bomb: non-artistic context (0% mitigation), lexicon-saturated
    # moderation-fixture text -> risk score pinned at 100 -> CRITICAL mask.
    mod_fixture = "rot decay slime trash basurero gore psicosis " * 3
    flagged = ArtAsset("ART-101", "Censura", mod_fixture,
                       MetadataLayer("Moderation stress fixture", ["fixture"], False),
                       EntityState.ACTIVE, now - 30)

    # State violation: same asset registered active AND decaying.
    both = ArtAsset("ART-102", "Paradoja", "estado doble",
                    MetadataLayer("State violation", ["paradox", "active_render"], True),
                    EntityState.DECAYING, now - 2)

    state.active_assets[flagged.asset_id] = flagged
    state.active_assets[both.asset_id] = both
    state.decaying_assets[both.asset_id] = both
    state.decaying_assets[bomb.asset_id] = bomb

    # Accumulation: >10 decaying, none purged, several racing the renderer.
    for i in range(10):
        tags = ["fungi", "colony"]
        if i < 3:
            tags.append("active_render")  # Decay-Render race within grace period
        spore = ArtAsset(f"ART-2{i:02d}", f"Colonia-{i:02d}",
                         f"[esporas lote {i:02d}] " + "hyphae " * 12,
                         MetadataLayer("Colony sprawl", tags, True),
                         EntityState.DECAYING, now - (5 if i < 3 else 900))
        state.decaying_assets[spore.asset_id] = spore
    return state

def execute_pipeline(output_dir=None, stress=False, mode=None):
    if mode is None:
        mode = "stress" if stress else "demo"
    elif stress and mode != "stress":
        raise ValueError(f"contradictory arguments: stress=True with mode={mode!r}")
    if mode not in ("demo", "stress", "live"):
        raise ValueError(f"unknown pipeline mode: {mode!r}")
    label = {"demo": "", "stress": " [STRESS]", "live": " [LIVE]"}[mode]
    print("SYSTEM PROJECTION PIPELINE" + label + "\n")

    if mode == "live":
        # Late import: --demo/--stress stay byte-compatible and independent.
        try:
            from tapiz_telemetry import build_live_ecosystem
        except ImportError:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from tapiz_telemetry import build_live_ecosystem
        ecosystem = build_live_ecosystem()
    elif mode == "stress":
        ecosystem = build_stress_ecosystem()
    else:
        ecosystem = build_mock_ecosystem()
    print(f"Active: {len(ecosystem.active_assets)}, Decaying: {len(ecosystem.decaying_assets)}\n")

    token_analyzer = TokenVolumetricAnalyzer()
    guardrail_analyzer = GuardrailSimulationAnalyzer()
    concurrency_analyzer = ConcurrencyLogicAnalyzer()

    all_assets = list(ecosystem.active_assets.values()) + list(ecosystem.decaying_assets.values())
    token_results, guardrail_results = [], []

    for asset in all_assets:
        t = token_analyzer.analyze_asset(asset)
        token_results.append(t)
        print(f"[Token] {t['asset_id']}: {t['estimated_tokens']} tokens ({t['context_overflow_risk']})")

        g = guardrail_analyzer.analyze_asset(asset)
        guardrail_results.append(g)
        print(f"[Guard] {g['asset_id']}: {g['final_risk_score']} ({g['risk_level']})")

    c = concurrency_analyzer.analyze_ecosystem(ecosystem)
    print(f"[Concur] {c['system_health']} | Conflicts: {len(c['race_conditions'])}\n")

    bridge = MetamorphicBridge(ecosystem, token_results, guardrail_results, c, output_dir=output_dir)
    return bridge.compile_and_export()

def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="compete_engine",
        description="Tapiz/Psicosis/Fungi artistic diagnostics pipeline.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--demo", action="store_true",
        help="run the pipeline against the built-in mock ecosystem",
    )
    mode.add_argument(
        "--stress", action="store_true",
        help="run against a hostile ecosystem that triggers every degraded "
             "state (OVERLOADED, CRITICAL, temporal tears, accumulation)",
    )
    mode.add_argument(
        "--live", action="store_true",
        help="run against LIVE repo telemetry (real sizes, git state, "
             "session-log weight); a self-portrait of the repo",
    )
    parser.add_argument(
        "--out", metavar="DIR", default=None,
        help="output directory for system_status.json "
             "(default: 'dist' next to this script)",
    )
    args = parser.parse_args(argv)

    if not (args.demo or args.stress or args.live):
        parser.error("no input mode selected; use --demo, --stress or --live")

    run_mode = "live" if args.live else "stress" if args.stress else "demo"

    _harden_console()
    try:
        execute_pipeline(output_dir=args.out, mode=run_mode)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    # Alias this __main__ module as 'compete_engine' so helpers that
    # 'import compete_engine' (e.g. tapiz_telemetry) share the SAME enum
    # classes; otherwise EntityState identity checks silently fail.
    sys.modules.setdefault("compete_engine", sys.modules[__name__])
    sys.exit(main())
