RESULTADOS=resultados
mkdir -p "$RESULTADOS"

# 2. Punto 2.1.a: energía y elección de dt

python3 scripts/energia_dt.py --tf 30 --dts 1e-2,5e-3,1e-3,1e-4,1e-5 --seeds 1,2 --out "$RESULTADOS/2_1_a"
# Tiempo: ~1 min con 16 núcleos. Genera energia_dt.png

# 3. Punto 2.1.b: tiempo de ejecución vs N

# TP4 (con la computadora quieta: mide tiempos, una corrida a la vez). Tarda ~70 min.
python3 scripts/tiempos_N.py --out "$RESULTADOS/2_1_b" --jobs 1

# TP3: usa el binario del TP3 tal como está compilado. Poné la ruta de tu copia.
python3 scripts/tiempos_tp3.py --exe /RUTA/AL/TP3/build/sds_tp3 --out "$RESULTADOS/2_1_b/tp3"     # ~30 s

# Figura con las dos curvas
python3 scripts/tiempos_N.py --reusar --tp3 "$RESULTADOS/2_1_b/tp3/tp3_tiempos.csv" --out "$RESULTADOS/2_1_b"
# Una prueba rápida con pocos datos: --ns 100,300 --reps 3 --tf 5 en el primer comando (~30 s).

# 4. Punto 2.2: posición de los obstáculos

python3 scripts/obstaculos_x0.py --n 100 --tf 100 --puntos 11 --reps 5 --out "$RESULTADOS/2_2_N100"    # ~6 min con 16 núcleos
python3 scripts/obstaculos_x0.py --n 20  --tf 100 --puntos 11 --reps 5 --out "$RESULTADOS/2_2_N20"     # ~2 min
# Generan t90_vs_x0.png, fu_vs_t.png, t90.csv y resumen.txt en $RESULTADOS/2_2_N100/ y 2_2_N20/.

# 5. Punto 2.3: distribución de velocidades (sistema sin obstáculos, N = 100)

python3 scripts/velocidades.py --n 100 --tf 30 --reps 5 --out "$RESULTADOS/2_3_N100"
# Genera distribuciones_vs_t.png, ajuste_estacionario.png, energia_cinetica_vs_t.png y CSVs.
# Para analizar corridas existentes: agregar --reusar.

# 6. Animaciones (GIF)

mkdir -p "$RESULTADOS/gifs"

# 2.1.a: sistema sin obstáculos, N = 300
./build/tp4 300 5 "$RESULTADOS/gifs/sin_obstaculos_N300.txt" --sin-obstaculos --every 1000
python3 scripts/visualizar.py "$RESULTADOS/gifs/sin_obstaculos_N300.txt" --every 5 --fps 20 \
        --save "$RESULTADOS/gifs/sin_obstaculos_N300.gif"

# 2.1.b: con obstáculos, varios N
for n in 100 300 700; do
  ./build/tp4 $n 5 "$RESULTADOS/gifs/N$n.txt" --every 1000
  python3 scripts/visualizar.py "$RESULTADOS/gifs/N$n.txt" --every 5 --fps 20 --save "$RESULTADOS/gifs/N$n.gif"
done

# 2.2: distintas posiciones x0 (N = 100, 30 s). Al visor hay que pasarle el mismo --x0.
for x in 0.0175 0.1000 0.2075 0.3025 0.4000 0.4925; do
  ./build/tp4 100 30 "$RESULTADOS/gifs/x0_$x.txt" --x0 $x --every 1000 --seed 1
  python3 scripts/visualizar.py "$RESULTADOS/gifs/x0_$x.txt" --x0 $x --every 10 --fps 15 \
          --save "$RESULTADOS/gifs/x0_$x.gif"
done
