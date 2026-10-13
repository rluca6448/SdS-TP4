#include "simulation/Simulation.h"

#include <cstdlib>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <string>

// Uso: tp4 [N] [tiempo_final] [archivo_salida] [--dt X] [--every N] [--seed S] [--sin-obstaculos]
int main(int argc, char* argv[]) {
    try {
        simulation::SimulationConfig config;
        std::string outputPath = "output.txt";

        int positional = 0;
        for (int i = 1; i < argc; i++) {
            const std::string arg = argv[i];
            if (arg == "--sin-obstaculos") {
                config.obstacles = false;
            } else if (arg == "--dt" || arg == "--every" || arg == "--seed") {
                if (i + 1 >= argc) throw std::invalid_argument("falta el valor de " + arg);
                const std::string value = argv[++i];
                if (arg == "--dt") config.dt = std::stod(value);
                else if (arg == "--every") config.outputEverySteps = std::stoi(value);
                else config.seed = static_cast<unsigned int>(std::stoul(value));
            } else if (arg.rfind("--", 0) == 0) {
                throw std::invalid_argument("opcion desconocida: " + arg);
            } else if (positional == 0) {
                config.particleCount = std::stoi(arg);
                positional++;
            } else if (positional == 1) {
                config.finalTime = std::stod(arg);
                positional++;
            } else if (positional == 2) {
                outputPath = arg;
                positional++;
            } else {
                throw std::invalid_argument("argumento de sobra: " + arg);
            }
        }
        if (config.dt <= 0.0 || config.outputEverySteps < 1) {
            throw std::invalid_argument("dt debe ser > 0 y --every >= 1");
        }

        simulation::Simulation sim(config);
        sim.run(outputPath);

        std::cout << "Listo: " << outputPath << '\n';
    } catch (const std::exception& exception) {
        std::cerr << "Error: " << exception.what() << '\n';
        return EXIT_FAILURE;
    }
}
