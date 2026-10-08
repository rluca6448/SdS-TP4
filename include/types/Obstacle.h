#pragma once

#include "types/Particle.h"

namespace types {

class Obstacle {
public:
    Obstacle(double x, double y, double radius);

    double getX() const;
    double getY() const;
    double getRadius() const;

private:
    double x;
    double y;
    
    double radius;
    
};
}