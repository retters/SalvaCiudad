#include "sim/noise.h"

namespace sc::sim {

namespace {

// Smoothstep 3t^2 - 2t^3 on t in [0, 65536] (16 fractional bits).
std::int64_t smooth(std::int64_t t) {
    const std::int64_t t2 = (t * t) >> 16;
    return (t2 * (3 * 65536 - 2 * t)) >> 16;
}

}  // namespace

std::int32_t lattice_value(std::uint64_t seed, std::int32_t ix, std::int32_t iz) {
    const std::uint64_t key = mix64(seed ^ (static_cast<std::uint64_t>(static_cast<std::uint32_t>(ix)) << 32) ^
                                    static_cast<std::uint32_t>(iz));
    return static_cast<std::int32_t>(key >> 48) - 32768;
}

std::int32_t value_noise(std::uint64_t seed, std::int32_t x, std::int32_t z, int log2_cell) {
    const std::int32_t ix = x >> log2_cell;
    const std::int32_t iz = z >> log2_cell;
    const std::int32_t mask = (1 << log2_cell) - 1;
    // Position inside the cell with 16 fractional bits.
    const std::int64_t fx = smooth((static_cast<std::int64_t>(x & mask) << 16) >> log2_cell);
    const std::int64_t fz = smooth((static_cast<std::int64_t>(z & mask) << 16) >> log2_cell);
    const std::int64_t v00 = lattice_value(seed, ix, iz);
    const std::int64_t v10 = lattice_value(seed, ix + 1, iz);
    const std::int64_t v01 = lattice_value(seed, ix, iz + 1);
    const std::int64_t v11 = lattice_value(seed, ix + 1, iz + 1);
    const std::int64_t a = v00 + (((v10 - v00) * fx) >> 16);
    const std::int64_t b = v01 + (((v11 - v01) * fx) >> 16);
    return static_cast<std::int32_t>(a + (((b - a) * fz) >> 16));
}

std::int32_t fbm(std::uint64_t seed, std::int32_t x, std::int32_t z, int log2_largest, int octaves) {
    std::int64_t sum = 0;
    std::int64_t weight_total = 0;
    std::int64_t weight = 1 << 16;
    int layers = 0;
    for (int o = 0; o < octaves && log2_largest - o >= 0; ++o) {
        sum += value_noise(mix64(seed + static_cast<std::uint64_t>(o) * 0x9E3779B97F4A7C15ull), x, z,
                           log2_largest - o) * weight;
        weight_total += weight;
        weight >>= 1;
        ++layers;
    }
    if (weight_total == 0) {
        return 0;
    }
    // Phase 140: the dividers of 1 to 15 layers, worked out once.
    static const std::array<WeightDivider, 16> dividers = [] {
        std::array<WeightDivider, 16> out{WeightDivider(0), WeightDivider(1),  WeightDivider(2),  WeightDivider(3),
                                          WeightDivider(4), WeightDivider(5),  WeightDivider(6),  WeightDivider(7),
                                          WeightDivider(8), WeightDivider(9),  WeightDivider(10), WeightDivider(11),
                                          WeightDivider(12), WeightDivider(13), WeightDivider(14), WeightDivider(15)};
        return out;
    }();
    const std::int64_t quotient =
        layers < static_cast<int>(dividers.size()) ? dividers[static_cast<std::size_t>(layers)](sum) : sum / weight_total;
    // Sums of independent layers rarely reach the extremes; stretch by 3/2
    // and clamp so the range is used well.
    const std::int64_t v = quotient * 3 / 2;
    return static_cast<std::int32_t>(v > 32767 ? 32767 : (v < -32768 ? -32768 : v));
}

WeightDivider::WeightDivider(int octaves) {
    std::int64_t weight = 1 << 16;
    for (int o = 0; o < octaves && weight > 0; ++o) {
        total_ += weight;
        weight >>= 1;
    }
    if (octaves < 1 || octaves > 15 || weight == 0) {
        return;  // Not the case worked out below: plain division.
    }
    // total = (2^k - 1) * 2^(17 - k), and every weight is a multiple of
    // 2^(17 - k), so sum / total = (sum >> (17 - k)) / d with d = 2^k - 1
    // and |sum >> (17 - k)| < 2^(15 + k). For n < 2^N, n / d is (n * M) >>
    // (N + L) with L = ceil(log2 d) and M = ceil(2^(N + L) / d) (Granlund
    // and Montgomery); here N = 15 + k and L = k, so n * M < 2^(31 + 2k + 1),
    // which fits in 64 bits up to k = 15.
    const int k = octaves;
    const auto d = (std::uint64_t{1} << k) - 1;
    drop_ = 17 - k;
    shift_ = 15 + 2 * k;
    magic_ = ((std::uint64_t{1} << shift_) + d - 1) / d;
    exact_ = true;
}

FbmRow::FbmRow(std::uint64_t seed, std::int32_t z, int log2_largest, int octaves) {
    std::int64_t weight = 1 << 16;
    for (int o = 0; o < octaves && log2_largest - o >= 0 && count_ < static_cast<int>(octaves_.size()); ++o) {
        Octave& oc = octaves_[static_cast<std::size_t>(count_++)];
        oc.seed = mix64(seed + static_cast<std::uint64_t>(o) * 0x9E3779B97F4A7C15ull);
        oc.log2 = log2_largest - o;
        oc.iz = z >> oc.log2;
        const std::int32_t mask = (1 << oc.log2) - 1;
        oc.fz = smooth((static_cast<std::int64_t>(z & mask) << 16) >> oc.log2);
        oc.weight = weight;
        weight_total_ += weight;
        weight >>= 1;
    }
    divide_ = WeightDivider(count_);
}

std::int32_t FbmRow::at(std::int32_t x) {
    if (weight_total_ == 0) {
        return 0;
    }
    std::int64_t sum = 0;
    for (int k = 0; k < count_; ++k) {
        Octave& oc = octaves_[static_cast<std::size_t>(k)];
        const std::int32_t ix = x >> oc.log2;
        if (!oc.ready || ix != oc.ix) {
            oc.ready = true;
            oc.ix = ix;
            oc.v00 = lattice_value(oc.seed, ix, oc.iz);
            oc.v10 = lattice_value(oc.seed, ix + 1, oc.iz);
            oc.v01 = lattice_value(oc.seed, ix, oc.iz + 1);
            oc.v11 = lattice_value(oc.seed, ix + 1, oc.iz + 1);
        }
        const std::int32_t mask = (1 << oc.log2) - 1;
        const std::int64_t fx = smooth((static_cast<std::int64_t>(x & mask) << 16) >> oc.log2);
        const std::int64_t a = oc.v00 + (((oc.v10 - oc.v00) * fx) >> 16);
        const std::int64_t b = oc.v01 + (((oc.v11 - oc.v01) * fx) >> 16);
        sum += static_cast<std::int64_t>(static_cast<std::int32_t>(a + (((b - a) * oc.fz) >> 16))) * oc.weight;
    }
    const std::int64_t v = divide_(sum) * 3 / 2;
    return static_cast<std::int32_t>(v > 32767 ? 32767 : (v < -32768 ? -32768 : v));
}

}  // namespace sc::sim
