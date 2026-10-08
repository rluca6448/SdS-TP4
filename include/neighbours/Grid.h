#pragma once

#include "types/Particle.h"

#include <vector>
#include <algorithm>

namespace neighbours {

class Grid {
public:
    Grid(double radius, double cellSize);

    void rebuild(std::vector<types::Particle>& particles);

    std::vector<types::Particle*> neighboursOf(const types::Particle& p) const;

private:
    double radius;
    double cellSize;
    
    std::vector<std::vector<types::Particle*>> grid_;
};
}