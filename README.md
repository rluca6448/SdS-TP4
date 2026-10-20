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
./tp4 [N] [tiempo_final] [archivo_salida] [--dt X] [--every N] [--seed S] [--x0 X] [--sin-obstaculos]
```

Los argumentos son opcionales. Los tres primeros son posicionales y van en ese orden; las opciones con `--` pueden ir en cualquier lugar. Lo que no se pasa usa los valores de `SimulationConfig` (`include/simulation/SimulationConfig.h`):

| Parámetro | Valor por defecto | Argumento de línea de comandos |
| --- | --- | --- |
| `particleCount` (N) | 100 | 1.º |
| `finalTime` | 5 s | 2.º |
| archivo de salida | `output.txt` | 3.º |
| `dt` | 1e-5 s | `--dt X` |
| `x0` (posición de los obstáculos) | 0.0175 m (en contacto) | `--x0 X` (entre r y R − r) |
| `springConstant` (k) | 1e4 N/m | no, editar `SimulationConfig.h` |
| `outputEverySteps` | 100 (guarda cada 1e-3 s) | `--every N` |
| `seed` | 1 | `--seed S` |
| `initialSpeed` (v0) | 1 m/s | no, editar `SimulationConfig.h` |
| `obstacles` | con obstáculos | `--sin-obstaculos` (sistema sin obstáculos) |

Con los valores por defecto (N = 100, 5 s) tarda unos 2 s. Los pares en contacto se buscan con una grilla de celdas. Para N grande (> ~440) la ubicación inicial al azar satura y se usa una red hexagonal con ruido; el máximo es N = 715.

## Formato de salida

Texto plano. Por cada estado guardado:

```
<tiempo>
<x> <y> <vx> <vy> <color>      # una línea por partícula
                               # línea en blanco
```

`color` es `1` si la partícula está fresca y `0` si ya está usada. Hay un estado en `t = 0` y luego uno cada `outputEverySteps` pasos.

Junto al output se escriben dos archivos más, en los mismos instantes. `<salida>_energia.txt` (por ejemplo `output_energia.txt`) tiene la energía total (cinética más elástica de los contactos, en J):

```
# t E
0 3.75
0.001 3.74999...
```

`<salida>_usadas.txt` tiene la cantidad de partículas usadas (`# t N_usadas`), de donde sale F_u(t) sin leer el estado completo.

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

## Scripts de análisis

Todos se corren desde la raíz con el proyecto compilado. Los datos quedan en `build/resultados/` y las figuras en `build/graficos/<punto>/` (los gráficos no llevan título). Todos aceptan `--reusar` (no corre, solo vuelve a analizar lo que ya existe) y `--out`.

| Script | Punto | Qué hace |
| --- | --- | --- |
| `oscilador_amortiguado.py` | Sistema 1 | Oscilador amortiguado: trayectorias y ECM vs dt de Euler, Verlet, Velocity Verlet y Beeman. `--verlet-v atras\|centrada` elige cómo se estima la velocidad en Verlet. |
| `energia_dt.py` | 2.1.a | Energía total vs dt (N = 300, sin obstáculos). Opciones `--tf`, `--n`, `--dts`, `--seeds`, `--graficos`, `--sufijo`. |
| `tiempos_N.py` | 2.1.b | Tiempo de ejecución vs N (log-log, con desvío). `--tp3 archivo.csv` superpone el TP3. Para medir usar `--jobs 1`. |
| `tiempos_tp3.py` | 2.1.b | Mide el tiempo del TP3 (`--exe` ejecutable ya compilado, que se usa tal cual) y genera el CSV para `--tp3`. |
| `obstaculos_x0.py` | 2.2 | F_u(t) y ⟨t90⟩ vs x0 entre r y R − r. Opciones `--n`, `--tf`, `--puntos`, `--x0s`, `--reps`. |
| `densidad_t90.py` | 2.4.a | ⟨t90⟩ y ⟨t100⟩ vs densidad ρ = N/área, con x0 = r. Opciones `--ns`, `--reps`, `--tf`. |
| `visualizar.py` | animaciones | Ver sección Visualizar. |
| `pipeline.py` | todo | Compila y corre todos los pasos (ver abajo). |

