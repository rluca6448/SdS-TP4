"""Punto 2.3: bolsas de velocidades y ajuste Maxwell-Boltzmann.

Flujo:
  1. Corre la simulación (o reusa los archivos con --reusar).
  2. Lee TODOS los frames de cada realización para calcular <v>(t).
  3. Grafica <v>(t) promediada sobre realizaciones para encontrar
     visualmente cuándo se estaciona.
  4. Detecta automáticamente el tiempo de estacionario (o lo toma de --t-estacionario).
  5. Usa sólo los frames del régimen estacionario para el ajuste de
     la distribución de Maxwell-Boltzmann.
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

ROOT = Path(__file__).resolve().parent.parent
MASS = 0.025


def floats(text, flag):
    try:
        values = sorted({float(value) for value in text.split(",")})
    except ValueError:
        parser.error(f"{flag} debe ser una lista de números separada por comas")
    if not values or any(value < 0 for value in values):
        parser.error(f"{flag} debe contener valores no negativos")
    return values


parser = argparse.ArgumentParser()
parser.add_argument("--n", type=int, default=100)
parser.add_argument("--tf", type=float, default=60.0,
                    help="Tiempo final de simulación (default: 60 s, más largo para asegurar estacionario)")
parser.add_argument("--reps", type=int, default=100)
parser.add_argument("--dt", type=float, default=1e-5)
parser.add_argument("--muestreo", type=float, default=0.1,
                    help="Intervalo de muestreo para guardar frames (default: 0.1 s)")
parser.add_argument("--tiempos", default=None,
                    help="Tiempos específicos para histogramas de f(v). Si no se da, se eligen automáticamente")
parser.add_argument("--t-estacionario", type=float, default=None,
                    help="Tiempo a partir del cual considerar estacionario. Si no se da, se detecta automáticamente")
parser.add_argument("--umbral-estacionario", type=float, default=0.02,
                    help="Umbral relativo para detectar estacionario: |d<v>/dt| / <v> < umbral (default: 0.02)")
parser.add_argument("--bins", type=int, default=80)
parser.add_argument("--jobs", type=int, default=os.cpu_count() or 1)
parser.add_argument("--bin", default=str(ROOT / "build" / "tp4"))
parser.add_argument("--out")
parser.add_argument("--reusar", action="store_true")
args = parser.parse_args()

if args.n < 1 or args.reps < 1 or args.tf <= 0 or args.dt <= 0 or args.muestreo <= 0:
    parser.error("--n, --reps, --tf, --dt y --muestreo deben ser positivos")
if args.bins < 5:
    parser.error("--bins debe ser al menos 5")

out = Path(args.out) if args.out else ROOT / "build" / "resultados" / f"2_3_N{args.n}"
runs = out / "runs"
runs.mkdir(parents=True, exist_ok=True)
seeds = list(range(1, args.reps + 1))
every = max(1, round(args.muestreo / args.dt))
saved_step = every * args.dt


def state_file(seed):
    return runs / f"run_s{seed}.txt"


def run(seed):
    command = [args.bin, str(args.n), f"{args.tf:g}", str(state_file(seed)), "--dt", f"{args.dt:g}",
               "--every", str(every), "--seed", str(seed), "--sin-obstaculos"]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"Falló {' '.join(command)}:\n{result.stderr}")


# ─── Paso 1: correr simulaciones ───────────────────────────────────────────────
if not args.reusar:
    if not Path(args.bin).exists():
        sys.exit(f"No existe {args.bin}: compilá primero")
    print(f"Corriendo {args.reps} realizaciones de N={args.n}; un estado cada {saved_step:g} s, "
          f"hasta t={args.tf:g} s...", flush=True)
    try:
        with ThreadPoolExecutor(args.jobs) as pool:
            list(pool.map(run, seeds))
    except RuntimeError as error:
        sys.exit(error)


# ─── Paso 2: leer TODOS los frames y calcular <v>(t) ───────────────────────────
def read_all_frames(path):
    """Lee todos los frames y devuelve {t: speeds_array}."""
    frames = {}
    with open(path, encoding="utf-8") as data:
        while line := data.readline():
            if not line.strip():
                continue
            time = float(line)
            speeds = np.empty(args.n)
            for index in range(args.n):
                fields = data.readline().split()
                if len(fields) < 4:
                    raise ValueError(f"Estado incompleto en {path}, t={time:g}")
                speeds[index] = np.hypot(float(fields[2]), float(fields[3]))
            data.readline()  # línea en blanco
            frames[time] = speeds
    return frames


print("Leyendo todos los frames de cada realización...", flush=True)
# all_frames[seed_index] = {t: speeds_array}
all_frames = []
for seed in seeds:
    path = state_file(seed)
    if not path.exists():
        sys.exit(f"Falta {path}; ejecutá sin --reusar")
    all_frames.append(read_all_frames(path))

# Construir la lista de tiempos comunes a todas las realizaciones
common_times = sorted(set.intersection(*[set(frames.keys()) for frames in all_frames]))
print(f"  {len(common_times)} frames en común, desde t={common_times[0]:g} hasta t={common_times[-1]:g} s")

# <v>(t) promediada sobre realizaciones
mean_speed_per_run = np.array([
    [np.mean(frames[t]) for t in common_times]
    for frames in all_frames
])  # shape: (reps, n_frames)
mean_speed = np.mean(mean_speed_per_run, axis=0)
std_speed = np.std(mean_speed_per_run, axis=0, ddof=1) / np.sqrt(args.reps) if args.reps > 1 else np.zeros(len(common_times))
times_array = np.array(common_times)


# ─── Paso 3: detectar el tiempo de estacionario ────────────────────────────────
def detect_stationary_time(times, values, threshold):
    """Detecta cuándo la señal se estaciona.

    Calcula la derivada suavizada de values y busca el primer instante
    a partir del cual la variación relativa se mantiene por debajo del umbral.
    """
    if len(times) < 20:
        return times[len(times) // 2]

    # Suavizar con media móvil (ventana del 5% de los datos, mínimo 5 puntos)
    window = max(5, len(times) // 20)
    smoothed = np.convolve(values, np.ones(window) / window, mode="same")

    # Derivada numérica del suavizado
    dt = np.diff(times)
    dv = np.diff(smoothed)
    derivative = dv / dt

    # Variación relativa: |dv/dt| * T_total / <v>_final
    v_ref = np.mean(smoothed[-window:])
    if v_ref < 1e-12:
        return times[0]
    # Normalizar por el valor de referencia y el intervalo de muestreo típico
    relative_change = np.abs(derivative) / v_ref

    # Buscar el primer punto donde la variación relativa se mantiene baja
    # por al menos el 20% de los puntos restantes
    min_sustained = max(10, len(derivative) // 5)
    for i in range(len(derivative)):
        remaining = relative_change[i:]
        if len(remaining) < min_sustained:
            break
        if np.all(remaining[:min_sustained] < threshold):
            return times[i]

    # Fallback: usar el último tercio
    return times[len(times) // 3]


if args.t_estacionario is not None:
    t_stationary = args.t_estacionario
    print(f"Usando tiempo estacionario provisto: t >= {t_stationary:g} s")
else:
    t_stationary = detect_stationary_time(times_array, mean_speed, args.umbral_estacionario)
    print(f"Tiempo estacionario detectado automáticamente: t >= {t_stationary:g} s")


# ─── Paso 4: gráfico de <v>(t) ─────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(times_array, mean_speed, "-", lw=1.2, color="tab:blue", label=r"$\langle v \rangle(t)$")
ax.axvline(t_stationary, color="tab:red", ls="--", lw=1.5,
           label=f"inicio estacionario: t = {t_stationary:g} s")
ax.set(xlabel="t (s)", ylabel=r"$\langle v \rangle$ (m/s)",
       title=f"Velocidad promedio vs tiempo — N={args.n}, {args.reps} realizaciones")
ax.grid(True, alpha=0.3)
ax.legend()
plt.tight_layout()
plt.savefig(out / "velocidad_promedio_vs_t.png", dpi=150)
plt.close(fig)
print(f"  → {out / 'velocidad_promedio_vs_t.png'}")


# ─── Paso 5: seleccionar tiempos para histogramas y estacionario ────────────────
# Tiempos para mostrar la evolución de f(v)
# Se excluye t=0 porque la delta en v0 aplasta la escala del resto.
if args.tiempos is not None:
    display_times = [t for t in floats(args.tiempos, "--tiempos") if t > 0]
else:
    # t = 10, 30, 60
    display_times = [0, 5, 10.0, 15, 20.0, 25, 30.0,35,40,45,50,55,60]

# Mapear cada display_time al frame más cercano
tolerance = saved_step / 2 + 1e-8


def closest_frame_time(target):
    idx = np.argmin(np.abs(times_array - target))
    return common_times[idx]


display_frame_times = sorted(set(closest_frame_time(t) for t in display_times))

# Tiempos estacionarios: todos los frames con t >= t_stationary
stationary_frame_times = [t for t in common_times if t >= t_stationary - 1e-9]
print(f"Frames estacionarios: {len(stationary_frame_times)} (desde t={stationary_frame_times[0]:g} "
      f"hasta t={stationary_frame_times[-1]:g} s)")


# ─── Paso 6: construir bolsas y ajustar ────────────────────────────────────────
def histogram(sample, edges):
    counts, _ = np.histogram(sample, edges)
    return counts, counts / (len(sample) * np.diff(edges))


def maxwell_boltzmann(speed, kbt):
    return MASS / kbt * speed * np.exp(-MASS * speed ** 2 / (2 * kbt))


def fit_kbt(centres, density, sigma, initial):
    """Minimiza chi² en log(kBT) mediante búsqueda por sección áurea."""
    usable = sigma > 0
    if usable.sum() < 3:
        usable, sigma = np.ones(len(centres), dtype=bool), np.ones(len(centres))

    def chi_square(log_kbt):
        model = maxwell_boltzmann(centres[usable], np.exp(log_kbt))
        return np.sum(((density[usable] - model) / sigma[usable]) ** 2)

    left, right = np.log(max(initial / 20, 1e-12)), np.log(initial * 20)
    ratio = (np.sqrt(5) - 1) / 2
    c, d = right - ratio * (right - left), left + ratio * (right - left)
    for _ in range(100):
        if chi_square(c) < chi_square(d):
            right, d = d, c
            c = right - ratio * (right - left)
        else:
            left, c = c, d
            d = left + ratio * (right - left)
    return float(np.exp((left + right) / 2))


# Bolsas para cada frame de display
pooled_display = {}
for t in display_frame_times:
    pooled_display[t] = np.concatenate([frames[t] for frames in all_frames])

# Bolsa estacionaria: TODOS los frames con t >= t_stationary, de todas las realizaciones
stationary_by_run = [
    np.concatenate([frames[t] for t in stationary_frame_times])
    for frames in all_frames
]
stationary_bag = np.concatenate(stationary_by_run)
print(f"Bolsa estacionaria: {len(stationary_bag)} velocidades "
      f"({len(stationary_frame_times)} frames × {args.reps} realizaciones × {args.n} partículas)")

maximum_speed = max(np.max(bag) for bag in [stationary_bag] + list(pooled_display.values()))
edges = np.linspace(0, maximum_speed * 1.05, args.bins + 1)
centres = (edges[:-1] + edges[1:]) / 2

histograms_display = {t: histogram(sample, edges) for t, sample in pooled_display.items()}
stationary_counts, stationary_density = histogram(stationary_bag, edges)
kbt_moment = MASS * np.mean(stationary_bag ** 2) / 2

# Error del histograma: desvío entre realizaciones
run_densities = np.array([histogram(sample, edges)[1] for sample in stationary_by_run])
sigma_density = run_densities.std(axis=0, ddof=1) / np.sqrt(args.reps) if args.reps > 1 else np.ones(args.bins)
kbt_fit = fit_kbt(centres, stationary_density, sigma_density, kbt_moment)

# Construir la función chi²(kBT) para graficar el pocito del error
usable_bins = sigma_density > 0
if usable_bins.sum() < 3:
    usable_bins = np.ones(len(centres), dtype=bool)
    sigma_for_chi2 = np.ones(len(centres))
else:
    sigma_for_chi2 = sigma_density


def chi2_of_kbt(kbt_val):
    model = maxwell_boltzmann(centres[usable_bins], kbt_val)
    return np.sum(((stationary_density[usable_bins] - model) / sigma_for_chi2[usable_bins]) ** 2)


# Barrer kBT alrededor del mínimo para el gráfico del pocito
kbt_scan = np.linspace(kbt_fit * 0.5, kbt_fit * 1.5, 500)
chi2_scan = np.array([chi2_of_kbt(k) for k in kbt_scan])
chi2_min = chi2_of_kbt(kbt_fit)

# Error del ajuste: rango donde chi² < chi²_min + 1 (1 sigma, 1 parámetro libre)
mask_1sigma = chi2_scan <= chi2_min + 1
kbt_in_1sigma = kbt_scan[mask_1sigma]
if len(kbt_in_1sigma) > 0:
    kbt_error_low = kbt_fit - kbt_in_1sigma[0]
    kbt_error_high = kbt_in_1sigma[-1] - kbt_fit
else:
    kbt_error_low = kbt_error_high = 0.0


# ─── Paso 7: guardar CSVs ──────────────────────────────────────────────────────
# CSV de <v>(t) para cada realización y promedio
with open(out / "velocidad_promedio_vs_t.csv", "w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    header = ["t_s", "v_promedio_m_s", "v_promedio_error_m_s"]
    writer.writerow(header)
    for i, t in enumerate(common_times):
        writer.writerow([t, mean_speed[i], std_speed[i]])

with open(out / "distribuciones.csv", "w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow(["t_s", "v_min_m_s", "v_max_m_s", "v_centro_m_s", "conteo", "densidad_s_m"])
    for t in display_frame_times:
        counts, density = histograms_display[t]
        for low, high, centre, count, value in zip(edges[:-1], edges[1:], centres, counts, density):
            writer.writerow([t, low, high, centre, count, value])

with open(out / "resumen.csv", "w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow(["t_s", "muestras", "v_promedio_m_s", "v2_promedio_m2_s2", "m_v2_sobre_2_J"])
    for t in display_frame_times:
        sample = pooled_display[t]
        writer.writerow([t, len(sample), np.mean(sample), np.mean(sample ** 2),
                         MASS * np.mean(sample ** 2) / 2])

with open(out / "ajuste_estacionario.csv", "w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow(["t_inicio_estacionario_s", "t_fin_s", "n_frames_estacionarios",
                     "muestras", "kBT_ajuste_J", "kBT_error_minus_J", "kBT_error_plus_J",
                     "chi2_min", "m_v2_sobre_2_J", "m_v0_2_sobre_2_J"])
    writer.writerow([t_stationary, common_times[-1], len(stationary_frame_times),
                     len(stationary_bag), kbt_fit, kbt_error_low, kbt_error_high,
                     chi2_min, kbt_moment, MASS / 2])


# ─── Paso 8: gráficos ──────────────────────────────────────────────────────────
# 8a: distribuciones f(v) para distintos tiempos (todas juntas)
fig, ax = plt.subplots(figsize=(8, 5))
for t in display_frame_times:
    ax.step(centres, histograms_display[t][1], where="mid", label=f"t = {t:g} s")
ax.set(xlabel="v (m/s)", ylabel="f(v) (s/m)",
       title=f"N={args.n}; bolsa de {args.reps * args.n} velocidades por tiempo")
ax.grid(True, alpha=0.3)
ax.legend(ncol=2, fontsize=8)
plt.tight_layout()
plt.savefig(out / "distribuciones_vs_t.png", dpi=130)
plt.close(fig)

# 8a-individual: f(v) vs v para cada tiempo por separado
curve_speed = np.linspace(0, edges[-1], 500)
for t in display_frame_times:
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    ax.step(centres, histograms_display[t][1], where="mid", lw=1.5, color="tab:blue",
            label=f"t = {t:g} s")
    ax.plot(curve_speed, maxwell_boltzmann(curve_speed, kbt_fit), lw=1.5, color="tab:red",
            ls="--", label="Maxwell-Boltzmann")
    ax.set(xlabel="v (m/s)", ylabel="f(v) (s/m)",
           title=f"f(v) — t = {t:g} s — N={args.n}, {args.reps * args.n} muestras")
    ax.grid(True, alpha=0.3)
    ax.legend()
    plt.tight_layout()
    plt.savefig(out / f"fv_t{t:g}.png", dpi=130)
    plt.close(fig)

# 8b: ajuste Maxwell-Boltzmann usando SÓLO datos estacionarios
fig, ax = plt.subplots(figsize=(7.5, 4.8))
ax.errorbar(centres, stationary_density, yerr=sigma_density, fmt="o", ms=3, capsize=2,
            label=f"bolsa estacionaria (t ≥ {t_stationary:g} s)")
curve_speed = np.linspace(0, edges[-1], 500)
ax.plot(curve_speed, maxwell_boltzmann(curve_speed, kbt_fit), lw=2,
        label=r"Maxwell-Boltzmann")
ax.set(xlabel="v (m/s)", ylabel="f(v) (s/m)",
       title=f"Ajuste con {len(stationary_bag)} velocidades (t ≥ {t_stationary:g} s)")
ax.grid(True, alpha=0.3)
ax.legend()
plt.tight_layout()
plt.savefig(out / "ajuste_estacionario.png", dpi=130)
plt.close(fig)

# 8c: gráfico del pocito de chi² — error del ajuste
fig, ax = plt.subplots(figsize=(7.5, 4.8))
ax.plot(kbt_scan, chi2_scan, "-", lw=1.5, color="tab:blue")
ax.axhline(chi2_min + 1, color="tab:orange", ls="--", lw=1, label=r"$\chi^2_{min} + 1$")
ax.axvline(kbt_fit, color="tab:red", ls="-", lw=1, alpha=0.7, label=rf"$k_BT = {kbt_fit:.4g}$ J")
if len(kbt_in_1sigma) > 0:
    ax.axvspan(kbt_in_1sigma[0], kbt_in_1sigma[-1], alpha=0.15, color="tab:red",
               label=rf"$\delta k_BT = ^{{+{kbt_error_high:.2g}}}_{{-{kbt_error_low:.2g}}}$ J")
ax.set(xlabel=r"$k_BT$ (J)", ylabel=r"$\chi^2(k_BT)$",
       title=r"Error del ajuste: $\chi^2$ vs $k_BT$")
ax.grid(True, alpha=0.3)
ax.legend()
plt.tight_layout()
plt.savefig(out / "chi2_vs_kbt.png", dpi=150)
plt.close(fig)

# 8d: energía cinética por partícula vs tiempo
moment_energy_vs_t = np.array([
    [MASS * np.mean(frames[t] ** 2) / 2 for t in common_times]
    for frames in all_frames
])
mean_energy = np.mean(moment_energy_vs_t, axis=0)

fig, ax = plt.subplots(figsize=(7.5, 4.5))
ax.plot(times_array, mean_energy, "-", lw=1.2, label=r"$m\langle v^2\rangle/2$")
ax.axhline(MASS / 2, color="gray", ls="--", label=r"$m v_0^2/2=0.0125$ J")
ax.axhline(kbt_fit, color="tab:red", ls=":", label=r"$k_BT$ ajustado")
ax.axvline(t_stationary, color="tab:green", ls="--", alpha=0.7,
           label=f"inicio estacionario: t = {t_stationary:g} s")
ax.set(xlabel="t (s)", ylabel="energía por partícula (J)", title="Evolución hacia el estacionario")
ax.grid(True, alpha=0.3)
ax.legend()
plt.tight_layout()
plt.savefig(out / "energia_cinetica_vs_t.png", dpi=130)
plt.close(fig)

# ─── Resumen ────────────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"Tiempo estacionario:  t >= {t_stationary:g} s")
print(f"Frames estacionarios: {len(stationary_frame_times)}")
print(f"Bolsa estacionaria:   {len(stationary_bag)} velocidades")
print(f"kBT ajuste = {kbt_fit:.6g} J  (+{kbt_error_high:.2g} / -{kbt_error_low:.2g})")
print(f"chi²_min   = {chi2_min:.4g}")
print(f"m<v²>/2    = {kbt_moment:.6g} J")
print(f"m v0²/2    = {MASS / 2:.6g} J")
print(f"Resultados en {out}")
