#pragma once

namespace simulation {
    
struct SimulationConfig {
    int particleCount = 100;
    double dt = 1e-5;
    double finalTime = 5.0;
    double x0 = 0.255;
    double springConstant = 1e4;
    int outputEverySteps = 100;
    unsigned int seed = 1;
    double initialSpeed = 1.0;
    bool obstacles = true;  // false: sistema sin obstaculos (punto 2.1.a)
};
}