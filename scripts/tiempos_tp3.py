"""Punto 2.1.b: tiempos de ejecución del TP3 (punto 1.1: mesa vacía, tf = 30 s) en esta computadora.

Corre el ejecutable del TP3 tal cual está compilado, sin modificarlo, midiendo el tiempo de pared
de cada realización igual que en tiempos_N.py (el estado va a /dev/null). Genera un CSV
N,promedio,desvio (s) que se pasa a:  python3 scripts/tiempos_N.py --reusar --tp3 <csv>

Uso:
    python3 scripts/tiempos_tp3.py --exe /ruta/al/TP3/build/sds_tp3
    python3 scripts/tiempos_tp3.py --exe ... --ns 100,200,300 --reps 3 --tf 5     # prueba rápida

Se ejecuta con un directorio de trabajo propio (build/tiempos_tp3/), así el TP3 no escribe en su repo.
Si un N no se puede ejecutar (por ejemplo, no entran las partículas), se informa y se omiten los N mayores.
"""
import argparse
import csv
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent

p = argparse.ArgumentParser()
p.add_argument("--exe", required=True, help="ejecutable del TP3 (sds_tp3)")
p.add_argument("--ns", default="100,200,300,400,500,600,700", help="lista de N separada por comas")
p.add_argument("--reps", type=int, default=10, help="realizaciones por N")
p.add_argument("--tf", type=int, default=30, help="tiempo simulado (s); el TP3 lo recibe como entero")
p.add_argument("--out", default=str(RAIZ / "build" / "tiempos_tp3"))
args = p.parse_args()

ns = [int(x) for x in args.ns.split(",")]
if args.reps < 1 or args.tf < 0 or any(n < 1 for n in ns):
    p.error("--reps, --tf y --ns deben ser positivos")
exe = Path(args.exe).resolve()
if not exe.exists():
    sys.exit(f"No existe {exe}")

out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)
mesa_vacia = out / "mesa_vacia.txt"
mesa_vacia.write_text("")  # un archivo vacío es una mesa sin obstáculos
estado = out / "states.txt"


def correr(n):
    if estado.is_symlink() or estado.exists():
        estado.unlink()
    estado.symlink_to(os.devnull)
    t0 = time.perf_counter()
    r = subprocess.run([str(exe), str(args.tf), str(n), mesa_vacia.name, estado.name],
                       cwd=out, capture_output=True, text=True)
    seg = time.perf_counter() - t0
    return r.returncode, seg, (r.stderr or r.stdout).strip().splitlines()


filas, crudos = [], []
for n in ns:
    tiempos = []
    for rep in range(1, args.reps + 1):
        codigo, seg, msg = correr(n)
        if codigo != 0:
            print(f"N = {n}: el TP3 falló ({msg[-1] if msg else 'sin mensaje'}). Se omiten los N mayores.")
            break
        tiempos.append(seg)
        crudos.append((n, rep, seg))
        print(f"  N = {n:4d}  realización {rep:2d}  {seg:8.2f} s", flush=True)
    else:
        filas.append((n, float(np.mean(tiempos)),
                      float(np.std(tiempos, ddof=1)) if len(tiempos) > 1 else 0.0))
        continue
    break

if estado.is_symlink():
    estado.unlink()
if not filas:
    sys.exit("No se obtuvo ningún resultado")

csv_path = out / "tp3_tiempos.csv"
with open(csv_path, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["N", "promedio", "desvio"])
    w.writerows((n, f"{m:.3f}", f"{d:.3f}") for n, m, d in filas)
with open(out / "tp3_tiempos_crudos.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["N", "realizacion", "segundos"])
    w.writerows((n, r, f"{s:.3f}") for n, r, s in crudos)

print(f"\n{'N':>6} {'promedio (s)':>13} {'desvío (s)':>11}")
for n, m, d in filas:
    print(f"{n:6d} {m:13.2f} {d:11.2f}")
print(f"\nCSV: {csv_path}")
