// Integer value noise for map generation: smooth pseudo-random fields from
// a seed, computed only with integers so every machine gets the same map.
#pragma once

#include <array>
#include <cstdint>

namespace sc::sim {

// Mixes 64-bit values into a well-distributed hash (splitmix64 finalizer).
[[nodiscard]] constexpr std::uint64_t mix64(std::uint64_t x) {
    x ^= x >> 30;
    x *= 0xbf58476d1ce4e5b9ull;
    x ^= x >> 27;
    x *= 0x94d049bb133111ebull;
    x ^= x >> 31;
    return x;
}

// A pseudo-random value in [-32768, 32767] for an integer lattice point.
[[nodiscard]] std::int32_t lattice_value(std::uint64_t seed, std::int32_t ix, std::int32_t iz);

// Smooth noise at (x, z), with lattice points every 2^log2_cell units.
// Result in [-32768, 32767].
[[nodiscard]] std::int32_t value_noise(std::uint64_t seed, std::int32_t x, std::int32_t z, int log2_cell);

// Fractal sum of `octaves` layers, from cells of 2^log2_largest units down,
// each half the size and half the weight of the previous. The result is
// normalized to [-32768, 32767].
[[nodiscard]] std::int32_t fbm(std::uint64_t seed, std::int32_t x, std::int32_t z, int log2_largest, int octaves);

// fbm along a row of fixed z: at(x) gives exactly fbm(seed, x, z,
// log2_largest, octaves), but keeps each layer's lattice corners while x
// stays in the same cell, so walking a row costs a fraction of the hashing.
class FbmRow {
public:
    FbmRow(std::uint64_t seed, std::int32_t z, int log2_largest, int octaves);
    [[nodiscard]] std::int32_t at(std::int32_t x);

private:
    struct Octave {
        std::uint64_t seed = 0;
        int log2 = 0;
        std::int32_t iz = 0;
        std::int64_t fz = 0;
        std::int64_t weight = 0;
        bool ready = false;
        std::int32_t ix = 0;
        std::int64_t v00 = 0, v10 = 0, v01 = 0, v11 = 0;
    };
    // Enough for any cell size a shift allows.
    std::array<Octave, 32> octaves_{};
    int count_ = 0;
    std::int64_t weight_total_ = 0;
};

}  // namespace sc::sim
