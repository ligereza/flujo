# -*- coding: utf-8 -*-
"""
flujo.cli_addons  -  Registra los subcomandos serve/index/route
en la app Typer existente, SIN pisar tus comandos (health/doctor/job/eventos...).

Se agrupan bajo el namespace 'hub' para no colisionar con nada:
    py -m flujo hub serve   [--port 8777] [--open]
    py -m flujo hub index   <build|stats|find|versions|dupes|cleanup|agent-brief> ...
    py -m flujo hub route    <where|cuna|doctor> ...

Integracion (UNA linea en cli.py, despues de crear `app`):
    from flujo.cli_addons import register_addons
    register_addons(app)

No reemplaza nada. Si 'hub' ya existiera, ajusta el nombre aqui.
"""

import typer

hub_app = typer.Typer(help="Hub: servidor local + index/route del arbol de material ($FLUJO_RD_ROOT, ver MAPA.md).",
                      no_args_is_help=True)


@hub_app.command("serve")
def hub_serve(port: int = 8777, host: str = "127.0.0.1", open: bool = False):
    """Levanta el servidor local del hub (HTML + /api)."""
    from flujo.serve import server
    server.run(port=port, open_browser=open, host=host)


@hub_app.command("index", context_settings={"allow_extra_args": True,
                                             "ignore_unknown_options": True})
def hub_index(ctx: typer.Context):
    """Indexa el arbol de material ($FLUJO_RD_ROOT) para agentes. Pasa args tal cual al indexador.
    Ej: py -m flujo hub index agent-brief "necesito la etiqueta de creatina" """
    from flujo.index import indexer
    raise typer.Exit(indexer.main(ctx.args))


@hub_app.command("route", context_settings={"allow_extra_args": True,
                                             "ignore_unknown_options": True})
def hub_route(ctx: typer.Context):
    """Resuelve donde esta/va una pieza. Ej: py -m flujo hub route where --area eventos --pieza flyer"""
    from flujo.route import resolver
    raise typer.Exit(resolver.main(ctx.args))


def register_addons(app):
    """Llamar una vez desde cli.py:  register_addons(app)"""
    app.add_typer(hub_app, name="hub")
    return app
