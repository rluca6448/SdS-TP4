"""Pipeline del TP4: compila el motor y corre todas las simulaciones, gráficos y animaciones.

Uso (desde la raíz del repo):
    python3 scripts/pipeline.py --listar                 # muestra los pasos y su duración aproximada
    python3 scripts/pipeline.py --rapido                 # prueba de humo con parámetros chicos (~10 min)
    python3 scripts/pipeline.py                          # todo, con los parámetros de la entrega (~2 h)
    python3 scripts/pipeline.py --solo sistema1,2.1.a    # solo algunos pasos
    python3 scripts/pipeline.py --omitir 2.1.b           # todo menos algunos pasos
    python3 scripts/pipeline.py --tp3-exe /ruta/al/TP3/build/sds_tp3    # suma el TP3 al punto 2.1.b

Pasos: compilar, sistema1, 2.1.a, 2.1.b, 2.2, 2.3, 2.4.a, animaciones.
El punto 2.3 se corre si existe scripts/distribucion_velocidades.py (se llama sin argumentos).
Los datos quedan en build/resultados/ y las figuras y animaciones en build/graficos/<punto>/. El paso 2.1.b mide tiempos: conviene no usar la computadora mientras corre.
"""
import argparse
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PY = sys.executable
S = RAIZ / "scripts"
RES = RAIZ / "build" / "resultados"
GRAF = RAIZ / "build" / "graficos"
TP4 = RAIZ / "build" / "tp4"
X0S = ["0.0175", "0.1000", "0.2075", "0.3025", "0.4000", "0.4925"]

p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument("--rapido", action="store_true", help="parámetros reducidos para probar que todo funciona")
p.add_argument("--solo", help="pasos a correr, separados por comas")
p.add_argument("--omitir", help="pasos a omitir, separados por comas")
p.add_argument("--listar", action="store_true", help="lista los pasos y sale")
p.add_argument("--sin-compilar", action="store_true", help="no recompilar el motor")
p.add_argument("--tp3-exe", help="ejecutable del TP3 para comparar en 2.1.b (se usa tal cual está compilado)")
p.add_argument("--detener-ante-error", action="store_true", help="cortar en el primer paso que falle")
args = p.parse_args()
R = args.rapido


def cmd(*partes):
    return [PY, *map(str, partes)]


def correr(c, **kw):
    """Corre un comando mostrando su salida; devuelve True si terminó bien."""
    print("  $ " + " ".join(map(str, c)), flush=True)
    return subprocess.run(list(map(str, c)), cwd=RAIZ, **kw).returncode == 0


# ---------------------------------------------------------------- pasos
def paso_compilar():
    return (correr(["cmake", "-S", ".", "-B", "build"], stdout=subprocess.DEVNULL)
            and correr(["cmake", "--build", "build"]))


def paso_sistema1():
    return correr(cmd(S / "oscilador_amortiguado.py"))


def paso_21a():
    out = RES / "2_1_a"
    if R:
        return correr(cmd(S / "energia_dt.py", "--tf", 2, "--dts", "1e-3,1e-4,1e-5", "--seeds", 1, "--out", out))
    dts = "1e-3,5e-4,2e-4,1e-4,5e-5,2e-5,1e-5,5e-6"
    ok = correr(cmd(S / "energia_dt.py", "--tf", 30, "--dts", dts, "--seeds", "1,2", "--out", out))
    if ok:  # versión ampliada, sin el dt que diverge
        ok = correr(cmd(S / "energia_dt.py", "--reusar", "--tf", 30, "--dts", "2e-4,1e-4,5e-5,2e-5,1e-5,5e-6",
                        "--seeds", "1,2", "--out", out, "--sufijo", "_zoom"))
    return ok


def paso_21b():
    out = RES / "2_1_b"
    base = (["--ns", "100,300", "--reps", 2, "--tf", 5] if R else [])
    ok = correr(cmd(S / "tiempos_N.py", *base, "--jobs", 1, "--out", out))
    if ok and args.tp3_exe:
        tp3 = out / "tp3"
        ok = correr(cmd(S / "tiempos_tp3.py", "--exe", args.tp3_exe, *base, "--out", tp3))
        if ok:
            tp3_base = (["--ns", "100,300", "--reps", 2, "--tf", 5] if R else [])
            ok = correr(cmd(S / "tiempos_N.py", "--reusar", *tp3_base, "--tp3", tp3 / "tp3_tiempos.csv", "--out", out))
    return ok


def paso_22():
    ok = True
    for n in (100, 20):
        extra = ["--tf", 20, "--puntos", 4, "--reps", 2] if R else ["--tf", 100, "--puntos", 11, "--reps", 5]
        ok = correr(cmd(S / "obstaculos_x0.py", "--n", n, *extra)) and ok
    return ok


def paso_23():
    script = S / "distribucion_velocidades.py"
    if not script.exists():
        print("  (2.3 todavía no está en el repo: se omite)")
        return None
    return correr(cmd(script))


def paso_24a():
    extra = ["--ns", "100,300", "--reps", 2, "--tf", 10] if R else []
    return correr(cmd(S / "densidad_t90.py", *extra))


