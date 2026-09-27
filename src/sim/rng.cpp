#include "sim/rng.h"

namespace sc::sim {

namespace {
constexpr std::uint64_t kMultiplier = 6364136223846793005ull;
}

Rng::Rng(std::uint64_t seed, std::uint64_t stream) : inc_((stream << 1u) | 1u) {
    // The reference seeding sequence.
    state_ = 0;
    (void)next_u32();
    state_ += seed;
    (void)next_u32();
}

std::uint32_t Rng::next_u32() {
    const std::uint64_t old = state_;
    state_ = old * kMultiplier + inc_;
    const auto xorshifted = static_cast<std::uint32_t>(((old >> 18u) ^ old) >> 27u);
    const auto rot = static_cast<std::uint32_t>(old >> 59u);
    return (xorshifted >> rot) | (xorshifted << ((0u - rot) & 31u));
}

std::uint32_t Rng::below(std::uint32_t bound) {
    if (bound == 0) {
        return 0;
    }
    // Lemire's method with rejection: exact uniformity, fixed rules, so the
    // number of draws consumed is itself deterministic.
    std::uint64_t m = static_cast<std::uint64_t>(next_u32()) * bound;
    auto low = static_cast<std::uint32_t>(m);
    if (low < bound) {
        const std::uint32_t threshold = (0u - bound) % bound;
        while (low < threshold) {
            m = static_cast<std::uint64_t>(next_u32()) * bound;
            low = static_cast<std::uint32_t>(m);
        }
    }
    return static_cast<std::uint32_t>(m >> 32);
}

std::int32_t Rng::range(std::int32_t lo, std::int32_t hi) {
    if (hi <= lo) {
        return lo;
    }
    const auto span = static_cast<std::uint64_t>(static_cast<std::int64_t>(hi) - lo) + 1;
    if (span > UINT32_MAX) {
        return static_cast<std::int32_t>(static_cast<std::int64_t>(lo) + next_u32());
    }
    return static_cast<std::int32_t>(static_cast<std::int64_t>(lo) + below(static_cast<std::uint32_t>(span)));
}

Fixed Rng::unit() {
    return Fixed::from_raw(static_cast<std::int32_t>(next_u32() >> 16));
}

bool Rng::chance_permille(std::uint32_t permille) {
    return below(1000) < permille;
}

Angle Rng::angle() {
    return {static_cast<std::uint16_t>(next_u32() >> 16)};
}

bool Rng::restore(std::uint64_t state, std::uint64_t increment, Rng& out) {
    if ((increment & 1u) == 0) {
        return false;
    }
    out.state_ = state;
    out.inc_ = increment;
    return true;
}

}  // namespace sc::sim
