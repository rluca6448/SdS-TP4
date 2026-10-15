#include "neighbours/Grid.h"

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace neighbours {

Grid::Grid(double halfWidth, double minCellSize) : halfWidth(halfWidth) {
    if (halfWidth <= 0.0 || minCellSize <= 0.0) {
        throw std::invalid_argument("Grid: halfWidth y minCellSize deben ser positivos");
    }
    // Cantidad entera de celdas con lado >= minCellSize
    cellsPerSide = std::max(1, static_cast<int>(std::floor(2.0 * halfWidth / minCellSize)));
    cellSize = 2.0 * halfWidth / cellsPerSide;
    head.assign(static_cast<std::size_t>(cellsPerSide) * cellsPerSide, -1);
}

int Grid::cellIndex(double coordinate) const {
    const int index = static_cast<int>(std::floor((coordinate + halfWidth) / cellSize));
    return std::clamp(index, 0, cellsPerSide - 1);  // una particula en el borde cae en la ultima celda
}

void Grid::rebuild(const std::vector<types::Particle>& particles) {
    std::fill(head.begin(), head.end(), -1);
    next.assign(particles.size(), -1);

    for (std::size_t i = 0; i < particles.size(); i++) {
        const types::Vector2D position = particles[i].getPosition();
        const std::size_t cell =
            static_cast<std::size_t>(cellIndex(position.y)) * cellsPerSide + cellIndex(position.x);
        next[i] = head[cell];
        head[cell] = static_cast<int>(i);
    }
}

}
