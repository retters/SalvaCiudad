#include "sim/worldgen.h"

#include <algorithm>
#include <functional>
#include <queue>
#include <utility>
#include <vector>

#include "sim/noise.h"
#include "sim/rng.h"

namespace sc::sim {

namespace {

using namespace worldgen;

// Seeds for each noise field, so they are unrelated to each other.
constexpr std::uint64_t kReliefSeed = 0x52454c4945460001ull;
constexpr std::uint64_t kBroadSeed = 0x42524f4144000002ull;
constexpr std::uint64_t kFertilitySeed = 0x4645525400000003ull;
constexpr std::uint64_t kRockSeed = 0x524f434b00000004ull;
constexpr std::uint64_t kClaySeed = 0x434c415900000005ull;
constexpr std::uint64_t kForestSeed = 0x464f524553540006ull;
constexpr std::uint64_t kPlacementSeed = 0x504c414345000008ull;
constexpr std::uint64_t kBiomeSeed = 0x42494f4d45000009ull;
constexpr std::uint64_t kBiomeWarpX = 0x5741525058000010ull;
constexpr std::uint64_t kBiomeWarpZ = 0x574152505a000011ull;
constexpr std::uint64_t kMountainSeed = 0x4d4f554e54000012ull;
constexpr std::uint64_t kMountainMaskSeed = 0x4d41534b00000013ull;
constexpr std::uint64_t kLakeWarpSeed = 0x4c414b4557000014ull;
constexpr std::uint64_t kBeachSeed = 0x4245414348000015ull;
constexpr std::uint64_t kIslandSeed = 0x49534c414e440016ull;
constexpr std::uint64_t kCoastSeed = 0x434f415354000017ull;
// Biomes are decided per block of this many cells.
constexpr std::int32_t kBiomeBlock = 4;

constexpr std::uint8_t kFlowBorder = 255;
constexpr std::uint8_t kUnvisited = 254;

// Per-amount multiplier in halves: Low 1x, Normal 2x, High 4x.
std::int64_t amount_factor(Amount a) {
    return a == Amount::Low ? 1 : (a == Amount::Normal ? 2 : 4);
}

// Land reaches up to this share (percent) of an island's radius, however
// its shoreline bends.
constexpr std::int32_t kIslandReach = 120;
// The island's slope under the sea reaches this far (percent of the radius).
constexpr std::int32_t kIslandSkirt = 144;
constexpr std::int32_t kIslandAngles = 1024;

// A position around a point, 0..1023 going once around, without
// trigonometry: 0 east (+x), 256 south (+z), 512 west, 768 north.
std::int32_t pseudo_angle(std::int64_t dx, std::int64_t dz) {
    const std::int64_t s = (dx < 0 ? -dx : dx) + (dz < 0 ? -dz : dz);
    if (s == 0) {
        return 0;
    }
    std::int64_t q = 0;
    if (dz >= 0) {
        q = dx >= 0 ? dz * 256 / s : 256 + (-dx) * 256 / s;
    } else {
        q = dx < 0 ? 512 + (-dz) * 256 / s : 768 + dx * 256 / s;
    }
    return static_cast<std::int32_t>(q) & (kIslandAngles - 1);
}

// How far an island's shoreline reaches in each direction: a smooth loop
// of values in [-32768, 32767], from three layers of value noise.
std::vector<std::int16_t> shoreline(std::uint64_t seed) {
    std::vector<std::int16_t> out(kIslandAngles);
    const auto layer = [&](std::int32_t points, std::uint64_t salt, std::int32_t q) {
        const std::int32_t pos = q * points;  // In 1/1024 of a point.
        const std::int32_t i = pos / kIslandAngles;
        const std::int64_t f = pos % kIslandAngles;
        const auto value = [&](std::int32_t k) {
            return static_cast<std::int64_t>(static_cast<std::int16_t>(mix64(seed ^ salt ^ static_cast<std::uint64_t>(k % points)) & 0xFFFF));
        };
        const std::int64_t a = value(i);
        const std::int64_t b = value(i + 1);
        const std::int64_t smooth = f * f * (3 * kIslandAngles - 2 * f) / (static_cast<std::int64_t>(kIslandAngles) * kIslandAngles);
        return a + (b - a) * smooth / kIslandAngles;
    };
    for (std::int32_t q = 0; q < kIslandAngles; ++q) {
        const std::int64_t v = (layer(6, 1, q) * 4 + layer(13, 2, q) * 2 + layer(29, 3, q)) / 7;
        out[static_cast<std::size_t>(q)] = static_cast<std::int16_t>(std::clamp<std::int64_t>(v, -32768, 32767));
    }
    return out;
}

class Generator {
public:
    Generator(const MapSettings& s, const Content& content, const GenProgress& progress)
        : s_(s), flora_(content.flora), progress_(progress), n_(map_cells(s.size)), v_(n_ + 1), rng_(s.seed, 7) {}

    std::optional<MapData> run() {
        out_.settings = s_;
        out_.size = n_;
        out_.generator_version = kGeneratorVersion;
        if (const MapTypeDef* type = map_type(); type != nullptr && type->islands) {
            islands_ = island_layout(s_.seed, n_, std::clamp<std::int32_t>(s_.players, 1, 12),
                                     std::min<std::int32_t>(s_.islands, max_islands_per_town(s_.size, s_.players)));
        }
        if (!relief() || !lakes() || !rivers() || !soil() || !biomes() || !forests() || !resources() || !starts()) {
            return std::nullopt;
        }
        finish();
        return std::move(out_);
    }

private:
    // --- Helpers -------------------------------------------------------------

    [[nodiscard]] std::size_t vi(std::int32_t x, std::int32_t z) const {
        return static_cast<std::size_t>(z) * static_cast<std::size_t>(v_) + static_cast<std::size_t>(x);
    }
    [[nodiscard]] std::size_t ci(std::int32_t x, std::int32_t z) const {
        return static_cast<std::size_t>(z) * static_cast<std::size_t>(n_) + static_cast<std::size_t>(x);
    }
    // How many things to place for a density given in tenths per km².
    [[nodiscard]] std::int32_t per_area(std::int64_t tenths_per_km2) const {
        const std::int64_t area = static_cast<std::int64_t>(n_) * n_;
        return static_cast<std::int32_t>(std::max<std::int64_t>(1, (area * tenths_per_km2 + 5'000'000) / 10'000'000));
    }
    bool report(GenStage stage, int percent) {
        return !progress_ || progress_(stage, percent);
    }
    [[nodiscard]] std::uint64_t point_hash(std::uint64_t salt, std::int32_t x, std::int32_t z) const {
        return mix64(s_.seed ^ salt ^ (static_cast<std::uint64_t>(static_cast<std::uint32_t>(x)) << 32) ^
                     static_cast<std::uint32_t>(z));
    }
    [[nodiscard]] Terrain cell_terrain(std::int32_t cx, std::int32_t cz) const {
        return static_cast<Terrain>(terrain_[ci(cx, cz)]);
    }
    [[nodiscard]] bool land(std::int32_t cx, std::int32_t cz) const {
        if (cx < 1 || cz < 1 || cx >= n_ - 1 || cz >= n_ - 1) {
            return false;
        }
        const Terrain t = cell_terrain(cx, cz);
        return t != Terrain::Water;
    }
    [[nodiscard]] std::int32_t cell_slope(std::int32_t cx, std::int32_t cz) const {
        const std::int32_t a = h_[vi(cx, cz)], b = h_[vi(cx + 1, cz)], c = h_[vi(cx, cz + 1)], d = h_[vi(cx + 1, cz + 1)];
        return std::max({a, b, c, d}) - std::min({a, b, c, d});
    }
    void add_feature(FeatureType type, Fixed x, Fixed z, Fixed scale, std::uint16_t rotation) {
        MapFeature f;
        f.type = type;
        f.x = x;
        f.z = z;
        f.scale = scale;
        f.rotation = rotation;
        out_.features.push_back(f);
    }
    [[nodiscard]] Fixed cell_center(std::int32_t c) const {
        return Fixed::from_raw(c * Fixed::kOneRaw + Fixed::kOneRaw / 2);
    }

    // --- Relief ----------------------------------------------------------------

