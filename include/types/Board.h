#pragma once

#include "types/Particle.h"
#include "types/Obstacle.h"

#include <array>

namespace types {

class Board {
public:
    Board(double radius = 0.51, double x0 = 0.51/2, double obstaclesRadius = 0.0175);
    
    double getRadius() const;

    const std::array<Obstacle, 2>& getObstacles() const;
private:
    double radius;
    double x0;
    std::array<Obstacle, 2> obstacles;
};
}