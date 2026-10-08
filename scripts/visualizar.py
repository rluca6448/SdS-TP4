"""Visor del output de tp4: partículas frescas en azul, usadas en rojo.

Uso:
    python3 scripts/visualizar.py build/output.txt              # animación
    python3 scripts/visualizar.py build/output.txt --every 5    # 1 de cada 5 estados
    python3 scripts/visualizar.py build/output.txt --every 5 --save sim.mp4   # guarda video (o .gif)
    python3 scripts/visualizar.py build/output.txt --png f.png --frame 40   # un cuadro, sin ventana
"""
import argparse
import os

import matplotlib
import numpy as np

R, r = 0.51, 0.0175  # radio del billar y de las partículas (consigna)

p = argparse.ArgumentParser()
p.add_argument("path")
p.add_argument("--x0", type=float, default=0.0175, help="posición de los obstáculos (|x|)")
p.add_argument("--every", type=int, default=1, help="mostrar 1 de cada N estados")
p.add_argument("--png", help="guardar un cuadro en este archivo y salir")
p.add_argument("--frame", type=int, default=-1, help="índice del cuadro para --png")
p.add_argument("--save", help="guardar la animación (.mp4 o .gif, según la extensión) sin abrir ventana")
p.add_argument("--fps", type=int, default=30, help="cuadros por segundo de --save")
args = p.parse_args()
if args.png and args.save:
    p.error("--png y --save no se pueden usar juntos")
if args.save and not args.save.lower().endswith((".mp4", ".gif")):
    p.error("--save solo admite archivos .mp4 o .gif")
for destino in (args.png, args.save):
    if destino and not os.path.isdir(os.path.dirname(destino) or "."):
        p.error(f"la carpeta de '{destino}' no existe")
if args.png or args.save:
    matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.collections import EllipseCollection

# Formato: línea con el tiempo, N líneas "x y vx vy color" (1 fresca, 0 usada), línea en blanco.
times, states = [], []
with open(args.path) as f:
    for block in f.read().strip().split("\n\n"):
        lines = block.strip().split("\n")
        times.append(float(lines[0]))
        states.append(np.array([l.split() for l in lines[1:]], dtype=float))
times, states = times[:: args.every], states[:: args.every]
n = len(states[0])

fig, ax = plt.subplots(figsize=(6, 6))
ax.set_aspect("equal")
ax.set_xlim(-R, R)
ax.set_ylim(-R, R)
ax.add_patch(plt.Circle((0, 0), R, fill=False))
for sx in (-1, 1):
    ax.add_patch(plt.Circle((sx * args.x0, 0), r, color="black"))
parts = EllipseCollection(widths=2 * r, heights=2 * r, angles=0, units="xy",
                          offsets=states[0][:, :2], offset_transform=ax.transData)
ax.add_collection(parts)
title = ax.set_title("")


def draw(i):
    s = states[i]
    parts.set_offsets(s[:, :2])
    parts.set_facecolor(np.where(s[:, 4] == 1, "tab:blue", "tab:red"))
    title.set_text(f"t = {times[i]:.3f} s   usadas: {int((s[:, 4] == 0).sum())}/{n}")


if args.png:
    draw(args.frame)
    fig.savefig(args.png, dpi=110)
else:
    anim = FuncAnimation(fig, draw, frames=len(states), interval=1000 / args.fps)
    if args.save:
        anim.save(args.save, fps=args.fps)
        print(f"Guardado: {args.save} ({len(states)} cuadros)")
    else:
        plt.show()
