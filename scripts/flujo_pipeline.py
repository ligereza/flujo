#!/usr/bin/env python3
"""Pipeline automático: correo → job → proyecto → render.

Uso:
  py scripts/flujo_pipeline.py "nombre pedido" inbox/correo.txt

Pasos:
  1. Crear job desde el correo.
  2. Revisar privacidad.
  3. Extraer brief.
  4. Preparar job (estado sugerido).
  5. Si el brief tiene medidas/tipo, crear proyecto de piezas_vectoriales.
  6. Generar SVGs del proyecto.
  7. Actualizar reporte diario.
  8. Guardar resumen en context/PIPELINE_RESULT.md.
"""
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

from _common import repo_root, load_json

ROOT = repo_root()
PY = sys.executable


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
    return bool(brief.get("tipo_pieza") and brief.get("tipo_pieza") != "pendiente_definir")


def main():
    if len(sys.argv) < 3:
        print("Uso: py scripts/flujo_pipeline.py \"nombre pedido\" inbox/correo.txt")
        sys.exit(1)

    name = sys.argv[1]
    email_path = Path(sys.argv[2])

    if not email_path.exists():
        print(f"ERROR: no existe archivo: {email_path}")
        sys.exit(1)

    result = {
        "inicio": datetime.now().isoformat(timespec="seconds"),
        "pedido": name,
        "correo": str(email_path),
        "job": None,
        "proyecto": None,
        "salidas": None,
        "errores": [],
    }

    # 1. Crear job
    run(python_cmd("job_from_text.py", name, str(email_path)))

    # Descubrir el job creado (el más reciente, excluyendo _template y _examples)
    jobs = sorted(
        (p for p in (ROOT / "jobs").glob("*/brief.yaml") if not p.parent.name.startswith("_")),
        key=lambda p: p.parent.name,
        reverse=True,
    )
    if not jobs:
        result["errores"].append("No se encontró job creado")
        save_result(result)
        sys.exit(1)

    job_dir = jobs[0].parent
    result["job"] = str(job_dir)
    print(f"\nJob creado: {job_dir}\n")

    # 2. Privacidad
    run(python_cmd("privacy_check_job.py", str(job_dir)))

    # 3. Extraer brief
    run(python_cmd("job_extract_brief.py", str(job_dir)))

    # 4. Preparar job
    run(python_cmd("job_prepare.py", str(job_dir)))

    # 5. Revisar si podemos crear proyecto
    brief = parse_brief(job_dir)
    if not brief:
        result["errores"].append("No se pudo parsear brief.yaml")
        save_result(result)
        sys.exit(1)

    estado = brief.get("estado", "")
    print(f"\nEstado del brief: {estado}")

    if estado in ("listo_para_disenar", "en_diseno") and (has_real_measurements(brief) or has_tipo(brief)):
        print("\nCreando proyecto de piezas_vectoriales...")
        run(python_cmd("brief_to_project.py", str(job_dir / "brief.yaml")))

        # Descubrir proyecto creado (más reciente)
        proyectos = sorted((ROOT / "projects" / "piezas_vectoriales").glob("*/config.json"), key=lambda p: p.parent.name, reverse=True)
        if proyectos:
            project_dir = proyectos[0].parent
            result["proyecto"] = str(project_dir)
            print(f"\nProyecto creado: {project_dir}\n")

            # 6. Generar SVGs
            run(python_cmd("piezas_generar.py", str(project_dir / "config.json")))
            result["salidas"] = str(project_dir / "salida_generada")
            print(f"\nSalidas generadas: {result['salidas']}\n")
    else:
        print("\nBrief no listo para generar proyecto automáticamente.")
        print("Motivo: estado != listo/en_diseno o faltan medidas/tipo.")
        print("Revisar el brief y completar datos.\n")

    # 7. Actualizar daily
    run(python_cmd("flujo_daily.py"))

    # 8. Guardar resumen
    result["fin"] = datetime.now().isoformat(timespec="seconds")
    save_result(result)

    print("\n=== Pipeline completado ===")
    print(f"Job:     {result['job']}")
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