Con los resultados del grupo, dt = 1e-5 s conserva la energía con un error máximo de 1e-5 a 2e-5 (N = 300, 30 s, dos semillas). El script de 2.3 (distribución de velocidades) lo hace otra persona; el pipeline lo corre si existe `scripts/distribucion_velocidades.py`.

## Pipeline

```bash
python3 scripts/pipeline.py --listar                 # pasos y duración aproximada
python3 scripts/pipeline.py --rapido                 # prueba con parámetros chicos
python3 scripts/pipeline.py                          # todo, con los parámetros de la entrega (~2 h)
python3 scripts/pipeline.py --solo sistema1,2.1.a    # solo algunos pasos
python3 scripts/pipeline.py --omitir 2.1.b           # todo menos algunos pasos
python3 scripts/pipeline.py --tp3-exe /ruta/sds_tp3  # suma el TP3 al punto 2.1.b
```

Pasos: `compilar`, `sistema1`, `2.1.a`, `2.1.b`, `2.2`, `2.3`, `2.4.a`, `animaciones`. Opciones: `--sin-compilar`, `--detener-ante-error`. Deja un resumen en `build/resultados/pipeline_resumen.txt`. El paso 2.1.b mide tiempos: conviene no usar la computadora mientras corre.

## Dónde quedan los resultados

Los datos (CSV y TXT) quedan en `build/resultados/`, y las figuras y animaciones en `build/graficos/`, con una carpeta por punto:

```
build/graficos/
  sistema1/   trayectorias y ECM vs dt
  2_1_a/      energía total (dt elegido y vecinos), desvío vs dt, GIF sin obstáculos
  2_1_b/      tiempo de ejecución vs N, ubicación inicial, GIF de N = 100 a 700
  2_2/        N100/ y N20/ (F_u(t) y t90 vs x0) y gifs/ (una animación por x0)
  2_4_a/      t90 y t100 vs densidad y F_u(t) (complementos/: corridas de 30 s y de validación)
  otros/      imágenes de pruebas anteriores
```

## Estructura

```
src/main.cpp                  punto de entrada
scripts/                      análisis y figuras (ver Scripts de análisis)
include/ y lib/
  types/                      Vector2D, Particle, Obstacle, Board
  simulation/                 Simulation (motor) y SimulationConfig
  io/                         StateWriter (escribe el output)
  neighbours/                 Grid (grilla de celdas para buscar pares en contacto)
```

## Cómo funciona

- **Contacto:** si dos discos se superponen una distancia `ξ = r_i + r_j - |r_j - r_i|`, cada uno recibe una fuerza `-k·ξ` a lo largo de la línea que une los centros. Si `ξ ≤ 0` no hay fuerza.
- **Pared:** se trata como una partícula fija de radio r ubicada fuera del círculo, sobre la recta radial que pasa por la partícula, en `(R + r)·n̂`. Se recalcula en cada paso.
- **Obstáculos:** partículas fijas de radio r.
- **Verlet:** `r(t+dt) = 2·r(t) − r(t−dt) + a(t)·dt²`. El primer paso estima `r(−dt)` con Euler hacia atrás. La velocidad no entra en la dinámica, y se estima con la diferencia hacia atrás `(r(t) − r(t−dt))/dt + ½·a(t)·dt` para dejar posición, velocidad y aceleración en el mismo instante.
- **Fresca → usada:** al final de cada paso, una partícula fresca que se superpone con un obstáculo pasa a usada y no vuelve a ser fresca.

## Estado

- **Hecho:** ubicación inicial sin solapamiento, fuerzas de contacto (partículas, obstáculos y pared), integración con Verlet, grilla de vecinos, conversión fresca → usada, salida a archivo (estado, energía, usadas), visor, Sistema 1, elección de `dt` (2.1.a), tiempos vs N (2.1.b), posición de los obstáculos (2.2), densidad (2.4.a) y pipeline.
- **Pendiente:** distribución de velocidades (2.3) y videos para la entrega.
