#include "simulation/Simulation.h"

namespace simulation {

Simulation::Simulation(SimulationConfig config) 
    : config(config), 
    board(0.51, config.x0, PARTICLE_RADIUS),
    grid(0.51, 2.0 * PARTICLE_RADIUS),
    writer(config.outputEverySteps),
    rng(config.seed),
    time(0.0) {}

void Simulation::run(std::string outputPath) {

}

void Simulation::initializeParticles() {

}

void Simulation::step() {

}

std::vector<types::Vector2D> Simulation::computeForces() {

}

void Simulation::addParticleForces(std::vector<types::Vector2D>& forces) {

}

void Simulation::addObstacleForces(std::vector<types::Vector2D>& forces) {

}

void Simulation::addWallForces(std::vector<types::Vector2D>& forces) {

}

bool Simulation::isValidInitialPosition(const types::Vector2D& position) const {
    
}

}