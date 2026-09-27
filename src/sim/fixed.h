// Fixed-point numbers for the deterministic simulation (section 7.3).
// Every operation is integer-only and fully defined: results saturate
// instead of overflowing, divisions round toward zero, and trigonometry
// reads generated integer tables. The same inputs give the same bits on
// any machine and compiler.
#pragma once

#include <compare>
#include <cstdint>

namespace sc::sim {

class Fixed {
public:
    static constexpr int kShift = 16;
    static constexpr std::int32_t kOneRaw = 1 << kShift;
    static constexpr std::int32_t kMaxRaw = INT32_MAX;
    static constexpr std::int32_t kMinRaw = INT32_MIN;

    constexpr Fixed() = default;

    [[nodiscard]] static constexpr Fixed from_raw(std::int32_t raw) {
        Fixed f;
        f.raw_ = raw;
        return f;
    }
    [[nodiscard]] static constexpr Fixed from_int(std::int32_t value) {
        return from_raw(saturate(static_cast<std::int64_t>(value) * kOneRaw));
    }
    // num / den, rounded toward zero. A zero denominator gives zero.
    [[nodiscard]] static constexpr Fixed from_ratio(std::int64_t num, std::int64_t den) {
        if (den == 0) {
            return {};
        }
        // Past this, num * 2^16 would overflow; the result saturates anyway.
        constexpr std::int64_t kLimit = INT64_MAX >> kShift;
        if (num > kLimit || num < -kLimit) {
            return (num > 0) == (den > 0) ? max() : min();
        }
        return from_raw(saturate(div_toward_zero(num * kOneRaw, den)));
    }
    [[nodiscard]] static constexpr Fixed max() { return from_raw(kMaxRaw); }
    [[nodiscard]] static constexpr Fixed min() { return from_raw(kMinRaw); }
    [[nodiscard]] static constexpr Fixed one() { return from_raw(kOneRaw); }

    [[nodiscard]] constexpr std::int32_t raw() const { return raw_; }
    // Rounds down (toward negative infinity).
    [[nodiscard]] constexpr std::int32_t floor_int() const { return raw_ >> kShift; }

    constexpr Fixed operator+(Fixed o) const { return from_raw(saturate(static_cast<std::int64_t>(raw_) + o.raw_)); }
    constexpr Fixed operator-(Fixed o) const { return from_raw(saturate(static_cast<std::int64_t>(raw_) - o.raw_)); }
    constexpr Fixed operator-() const { return from_raw(saturate(-static_cast<std::int64_t>(raw_))); }
    // Rounds toward negative infinity (arithmetic shift, defined in C++20).
    constexpr Fixed operator*(Fixed o) const {
        return from_raw(saturate((static_cast<std::int64_t>(raw_) * o.raw_) >> kShift));
    }
    // Rounds toward zero; dividing by zero saturates to the sign of the dividend.
    constexpr Fixed operator/(Fixed o) const {
        if (o.raw_ == 0) {
            return raw_ >= 0 ? max() : min();
        }
        return from_raw(saturate(div_toward_zero(static_cast<std::int64_t>(raw_) * kOneRaw, o.raw_)));
    }
    constexpr Fixed& operator+=(Fixed o) { return *this = *this + o; }
    constexpr Fixed& operator-=(Fixed o) { return *this = *this - o; }
    constexpr Fixed& operator*=(Fixed o) { return *this = *this * o; }

    constexpr auto operator<=>(const Fixed&) const = default;

private:
    [[nodiscard]] static constexpr std::int32_t saturate(std::int64_t v) {
        return v > kMaxRaw ? kMaxRaw : (v < kMinRaw ? kMinRaw : static_cast<std::int32_t>(v));
    }
    [[nodiscard]] static constexpr std::int64_t div_toward_zero(std::int64_t num, std::int64_t den) {
        // INT64_MIN / -1 is the only overflowing case; saturate it.
        if (num == INT64_MIN && den == -1) {
            return INT64_MAX;
        }
        return num / den;  // C++ integer division truncates toward zero.
    }

    std::int32_t raw_ = 0;
};

[[nodiscard]] constexpr Fixed abs(Fixed v) {
    return v.raw() < 0 ? -v : v;
}

// Square root of a non-negative value (negative inputs give zero). The
// result is the largest value whose square does not exceed the input.
[[nodiscard]] Fixed sqrt(Fixed v);

// Integer square root: the largest r with r * r <= v.
[[nodiscard]] std::uint64_t isqrt(std::uint64_t v);

// Binary angle: 65536 units per full turn, so it wraps for free.
struct Angle {
    std::uint16_t units = 0;

    [[nodiscard]] static constexpr Angle from_degrees(std::int32_t degrees) {
        const std::int64_t u = static_cast<std::int64_t>(degrees) * 65536 / 360;
        return {static_cast<std::uint16_t>(u & 0xFFFF)};
    }
    constexpr Angle operator+(Angle o) const { return {static_cast<std::uint16_t>(units + o.units)}; }
    constexpr Angle operator-(Angle o) const { return {static_cast<std::uint16_t>(units - o.units)}; }
    constexpr bool operator==(const Angle&) const = default;
};

[[nodiscard]] Fixed sin(Angle a);
[[nodiscard]] Fixed cos(Angle a);
// Angle of the vector (x, y) from the +x axis; atan2(0, 0) is 0.
[[nodiscard]] Angle atan2(Fixed y, Fixed x);

// A position or direction on the ground plane.
struct FixedVec2 {
    Fixed x;
    Fixed z;

    constexpr FixedVec2 operator+(FixedVec2 o) const { return {x + o.x, z + o.z}; }
    constexpr FixedVec2 operator-(FixedVec2 o) const { return {x - o.x, z - o.z}; }
    constexpr FixedVec2 operator*(Fixed s) const { return {x * s, z * s}; }
    constexpr bool operator==(const FixedVec2&) const = default;

    // Exact squared length in raw units squared (no overflow, no rounding).
    [[nodiscard]] std::uint64_t length_squared_raw() const;
    [[nodiscard]] Fixed length() const;
    // Unit vector in the same direction; zero stays zero.
    [[nodiscard]] FixedVec2 normalized() const;
};

}  // namespace sc::sim
