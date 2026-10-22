"""Sistema 1: oscilador puntual amortiguado, comparación de esquemas de integración (punto 1).

Integra m r'' = -k r - gamma r' con Euler predictor-corrector, Verlet original, Velocity Verlet y Beeman, y
compara con la solución analítica. Guarda la trayectoria para dt = 1e-3 y el ECM en función de dt.

Uso:
    python3 scripts/oscilador_amortiguado.py
    python3 scripts/oscilador_amortiguado.py --verlet-v centrada   # velocidad centrada de la teórica

--verlet-v elige cómo se estima la velocidad en Verlet original (la fuerza depende de v):
  atras     v = (r_new - r)/dt + a*dt/2           (versión original del grupo; error de 2.º orden)
  centrada  v = (r_new - r_before)/(2*dt)         (fórmula de la teórica; llega con un paso de retraso)
Figuras en build/graficos/sistema1/ (trayectorias.png y ecm_vs_dt.png).
"""
import argparse
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

RAIZ = Path(__file__).resolve().parent.parent
m, k, g, tf, A = 70.0, 1e4, 100.0, 5.0, 1.0
r0, v0 = 1.0, -A * g / (2 * m)
w = np.sqrt(k / m - g**2 / (4 * m**2))

p = argparse.ArgumentParser()
p.add_argument("--dt", type=float, default=1e-3, help="dt de la figura de trayectorias")
p.add_argument("--verlet-v", choices=["atras", "centrada"], default="atras")
p.add_argument("--out", default=str(RAIZ / "build" / "graficos" / "sistema1"), help="carpeta de las figuras")
args = p.parse_args()
out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)


def analitica(t):
    return A * np.exp(-(g / (2 * m)) * t) * np.cos(w * t)


def acc(r, v):
    return (-k * r - g * v) / m


def tiempos(n, dt):
    return np.arange(n + 1) * dt


def euler_pc(dt):
    n = int(round(tf / dt))
    r, v = r0, v0
    a = acc(r, v)
    rs = [r]
    for _ in range(n):
        a_new = acc(r + v * dt, v + a * dt)   # predicción de r y v, evaluación
        v = v + a_new * dt                    # corrección
        r = r + v * dt
        a = acc(r, v)
        rs.append(r)
    return tiempos(n, dt), np.array(rs)


def verlet_original(dt):
    n = int(round(tf / dt))
    r, v = r0, v0
    a = acc(r, v)
    r_before = r - v * dt + 0.5 * a * dt**2   # posición en el paso -1 (Euler hacia atrás)
    rs = [r]
    for _ in range(n):
        r_new = 2 * r - r_before + a * dt**2
        if args.verlet_v == "atras":
            v_new = (r_new - r) / dt + 0.5 * a * dt
        else:
            v_new = (r_new - r_before) / (2 * dt)
        a = acc(r_new, v_new)
        r_before, r = r, r_new
        rs.append(r)
    return tiempos(n, dt), np.array(rs)


def velocity_verlet(dt):
    n = int(round(tf / dt))
    r, v = r0, v0
    a = acc(r, v)
    rs = [r]
    for _ in range(n):
        r_new = r + v * dt + 0.5 * a * dt**2
        a_new = acc(r_new, v + a * dt)        # velocidad predicha
        v = v + 0.5 * (a + a_new) * dt
        r, a = r_new, a_new
        rs.append(r)
    return tiempos(n, dt), np.array(rs)


def beeman(dt):
    n = int(round(tf / dt))
    r, v = r0, v0
    a = acc(r, v)
    a_before = acc(r - v * dt + 0.5 * a * dt**2, v - a * dt)   # aceleración en el paso -1
    rs = [r]
    for _ in range(n):
        r_new = r + v * dt + (2 / 3) * a * dt**2 - (1 / 6) * a_before * dt**2
        a_new = acc(r_new, v + 1.5 * a * dt - 0.5 * a_before * dt)   # velocidad predicha
        v = v + (1 / 3) * a_new * dt + (5 / 6) * a * dt - (1 / 6) * a_before * dt
        a_before, r, a = a, r_new, a_new
        rs.append(r)
    return tiempos(n, dt), np.array(rs)


metodos = {"Euler predictor-corrector": (euler_pc, "r--"), "Verlet original": (verlet_original, "b-."),
           "Velocity Verlet": (velocity_verlet, "g:"), "Beeman": (beeman, "m-")}


def ecm(f, dt):
    t, r = f(dt)
    return np.mean((r - analitica(t)) ** 2)


# Trayectorias
plt.figure(figsize=(8, 4))
t_a = np.linspace(0, tf, 2000)
plt.plot(t_a, analitica(t_a), "k-", label="Analítica")
print(f"dt = {args.dt:g} s   (Verlet original con velocidad '{args.verlet_v}')")
for nombre, (f, estilo) in metodos.items():
    t, r = f(args.dt)
    plt.plot(t, r, estilo, label=nombre)
    print(f"  ECM {nombre:<26} {np.mean((r - analitica(t)) ** 2):.3e}")
plt.xlabel("t (s)")
plt.ylabel("r (m)")
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(out / "trayectorias.png", dpi=110)
plt.close()

# ECM vs dt
dts = np.logspace(-5, -2, 8)
resultados = {nombre: [ecm(f, d) for d in dts] for nombre, (f, _) in metodos.items()}
print(f"\n{'dt':>9}" + "".join(f"{n[:22]:>26}" for n in metodos))
for i, d in enumerate(dts):
    print(f"{d:9.2e}" + "".join(f"{resultados[n][i]:26.3e}" for n in metodos))
plt.figure(figsize=(6.5, 4.2))
for (nombre, (_, _)), marcador in zip(metodos.items(), "osd^"):
    plt.loglog(dts, resultados[nombre], marcador + "-", label=nombre)
plt.xlabel("dt (s)")
plt.ylabel(r"ECM (m$^2$)")
plt.legend()
plt.grid(True, which="both", alpha=0.3)
plt.tight_layout()
plt.savefig(out / "ecm_vs_dt.png", dpi=110)
print(f"\nFiguras en {out}")
