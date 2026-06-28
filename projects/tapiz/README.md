# VibeCode

Librería de acompañamiento visual para la generación de código, inspirada en la idea de que **el vacío entre el código cobra vida** mientras una IA o un agente escriben.

Como Colorama, se instala y se activa con una llamada. Desde ese momento, la salida de tu agente se transforma sutilmente: los espacios se iluminan, el texto respira en gris, y la intensidad visual es **proporcional a la velocidad de generación**. Cuando la IA descansa, la visualización también descansa.

No consume tokens ni recursos externos: solo observa localmente la estructura de la salida.

## Instalación

```bash
pip install .
```

## Uso

### Activación global (modo Colorama)

```python
import vibecode

vibecode.init()

# ... aquí tu agente o IA genera código ...

vibecode.deinit()
```

### Context manager

```python
import vibecode

with vibecode.watch():
    agent.run(prompt)
```

### Decorador

```python
import vibecode

@vibecode.life
def my_agent(prompt):
    return generate_code(prompt)
```

### Agentes personalizados

Si tu agente no imprime por stdout, puedes darle pulsos manuales:

```python
import vibecode

vibecode.init()
for chunk in llm_stream(prompt):
    print(chunk, end="")
    vibecode.pulse(len(chunk))
vibecode.deinit()
```

## Modos

- `negative` (default): los espacios se iluminan con fondo gris/blanco; el texto es gris tenue.
- `blocks`: los espacios se representan con bloques de densidad (`▁▂▃▄▅▆▇█`).

```python
with vibecode.watch(mode="blocks"):
    agent.run(prompt)
```

## Nota importante (para diseñadores)

Todas las salidas visuales (incluyendo visualizaciones de tapiz) deben respetar la identidad "flujo" definida en projects/flujo/flujo.json. Si una página o visual se ve amateur, daña la confianza del cliente en el trabajo profesional.

## Concepto

La idea es que la generación de código no sea solo texto cayendo, sino un **patrón en negativo**: el movimiento de la IA se aprecia en los espacios que deja. A mayor actividad, mayor brillo; al completarse, la pantalla descansa.

## Ejemplo

```bash
python example_agent.py
```
