"""Punto 2.1.b: tiempo de ejecución en función de N (con obstáculos en contacto, t_f = 30 s).

Corre build/tp4 para cada N con varias realizaciones (semillas), mide el tiempo de pared de cada
corrida y grafica el promedio con su desvío estándar (log-log). Opcionalmente superpone los
resultados del TP3 (--tp3 archivo.csv con columnas N,promedio,desvio, en segundos).

Uso (desde la raíz del repo, con el proyecto compilado):
    python3 scripts/tiempos_N.py                         # N = 100..700, 10 realizaciones, 30 s
    python3 scripts/tiempos_N.py --ns 100,300 --reps 3 --tf 5     # prueba rápida
    python3 scripts/tiempos_N.py --reusar --tp3 tp3.csv           # solo grafica

Con --jobs > 1 hay corridas simultáneas y los tiempos se ven afectados: para medir, usar --jobs 1.
El estado de las partículas se descarta (va a /dev/null); el formateo de la salida sí se mide.
Resultados en build/tiempos_N/ (tiempos_N.csv y tiempos_N.png).
"""
import argparse
import csv
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

RAIZ = Path(__file__).resolve().parent.parent

p = argparse.ArgumentParser()
p.add_argument("--ns", default="100,200,300,400,500,600,700", help="lista de N separada por comas")
p.add_argument("--reps", type=int, default=10, help="realizaciones por N")
p.add_argument("--tf", type=float, default=30.0, help="tiempo simulado (s)")
p.add_argument("--dt", type=float, default=1e-5)
p.add_argument("--every", type=int, default=100, help="cada cuántos pasos se guarda el estado")
p.add_argument("--jobs", type=int, default=1, help="corridas simultáneas (1 para medir tiempos)")
p.add_argument("--bin", default=str(RAIZ / "build" / "tp4"))
p.add_argument("--out", default=str(RAIZ / "build" / "tiempos_N"))
p.add_argument("--tp3", help="CSV del TP3 con columnas N,promedio,desvio (s)")
p.add_argument("--reusar", action="store_true", help="no correr: usar tiempos_N.csv existente")
args = p.parse_args()

ns = [int(x) for x in args.ns.split(",")]
if args.reps < 1 or args.tf <= 0 or args.dt <= 0 or any(n < 1 for n in ns):
    p.error("--reps, --tf, --dt y --ns deben ser positivos")
out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)
csv_path = out / "tiempos_N.csv"


def correr(par):
    n, seed = par
    estado = out / f"run_{n}_s{seed}.txt"
    if estado.is_symlink() or estado.exists():
        estado.unlink()
    estado.symlink_to(os.devnull)
    cmd = [args.bin, str(n), f"{args.tf:g}", str(estado), "--dt", f"{args.dt:g}",
           "--every", str(args.every), "--seed", str(seed)]
    t0 = time.perf_counter()
    r = subprocess.run(cmd, capture_output=True, text=True)
    dt = time.perf_counter() - t0
    for f in (estado, out / f"run_{n}_s{seed}_energia.txt"):
        if f.is_symlink() or f.exists():
            f.unlink()
    if r.returncode != 0:
        sys.exit(f"Falló {' '.join(cmd)}:\n{r.stderr}")
    return n, seed, dt


if not args.reusar:
    if not Path(args.bin).exists():
        sys.exit(f"No existe {args.bin}: compilá primero (cmake -S . -B build && cmake --build build)")
    pares = [(n, s) for n in ns for s in range(1, args.reps + 1)]
    print(f"{len(pares)} corridas (N = {args.ns}, {args.reps} realizaciones, {args.tf:g} s, dt = {args.dt:g}, "
          f"{args.jobs} simultánea{'s' if args.jobs > 1 else ''})", flush=True)
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["N", "semilla", "segundos"])
        with ThreadPoolExecutor(args.jobs) as pool:
            for n, seed, seg in pool.map(correr, pares):
                w.writerow([n, seed, f"{seg:.3f}"])
                f.flush()
                print(f"  N = {n:4d}  semilla {seed:2d}  {seg:8.2f} s", flush=True)

if not csv_path.exists():
    sys.exit(f"Falta {csv_path} (¿corriste sin --reusar?)")
datos = {}
with open(csv_path) as f:
    for fila in csv.DictReader(f):
        datos.setdefault(int(fila["N"]), []).append(float(fila["segundos"]))

Ns = np.array(sorted(datos))
medias = np.array([np.mean(datos[n]) for n in Ns])
desvios = np.array([np.std(datos[n], ddof=1) if len(datos[n]) > 1 else 0.0 for n in Ns])

print(f"\n{'N':>6} {'realizaciones':>13} {'promedio (s)':>13} {'desvío (s)':>11} {'desvío %':>9}")
for n, m, d in zip(Ns, medias, desvios):
    print(f"{n:6d} {len(datos[n]):13d} {m:13.2f} {d:11.2f} {100 * d / m:8.1f}%")

pendiente = None
if len(Ns) >= 2:
    pendiente, ordenada = np.polyfit(np.log(Ns), np.log(medias), 1)
    print(f"\nAjuste log-log: tiempo ~ N^{pendiente:.2f}")

fig, ax = plt.subplots(figsize=(7, 4.8))
ax.errorbar(Ns, medias, yerr=desvios, fmt="o-", capsize=4,
            label="TP4 (paso temporal, Verlet + grilla)" + (f", pendiente {pendiente:.2f}" if pendiente else ""))
if args.tp3:
    t3 = np.loadtxt(args.tp3, delimiter=",", skiprows=1, ndmin=2)
    ax.errorbar(t3[:, 0], t3[:, 1], yerr=t3[:, 2] if t3.shape[1] > 2 else None, fmt="s--", capsize=4,
                label="TP3 (dinámica por eventos)")
ax.set(xlabel="N (cantidad de partículas)", ylabel=f"tiempo de ejecución para {args.tf:g} s simulados (s)",
       xscale="log", yscale="log")
ax.grid(True, which="both", alpha=0.3)
ax.legend()
plt.tight_layout()
png = out / "tiempos_N.png"
plt.savefig(png, dpi=110)
print(f"\nFigura: {png}\nDatos: {csv_path}")