    bool relief() {
        h_.assign(static_cast<std::size_t>(v_) * static_cast<std::size_t>(v_), 0);
        lake_cut_.assign(h_.size(), 0);
        const std::int64_t amp = s_.relief == Relief::Low ? 5000 : (s_.relief == Relief::Gentle ? 10000 : 12000);  // mm
        const bool mountains = s_.relief == Relief::Mountainous;
        for (std::int32_t z = 0; z < v_; ++z) {
            for (std::int32_t x = 0; x < v_; ++x) {
                const std::int64_t detail = fbm(s_.seed ^ kReliefSeed, x, z, 10, 6);
                const std::int64_t broad = fbm(s_.seed ^ kBroadSeed, x, z, 11, 1);
                std::int64_t h = 20000 + detail * amp / 32768 + broad * amp / 65536;
                if (mountains) {
                    // Ranges in broad regions: sharp ridges where a noise
                    // field crosses zero, up to about 90 m high.
                    const std::int64_t mask = fbm(s_.seed ^ kMountainMaskSeed, x, z, 10, 2);
                    const std::int64_t ramp = std::clamp<std::int64_t>((mask + 2000) * 65536 / 12000, 0, 65536);
                    if (ramp > 0) {
                        const std::int64_t n = fbm(s_.seed ^ kMountainSeed, x, z, 9, 5);
                        const std::int64_t ridge = 32768 - (n < 0 ? -n : n);  // 32768 where n crosses zero.
                        const std::int64_t crest = std::max<std::int64_t>(0, ridge - 20000) * 32768 / 12768;
                        const std::int64_t sharp = (crest * crest) >> 15;
                        h += (ramp * sharp * 90000) >> 31;
                    }
                }
                h_[vi(x, z)] = static_cast<std::int32_t>(h);
            }
            if ((z & 63) == 0 && !report(GenStage::Relief, z * (islands_.empty() ? 90 : 60) / v_)) {
                return false;
            }
        }
        if (!islands_.empty() && !shape_islands(amp)) {
            return false;
        }
        // Basins that will hold lakes.
        const std::int32_t lakes = per_area(4 * amount_factor(s_.water));
        const std::int32_t margin = n_ / 10;
        for (std::int32_t i = 0; i < lakes; ++i) {
            const std::int32_t cx = rng_.range(margin, n_ - margin);
            const std::int32_t cz = rng_.range(margin, n_ - margin);
            const std::int32_t r = rng_.range(35, 110);
            const std::int64_t depth = rng_.range(2500, 5000);
            // One to three overlapping lobes, each with a shoreline bent by
            // noise: irregular lakes with bays and points.
            const std::int32_t lobes = rng_.range(1, 3);
            for (std::int32_t lobe = 0; lobe < lobes; ++lobe) {
                const std::int32_t lx = lobe == 0 ? cx : cx + rng_.range(-r * 7 / 10, r * 7 / 10);
                const std::int32_t lz = lobe == 0 ? cz : cz + rng_.range(-r * 7 / 10, r * 7 / 10);
                const std::int32_t lr = lobe == 0 ? r : r * rng_.range(45, 85) / 100;
                const std::int64_t lr2 = static_cast<std::int64_t>(lr) * lr;
                const std::int32_t reach = lr * 3 / 2;
                for (std::int32_t z = std::max(0, lz - reach); z <= std::min(v_ - 1, lz + reach); ++z) {
                    for (std::int32_t x = std::max(0, lx - reach); x <= std::min(v_ - 1, lx + reach); ++x) {
                        const std::int64_t d2 = static_cast<std::int64_t>(x - lx) * (x - lx) + static_cast<std::int64_t>(z - lz) * (z - lz);
                        // The warp stretches or shrinks the distance by up to 45 %.
                        const std::int64_t warp = fbm(s_.seed ^ kLakeWarpSeed, x, z, 5, 3);
                        const std::int64_t t = d2 * 65536 / lr2 * (65536 + warp * 29491 / 32768) / 65536;
                        if (t < 65536) {
                            const std::int64_t w = ((65536 - t) * (65536 - t)) >> 16;
                            const std::int64_t cut = (depth * w) >> 16;
                            // Overlapping lobes deepen to the deepest, not the sum.
                            lake_cut_[vi(x, z)] = static_cast<std::int32_t>(std::max<std::int64_t>(lake_cut_[vi(x, z)], cut));
                        }
                    }
                }
            }
        }
        for (std::size_t k = 0; k < h_.size(); ++k) {
            h_[k] -= lake_cut_[k];
        }
        lake_cut_.clear();
        lake_cut_.shrink_to_fit();
        for (std::int32_t& v : h_) {
            v = std::max(v, 1000);
        }
        if (!islands_.empty()) {
            sink_strays();
        }
        return report(GenStage::Relief, 100);
    }

    // --- Islands (phase 22) ------------------------------------------------------

    // Raises the islands out of the sea: land keeps the relief it had, the
    // rest drops to the sea floor, with a sloping shore between them.
    bool shape_islands(std::int64_t amp) {
        std::vector<std::vector<std::int16_t>> shores;
        shores.reserve(islands_.size());
        for (std::size_t i = 0; i < islands_.size(); ++i) {
            shores.push_back(shoreline(s_.seed ^ kCoastSeed ^ (static_cast<std::uint64_t>(i) << 40)));
        }
        // Islands by blocks of the map, to test only the nearby ones.
        constexpr std::int32_t kBlock = 256;
        const std::int32_t blocks = (v_ + kBlock - 1) / kBlock;
        std::vector<std::vector<std::uint16_t>> near(static_cast<std::size_t>(blocks) * static_cast<std::size_t>(blocks));
        for (std::size_t i = 0; i < islands_.size(); ++i) {
            const Island& is = islands_[i];
            const std::int32_t reach = is.radius * kIslandSkirt / 100 + 1;
            for (std::int32_t bz = std::max(0, (is.z - reach) / kBlock); bz <= std::min(blocks - 1, (is.z + reach) / kBlock); ++bz) {
                for (std::int32_t bx = std::max(0, (is.x - reach) / kBlock); bx <= std::min(blocks - 1, (is.x + reach) / kBlock);
                     ++bx) {
                    near[static_cast<std::size_t>(bz * blocks + bx)].push_back(static_cast<std::uint16_t>(i));
                }
            }
        }
        const std::int64_t spread = amp * 3 / 2;  // How far the relief goes below its middle.
        for (std::int32_t z = 0; z < v_; ++z) {
            for (std::int32_t x = 0; x < v_; ++x) {
                // How far into the nearest island, as squared distance over
                // squared radius (65536 = the shore).
                std::int64_t t = INT64_MAX;
                for (const std::uint16_t i : near[static_cast<std::size_t>((z / kBlock) * blocks + x / kBlock)]) {
                    const Island& is = islands_[i];
                    const std::int64_t dx = x - is.x;
                    const std::int64_t dz = z - is.z;
                    const std::int64_t r2 = static_cast<std::int64_t>(is.radius) * is.radius;
                    const std::int64_t d2 = dx * dx + dz * dz;
                    if (d2 * 10000 >= r2 * kIslandSkirt * kIslandSkirt) {
                        continue;
                    }
                    // The shoreline bends the distance by up to 30 %, by
                    // direction only, so every island is one piece.
                    const std::int64_t warp = shores[i][static_cast<std::size_t>(pseudo_angle(dx, dz))];
                    t = std::min(t, d2 * 65536 / r2 * (65536 + warp * 19661 / 32768) / 65536);
                }
                const auto smooth = [](std::int64_t u) { return (((u * u) >> 16) * (3 * 65536 - 2 * u)) >> 16; };
                const std::int64_t rel = h_[vi(x, z)] - 20000;
                const std::int64_t sea = std::clamp<std::int64_t>(kSeaLevelMm - 6000 + rel / 8, kSeaLevelMm - 9000,
                                                                  kSeaLevelMm - 2000);
                const std::int64_t top = kSeaLevelMm + 800 + std::max<std::int64_t>(0, rel + spread) / 2;
                std::int64_t h = sea;
                if (t < 65536) {
                    // Land: from a beach just above the sea, up gently over
                    // the outer 70 % to the island's own relief.
                    const std::int64_t u = std::min<std::int64_t>(65536, (65536 - t) * 65536 / 45875);
                    h = kSeaLevelMm + 100 + (((top - kSeaLevelMm - 100) * smooth(u)) >> 16);
                } else if (t < 65536 * 144 / 100) {
                    // Under the sea: down to the sea floor.
                    const std::int64_t u = (t - 65536) * 65536 / (65536 * 44 / 100);
                    h = kSeaLevelMm - 100 - (((kSeaLevelMm - 100 - sea) * smooth(u)) >> 16);
                }
                h_[vi(x, z)] = static_cast<std::int32_t>(h);
            }
            if ((z & 63) == 0 && !report(GenStage::Relief, 60 + z * 30 / v_)) {
                return false;
            }
        }
        return true;
    }

    // Land cut off from its island (by a lake at the shore, say) sinks, so
    // the map has exactly the islands it was asked for.
    void sink_strays() {
        std::vector<std::uint8_t> kept(h_.size(), 0);
        std::vector<std::uint32_t> queue;
        const auto keep = [&](std::int32_t x, std::int32_t z) {
            if (x < 0 || z < 0 || x >= v_ || z >= v_) {
                return;
            }
            const std::size_t v = vi(x, z);
            if (kept[v] == 0 && h_[v] >= kSeaLevelMm) {
                kept[v] = 1;
                queue.push_back(static_cast<std::uint32_t>(v));
            }
        };
        // Each island is the land around its middle.
        for (const Island& is : islands_) {
            const std::int32_t r = std::max(1, is.radius / 3);
            for (std::int32_t z = is.z - r; z <= is.z + r; ++z) {
                for (std::int32_t x = is.x - r; x <= is.x + r; ++x) {
                    keep(x, z);
                }
            }
        }
        for (std::size_t q = 0; q < queue.size(); ++q) {
            const std::int32_t x = static_cast<std::int32_t>(queue[q] % static_cast<std::uint32_t>(v_));
            const std::int32_t z = static_cast<std::int32_t>(queue[q] / static_cast<std::uint32_t>(v_));
            keep(x - 1, z);
            keep(x + 1, z);
            keep(x, z - 1);
            keep(x, z + 1);
        }
        for (std::size_t v = 0; v < h_.size(); ++v) {
            if (kept[v] == 0 && h_[v] >= kSeaLevelMm) {
                h_[v] = kSeaLevelMm - 1000;
            }
        }
    }

