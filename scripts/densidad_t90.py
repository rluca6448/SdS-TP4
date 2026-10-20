"""Punto 2.4.a: <t90> y <t100> en función de la densidad.

Obstáculos en contacto (x0 = r), semillas 1..10, dt = 1e-5. Las simulaciones guardan N_usadas(t)
(<salida>_usadas.txt); de ahí salen t90 (F_u >= 0.9) y t100 (F_u = 1) para cada N, que se grafican contra
la densidad rho = N / (pi R^2).

Rango de densidades: de N = 10 a N = 400. Con los obstáculos en contacto el tiempo t90 crece casi linealmente
con N a partir de N ~ 100 (t90 ~ 21 s con N = 50, ~91 s con N = 400) y para N >= 500 (más del 59 % del área
cubierta, casi sólido) no se alcanza ni en 100 s: esas densidades no sirven para este punto. t_max = 150 s
alcanza para N = 400 con margen. Con t_max menor, los puntos que no llegan al umbral se omiten y se informan.

Uso (desde la raíz del repo, con el proyecto compilado):
    python3 scripts/densidad_t90.py                              # N = 10..400, 10 realizaciones, 150 s (~15 min)
    python3 scripts/densidad_t90.py --ns 10,50 --reps 3 --tf 30     # prueba rápida
    python3 scripts/densidad_t90.py --reusar                     # solo vuelve a analizar

Datos en build/resultados/2_4_a/ (t90_t100.csv, resumen.txt); figuras en build/graficos/2_4_a/ (t90_t100_vs_densidad.png y fu_vs_t.png).
En el gráfico, un símbolo hueco indica que no todas las realizaciones llegaron al umbral (el promedio usa
solo las que llegaron); si ninguna llegó, el punto no se dibuja.
"""
import argparse
import csv
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
R, r = 0.51, 0.0175  # radio del billar y de las partículas (consigna)
AREA = np.pi * R**2

p = argparse.ArgumentParser()
p.add_argument("--ns", default="10,20,30,50,75,100,150,200,300,400", help="lista de N separada por comas")
p.add_argument("--reps", type=int, default=10, help="realizaciones por N")
p.add_argument("--tf", type=float, default=150.0, help="t_max (s)")
p.add_argument("--x0", type=float, default=r, help="posición de los obstáculos (por defecto en contacto)")
p.add_argument("--dt", type=float, default=1e-5)
p.add_argument("--every", type=int, default=100, help="cada cuántos pasos se guarda N_usadas (1 ms)")
p.add_argument("--jobs", type=int, default=os.cpu_count() or 1, help="corridas en paralelo")
p.add_argument("--bin", default=str(RAIZ / "build" / "tp4"))
p.add_argument("--out", default=str(RAIZ / "build" / "resultados" / "2_4_a"))
p.add_argument("--graficos", default=str(RAIZ / "build" / "graficos" / "2_4_a"), help="carpeta de las figuras")
p.add_argument("--reusar", action="store_true", help="no correr: usar los archivos que ya existen")
args = p.parse_args()

ns = sorted(int(x) for x in args.ns.split(","))
if args.reps < 1 or args.tf <= 0 or any(n < 1 for n in ns):
    p.error("--reps, --tf y --ns deben ser positivos")
out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)
graf = Path(args.graficos)
graf.mkdir(parents=True, exist_ok=True)
semillas = list(range(1, args.reps + 1))


def base(n, seed):
    return out / f"run_N{n}_s{seed}"


