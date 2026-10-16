#include "simulation/Simulation.h"

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
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
    grid(0.51, 2.0 * PARTICLE_RADIUS),
    writer(config.outputEverySteps),
    rng(config.seed),
    time(0.0) {
    // Los obstaculos van desde en contacto entre si (x0 = r) hasta en contacto con la pared (x0 = R - r)
    constexpr double TOLERANCE = 1e-9;
    if (config.obstacles && (config.x0 < PARTICLE_RADIUS - TOLERANCE ||
                             config.x0 > board.getRadius() - PARTICLE_RADIUS + TOLERANCE)) {
        throw std::invalid_argument("x0 debe estar entre " + std::to_string(PARTICLE_RADIUS) + " y " +
                                    std::to_string(board.getRadius() - PARTICLE_RADIUS));
    }
}

// Simula hasta finalTime y guarda el estado en t=0 y cada outputEverySteps pasos.
// Junto al output escribe, en los mismos instantes, <salida>_energia.txt con "t E" y
// <salida>_usadas.txt con "t N_usadas" (alcanza para F_u(t) y t90 sin guardar el estado).
void Simulation::run(std::string outputPath) {
    initializeParticles();
    writer.open(outputPath);

    std::filesystem::path energyPath(outputPath);
    energyPath.replace_extension();
    energyPath += "_energia.txt";
    std::ofstream energyOut(energyPath);
    if (!energyOut) {
        throw std::runtime_error("No se pudo abrir el archivo de energia: " + energyPath.string());
    }
    energyOut.precision(12);
    energyOut << "# t E\n";

    std::filesystem::path usedPath(outputPath);
    usedPath.replace_extension();
    usedPath += "_usadas.txt";
    std::ofstream usedOut(usedPath);
    if (!usedOut) {
        throw std::runtime_error("No se pudo abrir el archivo de usadas: " + usedPath.string());
    }
    usedOut.precision(12);
    usedOut << "# t N_usadas\n";

    auto save = [&]() {
        writer.writeStateImmediately(particles, time);
        energyOut << time << " " << totalEnergy() << "\n";
        usedOut << time << " " << std::count_if(particles.begin(), particles.end(),
                                                [](const types::Particle& p) { return p.getUsed(); }) << "\n";
    };

    save();
    const long long steps = std::llround(config.finalTime / config.dt);
    for (long long n = 0; n < steps; n++) {
        step();
        if ((n + 1) % config.outputEverySteps == 0) save();
    }
    writer.close();
}

double Simulation::totalEnergy() const {
    const double k = config.springConstant;
    const auto potential = [k](double xi) { return xi > 0.0 ? 0.5 * k * xi * xi : 0.0; };

    double energy = 0.0;
    for (std::size_t i = 0; i < particles.size(); i++) {
        const types::Particle& p = particles[i];
        const double speed = p.getVelocity().norm();
        energy += 0.5 * p.getMass() * speed * speed;

        for (std::size_t j = i + 1; j < particles.size(); j++) {
            const double distance = (particles[j].getPosition() - p.getPosition()).norm();
            energy += potential(p.getRadius() + particles[j].getRadius() - distance);
        }
        if (config.obstacles) {
            for (const auto& obstacle : board.getObstacles()) {
                const double distance =
                    (types::Vector2D{obstacle.getX(), obstacle.getY()} - p.getPosition()).norm();
                energy += potential(p.getRadius() + obstacle.getRadius() - distance);
            }
        }
        // pared: xi = |r| + r - R (particula imagen, ver addWallForces)
        energy += potential(p.getPosition().norm() + p.getRadius() - board.getRadius());
    }
    return energy;
}

// Ubica las N particulas y arma el estado inicial de Verlet: a(0) y r(-dt).
// Primero por rechazo (posiciones uniformes al azar); si el sorteo se satura (hacia el 55%
// del area cubierta) las ubica en una red hexagonal con ruido (placeOnLattice).
void Simulation::initializeParticles() {
    const double twoPi = 2.0 * std::acos(-1.0);
    const double maxRadius = board.getRadius() - PARTICLE_RADIUS;
    std::uniform_real_distribution<double> unit(0.0, 1.0);

    time = 0.0;
    particles.clear();
    particles.reserve(config.particleCount);

    bool saturated = false;
    for (int id = 0; id < config.particleCount && !saturated; id++) {
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
            saturated = true;
            break;
        }

        const double theta = twoPi * unit(rng);
        const types::Vector2D velocity{config.initialSpeed * std::cos(theta),
                                       config.initialSpeed * std::sin(theta)};
        particles.emplace_back(id, position, velocity, PARTICLE_MASS, PARTICLE_RADIUS);
    }
    if (saturated) placeOnLattice();

    updateAccelerations();

    // r(-dt) con Euler hacia atras (teorica, diap. 14)
    const double dt = config.dt;
    for (auto& p : particles) {
        p.setPreviousPosition(p.getPosition() - p.getVelocity() * dt +
                              p.getAcceleration() * (0.5 * dt * dt));
    }
}