    // The sea: everything below its level that reaches the map's edge. It
    // ends rivers like a lake does.
    void flood_sea() {
        std::vector<std::uint8_t> sea(h_.size(), 0);
        std::vector<std::uint32_t> queue;
        const auto reach = [&](std::int32_t x, std::int32_t z) {
            if (x < 0 || z < 0 || x >= v_ || z >= v_) {
                return;
            }
            const std::size_t v = vi(x, z);
            if (sea[v] == 0 && h_[v] < kSeaLevelMm) {
                sea[v] = 1;
                queue.push_back(static_cast<std::uint32_t>(v));
            }
        };
        for (std::int32_t i = 0; i < v_; ++i) {
            reach(i, 0);
            reach(i, v_ - 1);
            reach(0, i);
            reach(v_ - 1, i);
        }
        for (std::size_t q = 0; q < queue.size(); ++q) {
            const std::int32_t x = static_cast<std::int32_t>(queue[q] % static_cast<std::uint32_t>(v_));
            const std::int32_t z = static_cast<std::int32_t>(queue[q] / static_cast<std::uint32_t>(v_));
            reach(x - 1, z);
            reach(x + 1, z);
            reach(x, z - 1);
            reach(x, z + 1);
        }
        for (std::size_t v = 0; v < h_.size(); ++v) {
            if (sea[v] != 0) {
                lake_[v] = 1;
            }
        }
        for (std::int32_t z = 0; z < n_; ++z) {
            for (std::int32_t x = 0; x < n_; ++x) {
                const std::size_t corners[4] = {vi(x, z), vi(x + 1, z), vi(x, z + 1), vi(x + 1, z + 1)};
                bool wet = false;
                std::int32_t lowest = INT32_MAX;
                for (const std::size_t c : corners) {
                    wet = wet || sea[c] != 0;
                    lowest = std::min(lowest, h_[c]);
                }
                if (wet && lowest + 10 <= kSeaLevelMm) {
                    water_[ci(x, z)] = std::max(water_[ci(x, z)], kSeaLevelMm);
                    terrain_[ci(x, z)] = static_cast<std::uint8_t>(Terrain::Water);
                }
            }
        }
    }

    // --- Lakes: fill depressions from the border (priority flood) -----------

    bool lakes() {
        const std::size_t count = h_.size();
        filled_ = h_;
        flow_.assign(count, kUnvisited);
        // Min-heap on (height, index): the index breaks ties deterministically.
        std::priority_queue<std::uint64_t, std::vector<std::uint64_t>, std::greater<>> open;
        const auto push = [&](std::size_t i) {
            open.push((static_cast<std::uint64_t>(static_cast<std::uint32_t>(filled_[i])) << 32) | i);
        };
        for (std::int32_t i = 0; i < v_; ++i) {
            for (const std::size_t b : {vi(i, 0), vi(i, v_ - 1), vi(0, i), vi(v_ - 1, i)}) {
                if (flow_[b] == kUnvisited) {
                    flow_[b] = kFlowBorder;
                    push(b);
                }
            }
        }
        std::size_t done = 0;
        while (!open.empty()) {
            const std::uint64_t key = open.top();
            open.pop();
            const std::size_t idx = static_cast<std::size_t>(key & 0xFFFFFFFFu);
            const std::int32_t x = static_cast<std::int32_t>(idx % static_cast<std::size_t>(v_));
            const std::int32_t z = static_cast<std::int32_t>(idx / static_cast<std::size_t>(v_));
            // Neighbor offset and the flow code that points back to idx.
            const std::int32_t nx[4] = {x - 1, x + 1, x, x};
            const std::int32_t nz[4] = {z, z, z - 1, z + 1};
            const std::uint8_t back[4] = {1, 0, 3, 2};
            for (int k = 0; k < 4; ++k) {
                if (nx[k] < 0 || nz[k] < 0 || nx[k] >= v_ || nz[k] >= v_) {
                    continue;
                }
                const std::size_t n = vi(nx[k], nz[k]);
                if (flow_[n] != kUnvisited) {
                    continue;
                }
                filled_[n] = std::max(h_[n], filled_[idx]);
                flow_[n] = back[k];
                push(n);
            }
            if ((++done & 0xFFFFF) == 0 && !report(GenStage::Lakes, static_cast<int>(done * 70 / count))) {
                return false;
            }
        }

        // Deep, wide depressions become lakes; small puddles are filled in.
        lake_.assign(count, 0);
        std::vector<std::uint8_t> seen(count, 0);
        std::vector<std::uint32_t> component;
        for (std::size_t start = 0; start < count; ++start) {
            if (seen[start] != 0 || filled_[start] <= h_[start]) {
                continue;
            }
            component.clear();
            component.push_back(static_cast<std::uint32_t>(start));
            seen[start] = 1;
            std::int32_t max_depth = 0;
            for (std::size_t q = 0; q < component.size(); ++q) {
                const std::size_t idx = component[q];
                max_depth = std::max(max_depth, filled_[idx] - h_[idx]);
                const std::int32_t x = static_cast<std::int32_t>(idx % static_cast<std::size_t>(v_));
                const std::int32_t z = static_cast<std::int32_t>(idx / static_cast<std::size_t>(v_));
                const std::int32_t nx[4] = {x - 1, x + 1, x, x};
                const std::int32_t nz[4] = {z, z, z - 1, z + 1};
                for (int k = 0; k < 4; ++k) {
                    if (nx[k] < 0 || nz[k] < 0 || nx[k] >= v_ || nz[k] >= v_) {
                        continue;
                    }
                    const std::size_t n = vi(nx[k], nz[k]);
                    if (seen[n] == 0 && filled_[n] > h_[n]) {
                        seen[n] = 1;
                        component.push_back(static_cast<std::uint32_t>(n));
                    }
                }
            }
            const bool is_lake = max_depth >= 700 && component.size() >= 150;
            for (const std::uint32_t idx : component) {
                if (is_lake) {
                    lake_[idx] = 1;
                } else {
                    h_[idx] = filled_[idx];
                }
            }
        }

        terrain_.assign(static_cast<std::size_t>(n_) * static_cast<std::size_t>(n_), static_cast<std::uint8_t>(Terrain::Grass));
        water_.assign(terrain_.size(), 0);
        for (std::int32_t z = 0; z < n_; ++z) {
            for (std::int32_t x = 0; x < n_; ++x) {
                const std::size_t corners[4] = {vi(x, z), vi(x + 1, z), vi(x, z + 1), vi(x + 1, z + 1)};
                std::int32_t level = 0;
                std::int32_t lowest = INT32_MAX;
                for (const std::size_t c : corners) {
                    if (lake_[c] != 0) {
                        level = std::max(level, filled_[c]);
                    }
                    lowest = std::min(lowest, h_[c]);
                }
                // At least 1 cm of water, so it survives rounding to cm.
                if (level > 0 && lowest + 10 <= level) {
                    water_[ci(x, z)] = level;
                    terrain_[ci(x, z)] = static_cast<std::uint8_t>(Terrain::Water);
                }
            }
        }
        if (!islands_.empty()) {
            flood_sea();
        }
        return report(GenStage::Lakes, 100);
    }

    // --- Rivers: follow the flow to the border or a lake ---------------------

