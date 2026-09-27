// Deterministic random numbers for the simulation: PCG32 (O'Neill,
// pcg_setseq_64_xsh_rr). Never rand() or <random>, whose results differ
// between standard libraries.
#pragma once

#include <cstdint>

#include "sim/fixed.h"

namespace sc::sim {

class Rng {
public:
    Rng() : Rng(0, 0) {}
    // `stream` picks one of 2^63 independent sequences for the same seed,
    // so each system can have its own without disturbing the others.
    Rng(std::uint64_t seed, std::uint64_t stream);

    std::uint32_t next_u32();
    // Uniform in [0, bound); 0 when bound is 0. Unbiased.
    std::uint32_t below(std::uint32_t bound);
    // Uniform in [lo, hi] (inclusive).
    std::int32_t range(std::int32_t lo, std::int32_t hi);
    // Uniform in [0, 1) with 16 fractional bits.
    Fixed unit();
    // True with probability permille / 1000.
    bool chance_permille(std::uint32_t permille);
    Angle angle();

    [[nodiscard]] std::uint64_t state() const { return state_; }
    [[nodiscard]] std::uint64_t increment() const { return inc_; }
    // Restores a saved generator. `increment` must be odd.
    [[nodiscard]] static bool restore(std::uint64_t state, std::uint64_t increment, Rng& out);

    bool operator==(const Rng&) const = default;

private:
    std::uint64_t state_ = 0;
    std::uint64_t inc_ = 1;
};

}  // namespace sc::sim
