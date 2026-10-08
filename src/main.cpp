#include "simulation/Simulation.h"

#include <cstdlib>
#include <exception>
#include <iostream>
#include <string>

// Uso: tp4 [N] [tiempo_final] [archivo_salida]
int main(int argc, char* argv[]) {
    try {
        simulation::SimulationConfig config;
        std::string outputPath = "output.txt";

        if (argc > 1) config.particleCount = std::stoi(argv[1]);
        if (argc > 2) config.finalTime = std::stod(argv[2]);
        if (argc > 3) outputPath = argv[3];

        simulation::Simulation sim(config);
        sim.run(outputPath);

        std::cout << "Listo: " << outputPath << '\n';
    } catch (const std::exception& exception) {
        std::cerr << "Error: " << exception.what() << '\n';
        return EXIT_FAILURE;
    }
}
