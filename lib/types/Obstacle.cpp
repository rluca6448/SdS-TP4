#include "types/Obstacle.h"

#include <cmath>

namespace types {

Obstacle::Obstacle(double x, double y, double radius)
    : x(x), y(y), radius(radius) {}

double Obstacle::getX() const {
    return x;
}

double Obstacle::getY() const {
    return y;
}

double Obstacle::getRadius() const {
    return radius;
}
}