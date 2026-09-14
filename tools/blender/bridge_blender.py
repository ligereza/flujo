# ============================================================
#  PUENTE BLENDER  (consola Python <-> Claude, via disco)
#  Mismo patron que el puente MYRA de Unreal (C:\ARICA\MYRA).
#  Pegar UNA sola vez en la consola Python de Blender:
#    exec(open(r"C:\IA\flujo\.claude\worktrees\ultracode-p0\tools\blender\bridge_blender.py", encoding="utf-8").read())
#
#  Que hace:
#   - Registra un timer (bpy.app.timers) que VIGILA C:\rd\AUTOMATIZACION\bridge\
#   - Cuando Claude deja request.py + request.id (id nuevo), ejecuta
#     request.py DENTRO de la sesion de Blender, captura stdout/errores
#     y responde en response.txt + response.id (= ese id).
#   - Escribe heartbeat.txt cada tick (~1 s) para confirmar que vive.
#   - No bloquea la UI. Re-pegarlo re-instala limpio.
#   - NO guarda el .blend nunca; los jobs son en memoria salvo que un
#     job lo pida explicitamente.
# ============================================================
import bpy
import io
import os
import sys
import time
import traceback

BR = r"C:\rd\AUTOMATIZACION\bridge"
os.makedirs(BR, exist_ok=True)
REQ_PY = os.path.join(BR, "request.py")
REQ_ID = os.path.join(BR, "request.id")
RES_TXT = os.path.join(BR, "response.txt")
RES_ID = os.path.join(BR, "response.id")
HEART = os.path.join(BR, "heartbeat.txt")


def _wr(path, txt):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(txt)
    os.replace(tmp, path)


def _rd(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None


# marca de instalacion inmediata (si esto existe pero no hay heartbeat,
# el crash fue en el registro del timer, no en el paste)
_wr(os.path.join(BR, "install.txt"), time.strftime("%H:%M:%S") + " exec ok")

# --- desregistrar puente previo si se re-pega ---
try:
    _old = bpy.app.driver_namespace.get("_FLUJO_BRIDGE")
    if _old is not None and bpy.app.timers.is_registered(_old):
        bpy.app.timers.unregister(_old)
except Exception:
    pass

# arranca marcando el request actual como YA atendido (no re-corre lo viejo)
_STATE = {"done": (_rd(REQ_ID) or "").strip(), "n": 0}


def _run_job(code, jid):
    buf = io.StringIO()
    o, e = sys.stdout, sys.stderr
    sys.stdout = sys.stderr = buf
    ok = True
    try:
        exec(compile(code, "<bridge %s>" % jid, "exec"),
             {"__name__": "__main__", "bpy": bpy})
    except Exception:
        ok = False
        traceback.print_exc()
    finally:
        sys.stdout, sys.stderr = o, e
    return ok, buf.getvalue()


def _tick():
    # NUNCA propagar una excepcion desde el timer: pase lo que pase,
    # devolver el intervalo y seguir vivo.
    try:
        _wr(HEART, "%s blend=%s jobs=%d" % (
            time.strftime("%H:%M:%S"), bpy.data.filepath, _STATE["n"]))
        jid = (_rd(REQ_ID) or "").strip()
        if jid and jid != _STATE["done"]:
            _STATE["done"] = jid
            code = _rd(REQ_PY) or ""
            ok, out = _run_job(code, jid)
            _STATE["n"] += 1
            _wr(RES_TXT, "[%s] job=%s\n%s" % ("OK" if ok else "ERROR", jid, out))
            _wr(RES_ID, jid)
    except Exception:
        try:
            _wr(os.path.join(BR, "tick_error.txt"), traceback.format_exc())
        except Exception:
            pass
    return 1.0


bpy.app.timers.register(_tick, first_interval=2.0)
bpy.app.driver_namespace["_FLUJO_BRIDGE"] = _tick
print("puente flujo listo, vigilando", BR)
