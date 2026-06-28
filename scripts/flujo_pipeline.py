#!/usr/bin/env python3
"""Pipeline inteligente: correo → job → proyecto → render.

Intenta inferir tipo y medidas desde el correo para reducir bloqueos en
`pendiente_datos`. Si la inferencia es segura, crea el proyecto y genera SVGs
automáticamente.

Uso:
  py scripts/flujo_pipeline.py "nombre pedido" inbox/correo.txt [--confirm]

Sin `--confirm` el pipeline pregunta antes de aplicar inferencias.
Con `--confirm` aplica directamente inferencias de bajo riesgo.
"""
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

from _common import repo_root, load_json

ROOT = repo_root()
PY = sys.executable


# Mapeo de palabras clave a tipo de pieza, medidas y plantilla
TYPE_HINTS = {
    "etiqueta": {"tipo": "etiqueta", "ancho": 16.5, "alto": 6.5, "template": "etiqueta_horizontal_165x65.config.json"},
    "sticker": {"tipo": "sticker", "ancho": 10, "alto": 10, "template": "etiqueta_horizontal_165x65.config.json"},
    "flyer": {"tipo": "flyer", "ancho": 21, "alto": 29.7, "template": "flyer_horizontal_minimo.config.json"},
    "dossier": {"tipo": "dossier", "ancho": 21, "alto": 29.7, "template": "one_page_propuesta_210x297.config.json"},
    "one page": {"tipo": "one_page", "ancho": 21, "alto": 29.7, "template": "one_page_propuesta_210x297.config.json"},
    "one-page": {"tipo": "one_page", "ancho": 21, "alto": 29.7, "template": "one_page_propuesta_210x297.config.json"},
    "presentacion": {"tipo": "presentacion", "ancho": 21, "alto": 29.7, "template": "one_page_propuesta_210x297.config.json"},
    "carrusel": {"tipo": "carrusel", "ancho": 10.8, "alto": 10.8, "template": "carrusel_cuadrado_1080.config.json"},
    "rider": {"tipo": "rider", "ancho": 29.7, "alto": 21, "template": "rider_eventos_a4_horizontal.config.json"},
    "tarjeta": {"tipo": "tarjeta", "ancho": 9, "alto": 5, "template": "flyer_horizontal_minimo.config.json"},
}


def infer_type_and_size(text: str) -> dict | None:
    text_lower = text.lower()
    for keyword, data in TYPE_HINTS.items():
        if keyword in text_lower:
            return dict(data)
    return None


