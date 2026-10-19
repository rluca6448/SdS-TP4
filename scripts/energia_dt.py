"""Punto 2.1.a: conservación de la energía en función de dt (sistema sin obstáculos).

Corre build/tp4 para cada dt (y semilla), lee <salida>_energia.txt y calcula el observable
max_t |E(t) - E0| / E0. Guarda E(t) por dt y el observable vs dt.

Uso (desde la raíz del repo, con el proyecto compilado):
    python3 scripts/energia_dt.py                       # 2 s, N = 300, 1 semilla
    python3 scripts/energia_dt.py --tf 30 --dts 1e-4,5e-5,2e-5,1e-5 --seeds 1,2
    python3 scripts/energia_dt.py --reusar              # solo analiza corridas ya hechas

Datos en build/energia_dt/ (o --out); figuras en build/graficos/2_1_a/ (energia_dt.png y energia_total_vs_t.png). El estado de las partículas se descarta
(va a /dev/null), solo se guarda la energía.
"""
import argparse
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

RAIZ = Path(__file__).resolve().parent.parent
CHOQUE = 3.5e-3  # duración típica de un choque entre dos partículas (s)

p = argparse.ArgumentParser()
p.add_argument("--tf", type=float, default=2.0, help="tiempo simulado (s)")
p.add_argument("--n", type=int, default=300, help="cantidad de partículas")
p.add_argument("--dts", default="1e-3,5e-4,2e-4,1e-4,5e-5,2e-5,1e-5", help="lista de dt separada por comas")
p.add_argument("--seeds", default="1", help="lista de semillas separada por comas")
p.add_argument("--muestreo", type=float, default=1e-3, help="cada cuántos segundos se guarda la energía")
p.add_argument("--bin", default=str(RAIZ / "build" / "tp4"), help="ejecutable")
p.add_argument("--out", default=str(RAIZ / "build" / "energia_dt"), help="carpeta de salida")
p.add_argument("--jobs", type=int, default=os.cpu_count() or 1, help="corridas en paralelo")
p.add_argument("--graficos", default=str(RAIZ / "build" / "graficos" / "2_1_a"), help="carpeta de las figuras")
p.add_argument("--sufijo", default="", help="se agrega al nombre de las figuras (por ejemplo _zoom)")
p.add_argument("--reusar", action="store_true", help="no correr: usar los archivos que ya existen")
args = p.parse_args()

try:
    dts = [float(x) for x in args.dts.split(",")]
    seeds = [int(x) for x in args.seeds.split(",")]
except ValueError:
    p.error("--dts y --seeds deben ser listas de números separados por comas")
if any(dt <= 0 for dt in dts) or args.tf <= 0 or args.n < 1:
    p.error("dt, --tf y --n deben ser positivos")
out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)
graf = Path(args.graficos)
graf.mkdir(parents=True, exist_ok=True)


def archivo(dt, seed):
    return out / f"run_{dt:g}_s{seed}.txt"


def energia(dt, seed):
    return out / f"run_{dt:g}_s{seed}_energia.txt"


def correr(par):
    dt, seed = par
    estado = archivo(dt, seed)
    if estado.is_symlink() or estado.exists():
        estado.unlink()
    estado.symlink_to(os.devnull)  # el estado de las partículas no se necesita
    cada = max(1, round(args.muestreo / dt))
    cmd = [args.bin, str(args.n), str(args.tf), str(estado), "--dt", f"{dt:g}", "--every", str(cada),
           "--seed", str(seed), "--sin-obstaculos"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"Falló {' '.join(cmd)}:\n{r.stderr}")


pares = [(dt, s) for dt in dts for s in seeds]
if not args.reusar:
    if not Path(args.bin).exists():
        sys.exit(f"No existe {args.bin}: compilá primero (cmake -S . -B build && cmake --build build)")
    print(f"Corriendo {len(pares)} simulaciones (N = {args.n}, {args.tf:g} s, {args.jobs} en paralelo)...")
    with ThreadPoolExecutor(args.jobs) as pool:
        list(pool.map(correr, pares))

