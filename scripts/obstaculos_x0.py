"""Punto 2.2: posición de los obstáculos y tiempo t90.

Barre la posición x0 de los dos obstáculos (simétricos en (-x0, 0) y (+x0, 0)) desde x0 = r
(en contacto entre sí) hasta x0 = R - r (en contacto con la pared). Para cada x0 corre varias
realizaciones (semillas), calcula F_u(t) = N_usadas(t)/N a partir de <salida>_usadas.txt y t90 (el
primer instante con F_u >= 0.9). Grafica F_u(t) para algunos x0 típicos y <t90> en función de x0.

Uso (desde la raíz del repo, con el proyecto compilado):
    python3 scripts/obstaculos_x0.py                          # N = 100, 100 s, 11 valores de x0, 5 realizaciones
    python3 scripts/obstaculos_x0.py --n 20                   # comparación con densidad menor
    python3 scripts/obstaculos_x0.py --reusar --n 100         # solo vuelve a analizar

Datos en build/resultados/2_2_N<N>/ (t90.csv, resumen.txt); figuras en build/graficos/2_2/N<N>/ (fu_vs_t.png y t90_vs_x0.png).
Si alguna realización no llega a F_u = 0.9 antes de t_max se informa, y se grafica como una cruz roja.
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

p = argparse.ArgumentParser()
p.add_argument("--n", type=int, default=100, help="cantidad de partículas")
p.add_argument("--tf", type=float, default=100.0, help="t_max (s)")
p.add_argument("--puntos", type=int, default=11, help="cantidad de valores de x0 entre r y R - r")
p.add_argument("--x0s", help="lista de x0 separada por comas (reemplaza a --puntos)")
p.add_argument("--reps", type=int, default=5, help="realizaciones por x0")
p.add_argument("--umbral", type=float, default=0.9, help="fracción de usadas para t (0.9 = t90)")
p.add_argument("--every", type=int, default=100, help="cada cuántos pasos se guarda N_usadas (1 ms)")
p.add_argument("--dt", type=float, default=1e-5)
p.add_argument("--jobs", type=int, default=os.cpu_count() or 1, help="corridas en paralelo")
p.add_argument("--bin", default=str(RAIZ / "build" / "tp4"))
p.add_argument("--out", help="carpeta de salida (por defecto build/resultados/2_2_N<N>)")
p.add_argument("--graficos", help="carpeta de las figuras (por defecto build/graficos/2_2/N<N>)")
p.add_argument("--reusar", action="store_true", help="no correr: usar los archivos que ya existen")
args = p.parse_args()

x0s = ([float(x) for x in args.x0s.split(",")] if args.x0s
       else list(np.linspace(r, R - r, args.puntos)))
if args.reps < 1 or args.tf <= 0 or args.n < 1 or not 0 < args.umbral <= 1:
    p.error("--reps, --tf y --n deben ser positivos, y --umbral debe estar en (0, 1]")
if any(x < r - 1e-9 or x > R - r + 1e-9 for x in x0s):
    p.error(f"x0 debe estar entre {r} y {R - r}")
out = Path(args.out) if args.out else RAIZ / "build" / "resultados" / f"2_2_N{args.n}"
out.mkdir(parents=True, exist_ok=True)
graf = Path(args.graficos) if args.graficos else RAIZ / "build" / "graficos" / "2_2" / f"N{args.n}"
graf.mkdir(parents=True, exist_ok=True)
semillas = list(range(1, args.reps + 1))


def base(x0, seed):
    return out / f"run_x{x0:.4f}_s{seed}"


def correr(par):
    x0, seed = par
    estado = Path(f"{base(x0, seed)}.txt")
    if estado.is_symlink() or estado.exists():
        estado.unlink()
    estado.symlink_to(os.devnull)  # el estado completo no se necesita para F_u(t)
    cmd = [args.bin, str(args.n), f"{args.tf:g}", str(estado), "--dt", f"{args.dt:g}", "--every", str(args.every),
           "--seed", str(seed), "--x0", f"{x0:.6f}"]
    r_ = subprocess.run(cmd, capture_output=True, text=True)
    if r_.returncode != 0:
        sys.exit(f"Falló {' '.join(cmd)}:\n{r_.stderr}")


pares = [(x0, s) for x0 in x0s for s in semillas]
if not args.reusar:
    if not Path(args.bin).exists():
        sys.exit(f"No existe {args.bin}: compilá primero (cmake -S . -B build && cmake --build build)")
    print(f"Corriendo {len(pares)} simulaciones (N = {args.n}, {args.tf:g} s, {len(x0s)} valores de x0, "
          f"{args.reps} realizaciones, {args.jobs} en paralelo)...", flush=True)
    with ThreadPoolExecutor(args.jobs) as pool:
        list(pool.map(correr, pares))

# --- análisis ---
curvas, t90 = {}, {}
for x0, seed in pares:
    f = Path(f"{base(x0, seed)}_usadas.txt")
    if not f.exists():
        sys.exit(f"Falta {f} (¿corriste sin --reusar?)")
    t, nu = np.loadtxt(f, unpack=True)
    fu = nu / args.n
    curvas[(x0, seed)] = (t, fu)
    alcanzo = np.nonzero(fu >= args.umbral - 1e-12)[0]
    t90[(x0, seed)] = float(t[alcanzo[0]]) if len(alcanzo) else None

etiqueta = f"t{int(round(args.umbral * 100))}"
with open(out / "t90.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["x0", "semilla", etiqueta, "Fu_tmax"])
    for x0, seed in pares:
        v = t90[(x0, seed)]
        w.writerow([f"{x0:.4f}", seed, "" if v is None else f"{v:.3f}", f"{curvas[(x0, seed)][1][-1]:.3f}"])

media, desvio, alcanzaron, fu_final = {}, {}, {}, {}
for x0 in x0s:
    vals = [t90[(x0, s)] for s in semillas if t90[(x0, s)] is not None]
    alcanzaron[x0] = len(vals)
    media[x0] = float(np.mean(vals)) if vals else float("nan")
    desvio[x0] = float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0
    fu_final[x0] = float(np.mean([curvas[(x0, s)][1][-1] for s in semillas]))

lineas = [f"N = {args.n}, t_max = {args.tf:g} s, {args.reps} realizaciones por x0, dt = {args.dt:g}",
          f"{'x0 (m)':>8} {'alcanzaron':>11} {'<' + etiqueta + '> (s)':>11} {'desvío (s)':>11} {'<Fu(tmax)>':>11}"]
for x0 in x0s:
    marca = "" if alcanzaron[x0] == args.reps else "  <- no todas alcanzan F_u = " + f"{args.umbral:g}"
    lineas.append(f"{x0:8.4f} {alcanzaron[x0]:>8d}/{args.reps:<2d} {media[x0]:11.2f} {desvio[x0]:11.2f} "
                  f"{fu_final[x0]:11.3f}{marca}")
validos = [x0 for x0 in x0s if alcanzaron[x0] > 0]
if validos:
    mejor = min(validos, key=lambda x: media[x])
    lineas.append(f"\nMenor <{etiqueta}>: x0 = {mejor:.4f} m ({media[mejor]:.2f} s)")
texto = "\n".join(lineas)
print("\n" + texto)
(out / "resumen.txt").write_text(texto + "\n")

# F_u(t) para algunos x0 típicos: el menor, el mejor, uno intermedio y el mayor
tipicos = sorted({x0s[0], x0s[len(x0s) // 2], x0s[-1]} | ({mejor} if validos else set()))
fig, ax = plt.subplots(figsize=(7.5, 4.8))
for x0 in tipicos:
    t = curvas[(x0, semillas[0])][0]
    fus = np.array([curvas[(x0, s)][1] for s in semillas])
    m, d = fus.mean(axis=0), fus.std(axis=0, ddof=1) if len(semillas) > 1 else np.zeros_like(fus[0])
    linea, = ax.plot(t, m, label=f"{x0:.2f}")
    ax.fill_between(t, np.clip(m - d, 0, 1), np.clip(m + d, 0, 1), alpha=0.2, color=linea.get_color())
ax.axhline(args.umbral, color="gray", ls=":", lw=1)
ax.set(xlabel="t (s)", ylabel=r"$F_u$", ylim=(0, 1.02), xlim=(0, args.tf))
ax.legend(title=r"$x_0$ (m)")
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(graf / "fu_vs_t.png", dpi=110)
plt.close(fig)

# <t90> vs x0, con los puntos individuales y las realizaciones que no llegaron al umbral
fig, ax = plt.subplots(figsize=(7.5, 4.8))
for x0 in x0s:
    for s in semillas:
        v = t90[(x0, s)]
        if v is None:
            ax.plot(x0, args.tf, "x", color="red", ms=7)
        else:
            ax.plot(x0, v, ".", color="gray", alpha=0.6)
ok = [x0 for x0 in x0s if alcanzaron[x0] > 0]
ax.errorbar(ok, [media[x] for x in ok], yerr=[desvio[x] for x in ok], fmt="o-", capsize=4,
            label=rf"$\langle t_{{{etiqueta[1:]}}}\rangle$")
ax.plot([], [], "x", color="red", label="no llegan")
ax.plot([], [], ".", color="gray", label="realizaciones")
ax.set(xlabel=r"$x_0$ (m)", ylabel=rf"$\langle t_{{{etiqueta[1:]}}}\rangle$ (s)")
ax.legend(fontsize=9)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(graf / "t90_vs_x0.png", dpi=110)
print(f"\nDatos en {out}\nFiguras en {graf}")
