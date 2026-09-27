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
constexpr std::uint64_t kOakSeed = 0x4f414b0000000007ull;
constexpr std::uint64_t kPlacementSeed = 0x504c414345000008ull;

constexpr std::uint8_t kFlowBorder = 255;
constexpr std::uint8_t kUnvisited = 254;

// Per-amount multiplier in halves: Low 1x, Normal 2x, High 4x.
std::int64_t amount_factor(Amount a) {
    return a == Amount::Low ? 1 : (a == Amount::Normal ? 2 : 4);
}

class Generator {
public:
    Generator(const MapSettings& s, const GenProgress& progress)
        : s_(s), progress_(progress), n_(map_cells(s.size)), v_(n_ + 1), rng_(s.seed, 7) {}

    std::optional<MapData> run() {
        out_.settings = s_;
        out_.size = n_;
        if (!relief() || !lakes() || !rivers() || !soil() || !forests() || !resources() || !starts()) {
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
        const std::int64_t amp = s_.relief == Relief::Low ? 5000 : 10000;  // Millimeters.
        for (std::int32_t z = 0; z < v_; ++z) {
            for (std::int32_t x = 0; x < v_; ++x) {
                const std::int64_t detail = fbm(s_.seed ^ kReliefSeed, x, z, 10, 6);
                const std::int64_t broad = fbm(s_.seed ^ kBroadSeed, x, z, 11, 1);
                h_[vi(x, z)] = static_cast<std::int32_t>(20000 + detail * amp / 32768 + broad * amp / 65536);
            }
            if ((z & 63) == 0 && !report(GenStage::Relief, z * 90 / v_)) {
                return false;
            }
        }
        // Basins that will hold lakes.
        const std::int32_t lakes = per_area(4 * amount_factor(s_.water));
        const std::int32_t margin = n_ / 10;
        for (std::int32_t i = 0; i < lakes; ++i) {
            const std::int32_t cx = rng_.range(margin, n_ - margin);
            const std::int32_t cz = rng_.range(margin, n_ - margin);
            const std::int32_t r = rng_.range(35, 110);
            const std::int64_t depth = rng_.range(2500, 5000);
            const std::int64_t r2 = static_cast<std::int64_t>(r) * r;
            for (std::int32_t z = std::max(0, cz - r); z <= std::min(v_ - 1, cz + r); ++z) {
                for (std::int32_t x = std::max(0, cx - r); x <= std::min(v_ - 1, cx + r); ++x) {
                    const std::int64_t d2 = static_cast<std::int64_t>(x - cx) * (x - cx) + static_cast<std::int64_t>(z - cz) * (z - cz);
                    if (d2 < r2) {
                        const std::int64_t t = d2 * 65536 / r2;
                        const std::int64_t w = ((65536 - t) * (65536 - t)) >> 16;
                        h_[vi(x, z)] -= static_cast<std::int32_t>((depth * w) >> 16);
                    }
                }
            }
        }
        for (std::int32_t& v : h_) {
            v = std::max(v, 1000);
        }
        return report(GenStage::Relief, 100);
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
                if (level > 0 && lowest < level) {
                    water_[ci(x, z)] = level;
                    terrain_[ci(x, z)] = static_cast<std::uint8_t>(Terrain::Water);
                }
            }
        }
        return report(GenStage::Lakes, 100);
    }

    // --- Rivers: follow the flow to the border or a lake ---------------------

    bool rivers() {
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
                        h_[v] = std::min(h_[v], level - 900 + d * 250);
                    } else if (d <= reach) {
                        // Banks slope down toward the water, never below it.
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
                } else if (d <= 2) {
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

    // --- Forests -------------------------------------------------------------

    bool forests() {
        constexpr std::int32_t kStep = 3;
        for (std::int32_t gz = 0; gz < n_; gz += kStep) {
            for (std::int32_t gx = 0; gx < n_; gx += kStep) {
                const std::uint64_t hash = point_hash(kPlacementSeed, gx, gz);
                // A jittered point inside the 3 x 3 m square.
                const auto jx = static_cast<std::int32_t>((hash & 0xFFFFFF) % (kStep * 65536));
                const auto jz = static_cast<std::int32_t>(((hash >> 24) & 0xFFFFFF) % (kStep * 65536));
                const Fixed x = Fixed::from_raw(gx * 65536 + jx);
                const Fixed z = Fixed::from_raw(gz * 65536 + jz);
                const std::int32_t cx = x.floor_int();
                const std::int32_t cz = z.floor_int();
                if (cx >= n_ || cz >= n_ || !land(cx, cz)) {
                    continue;
                }
                const Terrain t = cell_terrain(cx, cz);
                const std::uint32_t roll = static_cast<std::uint32_t>((hash >> 36) % 1000);
                std::uint32_t chance = 0;
                if (t == Terrain::ForestFloor) {
                    chance = std::min<std::uint32_t>(900, 250 + forest_[ci(cx, cz)] * 3u);
                } else if (t == Terrain::Grass || t == Terrain::Meadow) {
                    chance = 8;  // A lone tree now and then.
                }
                if (roll >= chance) {
                    continue;
                }
                const bool wet = dist_[ci(cx, cz)] < 30;
                const bool oak = wet ? ((hash >> 46) % 10) < 7 : fbm(s_.seed ^ kOakSeed, cx, cz, 8, 2) > 4000;
                const Fixed scale = Fixed::from_ratio(80 + static_cast<std::int64_t>((hash >> 50) % 55), 100);
                add_feature(oak ? FeatureType::OakTree : FeatureType::PineTree, x, z, scale,
                            static_cast<std::uint16_t>(hash >> 48));
            }
            if ((gz & 63) == 0 && !report(GenStage::Forests, gz * 100 / n_)) {
                return false;
            }
        }
        return report(GenStage::Forests, 100);
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
            const std::int32_t trees = count_near(FeatureType::PineTree, s.x, s.z, kStartResourceRadius) +
                                       count_near(FeatureType::OakTree, s.x, s.z, kStartResourceRadius);
            if (trees < kStartMinTrees && ring_cell(s.x, s.z, 70, 150, x, z)) {
                cluster(FeatureType::PineTree, x, z, kStartMinTrees - trees + 10, 22, 80, 130);
            }
        }
        // Room for the town center, and no predators on the doorstep.
        const std::int64_t clear = meters2(kStartClearRadius);
        const std::int64_t safe = meters2(250);
        std::erase_if(out_.features, [&](const MapFeature& f) {
            return std::any_of(out_.starts.begin(), out_.starts.end(),
                               [&](const StartPosition& s) { return d2(f.x, f.z, s.x, s.z) <= clear; });
        });
        std::erase_if(out_.zones, [&](const Zone& zone) {
            const bool predator = zone.type == ZoneType::Wolves || zone.type == ZoneType::Bears;
            return predator && std::any_of(out_.starts.begin(), out_.starts.end(), [&](const StartPosition& s) {
                       return d2(zone.x, zone.z, s.x, s.z) <= safe;
                   });
        });
        return report(GenStage::Starts, 100);
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
    }

    const MapSettings& s_;
    const GenProgress& progress_;
    std::int32_t n_;
    std::int32_t v_;
    Rng rng_;
    MapData out_;
    std::vector<std::int32_t> h_;       // Vertex heights, millimeters.
    std::vector<std::int32_t> filled_;  // Heights with depressions filled.
    std::vector<std::uint8_t> flow_;    // Direction toward the outlet.
    std::vector<std::uint8_t> lake_;    // Vertex belongs to a lake.
    std::vector<std::int32_t> water_;   // Cell water surface, millimeters.
    std::vector<std::uint8_t> terrain_;
    std::vector<std::uint8_t> dist_;    // Cell distance to water, meters.
    std::vector<std::uint8_t> fertility_;
    std::vector<std::uint8_t> forest_;  // How deep in the forest, 0 = not forest.
};

}  // namespace

std::optional<MapData> generate_map(const MapSettings& settings, const GenProgress& progress) {
    Generator gen(settings, progress);
    return gen.run();
}

}  // namespace sc::sim
