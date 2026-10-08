#include "io/StateWriter.h"

namespace io {

StateWriter::StateWriter(int writeEverySteps) : writeEverySteps(writeEverySteps) {}
    
void StateWriter::open(std::string path) {
    out_.open(path);

    if (!out_) {
        throw std::runtime_error("No se pudo abrir el archivo de output: " + path);
    }

    stepCounter = 0;
}

void StateWriter::writeState(
    const std::vector<types::Particle>& particles,
    double time) {
    stepCounter++;

    if (stepCounter % writeEverySteps != 0) {
        return;
    }

    writeStateImmediately(particles, time);
}

void StateWriter::writeStateImmediately(
    const std::vector<types::Particle>& particles,
    double time) {
    out_ << time << "\n";

    for (const auto& p : particles) {
        out_ << p.getPosition().x << " " << p.getPosition().y << " "
             << p.getVelocity().x << " " << p.getVelocity().y << " "
             << (p.getUsed() ? "0" : "1") << "\n"; 
    }
    out_ << "\n";
}

void StateWriter::close() {
    if (out_.is_open()) {
        out_.close();
    }
}

}