# 🐣 Manual del Agente Rookie (v0.42.2)

Si eres el nuevo agente, lee esto antes de asumir que sabes lo que haces. Yo casi rompo el repo por "Rookie".

## 1. La ONG es lo Primero
Trabajamos para **Reduciendo Daño (RD)**. No somos una agencia de branding. Si ves lógica de "marca rígida", elimínala, pero mantén la **memoria técnica**. Los colores de los reactivos y los logos limpios son herramientas de salud, no estética.

## 2. No seas Destructivo (Lección v0.42.2)
Cuando elimines fricción (como el antiguo `brand.py`):
- **No rompas la CLI:** Asegúrate de que las sub-apps como `datadrop` sigan registradas. Si borras una app, el NameError romperá todo el sistema.
- **Mantén compatibilidad:** Deja comandos legacy como placeholders si es necesario para no romper scripts de Windows.
- **Migra, no borres:** La lógica de logos ahora vive en `knowledge/logos`.

## 3. El Entorno es Sagrado (Windows Git Bash)
- El usuario usa **`py`**, no `python`. Respeta sus alias.
- Usa **`npm ci`** y **`npx`** para herramientas de Node. Evita depender de instalaciones globales en Windows.
- El **Airdrop** debe pasar `validate_airdrop.py` (requiere HANDOFF_.md obligatorio dentro de _airdrop/).

## 4. Documentos Maestro
- `datadrops/Propuesta_Reduciendo_Dano.txt`: La biblia operativa. Entiende el stand y el testeo antes de codear.
- `linea_editorial/v4.1.md`: Especificaciones técnicas (HEX reactivos), no sugerencias creativas.
- `agente_rookie.md`: Este archivo.

## 5. El Flujo de Verificación
Antes de entregar, pide al usuario correr:
```bash
py -m flujo verify
cd web && npm run build:context && cd ..
```
Si algo falla en el `verify`, no es una entrega válida.

**Menos branding, más intervención.**
