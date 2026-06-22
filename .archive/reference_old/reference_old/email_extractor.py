# -*- coding: utf-8 -*-
"""
email_extractor.py

Extrae links de Instagram desde:
1. Texto copiado (copy-paste)
2. Correos IMAP (lectura automática)
3. Archivo de historial
"""

import imaplib
import json
import os
import re
from datetime import datetime, timedelta
from typing import List, Tuple


class EmailExtractor:
    """Extrae links de correos"""

    def __init__(self, config_file=None):
        self.config_file = config_file or r"C:\rd\AUTOMATIZACION\CONFIGURACION\email_config.json"
        self.config = self._load_config()
        self.eventos_history = r"C:\rd\AUTOMATIZACION\CONFIGURACION\eventos.json"

    def _load_config(self):
        """Carga configuración de correo"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {
            "email": "",
            "app_password": "",  # Para Gmail: contraseña de aplicación
            "imap_server": "imap.gmail.com",  # Gmail IMAP
            "enabled": False
        }

    def save_config(self, email, app_password):
        """Guarda credenciales de correo (encriptadas es mejor)"""
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        self.config = {
            "email": email,
            "app_password": app_password,
            "imap_server": "imap.gmail.com",
            "enabled": True
        }
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)

    @staticmethod
    def extract_instagram_links(text: str) -> List[str]:
        """Extrae URLs de Instagram de un texto"""
        # Patrones de Instagram
        patterns = [
            r'https://(?:www\.)?instagram\.com/(?:p|reel|tv)/[\w-]+',
            r'instagram\.com/(?:p|reel|tv)/[\w-]+',
        ]

        links = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            links.extend(matches)

        # Eliminar duplicados y garantizar protocolo
        links = list(set(links))
        links = ["https://" + link if not link.startswith("http") else link for link in links]

        return links

    @staticmethod
    def extract_event_name(email_subject: str) -> str:
        """
        Extrae nombre del evento del asunto del correo
        Ej: "[EVENTO] Flyer para Fiesta Neon 28/02" -> "evento_2026_02_28_Fiesta_Neon"
        """
        # Limpiar el asunto
        subject = email_subject.strip()

        # Buscar fecha (DD/MM o DD-MM)
        date_match = re.search(r'(\d{1,2})[/-](\d{1,2})', subject)
        date_part = ""
        if date_match:
            day, month = date_match.groups()
            date_part = f"_2026_{month:0>2}_{day:0>2}"

        # Eliminar caracteres especiales, mantener espacios
        name_part = re.sub(r'[^\w\s]', '', subject).replace(' ', '_')[:30]

        return f"evento{date_part}_{name_part}".lower()

    def fetch_recent_emails(self, hours=1) -> List[Tuple[str, str, str]]:
        """
        Obtiene correos recientes (por defecto última hora)

        Returns:
            List de (sender, subject, body, links)
        """
        if not self.config.get("enabled"):
            return []

        emails = []
        try:
            mail = imaplib.IMAP4_SSL(self.config["imap_server"])
            mail.login(self.config["email"], self.config["app_password"])
            mail.select("INBOX")

            # Fecha límite
            date_limit = (datetime.now() - timedelta(hours=hours)).strftime("%d-%b-%Y")

            # Buscar correos con "instagram" o "evento" o "flyer"
            status, messages = mail.search(
                None,
                f'SINCE {date_limit}',
                'OR (TEXT "instagram") (OR (TEXT "evento") (TEXT "flyer"))'
            )

            for msg_id in messages[0].split():
                status, msg_data = mail.fetch(msg_id, "(RFC822)")
                msg = msg_data[0][1].decode()

                # Extraer sender y subject
                sender = re.search(r'From: (.+?)\n', msg)
                subject = re.search(r'Subject: (.+?)\n', msg)

                if subject:
                    subject = subject.group(1)
                    # Buscar links de Instagram
                    links = self.extract_instagram_links(msg)
                    if links:
                        emails.append({
                            'from': sender.group(1) if sender else "Unknown",
                            'subject': subject,
                            'links': links,
                            'event_name': self.extract_event_name(subject)
                        })

            mail.close()
            mail.logout()

        except Exception as e:
            print(f"Error conectando a correo: {e}")

        return emails

    def extract_from_clipboard(self, text: str) -> List[str]:
        """Extrae links del texto copiado al portapapeles"""
        return self.extract_instagram_links(text)

    def save_event_history(self, event_data):
        """Guarda historial de eventos procesados"""
        os.makedirs(os.path.dirname(self.eventos_history), exist_ok=True)

        history = {}
        if os.path.exists(self.eventos_history):
            with open(self.eventos_history, 'r', encoding='utf-8') as f:
                history = json.load(f)

        event_id = event_data.get('event_name', f"evento_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        history[event_id] = {
            'timestamp': datetime.now().isoformat(),
            'email_from': event_data.get('from', 'manual'),
            'subject': event_data.get('subject', ''),
            'instagram_links': event_data.get('links', []),
            'colors': event_data.get('colors', []),
            'blender_project': event_data.get('blender_project', '')
        }

        with open(self.eventos_history, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

        return event_id

    def get_event_history(self) -> dict:
        """Lee historial de eventos"""
        if os.path.exists(self.eventos_history):
            with open(self.eventos_history, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}


def setup_gmail_integration():
    """Guía para configurar integración con Gmail"""
    config_text = """
    CONFIGURACIÓN DE GMAIL (Opcional)

    Para integrar con Gmail automático:

    1. Habilita "Acceso de apps menos seguras" en tu cuenta Google:
       https://myaccount.google.com/u/0/lesssecureapps

    2. O usa contraseña de aplicación (más seguro):
       a. Ve a https://myaccount.google.com/security
       b. Busca "Contraseñas de apps"
       c. Genera una nueva contraseña para "Correo" en "Windows"
       d. Cópiala

    3. En la app, pega tus credenciales en la sección de Email

    4. La app buscará automáticamente correos con links de Instagram
       en la carpeta INBOX

    Si no quieres configurar, simplemente copia-pega el link manualmente.
    """
    return config_text


if __name__ == "__main__":
    extractor = EmailExtractor()

    # Ejemplo: Extrae links de texto
    test_text = """
    Hola, el evento es aquí:
    https://www.instagram.com/p/ABC123DEF/
    Confirma en: https://instagram.com/reel/XYZ789ABC/
    """

    links = extractor.extract_instagram_links(test_text)
    print(f"✓ Links encontrados: {links}")

    # Ejemplo: Nombre del evento
    subject = "[EVENTO] Fiesta Neon 28/02 - Confirmado"
    event_name = extractor.extract_event_name(subject)
    print(f"✓ Nombre evento: {event_name}")
