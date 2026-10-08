#pragma once

#include "types/Particle.h"
#include "types/Board.h"
#include "io/StateWriter.h"
#include "simulation/SimulationConfig.h"

#include <vector>
#include <optional>
#include <limits>
#include <string>

constexpr double PARTICLE_RADIUS = 0.0175; 
constexpr double PARTICLE_MASS = 0.025;
constexpr double OBSTACLE_RADIUS = PARTICLE_RADIUS; 

namespace simulation {

class Simulation {
public:
    explicit Simulation(SimulationConfig config);

    void run(std::string outputPath);

    void initializeParticles();

    void step();

    std::vector<types::Vector2D> computeForces();

    void addParticleForces(std::vector<types::Vector2D>& forces);

    void addObstacleForces(std::vector<types::Vector2D>& forces);

    void addWallForces(std::vector<types::Vector2D>& forces);
    
    bool isValidInitialPosition(const types::Vector2D& position) const;

private:
    void updateAccelerations();

    void markUsedParticles();

    SimulationConfig config;
    types::Board board;
    std::vector<types::Particle> particles;
    io::StateWriter writer;
    std::mt19937 rng;
    double time;

};
}