    bool rivers() {
        bed_.assign(h_.size(), 0);
        const std::int32_t wanted = per_area(5 * amount_factor(s_.water));
        const std::int32_t margin = n_ / 10;
        struct Candidate {
            std::int32_t height;
            std::size_t index;
        };
        std::vector<Candidate> candidates;
        for (std::int32_t i = 0; i < wanted * 12; ++i) {
            const std::int32_t x = rng_.range(margin, v_ - 1 - margin);
            const std::int32_t z = rng_.range(margin, v_ - 1 - margin);
            const std::size_t idx = vi(x, z);
            if (lake_[idx] == 0) {
                candidates.push_back({filled_[idx], idx});
            }
        }
        // Highest first; ties by index.
        std::sort(candidates.begin(), candidates.end(), [](const Candidate& a, const Candidate& b) {
            return a.height != b.height ? a.height > b.height : a.index < b.index;
        });
        std::vector<std::size_t> sources;
        std::int64_t spacing = n_ / 5;
        while (static_cast<std::int32_t>(sources.size()) < wanted && spacing > 8) {
            for (const Candidate& c : candidates) {
                if (static_cast<std::int32_t>(sources.size()) >= wanted) {
                    break;
                }
                const std::int64_t cx = static_cast<std::int64_t>(c.index % static_cast<std::size_t>(v_));
                const std::int64_t cz = static_cast<std::int64_t>(c.index / static_cast<std::size_t>(v_));
                bool far = true;
                for (const std::size_t s : sources) {
                    const std::int64_t sx = static_cast<std::int64_t>(s % static_cast<std::size_t>(v_));
                    const std::int64_t sz = static_cast<std::int64_t>(s / static_cast<std::size_t>(v_));
                    if ((sx - cx) * (sx - cx) + (sz - cz) * (sz - cz) < spacing * spacing) {
                        far = false;
                        break;
                    }
                }
                if (far && std::find(sources.begin(), sources.end(), c.index) == sources.end()) {
                    sources.push_back(c.index);
                }
            }
            spacing = spacing * 3 / 4;
        }

        std::vector<std::size_t> path;
        for (std::size_t r = 0; r < sources.size(); ++r) {
            path.clear();
            std::size_t idx = sources[r];
            // Following the flow always ends at the border or in a lake.
            for (std::size_t steps = 0; steps < h_.size(); ++steps) {
                path.push_back(idx);
                if (flow_[idx] == kFlowBorder || lake_[idx] != 0) {
                    break;
                }
                const std::int32_t x = static_cast<std::int32_t>(idx % static_cast<std::size_t>(v_));
                const std::int32_t z = static_cast<std::int32_t>(idx / static_cast<std::size_t>(v_));
                switch (flow_[idx]) {
                    case 0: idx = vi(x - 1, z); break;
                    case 1: idx = vi(x + 1, z); break;
                    case 2: idx = vi(x, z - 1); break;
                    default: idx = vi(x, z + 1); break;
                }
            }
            carve(path);
            if (!report(GenStage::Rivers, static_cast<int>((r + 1) * 100 / std::max<std::size_t>(1, sources.size())))) {
                return false;
            }
        }
        return report(GenStage::Rivers, 100);
    }

    void carve(const std::vector<std::size_t>& path) {
        const std::int64_t length = static_cast<std::int64_t>(path.size());
        std::int32_t level = INT32_MAX;
        for (std::int64_t i = 0; i < length; ++i) {
            const std::size_t idx = path[static_cast<std::size_t>(i)];
            if (lake_[idx] != 0) {
                break;
            }
            // The water surface never rises going downstream.
            level = std::min(level, filled_[idx] - 300);
            // Rivers widen downstream: from about 5 m to 11 m.
            const std::int32_t radius = 2 + static_cast<std::int32_t>(4 * i / std::max<std::int64_t>(1, length));
            const std::int32_t px = static_cast<std::int32_t>(idx % static_cast<std::size_t>(v_));
            const std::int32_t pz = static_cast<std::int32_t>(idx / static_cast<std::size_t>(v_));
            const std::int32_t reach = radius + 2;
            for (std::int32_t z = std::max(0, pz - reach); z <= std::min(v_ - 1, pz + reach); ++z) {
                for (std::int32_t x = std::max(0, px - reach); x <= std::min(v_ - 1, px + reach); ++x) {
                    const std::int64_t d2 = static_cast<std::int64_t>(x - px) * (x - px) + static_cast<std::int64_t>(z - pz) * (z - pz);
                    const std::int32_t d = static_cast<std::int32_t>(isqrt(static_cast<std::uint64_t>(d2)));
                    const std::size_t v = vi(x, z);
                    if (d <= radius) {
                        // 90 cm deep in the middle, 15 cm at the edge of the bed.
                        h_[v] = std::min(h_[v], level - 150 - 750 * (radius - d) / std::max(1, radius));
                        bed_[v] = 1;
                    } else if (d <= reach && bed_[v] == 0 && lake_[v] == 0) {
                        // Banks slope down toward the water, never below it;
                        // a bed dug by an earlier step of a river, or a lake
                        // shore, stays as it is.
                        h_[v] = std::max(level + 100, std::min(h_[v], level + 150 * (d - radius) + 100));
                    }
                    if (d <= radius && x < n_ && z < n_) {
                        const std::size_t c = ci(x, z);
                        if (water_[c] == 0 || terrain_[c] != static_cast<std::uint8_t>(Terrain::Water)) {
                            water_[c] = level;
                        } else {
                            water_[c] = std::max(water_[c], level);
                        }
                        terrain_[c] = static_cast<std::uint8_t>(Terrain::Water);
                    }
                }
            }
        }
    }

    // --- Soil: moisture, fertility and ground types ---------------------------

    bool soil() {
        const std::size_t cells = terrain_.size();
        // Distance to water in meters (4-neighbor steps), capped at 255.
        dist_.assign(cells, 255);
        std::vector<std::uint32_t> queue;
        for (std::size_t c = 0; c < cells; ++c) {
            if (water_[c] != 0) {
                dist_[c] = 0;
                queue.push_back(static_cast<std::uint32_t>(c));
            }
        }
        for (std::size_t q = 0; q < queue.size(); ++q) {
            const std::size_t c = queue[q];
            const std::uint8_t d = dist_[c];
            if (d >= 254) {
                continue;
            }
            const std::int32_t x = static_cast<std::int32_t>(c % static_cast<std::size_t>(n_));
            const std::int32_t z = static_cast<std::int32_t>(c / static_cast<std::size_t>(n_));
            const std::int32_t nx[4] = {x - 1, x + 1, x, x};
            const std::int32_t nz[4] = {z, z, z - 1, z + 1};
            for (int k = 0; k < 4; ++k) {
                if (nx[k] < 0 || nz[k] < 0 || nx[k] >= n_ || nz[k] >= n_) {
                    continue;
                }
                const std::size_t n = ci(nx[k], nz[k]);
                if (dist_[n] > d + 1) {
                    dist_[n] = static_cast<std::uint8_t>(d + 1);
                    queue.push_back(static_cast<std::uint32_t>(n));
                }
            }
        }
        if (!report(GenStage::Soil, 20)) {
            return false;
        }

        fertility_.assign(cells, 0);
        forest_.assign(cells, 0);
        const std::int32_t forest_threshold = s_.forests == Amount::Low ? 9000 : (s_.forests == Amount::Normal ? 3500 : -2000);
        for (std::int32_t z = 0; z < n_; ++z) {
            for (std::int32_t x = 0; x < n_; ++x) {
                const std::size_t c = ci(x, z);
                if (terrain_[c] == static_cast<std::uint8_t>(Terrain::Water)) {
                    continue;
                }
                const std::int32_t d = dist_[c];
                const std::int32_t slope = cell_slope(x, z);
                std::int32_t fert = 110 + fbm(s_.seed ^ kFertilitySeed, x, z, 8, 4) * 60 / 32768;
                if (d <= 40) {
                    fert += (40 - d) * 2;
                }
                if (slope > 150) {
                    fert -= (slope - 150) / 4;
                }
                Terrain t = Terrain::Grass;
                const std::int32_t rock_noise = fbm(s_.seed ^ kRockSeed, x, z, 7, 3);
                if (slope > 450 || (rock_noise > 21000 && slope > 120) || rock_noise > 26000) {
                    t = Terrain::Rock;
                    fert = 0;
                } else if (d <= 2 + std::max<std::int32_t>(0, fbm(s_.seed ^ kBeachSeed, x, z, 6, 2)) * 6 / 32768 &&
                           slope <= 250) {
                    // Beaches of 2 to 8 m, where the shore is not steep.
                    t = Terrain::Sand;
                    fert = std::min(fert, 60);
                } else if (d <= 30 && fbm(s_.seed ^ kClaySeed, x, z, 6, 2) > 17000) {
                    t = Terrain::Clay;
                    fert = std::min(fert, 90);
                } else {
                    std::int32_t mask = fbm(s_.seed ^ kForestSeed, x, z, 8, 4);
                    if (d < 60) {
                        mask += (60 - d) * 100;
                    }
                    if (mask > forest_threshold) {
                        t = Terrain::ForestFloor;
                        forest_[c] = static_cast<std::uint8_t>(std::min(255, (mask - forest_threshold) / 64 + 1));
                    } else if (fert > 150) {
                        t = Terrain::Meadow;
                    }
                }
                terrain_[c] = static_cast<std::uint8_t>(t);
                fertility_[c] = static_cast<std::uint8_t>(std::clamp(fert, 0, 255));
            }
            if ((z & 63) == 0 && !report(GenStage::Soil, 20 + z * 80 / n_)) {
                return false;
            }
        }
        return report(GenStage::Soil, 100);
    }

    // --- Biomes ----------------------------------------------------------------

