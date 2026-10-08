#pragma once

namespace simulation {
    
struct SimulationConfig {
    int particleCount = 100;
    double dt = 1e-5;
    double finalTime = 30.0;
    double x0 = 0.0175;
    double springConstant = 1e4;
    int outputEverySteps = 100;
    unsigned int seed = 1;
    double initialSpeed = 1.0;
};
}