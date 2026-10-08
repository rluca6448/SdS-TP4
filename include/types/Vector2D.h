#pragma once

#include <cmath>

namespace types {

struct Vector2D {
    double x = 0.0;
    double y = 0.0;

    Vector2D operator+(const Vector2D& other) const {
        return {x + other.x, y + other.y};
    };

    Vector2D operator-(const Vector2D& other) const {
        return {x - other.x, y - other.y};
    };

    Vector2D operator*(double scalar) const {
        return {x * scalar, y * scalar};
    };

    Vector2D& operator+=(const Vector2D& other) {
        x += other.x;
        y += other.y;
        return *this;
    };

    double norm() const {
        return std::sqrt(x * x + y * y);
    };
};
}