cmake_minimum_required(VERSION 3.10)
project(SdS_TP4 CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

file(GLOB SOURCES lib/io/*.cpp lib/neighbours/*.cpp lib/simulation/*.cpp lib/types/*.cpp)

# Optimizacion entre archivos: sin ella las funciones chicas de Particle (definidas en otro .cpp)
# no se inlinean y la simulacion tarda ~4 veces mas.
include(CheckIPOSupported)
check_ipo_supported(RESULT ipo_supported OUTPUT ipo_message)
if(ipo_supported)
    set(CMAKE_INTERPROCEDURAL_OPTIMIZATION ON)
endif()

add_executable(tp4 src/main.cpp ${SOURCES})
target_include_directories(tp4 PRIVATE include)
target_compile_options(tp4 PRIVATE -Wall -Wextra)