// Red hexagonal con ruido para densidades altas: busca el mayor espaciado d (>= 2r) cuya red
// tiene al menos N sitios dentro del dominio, sortea N sitios y desplaza cada particula una
// distancia <= (d - 2r)/2 en una direccion al azar. Dos vecinas quedan a >= 2r: sin solapamiento.
void Simulation::placeOnLattice() {
    const double twoPi = 2.0 * std::acos(-1.0);
    const double r = PARTICLE_RADIUS;
    const double wallLimit = board.getRadius() - r;
    const std::size_t needed = static_cast<std::size_t>(config.particleCount);
    std::uniform_real_distribution<double> unit(0.0, 1.0);

    const double offsetX = unit(rng);
    const double offsetY = unit(rng);

    std::vector<types::Vector2D> sites;
    double slack = 0.0;  // desplazamiento maximo permitido, (d - 2r)/2
    bool found = false;
    constexpr int SPACING_STEPS = 1000;
    for (int k = 0; k <= SPACING_STEPS && !found; k++) {
        const double d = 4.0 * r - 2.0 * r * k / SPACING_STEPS;  // de 4r a 2r (en contacto)
        slack = (d - 2.0 * r) / 2.0;
        const double rowHeight = d * std::sqrt(3.0) / 2.0;

        sites.clear();
        for (int row = 0;; row++) {
            const double y = -wallLimit + (offsetY + row) * rowHeight;
            if (y > wallLimit) break;
            for (int col = 0;; col++) {
                const double x = -wallLimit + (offsetX + 0.5 * (row % 2) + col) * d;
                if (x > wallLimit) break;
                const types::Vector2D site{x, y};
                if (!isValidLatticeSite(site, slack)) continue;
                sites.push_back(site);
            }
        }
        found = sites.size() >= needed;
    }
    if (!found) {
        throw std::runtime_error("No se pudieron ubicar " + std::to_string(needed) +
                                 " particulas: no entran ni en una red hexagonal compacta");
    }

    std::shuffle(sites.begin(), sites.end(), rng);
    particles.clear();
    for (std::size_t id = 0; id < needed; id++) {
        const double rho = slack * std::sqrt(unit(rng));
        const double phi = twoPi * unit(rng);
        const types::Vector2D position = sites[id] + types::Vector2D{rho * std::cos(phi), rho * std::sin(phi)};

        const double theta = twoPi * unit(rng);
        const types::Vector2D velocity{config.initialSpeed * std::cos(theta),
                                       config.initialSpeed * std::sin(theta)};
        particles.emplace_back(static_cast<int>(id), position, velocity, PARTICLE_MASS, PARTICLE_RADIUS);
    }
}

// Un sitio sirve si, aun con el desplazamiento maximo, la particula queda dentro de la pared
// y sin solapar los obstaculos.
bool Simulation::isValidLatticeSite(const types::Vector2D& site, double slack) const {
    if (site.norm() > board.getRadius() - PARTICLE_RADIUS - slack) return false;
    if (config.obstacles) {
        for (const auto& obstacle : board.getObstacles()) {
            const types::Vector2D center{obstacle.getX(), obstacle.getY()};
            if ((site - center).norm() < PARTICLE_RADIUS + obstacle.getRadius() + slack) return false;
        }
    }
    return true;
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

    markUsedParticles();
    updateAccelerations();

    for (auto& p : particles) {
        p.setVelocity((p.getPosition() - p.getPreviousPosition()) * (1.0 / dt) +
                      p.getAcceleration() * (0.5 * dt));
    }
}

// Fresca -> usada al primer contacto con un obstaculo. Un choque dura cientos de pasos,
// asi que revisar la superposicion al final de cada paso no se pierde ninguno.
void Simulation::markUsedParticles() {
    if (!config.obstacles) return;
    for (auto& p : particles) {
        if (p.getUsed()) continue;
        for (const auto& obstacle : board.getObstacles()) {
            const types::Vector2D center{obstacle.getX(), obstacle.getY()};
            if ((p.getPosition() - center).norm() < p.getRadius() + obstacle.getRadius()) {
                p.setUsed();
                break;
            }
        }
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

// Solo se evaluan los pares de celdas contiguas de la grilla: dos particulas en contacto
// (distancia < 2r) siempre estan en la misma celda o en celdas contiguas.
void Simulation::addParticleForces(std::vector<types::Vector2D>& forces) {
    grid.rebuild(particles);
    grid.forEachPair([&](int i, int j) {
        const types::Vector2D f = springForce(
            particles[i].getPosition(), particles[j].getPosition(),
            particles[i].getRadius() + particles[j].getRadius(), config.springConstant);
        forces[i] += f;
        forces[j] += f * -1.0;  // tercera ley de Newton
    });
}

void Simulation::addObstacleForces(std::vector<types::Vector2D>& forces) {
    if (!config.obstacles) return;
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

    if (config.obstacles) {
        for (const auto& obstacle : board.getObstacles()) {
            const types::Vector2D center{obstacle.getX(), obstacle.getY()};
            if ((position - center).norm() < PARTICLE_RADIUS + obstacle.getRadius()) return false;
        }
    }

    for (const auto& p : particles) {
        if ((position - p.getPosition()).norm() < PARTICLE_RADIUS + p.getRadius()) return false;
    }
    return true;
}

}
