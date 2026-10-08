#include <exception>
#include <iostream>
#include <stdexcept>

int main(int argc, char* argv[]) {
    try {
        double radius = 0.51;
        double x0 = radius/2;
        int particleCount = 100;

        

    } catch (const std::exception& exception) {
        std::cerr << "Error: " << exception.what() << '\n';
        return EXIT_FAILURE;
    }
}