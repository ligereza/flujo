import os
import sys
import shutil
import imaplib
import email
import email.utils
import zipfile
import subprocess
from pathlib import Path
from datetime import datetime

from ..paths import repo_root, workspace_root


def _safe_extract_zip(zip_ref: zipfile.ZipFile, dest: Path) -> None:
    """Extract a zip after rejecting traversal/absolute member names."""
    dest = Path(dest).resolve()
    for info in zip_ref.infolist():
        name = info.filename.replace("\\", "/")
        parts = [part for part in name.split("/") if part and part != "."]
        if not parts or any(part == ".." for part in parts) or name.startswith("/"):
            raise ValueError(f"Ruta insegura en ZIP: {info.filename}")
        target = (dest / Path(*parts)).resolve()
        target.relative_to(dest)
    zip_ref.extractall(dest)

def _signed_airdrop_gate() -> "str | None":
    """VCD-09 signed-artifact gate for the mail path.

    The `From:` header is forgeable text, so it can never be the authorization
    to apply and push code. When the mail path is enabled, the payload MUST
    carry a valid HMAC-SHA256 signature (key in FLUJO_AIRDROP_HMAC_KEY): no
    key configured means nothing gets applied, and this path NEVER uses the
    human override (--allow-unsigned is a person typing it, not automation).

    Returns the refusal reason, or None when the extracted payload verifies.
    """
    from ..airdrop import SIGNING_KEY_ENV, get_signing_key, verify_airdrop

    if get_signing_key() is None:
        return (
            f"{SIGNING_KEY_ENV} no esta configurada: el canal de correo exige "
            "artefacto firmado (flujo airdrop sign) y sin clave no se aplica nada."
        )
    problems = verify_airdrop()
    if problems:
        return "firma del airdrop invalida: " + "; ".join(problems)
    return None


