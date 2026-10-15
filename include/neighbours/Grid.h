#pragma once

#include "types/Particle.h"

#include <vector>

namespace neighbours {

// Grilla uniforme de celdas sobre el cuadrado [-halfWidth, halfWidth]^2.
// Si el lado de la celda es >= al alcance del contacto, dos particulas en contacto estan
// en la misma celda o en celdas contiguas.
class Grid {
public:
    Grid(double halfWidth, double minCellSize);

    // Reasigna todas las particulas a su celda segun la posicion actual.
    void rebuild(const std::vector<types::Particle>& particles);

    // Llama f(i, j) una vez por cada par de particulas (indices) en la misma celda o en
    // celdas contiguas. Los pares candidatos incluyen otros que no se tocan.
    template <typename F>
    void forEachPair(F&& f) const {
        // Solo 4 de las 8 celdas vecinas: asi cada par de celdas se visita una sola vez.
        static constexpr int NEIGHBOUR_DX[4] = {1, -1, 0, 1};
        static constexpr int NEIGHBOUR_DY[4] = {0, 1, 1, 1};

        for (int cy = 0; cy < cellsPerSide; cy++) {
            for (int cx = 0; cx < cellsPerSide; cx++) {
                for (int i = head[cy * cellsPerSide + cx]; i >= 0; i = next[i]) {
                    for (int j = next[i]; j >= 0; j = next[j]) f(i, j);

                    for (int k = 0; k < 4; k++) {
                        const int nx = cx + NEIGHBOUR_DX[k];
                        const int ny = cy + NEIGHBOUR_DY[k];
                        if (nx < 0 || nx >= cellsPerSide || ny >= cellsPerSide) continue;
                        for (int j = head[ny * cellsPerSide + nx]; j >= 0; j = next[j]) f(i, j);
                    }
                }
            }
        }
    }

private:
    int cellIndex(double coordinate) const;

    double halfWidth;
    double cellSize;
    int cellsPerSide;

    std::vector<int> head;  // primera particula de cada celda (-1 si esta vacia)
    std::vector<int> next;  // siguiente particula de la misma celda (-1 si es la ultima)
};
}
