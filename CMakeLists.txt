cmake_minimum_required(VERSION 3.10)
project(SdS_TP4 CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

# ponytail: neighbours/Grid.cpp queda fuera hasta el punto 2.1.b (hoy los pares son O(N^2))
file(GLOB SOURCES lib/io/*.cpp lib/simulation/*.cpp lib/types/*.cpp)

add_executable(tp4 src/main.cpp ${SOURCES})
target_include_directories(tp4 PRIVATE include)
target_compile_options(tp4 PRIVATE -Wall -Wextra)