datos = {}
for dt, seed in pares:
    f = energia(dt, seed)
    if not f.exists():
        sys.exit(f"Falta {f} (¿corriste sin --reusar?)")
    datos[(dt, seed)] = np.loadtxt(f, unpack=True)

print(f"\nE0 = {datos[pares[0]][1][0]:.4f} J, N = {args.n}, tiempo simulado = {args.tf:g} s")
print(f"{'dt (s)':>8} {'pasos/choque':>12}" + "".join(f"{'max semilla ' + str(s):>18}" for s in seeds)
      + "".join(f"{'final semilla ' + str(s):>19}" for s in seeds))
maximos = {}
for dt in sorted(dts, reverse=True):
    fila, finales = [], []
    for s in seeds:
        t, E = datos[(dt, s)]
        dev = (E - E[0]) / E[0]
        maximos[(dt, s)] = np.abs(dev).max()
        fila.append(maximos[(dt, s)])
        finales.append(dev[-1])
    print(f"{dt:8.0e} {CHOQUE / dt:12.0f}" + "".join(f"{m:18.3e}" for m in fila) + "".join(f"{x:19.3e}" for x in finales))

fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
for dt in sorted(dts, reverse=True):
    t, E = datos[(dt, seeds[0])]
    ax[0].semilogy(t, np.maximum(np.abs(E - E[0]) / E[0], 1e-12), lw=0.9, label=f"{dt:g}")
ax[0].set(xlabel="t (s)", ylabel=r"$|E(t)-E_0|\,/\,E_0$")
ax[0].legend(title="dt (s)", fontsize=7, title_fontsize=8, ncol=2)
ax[0].grid(True, alpha=0.3)
for s, marcador in zip(seeds, "osd^v"):
    xs = sorted(dts)
    ax[1].loglog(xs, [maximos[(dt, s)] for dt in xs], marcador + "-", label=f"{s}")
ax[1].set(xlabel="dt (s)", ylabel=r"$\max\,|E-E_0|\,/\,E_0$")
ax[1].legend(title="semilla")
ax[1].grid(True, which="both", alpha=0.3)
plt.tight_layout()
png = graf / f"energia_dt{args.sufijo}.png"
plt.savefig(png, dpi=110)
plt.close(fig)

# Energía total E(t) (no solo su desviación): a la izquierda los dt grandes, a la derecha un zoom con los chicos.
# Los dt para los que la energía diverge (más de 2 veces E0) no se dibujan.
E0 = datos[(dts[0], seeds[0])][1][0]
fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
divergen = [dt for dt in dts if maximos[(dt, seeds[0])] > 1]
for dt in sorted((d for d in dts if d not in divergen), reverse=True):
    t, E = datos[(dt, seeds[0])]
    if dt >= 1e-4:
        ax[0].plot(t, E, lw=0.9, label=f"{dt:g}")
    if dt <= 1e-4:
        ax[1].plot(t, E, lw=0.9, label=f"{dt:g}")
for a in ax:
    a.axhline(E0, color="k", ls=":", lw=1)
    a.set(xlabel="t (s)", ylabel="E (J)")
    a.legend(title="dt (s)", fontsize=8, title_fontsize=8)
    a.grid(True, alpha=0.3)
ax[1].set_ylim(E0 * 0.995, E0 * 1.005)
if divergen:
    print("En E(t) no se dibuja (la energía diverge): dt = " + ", ".join(f"{d:g}" for d in sorted(divergen, reverse=True)))
plt.tight_layout()
png_total = graf / f"energia_total_vs_t{args.sufijo}.png"
plt.savefig(png_total, dpi=110)
print(f"\nFigura de la energía total: {png_total}")
print(f"\nFigura: {png}")
