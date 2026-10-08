#pragma once 

#include "types/Particle.h"

#include <string>
#include <vector>
#include <fstream>
#include <stdexcept>

namespace io {

class StateWriter {
public:
    StateWriter(int outputEverySteps);

    void open(std::string path);

    void writeState(const std::vector<types::Particle>& particles, double time);
    void writeStateImmediately(
        const std::vector<types::Particle>& particles,
        double time);

    void close();

private:
    std::ofstream out_;
    int stepCounter = 0;
    int writeEverySteps = 100;
    
};
}