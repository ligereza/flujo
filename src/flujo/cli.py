"""CLI unificada de flujo — Typer.

Completa: jobs, privacy, render, dashboard, intake, flyer, airdrop, etc.
La versión se centraliza en `flujo.version` (ver `flujo version`).

Comandos disponibles (ejecutar `flujo --help`):
  salud / info
    health                      Chequeo general del repo
    version                     Versión y changelog
  intake / flyers
    flyer-import                Importar flyers desde correo (links IG)
    ig-redownload               Reintentar descargas fallidas de IG
    analyze                     Analizar proyecto(s) flyer
    export                      Exportar ZIP listo para PS/AI
  index / db
    index                       Reconstruir/consultar índice SQLite de flyers
    code-index                 Indexar estructura AST de Python sin guardar código fuente
    flyer-list                  Listar flyers
  jobs
    job-new                     Crear job desde texto/correo
    job prepare                 Pipeline: privacidad → brief → estado
    job list                    Listar jobs y estados
    job-status <path>           Estado de un job específico
    job next                    Próximas acciones sugeridas por job
    job activate                brief → proyecto en projects/piezas_vectoriales/
    job-report <path>           Reporte detallado de un job
  privacy
    privacy-scan <archivo>      Escanear un texto
    privacy-sanitize <archivo>  Sanitizar texto → [EMAIL], [RUT], etc.
  brief
    brief-extract <job>         Re-extraer brief desde texto del job
    brief-to-project <brief>    Convertir brief.yaml en proyecto
    brief-show <brief>          Mostrar brief en formato legible
  render
    render <config.json>        Renderizar proyecto piezas_vectoriales
    validate <config.json>      Validar config.json
    formats [w h tipo]          Listar o sugerir formatos/plantillas
  dashboard
    daily                       Generar reporte diario (md + html)
  web
    app                         ENTRADA DIARIA: lanza la app + hub pro workspace (con delegación)
    serve                       (alias; --desktop para ventana nativa)
    package                     Empaqueta .exe standalone gratis (PyInstaller) → flujo-hub.exe onefile noconsole con icono premium (rounded+F), lanza directo pywebview desktop hub, assets (context/svg/brand + jobs/_template + src/flujo/templates) bundled, workspace next-to-exe, visualizers fully working. (equiv `flujo app --desktop`)
  plano
    plano <evento.json>         Generar plano SVG/rider/costos de stands
  datadrop (inverse airdrop)
    datadrop list            Lista datadrops subidos (fotos reales terminadas)
    datadrop prepare         Escribe _review_package.txt con for_future_ai + traits (para IA futura/linea)
  cotizaciones
    cotizaciones <evento.json> --para productora|interno  Cotización dual (flujo + formatos)
"""
from __future__ import annotations

import os
import sys
import unicodedata
from pathlib import Path
from typing import Optional


def _expose_repo_namespace() -> None:
    """Make repo-level namespace packages available to the installed CLI."""
    repo = Path(__file__).resolve().parents[2]
    if (repo / "cultura").is_dir() and str(repo) not in sys.path:
        sys.path.insert(0, str(repo))


_expose_repo_namespace()


def _configure_windows_stdio() -> None:
    """Avoid UnicodeEncodeError on Windows/Git Bash cp1252 consoles.

    Some Windows shells report cp1252 to Rich. CLI output contains symbols and
    arrows used across the changelog, so force UTF-8 with replacement before
    constructing the global Console.
    """
    if os.name != "nt":
        return
    for stream in (sys.stdout, sys.stderr):
        try:
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


_configure_windows_stdio()

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel


from .remote_ai import build_remote_ai_prompt, write_remote_ai_prompt
from .version import get_version as _get_pkg_version

app = typer.Typer(
    add_completion=False,
    help=f"flujo — Dimensiones del Orden · v{_get_pkg_version()}",
    no_args_is_help=True,
)
console = Console()


# ============================================================
# Sub-apps
# ============================================================




job_app = typer.Typer(help="Gestión de jobs y briefs.", no_args_is_help=True)
privacy_app = typer.Typer(help="Privacidad para textos antes de IA externa.", no_args_is_help=True)
brief_app = typer.Typer(help="Operaciones sobre briefs.", no_args_is_help=True)
intake_app = typer.Typer(help="Intake estructurado de pedidos (JSON 1.0).", no_args_is_help=True)
eventos_app = typer.Typer(help="Automatizaciones del area EVENTOS.", no_args_is_help=True)
resolume_app = typer.Typer(help="Automatizacion de shows Resolume/Chataigne por SMPTE/OSC.", no_args_is_help=True)
laser_app = typer.Typer(help="Estetica vectorial para laser/plotter (vpype): rayado, campos de flujo.", no_args_is_help=True)
render_app = typer.Typer(help="Render y validación de piezas vectoriales.", no_args_is_help=True)
airdrop_app = typer.Typer(help="Sistema de actualización profesional (airdrops).", no_args_is_help=True)
datadrop_app = typer.Typer(help="Gestión de datadrops (fotos reales terminadas).", no_args_is_help=True)
micelio_app = typer.Typer(help="El sobre micelio/1: semilla, fruto y nutriente entre un modelo web sin API y el organismo.", no_args_is_help=True)
autonomia_app = typer.Typer(help="Orquestacion externa MAK: estado, tandas, ledger y juez local.", no_args_is_help=True)

app.add_typer(job_app, name="job")
app.add_typer(privacy_app, name="privacy")
app.add_typer(brief_app, name="brief")
app.add_typer(intake_app, name="intake")
app.add_typer(eventos_app, name="eventos")
app.add_typer(resolume_app, name="resolume")
app.add_typer(laser_app, name="laser")
app.add_typer(render_app, name="render")
app.add_typer(airdrop_app, name="airdrop")
app.add_typer(datadrop_app, name="datadrop")
app.add_typer(micelio_app, name="micelio")
app.add_typer(autonomia_app, name="autonomia")


@autonomia_app.command("status")
def autonomia_status(
    common_ledger: str = typer.Option("", "--common-ledger", help="Override del ledger comun MAK."),
    batch_ledger: str = typer.Option("", "--batch-ledger", help="Override del ledger de tandas externas."),
    executor: str = typer.Option("local", "--executor", help="local | mak"),
    ssh_target: str = typer.Option("", "--ssh-target", help="Destino SSH MAK."),
):
    """Mide si el circuito remoto/local -> juez local -> ledger esta listo."""
    import json as _json
    from .autonomia import MAK_SSH_TARGET, autonomy_status as _status, mak_status
    from .autonomia import MAK_BOX_AVAILABLE, tandas as _tandas

    if not MAK_BOX_AVAILABLE:
        console.print("[yellow]MAK box layer ausente en este checkout: "
                      "este comando requiere el arbol cultura/mak_plataforma.[/]")
        raise typer.Exit(code=2)

    if executor == "mak":
        payload = mak_status(target=ssh_target or MAK_SSH_TARGET)
    else:
        payload = _status(
            common_path=common_ledger or _tandas.COMMON_LEDGER,
            batch_path=batch_ledger or _tandas.LEDGER,
            include_local_providers=False,
        )
    print(_json.dumps(payload, ensure_ascii=False, indent=2))


