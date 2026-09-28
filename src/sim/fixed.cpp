#include "sim/fixed.h"

#include <bit>

namespace sc::sim {

namespace {

#include "sim/fixed_tables.inc"

constexpr int kQuarterEntries = 1024;
constexpr int kCordicSteps = 16;

// sin for the first quarter turn: units in [0, 16384].
std::int32_t sin_quarter(std::int32_t units) {
    // 16 angle units per table step; interpolate linearly between entries.
    const std::int32_t index = units >> 4;
    const std::int32_t frac = units & 15;
    if (index >= kQuarterEntries) {
        return kSinQuarter[kQuarterEntries];
    }
    const std::int32_t a = kSinQuarter[index];
    const std::int32_t b = kSinQuarter[index + 1];
    return a + (((b - a) * frac) >> 4);
}

}  // namespace

std::uint64_t isqrt(std::uint64_t v) {
    // Bit-by-bit method, exact. It starts at the highest power of four not
    // above v and chooses without branches: map generation calls it for
    // hundreds of millions of points.
    if (v == 0) {
        return 0;
    }
    std::uint64_t result = 0;
    for (std::uint64_t bit = 1ull << ((std::bit_width(v) - 1) & ~1); bit != 0; bit >>= 2) {
        const std::uint64_t trial = result + bit;
        const std::uint64_t fits = v >= trial ? ~0ull : 0ull;
        v -= trial & fits;
        result = (result >> 1) + (bit & fits);
    }
    return result;
}

Fixed sqrt(Fixed v) {
    if (v.raw() <= 0) {
        return {};
    }
    // sqrt(raw / 2^16) * 2^16 = sqrt(raw * 2^16).
    const std::uint64_t r = isqrt(static_cast<std::uint64_t>(v.raw()) << Fixed::kShift);
    return Fixed::from_raw(static_cast<std::int32_t>(r));
}

Fixed sin(Angle a) {
    const std::int32_t u = a.units;
    const std::int32_t quadrant = u >> 14;
    const std::int32_t within = u & 0x3FFF;
    switch (quadrant) {
        case 0: return Fixed::from_raw(sin_quarter(within));
        case 1: return Fixed::from_raw(sin_quarter(16384 - within));
        case 2: return Fixed::from_raw(-sin_quarter(within));
        default: return Fixed::from_raw(-sin_quarter(16384 - within));
    }
}

Fixed cos(Angle a) {
    return sin(Angle{static_cast<std::uint16_t>(a.units + 16384)});
}

Angle atan2(Fixed y, Fixed x) {
    std::int64_t vx = x.raw();
    std::int64_t vy = y.raw();
    if (vx == 0 && vy == 0) {
        return {};
    }
    // Rotate into the right half-plane first; CORDIC converges within ±90°.
    std::int32_t angle = 0;
    if (vx < 0) {
        const std::int64_t tx = vx;
        if (vy >= 0) {
            vx = vy;
            vy = -tx;
            angle = 16384;  // +90°
        } else {
            vx = -vy;
            vy = tx;
            angle = -16384;  // -90°
        }
    }
    // Scale up for precision while staying far from overflow.
    while (vx < (1ll << 40) && vy < (1ll << 40) && vx > -(1ll << 40) && vy > -(1ll << 40)) {
        vx <<= 1;
        vy <<= 1;
    }
    for (int i = 0; i < kCordicSteps; ++i) {
        const std::int64_t dx = vx >> i;
        const std::int64_t dy = vy >> i;
        if (vy > 0) {
            vx += dy;
            vy -= dx;
            angle += kCordicAngles[i];
        } else if (vy < 0) {
            vx -= dy;
            vy += dx;
            angle -= kCordicAngles[i];
        } else {
            break;
        }
    }
    return {static_cast<std::uint16_t>(angle & 0xFFFF)};
}

std::uint64_t FixedVec2::length_squared_raw() const {
    const auto ax = static_cast<std::uint64_t>(x.raw() < 0 ? -static_cast<std::int64_t>(x.raw()) : x.raw());
    const auto az = static_cast<std::uint64_t>(z.raw() < 0 ? -static_cast<std::int64_t>(z.raw()) : z.raw());
    return ax * ax + az * az;  // Each term < 2^62, so the sum fits.
}

Fixed FixedVec2::length() const {
    const std::uint64_t r = isqrt(length_squared_raw());
    return Fixed::from_raw(r > static_cast<std::uint64_t>(Fixed::kMaxRaw) ? Fixed::kMaxRaw : static_cast<std::int32_t>(r));
}

FixedVec2 FixedVec2::normalized() const {
    const Fixed len = length();
    if (len.raw() == 0) {
        return {};
    }
    return {x / len, z / len};
}

}  // namespace sc::sim
