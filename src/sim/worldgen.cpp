#include "sim/worldgen.h"

#include <algorithm>
#include <functional>
#include <limits>
#include <utility>
#include <vector>
#if defined(_MSC_VER) && !defined(__clang__) && (defined(_M_X64) || defined(_M_IX86))
#include <xmmintrin.h>
#endif

#include "sim/noise.h"
#include "sim/rng.h"
#include "sim/worldgen_hier.h"

namespace sc::sim {

namespace {

using namespace worldgen;

// Seeds for each noise field, so they are unrelated to each other.
constexpr std::uint64_t kFertilitySeed = 0x4645525400000003ull;
constexpr std::uint64_t kRockSeed = 0x524f434b00000004ull;
constexpr std::uint64_t kClaySeed = 0x434c415900000005ull;
constexpr std::uint64_t kForestSeed = 0x464f524553540006ull;
constexpr std::uint64_t kPlacementSeed = 0x504c414345000008ull;
constexpr std::uint64_t kBiomeSeed = 0x42494f4d45000009ull;
constexpr std::uint64_t kGiantSeed = 0x4749414e54000013ull;
// Giants (phase 55): at least this far from a town's start and from each
// other (meters; on big maps they keep further apart), on ground no steeper
// than this (centimeters across a cell), with this clearing around.
constexpr std::int32_t kGiantFromStart = 200;
constexpr std::int32_t kGiantApart = 160;
constexpr std::int32_t kGiantSlope = 120;
constexpr std::int32_t kGiantClearing = 18;
constexpr std::uint64_t kTemperatureSeed = 0x54454d5000000011ull;
constexpr std::uint64_t kHumiditySeed = 0x48554d4944000012ull;
// How far outside its ranges of temperature and humidity a biome still grows.
constexpr std::int32_t kClimateSlack = 6;
constexpr std::uint64_t kBeachSeed = 0x4245414348000015ull;
constexpr std::uint64_t kIslandSeed = 0x49534c414e440016ull;
constexpr std::uint64_t kFlatOrderSeed = 0x464c41544f520031ull;

constexpr std::uint8_t kFlowBorder = 255;
constexpr std::uint8_t kUnvisited = 254;

// A hint to the processor to load memory that is needed soon.
inline void prefetch(const void* p) {
#if defined(__GNUC__) || defined(__clang__)
    __builtin_prefetch(p);
#elif defined(_M_X64) || defined(_M_IX86)
    _mm_prefetch(static_cast<const char*>(p), _MM_HINT_T0);
#else
    (void)p;
#endif
}


// Rivers' courses in the map's landforms (phase 37): a point every this
// many steps, and their width (beds reach 13 m across).
constexpr std::int64_t kRiverCourseStep = 8;
constexpr std::int32_t kRiverWidth = 14;
// A lake outside the basins needs this many vertices under 10 cm of water
// or more (about 1.5 ha; phase 39).
constexpr std::size_t kFreeLake = 15000;

// A point on the map, in meters.
struct Point {
    std::int32_t x = 0;
    std::int32_t z = 0;
};

class Generator {
public:
    Generator(const MapSettings& s, const Content& content, const GenProgress& progress)
        : s_(s), flora_(content.flora), progress_(progress), n_(map_cells(s.size)), v_(n_ + 1),
          rng_(s.seed, 7) {}