def check_and_apply_email_airdrops() -> dict:
    """Se conecta al buzón IMAP especificado en variables de entorno,
    busca correos con asunto '[flujo-airdrop]' de remitentes autorizados,
    descarga el archivo adjunto (que debe ser un ZIP de airdrop),
    lo extrae en _airdrop/ y ejecuta la validación y aplicación automática.
    """
    # VCD-09 (diagnostico de seguridad, 2026-07-27): esta funcion autoriza
    # comparando UNICAMENTE la direccion del header `From:`, descarga un ZIP, lo
    # aplica y dispara commit/push. `From:` no es una firma: es texto que
    # cualquiera escribe. SPF/DKIM/DMARC pueden ayudar en el servidor de correo,
    # pero aca no se verifica ningun resultado de autenticacion ni ninguna firma
    # del artefacto.
    #
    # Y no la llama nadie: se busco en todo el repo y no hay comando ni cron que
    # la invoque. Asi que es una mina sin consumidor, y lo proporcional no es
    # inventarle un sistema de firmas para algo que no se usa: es que no pueda
    # dispararse sola. Queda apagada salvo que alguien la encienda a proposito.
    #
    # Cierre del hallazgo (2026-07-31): el artefacto firmado existe. Aun con
    # FLUJO_IMAP_AUTOAPLICAR=1, `_signed_airdrop_gate()` exige clave
    # FLUJO_AIRDROP_HMAC_KEY configurada Y firma HMAC-SHA256 valida del payload
    # (`flujo airdrop sign` / `verify`); sin eso no se aplica nada. Esta guarda
    # de encendido se mantiene igual como primera capa: encender el canal sigue
    # siendo una decision humana explicita.
    if os.getenv("FLUJO_IMAP_AUTOAPLICAR") != "1":
        return {"ok": False, "error":
                "aplicar airdrops por correo esta apagado: autoriza por el header "
                "From:, que es falsificable, y aplica y pushea codigo. Encender "
                "a proposito con FLUJO_IMAP_AUTOAPLICAR=1."}

    host = os.getenv("FLUJO_IMAP_HOST")
    user = os.getenv("FLUJO_IMAP_USER")
    password = os.getenv("FLUJO_IMAP_PASSWORD")
    allowed = {s.strip().lower() for s in os.getenv("FLUJO_IMAP_ALLOWED_SENDERS", "").split(",") if s.strip()}

    if not (host and user and password):
        return {"ok": False, "error": "Faltan variables de entorno IMAP (FLUJO_IMAP_HOST, FLUJO_IMAP_USER, FLUJO_IMAP_PASSWORD)."}

    try:
        # Conexión SSL
        mail = imaplib.IMAP4_SSL(host)
        mail.login(user, password)
        mail.select("inbox")

        # Buscar correos no leídos con el asunto específico
        status, response = mail.search(None, '(UNSEEN SUBJECT "[flujo-airdrop]")')
        if status != "OK":
            return {"ok": True, "processed": 0, "message": "No se encontraron correos nuevos."}

        email_ids = response[0].split()
        if not email_ids:
            return {"ok": True, "processed": 0, "message": "No hay correos pendientes."}

        processed_count = 0
        applied_airdrops = []

        for e_id in email_ids:
            status, data = mail.fetch(e_id, "(RFC822)")
            if status != "OK":
                continue

            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)

            # Verificar remitente: comparar la direccion exacta parseada,
            # nunca por substring (un dominio lookalike o el display-name
            # burlarian el whitelist).
            from_addr = email.utils.parseaddr(str(msg.get("From", "")))[1].lower()
            authorized = bool(from_addr) and from_addr in allowed


            if not authorized:
                # Marcar como leído para no procesarlo de nuevo, o ignorar
                mail.store(e_id, "+FLAGS", "\\Seen")
                continue

            # Buscar adjuntos .zip
            for part in msg.walk():
                if part.get_content_maintype() == "multipart":
                    continue
                if part.get("Content-Disposition") is None:
                    continue

                filename = part.get_filename()
                if filename and filename.lower().endswith(".zip"):
                    # Descargar el zip
                    zip_data = part.get_payload(decode=True)

                    # Guardar temporalmente
                    temp_zip = Path(workspace_root()) / "temp_airdrop.zip"
                    temp_zip.write_bytes(zip_data)

                    # Extraer en _airdrop/ de forma segura
                    airdrop_dir = Path(repo_root()) / "_airdrop"
                    if airdrop_dir.exists():
                        shutil.rmtree(airdrop_dir)
                    airdrop_dir.mkdir(parents=True, exist_ok=True)

                    with zipfile.ZipFile(temp_zip, "r") as zip_ref:
                        _safe_extract_zip(zip_ref, airdrop_dir)

                    try:
                        temp_zip.unlink()
                    except Exception:
                        pass

                    # VCD-09: signed artifact required. Refuse BEFORE invoking
                    # apply; this path never passes --allow-unsigned (the human
                    # override exists only for a person at a keyboard).
                    gate_error = _signed_airdrop_gate()
                    if gate_error is not None:
                        mail.store(e_id, "+FLAGS", "\\Seen")
                        processed_count += 1
                        applied_airdrops.append({
                            "filename": filename,
                            "success": False,
                            "error": gate_error,
                        })
                        break  # Solo un zip por correo

                    # Aplicar el airdrop usando el Python actual. Cambios al motor
                    # solo se permiten con opt-in explícito por variable de entorno.
                    message = f"Auto-applied from email at {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                    cmd = [sys.executable, "-m", "flujo", "airdrop", "apply"]
                    if os.getenv("FLUJO_IMAP_ALLOW_AIRDROP_ENGINE") == "1":
                        cmd.append("--allow-airdrop-engine")
                    cmd.append(message)

                    res = subprocess.run(cmd, cwd=str(repo_root()), capture_output=True, text=True)

                    # Marcar correo como leído
                    mail.store(e_id, "+FLAGS", "\\Seen")
                    processed_count += 1
                    applied_airdrops.append({
                        "filename": filename,
                        "success": res.returncode == 0,
                        "stdout": res.stdout,
                        "stderr": res.stderr
                    })
                    break # Solo un zip por correo

        return {
            "ok": True,
            "processed": processed_count,
            "results": applied_airdrops
        }

    except Exception as e:
        return {"ok": False, "error": str(e)}