def correr(par):
    n, seed = par
    estado = Path(f"{base(n, seed)}.txt")
    if estado.is_symlink() or estado.exists():
        estado.unlink()
    estado.symlink_to(os.devnull)  # el estado completo no se necesita
    cmd = [args.bin, str(n), f"{args.tf:g}", str(estado), "--dt", f"{args.dt:g}", "--every", str(args.every),
           "--seed", str(seed), "--x0", f"{args.x0:.6f}"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        sys.exit(f"Falló {' '.join(cmd)}:\n{res.stderr}")


pares = [(n, s) for n in ns for s in semillas]
if not args.reusar:
    if not Path(args.bin).exists():
        sys.exit(f"No existe {args.bin}: compilá primero (cmake -S . -B build && cmake --build build)")
    print(f"Corriendo {len(pares)} simulaciones (N = {args.ns}, {args.reps} realizaciones, {args.tf:g} s, "
          f"{args.jobs} en paralelo)...", flush=True)
    # las más pesadas primero, para que no queden al final del reparto
    with ThreadPoolExecutor(args.jobs) as pool:
        list(pool.map(correr, sorted(pares, key=lambda x: -x[0])))

curvas, t90, t100 = {}, {}, {}
for n, seed in pares:
    f = Path(f"{base(n, seed)}_usadas.txt")
    if not f.exists():
        sys.exit(f"Falta {f} (¿corriste sin --reusar?)")
    t, nu = np.loadtxt(f, unpack=True)
    curvas[(n, seed)] = (t, nu / n)
    for dic, minimo in ((t90, int(np.ceil(0.9 * n - 1e-9))), (t100, n)):
        hit = np.nonzero(nu >= minimo)[0]
        dic[(n, seed)] = float(t[hit[0]]) if len(hit) else None

with open(out / "t90_t100.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["N", "densidad_1_m2", "semilla", "t90", "t100", "Fu_tmax"])
    for n, s in pares:
        w.writerow([n, f"{n / AREA:.2f}", s, "" if t90[(n, s)] is None else f"{t90[(n, s)]:.3f}",
                    "" if t100[(n, s)] is None else f"{t100[(n, s)]:.3f}", f"{curvas[(n, s)][1][-1]:.3f}"])


def estadistica(dic, n):
    vals = [dic[(n, s)] for s in semillas if dic[(n, s)] is not None]
    return (len(vals), float(np.mean(vals)) if vals else float("nan"),
            float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0)


lineas = [f"x0 = {args.x0:g} m, t_max = {args.tf:g} s, {args.reps} realizaciones por N, dt = {args.dt:g}",
          f"{'N':>5} {'rho (1/m2)':>11} {'area cub.':>9} {'t90 ok':>7} {'<t90> (s)':>10} {'desv':>6} "
          f"{'t100 ok':>8} {'<t100> (s)':>11} {'desv':>6} {'<Fu(tmax)>':>11}"]
est = {}
for n in ns:
    a90, m90, d90 = estadistica(t90, n)
    a100, m100, d100 = estadistica(t100, n)
    fu = float(np.mean([curvas[(n, s)][1][-1] for s in semillas]))
    est[n] = (a90, m90, d90, a100, m100, d100)
    lineas.append(f"{n:5d} {n / AREA:11.1f} {100 * n * r**2 / R**2:8.1f}% {a90:>4d}/{args.reps:<2d} {m90:10.2f} "
                  f"{d90:6.2f} {a100:>5d}/{args.reps:<2d} {m100:11.2f} {d100:6.2f} {fu:11.3f}")
completos = [n for n in ns if est[n][0] == args.reps]
if completos:
    mejor = min(completos, key=lambda n: est[n][1])
    # N cuyo <t90> no se distingue del mínimo a un desvío (las barras de error se solapan)
    tope = est[mejor][1] + est[mejor][2]
    compat = [n for n in completos if est[n][1] - est[n][2] <= tope]
    lineas.append(f"\nMenor <t90>: N = {mejor} (densidad {mejor / AREA:.0f} 1/m2, {est[mejor][1]:.2f} s).")
    lineas.append("N cuyo <t90> no se distingue del mínimo (barras de error de un desvío que se solapan): "
                  + ", ".join(map(str, compat)))
sin_t90 = [n for n in ns if est[n][0] < args.reps]
if sin_t90:
    lineas.append("Hay realizaciones que no llegaron a t90 antes de t_max para N = "
                  + ", ".join(f"{n} ({est[n][0]}/{args.reps})" for n in sin_t90))
texto = "\n".join(lineas)
print("\n" + texto)
(out / "resumen.txt").write_text(texto + "\n")

# <t90> y <t100> vs densidad (eje logarítmico). Símbolo hueco: no todas las realizaciones llegaron.
fig, ax = plt.subplots(figsize=(7.8, 5))
for idx, color, nombre, marca in ((1, "tab:blue", "t_{90}", "o"), (4, "tab:red", "t_{100}", "s")):
    ok = [n for n in ns if est[n][idx - 1] > 0]
    x = [n / AREA for n in ok]
    ax.errorbar(x, [est[n][idx] for n in ok], yerr=[est[n][idx + 1] for n in ok], fmt="-", color=color,
                capsize=3, lw=1.2, label=rf"$\langle {nombre}\rangle$")
    llenos = [n for n in ok if est[n][idx - 1] == args.reps]
    huecos = [n for n in ok if est[n][idx - 1] < args.reps]
    ax.plot([n / AREA for n in llenos], [est[n][idx] for n in llenos], marca, color=color)
    ax.plot([n / AREA for n in huecos], [est[n][idx] for n in huecos], marca, color=color, mfc="white")
ax.set(xscale="log", xlabel=r"$\rho$ (partículas/m$^2$)", ylabel=r"$\langle t\rangle$ (s)")
ax.legend(fontsize=9, loc="upper left")
marcas = [m for m in (10, 20, 50, 100, 200, 500) if min(ns) / AREA / 1.5 <= m <= max(ns) / AREA * 1.5]
ax.set_xticks(marcas)
ax.set_xticklabels([str(m) for m in marcas])
ax.minorticks_off()
ax.grid(True, which="major", alpha=0.3)
plt.tight_layout()
plt.savefig(graf / "t90_t100_vs_densidad.png", dpi=110)
plt.close(fig)

# F_u(t) promedio para cada N
fig, ax = plt.subplots(figsize=(7.8, 5))
colores = plt.cm.viridis(np.linspace(0, 0.95, len(ns)))
for n, c in zip(ns, colores):
    t = curvas[(n, semillas[0])][0]
    ax.plot(t, np.mean([curvas[(n, s)][1] for s in semillas], axis=0), color=c, label=f"{n / AREA:.0f}")
ax.axhline(0.9, color="gray", ls=":", lw=1)
ax.set(xlabel="t (s)", ylabel="fracción de usadas", ylim=(0, 1.02), xlim=(0, args.tf))
ax.legend(title=r"$\rho$ (partículas/m$^2$)", fontsize=7, title_fontsize=8, ncol=2)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(graf / "fu_vs_t.png", dpi=110)
print(f"\nDatos en {out}\nFiguras en {graf}")