def run(cmd, cwd=ROOT):
    print("$", " ".join(str(c) for c in cmd))
    result = subprocess.run(cmd, cwd=cwd, check=False, text=True, capture_output=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    if result.returncode != 0:
        print(f"ERROR: comando falló con código {result.returncode}")
        sys.exit(result.returncode)
    return result


def python_cmd(script, *args):
    return [PY, str(ROOT / "scripts" / script), *args]


def parse_brief(job_dir):
    brief_path = job_dir / "brief.yaml"
    if not brief_path.exists():
        return None
    try:
        return yaml.safe_load(brief_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"No se pudo leer brief.yaml: {e}")
        return None


def has_real_measurements(brief):
    m = brief.get("medidas", {})
    return bool(m.get("ancho_cm") and m.get("alto_cm"))


def has_tipo(brief):
    t = brief.get("tipo_pieza", "")
    return bool(t and t != "pendiente_definir")


def update_brief(job_dir, inferred, confirm=False):
    brief_path = job_dir / "brief.yaml"
    text = brief_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    # Reemplazar tipo_pieza
    for i, line in enumerate(lines):
        if line.startswith("tipo_pieza:"):
            lines[i] = f"tipo_pieza: {inferred['tipo']}"
        if line.startswith("  ancho_cm:"):
            lines[i] = f"  ancho_cm: {inferred['ancho']}"
        if line.startswith("  alto_cm:"):
            lines[i] = f"  alto_cm: {inferred['alto']}"
        if line.startswith("estado:"):
            lines[i] = "estado: listo_para_disenar"

    # Agregar nota de inferencia
    lines.append("")
    lines.append(f"# Inferido automáticamente desde el correo: tipo={inferred['tipo']}, medidas={inferred['ancho']}x{inferred['alto']}cm")
    if not confirm:
        lines.append("# Revisar antes de generar salidas finales.")

    brief_path.write_text("\n".join(lines), encoding="utf-8")


def discover_recent_job():
    jobs = sorted(
        (p for p in (ROOT / "jobs").glob("*/brief.yaml") if not p.parent.name.startswith("_")),
        key=lambda p: p.parent.name,
        reverse=True,
    )
    return jobs[0].parent if jobs else None


def discover_project_for_job(job_dir):
    """Busca el proyecto recién creado que referencie este job."""
    job_str = str(job_dir)
    for config in (ROOT / "projects" / "piezas_vectoriales").glob("*/config.json"):
        data = load_json(config)
        if data and data.get("project", {}).get("source_job") == job_str:
            return config.parent
    return None


def main():
    confirm = "--confirm" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--confirm"]

    if len(args) < 2:
        print("Uso: py scripts/flujo_pipeline.py \"nombre pedido\" inbox/correo.txt [--confirm]")
        sys.exit(1)

    name = args[0]
    email_path = Path(args[1])

    if not email_path.exists():
        print(f"ERROR: no existe archivo: {email_path}")
        sys.exit(1)

    email_text = email_path.read_text(encoding="utf-8", errors="ignore")

    result = {
        "inicio": datetime.now().isoformat(timespec="seconds"),
        "pedido": name,
        "correo": str(email_path),
        "job": None,
        "proyecto": None,
        "salidas": None,
        "inferencia": None,
        "errores": [],
    }

    # 1. Crear job
    run(python_cmd("job_from_text.py", name, str(email_path)))

    job_dir = discover_recent_job()
    if not job_dir:
        result["errores"].append("No se encontró job creado")
        save_result(result)
        sys.exit(1)

    result["job"] = str(job_dir)
    print(f"\nJob creado: {job_dir}\n")

    # 2. Privacidad
    run(python_cmd("privacy_check_job.py", str(job_dir)))

    # 3. Extraer brief
    run(python_cmd("job_extract_brief.py", str(job_dir)))

    # 4. Preparar job
    run(python_cmd("job_prepare.py", str(job_dir)))

    # 5. Revisar si necesitamos inferencia
    brief = parse_brief(job_dir)
    if not brief:
        result["errores"].append("No se pudo parsear brief.yaml")
        save_result(result)
        sys.exit(1)

    estado = brief.get("estado", "")
    print(f"\nEstado del brief: {estado}")

    inferred = infer_type_and_size(email_text)

    if estado in ("listo_para_disenar", "en_diseno") and (has_real_measurements(brief) or has_tipo(brief)):
        print("\nBrief tiene datos suficientes. Creando proyecto...")
    elif inferred:
        print(f"\nInferencia desde correo: tipo={inferred['tipo']}, medidas={inferred['ancho']}x{inferred['alto']}cm")
        if not confirm:
            resp = input("¿Aplicar inferencia y continuar? (s/n): ")
            if resp.lower() not in ("s", "si", "sí"):
                print("Pipeline detenido. Revisar el brief manualmente.")
                result["inferencia"] = inferred
                save_result(result)
                sys.exit(0)
        update_brief(job_dir, inferred, confirm=confirm)
        result["inferencia"] = inferred
        print("Brief actualizado con inferencia.\n")
    else:
        print("\nNo se pudo inferir tipo/medidas desde el correo.")
        print("Pipeline se detiene. Revisar el brief y completar datos.\n")
        save_result(result)
        sys.exit(0)

    # 6. Crear proyecto
    run(python_cmd("brief_to_project.py", str(job_dir / "brief.yaml")))

    project_dir = discover_project_for_job(job_dir)
    if project_dir:
        result["proyecto"] = str(project_dir)
        print(f"\nProyecto creado: {project_dir}\n")

        # 7. Generar SVGs
        run(python_cmd("piezas_generar.py", str(project_dir / "config.json")))
        result["salidas"] = str(project_dir / "salida_generada")
        print(f"\nSalidas generadas: {result['salidas']}\n")

    # 8. Actualizar daily
    run(python_cmd("flujo_daily.py"))

    result["fin"] = datetime.now().isoformat(timespec="seconds")
    save_result(result)

    print("\n=== Pipeline completado ===")
    print(f"Job:      {result['job']}")
    print(f"Inferencia: {result['inferencia']}")
    print(f"Proyecto: {result['proyecto'] or 'no generado'}")
    print(f"Salidas:  {result['salidas'] or 'no generadas'}")
    print(f"Resumen:  {ROOT / 'context' / 'PIPELINE_RESULT.md'}")


def save_result(result):
    lines = [
        "# Resultado del último pipeline",
        "",
        f"- Inicio: {result['inicio']}",
        f"- Fin: {result.get('fin', 'en progreso')}",
        f"- Pedido: {result['pedido']}",
        f"- Correo: {result['correo']}",
        f"- Job: {result['job']}",
        f"- Inferencia: {result['inferencia']}",
        f"- Proyecto: {result['proyecto'] or 'no generado'}",
        f"- Salidas: {result['salidas'] or 'no generadas'}",
    ]
    if result["errores"]:
        lines.extend(["", "## Errores"])
        for e in result["errores"]:
            lines.append(f"- {e}")
    lines.extend(["", "Ver también: `context/DAILY.md`"])

    (ROOT / "context" / "PIPELINE_RESULT.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