    // Regions around jittered points, one every `patch_m` meters, with
    // edges bent by noise; each region takes a biome from the map type.
    bool biomes() {
        const std::size_t cells = terrain_.size();
        const std::uint8_t only = s_.biome < flora_.biomes.size() ? s_.biome : 0;
        biome_.assign(cells, only);
        const MapTypeDef* type_ptr = map_type();
        if (type_ptr == nullptr || type_ptr->biomes.empty() || type_ptr->patch_m <= 0) {
            return report(GenStage::Biomes, 100);
        }
        const MapTypeDef& type = *type_ptr;
        const std::int32_t p = type.patch_m;
        const std::int32_t warp = p / 3;
        for (std::int32_t bz = 0; bz < n_; bz += kBiomeBlock) {
            for (std::int32_t bx = 0; bx < n_; bx += kBiomeBlock) {
                const std::int32_t wx = bx + static_cast<std::int32_t>(fbm(s_.seed ^ kBiomeWarpX, bx, bz, 8, 3) * warp / 32768);
                const std::int32_t wz = bz + static_cast<std::int32_t>(fbm(s_.seed ^ kBiomeWarpZ, bx, bz, 8, 3) * warp / 32768);
                const std::int32_t gx = (wx < 0 ? wx - p + 1 : wx) / p;
                const std::int32_t gz = (wz < 0 ? wz - p + 1 : wz) / p;
                std::int64_t best = INT64_MAX;
                std::uint64_t best_hash = 0;
                for (std::int32_t oz = -1; oz <= 1; ++oz) {
                    for (std::int32_t ox = -1; ox <= 1; ++ox) {
                        const std::uint64_t h = point_hash(kBiomeSeed, gx + ox, gz + oz);
                        const std::int64_t px = static_cast<std::int64_t>(gx + ox) * p + static_cast<std::int64_t>(h % static_cast<std::uint64_t>(p));
                        const std::int64_t pz = static_cast<std::int64_t>(gz + oz) * p +
                                                static_cast<std::int64_t>((h >> 20) % static_cast<std::uint64_t>(p));
                        const std::int64_t d = (px - wx) * (px - wx) + (pz - wz) * (pz - wz);
                        if (d < best) {
                            best = d;
                            best_hash = h;
                        }
                    }
                }
                const std::uint8_t b = pick_weighted(type.biomes, static_cast<std::uint32_t>(best_hash >> 40));
                for (std::int32_t z = bz; z < std::min(n_, bz + kBiomeBlock); ++z) {
                    for (std::int32_t x = bx; x < std::min(n_, bx + kBiomeBlock); ++x) {
                        biome_[ci(x, z)] = b;
                    }
                }
            }
            if ((bz & 127) == 0 && !report(GenStage::Biomes, bz * 100 / n_)) {
                return false;
            }
        }
        return report(GenStage::Biomes, 100);
    }

    // --- Forests -------------------------------------------------------------

    // Trunks keep apart by their size: each tree reserves a disc of half its
    // spacing, and a new tree needs its own disc free.
    [[nodiscard]] bool room_for(std::int32_t cx, std::int32_t cz, std::int32_t radius) const {
        for (std::int32_t z = std::max(0, cz - radius); z <= std::min(n_ - 1, cz + radius); ++z) {
            for (std::int32_t x = std::max(0, cx - radius); x <= std::min(n_ - 1, cx + radius); ++x) {
                if ((x - cx) * (x - cx) + (z - cz) * (z - cz) <= radius * radius && taken_[ci(x, z)] != 0) {
                    return false;
                }
            }
        }
        return true;
    }
    void reserve(std::int32_t cx, std::int32_t cz, std::int32_t radius) {
        for (std::int32_t z = std::max(0, cz - radius); z <= std::min(n_ - 1, cz + radius); ++z) {
            for (std::int32_t x = std::max(0, cx - radius); x <= std::min(n_ - 1, cx + radius); ++x) {
                if ((x - cx) * (x - cx) + (z - cz) * (z - cz) <= radius * radius) {
                    taken_[ci(x, z)] = 1;
                }
            }
        }
    }
    [[nodiscard]] static std::int32_t tree_radius(TreeSize size) {
        return std::max<std::int32_t>(1, size_info(size).spacing_m / 2);
    }

    // Places a tree if there is room; `hash` gives its height and rotation.
    [[nodiscard]] const MapTypeDef* map_type() const {
        if (flora_.map_types.empty()) {
            return nullptr;
        }
        return &flora_.map_types[s_.map_type < flora_.map_types.size() ? s_.map_type : 0];
    }

    bool plant(Fixed x, Fixed z, std::uint8_t species, TreeSize size, std::uint64_t hash) {
        const std::int32_t cx = x.floor_int();
        const std::int32_t cz = z.floor_int();
        if (!land(cx, cz) || !room_for(cx, cz, tree_radius(size))) {
            return false;
        }
        reserve(cx, cz, tree_radius(size));
        const SizeInfo& si = size_info(size);
        const std::int64_t height = si.min_cm + static_cast<std::int64_t>((hash >> 44) % static_cast<std::uint64_t>(si.max_cm - si.min_cm + 1));
        MapFeature f;
        f.type = FeatureType::Tree;
        f.species = species;
        f.size = static_cast<std::uint8_t>(size);
        f.x = x;
        f.z = z;
        f.scale = Fixed::from_ratio(height, si.model_cm);
        f.rotation = static_cast<std::uint16_t>(hash >> 28);
        out_.features.push_back(f);
        return true;
    }

    bool forests() {
        taken_.assign(terrain_.size(), 0);
        const MapTypeDef* type_ptr = map_type();
        if (type_ptr == nullptr || flora_.biomes.empty() || flora_.species.empty()) {
            return report(GenStage::Forests, 100);
        }
        const MapTypeDef& type = *type_ptr;
        // Biggest first; smaller trees fill the gaps.
        for (int pass = static_cast<int>(kTreeSizes) - 1; pass >= 0; --pass) {
            const auto size = static_cast<TreeSize>(pass);
            const std::int32_t step = size_info(size).spacing_m;
            for (std::int32_t gz = 0; gz < n_; gz += step) {
                for (std::int32_t gx = 0; gx < n_; gx += step) {
                    const std::uint64_t hash = point_hash(kPlacementSeed + static_cast<std::uint64_t>(pass), gx, gz);
                    // A jittered point inside the step x step square.
                    const auto jx = static_cast<std::int32_t>((hash & 0xFFFFFF) % static_cast<std::uint64_t>(step * 65536));
                    const auto jz = static_cast<std::int32_t>(((hash >> 24) & 0xFFFFFF) % static_cast<std::uint64_t>(step * 65536));
                    const Fixed x = Fixed::from_raw(gx * 65536 + jx);
                    const Fixed z = Fixed::from_raw(gz * 65536 + jz);
                    const std::int32_t cx = x.floor_int();
                    const std::int32_t cz = z.floor_int();
                    if (cx >= n_ || cz >= n_ || !land(cx, cz)) {
                        continue;
                    }
                    const Terrain t = cell_terrain(cx, cz);
                    std::int64_t chance = 0;  // Per mille, before the size share.
                    if (t == Terrain::ForestFloor) {
                        chance = std::min<std::int64_t>(900, 250 + forest_[ci(cx, cz)] * 3);
                    } else if ((t == Terrain::Grass || t == Terrain::Meadow) && size <= TreeSize::Medium) {
                        chance = 8;  // A lone tree now and then.
                    }
                    if (chance == 0) {
                        continue;
                    }
                    const BiomeDef& biome = flora_.biomes[std::min<std::size_t>(biome_[ci(cx, cz)], flora_.biomes.size() - 1)];
                    if (biome.species.empty()) {
                        continue;
                    }
                    std::int64_t total = 0;
                    for (std::size_t k = 0; k < kTreeSizes; ++k) {
                        total += static_cast<std::int64_t>(biome.size_weights[k]) * type.size_bias[k];
                    }
                    const std::int64_t share = static_cast<std::int64_t>(biome.size_weights[pass]) * type.size_bias[pass];
                    if (total == 0 || share == 0) {
                        continue;
                    }
                    // The size weights share out the forest's ground: each
                    // bigger size fills its share of its own grid squares,
                    // and small trees fill whatever room is left.
                    chance = size == TreeSize::Small ? chance * biome.density / 100
                                                     : chance * biome.density * share / (100 * total);
                    const auto roll = static_cast<std::int64_t>((hash >> 36) % 1000);
                    if (roll >= std::min<std::int64_t>(950, chance)) {
                        continue;
                    }
                    const std::uint8_t species = pick_weighted(biome.species, static_cast<std::uint32_t>(hash >> 8));
                    (void)plant(x, z, species, flora_.fit_size(species, size), hash);
                }
                if ((gz & 63) == 0 && !report(GenStage::Forests, ((kTreeSizes - 1 - static_cast<std::size_t>(pass)) * 100 +
                                                                  static_cast<std::size_t>(gz) * 100 / static_cast<std::size_t>(n_)) /
                                                                     kTreeSizes)) {
                    return false;
                }
            }
        }
        return report(GenStage::Forests, 100);
    }

