import os
import requests
from pathlib import Path

def upload_to_canva(file_path: Path, asset_name: str) -> dict:
    """Sube una pieza (como un SVG o PNG) a la cuenta de Canva de la ONG.
    Utiliza el Token de API configurado en la variable de entorno CANVA_API_TOKEN.
    """
    token = os.getenv("CANVA_API_TOKEN")
    if not token:
        return {"ok": False, "error": "Falta la variable de entorno CANVA_API_TOKEN con el token oficial de Canva."}
        
    file_path = Path(file_path)
    if not file_path.exists():
        return {"ok": False, "error": f"El archivo no existe: {file_path}"}
        
    # Endpoint oficial de Canva API para subir recursos (assets)
    url = "https://api.canva.com/rest/v1/assets"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/octet-stream",
        "Canva-Asset-Name": asset_name
    }
    
    try:
        # Canva API v1 asset upload accepts binary data directly
        data = file_path.read_bytes()
        res = requests.post(url, headers=headers, data=data)
        if res.status_code in (200, 201):
            return {"ok": True, "data": res.json()}
        else:
            return {"ok": False, "error": f"Canva API error {res.status_code}: {res.text}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