@autonomia_app.command("run")
def autonomia_run(
    areas: str = typer.Option("", "--areas", help="CSV de areas; default: todas."),
    providers: str = typer.Option("groq,gemini,ollama", "--providers", help="CSV: groq,gemini,ollama."),
    round_id: str = typer.Option("", "--round-id", help="Id estable de corrida."),
    out_dir: str = typer.Option("", "--out-dir", help="Carpeta de salida; default en _logs."),
    common_ledger: str = typer.Option("", "--common-ledger", help="Override del ledger comun MAK."),
    batch_ledger: str = typer.Option("", "--batch-ledger", help="Override del ledger de tandas externas."),
    max_tokens: int = typer.Option(1800, "--max-tokens", help="Tope por llamada externa."),
    max_items: int = typer.Option(5, "--max-items", help="Maximo de items por proveedor y area."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Solo escribir briefs; no llamar proveedores."),
    allow_dirty: bool = typer.Option(False, "--allow-dirty", help="Permite correr aunque el repo este sucio."),
    no_ollama: bool = typer.Option(False, "--no-ollama", help="Usar juez determinista sin Ollama."),
    instruction: str = typer.Option("", "--instruction", help="Instruccion especifica de esta tanda."),
    executor: str = typer.Option("mak", "--executor", help="mak ejecuta providers/Ollama; local solo para tests/dry-run."),
    ssh_target: str = typer.Option("", "--ssh-target", help="Destino SSH MAK."),
    mak_repo: str = typer.Option("~/flujo", "--mak-repo", help="Repo en MAK."),
):
    """Ejecuta tandas controladas; por defecto corre providers/Ollama en MAK."""
    import json as _json
    from cultura.mak_plataforma import tandas as _tandas
    from .autonomia import MAK_SSH_TARGET, build_run_options, run_autonomy

    try:
        options = build_run_options(
            areas=areas or None,
            providers=providers or None,
            round_id=round_id,
            out_dir=out_dir,
            common_ledger_path=common_ledger or _tandas.COMMON_LEDGER,
            batch_ledger_path=batch_ledger or _tandas.LEDGER,
            max_tokens=max_tokens,
            max_items=max_items,
            use_ollama=not no_ollama,
            require_clean=not allow_dirty,
            dry_run=dry_run,
            instruction=instruction,
            executor=executor,
            ssh_target=ssh_target or MAK_SSH_TARGET,
            mak_repo=mak_repo,
        )
    except ValueError as exc:
        _err(str(exc))
    payload = run_autonomy(options)
    print(_json.dumps(payload, ensure_ascii=False, indent=2))
    if not payload.get("ok"):
        raise typer.Exit(2)


@micelio_app.command("formato")
def micelio_formato(
    salida: str = typer.Option("", "--salida", help="Escribirlo a un archivo en vez de a la pantalla."),
):
    """Imprime el formato para PEGARSELO al modelo web antes de contarle la idea.

    Es el primer paso del ciclo y el unico que hace el usuario a mano. Existe
    para que la parte cara -- el unico modelo capaz que queda, en un chat, sin
    API -- no dependa de acordarse de las reglas.
    """
    from .micelio import formato_para_el_modelo
    texto = formato_para_el_modelo()
    if salida:
        Path(salida).write_text(texto, encoding="utf-8")
        console.print(f"OK -> {salida}")
    else:
        # print pelado, no console.print: esto se copia y se pega, y rich le
        # mete saltos de linea que le cambian el sentido a un bloque JSON.
        print(texto)


@micelio_app.command("validar")
def micelio_validar(
    archivo: str = typer.Argument(..., help="El sobre que devolvio el modelo web (acepta el ```json alrededor)."),
):
    """Dice si el sobre sirve, y si no, QUE le falta -- en castellano, para
    poder pegarle la respuesta de vuelta al modelo que lo escribio."""
    from .micelio import SobreInvalido, leer
    try:
        sobre = leer(archivo)
    except SobreInvalido as e:
        console.print(f"[red]sobre invalido[/red]: {e}")
        raise typer.Exit(1)
    except OSError as e:
        console.print(f"[red]no pude leerlo[/red]: {e}")
        raise typer.Exit(2)
    crit = sobre.get("criterio") or []
    console.print(f"OK  {sobre['tipo']}: {sobre['asunto']}")
    for c in crit:
        console.print(f"    criterio {c['tipo']}: {c.get('nombre', '')}")
    if sobre["tipo"] == "fruto" and sobre.get("recortado"):
        console.print(f"[yellow]recortado[/yellow]: {sobre['recortado']} "
                      "-- lo que estas leyendo NO es todo")


@micelio_app.command("fruto")
def micelio_fruto(
    dataset: str = typer.Argument(..., help="Un .json o .jsonl a medir (archivo.json, fichas.jsonl...)."),
    salida: str = typer.Option("", "--salida", help="Escribir el sobre a un archivo."),
    asunto: str = typer.Option("", "--asunto", help="La linea que lo describe."),
):
    """Mide un dataset y arma un fruto que CABE en una ventana de chat.

    El fruto no es un volcado: lleva el estado medido, lo anomalo, unas pocas
    muestras del extremo pobre y punteros. Si algo se recorto para que entrara,
    lo dice en `recortado` -- un recorte callado se lee como "esto era todo".
    """
    import json as _json

    from .micelio import escribir as _escribir, fruto as _fruto, medir_dataset
    try:
        medido, anomalias, muestras = medir_dataset(dataset)
    except OSError as e:
        console.print(f"[red]no pude leerlo[/red]: {e}")
        raise typer.Exit(2)
    sobre = _fruto(
        asunto or f"estado de {Path(dataset).name}",
        medido, anomalias, muestras,
        punteros=[str(dataset)],
    )
    texto = _json.dumps(sobre, ensure_ascii=False, indent=1)
    if salida:
        _escribir(sobre, salida)
        console.print(f"OK -> {salida}  ({len(texto)} bytes, pegable)")
    else:
        print(texto)
    for a in anomalias:
        console.print(f"[yellow]anomalia[/yellow] {a['campo']}: "
                      f"{a.get('cobertura_pct', '?')}% de cobertura")


@micelio_app.command("verificar")
def micelio_verificar(
    archivo: str = typer.Argument(..., help="Sobre con `criterio` (semilla o nutriente)."),
    raiz: str = typer.Option(".", "--raiz", help="Desde donde se resuelven las rutas."),
):
    """Corre el criterio y devuelve VERDE o ROJO. Es el semaforo del ciclo.

    Un modelo debil no necesita entender el pedido: repite hasta que esto da
    verde. Sale con codigo 1 en rojo, para que un script lo use como compuerta.
    """
    from .micelio import SobreInvalido, leer, verificar as _verificar
    try:
        sobre = leer(archivo)
    except SobreInvalido as e:
        console.print(f"[red]sobre invalido[/red]: {e}")
        raise typer.Exit(2)
    r = _verificar(sobre, raiz)
    for c in r.checks:
        color = "green" if c["verde"] else "red"
        console.print(f"[{color}]{'OK  ' if c['verde'] else 'FALLA'}[/{color}] "
                      f"{c['nombre']}: {c['detalle']}")
    if not r.checks:
        console.print("[yellow]el sobre no trae criterio: no hay nada que "
                      "verificar, y eso NO es verde[/yellow]")
    console.print("[green]VERDE[/green]" if r.verde else "[red]ROJO[/red]")
    if not r.verde:
        raise typer.Exit(1)

@micelio_app.command("cosechar")
def micelio_cosechar(
    archivo: str = typer.Argument(..., help="El sobre `semilla` o `nutriente` que se depositó."),
    raiz: str = typer.Option(".", "--raiz", help="Desde donde se resuelven las rutas."),
    salida: str = typer.Option("", "--salida", help="Escribir el sobre a un archivo."),
):
    """Corre el criterio y devuelve el SOBRE de vuelta: fruto si crecio, hongo si no.

    Es la pata de regreso del circuito, y era la que faltaba. `verificar`
    imprime VERDE o ROJO en una consola, que no le sirve al unico lector que
    importa aca: un modelo web sin API, que solo recibe lo que una persona
    pega en un chat.

    El flujo, en palabras del usuario: le pide una semilla a un modelo web, la
    deposita, y SI HAY BUG el micelio le entrega un hongo; le pasa el hongo al
    modelo, que responde con un nutriente; si el nutriente lo arregla, la
    semilla corre y se crea un fruto.

    Por eso el hongo no es un log de error: es el sobre que un modelo necesita
    para escribir la correccion sin ver la maquina -- que se pidio, que
    criterios se pusieron rojos con su mensaje literal, y que produjo el
    organismo de verdad.
    """
    import json as _json
    from .micelio import SobreInvalido, cosechar as _cosechar, leer
    try:
        sobre = leer(archivo)
    except SobreInvalido as e:
        console.print(f"[red]sobre invalido[/red]: {e}")
        raise typer.Exit(2)
    resultado = _cosechar(sobre, raiz)
    texto = _json.dumps(resultado, ensure_ascii=False, indent=1)
    if salida:
        from pathlib import Path as _Path
        _Path(salida).parent.mkdir(parents=True, exist_ok=True)
        _Path(salida).write_text(texto, encoding="utf-8")
        console.print(f"escrito: {salida}")
    else:
        print(texto)
    # Codigo 1 cuando es hongo, para que un script lo use como compuerta.
    if resultado["tipo"] == "hongo":
        raise typer.Exit(1)


@micelio_app.command("depositar")
def micelio_depositar(
    archivo: str = typer.Argument(..., help="Sobre `semilla` o `nutriente` a depositar."),
    cola: str = typer.Option("", "--cola", help="material.jsonl del organismo (por defecto ~/plataforma/material.jsonl)."),
    depto: str = typer.Option("codex", "--depto", help="Departamento que la trabaja: codex o research."),
    aplicar: bool = typer.Option(False, "--aplicar", help="Escribir de verdad en la cola."),
):
    """Mete el sobre en la cola de trabajo del organismo.

    Este es el eslabon que faltaba. El formato existia, el organismo existia, y
    entre los dos no habia nada: una semilla validada se quedaba en un archivo
    que nadie leia. `material.jsonl` es la cola que `trabajo.py` consume ANTES
    que las fuentes autonomas, asi que depositar ahi es lo que hace que la
    semilla se trabaje sola.

    Dos cosas viajan al organismo y las dos importan:

    - el CRITERIO va dentro del texto de la tarea. Quien la ejecuta es un
      modelo debil sin supervision: si no le decis como se lo va a medir, no
      puede saber si termino.
    - el sobre queda guardado al lado de la cola, asi que `micelio verificar`
      puede correr el mismo criterio despues, contra el trabajo real.
    """
    import json as _json
    import hashlib as _hashlib
    from pathlib import Path as _Path
    from .micelio import SobreInvalido, leer
    try:
        sobre = leer(archivo)
    except SobreInvalido as e:
        console.print(f"[red]sobre invalido[/red]: {e}")
        raise typer.Exit(2)
    if sobre.get("tipo") not in ("semilla", "nutriente"):
        console.print("[red]solo se depositan semillas y nutrientes[/red]; "
                      f"este es `{sobre.get('tipo')}`")
        raise typer.Exit(2)
    if depto not in ("codex", "research"):
        console.print("[red]--depto tiene que ser codex o research[/red]")
        raise typer.Exit(2)

    ruta_cola = _Path(cola) if cola else _Path.home() / "plataforma" / "material.jsonl"
    cuerpo = _json.dumps(sobre.get("cuerpo") or {}, ensure_ascii=False, indent=1)
    criterio = _json.dumps(sobre.get("criterio") or [], ensure_ascii=False, indent=1)
    texto = (
        f"{sobre['asunto']}\n\nQUE HAY QUE HACER:\n{cuerpo}\n\n"
        "COMO SE VA A MEDIR (esto se corre tal cual, no es una sugerencia):\n"
        f"{criterio}\n\n"
        "No entregues hasta que ese criterio de verde. Si no podes hacerlo dar "
        "verde, decilo y decir por que es una entrega valida; inventar que "
        "funciona no lo es."
    )
    tarea = {
        "id": _hashlib.sha1(texto.encode("utf-8")).hexdigest()[:12],
        "origen": "micelio",
        "depto": depto,
        "modo": depto,
        "texto": texto,
        "estado": "pendiente",
        "sobre": sobre["asunto"][:120],
    }

    if not aplicar:
        console.print(f"[yellow]ensayo[/yellow]: no se escribio nada. "
                      f"Iria a {ruta_cola} como tarea {tarea['id']} "
                      f"para {depto}, {len(texto)} caracteres.")
        console.print("Para depositarla de verdad: --aplicar")
        return

    ruta_cola.parent.mkdir(parents=True, exist_ok=True)
    # Dedup por id: depositar dos veces la misma semilla no la trabaja dos
    # veces. La cola ya deduplica por hash del texto y esto respeta lo mismo.
    existentes = set()
    if ruta_cola.exists():
        for linea in ruta_cola.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if not linea:
                continue
            try:
                existentes.add(_json.loads(linea).get("id"))
            except ValueError:
                continue
    if tarea["id"] in existentes:
        console.print(f"[yellow]ya estaba en la cola[/yellow] ({tarea['id']}): "
                      "no se duplica")
        return
    with ruta_cola.open("a", encoding="utf-8") as fh:
        fh.write(_json.dumps(tarea, ensure_ascii=False) + "\n")
    guardado = ruta_cola.parent / f"sobre-{tarea['id']}.json"
    guardado.write_text(_json.dumps(sobre, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    console.print(f"[green]depositada[/green] {tarea['id']} en {ruta_cola} "
                  f"para {depto}")
    console.print(f"el sobre quedo en {guardado.name}; para el semaforo: "
                  f"py -m flujo micelio verificar {guardado}")


suplementos_app = typer.Typer(help="Generación de contraportadas para suplementos RD.", no_args_is_help=True)
app.add_typer(suplementos_app, name="suplementos")

rd_app = typer.Typer(help="Base de datos RD: reactivos, packs, suplementos, productoras, eventos.", no_args_is_help=True)
app.add_typer(rd_app, name="rd-db")


@rd_app.command("build")
def rd_build(
    canonical_source: Optional[str] = typer.Option(
        None,
        "--canonical-source",
        help="Promueve una candidata RD completa validada de 92 tablas.",
    ),
):
    """Construye la proyección portable o promueve una fuente RD completa."""
    from .rd import build_rd_db

    path = build_rd_db(canonical_source=canonical_source)
    _ok(f"RD DB construida: {path}")


@rd_app.command("reactivo")
def rd_reactivo(
    familia: str = typer.Option("", "--familia", "-f", help="Filtra por familia de sustancia (ej. MDMA)"),
    reactivo: str = typer.Option("", "--reactivo", "-r", help="Filtra por reactivo (ej. Marquis)"),
):
    """Consulta la colorimetria presuntiva. El test es PRESUNTIVO: indica familia
    posible, no identifica ni mide pureza."""
    from .rd import disclaimer, reactivos_por_familia, reactivos_por_reactivo

    if familia:
        filas = reactivos_por_familia(familia)
    elif reactivo:
        filas = reactivos_por_reactivo(reactivo)
    else:
        _warn("Usa --familia MDMA o --reactivo Marquis")
        raise typer.Exit(1)
    _section("flujo · rd · reactivos")
    for f in filas:
        console.print(f"  {f['reactivo']:<12} {f['familia']:<20} {f['reaccion']:<24} {f['hex']}")
    console.print(f"\n[dim]{disclaimer()}[/]")


@rd_app.command("packs")
def rd_packs():
    """Lista los packs de servicio con precio e inclusiones."""
    from .rd import packs as _packs

    _section("flujo · rd · packs")
    for p in _packs():
        console.print(f"  [bold]{p['id']}[/] {p['nombre']} -- ${p['precio']:,} CLP ({p['voluntarios']} vol)")
        for inc in p["inclusiones"]:
            console.print(f"      - {inc}")


@rd_app.command("eventos")
def rd_eventos():
    """Lista los eventos registrados con su pack sugerido."""
    from .rd import eventos as _eventos

    _section("flujo · rd · eventos")
    for e in _eventos():
        pack = e["pack_sugerido"] or "(sin match)"
        console.print(f"  {e['nombre']}  |  {e['voluntarios']} vol -> {pack}  |  {e['fuente']}")


@rd_app.command("testeos")
def rd_testing():
    """Show only the internal summary of imported testing evidence.

    It exposes no observations and does not turn colors into public claims.
    """
    from .rd import testing_evidence_summary

    res = testing_evidence_summary()
    _section("flujo · rd · evidencia de testeos")
    if not res.get("available"):
        _warn("No hay evidencia de testeos importada")
        return
    source = res["source"]
    console.print(f"  Fuente: {source['file_name']}  | SHA-256: {source['sha256']}")
    for key, value in res["counts"].items():
        console.print(f"  {key}: {value}")
    console.print(f"\n[dim]Estado: {res['status']}; publicación automática: no.[/]")


@rd_app.command("productora")
def rd_productora(slug: str = typer.Argument(..., help="Slug de la productora, ej. thegrid")):
    """Perfil completo: instagram, aliases, tipos de fecha, venues (preferido
    marcado) y logos."""
    from .rd import productora as _productora

    p = _productora(slug)
    if p is None:
        _warn(f"No hay productora '{slug}' (ver data/productoras/)")
        raise typer.Exit(1)
    _section(f"flujo · rd · productora · {p['nombre']}")
    console.print(f"  Instagram: {p.get('instagram') or '-'}")
    console.print(f"  Aliases: {', '.join(p['aliases']) or '-'}")
    console.print(f"  Tipos de fecha: {', '.join(p['tipos_fecha']) or '-'}")
    if p["venues"]:
        console.print("  Venues:")
        for v in p["venues"]:
            estrella = "* " if v["preferido"] else "  "
            canon = " (canonico)" if v["venue_id"] else ""
            console.print(f"    {estrella}{v['venue_nombre']}{canon} [{v['estado']}]", markup=False)
    else:
        console.print("  Venues: (sin confirmar)")
    for lg in p["logos"]:
        console.print(f"  Logo: {lg['logo_id']} ({lg['estado']}) -> {lg['knowledge']}")


@rd_app.command("venues")
def rd_venues():
    """Venues canonicos con preset recomendado y voluntarios minimos."""
    from .rd import venues as _venues

    _section("flujo · rd · venues")
    for v in _venues():
        vmin = v.get("voluntarios_min") or "?"
        console.print(f"  {v['nombre']:<24} {v.get('tipo') or '-':<20} preset={v.get('preset_reco') or '-'}  vol_min={vmin}")


@rd_app.command("por-tipo")
def rd_por_tipo(tipo: str = typer.Argument(..., help="Tipo de fecha, ej. RAVE, FESTIVAL, AFTER")):
    """Que productoras hacen fechas de un tipo dado."""
    from .rd import productoras_por_tipo

    slugs = productoras_por_tipo(tipo)
    _section(f"flujo · rd · por-tipo · {tipo.upper()}")
    if not slugs:
        _warn(f"Ninguna productora registrada con tipo '{tipo}'")
        return
    for s in slugs:
        console.print(f"  {s}")


@rd_app.command("lookup")
def rd_lookup(familia: str = typer.Argument(..., help="Familia de sustancia, ej. MDMA")):
    """Consulta de operador en terreno: reactivos que marcan la familia + packs
    que incluyen testeo + disclaimer, en una sola vista (JOIN reactivos+packs)."""
    from .rd import lookup_familia

    res = lookup_familia(familia)
    _section(f"flujo · rd · lookup · {familia}")
    if not res["reactivos"]:
        _warn(f"Sin reacciones registradas para '{familia}'")
    for f in res["reactivos"]:
        console.print(f"  {f['reactivo']:<12} {f['familia']:<20} {f['reaccion']:<24} {f['hex']}")
    packs_txt = ", ".join(f"{p['id']} (${p['precio']:,})" for p in res["packs_con_testeo"]) or "(ninguno)"
    console.print(f"\n  Testeo incluido en packs: {packs_txt}")
    console.print(f"\n[dim]{res['disclaimer']}[/]")


rd_datos_app = typer.Typer(
    help="Ingesta privacy-first de datos de campo RD (testeo, atenciones, encuestas).",
    no_args_is_help=True,
)
app.add_typer(rd_datos_app, name="rd-datos")


@rd_datos_app.command("ingest")
def rd_datos_ingest(
    csv_path: Path = typer.Argument(..., help="Ruta al CSV de terreno a ingerir"),
    tipo: str = typer.Option(..., "--tipo", "-t", help="testeo | atencion | encuesta"),
    policy: str = typer.Option(
        "strict", "--policy", "-p", help="strict (rechaza cualquier PII) | sanitize (sanitiza y persiste)"
    ),
    db: Optional[str] = typer.Option(None, "--db", help="Ruta a la DB (default data/rd.db)"),
):
    """Ingesta un CSV de datos de campo (testeo de reactivos, atenciones o
    encuestas) a la DB privacy-first data/rd.db. Toda fila pasa por
    flujo.privacy.scan_text ANTES de persistir: RUT chileno o numero de
    tarjeta detectados rechazan la fila SIEMPRE (nunca se loguea el
    contenido)."""
    from .rd.datos import ingest_csv

    if not csv_path.exists():
        _warn(f"No existe el CSV: {csv_path}")
        raise typer.Exit(1)
    try:
        res = ingest_csv(csv_path, tipo, db=db, policy=policy)
    except ValueError as e:
        _err(str(e))
        return
    _section(f"flujo · rd-datos · ingest · {tipo}")
    _ok(f"Insertadas: {res.insertadas}")
    if res.rechazadas_pii:
        _warn(f"Rechazadas por PII: {res.rechazadas_pii} (contenido nunca logueado)")
    if res.invalidas:
        _warn(f"Invalidas (forma): {res.invalidas}")
        for d in res.detalle_invalidas:
            console.print(f"    {d}", markup=False)


@rd_datos_app.command("informe")
def rd_datos_informe(
    salida: Path = typer.Option(
        ..., "--salida", "-o", help="Ruta del .md de salida (ej. reportes/informe_2026-Q3.md)"
    ),
    trimestre: Optional[str] = typer.Option(
        None, "--trimestre", "-t", help="Filtrar un trimestre: 'YYYY-Q1'..'YYYY-Q4' (default: todo el historico)"
    ),
    db: Optional[str] = typer.Option(None, "--db", help="Ruta a la DB (default data/rd.db)"),
):
    """Genera el informe trimestral de datos de campo RD (markdown): 3 tablas
    (tendencias por sustancia/mes, tasa de no-coincidencia por sustancia,
    atenciones por tipo) precedidas por el disclaimer obligatorio de
    resultados presuntivos + datos demo. Escribe el .md en --salida."""
    from .rd.informe import informe_trimestral

    try:
        md = informe_trimestral(db_path=db, trimestre=trimestre)
    except ValueError as e:
        _err(str(e))
        return
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(md, encoding="utf-8")
    _section(f"flujo · rd-datos · informe{f' · {trimestre}' if trimestre else ''}")
    _ok(f"Informe escrito: {salida}")


@app.command("tapiz")
def tapiz(modo: str = typer.Argument("demo", help="demo | stress | live")):
    """Ecosistema Tapiz<->Psicosis<->Fungi: pipeline generativo (tools/compete_engine.py).

    Cablea el cluster (compete_engine + tapiz_live_loop + telemetry + system_map)
    al CLI para que sea reachable/usable, no codigo suelto. Exporta a tools/dist/.
    """
    from .paths import repo_root

    flag = {"demo": "--demo", "stress": "--stress", "live": "--live"}.get(modo)
    if not flag:
        _warn("modo invalido: usa demo | stress | live")
        raise typer.Exit(1)
    script = repo_root() / "tools" / "compete_engine.py"
    if not script.exists():
        _warn(f"no existe {script}")
        raise typer.Exit(1)
    import subprocess

    _section(f"flujo - tapiz {modo}")
    raise typer.Exit(subprocess.call([sys.executable, str(script), flag]))


knowledge_app = typer.Typer(help="Knowledge base local: productoras, venues, logos y ejemplos.", no_args_is_help=True)
app.add_typer(knowledge_app, name="knowledge")




# ============================================================
# Helpers
# ============================================================

def _ascii(s: str) -> str:
    """Transliterate a string to ASCII-only (drops accents/non-ASCII marks)."""
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")


def _err(msg: str) -> None:
    console.print(f"[red]Error:[/] {msg}")
    raise typer.Exit(1)


def _ok(msg: str) -> None:
    console.print(f"[green]✓[/] {msg}")


def _warn(msg: str) -> None:
    console.print(f"[yellow]⚠[/] {msg}")


def _section(title: str) -> None:
    console.print()
    console.print(Panel(f"[bold green]{title}[/]", border_style="green"))  # brand accent-aligned (use green as proxy; prefer --accent in HTML)


def _validate_airdrop_or_exit(allow_airdrop_engine: bool = False) -> None:
    """Ejecuta el validador conservador antes de aplicar un airdrop."""
    import subprocess
    from .paths import repo_root

    root = repo_root()
    script = root / "scripts" / "validate_airdrop.py"
    if not script.exists():
        _warn("No existe scripts/validate_airdrop.py; no se pudo validar automáticamente.")
        return
    cmd = [sys.executable, str(script)]
    if allow_airdrop_engine:
        cmd.append("--allow-airdrop-engine")
    res = subprocess.run(cmd, cwd=root, text=True, capture_output=True)
    if res.stdout:
        console.print(res.stdout.rstrip())
    if res.stderr:
        console.print(res.stderr.rstrip())
    if res.returncode != 0:
        _err(
            "Validación de _airdrop/ falló. No se aplicó nada. "
            "Usa --allow-airdrop-engine solo si revisaste cambios al motor."
        )


# ============================================================
# Airdrop
# ============================================================

@airdrop_app.command("status")
def airdrop_status():
    """Muestra la versión actual del sistema flujo."""
    from .version import get_version
    v = get_version()
    console.print(f"\n[bold cyan]flujo version actual:[/] [bold]{v}[/]\n")


@airdrop_app.command("list")
def airdrop_list():
    """Lista los archivos pendientes de aplicar en _airdrop/."""
    from .airdrop import list_airdrop_files
    files = list_airdrop_files()
    if not files:
        _warn("No hay archivos pendientes en _airdrop/")
        return
    _section("Archivos en _airdrop/ (pendientes de aplicar)")
    for rel in files:
        console.print(f"  · [bold cyan]{rel}[/]")


@airdrop_app.command("dry-run")
def airdrop_dry_run():
    """Simula la aplicación del airdrop sin realizar cambios."""
    from .airdrop import scan_airdrop
    try:
        changes = scan_airdrop()
        if not changes:
            _warn("No hay archivos pendientes en _airdrop/")
            return
        _section("Simulación de Airdrop (_airdrop/)")
        for c in changes:
            color = "green" if c["status"] == "NEW" else "yellow"
            console.print(f"  [{color}]{c['status']:<8}[/] {c['rel']}")
        console.print(f"\n[bold]Total: {len(changes)} archivos serían afectados.[/]")
    except Exception as e:
        _err(str(e))


@airdrop_app.command("sign")
def airdrop_sign():
    """Genera el manifiesto SHA-256 y la firma HMAC del payload de _airdrop/.

    Requiere la clave en la variable de entorno FLUJO_AIRDROP_HMAC_KEY.
    Escribe _airdrop/_airdrop_signed_manifest.json y su .sig separado.
    """
    from .airdrop import sign_airdrop
    try:
        manifest_path, signature_path = sign_airdrop()
    except Exception as e:
        _err(str(e))
        return
    _section("Airdrop firmado")
    console.print(f"  Manifiesto: [bold cyan]{manifest_path}[/]")
    console.print(f"  Firma:      [bold cyan]{signature_path}[/]")
    _ok("Payload firmado. Verifícalo con: flujo airdrop verify")


@airdrop_app.command("verify")
def airdrop_verify():
    """Verifica la firma HMAC y los hashes SHA-256 del payload de _airdrop/.

    Nombra el archivo exacto que falla y por qué. Sale con código 1 si algo
    falla. Requiere FLUJO_AIRDROP_HMAC_KEY configurada.
    """
    from .airdrop import scan_airdrop, verify_airdrop
    problems = verify_airdrop()
    if problems:
        _section("Verificación de firma: FALLÓ")
        for p in problems:
            console.print(f"  [red]✗[/] {p}")
        _err("Firma de _airdrop/ inválida. No apliques este payload.")
        return
    total = len(scan_airdrop())
    _ok(f"Firma válida: {total} archivo(s) verificados contra el manifiesto firmado.")


@airdrop_app.command("apply")
def airdrop_apply(
    message: Optional[str] = typer.Argument(
        None, help="Mensaje del checkpoint (ej. 'fix airdrop cli')"
    ),
    skip_validation: bool = typer.Option(
        False, "--skip-validation", help="omitir scripts/validate_airdrop.py"
    ),
    allow_airdrop_engine: bool = typer.Option(
        False,
        "--allow-airdrop-engine",
        help="permitir cambios al motor src/flujo/airdrop.py tras revisión explícita",
    ),
    allow_unsigned: bool = typer.Option(
        False,
        "--allow-unsigned",
        help=(
            "aprobación humana explícita: aplicar un payload sin firma válida "
            "aunque FLUJO_AIRDROP_HMAC_KEY esté configurada (solo tras revisión "
            "manual; nunca automatizado)"
        ),
    ),
):
    """Aplica los archivos de _airdrop/, crea backup y dispara checkpoint + push."""
    from .airdrop import apply_airdrop, run_auto_checkpoint, scan_airdrop
    try:
        pending = scan_airdrop()
        if not pending:
            _warn("No hay archivos pendientes en _airdrop/")
            return

        if not skip_validation:
            _validate_airdrop_or_exit(allow_airdrop_engine=allow_airdrop_engine)

        changes = apply_airdrop(allow_unsigned=allow_unsigned)

        _section("Airdrop Aplicado")
        for c in changes:
            console.print(f"  [green]✓[/] {c['rel']}")

        _ok("Archivos aplicados exitosamente.")

        # --- AUTOMATIZACIÓN: backup -> apply -> checkpoint -> push ---
        console.print("\n[cyan]Ejecutando auto-checkpoint y push...[/]")
        if run_auto_checkpoint(message):
            _ok("Checkpoint creado y cambios subidos al servidor.")
        else:
            _warn("No se pudo realizar el auto-checkpoint. Por favor, hazlo manualmente.")

        _section("Proceso Completado")
        console.print("[bold green]Airdrop está activo y sincronizado.[/]")

    except Exception as e:
        _err(str(e))


@airdrop_app.command("rollback")
def airdrop_rollback():
    """Revierte los cambios al último backup de airdrop."""
    from .airdrop import rollback_last
    backup = rollback_last()
    if not backup:
        _err("No se encontró ningún backup para revertir.")
    _ok(f"Rollback completado desde: {backup.name}")


@airdrop_app.command("finish")
def airdrop_finish():
    """Finaliza el proceso de airdrop (estatus y sugerencias)."""
    _section("Finalización de Airdrop")
    import subprocess
    try:
        # Usar git status --short para mostrar cambios
        res = subprocess.run(["git", "status", "--short"], capture_output=True, text=True)
        console.print(res.stdout if res.stdout else "No hay cambios pendientes en git.")
    except Exception:
        _warn("No se pudo ejecutar git status.")

    console.print("\n[bold cyan]Pasos recomendados:[/]")
    console.print("  1. Revisar cambios: [bold]git diff[/]")
    console.print("  2. Commit y push (o [bold]flujo airdrop[/] si no tienes push directo).")


# ============================================================
# Salud / info
# ============================================================

@app.command("health")
def health():
    """Chequeo general del repo."""
    from .paths import repo_root
    from .jobs.job import list_jobs

    root = repo_root()
    _section("flujo · health check")

    console.print(f"[cyan]Repo root:[/] {root}")
    console.print(f"[cyan]Versión:[/] {_get_version()}")
    console.print()

    # existence checks
    required = ["jobs", "inbox", "projects", "scripts", "tools", "docs"]
    for sub in required:
        path = root / sub
        status = "[green]OK[/]" if path.exists() else "[yellow]falta[/]"
        console.print(f"  {sub:<12} {status}")

    # jobs
    jobs = list_jobs()
    console.print(f"\n[cyan]Jobs:[/] {len(jobs)}")
    for j in jobs[:5]:
        console.print(f"  · {j.name} [{j.estado}] ({j.pendientes} pendientes)")

    # indices
    db = root / "data" / "flujo.db"
    if db.exists():
        console.print(f"\n[cyan]Index:[/] {db}")
    else:
        _warn("Index no existe. Ejecutar: flujo index --rebuild")



@app.command("ai-prompt")
def ai_prompt(
    text: str = typer.Argument("", help="Texto a procesar"),
    area: str = typer.Option("suplementos", "--area", "-a", help="suplementos | eventos | general"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Ruta de archivo para guardar el prompt"),
):
    """Genera un prompt listo para copiar en una IA web y convertir pedidos en briefs/cotizaciones."""
    prompt = build_remote_ai_prompt(text, area=area)
    target = write_remote_ai_prompt(output, prompt)
    if target is not None:
        _ok(f"prompt guardado en {target}")
    typer.echo(prompt)


@app.command("github-sync")
def github_sync(
    status: bool = typer.Option(False, "--status", help="Mostrar rama, remoto y estado local"),
    push: bool = typer.Option(False, "--push", help="Crear commit y subir cambios a GitHub"),
    branch: Optional[str] = typer.Option(None, "--branch", help="Rama a usar para el push"),
    message: Optional[str] = typer.Option(None, "--message", "-m", help="Mensaje del commit cuando se usa --push"),
):
    """Sincroniza el repo local con GitHub de forma simple y segura."""
    import subprocess

    from .paths import repo_root

    root = repo_root()
    _section("GitHub sync")

    def run_git(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=root,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
        )

    branch_name = branch or (run_git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip() or "main")
    upstream = run_git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
    remote_name = ""
    if upstream.returncode == 0 and "/" in upstream.stdout.strip():
        remote_name = upstream.stdout.strip().split("/", 1)[0]
    if not remote_name:
        remotes = run_git("remote")
        names = remotes.stdout.splitlines() if remotes.returncode == 0 else []
        remote_name = "origin" if "origin" in names else (names[0] if names else "")
    remote = run_git("remote", "get-url", remote_name) if remote_name else None
    if remote is not None and remote.returncode == 0:
        console.print(f"[cyan]Remote ({remote_name}):[/] {remote.stdout.strip()}")
    else:
        _warn("No hay remote configurado para este checkout.")

    console.print(f"[cyan]Branch:[/] {branch_name}")
    status_proc = run_git("status", "--short")
    status_failed = status_proc.returncode != 0
    if status_failed:
        _warn("No se pudo medir el working tree: `git status --short` salio con "
              f"codigo {status_proc.returncode}. "
              + (status_proc.stderr.strip().splitlines()[-1]
                 if status_proc.stderr.strip() else "sin mensaje de git")
              + ". NO se afirma que este limpio.")
    elif status_proc.stdout.strip():
        console.print("[yellow]Cambios locales:[/]")
        for line in status_proc.stdout.strip().splitlines():
            console.print(f"  {line}")
    else:
        _ok("Working tree limpio.")

    if not push:
        if status_failed:
            _warn("Estado de GitHub NO verificado: la medicion del working tree fallo.")
            raise typer.Exit(1)
        _ok("Estado de GitHub preparado. Usa --push para sincronizar con GitHub.")
        return

    if not message:
        message = "chore: sync local changes"

    if status_proc.stdout.strip():
        add_res = run_git("add", "-A")
        if add_res.returncode != 0:
            _err(add_res.stderr.strip() or add_res.stdout.strip() or "No se pudo stagear el cambio.")
        commit_res = run_git("commit", "-m", message)
        if commit_res.returncode != 0:
            if "nothing to commit" in (commit_res.stdout + commit_res.stderr).lower():
                _warn("No había cambios nuevos para commitear.")
            else:
                _err(commit_res.stderr.strip() or commit_res.stdout.strip() or "No se pudo crear el commit.")
    else:
        _warn("No hay cambios para commitear.")

    if not remote_name:
        _err("No hay remote configurado; no se puede hacer el push.")
    push_res = run_git("push", "-u", remote_name, branch_name)
    if push_res.returncode != 0:
        _err(push_res.stderr.strip() or push_res.stdout.strip() or "No se pudo hacer el push.")

    _ok(f"Sincronizado con GitHub en la rama {branch_name}.")


@app.command("doctor")
def doctor():
    """Diagnóstico humano del entorno local: Python, Git, encoding, index, hub y airdrop.

    A diferencia de `verify`, no ejecuta tests pesados. Sirve para saber rápido
    si una máquina nueva / Windows / clon fresco está listo para trabajar.
    """
    import locale
    import socket
    import subprocess

    from .paths import repo_root, workspace_root, inbox_dir, jobs_dir, datadrops_dir

    root = repo_root()
    workspace = workspace_root()
    rows: list[tuple[str, str, str]] = []

    def add(name: str, ok: bool, detail: str = "") -> None:
        rows.append((name, "OK" if ok else "AVISO", detail))

    _section("flujo · doctor")
    add("versión", True, _get_version())
    add("python", sys.version_info >= (3, 10), sys.executable)
    enc = (getattr(sys.stdout, "encoding", None) or locale.getpreferredencoding(False) or "").lower()
    add("encoding stdout", "utf" in enc, enc or "desconocido")
    add("repo root", root.exists(), str(root))
    add("workspace", workspace.exists(), str(workspace))
    add("jobs/", jobs_dir().exists(), str(jobs_dir()))
    add("inbox/", inbox_dir().exists(), str(inbox_dir()))
    add("datadrops/", datadrops_dir().exists(), str(datadrops_dir()))
    add("index db", (root / "data" / "flujo.db").exists(), "opcional; crear con `flujo index --rebuild`")
    airdrop_dir = root / "_airdrop"
    pending = airdrop_dir.exists() and any(p.is_file() for p in airdrop_dir.rglob("*"))
    add("airdrop pendiente", not pending, "hay archivos en _airdrop/" if pending else "no")

    try:
        branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace")
        add("git branch", branch.returncode == 0, branch.stdout.strip() or branch.stderr.strip())
        upstream = subprocess.run(["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"], cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace")
        remote_name = ""
        if upstream.returncode == 0 and "/" in upstream.stdout.strip():
            remote_name = upstream.stdout.strip().split("/", 1)[0]
        if not remote_name:
            remotes = subprocess.run(["git", "remote"], cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace")
            names = remotes.stdout.splitlines() if remotes.returncode == 0 else []
            remote_name = "origin" if "origin" in names else (names[0] if names else "")
        remote = subprocess.run(["git", "remote", "get-url", remote_name], cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace") if remote_name else None
        if remote is None:
            add("git remote", False, "No hay remote configurado")
        else:
            add("git remote", remote.returncode == 0, f"{remote_name}: {(remote.stdout or remote.stderr).strip()}")
        status = subprocess.run(["git", "status", "--short"], cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if status.returncode != 0:
            detail = status.stderr.strip() or status.stdout.strip() or "sin mensaje de git"
            add("git working tree", False,
                f"No se pudo medir (codigo {status.returncode}): {detail}")
        else:
            dirty = bool(status.stdout.strip())
            add("git working tree", not dirty,
                "limpio" if not dirty else "hay cambios locales")
    except Exception as e:
        add("git", False, str(e))

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        add("puertos locales", True, f"puerto libre detectado: {port}")
    except Exception as e:
        add("puertos locales", False, str(e))

    # The web build declares a Node minimum in web/package.json. Measured on
    # 2026-08-21: PATH resolved 18.20.4, Vite warned, and the 20.x/24.x installs
    # that satisfy the requirement sat unlisted on the same machine. Doctor is
    # the entrypoint that already runs probes, so it names the binary to use
    # instead of leaving the build to warn and the caller to guess.
    try:
        from .knowledge.runtime_tools import declared_node_minimum, node_candidates

        spec = declared_node_minimum(root)
        wanted = tuple(int(part) for part in
                       spec.lstrip(">=~^ ").split("-")[0].split(".")[:3]) if spec else ()

        def _probe(binary: Path) -> tuple[int, ...]:
            out = subprocess.run([str(binary), "--version"], capture_output=True,
                                 text=True, encoding="utf-8", errors="replace",
                                 timeout=30)
            if out.returncode != 0:
                return ()
            raw = (out.stdout or "").strip().lstrip("v")
            try:
                return tuple(int(part) for part in raw.split(".")[:3])
            except ValueError:
                return ()

        found = node_candidates(root)
        if not found:
            add("node", False, f"no se encontro node; el build web pide {spec or 'sin minimo declarado'}")
        else:
            versions = {}
            for binary in found:
                try:
                    versions[binary] = _probe(binary)
                except Exception:
                    versions[binary] = ()
            active = found[0]
            active_version = versions.get(active, ())
            shown = ".".join(str(part) for part in active_version) or "desconocida"
            if not wanted:
                add("node", bool(active_version), f"{active} v{shown}; web/package.json no declara minimo")
            elif active_version >= wanted:
                add("node", True, f"{active} v{shown} cumple {spec}")
            else:
                better = next((b for b, v in versions.items() if v and v >= wanted), None)
                detail = (f"activo {active} v{shown} esta bajo {spec}")
                if better is not None:
                    good = ".".join(str(part) for part in versions[better])
                    detail += f"; usa NODE_EXE={better} (v{good})"
                else:
                    detail += "; ningun node local cumple el minimo"
                add("node", False, detail)
    except Exception as e:
        add("node", False, str(e))

    table = Table(title="Diagnóstico local")
    table.add_column("Check")
    table.add_column("Estado")
    table.add_column("Detalle")
    for name, status, detail in rows:
        style = "green" if status == "OK" else "yellow"
        table.add_row(name, f"[{style}]{status}[/]", detail)
    console.print(table)

    if any(status != "OK" for _, status, _ in rows):
        _warn("Doctor terminó con avisos (no necesariamente errores).")
    else:
        _ok("Doctor OK: entorno listo.")


@app.command("diagnose")
def diagnose(
    area: str = typer.Option("auto", "--area", "-a", help="auto | core | rd | portfolio | cultura | research"),
    idea: str = typer.Option("", "--idea", "-i", help="Idea o incidente para rutear el contexto."),
    operation: str = typer.Option("", "--operation", help="Operacion que fallo."),
    error: str = typer.Option("", "--error", help="Error o traceback breve; se sanitiza antes de imprimir."),
    error_file: Optional[Path] = typer.Option(None, "--error-file", help="Archivo de error; solo se lee y se acota."),
    command: str = typer.Option("", "--command", help="Comando reproducible, no se ejecuta."),
    expected: str = typer.Option("", "--expected", help="Resultado esperado."),
    observed: str = typer.Option("", "--observed", help="Resultado observado."),
    output_format: str = typer.Option("markdown", "--format", help="markdown | json"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Escribe el reporte en esta ruta."),
):
    """Genera un reporte local, sanitizado y copiable para otro agente.

    Este comando solo inspecciona metadatos, Git y rutas del packet elegido.
    Nunca ejecuta el comando recibido en --command ni abre el archivo WIN.
    """
    import json as _json

    from .diagnostics import build_diagnostic_report, render_markdown

    if output_format not in {"markdown", "json"}:
        raise typer.BadParameter("debe ser markdown o json", param_hint="--format")
    if error_file is not None:
        try:
            error = error_file.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            raise typer.BadParameter(str(exc), param_hint="--error-file") from exc
    report = build_diagnostic_report(
        area=area,
        idea=idea,
        operation=operation,
        error=error,
        command=command,
        expected=expected,
        observed=observed,
    )
    rendered = (
        _json.dumps(report, ensure_ascii=False, indent=2)
        if output_format == "json"
        else render_markdown(report)
    )
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
        _ok(f"Reporte {output_format} guardado en {output}")
        return
    # Plain stdout is deliberate: the user can paste it into an external agent.
    typer.echo(rendered, nl=not rendered.endswith("\n"))


@app.command("route")
def route(
    text: str = typer.Argument(..., help="Idea o incidente que necesita contexto."),
    area: str = typer.Option("auto", "--area", "-a", help="auto | core | rd | portfolio | cultura | research"),
    output_format: str = typer.Option("markdown", "--format", help="markdown | json"),
):
    """Selecciona el packet minimo para una idea sin leer todo el repo."""
    import json as _json

    from .diagnostics import render_route_markdown, route_idea

    if output_format not in {"markdown", "json"}:
        raise typer.BadParameter("debe ser markdown o json", param_hint="--format")
    routed = route_idea(text, area=area)
    if output_format == "json":
        typer.echo(_json.dumps(routed, ensure_ascii=False, indent=2))
    else:
        typer.echo(render_route_markdown(routed), nl=False)


def _run_verify_subprocess(label: str, cmd: list[str], cwd: Path) -> None:
    import subprocess

    console.print(f"\n[cyan]> {label}[/] {' '.join(cmd)}")
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        _err(f"verify falló en {label} (código {proc.returncode})")


@app.command("verify")
def verify(
    run_pytest: bool = typer.Option(True, "--pytest/--no-pytest", help="ejecutar pytest"),
    hub_smoke: bool = typer.Option(True, "--hub-smoke/--no-hub-smoke", help="probar servidor hub + SSE + seguridad static"),
):
    """Verificación integral local/CI: compileall, tests, health, version y hub smoke.

    Es el comando único para responder: "¿el repo está sano después de un
    airdrop/cambio?". En CI se recomienda correrlo en Linux y Windows.
    """
    from .paths import repo_root

    root = repo_root()
    _section("flujo · verify")
    console.print(f"[cyan]Repo root:[/] {root}")
    console.print(f"[cyan]Python:[/] {sys.executable}")

    compile_targets = ["src", "scripts", "tests"]
    generator = root / "tools" / "piezas_vectoriales" / "scripts" / "generar_desde_json.py"
    if generator.exists():
        compile_targets.append(str(generator.relative_to(root)))
    _run_verify_subprocess(
        "compileall",
        [sys.executable, "-m", "compileall", "-q", *compile_targets],
        root,
    )
    if run_pytest:
        # -rs: los motivos de los saltos SE IMPRIMEN. Sin eso, un guardian que
        # se salta y uno que mide se ven igual de verdes -- el 2026-07-30 la
        # matriz quedo verde saltandose los 16 iconos y hubo que ir a contar
        # puntos en el log para notarlo.
        _run_verify_subprocess(
            "pytest", [sys.executable, "-m", "pytest", "tests/", "-q", "-rs"], root)
    _run_verify_subprocess("health", [sys.executable, "-m", "flujo", "health"], root)
    _run_verify_subprocess("version", [sys.executable, "-m", "flujo", "version"], root)
    if hub_smoke:
        smoke = root / "scripts" / "hub_smoke.py"
        if smoke.exists():
            _run_verify_subprocess("hub smoke", [sys.executable, str(smoke)], root)
        else:
            _warn("scripts/hub_smoke.py no existe; se omite hub smoke")

    _ok("verify OK")


@app.command()
def version():
    """Muestra versión y changelog."""
    from .version import get_version, get_changelog
    v = get_version()
    _section(f"flujo · versión {v}")
    changelog = get_changelog()
    for ver, info in changelog.items():
        console.print(f"\n[bold cyan]v{ver}[/] — {info['titulo']} ({info['fecha']})")
        for h in info.get("highlights", []):
            console.print(f"  · {h}")


@app.command("delegate")
def delegate(
    role: str = typer.Argument(..., help="creative-director | visual-polish | pipeline | brand | future | packaging"),
    task: str = typer.Argument(..., help="Descripción precisa de la tarea a delegar"),
):
    """Genera prompt preciso para delegar a agente especializado (5 roles; soporta paralelo via hub o clones).
    Salida lista para copiar a otra sesión IA. Ideal para multi-agente workflow.

    Ej:
      flujo delegate future "Añadir WebSocket real-time previews al hub"
      flujo delegate visual-polish "Pulir plano_demo.html con brand exacto"
    """
    # Reuse logic from web hub for consistency (single source)
    try:
        from .web.hub import HubRequestHandler
        # Instantiate minimally for _handle_delegate
        h = HubRequestHandler.__new__(HubRequestHandler)
        h.root = None  # not needed
        result = h._handle_delegate({"role_id": role, "task": task})
        role_info = result["role"]
        console.print(Panel(f"[bold]{role_info['name']}[/]", border_style="cyan"))
        console.print(f"[dim]Task:[/] {result['task']}")
        console.print("\n[bold green]Prompt listo para pegar en sub-agente:[/]\n")
        console.print(result["full_prompt"])
        console.print("\n[dim]Lanza el trabajo en un entorno aislado y verifica el resultado antes de integrarlo.[/dim]")
    except Exception as e:
        _err(f"No se pudo generar delegación: {e}")


def _get_version() -> str:
    from .version import get_version
    return get_version()


# ============================================================
# Brand (flujo) — Identidad visual + análisis de ejemplos
# ============================================================

@datadrop_app.command("list")
def datadrop_list():
    """Lista datadrops (fotos reales de entregados) desde workspace/datadrops/."""
    from .paths import datadrops_dir
    dd = datadrops_dir(create=False)
    if not dd.exists():
        _warn("No hay datadrops todavía. Usa el hub (`flujo app`) → sección Datadrop para subir fotos terminadas.")
        return
    drops = [p for p in sorted(dd.iterdir()) if p.is_dir() if p.name != "incoming" and not p.name.startswith(".")]
    if not drops:
        _warn("No hay datadrops todavía. Usa el hub (`flujo app`) → sección Datadrop para subir fotos terminadas.")
        return
    _section("Datadrops (inverse airdrop)")
    for d in drops:
        m = d / "manifest.json"
        if m.exists():
            try:
                import json as jsonlib
                info = jsonlib.loads(m.read_text(encoding="utf-8"))
                console.print(f"  {d.name}  [{info.get('type','?')}] {info.get('description','')[:40]}")
            except:
                console.print(f"  {d.name}")
        else:
            console.print(f"  {d.name} (raw)")


@datadrop_app.command("scan")
def datadrop_scan():
    """Escanea la carpeta datadrops/incoming/ y procesa las fotos convirtiéndolas en datadrops."""
    from .web.hub import scan_incoming_datadrops
    _section("Datadrop Bulk Scan")
    res = scan_incoming_datadrops()
    if res.get("ok"):
        processed = res.get("processed", 0)
        if processed > 0:
            _ok(f"Procesados {processed} datadrops exitosamente.")
            for f in res.get("files", []):
                console.print(f"  [green]✓[/green] {f}")
        else:
            _warn("No se encontraron fotos nuevas en datadrops/incoming/.")
    else:
        _err(f"Error durante el escaneo: {res.get('error', 'desconocido')}")


@datadrop_app.command("ingest")
def datadrop_ingest(file_path: Path = typer.Argument(..., help="archivo PDF o imagen a importar como referencia real")):
    """Importar un PDF o imagen como datadrop de referencia real."""
    from .datadrops import ingest_datadrop_reference
    if not file_path.exists():
        _err(f"No existe: {file_path}")
    out_dir = ingest_datadrop_reference(file_path)
    _ok(f"Datadrop importado: {out_dir}")
    console.print("  Revisa manifest.json + analysis/ para usarlo como ground truth visual.")


@datadrop_app.command("prepare")
def datadrop_prepare():
    """Genera paquete de revisión persistente (_review_package.txt) con manifests + notas 'for_future_ai'.
    Para que otra IA (linea_editorial) lea y sepa exactamente qué buscar en trabajos reales terminados."""
    from .paths import datadrops_dir
    import json as jsonlib
    dd = datadrops_dir()
    drops = [p for p in sorted(dd.iterdir()) if p.is_dir() if p.name != "incoming" and not p.name.startswith(".")]
    if not drops:
        _warn("No hay datadrops. Usa `flujo app` → sección Datadrop en hub para subir fotos de entregados.")
        return
    items = []
    for d in drops:
        mpath = d / "manifest.json"
        if mpath.exists():
            try:
                it = jsonlib.loads(mpath.read_text(encoding="utf-8"))
                items.append(it)
            except:
                items.append({"id": d.name, "type": "?", "description": "(manifest error)"})
        else:
            items.append({"id": d.name, "type": "raw", "description": ""})
    instructions = (
        "DATADROP REVIEW PACKAGE — Inverse airdrop for future AI review.\n"
        "Fuente: fotos reales de flyers/etiquetas/etc ya entregados por usuario.\n"
        "Usa: cada manifest.json (palette, ocr_hints, visual_traits, for_future_ai) + imagen real (datadrops/<id>/img).\n"
        "Objetivo: 'sabrá qué buscar' en briefs/análisis — patrones de paletas reales, contraste, densidad de layouts, textos OCR de entregas.\n"
        "Ej: si los datadrops muestran magenta alto contraste en flyers rave oscuros + icon grids densos, eso es lo que YA se entregó.\n"
        "Son REFERENCIA, no regla: describen lo entregado, no obligan a que la próxima pieza se vea igual.\n"
        "Privacidad: local only. Copia o cat este archivo + manifests cuando te unas a la tarea.\n"
        "Generado via hub (`flujo app`) o CLI `py -m flujo datadrop prepare`.\n\n"
    )
    summary_lines = []
    for it in items:
        summary_lines.append(f"ID: {it.get('id')}\nType: {it.get('type')}\nDesc: {it.get('description','')}\nTraits: {(it.get('visual_traits') or '')[:200]}\nForAI: {(it.get('for_future_ai') or '')[:300]}\nPalette: {str((it.get('palette') or [])[:2])}\n---")
    pkg_text = instructions + "\n".join(summary_lines) + f"\n\nTotal: {len(items)} datadrops. Dir: {str(dd)}\nRevisa imágenes directamente desde el hub o FS para ground truth visual."
    pkg_path = dd / "_review_package.txt"
    pkg_path.write_text(pkg_text, encoding="utf-8")
    _ok(f"Paquete review: {pkg_path}")
    console.print(f"  Datadrops: {len(items)}")
    console.print("  Lee el .txt + imágenes + manifests para 'saber qué buscar' (paletas reales, patrones ground-truth).")
    console.print("  Úsalo cuando mejores linea_editorial (feed real examples).")


# ============================================================
# Flyers / Instagram
# ============================================================

@app.command("flyer-import")
def flyer_import(email: Path = typer.Argument(..., help="ruta a correo.txt")):
    """Importar flyers desde correo con links de Instagram."""
    from .flyer.import_email import import_from_email
    if not email.exists():
        _err(f"No existe: {email}")
    res = import_from_email(email)
    _ok(f"Flyers creados: {res['created']} | Omitidos: {res['skipped']} | Links: {res['found']}")


@app.command("ig-redownload")
def ig_redownload(
    project: Optional[Path] = typer.Argument(None, help="proyecto flyer específico"),
    all_projects: bool = typer.Option(False, "--all", help="reintentar todos"),
):
    """Reintentar descarga de posts de Instagram que fallaron."""
    from .paths import flyer_base
    from .ig.download import download_post
    from .manifest import load_json, write_json

    base = flyer_base()
    if not base.exists():
        _err(f"No existe: {base}")

    targets = []
    if project:
        if not (project / "manifest.json").exists():
            _err(f"No es un proyecto flyer válido: {project}")
        targets = [project]
    else:
        for d in base.iterdir():
            if not d.is_dir() or not (d / "manifest.json").exists():
                continue
            targets.append(d)

    if not targets:
        _warn("No hay proyectos flyer.")
        return

    reintentos = 0
    ok = 0
    for p in targets:
        data = load_json(p / "manifest.json") or {}
        ig = data.get("instagram", {})
        if ig.get("download_status") == "downloaded":
            continue
        url = ig.get("url")
        if not url:
            continue
        reintentos += 1
        console.print(f"  · {p.name}: {url}")
        try:
            res = download_post(url, p / "input", retries=1)
            if res.get("status") == "downloaded":
                ig.update({
                    "download_status": "downloaded",
                    "manual_download_possible": False,
                    "media_type": res.get("media_type", ""),
                    "file_count": res.get("file_count", 0),
                    "owner": res.get("owner", ""),
                    "date_utc": res.get("date", ""),
                })
                data["instagram"] = ig
                write_json(p / "manifest.json", data)
                ok += 1
                _ok(f"  descargado: {p.name}")
            else:
                _warn(f"  fallo: {res.get('reason', '?')}")
        except Exception as e:
            _warn(f"  error: {e}")

    _section(f"Resultado: {ok} re-descargados de {reintentos} intentos")


@app.command()
def analyze(
    project: Optional[Path] = typer.Argument(None, help="proyecto flyer a analizar"),
    all_projects: bool = typer.Option(False, "--all", help="analizar todos"),
    force_ocr: bool = typer.Option(False, "--force-ocr", help="forzar OCR"),
):
    """Analizar colores dominantes y OCR de un proyecto flyer."""
    from .analyze.run import analyze_project, find_latest_flyer
    from .paths import flyer_base

    target = None
    if all_projects:
        base = flyer_base()
        targets = sorted([p for p in base.iterdir() if (p / "manifest.json").exists()], reverse=True)
        _section(f"Analizando {len(targets)} proyectos")
        for t in targets:
            res = analyze_project(t, force_ocr=force_ocr)
            palette = res.get("palette", {})
            colors = palette.get("colors", [])
            console.print(f"  · [cyan]{t.name}[/]: {len(colors)} colores")
        return
    else:
        target = project or find_latest_flyer()
        if not target:
            _err("No hay proyectos flyer. Crear con: flujo flyer-import")
        res = analyze_project(target, force_ocr=force_ocr)
        _section(f"Análisis: {target.name}")
        console.print(f"  status: {res.get('status')}")
        for c in res.get("palette", {}).get("colors", []):
            console.print(f"  · [bold]{c['hex']}[/] ({c['pct']*100:.1f}%)")
        if res.get("ocr", {}).get("available"):
            console.print(f"  · OCR chars: {res['ocr'].get('chars', 0)}")


@app.command()
def export(
    project: Path = typer.Argument(..., help="ruta al proyecto"),
    output: Optional[Path] = typer.Option(None, "--output", "-o"),
    for_app: str = typer.Option(
        None, "--for", "-f",
        help="preparar para: illustrator | photoshop | blender"
    ),
):
    """Exportar ZIP listo para tus herramientas (AI / PS / Blender)."""
    from .export.zipper import export_flyer
    if not (project / "manifest.json").exists():
        _err(f"No es un proyecto flyer válido: {project}")
    try:
        zip_path = export_flyer(project, output)
        _ok(f"ZIP: {zip_path}")
        if for_app:
            _ok(f"Preparado para {for_app}. Revisa la carpeta exports/ y corre el script correspondiente.")
    except Exception as e:
        _err(str(e))


# ============================================================
# Index
# ============================================================

@app.command()
def index(
    rebuild: bool = typer.Option(False, "--rebuild", help="reconstruir índice"),
    duplicates: bool = typer.Option(False, "--duplicates", help="mostrar duplicados"),
):
    """Reconstruir o consultar el índice SQLite de flyers."""
    from .index.db import rebuild_index, find_duplicates, list_flyers

    if rebuild:
        res = rebuild_index()
        _ok(f"Indexados: {res['indexed']} flyers")
    elif duplicates:
        dups = find_duplicates()
        if not dups:
            _ok("Sin duplicados.")
        else:
            for d in dups:
                _warn(f"shortcode {d['shortcode']}: {d['c']} proyectos")
                for p in d["paths"].split("|"):
                    console.print(f"    {p}")
    else:
        rows = list_flyers(limit=50)
        table = Table(title=f"Flyers ({len(rows)})")
        for col in ("name", "shortcode", "owner", "status", "media_type"):
            table.add_column(col)
        for r in rows:
            table.add_row(
                str(r.get("name", ""))[:40],
                str(r.get("shortcode", ""))[:20],
                str(r.get("owner", ""))[:20],
                str(r.get("status", "")),
                str(r.get("media_type", "")),
            )
        console.print(table)


@app.command("code-index")
def code_index(
    root: Optional[Path] = typer.Option(None, "--root", help="raíz del árbol Python"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="JSON del índice"),
    query: str = typer.Option("", "--query", "-q", help="consulta estructural"),
    output_format: str = typer.Option("json", "--format", help="json | markdown"),
):
    """Crear un índice AST consultable sin incluir texto fuente."""
    import json as _json

    from .index.code_index import (
        DEFAULT_OUTPUT,
        build_index,
        make_brief,
        render_brief,
        save_index,
    )

    if output_format not in {"json", "markdown"}:
        raise typer.BadParameter("debe ser json o markdown", param_hint="--format")
    base = (root or Path(__file__).resolve().parents[2]).expanduser().resolve()
    structure = build_index(base)
    target = (output or (base / DEFAULT_OUTPUT)).expanduser()
    saved = save_index(structure, target)
    brief = make_brief(structure, query)
    brief["output"] = str(saved)
    brief["index_schema"] = structure["schema"]
    if output_format == "markdown":
        typer.echo(render_brief(brief), nl=False)
    else:
        typer.echo(_json.dumps(brief, ensure_ascii=True, indent=2))


@app.command("flyer-list")
def flyer_list(
    status: Optional[str] = typer.Option(None, "--status", help="filtrar por status"),
    limit: int = typer.Option(50, "--limit", "-n"),
):
    """Listar flyers indexados."""
    from .index.db import list_flyers
    rows = list_flyers(status=status, limit=limit)
    table = Table(title=f"Flyers (status={status or '*'})")
    for col in ("name", "shortcode", "owner", "status", "media_type", "date_utc"):
        table.add_column(col)
    for r in rows:
        table.add_row(
            str(r.get("name", ""))[:40],
            str(r.get("shortcode", ""))[:20],
            str(r.get("owner", ""))[:20],
            str(r.get("status", "")),
            str(r.get("media_type", "")),
            str(r.get("date_utc", ""))[:10],
        )
    console.print(table)


# ============================================================
# Jobs
# ============================================================

@job_app.command("new")
def job_new(
    name: str = typer.Argument(..., help="nombre del pedido"),
    email: Optional[Path] = typer.Option(None, "--email", "-e", help="archivo de correo/texto fuente"),
):
    """Crear un nuevo job desde un nombre (y opcionalmente texto fuente)."""
    from .jobs.job import create_job
    job = create_job(name, source_path=email)
    _ok(f"Job creado: {job}")
    console.print(f"  Siguiente: [cyan]flujo job prepare {job}[/]")


@job_app.command("prepare")
def job_prepare(
    job: Path = typer.Argument(..., help="ruta al job"),
    no_privacy: bool = typer.Option(False, "--no-privacy", help="omitir paso de privacidad"),
):
    """Pipeline: privacidad → brief → estado."""
    from .jobs.lifecycle import prepare_job
    if not job.exists():
        _err(f"No existe: {job}")
    res = prepare_job(job, run_privacy=not no_privacy)
    if not res.ok:
        for e in res.errors:
            _warn(e)
    _section(f"Job: {job.name}")
    console.print(f"  estado inicial: {res.estado_inicial.value}")
    console.print(f"  estado final:   [bold]{res.estado_final.value}[/]")
    if res.privacy_report:
        console.print(f"  privacy_report: {res.privacy_report}")
    for s in res.steps:
        console.print(f"  · {s}")


@job_app.command("list")
def job_list(
    examples: bool = typer.Option(False, "--examples", help="incluir _examples"),
    status: Optional[str] = typer.Option(None, "--status", help="filtrar por estado"),
):
    """Listar jobs y sus estados."""
    from .jobs.job import list_jobs
    items = list_jobs(include_examples=examples)
    if status:
        items = [j for j in items if j.estado == status]
    if not items:
        _warn("No hay jobs.")
        return
    table = Table(title=f"Jobs ({len(items)})")
    for col in ("name", "estado", "tipo", "proyecto", "pendientes"):
        table.add_column(col)
    for j in items:
        table.add_row(j.name, j.estado, j.tipo_pieza or "?", j.proyecto or "?", str(j.pendientes))
    console.print(table)


@job_app.command("status")
def job_status_cmd(
    job: Path = typer.Argument(..., help="ruta al job"),
):
    """Estado detallado de un job."""
    from .jobs.brief import load_brief
    from .jobs.lifecycle import suggest_next_action
    if not job.exists():
        _err(f"No existe: {job}")
    brief_path = job / "brief.yaml"
    if not brief_path.exists():
        _err(f"No hay brief.yaml en {job}")
    brief = load_brief(brief_path)
    _section(f"Job: {job.name}")
    console.print(f"  estado:        [bold]{brief.estado.value}[/]")
    console.print(f"  cliente:       {brief.cliente or '-'}")
    console.print(f"  proyecto:      {brief.proyecto or '-'}")
    console.print(f"  tipo_pieza:    {brief.tipo_pieza or '-'}")
    console.print(f"  medida:        {brief.medidas.ancho_cm or '?'}x{brief.medidas.alto_cm or '?'} cm")
    productos_txt = []
    for producto in brief.productos:
        if isinstance(producto, dict):
            nombre = producto.get("nombre") or producto.get("name") or producto.get("id")
            if nombre is None:
                nombre = str(producto)
            amount = producto.get("valor_dia_clp")
            if amount is not None:
                nombre = f"{nombre} (${amount:,} CLP)"
            productos_txt.append(str(nombre))
        else:
            productos_txt.append(str(producto))
    console.print(f"  productos:     {', '.join(productos_txt) or '-'}")
    console.print(f"  texto_aprobado: {brief.contenido.texto_aprobado}")
    console.print(f"  pendientes:    {len(brief.pendientes)}")
    for p in brief.pendientes:
        if isinstance(p, dict) and len(p) == 1:
            key, amount = next(iter(p.items()))
            p = f"{key}: {amount}"
        console.print(f"    · {p}")
    console.print(f"  próxima:       {suggest_next_action(brief)}")


@job_app.command("next")
def job_next():
    """Próximas acciones sugeridas para cada job."""
    from .jobs.job import list_jobs
    from .jobs.brief import load_brief
    from .jobs.lifecycle import suggest_next_action
    items = list_jobs()
    if not items:
        _warn("No hay jobs.")
        return
    for j in items:
        brief_path = j.path / "brief.yaml"
        try:
            brief = load_brief(brief_path)
            suggestion = suggest_next_action(brief)
        except Exception:
            suggestion = "revisar brief.yaml"
        console.print(f"  · [cyan]{j.name}[/] [{j.estado}] → {suggestion}")


@job_app.command("activate")
def job_activate(
    job: Path = typer.Argument(..., help="ruta al job"),
    project_name: Optional[str] = typer.Option(None, "--name", "-n"),
    template: Optional[str] = typer.Option(None, "--template", "-t"),
):
    """brief → proyecto en projects/piezas_vectoriales/."""
    from .jobs.lifecycle import activate_job
    if not job.exists():
        _err(f"No existe: {job}")
    res = activate_job(job, project_name=project_name, template=template)
    if not res.ok:
        for e in res.errors:
            _warn(e)
        _err("No se pudo activar el job.")
    _section(f"Job activado: {job.name}")
    if res.project_path:
        _ok(f"Proyecto: {res.project_path}")
        console.print(f"  Siguiente: [cyan]flujo render run {res.project_path / 'config.json'}[/]")


@job_app.command("report")
def job_report(
    job: Path = typer.Argument(..., help="ruta al job"),
):
    """Generar reporte detallado de un job."""
    from .jobs.lifecycle import prepare_job
    if not job.exists():
        _err(f"No existe: {job}")
    # prepare_job también escribe reporte_job.md
    res = prepare_job(job, run_privacy=False, run_brief_extract=False)
    rep = job / "reporte_job.md"
    if rep.exists():
        _ok(f"Reporte: {rep}")
        console.print(rep.read_text(encoding="utf-8"))


# ============================================================
# Privacy
# ============================================================

@privacy_app.command("scan")
def privacy_scan(
    source: Path = typer.Argument(..., help="archivo de texto a escanear"),
):
    """Escanear un texto en busca de datos personales."""
    from .privacy import scan_text, write_report
    if not source.exists():
        _err(f"No existe: {source}")
    text = source.read_text(encoding="utf-8", errors="ignore")
    scan = scan_text(text, source=str(source.name))
    _section(f"Privacidad scan: {source.name}")
    console.print(f"  riesgo:                 [bold]{scan.risk}[/]")
    console.print(f"  total_pii:              {scan.total_pii}")
    console.print(f"  requiere_sanitizacion:  {scan.requiere_sanitizacion}")
    console.print(f"  requiere_revision_humana: {scan.requiere_revision_humana}")
    console.print(f"  aprobado_para_ia_externa: {scan.aprobado_para_ia_externa}")
    if scan.matches:
        for name, matches in scan.matches.items():
            console.print(f"  · {name}: {len(matches)} ({', '.join(matches[:3])})")
    if scan.sensitive_keywords:
        console.print(f"  · keywords: {', '.join(scan.sensitive_keywords[:10])}")


@privacy_app.command("sanitize")
def privacy_sanitize(
    source: Path = typer.Argument(..., help="archivo de texto a sanitizar"),
    output: Optional[Path] = typer.Option(None, "--output", "-o"),
):
    """Sanitizar texto reemplazando PII por placeholders."""
    from .privacy import sanitize_text
    if not source.exists():
        _err(f"No existe: {source}")
    text = source.read_text(encoding="utf-8", errors="ignore")
    output = output or source.with_name(f"{source.stem}_sanitizado.txt")
    sanitize_text(text, output)
    _ok(f"Sanitizado: {output}")


@privacy_app.command("check")
def privacy_check(
    job: Path = typer.Argument(..., help="ruta al job"),
):
    """Escanear pedido_original.txt de un job + sanitizar."""
    from .privacy import scan_text, sanitize_text, write_report
    if not job.exists():
        _err(f"No existe: {job}")
    src = job / "pedido_original.txt"
    if not src.exists():
        _err(f"No hay pedido_original.txt en {job}")
    text = src.read_text(encoding="utf-8", errors="ignore")
    scan = scan_text(text, source=str(src.name))
    sanitize_text(text, job / "pedido_sanitizado.txt")
    write_report(job / "privacy_report.md", scan, source_name=str(src.name))
    _section(f"Privacy check: {job.name}")
    console.print(f"  riesgo:    {scan.risk}")
    console.print(f"  sanitizado: {job / 'pedido_sanitizado.txt'}")
    console.print(f"  reporte:    {job / 'privacy_report.md'}")


# ============================================================
# Eventos
# ============================================================

@eventos_app.command("flyer-auto")
def eventos_flyer_auto(
    url: str = typer.Argument(..., help="Instagram /p/ or /reel/ URL"),
    base_dir: Optional[Path] = typer.Option(None, "--base-dir", help="Carpeta base de automatizacion. Default: $FLUJO_EVENTOS_AUTOMATIZACION_DIR (ver MAPA.md)"),
    run_droplet: bool = typer.Option(False, "--run-droplet", help="Autorizar apertura de Droplet_Flyer.exe con historia.psd"),
    open_blender: bool = typer.Option(False, "--open-blender", help="Abrir cartelera.blend en Blender al final"),
    render_blender: bool = typer.Option(False, "--render-blender", help="Renderizar frame 1 de cartelera.blend a preview_cartelera.png"),
    blender_exe: str = typer.Option("blender", "--blender-exe", help="Comando o ruta a blender.exe"),
    yes: bool = typer.Option(False, "--yes", "-y", help="No preguntar confirmacion para droplet/blender"),
    keep_temp: bool = typer.Option(False, "--keep-temp", help="Conservar carpeta temp_flyer para debug"),
):
    """EVENTOS: descargar Instagram, crear palette_ig y opcionalmente lanzar Photoshop/Blender.

    Por defecto NO abre droplet ni Blender. Eso deja autorizacion humana antes
    de ejecutar programas externos. Para correr pasos extra, agrega flags.
    """
    from .eventos.flyer_auto import default_base_dir, run_eventos_flyer_auto

    target_base = base_dir or default_base_dir()
    if (run_droplet or open_blender or render_blender) and not yes:
        console.print(f"Base dir: {target_base}")
        if run_droplet:
            console.print("This will launch Droplet_Flyer.exe with historia.psd.")
        if render_blender:
            console.print("This will render cartelera.blend frame 1 to preview_cartelera.png.")
        if open_blender:
            console.print("This will open cartelera.blend in Blender.")
        if not typer.confirm("Authorize external app step(s) now?"):
            _warn("Cancelled by user before external app launch.")
            raise typer.Exit(1)

    res = run_eventos_flyer_auto(
        url=url,
        base_dir=target_base,
        run_droplet=run_droplet,
        open_blender=open_blender,
        render_blender=render_blender,
        blender_exe=blender_exe,
        keep_temp=keep_temp,
    )
    _section("EVENTOS flyer automation")
    if not res.ok:
        _err(res.error or "eventos flyer automation failed")
    _ok(f"Shortcode: {res.shortcode}")
    console.print(f"  base:            [cyan]{res.base_dir}[/]")
    console.print(f"  input jpg:       [cyan]{res.input_image}[/]")
    console.print(f"  palette png:     [cyan]{res.palette_image}[/]")
    console.print(f"  palette json:    [cyan]{res.palette_json}[/]")
    console.print(f"  droplet:         [cyan]{res.droplet_path}[/]")
    console.print(f"  psd:             [cyan]{res.psd_path}[/]")
    console.print(f"  blender file:    [cyan]{res.blender_file}[/]")
    console.print(f"  blender preview: [cyan]{res.blender_render}[/]")
    console.print(f"  droplet started: [bold]{'yes' if res.droplet_started else 'no'}[/]")
    console.print(f"  blender opened:  [bold]{'yes' if res.blender_started else 'no'}[/]")
    console.print(f"  blender render:  [bold]{'yes' if res.blender_rendered else 'no'}[/]")
    if not (res.droplet_started or res.blender_started or res.blender_rendered):
        console.print("\nNext examples:")
        console.print(f"  py -m flujo eventos flyer-auto \"{url}\" --run-droplet")
        console.print(f"  py -m flujo eventos flyer-auto \"{url}\" --render-blender")
        console.print(f"  py -m flujo eventos flyer-auto \"{url}\" --render-blender --open-blender")


# ============================================================
# Resolume / Chataigne
# ============================================================

@resolume_app.command("automatizar")
def resolume_automatizar(
    job: Path = typer.Argument(..., help="ruta al job EVENTOS con intake.json o brief.md"),
    fps: int = typer.Option(30, "--fps", help="frames por segundo para validar SMPTE"),
    host: str = typer.Option("127.0.0.1", "--host", help="host OSC de Resolume Arena"),
    port: int = typer.Option(7000, "--port", help="puerto OSC de Resolume Arena"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="XML de salida"),
):
    """Generar XML pre-flight Chataigne/OSC para Resolume desde un setlist SMPTE.

    Lee `intake.json` o `brief.md` dentro del job, extrae cues `HH:MM:SS:FF`
    y escribe `deliverables/show_automation.xml` con acciones OSC a Resolume.
    """
    from .resolume.automator import generate_show_automation, parse_smpte_setlist

    if not job.exists():
        _err(f"No existe: {job}")
    try:
        cues, eff_fps = parse_smpte_setlist(job, fps=fps)
        out_path = generate_show_automation(job, fps=fps, host=host, port=port, output=output)
    except Exception as e:
        _err(str(e))
    _section("Resolume / Chataigne automation")
    _ok(f"XML pre-flight generado: {out_path}")
    sidecars = [
        out_path.parent / "osc_cues.csv",
        out_path.parent / f"{out_path.stem}.experimental.noisette",
        out_path.parent / "README_CHATAIGNE.md",
    ]
    for sidecar in sidecars:
        if sidecar.exists():
            _ok(f"Sidecar: {sidecar}")
    console.print(f"  cues:       [bold]{len(cues)}[/]")
    console.print(f"  fps:        [cyan]{eff_fps}[/]")
    console.print(f"  OSC target: [cyan]{host}:{port}[/]")
    console.print("  nota:       [yellow].noisette experimental; para compatibilidad total usa template exportado desde tu Chataigne[/]")
    for cue in cues:
        console.print(f"  · {cue.smpte}  {cue.title}  -> {cue.osc_address()}")


# ============================================================
# Intake JSON
# ============================================================

@intake_app.command("json")
def intake_json(
    source: Path = typer.Argument(..., help="archivo intake JSON 1.0"),
    show_ack: bool = typer.Option(True, "--show-ack/--no-show-ack", help="mostrar acuse resultado.md al final"),
):
    """Validar intake JSON 1.0, crear job, brief y acuse de recibo.

    Contrato: `schemas/intake.schema.json`. No inventa datos: si faltan
    producto/entrega/catálogo, deja pendientes en `brief.yaml` y `resultado.md`.

    Ejemplo:
      flujo intake json schemas/ejemplos/flyer_evento.json
    """
    from .intake.json_parser import process_json_intake

    res = process_json_intake(source)
    if not res.get("ok"):
        for err in res.get("errors", []) or [res.get("error", "error desconocido")]:
            _warn(str(err))
        _err("No se pudo procesar el intake JSON.")

    _section("Intake JSON procesado")
    _ok(f"Job: {res.get('job_dir')}")
    console.print(f"  brief:     [cyan]{res.get('brief_path')}[/]")
    console.print(f"  resultado: [cyan]{res.get('resultado_path')}[/]")
    console.print(f"  estado:    [bold]{res.get('estado')}[/]")
    for w in res.get("warnings", []) or []:
        _warn(str(w))

    if show_ack and res.get("resultado_path"):
        p = Path(str(res["resultado_path"]))
        if p.exists():
            console.print("\n[bold]Acuse generado:[/]\n")
            console.print(p.read_text(encoding="utf-8", errors="ignore"))

    console.print("\nSiguiente: revisar brief.yaml; si está listo, `flujo job activate <job>`.")


# ============================================================
# Brief
# ============================================================

@brief_app.command("extract")
def brief_extract(
    job: Path = typer.Argument(..., help="ruta al job"),
):
    """Re-extraer brief desde el texto del job."""
    from .jobs.lifecycle import prepare_job
    if not job.exists():
        _err(f"No existe: {job}")
    res = prepare_job(job, run_privacy=False, run_brief_extract=True)
    _ok(f"Brief actualizado: {job / 'brief.yaml'}")


@brief_app.command("to-project")
def brief_to_project(
    brief: Path = typer.Argument(..., help="ruta al brief.yaml"),
    name: Optional[str] = typer.Option(None, "--name", "-n"),
    template: Optional[str] = typer.Option(None, "--template", "-t"),
):
    """Convertir brief.yaml en proyecto en projects/piezas_vectoriales/."""
    from .render.piezas import create_project_from_brief
    if not brief.exists():
        _err(f"No existe: {brief}")
    project = create_project_from_brief(brief, project_name=name, explicit_template=template)
    _ok(f"Proyecto: {project}")
    console.print(f"  Siguiente: [cyan]flujo render {project / 'config.json'}[/]")


@brief_app.command("paquete-cotizacion")
def brief_paquete_cotizacion(
    source: Path = typer.Argument(..., help="ruta a job/ o archivo .txt con el pedido"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="carpeta de salida (default: salida_comercial/)"),
    cliente: str = typer.Option("", "--cliente", help="cliente/productora (opcional)"),
    titulo: str = typer.Option("Brief estructura imagen/texto + cotización", "--titulo", help="título del documento"),
    moneda: str = typer.Option("CLP", "--moneda", help="moneda para cotización"),
    precio_paquete: str = typer.Option("", "--precio-paquete", help="precio del paquete completo (opcional)"),
    precio_flyer: str = typer.Option("", "--precio-flyer", help="precio flyer (opcional)"),
    precio_etiqueta: str = typer.Option("", "--precio-etiqueta", help="precio etiqueta (opcional)"),
    precio_pendon: str = typer.Option("", "--precio-pendon", help="precio pendón (opcional)"),
    precio_post_instagram: str = typer.Option("", "--precio-post-instagram", help="precio post Instagram (opcional)"),
):
    """Generar brief imagen/texto + cotización base para flyer/etiqueta/pendón/post IG.

    No inventa precios: deja "A definir" salvo que se pasen valores por opciones.
    Acepta un job (carpeta con pedido_original.txt) o un archivo .txt directo.
    """
    from .comercial.multiformato import generate_from_path

    precios = {
        "paquete": precio_paquete,
        "flyer": precio_flyer,
        "etiqueta": precio_etiqueta,
        "pendon": precio_pendon,
        "post_instagram": precio_post_instagram,
    }
    precios = {k: v for k, v in precios.items() if v}
    try:
        written = generate_from_path(
            source,
            output=output,
            titulo=titulo,
            cliente=cliente,
            moneda=moneda,
            precios=precios,
        )
    except Exception as e:
        _err(str(e))
    _section("Paquete comercial generado")
    for name, path in written.items():
        console.print(f"  · [cyan]{name}[/] → {path}")
    console.print("\nSiguiente: completa precios/datos pendientes y revisa cotizacion_base.md antes de enviar.")


@brief_app.command("show")
def brief_show(
    brief: Path = typer.Argument(..., help="ruta al brief.yaml"),
):
    """Mostrar brief en formato legible."""
    from .jobs.brief import load_brief
    if not brief.exists():
        _err(f"No existe: {brief}")
    b = load_brief(brief)
    _section(f"Brief: {brief.parent.name}")
    console.print(f"  id:           {b.id}")
    console.print(f"  estado:       [bold]{b.estado.value}[/]")
    console.print(f"  origen:       {b.origen}")
    console.print(f"  cliente:      {b.cliente or '-'}")
    console.print(f"  proyecto:     {b.proyecto or '-'}")
    console.print(f"  tipo_pieza:   {b.tipo_pieza or '-'}")
    console.print(f"  medidas:      {b.medidas.ancho_cm or '?'}x{b.medidas.alto_cm or '?'} cm ({b.medidas.orientacion or '?'})")
    console.print(f"  productos:    {', '.join(b.productos) or '-'}")
    console.print(f"  entrega:      editable={b.entrega.editable_svg} vectorizado={b.entrega.vectorizado_svg} pdf={b.entrega.pdf_impresion} zip={b.entrega.zip}")
    console.print(f"  texto_aprobado: {b.contenido.texto_aprobado}")
    console.print(f"  pendientes:   {len(b.pendientes)}")
    for p in b.pendientes:
        console.print(f"    · {p}")


# ============================================================
# Render
# ============================================================

@render_app.command("run")
def render_run(
    config: Path = typer.Argument(..., help="ruta al config.json"),
    for_app: str = typer.Option(
        None, "--for", "-f",
        help="Objetivo: illustrator | photoshop | blender (prepara export según tu flujo)"
    ),
):
    """Renderizar un proyecto piezas_vectoriales.

    Con --for illustrator/photoshop/blender prepara los archivos y scripts
    optimizados para abrir directamente en esa aplicación.
    """
    from .render.piezas import render_config
    if not config.exists():
        _err(f"No existe: {config}")

    rc = render_config(config)
    if rc != 0:
        raise typer.Exit(rc)

    if for_app:
        msg = f"Render listo. Archivos preparados para {for_app.upper()} (usa flujo)."
        if for_app.lower() in ("illustrator", "ai"):
            msg += " Abre el SVG editable en AI."
        elif for_app.lower() in ("photoshop", "ps"):
            msg += " Exporta ZIP y corre el JSX en PS."
        elif for_app.lower() == "blender":
            msg += " Ejecuta blender_setup.py en Blender."
        _ok(msg)
    else:
        _ok(f"Render OK: {config.parent}")


@render_app.command("illustrator")
def render_illustrator(
    input_path: Path = typer.Argument(..., help="archivo o carpeta SVG para preparar"),
    output_dir: Optional[Path] = typer.Option(None, "--output", "-o", help="carpeta base donde se creará el paquete"),
    project_name: str = typer.Option("flujo_svg", "--project-name", help="nombre base del paquete"),
):
    """Preparar un paquete listo para abrir en Illustrator desde uno o varios SVG."""
    from .export.illustrator import prepare_svg_for_illustrator

    package_dir = prepare_svg_for_illustrator(input_path, output_dir=output_dir, project_name=project_name)
    _ok(f"Paquete Illustrator preparado: {package_dir}")


@render_app.command("bridge")
def render_bridge(
    spec: Path = typer.Argument(..., help="archivo JSON con spec de documento, imagen y texto"),
    output: Path = typer.Option(Path("flows/illustrator_bridge.jsx"), "--output", "-o", help="ruta del script JSX a generar"),
):
    """Generar un script JSX para Illustrator a partir de un JSON de entrada."""
    import json

    from .export.illustrator_bridge import write_illustrator_bridge

    if not spec.exists():
        _err(f"No existe: {spec}")
    payload = json.loads(spec.read_text(encoding="utf-8"))
    out_path = write_illustrator_bridge(payload, output, base_dir=spec.parent)
    _ok(f"Bridge Illustrator generado: {out_path}")


@render_app.command("validate")
def render_validate(
    config: Path = typer.Argument(..., help="ruta al config.json"),
):
    """Validar un config.json sin renderizar."""
    from .render.piezas import validate_config
    if not config.exists():
        _err(f"No existe: {config}")
    errors = validate_config(config)
    if errors:
        _section(f"Errores en {config}")
        for e in errors:
            _warn(e)
        raise typer.Exit(1)
    _ok(f"Config OK: {config}")


@render_app.command("formats")
def render_formats(
    width: Optional[float] = typer.Option(None, "--width", "-w", help="ancho en cm"),
    height: Optional[float] = typer.Option(None, "--height", "-h", help="alto en cm"),
    tipo: Optional[str] = typer.Option(None, "--tipo", "-t", help="tipo (etiqueta, flyer, rider...)"),
    area: Optional[str] = typer.Option(None, "--area", "-a", help="filtrar por área (eventos, suplementos)"),
    medio: Optional[str] = typer.Option(None, "--medio", "-m", help="filtrar por medio (impresion, digital)"),
    herramienta: Optional[str] = typer.Option(None, "--herramienta", help="filtrar por herramienta (illustrator, photoshop, blender)"),
):
    """Listar, filtrar o sugerir formatos/plantillas.

    Ejemplos:
      flujo render formats                      # todos
      flujo render formats -a suplementos       # solo área suplementos
      flujo render formats -m impresion         # solo impresión (Illustrator)
      flujo render formats -w 16.5 -h 6.5 -t etiqueta   # sugerir por medida
    """
    from .render.formats import list_formats, suggest_format
    if width and height:
        sugs = suggest_format(width, height, tipo or "")
        _section(f"Sugerencias para {width:g}x{height:g}cm {tipo or ''}")
        for s in sugs:
            console.print(f"  · {s}")
    else:
        formats = list_formats(area or "", medio or "", herramienta or "")
        if not formats:
            _warn("No hay formatos que coincidan (o falta INDEX_FORMATOS.json)")
            return
        filtros = " ".join(x for x in [
            f"área={area}" if area else "",
            f"medio={medio}" if medio else "",
            f"herramienta={herramienta}" if herramienta else "",
        ] if x)
        title = f"Formatos disponibles ({len(formats)})" + (f" — {filtros}" if filtros else "")
        _section(title)
        for f in formats:
            console.print(f"  · {f}")


@render_app.command("rescale")
def render_rescale(
    config: Path = typer.Argument(..., help="ruta al config.json"),
    dpi: Optional[float] = typer.Option(None, "--dpi", help="resolución objetivo (ej. 300)"),
    width: Optional[float] = typer.Option(None, "--width", "-w", help="nuevo ancho en cm (cambio de proporción)"),
    height: Optional[float] = typer.Option(None, "--height", "-h", help="nuevo alto en cm (cambio de proporción)"),
    scale_elements: Optional[bool] = typer.Option(
        None, "--scale-elements/--no-scale-elements",
        help="reposicionar elementos al nuevo tamaño (por defecto: sí en --dpi, no en proporción)",
    ),
    out: Optional[Path] = typer.Option(None, "--out", help="archivo de salida (por defecto sobrescribe)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="solo mostrar el cálculo, no escribir"),
):
    """Reescalar proporción (medida cm) o resolución (DPI) de un config.json.

    Ejemplos:
      flujo render rescale c.json --dpi 300            # subir resolución (anti-pixelado)
      flujo render rescale c.json -w 14 -h 10          # cambiar proporción a 14x10 cm
    """
    from .render.rescale import load_config, set_dpi, set_real_size, save_config, current_dpi

    if not config.exists():
        _err(f"No existe: {config}")
    if dpi is None and (width is None or height is None):
        _err("Indica --dpi, o bien --width y --height (cm).")

    try:
        cfg = load_config(config)
    except Exception as e:
        _err(f"No se pudo leer el config: {e}")

    try:
        if width is not None and height is not None:
            se = bool(scale_elements) if scale_elements is not None else False
            new_cfg, info = set_real_size(cfg, width, height, dpi=dpi, scale_elements=se)
        else:
            se = bool(scale_elements) if scale_elements is not None else True
            new_cfg, info = set_dpi(cfg, dpi, scale_elements=se)
    except ValueError as e:
        _err(str(e))

    _section(f"Rescale ({info['modo']}) — {config.name}")
    ca, cd = info["canvas_antes"], info["canvas_despues"]
    console.print(f"  canvas: [yellow]{ca[0]}x{ca[1]}px[/] → [green]{cd[0]}x{cd[1]}px[/]")
    if info["modo"] == "dpi":
        da = info["dpi_antes"]
        console.print(f"  dpi:    [yellow]{da:.0f}[/] → [green]{info['dpi_despues']:.0f}[/]" if da else f"  dpi:    → [green]{info['dpi_despues']:.0f}[/]")
    else:
        ra, rd = info["real_antes"], info["real_despues"]
        console.print(f"  medida: [yellow]{ra[0]}x{ra[1]}cm[/] → [green]{rd[0]}x{rd[1]}cm[/] @ {info['dpi_usado']:.0f}dpi")
    console.print(f"  elementos reescalados: {'sí' if info['elementos_reescalados'] else 'no'}")
    if info.get("aviso"):
        _warn(info["aviso"])

    if dry_run:
        _ok("Dry-run: no se escribió nada.")
        return

    target = out or config
    save_config(new_cfg, target)
    _ok(f"Guardado: {target}")


# Alias: `flujo render` sin subcomando → render_run
@render_app.callback(invoke_without_command=True)
def render_default(ctx: typer.Context):
    if ctx.invoked_subcommand is not None:
        return
    _warn("Uso: flujo render run <config.json> | validate | formats")


# ============================================================
# Suplementos RD (Comercial)
# ============================================================

@suplementos_app.command("list")
def suplementos_list():
    """Listar suplementos disponibles."""
    from .comercial.suplementos_config import list_suplementos

    items = list_suplementos()
    _section(f"Suplementos RD ({len(items)})")
    for nombre in items:
        console.print(f"  · {nombre}")
    console.print(f"\nUsage: [cyan]py -m flujo suplementos contraportada \"<nombre>\" --output <salida.svg>[/]")


@suplementos_app.command("contraportada")
def suplementos_contraportada(
    nombre: Optional[str] = typer.Argument(
        None, help="Suplemento puntual (ej. 'IMPULSO'). Sin argumento, regenera los 8."
    ),
):
    """Regenerar las contraportadas desde la plantilla aprobada.

    El estilo sale de `svg/suplementos_rd/_plantilla/contraportada_cambios.svg`,
    que es la exportacion del .ai del usuario y NO se toca. El texto sale del
    archivo de contenido aprobado. El generador solo superpone el texto dentro
    de las cajas medidas de la plantilla, asi que cambiar el texto nunca rompe
    el diseno.

    No hay opcion para escribir texto a mano: en suplementos el texto viene del
    archivo que manda el encargado de RD, y ese archivo manda (orden del usuario,
    2026-07-26). El `--brief` que este comando tenia antes era un concepto de
    EVENTOS colado aca; vive donde corresponde, en plano/rider.

    Ejemplo:
      py -m flujo suplementos contraportada
      py -m flujo suplementos contraportada "IMPULSO"
    """
    import subprocess
    import sys as _sys

    from .comercial.suplementos_config import get_suplemento, list_suplementos
    from .paths import repo_root

    raiz = repo_root()
    if nombre:
        try:
            supl = get_suplemento(nombre)
        except KeyError as e:
            _err(str(e))
            console.print(f"  Reales: {', '.join(list_suplementos())}")
            return
    else:
        supl = None

    generador = raiz / ".claude" / "skills" / "entregas-rd" / "generadores" / "gen_contraportadas.py"
    if not generador.is_file():
        _err(f"No existe el generador aprobado: {generador}")
        return

    r = subprocess.run(
        [_sys.executable, str(generador)],
        cwd=str(raiz), capture_output=True, encoding="utf-8", errors="replace",
    )
    if r.returncode != 0:
        _err("El generador fallo:")
        console.print((r.stderr or r.stdout or "").strip()[:1200])
        return

    salidas = sorted((raiz / "svg" / "suplementos_rd" / "09_contraportadas_dark").glob("*.svg"))
    if supl is not None:
        salidas = [p for p in salidas if p.stem == supl.id] or salidas
        _ok(f"Contraportada regenerada: {supl.nombre}")
    else:
        _ok(f"Contraportadas regeneradas: {len(salidas)}")
    for p in salidas:
        console.print(f"  · {p.relative_to(raiz)}")
    console.print("  Tamaño: 10×14 cm (2000x2800 px @ 300dpi)")


@suplementos_app.command("validate")
def suplementos_validate(
    paths: list[Path] = typer.Argument(..., help="SVG(s) de suplementos o contraportadas a validar"),
    contraportada: bool = typer.Option(True, "--contraportada/--generic", help="esperar tamano de contraportada 10x14 cm (2000x2800 px)"),
):
    """Validar SVGs de suplementos antes de revisar/exportar en Illustrator."""
    from .comercial.svg_validator import (
        EXPECTED_CONTRAPORTADA_SIZE,
        render_svg_validation_report,
        validate_svg_files,
    )

    expected = EXPECTED_CONTRAPORTADA_SIZE if contraportada else None
    report = validate_svg_files(paths, expected_size=expected)
    console.print(render_svg_validation_report(report))
    if not report["ok"]:
        raise typer.Exit(1)


@suplementos_app.command("illustrator")
def suplementos_illustrator(
    nombres: Optional[list[str]] = typer.Argument(None, help="Nombres de suplementos a incluir (ej. 'Impulso' 'Creatina')"),
    output_dir: Optional[Path] = typer.Option(None, "--output", "-o", help="Directorio base del paquete Illustrator"),
    project_name: str = typer.Option("suplementos_rd", "--project-name", help="Nombre del paquete Illustrator"),
):
    """Preparar un paquete Illustrator con varias contraportadas de suplementos."""
    from .export.illustrator import prepare_supplement_contraportadas_for_illustrator

    selected = nombres or ["Impulso", "Creatina"]
    package_dir = prepare_supplement_contraportadas_for_illustrator(
        selected,
        output_dir=output_dir,
        project_name=project_name,
    )
    _ok(f"Paquete Illustrator de suplementos preparado: {package_dir}")


# El comando `portal` se retiro el 2026-07-26. No estaba viejo: estaba ROTO --
# reventaba con AttributeError al ejecutarlo. Exportaba un HTML estatico con
# links a GitHub Issues, planteado como alternativa a monday.com, y hoy choca
# con dos cosas: el panel de Trabajos ya muestra ese estado, y los issues son un
# canal de entrada, no un tablero de tareas. Archivado en
# retirado el 2026-07-30 con su motivo; vive en el historial de git.


@app.command()
def daily(
    output_md: Optional[Path] = typer.Option(None, "--md", help="ruta al markdown"),
    output_html: Optional[Path] = typer.Option(None, "--html", help="ruta al html"),
):
    """Generar reporte diario (md + html)."""
    from .paths import context_dir
    from .dashboard import collect_items, render_markdown, render_html

    items = collect_items()
    md = render_markdown(items)
    html = render_html(items)

    md_path = output_md or (context_dir() / "DAILY.md")
    html_path = output_html or (context_dir() / "dashboard.html")
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(md, encoding="utf-8")
    html_path.write_text(html, encoding="utf-8")

    _section(f"Daily report: {len(items)} items")
    console.print(f"  md:   {md_path}")
    console.print(f"  html: {html_path}")
    # mostrar resumen
    alta = sum(1 for i in items if i.priority.value == "alta")
    media = sum(1 for i in items if i.priority.value == "media")
    baja = sum(1 for i in items if i.priority.value == "baja")
    console.print(f"  alta: {alta}  media: {media}  baja: {baja}")


# ============================================================
# Laser / plotter (estetica vectorial via vpype)
# ============================================================

@laser_app.command("estado")
def laser_estado():
    """Que parte de la cadena vpype esta instalada, medido ejecutandola."""
    from .laser import verificar
    estado = verificar()
    for pieza, ok in estado.items():
        console.print(f"  {'OK ' if ok else '-- '}{pieza}")
    if not estado["vpype"]:
        # \[all] escapado: rich se come [all] como si fuera markup
        console.print('Instalar: pip install "vpype\\[all]" hatched y el '
                      'plugin flow desde git (ver flujo laser --help)')
        raise typer.Exit(1)


def _laser_reporte(destino, medida):
    """Presupuesto de puntos: 600-1000 por frame a 30 kpps
    (docs/laser/TOOLKIT_INDICE.md). Decirlo siempre, nunca recortar solo."""
    aviso = "" if medida["dentro"] else         "  [AVISO: sobre el presupuesto, simplificar mas o partir la pieza]"
    tol = (" (linesimplify %smm)" % medida["tolerancia_mm"]
           if medida["tolerancia_mm"] else "")
    extra = ""
    if medida.get("trazos") is not None:
        extra = (f", {medida['trazos']} trazos, "
                 f"viaje apagado {medida['viaje_apagado']} ud")
    console.print(f"OK -> {destino}  {medida['puntos']} puntos{tol}{extra}{aviso}")
    antes = medida.get("viaje_apagado_antes")
    despues = medida.get("viaje_apagado_despues")
    if antes is not None and despues is not None:
        baja = (100 * (antes - despues) / antes) if antes else 0.0
        console.print(f"viaje apagado antes del orden: {antes} ud -> "
                      f"despues: {despues} ud ({baja:.0f}% menos)")


@laser_app.command("hatched")
def laser_hatched(
    imagen: Path = typer.Argument(..., help="imagen de entrada (jpg/png/webp)"),
    salida: Optional[Path] = typer.Option(None, "--output", "-o", help="SVG de salida"),
    pitch: int = typer.Option(4, "--pitch", help="separacion del rayado en px"),
    medir_viaje: bool = typer.Option(False, "--medir-viaje", help="mide el viaje apagado antes/despues de ordenar (una pasada extra de vpype)"),
):
    """Zonas oscuras a rayado: un logo solido deja de llegar hueco al laser."""
    from .laser import hatched
    if not imagen.exists():
        _err(f"No existe: {imagen}")
        raise typer.Exit(1)
    destino = salida or imagen.with_suffix(".hatched.svg")
    try:
        medida = hatched(imagen, destino, pitch=pitch, medir_viaje=medir_viaje)
    except RuntimeError as e:
        _err(str(e))
        raise typer.Exit(1)
    _laser_reporte(destino, medida)


@laser_app.command("flow")
def laser_flow(
    imagen: Path = typer.Argument(..., help="imagen de entrada (jpg/png/webp)"),
    salida: Optional[Path] = typer.Option(None, "--output", "-o", help="SVG de salida"),
    semilla: int = typer.Option(7, "--semilla", help="misma semilla = mismo dibujo"),
    medir_viaje: bool = typer.Option(False, "--medir-viaje", help="mide el viaje apagado antes/despues de ordenar (una pasada extra de vpype)"),
):
    """La imagen se vuelve trazos largos de campo de flujo, casi sin saltos."""
    from .laser import flow
    if not imagen.exists():
        _err(f"No existe: {imagen}")
        raise typer.Exit(1)
    destino = salida or imagen.with_suffix(".flow.svg")
    try:
        medida = flow(imagen, destino, semilla=semilla, medir_viaje=medir_viaje)
    except RuntimeError as e:
        _err(str(e))
        raise typer.Exit(1)
    _laser_reporte(destino, medida)


@laser_app.command("lote")
def laser_lote(
    carpeta: Path = typer.Argument(..., help="carpeta con el material (imagenes)"),
    modo: str = typer.Option("flow", "--modo", help="flow | hatched"),
    limite: Optional[int] = typer.Option(None, "--limite", help="procesar solo N"),
    ild: bool = typer.Option(False, "--ild", help="escribe ademas un .ild (ILDA Type 5, importable en QuickShow) junto a cada SVG"),
):
    """Deriva una pieza laser por imagen y escribe el manifiesto del archivo.

    Las salidas van a iskvw/piel/laser/ y el manifiesto a
    iskvw/datos/laser.json: con eso las piezas entran al archivo del
    portafolio vinculadas a su obra curada (la clave es el media id del
    nombre de archivo). En MAK corre igual: mismo repo, misma orden.
    """
    from .laser import lote
    if modo not in ("flow", "hatched"):
        _err("modo tiene que ser flow o hatched")
        raise typer.Exit(1)
    if not carpeta.is_dir():
        _err(f"No es carpeta: {carpeta}")
        raise typer.Exit(1)
    raiz = Path(__file__).resolve().parents[2]
    try:
        filas = lote(carpeta, raiz / "iskvw" / "piel" / "laser",
                     raiz / "iskvw" / "datos" / "laser.json",
                     modo=modo, limite=limite, ild=ild)
    except RuntimeError as e:
        _err(str(e))
        raise typer.Exit(1)
    buenas = [f for f in filas if "src" in f]
    con_error = len(filas) - len(buenas)
    console.print(f"{len(buenas)} piezas {modo} -> iskvw/piel/laser/ "
                  f"({con_error} con error)")
    if ild:
        con_ild = sum(1 for f in buenas if "ild" in f)
        console.print(f"{con_ild} archivos .ild (ILDA Type 5) junto a los SVG")
    console.print("manifiesto -> iskvw/datos/laser.json")


@laser_app.command("medir")
def laser_medir(
    svg: Path = typer.Argument(..., help="SVG de trazos (salida de vpype o similar)"),
    presupuesto: int = typer.Option(800, "--presupuesto", help="puntos por frame (600-1000 a 30 kpps)"),
):
    """Los numeros reales del frame: puntos, trazos, dibujo y viaje apagado.

    Es la respuesta medida a 'esto se ve bien en laser?': cada salto en
    negro gasta puntos sin dibujar y la regla de diseno del toolkit pide
    menos de 8 subtrazos. No necesita vpype instalado.
    """
    from .laser import medir
    if not svg.exists():
        _err(f"No existe: {svg}")
        raise typer.Exit(1)
    try:
        m = medir(svg)
    except RuntimeError as e:
        _err(str(e))
        raise typer.Exit(1)
    dentro = m["puntos"] <= presupuesto
    console.print(f"{svg}")
    console.print(f"  puntos: {m['puntos']}  (presupuesto {presupuesto}: "
                  f"{'dentro' if dentro else 'SOBRE'})")
    console.print(f"  trazos: {m['trazos']}"
                  + ("  [AVISO: el toolkit pide <8 subtrazos]"
                     if m["trazos"] >= 8 else ""))
    console.print(f"  dibujo: {m['dibujo']} ud   "
                  f"viaje apagado: {m['viaje_apagado']} ud")
    if not dentro:
        raise typer.Exit(1)


@laser_app.command("ild")
def laser_ild(
    svg: Path = typer.Argument(..., help="SVG de trazos a convertir"),
    salida: Optional[Path] = typer.Option(None, "--output", "-o", help=".ild de salida"),
    color: str = typer.Option("255,255,255", "--color", help="R,G,B del trazo (blanco = los 3 canales)"),
    reposo: int = typer.Option(4, "--reposo", help="puntos apagados de reposo al inicio y fin de cada trazo"),
):
    """SVG a ILDA Type 5 (RGB): el formato que QuickShow SI importa.

    Cierra la ruta B del toolkit sin Modulaser ni msvg2ild: exporta 2D true
    color (nunca tabla de paleta) y verifica el archivo releyendolo antes de
    reportar. Revisar igual en ilda-viewer antes del venue.
    """
    from .laser import escribir_ild, leer_ild
    if not svg.exists():
        _err(f"No existe: {svg}")
        raise typer.Exit(1)
    try:
        rgb = tuple(int(c) for c in color.split(","))
        if len(rgb) != 3 or any(not 0 <= c <= 255 for c in rgb):
            raise ValueError
    except ValueError:
        _err("--color tiene que ser R,G,B con valores 0-255")
        raise typer.Exit(1)
    destino = salida or svg.with_suffix(".ild")
    try:
        r = escribir_ild(svg, destino, color=rgb, reposo=reposo)
        frames = leer_ild(destino)
    except RuntimeError as e:
        _err(str(e))
        raise typer.Exit(1)
    if len(frames) != 1 or len(frames[0]["puntos"]) != r["puntos_ild"]:
        _err(f"verificacion fallo: el .ild releido no coincide ({destino})")
        raise typer.Exit(1)
    aviso = ("" if r["puntos_ild"] <= 1000 else
             "  [AVISO: sobre 1000 puntos con reposo incluido, simplificar]")
    console.print(f"OK -> {destino}  {r['puntos_ild']} puntos ILDA "
                  f"({r['en_blanco']} apagados, {r['trazos']} trazos), "
                  f"verificado releyendo{aviso}")


# ============================================================
# Plano (stands de eventos)
# ============================================================

@app.command()
def plano(
    evento: Path = typer.Argument(..., help="ruta al JSON del evento"),
    rider: bool = typer.Option(False, "--rider", help="imprimir rider de texto"),
    costs: bool = typer.Option(False, "--costs", help="imprimir desglose de costos"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="archivo SVG de salida (solo sin --rider)"),
    px_por_metro: float = typer.Option(90.0, "--scale", help="escala px por metro"),
    validate: bool = typer.Option(False, "--validate", help="validar evento antes de renderizar"),
):
    """Generar plano SVG, rider o costos de stands desde un JSON de evento.

    Ejemplo:
      flujo plano projects/plano/ejemplos/evento_ejemplo.json
      flujo plano projects/plano/ejemplos/evento_ejemplo.json --rider
      flujo plano projects/plano/ejemplos/evento_ejemplo.json --costs
      flujo plano <evento.json> -o plano.svg
    """
    from .plano import load_evento, render_svg, render_rider, resumen_costos, render_validation_report, validate_evento
    if not evento.exists():
        _err(f"No existe: {evento}")
    try:
        ev = load_evento(evento)
    except Exception as e:
        _err(f"No se pudo leer el evento: {e}")

    if validate:
        report = validate_evento(ev)
        console.print(render_validation_report(ev))
        if not report["ok"]:
            raise typer.Exit(1)
        if not (costs or rider or output):
            return

    if costs:
        console.print(resumen_costos(ev))
    elif rider:
        console.print(render_rider(ev))
    else:
        svg = render_svg(ev, px_por_metro=px_por_metro)
        if output:
            output.write_text(svg, encoding="utf-8")
            _ok(f"SVG guardado: {output}")
        else:
            console.print(svg)


@app.command("cotizaciones")
def cotizaciones(
    evento: Path = typer.Argument(..., help="evento.json (reusa el de plano)"),
    para: str = typer.Option("productora", "--para", help="productora | interno | empresa"),
    output: Optional[Path] = typer.Option(None, "--output", "-o"),
):
    """Genera cotización dual integrada con flujo.

    --para productora: versión externa (la que recibe el recinto o la productora)
    --para interno/empresa: desglose detallado interno.

    Los colores salen de la paleta por defecto y el evento puede sobrescribirlos
    con un bloque `estilo`; no hay estética obligatoria.
    """
    # Robust import for cotizaciones (satellite, not in main pkg layout).
    # Works after `pip install -e .` (flujo in path) + from repo root or packaged context.
    # Note: projects/cotizaciones not bundled in `flujo package` (only projects/flujo brand).
    try:
        from projects.cotizaciones.engine import generar_cotizacion
    except ImportError:
        import sys
        from pathlib import Path
        try:
            from .paths import repo_root
            r = repo_root()
            if str(r) not in sys.path:
                sys.path.insert(0, str(r))
            from projects.cotizaciones.engine import generar_cotizacion
        except Exception:
            def generar_cotizacion(*a, **k):
                raise RuntimeError("cotizaciones engine unavailable (run from repo root after pip install -e .; not bundled in package)")
    if not evento.exists():
        _err(f"No existe: {evento}")
    res = generar_cotizacion(evento, audiencia=para, output_dir=output)
    console.print(f"Cotización generada: {res['files']}")


# ============================================================
# App web (Gradio)
# ============================================================

@app.command()
def serve(
    port: int = typer.Option(None, "--port", "-p", help="puerto del servidor; sin este flag se busca uno libre desde el puerto contractual"),
    host: str = typer.Option("127.0.0.1", "--host", help="host (0.0.0.0 para red local)"),
    desktop: bool = typer.Option(False, "--desktop", help="abrir en ventana nativa con pywebview (si está instalado)"),
    procesar_pendientes: bool = typer.Option(False, "--procesar-pendientes", help="al arrancar, avanzar los jobs de flyer pendientes (modifica jobs: por eso no es el default)"),
    abrir: bool = typer.Option(True, "--abrir/--no-abrir", help="abrir el navegador al arrancar (--no-abrir deja solo el servidor)"),
):
    """Iniciar el workspace local: el hub, que es la entrada diaria.

    Sirve `context/flujo_hub.html` + los visualizadores SVG/Plano con la API
    real en http://{host}:{port}: intake, jobs, base de datos RD, tarifa,
    simbolos del plano y el puente de pywebview.

    --desktop: ventana nativa (pywebview), sin barra de navegador.
    --no-abrir: levanta el servidor sin abrir el navegador, util para revisar o
    automatizar sin acumular pestanas.

    Habia un `--legacy` que lanzaba un editor Gradio. Se retiro el 2026-07-26:
    importaba `flujo.web.editor`, un modulo que NO existe, y caia a
    `scripts/app.py`, una tercera interfaz sin tocar desde el commit inicial.
    Encima gradio no esta declarado en pyproject, asi que en una instalacion
    limpia ese camino ni arrancaba. Archivado en
    el historial de git (retirado del arbol el 2026-07-30).
    """
    from .web.hub import launch, CONTRACT_PORT
    from .paths import repo_root
    # Omitting --port asks for auto-detection from the contract port; passing
    # it asks for that exact port and must never be moved silently.
    auto_port = port is None
    port = CONTRACT_PORT if auto_port else port
    r = repo_root()
    console.print(f"[cyan]flujo workspace (hub) en http://{host}:{port}[/]")
    console.print(f"[dim]Repo context: {r}[/dim]")
    # --no-abrir existe porque levantar el hub para revisarlo o para un chequeo
    # abria una pestana cada vez; ocho arranques seguidos dejan ocho pestanas.
    launch(host=host, port=port, desktop=desktop, root=r,
           procesar_pendientes=procesar_pendientes, open_browser=abrir,
           auto_port=auto_port)


# Alias: flujo app → flujo serve
@app.command("app")
def app_alias(
    port: int = typer.Option(None, "--port", "-p"),
    host: str = typer.Option("127.0.0.1", "--host"),
    desktop: bool = typer.Option(False, "--desktop"),
    procesar_pendientes: bool = typer.Option(False, "--procesar-pendientes", help="al arrancar, avanzar los jobs de flyer pendientes"),
    abrir: bool = typer.Option(True, "--abrir/--no-abrir", help="abrir el navegador al arrancar (--no-abrir deja solo el servidor)"),
):
    """Alias de serve. Lanza la nueva app (hub pro workspace recomendado como entrada diaria). Real backend + parse/create jobs live cuando activo."""
    serve(port=port, host=host, desktop=desktop,
          procesar_pendientes=procesar_pendientes, abrir=abrir)


# ============================================================
# Packaging (free, PyInstaller focused, Windows .exe for daily designer use)
# ============================================================

@app.command("package")
def package(
    onefile: bool = typer.Option(True, "--onefile/--onedir", help="single .exe (recomendado) o carpeta"),
    show_console: bool = typer.Option(False, "--console/--noconsole", help="mostrar consola (debug) o ventana limpia"),
    output: str = typer.Option("dist", "--output", "-o", help="carpeta de salida"),
):
    """Empaqueta el hub pro como aplicación de escritorio real .exe (Windows).

    Usa PyInstaller (gratis, en extra 'build').
    Genera flujo-hub.exe (onefile recomendado) o carpeta:
    - --noconsole por defecto (sin terminal visible)
    - Icono profesional embebido (generado con Pillow gratis en build: rounded accent + F geométrico limpio)
    - Assets incluidos: context/ (hub + visualizers), svg/ (visualizador carga SVGs), projects/flujo (brand),
      jobs/_template, src/flujo/templates (internos)
    - Launcher dedicado (entry point): abre SIEMPRE pywebview nativo premium + tray opcional + bridge directo
      (equivalente a `flujo app --desktop` pero sin consola ni python feel)
    - En runtime: jobs/data/inbox/piezas etc se crean en 'flujo_workspace/' sibling al exe (persistente, sobrevive onefile)
    - Soporte onefile (simple dist) / onedir (más rápido)
    - Frozen paths: asset_root para reads (HTML/brand/svg), workspace para writes.
    - Servidor hub soporta servir assets bundled (/svg/* /projects/* etc) para que visualizers funcionen completos.

    Instalación previa (gratis):
      py -m pip install -e .[web,desktop-extras,build]

    Uso:
      flujo package
      flujo package --onedir
      flujo package -o mi-dist

    Resultado se siente como app real (no script python). Doble clic → ventana pro "flujo • Workspace".
    Para menú/instalador completo: Inno Setup (gratis, ver output hints).
    """
    try:
        import PyInstaller.__main__ as pyi
    except ImportError:
        _err("PyInstaller no encontrado. Instala gratis: py -m pip install pyinstaller")
        return

    from .paths import repo_root, asset_root
    root = repo_root()
    # Use a generated launcher (temp, no repo pollution) so the .exe ALWAYS starts the premium desktop hub
    # (pywebview window, no console, tray if avail, direct bridge). Double-click the exe feels like real app.
    import tempfile
    import os as _os

    launcher_code = '''import os
import sys
from pathlib import Path

# Signal packaged mode for paths.py (assets vs workspace separation)
# This makes the standalone .exe write user data (jobs, data) to flujo_workspace/ next to exe.
os.environ.setdefault("FLUJO_PACKAGED", "1")

# When executed inside PyInstaller bundle, sys.frozen + _MEIPASS will be set automatically by bootloader.
# Launcher forces desktop launch (native window + pro UX). No browser, no terminal.
# All imports use the bundled package (PyInstaller collects via --collect-submodules + --paths src).

from flujo.web.hub import launch
from flujo.paths import asset_root, workspace_root

# Silent prints in --noconsole mode; useful if console build for debug.
print("[flujo packaged desktop] assets:", asset_root())
print("[flujo packaged desktop] workspace next to exe:", workspace_root())

# Force desktop=True, no auto browser (pywebview owns the window) -> direct `flujo app --desktop` equivalent.
launch(
    host="127.0.0.1",
    port=8765,
    desktop=True,
    open_browser=False,
    root=asset_root()
)
'''

    # write temp launcher (deleted after build)
    fd, launcher_path = tempfile.mkstemp(suffix="_flujo_desktop_launcher.py", text=True)
    with _os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(launcher_code)

    spec_name = "flujo-hub"
    dist_dir = Path(output)
    dist_dir.mkdir(parents=True, exist_ok=True)

    # Generate real .ico at build time (free, using Pillow if available) for the exe icon + pro feel.
    icon_arg = ""
    try:
        from PIL import Image, ImageDraw
        ico_path = dist_dir / "flujo-build-icon.ico"
        # Professional dark + flujo accent rounded + clean geometric F (256 base)
        accent = (45, 90, 74, 255)
        img = Image.new("RGBA", (256, 256), (10, 10, 10, 255))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([24, 24, 232, 232], radius=28, fill=accent)
        dark = (10, 10, 10, 255)
        draw.rectangle([66, 58, 90, 198], fill=dark)   # F stem
        draw.rectangle([90, 58, 188, 82], fill=dark)   # top bar
        draw.rectangle([90, 112, 170, 136], fill=dark) # mid bar
        sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        img.save(str(ico_path), format="ICO", sizes=sizes)
        icon_arg = f"--icon={ico_path}"
        console.print(f"[cyan]Icono generado: {ico_path}[/]")
    except Exception as _e:
        console.print(f"[yellow]Sin icono embebido (instala pillow para .ico en build): {_e}[/]")

    # Collect data: only what hub needs for pro desktop (brand + visuals). Other projects stay out for size.
    # Use os.pathsep ( ; on Windows, : on POSIX) for --add-data at build time. Targets Windows .exe but portable build.
    # workspace is created at runtime next to exe.
    # Bundle internal templates (for export blender etc) + jobs/_template (for create_job) under bundle so reads work in frozen.
    # svg + projects/flujo + context are essential for visualizers + brand + hub HTMLs to work via server in packaged exe.
    import os as _os_path
    _sep = _os_path.pathsep
    add_datas = [
        f"--add-data={root / 'context'}{_sep}context",
        f"--add-data={root / 'projects' / 'flujo'}{_sep}projects/flujo",
        f"--add-data={root / 'svg'}{_sep}svg",
        f"--add-data={root / 'jobs' / '_template'}{_sep}jobs/_template",
        f"--add-data={root / 'src' / 'flujo' / 'templates'}{_sep}flujo/templates",
    ]

    args = [
        "--clean",
        "--noconfirm",
        f"--{ 'onefile' if onefile else 'onedir' }",
        f"--{ 'console' if show_console else 'windowed' }",
        f"--name={spec_name}",
        f"--distpath={output}",
        "--paths", str(root / "src"),  # help PyInstaller find the src layout
    ] + add_datas + [
        "--hidden-import=webview",
        "--hidden-import=PIL",
        "--hidden-import=pystray",
        "--hidden-import=yaml",
        "--hidden-import=pydantic",
        "--hidden-import=typer",
        "--hidden-import=rich",
        "--collect-submodules=flujo",
        launcher_path,  # the entry that forces desktop app feel
    ]
    if icon_arg:
        args.append(icon_arg)

    console.print(f"[cyan]Construyendo .exe profesional con PyInstaller (100% gratis)...[/]")
    console.print(f"[dim]Opciones: onefile={onefile} noconsole={not show_console} output={output}[/]")
    console.print(f"[dim]Comando equiv (aprox): pyinstaller {' '.join(args)}[/]")

    try:
        pyi.run(args)  # programmatic = no extra shell
        exe_name = spec_name + (".exe" if onefile else "")
        exe_path = dist_dir / exe_name
        if not onefile:
            # onedir the binary is inside the folder
            exe_path = dist_dir / spec_name / (spec_name + ".exe")
        console.print(f"[green]✓[/] Empaquetado OK: {exe_path}")
        console.print("")
        console.print("[bold]Cómo usar la app de escritorio real (Windows):[/]")
        console.print(f"  1. Prepara: py -m pip install -e .[web,desktop-extras,build]")
        console.print(f"  2. Ejecuta: flujo package   (o con --onedir si prefieres carpeta)")
        console.print(f"  3. Ve a {output}/  y lanza {spec_name}.exe (doble clic)")
        console.print("     - Abre ventana nativa premium (pywebview) -- equivalente directo a flujo app --desktop")
        console.print("     - Icono profesional + título 'flujo • Workspace' (sin feel de Python)")
        console.print("     - Sin terminal visible (--noconsole / windowed)")
        console.print("     - Tray icon (si pystray+pillow instalados en build)")
        console.print("     - Todo el hub + intake real + delegación + visualizers SVG/plano + bridge (SVGs cargan)")
        console.print("     - Crea jobs/ + data/ en 'flujo_workspace' (sibling al exe) -- persistente")
        console.print("")
        console.print("[bold]Para que se sienta aún más profesional (gratis):[/]")
        console.print("  - Copia el exe (y flujo_workspace si usas) a un lugar fijo (ej. Desktop o C:\\flujo).")
        console.print("  - Usa Inno Setup (https://jrsoftware.org - gratuito) para installer con Start Menu:")
        console.print(f"      [Setup]  AppName=flujo  AppVersion={_get_version()} OutputDir=installer")
        console.print("      [Files]  Source: dist\\flujo-hub.exe ; DestDir: {app}")
        console.print("      [Icons]  Name: {autoprograms}\\flujo ; Filename: {app}\\flujo-hub.exe")
        console.print("      (agrega .ico , asocia .json si quieres para proyectos)")
        console.print("  - Resultado: entrada en Inicio, desinstalador, icono real en barra de tareas.")
        console.print("")
        console.print("[dim]Todo gratis (PyInstaller + Pillow), Python-native, sin pagar nada. El exe es standalone para el diseñador Windows.[/]")
        console.print("[dim]Maneja paths frozen correctamente (asset vs workspace). Para actualizar: rebuild con flujo package después de cambios.[/]")
    except Exception as e:
        _err(f"PyInstaller falló: {e}")
    finally:
        # cleanup temp launcher
        try:
            if 'launcher_path' in locals() and Path(launcher_path).exists():
                Path(launcher_path).unlink(missing_ok=True)
        except Exception:
            pass


# ============================================================
# Clean
# ============================================================

@app.command()
def clean(
    cache: bool = typer.Option(True, "--cache/--no-cache", help="limpiar __pycache__"),
    generated: bool = typer.Option(False, "--generated", help="limpiar outputs regenerables"),
):
    """Limpiar archivos temporales del repo."""
    from .paths import repo_root
    import shutil
    root = repo_root()
    removed = 0
    if cache:
        for p in root.rglob("__pycache__"):
            if ".git" in p.parts:
                continue
            shutil.rmtree(p, ignore_errors=True)
            removed += 1
        for p in root.rglob("*.pyc"):
            if ".git" in p.parts:
                continue
            p.unlink(missing_ok=True)
            removed += 1
    if generated:
        for p in root.glob("projects/piezas_vectoriales/*/salida_generada"):
            shutil.rmtree(p, ignore_errors=True)
            removed += 1
    _ok(f"Limpieza: {removed} items removidos")


# ============================================================
# Init
# ============================================================

@app.command()
def init(
    fresh: bool = typer.Option(False, "--fresh", help="prepara workspace completo: carpetas, datadrops e índice"),
    rebuild_index: bool = typer.Option(True, "--rebuild-index/--no-rebuild-index", help="reconstruir índice SQLite en --fresh"),
):
    """Inicializa carpetas del repo/workspace (jobs/_template, data, inbox, datadrops)."""
    from .jobs.job import _ensure_template
    from .paths import repo_root, workspace_root, inbox_dir, jobs_dir, data_dir, datadrops_dir
    root = repo_root()
    workspace = workspace_root()
    tpl = _ensure_template(workspace)
    created = [
        jobs_dir(),
        inbox_dir(),
        data_dir(),
        datadrops_dir(),
        datadrops_dir() / "incoming",
    ]
    for d in created:
        d.mkdir(parents=True, exist_ok=True)
    _ok(f"Template: {tpl}")
    _ok(f"Workspace listo en {workspace}")

    if fresh:
        if rebuild_index:
            try:
                from .index.db import rebuild_index as _rebuild_index
                res = _rebuild_index()
                _ok(f"Índice reconstruido: {res.get('indexed', 0)} flyers")
            except Exception as e:
                _warn(f"No se pudo reconstruir índice: {e}")
        console.print("Siguiente recomendado: [cyan]flujo doctor[/] y luego [cyan]flujo app[/]")



# ============================================================
# Knowledge base
# ============================================================

@knowledge_app.command("list")
def knowledge_list(entity: str = typer.Argument("productoras", help="productoras | venues | logos | events")):
    """Lista entidades de la knowledge base."""
    from .knowledge.store import list_entities
    items = list_entities(entity)
    if not items:
        _warn(f"Sin entidades para {entity}")
        return
    for item in items:
        console.print(item)


@knowledge_app.command("show")
def knowledge_show(
    entity: str = typer.Argument(..., help="productora | venue | logo | event"),
    item_id: str = typer.Argument(..., help="ID a mostrar"),
):
    """Muestra una entidad YAML como JSON legible."""
    import json
    from .knowledge.store import load_entity
    try:
        data = load_entity(entity, item_id)
    except FileNotFoundError as e:
        _err(f"No existe: {e}")
    console.print(json.dumps(data, ensure_ascii=False, indent=2))


@knowledge_app.command("classify")
def knowledge_classify(text: str = typer.Argument(..., help="Texto/correo/pedido a clasificar")):
    """Clasifica un texto usando productoras/venues conocidos."""
    import json
    from .knowledge.store import classify_event_text
    console.print(json.dumps(classify_event_text(text), ensure_ascii=False, indent=2))


@knowledge_app.command("ingest-example")
def knowledge_ingest_example(
    path: Path = typer.Argument(..., help="Archivo o carpeta de ejemplo real"),
    type: str = typer.Option("unknown", "--type", help="flyer_evento | cartelera | suplemento | logo | etc."),
    producer: str = typer.Option("", "--producer", help="producer_id si se conoce"),
):
    """Copia un ejemplo real a knowledge/examples y crea manifest para IA."""
    from .knowledge.store import ingest_example
    try:
        manifest = ingest_example(path, example_type=type, producer=producer)
    except Exception as e:
        _err(str(e))
    _ok(f"Example manifest: {manifest}")


@knowledge_app.command("logo-source")
def knowledge_logo_source(
    producer: str = typer.Argument(..., help="producer_id, ej: creamfields"),
    source: Path = typer.Argument(..., help="imagen fuente del logo"),
):
    """Registra una fuente de logo para logo clean lab."""
    from .knowledge.store import register_logo_source
    try:
        path = register_logo_source(producer, source)
    except Exception as e:
        _err(str(e))
    _ok(f"Logo registrado: {path}")


# ============================================================
# Main
# ============================================================


@knowledge_app.command("logo-lab")
def knowledge_logo_lab(
    producer: str = typer.Argument(..., help="producer_id, ej: creamfields"),
    source: Path = typer.Argument(..., help="imagen fuente del logo"),
):
    """Bridge para Logo Clean Lab: prepara estructura de carpetas y manifest."""
    from .knowledge.store import prepare_logo_lab
    try:
        manifest_path = prepare_logo_lab(producer, source)
    except Exception as e:
        _err(str(e))
    _ok(f"Logo Lab preparado: {manifest_path}")



def main():
    app()


if __name__ == "__main__":
    main()




from flujo.cli_addons import register_addons
register_addons(app)
