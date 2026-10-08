#include "neighbours/Grid.h"

namespace neighbours {

Grid::Grid(double radius, double cellSize)
    : radius(radius), cellSize(cellSize) {}

void Grid::rebuild(std::vector<types::Particle>& particles) {
    for (auto& cell : grid_) cell.clear();
    for (auto& p : particles) {
        int cx = cellIndexX(p.getXLocation());
        int cy = cellIndexY(p.getYLocation());
        p.setCellXIndex(cx);
        p.setCellYIndex(cy);
        grid_[flatIndex(cx, cy)].push_back(&p);
    }
}

std::vector<types::Particle*> Grid::neighboursOf(const types::Particle& p) const {
    std::vector<types::Particle*> result;
    int cx = p.getCellXIndex();
    int cy = p.getCellYIndex();
    for (int dx = -1; dx <= 1; dx++) {
        for (int dy = -1; dy <= 1; dy++) {
            int nx = cx + dx, ny = cy + dy;
            if (nx < 0 || nx >= cellsX_ || ny < 0 || ny >= cellsY_) continue;
            for (auto* other : grid_[flatIndex(nx, ny)]) {
                if (other->getId() != p.getId()) result.push_back(other);
            }
        }
    }
    return result;
}

} 