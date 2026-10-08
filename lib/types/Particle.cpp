#include "types/Particle.h"

namespace types {

Particle::Particle(int id, Vector2D position, Vector2D velocity, double mass, double radius)
    : id(id), position(position), previousPosition(position), velocity(velocity),
      radius(radius), mass(mass), used(false) {}

int Particle::getId() const { return id; }

Vector2D Particle::getPosition() const { return position; }
void Particle::setPosition(Vector2D position) { this->position = position; }

Vector2D Particle::getVelocity() const { return velocity; }
void Particle::setVelocity(Vector2D velocity) { this->velocity = velocity; }

Vector2D Particle::getPreviousPosition() const { return previousPosition; }
void Particle::setPreviousPosition(Vector2D previousPosition) { this->previousPosition = previousPosition; }

Vector2D Particle::getAcceleration() const { return acceleration; }
void Particle::setAcceleration(Vector2D acceleration) { this->acceleration = acceleration; };

double Particle::getRadius() const { return radius; }

bool Particle::getUsed() const { return used; }
void Particle::setUsed() { this->used = true; }

void Particle::setMass(double mass) { this->mass = mass; }
double Particle::getMass() const { return mass; }

} 
