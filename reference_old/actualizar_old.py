import instaloader
import os
import glob
import shutil
import time  # <-- Necesario para la pausa

# --- RUTAS DE TU CARPETA ---
CARPETA_BASE = r"C:\rd\AUTOMATIZACION"
RUTA_DROPLET = os.path.join(CARPETA_BASE, "Droplet_Flyer.exe")
ARCHIVO_PSD = os.path.join(CARPETA_BASE, "historia.psd")
ARCHIVO_INPUT = os.path.join(CARPETA_BASE, "input_ig.jpg")
# ---------------------------

def automatizar_flyer():
    os.chdir(CARPETA_BASE)

    if os.path.exists("temp_flyer"):
        shutil.rmtree("temp_flyer", ignore_errors=True)

    print("=== AUTOMATIZADOR DE FLYERS ===")
    url = input("SUELTALO XUXATUMAREEE:\n> ")

    try:
        if "/p/" in url:
            shortcode = url.split("/p/")[1].split("/")[0]
        elif "/reel/" in url:
            shortcode = url.split("/reel/")[1].split("/")[0]
        else:
            print("\nError: Link no válido.")
            return
    except Exception:
        print("\nHubo un error leyendo el link.")
        return

    print("\nDescargando flyer crudo desde Instagram...")
    L = instaloader.Instaloader(download_video_thumbnails=False, download_comments=False, save_metadata=False)

    try:
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        L.download_post(post, target="temp_flyer")
    except Exception as e:
        print(f"\nError al descargar: {e}")
        return

    archivos_jpg = glob.glob(os.path.join("temp_flyer", "*.jpg"))
    if not archivos_jpg:
        print("\nNo se encontró ninguna imagen.")
        return

    imagen_descargada = os.path.abspath(archivos_jpg[0])

    print("Actualizando input_ig.jpg...")
    if os.path.exists(ARCHIVO_INPUT):
        os.remove(ARCHIVO_INPUT)
    shutil.copy(imagen_descargada, ARCHIVO_INPUT)

    # 1. Pausa vital para que Windows asimile el archivo nuevo
    print("Dando un respiro al sistema para registrar la imagen...")
    time.sleep(2)

    print("\nAbriendo Photoshop...")

    # 2. EL TRUCO MAESTRO: Usar 'start' simula que tú mismo arrastraste el archivo con el mouse
    comando_magico = f'start "" "{RUTA_DROPLET}" "{ARCHIVO_PSD}"'
    os.system(comando_magico)

    print("\n¡ÉXITO! Proceso terminado.")

    shutil.rmtree("temp_flyer", ignore_errors=True)

if __name__ == "__main__":
    automatizar_flyer()