def paso_gifs():
    estados = RES / "animaciones"  # archivos de estado; los GIF van a graficos/<punto>/
    estados.mkdir(parents=True, exist_ok=True)
    tf = 5 if R else 30
    # (nombre, argumentos del simulador, "cada fps x0" del visor, carpeta del GIF)
    trabajos = [("sin_obstaculos_N300", ["300", 5, "--sin-obstaculos"], "5 20 0.0175", "2_1_a")]
    if not R:
        trabajos += [(f"N{n}", [str(n), 5], "5 20 0.0175", "2_1_b") for n in (100, 300, 700)]
    xs = ["0.2075"] if R else X0S
    trabajos += [(f"x0_{x}", ["100", tf, "--x0", x, "--seed", 1], f"10 15 {x}", "2_2/gifs") for x in xs]

    def un_gif(trabajo):
        nombre, sim_args, vis, carpeta = trabajo
        cada, fps, x0 = vis.split()
        estado = estados / f"{nombre}.txt"
        destino = GRAF / carpeta
        destino.mkdir(parents=True, exist_ok=True)
        ok = subprocess.run([str(TP4), sim_args[0], str(sim_args[1]), str(estado), "--every", "1000", *map(str, sim_args[2:])],
                            cwd=RAIZ, capture_output=True).returncode == 0
        ok = ok and subprocess.run([PY, str(S / "visualizar.py"), str(estado), "--x0", x0, "--every", cada, "--fps", fps,
                                    "--save", str(destino / f"{nombre}.gif")], cwd=RAIZ, capture_output=True).returncode == 0
        print(f"  {'OK   ' if ok else 'FALLÓ'} {carpeta}/{nombre}.gif", flush=True)
        return ok

    with ThreadPoolExecutor(os.cpu_count() or 1) as pool:
        return all(pool.map(un_gif, trabajos))


PASOS = [  # id, descripción, función, duración aproximada (completo / rápido)
    ("compilar", "Compilar el motor (cmake)", paso_compilar, "1 min", "1 min"),
    ("sistema1", "Sistema 1: oscilador amortiguado, ECM vs dt", paso_sistema1, "10 s", "10 s"),
    ("2.1.a", "Energía total y elección de dt", paso_21a, "1 min", "10 s"),
    ("2.1.b", "Tiempo de ejecución vs N (+ TP3 con --tp3-exe)", paso_21b, "70 min", "1 min"),
    ("2.2", "Posición de los obstáculos: F_u(t) y t90 (N = 100 y N = 20)", paso_22, "8 min", "1 min"),
    ("2.3", "Distribución de velocidades (si existe el script)", paso_23, "?", "?"),
    ("2.4.a", "<t90> y <t100> vs densidad", paso_24a, "10 min", "1 min"),
    ("animaciones", "GIF de las simulaciones", paso_gifs, "2 min", "20 s"),
]
IDS = [pid for pid, *_ in PASOS]

if args.listar:
    print(f"{'paso':<12} {'completo':>9} {'--rapido':>9}  descripción")
    for pid, desc, _, tc, tr in PASOS:
        print(f"{pid:<12} {tc:>9} {tr:>9}  {desc}")
    sys.exit(0)

solo = set(args.solo.split(",")) if args.solo else set(IDS)
omitir = set(args.omitir.split(",")) if args.omitir else set()
if args.sin_compilar:
    omitir.add("compilar")
desconocidos = (solo | omitir) - set(IDS)
if desconocidos:
    p.error(f"pasos desconocidos: {', '.join(sorted(desconocidos))}. Pasos válidos: {', '.join(IDS)}")
if args.tp3_exe and not Path(args.tp3_exe).exists():
    p.error(f"no existe {args.tp3_exe}")
seleccion = [pid for pid in IDS if pid in solo and pid not in omitir]

if not TP4.exists() and "compilar" not in seleccion:
    print("Falta build/tp4: se agrega el paso 'compilar'")
    seleccion.insert(0, "compilar")

RES.mkdir(parents=True, exist_ok=True)
resultados = []
inicio = time.time()
for pid, desc, fn, *_ in PASOS:
    if pid not in seleccion:
        continue
    print(f"\n=== [{pid}] {desc}" + ("  (modo rápido)" if R else ""), flush=True)
    t0 = time.time()
    try:
        ok = fn()
    except Exception as e:  # un error de un paso no tira abajo a los demás
        print(f"  Error: {e}")
        ok = False
    resultados.append((pid, ok, time.time() - t0))
    if ok is False and args.detener_ante_error:
        break

lineas = ["", f"{'paso':<12} {'estado':<8} {'tiempo':>8}"]
for pid, ok, seg in resultados:
    estado = "omitido" if ok is None else ("OK" if ok else "FALLÓ")
    lineas.append(f"{pid:<12} {estado:<8} {seg / 60:7.1f}m")
lineas.append(f"\nTiempo total: {(time.time() - inicio) / 60:.1f} min")
generados = sorted(f for f in GRAF.rglob("*") if f.suffix in (".png", ".gif", ".mp4"))
lineas.append(f"\nFiguras y animaciones en {GRAF.relative_to(RAIZ)}/ ({len(generados)}):")
for f in generados:
    lineas.append(f"  {f.relative_to(GRAF)}  ({f.stat().st_size / 1024:.0f} KB)")
texto = "\n".join(lineas)
print(texto)
(RES / "pipeline_resumen.txt").write_text(texto + "\n")
sys.exit(0 if all(ok is not False for _, ok, _ in resultados) else 1)