    // Young trees of the local biome around a point (start fairness).
    void grove(std::int32_t cx, std::int32_t cz, std::int32_t count, std::int32_t spread) {
        for (std::int32_t i = 0, tries = 0; i < count && tries < count * 6; ++tries) {
            const Angle a = rng_.angle();
            const Fixed r = Fixed::from_int(rng_.range(0, spread));
            const Fixed x = cell_center(cx) + cos(a) * r;
            const Fixed z = cell_center(cz) + sin(a) * r;
            const std::int32_t px = std::clamp(x.floor_int(), 0, n_ - 1);
            const std::int32_t pz = std::clamp(z.floor_int(), 0, n_ - 1);
            if (flora_.biomes.empty()) {
                return;
            }
            const BiomeDef& biome = flora_.biomes[std::min<std::size_t>(biome_[ci(px, pz)], flora_.biomes.size() - 1)];
            if (biome.species.empty()) {
                continue;
            }
            const std::uint64_t hash = (static_cast<std::uint64_t>(rng_.next_u32()) << 32) | rng_.next_u32();
            const std::uint8_t species = pick_weighted(biome.species, static_cast<std::uint32_t>(hash >> 8));
            const TreeSize size = flora_.fit_size(species, (hash & 1) != 0 ? TreeSize::Small : TreeSize::Medium);
            if (plant(x, z, species, size, hash)) {
                ++i;
            }
        }
    }

    // --- Resources and animal zones ------------------------------------------

    // A random land cell satisfying `accept`, trying a few times; the best
    // by `score` among the accepted ones wins. False if none was found.
    bool pick_cell(int tries, const std::function<bool(std::int32_t, std::int32_t)>& accept,
                   const std::function<std::int32_t(std::int32_t, std::int32_t)>& score, std::int32_t& ox, std::int32_t& oz) {
        bool found = false;
        std::int32_t best = INT32_MIN;
        for (int i = 0; i < tries; ++i) {
            const std::int32_t x = rng_.range(2, n_ - 3);
            const std::int32_t z = rng_.range(2, n_ - 3);
            if (!land(x, z) || !accept(x, z)) {
                continue;
            }
            const std::int32_t sc = score ? score(x, z) : 0;
            if (!found || sc > best) {
                found = true;
                best = sc;
                ox = x;
                oz = z;
            }
        }
        return found;
    }

    void cluster(FeatureType type, std::int32_t cx, std::int32_t cz, std::int32_t count, std::int32_t spread,
                 std::int32_t scale_min, std::int32_t scale_max) {
        for (std::int32_t i = 0; i < count; ++i) {
            const Angle a = rng_.angle();
            const Fixed r = Fixed::from_int(i == 0 ? 0 : rng_.range(1, spread));
            const Fixed x = cell_center(cx) + cos(a) * r;
            const Fixed z = cell_center(cz) + sin(a) * r;
            if (!land(x.floor_int(), z.floor_int())) {
                continue;
            }
            add_feature(type, x, z, Fixed::from_ratio(rng_.range(scale_min, scale_max), 100),
                        static_cast<std::uint16_t>(rng_.next_u32()));
        }
    }

    bool resources() {
        const std::int64_t k = amount_factor(s_.resources);
        std::int32_t x = 0;
        std::int32_t z = 0;
        const auto any = [](std::int32_t, std::int32_t) { return true; };
        const auto rocky = [this](std::int32_t cx, std::int32_t cz) {
            return cell_slope(cx, cz) + (cell_terrain(cx, cz) == Terrain::Rock ? 1000 : 0);
        };
        const std::int32_t stones = per_area(125 * k);
        for (std::int32_t i = 0; i < stones; ++i) {
            if (pick_cell(8, any, rocky, x, z)) {
                cluster(FeatureType::Stone, x, z, rng_.range(1, 3), 5, 100, 220);
            }
        }
        if (!report(GenStage::Resources, 25)) {
            return false;
        }
        const std::int32_t ores = per_area(30 * k);
        for (std::int32_t i = 0; i < ores; ++i) {
            if (pick_cell(16, any, rocky, x, z)) {
                cluster(FeatureType::IronOre, x, z, rng_.range(1, 2), 4, 100, 170);
            }
        }
        const auto forest_edge = [this](std::int32_t cx, std::int32_t cz) {
            const Terrain t = cell_terrain(cx, cz);
            return (t == Terrain::ForestFloor && forest_[ci(cx, cz)] < 40) || t == Terrain::Meadow;
        };
        const std::int32_t berries = per_area(100 * k);
        for (std::int32_t i = 0; i < berries; ++i) {
            if (pick_cell(10, forest_edge, {}, x, z)) {
                cluster(FeatureType::BerryBush, x, z, rng_.range(2, 4), 6, 80, 130);
            }
        }
        const auto deep_forest = [this](std::int32_t cx, std::int32_t cz) {
            return cell_terrain(cx, cz) == Terrain::ForestFloor && forest_[ci(cx, cz)] >= 60;
        };
        const std::int32_t herbs = per_area(75 * k);
        for (std::int32_t i = 0; i < herbs; ++i) {
            if (pick_cell(10, deep_forest, {}, x, z)) {
                cluster(FeatureType::Herbs, x, z, rng_.range(2, 5), 5, 80, 140);
            }
        }
        if (!report(GenStage::Resources, 70)) {
            return false;
        }
        // Animals.
        const auto wild = [this](std::int32_t cx, std::int32_t cz) {
            const Terrain t = cell_terrain(cx, cz);
            return t == Terrain::ForestFloor || t == Terrain::Meadow;
        };
        const struct {
            ZoneType type;
            std::int64_t tenths;
            bool deep;
        } kinds[] = {{ZoneType::Deer, 30, false}, {ZoneType::Boar, 20, false}, {ZoneType::Wolves, 10, true},
                     {ZoneType::Bears, 5, true}};
        for (const auto& kind : kinds) {
            const std::int32_t count = per_area(kind.tenths);
            for (std::int32_t i = 0; i < count; ++i) {
                const std::function<bool(std::int32_t, std::int32_t)> accept =
                    kind.deep ? std::function<bool(std::int32_t, std::int32_t)>(deep_forest) : wild;
                if (pick_cell(10, accept, {}, x, z)) {
                    out_.zones.push_back({kind.type, cell_center(x), cell_center(z), Fixed::from_int(rng_.range(60, 150))});
                }
            }
        }
        return report(GenStage::Resources, 100);
    }

    // --- Start positions -------------------------------------------------------

    [[nodiscard]] static std::int64_t d2(Fixed ax, Fixed az, Fixed bx, Fixed bz) {
        const std::int64_t dx = (static_cast<std::int64_t>(ax.raw()) - bx.raw()) >> 8;
        const std::int64_t dz = (static_cast<std::int64_t>(az.raw()) - bz.raw()) >> 8;
        return dx * dx + dz * dz;  // In (1/256 m)^2.
    }
    [[nodiscard]] static std::int64_t meters2(std::int64_t m) { return m * m * 65536; }

    [[nodiscard]] std::int32_t count_near(FeatureType type, Fixed x, Fixed z, std::int32_t radius) const {
        std::int32_t n = 0;
        const std::int64_t r2 = meters2(radius);
        for (const MapFeature& f : out_.features) {
            if (f.type == type && d2(f.x, f.z, x, z) <= r2) {
                ++n;
            }
        }
        return n;
    }

    [[nodiscard]] bool flat_enough(std::int32_t cx, std::int32_t cz) const {
        std::int32_t lo = INT32_MAX;
        std::int32_t hi = INT32_MIN;
        for (std::int32_t dz = -15; dz <= 15; dz += 5) {
            for (std::int32_t dx = -15; dx <= 15; dx += 5) {
                const std::int32_t x = std::clamp(cx + dx, 0, v_ - 1);
                const std::int32_t z = std::clamp(cz + dz, 0, v_ - 1);
                lo = std::min(lo, h_[vi(x, z)]);
                hi = std::max(hi, h_[vi(x, z)]);
            }
        }
        return hi - lo <= 3000;
    }

    // A land cell at a distance between r0 and r1 from the point, or false.
    bool ring_cell(Fixed x, Fixed z, std::int32_t r0, std::int32_t r1, std::int32_t& ox, std::int32_t& oz) {
        for (int i = 0; i < 40; ++i) {
            const Angle a = rng_.angle();
            const Fixed r = Fixed::from_int(rng_.range(r0, r1));
            const std::int32_t cx = (x + cos(a) * r).floor_int();
            const std::int32_t cz = (z + sin(a) * r).floor_int();
            if (land(cx, cz) && cell_terrain(cx, cz) != Terrain::Sand) {
                ox = cx;
                oz = cz;
                return true;
            }
        }
        return false;
    }