    std::optional<MapData> run() {
        out_.settings = s_;
        out_.size = n_;
        out_.generator_version = kGeneratorVersion;
        if (!relief() || !lakes() || !rivers() || !soil() || !biomes() || !forests() || !resources() || !starts()) {
            return std::nullopt;
        }
        giants();
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

    // The ground, sea and islands come from the hierarchical module
    // (worldgen_hier): its regions and structures are the map's landforms,
    // and its rivers start where its valleys and canyons ask for one.
    bool relief() {
        hier::Ground r;
        if (!hier::shape(s_, n_, s_.island_map(), [this](int percent) { return report(GenStage::Relief, percent); }, r)) {
            return false;
        }
        h_ = std::move(r.h);
        sea_mm_ = r.sea_mm;
        out_.landforms = std::move(r.landforms);
        out_.region_owner = std::move(r.region_owner);
        out_.structure_owner = std::move(r.structure_owner);
        islands_ = std::move(r.islands);
        for (const auto& p : r.river_sources) {
            river_heads_.push_back({p[0], p[1]});
        }
        return true;
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
            if (sea[v] == 0 && h_[v] < sea_mm_) {
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
                if (wet && lowest + 10 <= sea_mm_) {
                    water_[ci(x, z)] = std::max(water_[ci(x, z)], sea_mm_);
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
        // Lowest first by height, then a scrambled order, then the vertex:
        // on flat ground (filled hollows) the flow spreads unevenly instead
        // of in straight lines along the grid. Heights fit in 20 bits of
        // millimeters (up to 1048 m) and vertices in 29 (a colossal map has
        // 268 million).
        // A heap per millimeter of height: nothing is ever pushed below the
        // height being drained (a vertex is filled at least to the one that
        // reaches it), so draining the heights in order pops the same order
        // as a single heap, but each heap stays small on big maps.
        // Only the heights the map has: nothing is filled above its highest
        // point.
        const auto [low, high] = std::minmax_element(h_.begin(), h_.end());
        const auto base = static_cast<std::size_t>(std::clamp(*low, 0, 0xFFFFF));
        const std::size_t heights = static_cast<std::size_t>(std::clamp(*high, 0, 0xFFFFF)) + 1 - base;
        std::vector<std::vector<std::uint64_t>> open(heights);
        std::size_t draining = heights;
        const auto push = [&](std::size_t i) {
            const std::uint64_t scramble = mix64(s_.seed ^ kFlatOrderSeed ^ i) & 0x7FFFu;
            const auto height = static_cast<std::size_t>(std::clamp(filled_[i], 0, 0xFFFFF)) - base;
            std::vector<std::uint64_t>& heap = open[height];
            heap.push_back((scramble << 29) | i);
            if (height == draining) {
                std::push_heap(heap.begin(), heap.end(), std::greater<>());
            }
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
        for (draining = 0; draining < heights; ++draining) {
            std::vector<std::uint64_t>& heap = open[draining];
            std::make_heap(heap.begin(), heap.end(), std::greater<>());
            while (!heap.empty()) {
                std::pop_heap(heap.begin(), heap.end(), std::greater<>());
                const std::uint64_t key = heap.back();
                heap.pop_back();
                // The next vertex out is most likely the top: its memory is
                // loaded meanwhile (the order is random on flat ground).
                if (!heap.empty()) {
                    const std::size_t next = static_cast<std::size_t>(heap.front() & 0x1FFFFFFFu);
                    prefetch(&filled_[next]);
                    prefetch(&flow_[next]);
                    prefetch(&h_[next]);
                    if (next >= static_cast<std::size_t>(v_) && next + static_cast<std::size_t>(v_) < filled_.size()) {
                        for (const std::size_t n : {next - static_cast<std::size_t>(v_), next + static_cast<std::size_t>(v_)}) {
                            prefetch(&flow_[n]);
                            prefetch(&h_[n]);
                            prefetch(&filled_[n]);
                        }
                    }
                }
                const auto idx32 = static_cast<std::uint32_t>(key & 0x1FFFFFFFu);
                const std::size_t idx = idx32;
                const auto z = static_cast<std::int32_t>(idx32 / static_cast<std::uint32_t>(v_));
                const std::int32_t x = static_cast<std::int32_t>(idx32) - z * v_;
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
            std::vector<std::uint64_t>().swap(heap);
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
            std::size_t deep = 0;   // Vertices under 10 cm of water or more.
            std::size_t basin = 0;  // Vertices in a basin region.
            for (std::size_t q = 0; q < component.size(); ++q) {
                const std::size_t idx = component[q];
                max_depth = std::max(max_depth, filled_[idx] - h_[idx]);
                deep += filled_[idx] - h_[idx] >= 100 ? 1 : 0;
                basin += in_basin(idx) ? 1 : 0;
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
            // A lake: deep somewhere and wide where it is not shallow (a wide
            // hollow barely wet but for one pit is filled in). Lakes belong
            // in the basins: elsewhere only a big one stays (phase 39).
            // "Lakes" (phase 56): at 100 % a lake is 70 cm deep somewhere and
            // 150 vertices wide; more lakes take smaller hollows, none at 0 %.
            const std::size_t easier = std::max<std::size_t>(1, s_.lakes);
            const bool allowed = basin * 2 >= component.size() || deep >= kFreeLake * 100 / easier;
            const bool is_lake = s_.lakes > 0 && max_depth >= static_cast<std::int32_t>(700 * 100 / easier) &&
                                 deep >= 150 * 100 / easier && allowed;
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
        drop_puddles();
        if (sea_mm_ > 0) {
            flood_sea();
        }
        return report(GenStage::Lakes, 100);
    }

    // Whether a town may start here: in a plain or hills and away from any
    // structure (phase 42).
    [[nodiscard]] bool town_ground(std::int32_t x, std::int32_t z) const {
        const std::uint16_t region = out_.owner_at(out_.region_owner, x, z);
        const LandformKind kind = region == 0 ? LandformKind::Sea : out_.landforms[region - 1u].kind;
        return (kind == LandformKind::Plain || kind == LandformKind::Hills) && out_.owner_at(out_.structure_owner, x, z) == 0;
    }

    // Whether a vertex lies in a basin region.
    [[nodiscard]] bool in_basin(std::size_t idx) const {
        const auto x = static_cast<std::int32_t>(idx % static_cast<std::size_t>(v_));
        const auto z = static_cast<std::int32_t>(idx / static_cast<std::size_t>(v_));
        const std::uint16_t owner = out_.owner_at(out_.region_owner, std::min(x, n_ - 1), std::min(z, n_ - 1));
        return owner != 0 && out_.landforms[owner - 1u].kind == LandformKind::Basin;
    }

    // Bits of a lake's shallow rim cut off from it by bumps of a few
    // centimeters dry up: water areas under 64 cells away from the border.
    void drop_puddles() {
        std::vector<std::uint8_t> seen(water_.size(), 0);
        std::vector<std::uint32_t> area;
        for (std::size_t start = 0; start < water_.size(); ++start) {
            if (water_[start] == 0 || seen[start] != 0) {
                continue;
            }
            area.assign(1, static_cast<std::uint32_t>(start));
            seen[start] = 1;
            bool border = false;
            for (std::size_t q = 0; q < area.size(); ++q) {
                const std::int32_t x = static_cast<std::int32_t>(area[q] % static_cast<std::uint32_t>(n_));
                const std::int32_t z = static_cast<std::int32_t>(area[q] / static_cast<std::uint32_t>(n_));
                border = border || x == 0 || z == 0 || x == n_ - 1 || z == n_ - 1;
                const std::int32_t nx[4] = {x - 1, x + 1, x, x};
                const std::int32_t nz[4] = {z, z, z - 1, z + 1};
                for (int k = 0; k < 4; ++k) {
                    if (nx[k] < 0 || nz[k] < 0 || nx[k] >= n_ || nz[k] >= n_) {
                        continue;
                    }
                    const std::size_t c = ci(nx[k], nz[k]);
                    if (water_[c] != 0 && seen[c] == 0) {
                        seen[c] = 1;
                        area.push_back(static_cast<std::uint32_t>(c));
                    }
                }
            }
            if (!border && area.size() < 64) {
                for (const std::uint32_t c : area) {
                    water_[c] = 0;
                    terrain_[c] = static_cast<std::uint8_t>(Terrain::Grass);
                }
            }
        }
    }

    // --- Rivers: follow the flow to the border or a lake ---------------------

    bool rivers() {
        bed_.assign(h_.size(), 0);
        const std::int32_t wanted = per_area(std::int64_t{10} * s_.rivers / 100);
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
        for (const Point& head : river_heads_) {
            const std::size_t v = vi(std::clamp(head.x, 0, v_ - 1), std::clamp(head.z, 0, v_ - 1));
            // The valleys and canyons all get the river they asked for.
            if (lake_[v] == 0) {
                sources.push_back(v);
            }
        }
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
        // Its course for the name, a point every few meters.
        std::vector<Point> course;
        const auto at = [&](std::size_t idx) {
            return Point{static_cast<std::int32_t>(idx % static_cast<std::size_t>(v_)),
                         static_cast<std::int32_t>(idx / static_cast<std::size_t>(v_))};
        };
        for (std::int64_t i = 0; i < length; ++i) {
            const std::size_t idx = path[static_cast<std::size_t>(i)];
            if (lake_[idx] != 0) {
                break;
            }
            if (i % kRiverCourseStep == 0) {
                course.push_back(at(idx));
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
        // The last carved point closes the course.
        for (std::int64_t i = length - 1; i >= 0; --i) {
            const std::size_t idx = path[static_cast<std::size_t>(i)];
            if (lake_[idx] == 0) {
                if (i % kRiverCourseStep != 0) {
                    course.push_back(at(idx));
                }
                break;
            }
        }
        if (course.size() >= 2) {
            // At most a point per step, so long rivers fit a save's limit.
            while (course.size() > kMaxLandformPoints) {
                std::vector<Point> half;
                for (std::size_t k = 0; k < course.size(); k += 2) {
                    half.push_back(course[k]);
                }
                if (half.back().x != course.back().x || half.back().z != course.back().z) {
                    half.push_back(course.back());
                }
                course = std::move(half);
            }
            record(LandformKind::River, course, kRiverWidth);
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
        // 9000 at 50 %, 3500 at 100 %, -2000 at 200 %; no forest at all at 0 %.
        const std::int32_t forest_threshold = s_.forests == 0     ? std::numeric_limits<std::int32_t>::max()
                                              : s_.forests <= 100 ? 3500 + (100 - s_.forests) * 110
                                                                  : 3500 - (s_.forests - 100) * 55;
        for (std::int32_t z = 0; z < n_; ++z) {
            FbmRow fertility_row(s_.seed ^ kFertilitySeed, z, 8, 4);
            FbmRow rock_row(s_.seed ^ kRockSeed, z, 7, 3);
            FbmRow beach_row(s_.seed ^ kBeachSeed, z, 6, 2);
            FbmRow clay_row(s_.seed ^ kClaySeed, z, 6, 2);
            FbmRow forest_row(s_.seed ^ kForestSeed, z, 8, 4);
            for (std::int32_t x = 0; x < n_; ++x) {
                const std::size_t c = ci(x, z);
                if (terrain_[c] == static_cast<std::uint8_t>(Terrain::Water)) {
                    continue;
                }
                const std::int32_t d = dist_[c];
                const std::int32_t slope = cell_slope(x, z);
                std::int32_t fert = 110 + fertility_row.at(x) * 60 / 32768;
                if (d <= 40) {
                    fert += (40 - d) * 2;
                }
                if (slope > 150) {
                    fert -= (slope - 150) / 4;
                }
                Terrain t = Terrain::Grass;
                const std::int32_t rock_noise = rock_row.at(x);
                if (slope > 450 || (rock_noise > 21000 && slope > 120) || rock_noise > 26000) {
                    t = Terrain::Rock;
                    fert = 0;
                } else if (d <= 2 + std::max<std::int32_t>(0, beach_row.at(x)) * 6 / 32768 &&
                           slope <= 250) {
                    // Beaches of 2 to 8 m, where the shore is not steep.
                    t = Terrain::Sand;
                    fert = std::min(fert, 60);
                } else if (d <= 30 && clay_row.at(x) > 17000) {
                    t = Terrain::Clay;
                    fert = std::min(fert, 90);
                } else {
                    std::int32_t mask = forest_row.at(x);
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

    // Distance in meters (4-neighbor steps, capped at 255) from every cell
    // to the nearest water cell that `pick` accepts.
    template <typename Pick>
    std::vector<std::uint8_t> water_distance(Pick pick) const {
        std::vector<std::uint8_t> dist(terrain_.size(), 255);
        std::vector<std::uint32_t> queue;
        for (std::size_t c = 0; c < dist.size(); ++c) {
            if (water_[c] != 0 && pick(c)) {
                dist[c] = 0;
                queue.push_back(static_cast<std::uint32_t>(c));
            }
        }
        for (std::size_t q = 0; q < queue.size(); ++q) {
            const std::size_t c = queue[q];
            const std::uint8_t d = dist[c];
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
                if (dist[n] > d + 1) {
                    dist[n] = static_cast<std::uint8_t>(d + 1);
                    queue.push_back(static_cast<std::uint32_t>(n));
                }
            }
        }
        return dist;
    }

    // Phase 54. Every 8 m block takes the biome that fits it best: by its
    // climate (a temperature that falls with the height and toward the
    // north, z = 0; a humidity that rises near water), by the water nearby,
    // by its region and by how high it lies among the map's land. A slow
    // noise of its own makes each biome win in patches where several fit.
    bool biomes() {
        const std::size_t cells = terrain_.size();
        biome_.assign(cells, 0);
        const std::size_t count = std::min<std::size_t>(flora_.biomes.size(), kMaxBiomes);
        std::vector<std::uint8_t> allowed;
        for (std::size_t b = 0; b < count; ++b) {
            if (s_.biomes == 0 || (b < 64 && ((s_.biomes >> b) & 1u) != 0)) {
                allowed.push_back(static_cast<std::uint8_t>(b));
            }
        }
        if (allowed.empty() && count > 0) {
            allowed.push_back(0);
        }
        if (allowed.size() <= 1) {
            biome_.assign(cells, allowed.empty() ? std::uint8_t{0} : allowed[0]);
            out_.climate.assign(static_cast<std::size_t>(out_.owner_side()) * static_cast<std::size_t>(out_.owner_side()), 0);
            return report(GenStage::Biomes, 100);
        }
        const bool sea = sea_mm_ > 0;
        const std::vector<std::uint8_t> fresh_m =
            water_distance([&](std::size_t c) { return !sea || water_[c] != sea_mm_; });
        const std::vector<std::uint8_t> sea_m =
            sea ? water_distance([&](std::size_t c) { return water_[c] == sea_mm_; }) : std::vector<std::uint8_t>(cells, 255);
        if (!report(GenStage::Biomes, 25)) {
            return false;
        }
        // How high each block lies among the land: the share of land below.
        std::int32_t lowest = std::numeric_limits<std::int32_t>::max();
        std::int32_t highest = 0;
        for (std::int32_t z = 0; z < n_; z += 2) {
            for (std::int32_t x = 0; x < n_; x += 2) {
                if (land(x, z)) {
                    lowest = std::min(lowest, h_[vi(x, z)]);
                    highest = std::max(highest, h_[vi(x, z)]);
                }
            }
        }
        if (lowest > highest) {
            return report(GenStage::Biomes, 100);  // No land.
        }
        constexpr std::int32_t kSteps = 1024;
        const std::int64_t range = std::max<std::int64_t>(1, highest - lowest);
        std::vector<std::uint32_t> below(kSteps + 1, 0);
        std::uint32_t land_cells = 0;
        for (std::int32_t z = 0; z < n_; z += 2) {
            for (std::int32_t x = 0; x < n_; x += 2) {
                if (land(x, z)) {
                    ++below[static_cast<std::size_t>((h_[vi(x, z)] - lowest) * std::int64_t{kSteps - 1} / range) + 1];
                    ++land_cells;
                }
            }
        }
        for (std::int32_t i = 1; i <= kSteps; ++i) {
            below[static_cast<std::size_t>(i)] += below[static_cast<std::size_t>(i - 1)];
        }
        const std::int32_t base = sea ? sea_mm_ : lowest;
        const std::int32_t side = out_.owner_side();
        out_.climate.assign(static_cast<std::size_t>(side) * static_cast<std::size_t>(side), 0);
        for (std::int32_t bz = 0; bz < n_; bz += kOwnerBlock) {
            for (std::int32_t bx = 0; bx < n_; bx += kOwnerBlock) {
                const std::int32_t cx = std::min(n_ - 1, bx + kOwnerBlock / 2);
                const std::int32_t cz = std::min(n_ - 1, bz + kOwnerBlock / 2);
                const std::size_t c = ci(cx, cz);
                const std::int32_t height = h_[vi(cx, cz)];
                // Temperature: 20 in the north to 80 in the south at 100 % and the widest range,
                // a degree less every 5 m of height, and a slow noise.
                std::int32_t temp = 50 + (static_cast<std::int32_t>(s_.temperature) - 100) * 3 / 10 +
                                    (2 * cz - n_) * static_cast<std::int32_t>(s_.climate_range) / n_ -
                                    std::max(0, height - base) / 5000 +
                                    fbm(s_.seed ^ kTemperatureSeed, cx, cz, 8, 2) * 8 / 32768;
                // Humidity: a slow noise, wetter within 60 m of water.
                const std::int32_t water_m = std::min<std::int32_t>(fresh_m[c], sea_m[c]);
                std::int32_t hum = 50 + (static_cast<std::int32_t>(s_.humidity) - 100) * 3 / 10 +
                                   fbm(s_.seed ^ kHumiditySeed, cx, cz, 9, 3) * 34 / 32768 +
                                   (water_m < 60 ? (60 - water_m) / 3 : 0);
                temp = std::clamp(temp, 0, 100);
                hum = std::clamp(hum, 0, 100);
                const auto step = static_cast<std::size_t>(std::clamp<std::int64_t>(
                    (height - lowest) * std::int64_t{kSteps - 1} / range, 0, kSteps - 1));
                const auto alt = static_cast<std::int32_t>(std::uint64_t{below[step]} * 100 / std::max<std::uint32_t>(1, land_cells));
                const std::uint16_t region = out_.owner_at(out_.region_owner, cx, cz);
                std::uint8_t kind_bit = 0;
                if (region != 0 && region - 1u < out_.landforms.size()) {
                    switch (out_.landforms[region - 1u].kind) {
                        case LandformKind::Plain: kind_bit = 1u << static_cast<unsigned>(BiomeRegion::Plain); break;
                        case LandformKind::Hills: kind_bit = 1u << static_cast<unsigned>(BiomeRegion::Hills); break;
                        case LandformKind::Mountains: kind_bit = 1u << static_cast<unsigned>(BiomeRegion::Mountains); break;
                        case LandformKind::Plateau: kind_bit = 1u << static_cast<unsigned>(BiomeRegion::Plateau); break;
                        case LandformKind::Basin: kind_bit = 1u << static_cast<unsigned>(BiomeRegion::Basin); break;
                        default: break;
                    }
                }
                // The best of those whose place this can be; if none, the nearest in climate.
                std::int64_t best = std::numeric_limits<std::int64_t>::min();
                std::uint8_t pick = allowed[0];
                for (int strict = 1; strict >= 0 && best == std::numeric_limits<std::int64_t>::min(); --strict) {
                    for (const std::uint8_t b : allowed) {
                        const BiomeDef& d = flora_.biomes[b];
                        const auto outside = [](std::int32_t v, const std::uint8_t* r) {
                            return v < r[0] ? r[0] - v : v > r[1] ? v - r[1] : 0;
                        };
                        const std::int32_t off_t = outside(temp, d.temperature);
                        const std::int32_t off_h = outside(hum, d.humidity);
                        // The water it needs and its height are never given up; its
                        // climate and its region are, where nothing else fits.
                        if (outside(alt, d.altitude) > 0 || (d.water == BiomeWater::Fresh && fresh_m[c] > d.water_m) ||
                            (d.water == BiomeWater::Sea && sea_m[c] > d.water_m)) {
                            continue;
                        }
                        if (strict != 0 && (off_t > kClimateSlack || off_h > kClimateSlack ||
                                            (d.regions != 0 && (d.regions & kind_bit) == 0))) {
                            continue;
                        }
                        // Its own slow noise, 0 to 1024: where it is high, the biome wins.
                        const std::int64_t patch =
                            (fbm(mix64(s_.seed ^ kBiomeSeed ^ (b + 1u)), cx, cz, 8, 2) + 32768) * 1024 / 65536;
                        const std::int64_t score = 10000 - (off_t * 40 + off_h * 30) * 10 + d.weight * patch / 16;
                        if (score > best) {
                            best = score;
                            pick = b;
                        }
                    }
                }
                for (std::int32_t z = bz; z < std::min(n_, bz + kOwnerBlock); ++z) {
                    for (std::int32_t x = bx; x < std::min(n_, bx + kOwnerBlock); ++x) {
                        biome_[ci(x, z)] = pick;
                    }
                }
                // For F3 and the map report: temperature and humidity.
                out_.climate[static_cast<std::size_t>(bz / kOwnerBlock) * static_cast<std::size_t>(side) +
                             static_cast<std::size_t>(bx / kOwnerBlock)] =
                    static_cast<std::uint16_t>(temp | (hum << 8));
            }
            if ((bz & 127) == 0 && !report(GenStage::Biomes, 25 + bz * 75 / n_)) {
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
        if (flora_.biomes.empty() || flora_.species.empty()) {
            return report(GenStage::Forests, 100);
        }
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
                        total += static_cast<std::int64_t>(biome.size_weights[k]);
                    }
                    const std::int64_t share = static_cast<std::int64_t>(biome.size_weights[pass]);
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
        const std::int64_t k = s_.resources;  // In fiftieths: 100 % is 2.
        std::int32_t x = 0;
        std::int32_t z = 0;
        const auto any = [](std::int32_t, std::int32_t) { return true; };
        const auto rocky = [this](std::int32_t cx, std::int32_t cz) {
            return cell_slope(cx, cz) + (cell_terrain(cx, cz) == Terrain::Rock ? 1000 : 0);
        };
        const std::int32_t stones = per_area(125 * k / 50);
        for (std::int32_t i = 0; i < stones; ++i) {
            if (pick_cell(8, any, rocky, x, z)) {
                cluster(FeatureType::Stone, x, z, rng_.range(1, 3), 5, 100, 220);
            }
        }
        if (!report(GenStage::Resources, 25)) {
            return false;
        }
        const std::int32_t ores = per_area(30 * k / 50);
        for (std::int32_t i = 0; i < ores; ++i) {
            if (pick_cell(16, any, rocky, x, z)) {
                cluster(FeatureType::IronOre, x, z, rng_.range(1, 2), 4, 100, 170);
            }
        }
        const auto forest_edge = [this](std::int32_t cx, std::int32_t cz) {
            const Terrain t = cell_terrain(cx, cz);
            return (t == Terrain::ForestFloor && forest_[ci(cx, cz)] < 40) || t == Terrain::Meadow;
        };
        const std::int32_t berries = per_area(100 * k / 50);
        for (std::int32_t i = 0; i < berries; ++i) {
            if (pick_cell(10, forest_edge, {}, x, z)) {
                cluster(FeatureType::BerryBush, x, z, rng_.range(2, 4), 6, 80, 130);
            }
        }
        const auto deep_forest = [this](std::int32_t cx, std::int32_t cz) {
            return cell_terrain(cx, cz) == Terrain::ForestFloor && forest_[ci(cx, cz)] >= 60;
        };
        const std::int32_t herbs = per_area(75 * k / 50);
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

    // Whether a feature goes to make room for a town center (big trees keep
    // farther away, so their crowns stay outside).
    [[nodiscard]] bool cleared(const MapFeature& f) const {
        const std::int64_t reach = f.type == FeatureType::Tree
                                       ? meters2(kStartClearRadius + size_info(static_cast<TreeSize>(f.size)).spacing_m)
                                       : meters2(kStartClearRadius);
        return std::any_of(out_.starts.begin(), out_.starts.end(),
                           [&](const StartPosition& s) { return d2(f.x, f.z, s.x, s.z) <= reach; });
    }

    // What a start will have within `radius`: what is cleared for the town
    // centers does not count (phase 49, D-4907).
    [[nodiscard]] std::int32_t count_near(FeatureType type, Fixed x, Fixed z, std::int32_t radius) const {
        std::int32_t n = 0;
        const std::int64_t r2 = meters2(radius);
        for (const MapFeature& f : out_.features) {
            if (f.type == type && d2(f.x, f.z, x, z) <= r2 && !cleared(f)) {
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
                if (d >= 12 && d <= kStartMaxWaterDistance && town_ground(x, z)) {
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
        const std::int64_t safe = meters2(250);
        std::erase_if(out_.features, [&](const MapFeature& f) { return cleared(f); });
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

    // --- Giants (phase 55) ---------------------------------------------------------

    // A few giant trees as landmarks: each in a clearing of its biome, far
    // from the towns' starts and from each other. A giant whose biome the
    // map lacks is left out.
    void giants() {
        std::vector<std::uint8_t> kinds;
        for (std::size_t s = 0; s < flora_.species.size() && s < kMaxSpecies; ++s) {
            if (flora_.species[s].giant_biome >= 0) {
                kinds.push_back(static_cast<std::uint8_t>(s));
            }
        }
        static constexpr std::int32_t kCount[] = {2, 3, 6, 10, 18, 30};  // By map size, at 100 %.
        const std::int32_t wanted =
            (kCount[std::min<std::size_t>(static_cast<std::size_t>(s_.size), std::size(kCount) - 1)] * s_.giants + 50) / 100;
        if (kinds.empty() || wanted <= 0) {
            return;
        }
        const bool sea = sea_mm_ > 0;
        // Only when a giant asks for its water nearby.
        std::vector<std::uint8_t> fresh_m, sea_m;
        for (const std::uint8_t k : kinds) {
            const SpeciesDef& sp = flora_.species[k];
            const BiomeWater water = flora_.biomes[static_cast<std::size_t>(sp.giant_biome)].water;
            if (sp.giant_water_m != 0 && water == BiomeWater::Fresh && fresh_m.empty()) {
                fresh_m = water_distance([&](std::size_t c) { return !sea || water_[c] != sea_mm_; });
            } else if (sp.giant_water_m != 0 && water == BiomeWater::Sea && sea_m.empty() && sea) {
                sea_m = water_distance([&](std::size_t c) { return water_[c] == sea_mm_; });
            }
        }
        struct Spot {
            std::int32_t x, z;
        };
        std::vector<Spot> placed;
        const std::int64_t apart = std::max<std::int64_t>(kGiantApart, n_ / 8);
        // The kinds take turns, starting with one the seed picks; each takes
        // the free spot of its biome with the best hash.
        const std::size_t first = static_cast<std::size_t>(mix64(s_.seed ^ kGiantSeed) % kinds.size());
        std::int32_t misses = 0;
        for (std::size_t turn = 0; static_cast<std::int32_t>(placed.size()) < wanted && misses < static_cast<std::int32_t>(kinds.size()); ++turn) {
            const std::uint8_t kind = kinds[(first + turn) % kinds.size()];
            const SpeciesDef& sp = flora_.species[kind];
            const BiomeWater water = flora_.biomes[static_cast<std::size_t>(sp.giant_biome)].water;
            bool found = false;
            std::uint64_t best = 0;
            Spot spot{0, 0};
            for (std::int32_t z = kGiantClearing; z < n_ - kGiantClearing; z += kOwnerBlock) {
                for (std::int32_t x = kGiantClearing; x < n_ - kGiantClearing; x += kOwnerBlock) {
                    const std::size_t c = ci(x, z);
                    if (biome_[c] != sp.giant_biome || !land(x, z) || cell_slope(x, z) > kGiantSlope) {
                        continue;
                    }
                    const Terrain t = cell_terrain(x, z);
                    if (t == Terrain::Rock || t == Terrain::Water) {
                        continue;
                    }
                    if (sp.giant_water_m != 0) {
                        const std::vector<std::uint8_t>& dist = water == BiomeWater::Sea ? sea_m : fresh_m;
                        if (dist.empty() || dist[c] > sp.giant_water_m) {
                            continue;
                        }
                    }
                    const auto far_from = [&](std::int64_t px, std::int64_t pz, std::int64_t meters) {
                        return (px - x) * (px - x) + (pz - z) * (pz - z) >= meters * meters;
                    };
                    bool free_spot = true;
                    for (const StartPosition& st : out_.starts) {
                        free_spot = free_spot && far_from(st.x.floor_int(), st.z.floor_int(), kGiantFromStart);
                    }
                    for (const Spot& p : placed) {
                        free_spot = free_spot && far_from(p.x, p.z, apart);
                    }
                    const std::uint64_t hash = point_hash(kGiantSeed + kind, x, z);
                    if (free_spot && (!found || hash > best)) {
                        found = true;
                        best = hash;
                        spot = {x, z};
                    }
                }
            }
            if (!found) {
                ++misses;
                continue;
            }
            misses = 0;
            placed.push_back(spot);
            // Its clearing: the trees around make way.
            std::erase_if(out_.features, [&](const MapFeature& f) {
                const std::int64_t dx = f.x.floor_int() - spot.x, dz = f.z.floor_int() - spot.z;
                return f.type == FeatureType::Tree && dx * dx + dz * dz < std::int64_t{kGiantClearing} * kGiantClearing;
            });
            const SizeInfo& si = size_info(TreeSize::Huge);
            const std::int64_t height = si.min_cm + static_cast<std::int64_t>((best >> 44) % static_cast<std::uint64_t>(si.max_cm - si.min_cm + 1));
            MapFeature f;
            f.type = FeatureType::Tree;
            f.species = kind;
            f.size = static_cast<std::uint8_t>(TreeSize::Huge);
            f.x = cell_center(spot.x);
            f.z = cell_center(spot.z);
            f.scale = Fixed::from_ratio(height, si.model_cm);
            f.rotation = static_cast<std::uint16_t>(best >> 28);
            out_.features.push_back(f);
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
        out_.sea_levels.assign(1, static_cast<std::uint16_t>(std::clamp(sea_mm_ / 10, 0, 65535)));
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
    std::vector<Island> islands_;       // Map type with islands: main islands first.
    std::int32_t sea_mm_ = 0;           // Sea surface, millimeters; 0 without a sea.

    // Keeps a landform in the map, for its name under the cursor.
    void record(LandformKind kind, const std::vector<Point>& points, std::int32_t width) {
        Landform l;
        l.kind = kind;
        l.width = width;
        for (const Point& pt : points) {
            l.points.push_back({pt.x, pt.z});
        }
        out_.landforms.push_back(std::move(l));
    }

    std::vector<Point> river_heads_;  // Where the valleys and canyons ask for a river.
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
    world.sea_levels.assign(static_cast<std::size_t>(k) * static_cast<std::size_t>(k), 0);
    const auto squares = static_cast<std::size_t>(world.owner_side()) * static_cast<std::size_t>(world.owner_side());
    world.region_owner.assign(squares, 0);
    world.structure_owner.assign(squares, 0);
    world.climate.assign(squares, 0);
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
        // Each map's owners name its landforms, now further along the list.
        const auto first = static_cast<std::uint16_t>(world.landforms.size());
        if (!m->region_owner.empty()) {
            const std::int32_t from = m->owner_side();
            const std::int32_t to = world.owner_side();
            const auto bx = static_cast<std::int32_t>(ox) / kOwnerBlock;
            const auto bz = static_cast<std::int32_t>(oz) / kOwnerBlock;
            for (std::int32_t z = 0; z < from; ++z) {
                for (std::int32_t x = 0; x < from; ++x) {
                    const auto src = static_cast<std::size_t>(z * from + x);
                    const auto dst = static_cast<std::size_t>((bz + z) * to + bx + x);
                    for (auto [a, b] : {std::pair{&m->region_owner, &world.region_owner},
                                        std::pair{&m->structure_owner, &world.structure_owner}}) {
                        (*b)[dst] = (*a)[src] == 0 ? 0 : static_cast<std::uint16_t>((*a)[src] + first);
                    }
                    if (src < m->climate.size()) {
                        world.climate[dst] = m->climate[src];
                    }
                }
            }
        }
        for (Landform l : m->landforms) {
            for (auto& pt : l.points) {
                pt[0] += static_cast<std::int32_t>(ox);
                pt[1] += static_cast<std::int32_t>(oz);
            }
            world.landforms.push_back(std::move(l));
        }
        world.sea_levels[static_cast<std::size_t>(i)] = m->sea_levels.empty() ? 0 : m->sea_levels[0];
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
        world.sea_levels[static_cast<std::size_t>(i)] = static_cast<std::uint16_t>(std::max(100, static_cast<int>(lowest) - 100));
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
    const std::int64_t reach = static_cast<std::int64_t>(radius) + gap / 2;
    return reach * reach * 22 / 7;
}

}  // namespace

std::vector<Island> island_layout(std::uint64_t seed, std::int32_t cells, std::int32_t towns, std::int32_t per_town) {
    towns = std::max(1, towns);
    per_town = std::clamp(per_town, 1, static_cast<std::int32_t>(kMaxIslandsPerTown));
    Rng rng(seed ^ kIslandSeed, 11);
    // Archipelagos: each town's main island weighs 5, its others 0.8 to
    // 1.8, biggest first. The discs cover 60 % of the map; with their bent
    // shapes about a third of it is land.
    struct Wanted {
        std::int64_t weight = 0;
        std::uint8_t town = 0;
    };
    std::vector<Wanted> wanted;
    for (std::int32_t t = 0; t < towns; ++t) {
        wanted.push_back({500, static_cast<std::uint8_t>(t)});
    }
    for (std::int32_t t = 0; t < towns; ++t) {
        std::vector<std::int64_t> w;
        for (std::int32_t k = 1; k < per_town; ++k) {
            w.push_back(rng.range(80, 180));
        }
        std::sort(w.begin(), w.end(), std::greater<>());
        for (const std::int64_t v : w) {
            wanted.push_back({v, static_cast<std::uint8_t>(t)});
        }
    }
    std::int64_t total = 0;
    for (const Wanted& w : wanted) {
        total += w.weight;
    }
    const std::int64_t land = static_cast<std::int64_t>(cells) * cells * 60 / 100;
    std::vector<std::int32_t> radius(wanted.size());
    for (std::size_t i = 0; i < radius.size(); ++i) {
        radius[i] = std::max<std::int32_t>(
            12, static_cast<std::int32_t>(isqrt(static_cast<std::uint64_t>(wanted[i].weight * land * 7 / (total * 22)))));
    }
    const std::int32_t edge = island_edge(cells);
    const std::int32_t gap = island_gap(cells);
    // The discs may not overlap; the channels between the islands keep them apart.
    const auto reach_of = [](std::int32_t r) { return static_cast<std::int64_t>(r); };
    std::vector<Island> out;
    // Placed one by one where they fit; if some island finds no room, all
    // shrink a little and the placement starts over.
    for (int round = 0; round < 60; ++round) {
        out.clear();
        bool ok = true;
        for (std::size_t i = 0; i < wanted.size() && ok; ++i) {
            const std::int32_t r = radius[i];
            const std::int64_t reach = reach_of(r);
            const std::int64_t lo = edge + reach;
            const std::int64_t hi = cells - edge - reach;
            if (lo > hi) {
                ok = false;
                break;
            }
            const bool main = static_cast<std::int32_t>(i) < towns;
            const auto fits = [&](const Island& c) {
                if (c.x < lo || c.x > hi || c.z < lo || c.z > hi) {
                    return false;
                }
                return std::all_of(out.begin(), out.end(), [&](const Island& o) {
                    const std::int64_t dx = c.x - o.x;
                    const std::int64_t dz = c.z - o.z;
                    const std::int64_t apart = reach + reach_of(o.radius) + gap;
                    return dx * dx + dz * dz >= apart * apart;
                });
            };
            const auto d2 = [](const Island& a, const Island& b) {
                return static_cast<std::int64_t>(a.x - b.x) * (a.x - b.x) + static_cast<std::int64_t>(a.z - b.z) * (a.z - b.z);
            };
            bool found = false;
            Island best;
            if (main) {
                // Main islands as far from each other as they can.
                std::int64_t best_score = -1;
                for (int t = 0; t < 48; ++t) {
                    const Island c{rng.range(static_cast<std::int32_t>(lo), static_cast<std::int32_t>(hi)),
                                   rng.range(static_cast<std::int32_t>(lo), static_cast<std::int32_t>(hi)), r, wanted[i].town};
                    if (!fits(c)) {
                        continue;
                    }
                    std::int64_t nearest = INT64_MAX;
                    for (const Island& o : out) {
                        nearest = std::min(nearest, d2(c, o));
                    }
                    if (nearest > best_score) {
                        best_score = nearest;
                        best = c;
                        found = true;
                    }
                }
            } else {
                // The others around their town's main island, nearer to it
                // than to any other main island.
                const Island& home = out[wanted[i].town];
                const std::int64_t ring = reach_of(home.radius) + reach + gap;
                for (int t = 0; t < 160 && !found; ++t) {
                    const Angle a = rng.angle();
                    const std::int64_t d = ring + rng.range(0, std::max(gap, home.radius / 2) * (1 + t / 40));
                    const Island c{home.x + (cos(a) * Fixed::from_int(static_cast<std::int32_t>(d))).floor_int(),
                                   home.z + (sin(a) * Fixed::from_int(static_cast<std::int32_t>(d))).floor_int(), r,
                                   wanted[i].town};
                    if (!fits(c)) {
                        continue;
                    }
                    bool own = true;
                    for (std::int32_t m = 0; m < towns && own; ++m) {
                        own = m == wanted[i].town || d2(c, out[static_cast<std::size_t>(m)]) > d2(c, home);
                    }
                    if (own) {
                        best = c;
                        found = true;
                    }
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
    // Room for a town: a main island of 110 m at least; the others 40 m.
    const std::int32_t cells = map_cells(size);
    const std::int32_t gap = island_gap(cells);
    const std::int64_t budget = static_cast<std::int64_t>(cells) * cells * 35 / 100;
    const std::int64_t home = island_footprint(110, gap);
    const std::int64_t other = island_footprint(40, gap);
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
