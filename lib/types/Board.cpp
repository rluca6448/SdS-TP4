#include "types/Board.h"

#include <cmath>
#include <limits>

namespace types {

Board::Board(double radius, double x0, double obstacleRadius)
    : radius(radius), obstacles{Obstacle(-x0, 0, obstacleRadius), Obstacle(x0, 0, obstacleRadius)} {}

double Board::getRadius() const {
    return radius;
}

const std::array<Obstacle, 2>& Board::getObstacles() const {
    return obstacles;
}
}