    bool starts() {
        struct Candidate {
            std::int32_t score;
            std::int32_t x;
            std::int32_t z;
        };
        const std::int32_t players = std::clamp<std::int32_t>(s_.players, 1, 12);
        const std::int32_t margin = n_ / 10;
        std::vector<Candidate> candidates;
        std::vector<Candidate> fallback;
        for (std::int32_t z = margin; z < n_ - margin; z += 32) {
            for (std::int32_t x = margin; x < n_ - margin; x += 32) {
                const Terrain t = cell_terrain(x, z);
                if (t == Terrain::Water || t == Terrain::Rock || t == Terrain::Sand || !flat_enough(x, z)) {
                    continue;
                }
                const std::int32_t d = dist_[ci(x, z)];
                // Prefer good soil and the middle of the map for one player.
                std::int32_t score = fertility_[ci(x, z)] * 4;
                if (players == 1) {
                    score -= (std::abs(x - n_ / 2) + std::abs(z - n_ / 2)) / 4;
                }
                const Candidate c{score, x, z};
                if (d >= 12 && d <= kStartMaxWaterDistance) {
                    candidates.push_back(c);
                } else {
                    fallback.push_back(c);
                }
            }
        }
        if (!islands_.empty()) {
            candidates.clear();  // Each town on its own island instead.
            island_starts(players);
        }
        if (static_cast<std::int32_t>(candidates.size()) < players) {
            candidates.insert(candidates.end(), fallback.begin(), fallback.end());
        }
        std::sort(candidates.begin(), candidates.end(), [](const Candidate& a, const Candidate& b) {
            return a.score != b.score ? a.score > b.score : (a.z != b.z ? a.z < b.z : a.x < b.x);
        });
        // As far apart as the map allows.
        std::int64_t spacing = static_cast<std::int64_t>(n_) * 60 / 100 * 1000 /
                               static_cast<std::int64_t>(isqrt(static_cast<std::uint64_t>(players) * 1000000));
        while (static_cast<std::int32_t>(out_.starts.size()) < players && !candidates.empty()) {
            for (const Candidate& c : candidates) {
                if (static_cast<std::int32_t>(out_.starts.size()) >= players) {
                    break;
                }
                const Fixed cx = cell_center(c.x);
                const Fixed cz = cell_center(c.z);
                bool ok = true;
                for (const StartPosition& s : out_.starts) {
                    if (d2(s.x, s.z, cx, cz) < meters2(spacing)) {
                        ok = false;
                        break;
                    }
                }
                if (ok) {
                    out_.starts.push_back({cx, cz});
                }
            }
            spacing = spacing * 85 / 100;
            if (spacing < 8) {
                break;
            }
        }
        if (!report(GenStage::Starts, 50)) {
            return false;
        }

        // Fairness: every start gets the basics within reach.
        for (const StartPosition& s : out_.starts) {
            std::int32_t x = 0;
            std::int32_t z = 0;
            // A few tries each; a start surrounded by water may end up short.
            for (int attempt = 0; attempt < 6 && count_near(FeatureType::Stone, s.x, s.z, kStartResourceRadius) < kStartMinStones;
                 ++attempt) {
                if (ring_cell(s.x, s.z, 60, 150, x, z)) {
                    cluster(FeatureType::Stone, x, z, 2, 4, 120, 200);
                }
            }
            for (int attempt = 0;
                 attempt < 6 && count_near(FeatureType::BerryBush, s.x, s.z, kStartResourceRadius) < kStartMinBerries;
                 ++attempt) {
                if (ring_cell(s.x, s.z, 50, 150, x, z)) {
                    cluster(FeatureType::BerryBush, x, z, 3, 5, 90, 120);
                }
            }
            for (int attempt = 0; attempt < 4; ++attempt) {
                const std::int32_t trees = count_near(FeatureType::Tree, s.x, s.z, kStartResourceRadius);
                if (trees >= kStartMinTrees || !ring_cell(s.x, s.z, 70, 150, x, z)) {
                    break;
                }
                grove(x, z, kStartMinTrees - trees + 10, 25);
            }
        }
        // Room for the town center, and no predators on the doorstep.
        const std::int64_t clear = meters2(kStartClearRadius);
        const std::int64_t safe = meters2(250);
        std::erase_if(out_.features, [&](const MapFeature& f) {
            // Big trees keep farther away, so their crowns stay outside.
            const std::int64_t reach = f.type == FeatureType::Tree
                                           ? meters2(kStartClearRadius + size_info(static_cast<TreeSize>(f.size)).spacing_m)
                                           : clear;
            return std::any_of(out_.starts.begin(), out_.starts.end(),
                               [&](const StartPosition& s) { return d2(f.x, f.z, s.x, s.z) <= reach; });
        });
        std::erase_if(out_.zones, [&](const Zone& zone) {
            const bool predator = zone.type == ZoneType::Wolves || zone.type == ZoneType::Bears;
            return predator && std::any_of(out_.starts.begin(), out_.starts.end(), [&](const StartPosition& s) {
                       return d2(zone.x, zone.z, s.x, s.z) <= safe;
                   });
        });
        return report(GenStage::Starts, 100);
    }

    // Islands: each town near the middle of its home island, on good
    // ground with water at hand; failing that, on the land nearest the
    // middle.
    void island_starts(std::int32_t players) {
        for (std::int32_t p = 0; p < players && p < static_cast<std::int32_t>(islands_.size()); ++p) {
            const Island& is = islands_[static_cast<std::size_t>(p)];
            const std::int32_t reach = std::max(8, is.radius * 55 / 100);
            const std::int32_t step = std::clamp(is.radius / 12, 4, 32);
            bool found = false;
            std::int64_t best = INT64_MIN;
            std::int32_t bx = std::clamp(is.x, 0, n_ - 1);
            std::int32_t bz = std::clamp(is.z, 0, n_ - 1);
            std::int64_t nearest = INT64_MAX;
            for (std::int32_t z = is.z - reach; z <= is.z + reach; z += step) {
                for (std::int32_t x = is.x - reach; x <= is.x + reach; x += step) {
                    if (!land(x, z)) {
                        continue;
                    }
                    const std::int64_t from_middle = static_cast<std::int64_t>(x - is.x) * (x - is.x) +
                                                     static_cast<std::int64_t>(z - is.z) * (z - is.z);
                    const Terrain t = cell_terrain(x, z);
                    const std::int32_t d = dist_[ci(x, z)];
                    if (t != Terrain::Rock && t != Terrain::Sand && flat_enough(x, z) && d >= 12 &&
                        d <= kStartMaxWaterDistance) {
                        const std::int64_t score = fertility_[ci(x, z)] * 4 - isqrt(static_cast<std::uint64_t>(from_middle)) / 4;
                        if (!found || score > best) {
                            found = true;
                            best = score;
                            bx = x;
                            bz = z;
                        }
                    } else if (!found && from_middle < nearest) {
                        nearest = from_middle;
                        bx = x;
                        bz = z;
                    }
                }
            }
            out_.starts.push_back({cell_center(bx), cell_center(bz)});
        }
    }

    // --- Output ------------------------------------------------------------------

    void finish() {
        out_.heights.resize(h_.size());
        for (std::size_t i = 0; i < h_.size(); ++i) {
            out_.heights[i] = static_cast<std::uint16_t>(std::clamp(h_[i] / 10, 1, 65535));
        }
        out_.water.resize(water_.size());
        for (std::size_t i = 0; i < water_.size(); ++i) {
            out_.water[i] = water_[i] == 0 ? 0 : static_cast<std::uint16_t>(std::clamp(water_[i] / 10, 1, 65535));
        }
        out_.terrain = std::move(terrain_);
        out_.fertility = std::move(fertility_);
        out_.biome = std::move(biome_);
    }

