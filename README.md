# SdS TP4 – Billar circular (dinámica molecular regida por el paso temporal)

Simulación de N partículas en un billar circular de radio R = 0.51 m con dos obstáculos fijos en `(-x0, 0)` y `(+x0, 0)`. Las partículas interactúan por contacto con un resorte lineal y se integran con el esquema de Verlet. Una partícula "fresca" pasa a "usada" la primera vez que toca un obstáculo.

## Requisitos

- g++ con soporte de C++17 y CMake ≥ 3.10.
- Para el visor: Python 3 con `numpy` y `matplotlib` (que trae Pillow para guardar `.gif`), y `ffmpeg` para guardar `.mp4`.

## Compilar

```bash
cmake -S . -B build
cmake --build build
```

## Ejecutar

```bash
cd build
./tp4 [N] [tiempo_final] [archivo_salida]
```

Los argumentos son opcionales y van en ese orden. Lo que no se pasa usa los valores de `SimulationConfig` (`include/simulation/SimulationConfig.h`):

| Parámetro | Valor por defecto | Argumento de línea de comandos |
| --- | --- | --- |
| `particleCount` (N) | 100 | 1.º |
| `finalTime` | 5 s | 2.º |
| archivo de salida | `output.txt` | 3.º |
| `dt` | 1e-5 s | no, editar `SimulationConfig.h` |
| `x0` (posición de los obstáculos) | 0.0175 m (en contacto) | no, editar `SimulationConfig.h` |
| `springConstant` (k) | 1e4 N/m | no, editar `SimulationConfig.h` |
| `outputEverySteps` | 100 (guarda cada 1e-3 s) | no, editar `SimulationConfig.h` |
| `seed` | 1 | no, editar `SimulationConfig.h` |
| `initialSpeed` (v0) | 1 m/s | no, editar `SimulationConfig.h` |

Con los valores por defecto (N = 100, 5 s) tarda unos 45 s. La búsqueda de pares es O(N²) por ahora.

## Formato de salida

Texto plano. Por cada estado guardado:

```
<tiempo>
<x> <y> <vx> <vy> <color>      # una línea por partícula
                               # línea en blanco
```

`color` es `1` si la partícula está fresca y `0` si ya está usada. Hay un estado en `t = 0` y luego uno cada `outputEverySteps` pasos.

## Visualizar

```bash
python3 scripts/visualizar.py build/output.txt --every 5                 # ventana
python3 scripts/visualizar.py build/output.txt --every 5 --save sim.mp4  # guarda el video
python3 scripts/visualizar.py build/output.txt --png cuadro.png --frame 40
```

Dibuja el billar, los obstáculos y las partículas (frescas en azul, usadas en rojo). El título muestra el tiempo y cuántas partículas están usadas.

| Opción | Qué hace |
| --- | --- |
| `--every N` | Muestra 1 de cada N estados. Conviene usarla: cada estado guardado es un cuadro y animarlos todos es lento. |
| `--save archivo` | Guarda la animación sin abrir ventana. El formato sale de la extensión: `.mp4` (necesita `ffmpeg`) o `.gif`. |
| `--fps N` | Cuadros por segundo de `--save` (30 por defecto). |
| `--png archivo` | Guarda un solo cuadro y sale. Con `--frame i` se elige cuál (el último por defecto). No se puede usar junto con `--save`. |
| `--x0 X` | Posición de los obstáculos. El archivo de salida no la guarda, así que debe coincidir con la de la simulación. |

## Estructura

```
src/main.cpp                  punto de entrada
scripts/visualizar.py         visor del output (Python)
include/ y lib/
  types/                      Vector2D, Particle, Obstacle, Board
  simulation/                 Simulation (motor) y SimulationConfig
  io/                         StateWriter (escribe el output)
  neighbours/                 Grid (todavía no se compila ni se usa)
```

## Cómo funciona

- **Contacto:** si dos discos se superponen una distancia `ξ = r_i + r_j - |r_j - r_i|`, cada uno recibe una fuerza `-k·ξ` a lo largo de la línea que une los centros. Si `ξ ≤ 0` no hay fuerza.
- **Pared:** se trata como una partícula fija de radio r ubicada fuera del círculo, sobre la recta radial que pasa por la partícula, en `(R + r)·n̂`. Se recalcula en cada paso.
- **Obstáculos:** partículas fijas de radio r.
- **Verlet:** `r(t+dt) = 2·r(t) − r(t−dt) + a(t)·dt²`. El primer paso estima `r(−dt)` con Euler hacia atrás. La velocidad no entra en la dinámica, y se estima con la diferencia hacia atrás `(r(t) − r(t−dt))/dt + ½·a(t)·dt` para dejar posición, velocidad y aceleración en el mismo instante.
- **Fresca → usada:** al final de cada paso, una partícula fresca que se superpone con un obstáculo pasa a usada y no vuelve a ser fresca.

## Estado

- **Hecho:** ubicación inicial sin solapamiento, fuerzas de contacto (partículas, obstáculos y pared), integración con Verlet, conversión fresca → usada, salida a archivo y visor.
- **Pendiente:** energía total para elegir `dt` (2.1.a), grilla de vecinos y tiempos de ejecución (2.1.b), análisis de `t90` y obstáculos (2.2 y 2.4), distribución de velocidades (2.3) y animación para la entrega.
