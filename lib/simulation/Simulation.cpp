#include "simulation/Simulation.h"

#include <cmath>
#include <stdexcept>

namespace simulation {

namespace {

constexpr int MAX_PLACEMENT_ATTEMPTS = 100000;

// Fuerza sobre i por contacto con j: F = -k * xi * e_ij, con xi = (r_i + r_j) - |r_j - r_i|.
// Cero si no hay superposicion.
types::Vector2D springForce(const types::Vector2D& ri, const types::Vector2D& rj,
                            double radiusSum, double k) {
    const types::Vector2D diff = rj - ri;
    const double distance = diff.norm();
    const double xi = radiusSum - distance;
    if (xi <= 0.0 || distance < 1e-12) return {};
    return diff * (-k * xi / distance);
}

}  // namespace

Simulation::Simulation(SimulationConfig config)
    : config(config),
    board(0.51, config.x0, PARTICLE_RADIUS),
    writer(config.outputEverySteps),
    rng(config.seed),
    time(0.0) {}

void Simulation::run(std::string outputPath) {

}

// Ubica las N particulas (rechazo) y arma el estado inicial de Verlet: a(0) y r(-dt).
void Simulation::initializeParticles() {
    const double twoPi = 2.0 * std::acos(-1.0);
    const double maxRadius = board.getRadius() - PARTICLE_RADIUS;
    std::uniform_real_distribution<double> unit(0.0, 1.0);

    time = 0.0;
    particles.clear();
    particles.reserve(config.particleCount);

    for (int id = 0; id < config.particleCount; id++) {
        types::Vector2D position;
        bool placed = false;
        for (int attempt = 0; attempt < MAX_PLACEMENT_ATTEMPTS && !placed; attempt++) {
            // sqrt(u) para que la densidad sea uniforme en el area del circulo
            const double rho = maxRadius * std::sqrt(unit(rng));
            const double phi = twoPi * unit(rng);
            position = {rho * std::cos(phi), rho * std::sin(phi)};
            placed = isValidInitialPosition(position);
        }
        if (!placed) {
            throw std::runtime_error("No se pudo ubicar la particula " + std::to_string(id) +
                                     " sin solapamientos");
        }

        const double theta = twoPi * unit(rng);
        const types::Vector2D velocity{config.initialSpeed * std::cos(theta),
                                       config.initialSpeed * std::sin(theta)};
        particles.emplace_back(id, position, velocity, PARTICLE_MASS, PARTICLE_RADIUS);
    }

    updateAccelerations();

    // r(-dt) con Euler hacia atras (teorica, diap. 14)
    const double dt = config.dt;
    for (auto& p : particles) {
        p.setPreviousPosition(p.getPosition() - p.getVelocity() * dt +
                              p.getAcceleration() * (0.5 * dt * dt));
    }
}

// Verlet: r(t+dt) = 2 r(t) - r(t-dt) + a(t) dt^2.
// Las fuerzas solo dependen de las posiciones, asi que la velocidad no entra en la dinamica;
// se estima para el output con la diferencia hacia atras, que usa a(t+dt) y deja
// (r, v, a) en el mismo instante.
// ponytail: v tiene error O(dt^2). Con la centrada de la teorica, v(t) = (r(t+dt) - r(t-dt))/(2dt),
// la velocidad quedaria un paso atrasada respecto de la posicion.
void Simulation::step() {
    const double dt = config.dt;

    for (auto& p : particles) {
        const types::Vector2D r = p.getPosition();
        p.setPosition(r * 2.0 - p.getPreviousPosition() + p.getAcceleration() * (dt * dt));
        p.setPreviousPosition(r);
    }
    time += dt;

    updateAccelerations();

    for (auto& p : particles) {
        p.setVelocity((p.getPosition() - p.getPreviousPosition()) * (1.0 / dt) +
                      p.getAcceleration() * (0.5 * dt));
    }
}

void Simulation::updateAccelerations() {
    const std::vector<types::Vector2D> forces = computeForces();
    for (std::size_t i = 0; i < particles.size(); i++) {
        particles[i].setAcceleration(forces[i] * (1.0 / particles[i].getMass()));
    }
}

std::vector<types::Vector2D> Simulation::computeForces() {
    std::vector<types::Vector2D> forces(particles.size());
    addParticleForces(forces);
    addObstacleForces(forces);
    addWallForces(forces);
    return forces;
}

// ponytail: todos contra todos, O(N^2). Reemplazar por neighbours::Grid en 2.1.b.
void Simulation::addParticleForces(std::vector<types::Vector2D>& forces) {
    for (std::size_t i = 0; i < particles.size(); i++) {
        for (std::size_t j = i + 1; j < particles.size(); j++) {
            const types::Vector2D f = springForce(
                particles[i].getPosition(), particles[j].getPosition(),
                particles[i].getRadius() + particles[j].getRadius(), config.springConstant);
            forces[i] += f;
            forces[j] += f * -1.0;  // tercera ley de Newton
        }
    }
}

void Simulation::addObstacleForces(std::vector<types::Vector2D>& forces) {
    for (std::size_t i = 0; i < particles.size(); i++) {
        for (const auto& obstacle : board.getObstacles()) {
            forces[i] += springForce(
                particles[i].getPosition(), {obstacle.getX(), obstacle.getY()},
                particles[i].getRadius() + obstacle.getRadius(), config.springConstant);
        }
    }
}

// Pared como particula imagen fija de radio r en (R + r) * n, con n radial (consigna, Fig. 1b).
void Simulation::addWallForces(std::vector<types::Vector2D>& forces) {
    const double wallRadius = board.getRadius();
    for (std::size_t i = 0; i < particles.size(); i++) {
        const types::Vector2D position = particles[i].getPosition();
        const double distance = position.norm();
        const double r = particles[i].getRadius();
        if (distance <= wallRadius - r) continue;  // sin contacto (y evita normalizar el origen)

        const types::Vector2D image = position * ((wallRadius + r) / distance);
        forces[i] += springForce(position, image, 2.0 * r, config.springConstant);
    }
}

bool Simulation::isValidInitialPosition(const types::Vector2D& position) const {
    if (position.norm() > board.getRadius() - PARTICLE_RADIUS) return false;

    for (const auto& obstacle : board.getObstacles()) {
        const types::Vector2D center{obstacle.getX(), obstacle.getY()};
        if ((position - center).norm() < PARTICLE_RADIUS + obstacle.getRadius()) return false;
    }

    for (const auto& p : particles) {
        if ((position - p.getPosition()).norm() < PARTICLE_RADIUS + p.getRadius()) return false;
    }
    return true;
}

}