    const MapSettings& s_;
    const Flora& flora_;
    const GenProgress& progress_;
    std::int32_t n_;
    std::int32_t v_;
    Rng rng_;
    MapData out_;
    std::vector<std::int32_t> h_;       // Vertex heights, millimeters.
    std::vector<std::int32_t> lake_cut_;  // Depth of the lake basins being dug.
    std::vector<std::uint8_t> bed_;        // Vertex dug as a river bed.
    std::vector<std::int32_t> filled_;  // Heights with depressions filled.
    std::vector<std::uint8_t> flow_;    // Direction toward the outlet.
    std::vector<std::uint8_t> lake_;    // Vertex belongs to a lake.
    std::vector<std::int32_t> water_;   // Cell water surface, millimeters.
    std::vector<std::uint8_t> terrain_;
    std::vector<std::uint8_t> dist_;    // Cell distance to water, meters.
    std::vector<std::uint8_t> fertility_;
    std::vector<std::uint8_t> forest_;  // How deep in the forest, 0 = not forest.
    std::vector<std::uint8_t> biome_;   // Cell biome.
    std::vector<std::uint8_t> taken_;   // Cells kept free around trunks.
    std::vector<Island> islands_;       // Map type with islands: home islands first.
};

}  // namespace

namespace {

// Separate maps: one map per player from seed + player number, side by
// side; the squares nobody has are sea.
std::optional<MapData> generate_world(const MapSettings& settings, const Content& content, const GenProgress& progress,
                                      MapHooks* hooks) {
    const std::int32_t k = world_grid(settings);
    const std::int32_t n = settings.players;
    MapSettings tile = settings;
    tile.separate = false;
    tile.players = 1;
    tile.size = region_map_size(settings);
    const std::int32_t t = map_cells(tile.size);
    MapData world;
    world.settings = settings;
    world.generator_version = kGeneratorVersion;
    world.size = t * k;
    const auto side = static_cast<std::size_t>(world.size);
    const auto vside = side + 1;
    world.heights.assign(vside * vside, 0);
    world.water.assign(side * side, 0);
    world.terrain.assign(side * side, static_cast<std::uint8_t>(Terrain::Water));
    world.fertility.assign(side * side, 0);
    world.biome.assign(side * side, 0);
    std::uint16_t lowest = 65535;
    constexpr auto kStages = static_cast<std::int32_t>(GenStage::Count);
    for (std::int32_t i = 0; i < n; ++i) {
        tile.seed = settings.seed + static_cast<std::uint64_t>(i);
        // Progress through all the maps: each stage once per map.
        const GenProgress each = [&](GenStage stage, int percent) {
            if (!progress) {
                return true;
            }
            const std::int32_t at = i * kStages + static_cast<std::int32_t>(stage);
            return progress(static_cast<GenStage>(at / n), ((at % n) * 100 + percent) / n);
        };
        std::optional<MapData> m = generate_map(tile, content, each, hooks);
        if (!m.has_value()) {
            return std::nullopt;
        }
        const auto ox = static_cast<std::size_t>((i % k) * t);
        const auto oz = static_cast<std::size_t>((i / k) * t);
        const auto tv = static_cast<std::size_t>(t) + 1;
        for (std::size_t vz = 0; vz < tv; ++vz) {
            for (std::size_t vx = 0; vx < tv; ++vx) {
                const std::uint16_t h = m->heights[vz * tv + vx];
                world.heights[(oz + vz) * vside + ox + vx] = h;
                lowest = std::min(lowest, h);
            }
        }
        const auto tc = static_cast<std::size_t>(t);
        for (std::size_t cz = 0; cz < tc; ++cz) {
            for (std::size_t cx = 0; cx < tc; ++cx) {
                const std::size_t from = cz * tc + cx;
                const std::size_t to = (oz + cz) * side + ox + cx;
                world.water[to] = m->water[from];
                world.terrain[to] = m->terrain[from];
                world.fertility[to] = m->fertility[from];
                world.biome[to] = m->biome[from];
            }
        }
        const Fixed fx = Fixed::from_int(static_cast<std::int32_t>(ox));
        const Fixed fz = Fixed::from_int(static_cast<std::int32_t>(oz));
        for (MapFeature f : m->features) {
            f.x = f.x + fx;
            f.z = f.z + fz;
            world.features.push_back(f);
        }
        for (Zone z : m->zones) {
            z.x = z.x + fx;
            z.z = z.z + fz;
            world.zones.push_back(z);
        }
        StartPosition start{fx + Fixed::from_int(t / 2), fz + Fixed::from_int(t / 2)};
        if (!m->starts.empty()) {
            start = {m->starts[0].x + fx, m->starts[0].z + fz};
        }
        world.starts.push_back(start);
    }
    // The empty squares: sea a little below the lowest land.
    for (std::int32_t i = n; i < k * k; ++i) {
        const auto ox = static_cast<std::size_t>((i % k) * t);
        const auto oz = static_cast<std::size_t>((i / k) * t);
        for (std::size_t vz = 0; vz <= static_cast<std::size_t>(t); ++vz) {
            for (std::size_t vx = 0; vx <= static_cast<std::size_t>(t); ++vx) {
                const bool edge = (vz == 0 || vx == 0 || vz == static_cast<std::size_t>(t) || vx == static_cast<std::size_t>(t));
                if (!edge) {
                    world.heights[(oz + vz) * vside + ox + vx] = static_cast<std::uint16_t>(std::max(0, lowest - 300));
                }
            }
        }
        for (std::size_t cz = 0; cz < static_cast<std::size_t>(t); ++cz) {
            for (std::size_t cx = 0; cx < static_cast<std::size_t>(t); ++cx) {
                world.water[(oz + cz) * side + ox + cx] = static_cast<std::uint16_t>(std::max(100, static_cast<int>(lowest) - 100));
            }
        }
    }
    return world;
}

}  // namespace

namespace worldgen {

namespace {

// Sea kept around the map and between islands, meters.
std::int32_t island_edge(std::int32_t cells) {
    return std::max(16, cells / 40);
}
std::int32_t island_gap(std::int32_t cells) {
    return std::max(20, cells / 64);
}
// Area an island takes with the sea it needs around it (about pi r^2).
std::int64_t island_footprint(std::int32_t radius, std::int32_t gap) {
    const std::int64_t reach = static_cast<std::int64_t>(radius) * kIslandReach / 100 + gap / 2;
    return reach * reach * 22 / 7;
}

}  // namespace

std::vector<Island> island_layout(std::uint64_t seed, std::int32_t cells, std::int32_t towns, std::int32_t per_town) {
    towns = std::max(1, towns);
    per_town = std::clamp(per_town, 1, static_cast<std::int32_t>(kMaxIslandsPerTown));
    const std::int32_t count = towns * per_town;
    Rng rng(seed ^ kIslandSeed, 11);
    // Home islands weigh 3, the others 1 to 2; about 40 % of the map is land.
    std::vector<std::int64_t> weight(static_cast<std::size_t>(count), 300);
    for (std::int32_t i = towns; i < count; ++i) {
        weight[static_cast<std::size_t>(i)] = rng.range(100, 200);
    }
    // The others biggest first, so they find room.
    std::sort(weight.begin() + towns, weight.end(), std::greater<>());
    std::int64_t total = 0;
    for (const std::int64_t w : weight) {
        total += w;
    }
    const std::int64_t land = static_cast<std::int64_t>(cells) * cells * 40 / 100;
    std::vector<std::int32_t> radius(static_cast<std::size_t>(count));
    for (std::size_t i = 0; i < radius.size(); ++i) {
        radius[i] = std::max<std::int32_t>(
            12, static_cast<std::int32_t>(isqrt(static_cast<std::uint64_t>(weight[i] * land * 7 / (total * 22)))));
    }
    const std::int32_t edge = island_edge(cells);
    const std::int32_t gap = island_gap(cells);
    std::vector<Island> out;
    // Placed one by one where they fit; if some island finds no room, all
    // shrink a little and the placement starts over.
    for (int round = 0; round < 60; ++round) {
        out.clear();
        bool ok = true;
        for (std::int32_t i = 0; i < count && ok; ++i) {
            const std::int32_t r = radius[static_cast<std::size_t>(i)];
            const std::int32_t reach = r * kIslandReach / 100;
            const std::int32_t lo = edge + reach;
            const std::int32_t hi = cells - edge - reach;
            if (lo > hi) {
                ok = false;
                break;
            }
            const bool home = i < towns;
            bool found = false;
            Island best;
            std::int64_t best_score = -1;
            for (int t = 0; t < (home ? 48 : 160); ++t) {
                const Island c{rng.range(lo, hi), rng.range(lo, hi), r};
                bool fits = true;
                std::int64_t nearest_home = INT64_MAX;
                for (std::size_t j = 0; j < out.size() && fits; ++j) {
                    const Island& o = out[j];
                    const std::int64_t dx = c.x - o.x;
                    const std::int64_t dz = c.z - o.z;
                    const std::int64_t d2 = dx * dx + dz * dz;
                    const std::int64_t apart = reach + static_cast<std::int64_t>(o.radius) * kIslandReach / 100 + gap;
                    fits = d2 >= apart * apart;
                    if (static_cast<std::int32_t>(j) < towns) {
                        nearest_home = std::min(nearest_home, d2);
                    }
                }
                if (!fits) {
                    continue;
                }
                // Homes as far from each other as they can; the others
                // wherever they fit first.
                if (!home) {
                    best = c;
                    found = true;
                    break;
                }
                if (nearest_home > best_score) {
                    best_score = nearest_home;
                    best = c;
                    found = true;
                }
            }
            if (!found) {
                ok = false;
                break;
            }
            out.push_back(best);
        }
        if (ok) {
            return out;
        }
        for (std::int32_t& r : radius) {
            r = std::max(12, r * 9 / 10);
        }
    }
    return out;  // Some islands did not fit (only with far too many for the map).
}

std::int32_t max_islands_per_town(MapSize size, std::int32_t towns) {
    // Room for a town: a home island of 110 m at least; the others 45 m.
    const std::int32_t cells = map_cells(size);
    const std::int32_t gap = island_gap(cells);
    const std::int64_t budget = static_cast<std::int64_t>(cells) * cells * 35 / 100;
    const std::int64_t home = island_footprint(110, gap);
    const std::int64_t other = island_footprint(45, gap);
    towns = std::max(1, towns);
    for (std::int32_t k = kMaxIslandsPerTown; k > 1; --k) {
        if (towns * home + towns * (k - 1) * other <= budget) {
            return k;
        }
    }
    return 1;
}

}  // namespace worldgen

std::optional<MapData> generate_map(const MapSettings& settings, const Content& content, const GenProgress& progress,
                                    MapHooks* hooks) {
    if (world_grid(settings) > 1) {
        return generate_world(settings, content, progress, hooks);
    }
    Generator gen(settings, content, progress);
    std::optional<MapData> map = gen.run();
    if (map.has_value() && hooks != nullptr && !hooks->map_generated(*map)) {
        return std::nullopt;
    }
    return map;
}

}  // namespace sc::sim
