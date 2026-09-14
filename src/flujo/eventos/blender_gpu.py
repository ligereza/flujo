"""Force Cycles to render on GPU (OptiX/CUDA/HIP), never CPU.

Non-destructive: sets device in-memory for this Blender session only, does
NOT modify/save the .blend file. Import and call force_gpu() from any bpy
script BEFORE bpy.ops.render.render(), or run standalone via:
    blender -b file.blend --python blender_gpu.py -f 1
"""


def force_gpu(prefer=("OPTIX", "CUDA", "HIP", "METAL")):
    """Enable the first available GPU compute backend and select all its
    devices. Returns a dict report (backend, devices enabled) for logging.
    Falls back to CPU only if truly no GPU backend is available (never
    silently renders on CPU when a GPU exists).

    FLUJO_GPU_BACKEND overrides the order for one machine. It exists because
    OptiX is not always the fast one: measured 2026-07-27 on the same scene,
    the box's GTX 1650 took 300s on CUDA and 459s on OptiX -- 35% slower. That
    card is the only Turing WITHOUT RT cores, so OptiX emulates in software
    what it was built to accelerate. On the laptop's RTX 4070 OptiX wins, which
    is why this is per-machine and not a new default.
    """
    import os

    import bpy

    elegido = os.environ.get("FLUJO_GPU_BACKEND", "").strip().upper()
    if elegido:
        prefer = (elegido,) + tuple(b for b in prefer if b != elegido)

    scene = bpy.context.scene
    if scene.render.engine != "CYCLES":
        return {"engine": scene.render.engine, "note": "not Cycles, GPU device N/A"}

    cprefs = bpy.context.preferences.addons["cycles"].preferences
    chosen = None
    for backend in prefer:
        try:
            cprefs.compute_device_type = backend
            cprefs.get_devices()
            if any(d.type == backend for d in cprefs.devices):
                chosen = backend
                break
        except Exception:
            continue

    if chosen is None:
        scene.cycles.device = "CPU"
        return {"engine": "CYCLES", "device": "CPU", "reason": "no GPU backend detected"}

    enabled = []
    for d in cprefs.devices:
        if d.type == chosen:
            d.use = True
            enabled.append(d.name)
        elif d.type == "CPU":
            d.use = False  # GPU only, CPU stays idle so it doesn't bottleneck

    scene.cycles.device = "GPU"
    return {"engine": "CYCLES", "device": "GPU", "backend": chosen, "devices_enabled": enabled}


if __name__ == "__main__":
    import json
    print("=== GPU_FORCE_JSON_START ===")
    print(json.dumps(force_gpu(), indent=2))
    print("=== GPU_FORCE_JSON_END ===")
