#pragma once

#include <types/Vector2D.h>

#include <string>
#include <vector>
#include <cmath>
#include <random>
#include <sstream>

namespace types {

class Particle {
public:
    Particle(int id, Vector2D position, Vector2D velocity, double mass = 0.025, double radius = 0.0175);

    int getId() const;

    Vector2D getPosition() const;
    void setPosition(Vector2D position);

    Vector2D getVelocity() const;
    void setVelocity(Vector2D velocity);

    Vector2D getPreviousPosition() const;
    void setPreviousPosition(Vector2D previousPosition);

    Vector2D getAcceleration() const;
    void setAcceleration(Vector2D acceleration);

    double getRadius() const;

    void setMass(double mass);
    double getMass() const;

    bool getUsed() const;
    void setUsed();
        
private:
    int id;

    Vector2D position;
    Vector2D previousPosition;  // r(t-dt), lo necesita Verlet
    Vector2D velocity;
    Vector2D acceleration;

    double radius;
    double mass;
    bool used;
    
};
}