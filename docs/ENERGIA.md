ENERGIA.md -- Medicion Wh/dia GPU+CPU y politica valle
=========================================================

PROPOSITO
---------
Medir consumo de energia en MAK (maquina Linux Blender renderizador) por componente
(GPU NVIDIA + CPU Intel RAPL) e integrar sobre 24h para contabilizar Wh/dia.
Detectar picos y optimizar horario de render a ventana de electricidad barata (00:00-07:00).

COMO FUNCIONA
-------------

energia_log.py extiende energia.py (WoL/suspend) con telemetria:

1. leer_gpu_w()
   Subprocess: nvidia-smi --query-gpu=power.draw --format=csv,noheader,nounits
   Retorna: watts (float) o None si GPU no disponible.
   Timeout: 3s. Si falla, sigue sin crash.

2. leer_cpu_uj()
   Lee archivo virtual: /sys/class/powercap/intel-rapl:0/energy_uj
   Retorna: microjoules acumulados (int) o None si no existe.
   Nota: solo Intel; AMD RAPL es otro path.

3. muestrear(intervalo_s=5)
   Toma snapshot: GPU instantaneo + CPU delta (dos lecturas separadas intervalo_s).
   Retorna: {"ts": "ISO 8601", "gpu_w": float|None, "cpu_w": float|None}
   cpu_w = (uj_final - uj_inicio) / intervalo_s / 1e6 watts

4. acumular(ruta_jsonl)
   Append una muestra a archivo JSONL (crea si no existe).
   Ruta default: cultura/mak_plataforma/energia.jsonl

5. resumen(ruta_jsonl, dias=7)
   Lee JSONL y agrupa por fecha calendario.
   Por cada dia: integra potencia (promedio entre muestras consecutivas * delta tiempo).
   Retorna tabla ASCII: Fecha | GPU Wh/dia | CPU Wh/dia | TOTAL
   Tolerante: archivo vacio, sin datos en ventana, etc. -> "(sin datos)"

INSTALACION
-----------

Maquina MAK (Linux, Blender renderizador):

1. GPU NVIDIA:
   pip install nvidia-smi  # ya viene con driver CUDA

2. CPU Intel RAPL:
   Kernel lo expone en /sys/class/powercap/intel-rapl:0/ (read-only)
   Verifica: cat /sys/class/powercap/intel-rapl:0/energy_uj
   Si no existe, script sigue con cpu_w=None (GPU se mide igual)

3. Script:
   cp cultura/mak_plataforma/energia_log.py ~/plataforma/energia_log.py
   chmod +x ~/plataforma/energia_log.py

USO
---

A. Muestreo (cada 5 minutos via cron):
   */5 * * * * python3 ~/plataforma/energia_log.py muestra >> /var/log/energia.log 2>&1

   Genera: ~/plataforma/energia.jsonl
   Formato: linea JSON por muestra, timestamp ISO, potencias en watts.

B. Resumen (en operador, para revisar):
   python3 ~/plataforma/energia_log.py resumen
   python3 ~/plataforma/energia_log.py resumen 14  # ultimos 14 dias

   Salida:
   Fecha        | GPU Wh/dia | CPU Wh/dia | Total Wh/dia
   -------------------------------------------------------
   2026-07-22   |      45.23 |      18.50 |       63.73
   ...
   TOTAL        |    1234.56 |     892.10 |     2126.66

POLITICA VALLE (Render Schedule)
--------------------------------

Objetivo: minimizar costo electrico rindiendo en horario barato (valle).

1. Ventana de render recomendada: 00:00 - 07:00 (7h dia UTC).
   (Ajustar segun tarifa local; en Chile suele ser 00:00-07:00 / 22:00-23:30)

2. Logica en capataz.py (orch MAK):
   - Leer resumen() cada dia a las 07:05 (post-valle)
   - Si promedio Wh/dia creció >10% respecto semana anterior:
     * Alarma a operador (check job bloats, filtros ineficientes)
     * Reducir paralelismo render en siguiente ciclo

3. Herramientas MAK para cumplir:
   energia.py dormir    # MAK duerme (WoWLAN armado)
   xio wake             # Telefono la despierta via magic packet a MAC_WIFI
   cron 23:55           # trigger: wake + espera conexion + inicia capataz
   cron 07:30           # trigger: dormir (tras postproceso)

4. Contingencia: si no hay datos (GPU/RAPL falla):
   - Script sigue corriendo (campos None en JSONL)
   - resumen() muestra "None" o salta esos componentes
   - Operador es responsable de investigar hardware

PENDIENTES / NEXT
-----------------

1. Autostart Ollama-WIN (en Windows kvm-link):
   - energia_log.py solo mide Linux MAK
   - Para sincronizar render + inferencia, necesita coordinacion xio
   - TODO: agregar wake/sleep de Windows desde MAK via WoL al PC Windows

2. Alertas anomalia:
   - Deteccion de picos GPU anomalos (job runaway)
   - Notificacion por Telegram/slack a equipo

3. Proyeccion costo:
   - Tarifa en $/kWh (desde cuota base MAK)
   - Pronostico costo semanal

4. Multi-GPU:
   - Actual: nvidia-smi lee GPU unica
   - TODO: Query todas las GPUs si existen

TESTING
-------

python3 -m pytest tests/test_energia_log.py -v

Cubre:
- Mock de nvidia-smi (OK, timeout, error parse)
- Mock de RAPL read (OK, no existe, error parse)
- Muestreo ambos sensores, solo uno
- Acumular crea/append JSONL
- Resumen integra Wh/dia, maneja datos viejos/vacios
- CLI parsea argumentos

CODIGO
------

Ubicacion: cultura/mak_plataforma/energia_log.py
Tests: tests/test_energia_log.py
Stdlib puro (sin deps externa): json, subprocess, sys, datetime, pathlib
ASCII-only (para robustez en Linux MAK)
Tolerancia: sin GPU/RAPL -> None, sigue

EJEMPLO: 7 dias de datos

$ python3 energia_log.py resumen
Fecha        | GPU Wh/dia | CPU Wh/dia | Total Wh/dia
-------------------------------------------------------
2026-07-16   |     102.45 |      42.30 |      144.75
2026-07-17   |      98.20 |      40.15 |      138.35
2026-07-18   |     145.67 |      48.90 |      194.57
2026-07-19   |      89.34 |      35.67 |      125.01
2026-07-20   |     125.78 |      44.23 |      170.01
2026-07-21   |      67.89 |      32.10 |      100.99
2026-07-22   |      51.23 |      28.45 |       79.68
-------------------------------------------------------
TOTAL        |     680.56 |     271.80 |      952.36

Promedio: 136.51 Wh/dia (952.36 / 7)

Accion: si 2026-07-18 > 194 Wh/dia, investigar job o settings Blender ese dia.
