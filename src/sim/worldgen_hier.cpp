#include "sim/worldgen_hier.h"

#include <algorithm>
#include <array>
#include <utility>

#include "sim/fixed.h"
#include "sim/noise.h"
#include "sim/rng.h"

namespace sc::sim::hier {

namespace {

// A value for a percent setting (0..200) that goes through four points: at
// 0, 50, 100 and 200 %, in straight lines between them.
[[nodiscard]] std::int32_t by_percent(std::int32_t percent, std::int32_t at0, std::int32_t at50, std::int32_t at100,
                                      std::int32_t at200) {
    if (percent <= 50) {
        return at0 + (at50 - at0) * percent / 50;
    }
    if (percent <= 100) {
        return at50 + (at100 - at50) * (percent - 50) / 50;
    }
    return at100 + (at200 - at100) * (std::min(percent, 200) - 100) / 100;
}

// Seeds for each noise field and random stream, so they are unrelated.
constexpr std::uint64_t kRegionSeed = 0x4849455252454730ull;
constexpr std::uint64_t kWarpXSeed = 0x4849455257415831ull;
constexpr std::uint64_t kWarpZSeed = 0x4849455257415a32ull;
constexpr std::uint64_t kRoleSeed = 0x48494552524f4c33ull;
constexpr std::uint64_t kDetailSeed = 0x4849455244455434ull;
constexpr std::uint64_t kMicroSeed = 0x484945524d494335ull;
constexpr std::uint64_t kBumpSeed = 0x4849455242554d36ull;
constexpr std::uint64_t kRagXSeed = 0x4849455252414737ull;
constexpr std::uint64_t kRagZSeed = 0x4849455252414738ull;
constexpr std::uint64_t kStructSeed = 0x4849455253545239ull;
constexpr std::uint64_t kPeakSeed = 0x484945525045414bull;
constexpr std::uint64_t kSeaSeed = 0x484945525345414cull;
constexpr std::uint64_t kShoreSeed = 0x48494552534f524dull;

enum class Role : std::uint8_t { Plain, Hills, Mountains, Plateau, Basin, Sea };

// Where the sea goes on a map with a coast, and the small bits of it.
struct Disc {
    std::int32_t x = 0;
    std::int32_t z = 0;
    std::int32_t radius = 0;
};

LandformKind role_kind(Role r) {
    switch (r) {
        case Role::Hills: return LandformKind::Hills;
        case Role::Mountains: return LandformKind::Mountains;
        case Role::Plateau: return LandformKind::Plateau;
        case Role::Basin: return LandformKind::Basin;
        case Role::Sea: return LandformKind::Sea;
        case Role::Plain: break;
    }
    return LandformKind::Plain;
}

struct Region {
    std::int32_t x = 0;  // Center, meters (may lie a little off the map).
    std::int32_t z = 0;
    Role role = Role::Plain;
    std::int32_t height = 0;  // Base height, millimeters.
    std::int32_t rough = 0;   // Amplitude of its broad swells, millimeters.
    std::int32_t bumps = 0;   // Amplitude of its small bumps, millimeters.
    std::int32_t blocks = 0;  // Squares of the map it covers.
    std::vector<std::uint32_t> neighbors;
};

// Smallest power of two exponent with 2^k >= v.
int log2_ceil(std::int32_t v) {
    int k = 0;
    while ((1 << k) < v && k < 30) {
        ++k;
    }
    return k;
}

class Shaper {
public:
    Shaper(const MapSettings& s, std::int32_t n, bool islands, const Progress& progress, Ground& out)
        : s_(s), n_(n), v_(n + 1), island_type_(islands), progress_(progress), out_(out), spacing_(region_spacing(n)),
          grid_((n + spacing_ - 1) / spacing_), warp_log2_(log2_ceil(spacing_) - 1), side_((n + kOwnerBlock - 1) / kOwnerBlock) {}

    bool run() {
        place_regions();
        if (!find_owners()) {
            return false;
        }
        find_neighbors();
        plan_sea();
        assign_roles();
        shape_coast();
        set_heights();
        record_regions();
        if (!base_field()) {
            return false;
        }
        own_water();
        if (!vertices() || !structures()) {
            return false;
        }
        return report(100);
    }

private:
    const MapSettings& s_;
    std::int32_t n_;
    std::int32_t v_;
    bool island_type_;
    const Progress& progress_;
    Ground& out_;
    std::int32_t spacing_;
    std::int32_t grid_;       // Region centers per side.
    int warp_log2_;
    std::int32_t side_;       // Owner squares per side.
    std::vector<Region> regions_;
    std::vector<std::vector<std::uint32_t>> chains_;  // Mountain regions, in chains.
    // Base height and bump amplitude at the corners of the owner squares,
    // (side + 1)^2, millimeters.
    std::vector<std::int32_t> base_;
    std::vector<std::int32_t> rough_;
    std::vector<std::int32_t> bumps_;
    std::vector<std::int32_t> mountain_;  // How much of it is mountains, 0..65536.
    std::vector<std::int32_t> land_;      // How much of it is land (not sea), 0..65536.
    std::vector<std::uint8_t> cliff_;     // A plateau's rim near: its vertices are sampled one by one.
    // Level 0: the sea. Its surface (millimeters, 0 without a sea), the
    // islands of a map type with islands, and on a coast the regions that
    // became gulfs or peninsulas and the islets off it.
    std::int32_t sea_mm_ = 0;
    std::vector<Disc> islets_;
    std::vector<std::uint32_t> gulfs_;
    std::vector<std::uint32_t> peninsulas_;
    std::uint16_t sea_owner_ = 0;  // The open sea's landform, index + 1.

    bool report(int percent) { return !progress_ || progress_(percent); }

    // --- Level 1: regions --------------------------------------------------------

    // A center in each cell of a grid, moved at random within it.
    void place_regions() {
        Rng rng(s_.seed ^ kRegionSeed, 39);
        regions_.resize(static_cast<std::size_t>(grid_) * static_cast<std::size_t>(grid_));
        for (std::int32_t j = 0; j < grid_; ++j) {
            for (std::int32_t i = 0; i < grid_; ++i) {
                Region& r = regions_[static_cast<std::size_t>(j * grid_ + i)];
                r.x = i * spacing_ + rng.range(spacing_ * 15 / 100, spacing_ * 85 / 100);
                r.z = j * spacing_ + rng.range(spacing_ * 15 / 100, spacing_ * 85 / 100);
            }
        }
    }

    // The point (x, z) moved by noise, so region borders bend widely and
    // are ragged up close (a plateau's rim is not a straight line).
    [[nodiscard]] std::pair<std::int64_t, std::int64_t> warped(std::int32_t x, std::int32_t z) const {
        const std::int64_t w = spacing_ * 30 / 100;
        constexpr std::int64_t kRag = 14;
        return {x + fbm(s_.seed ^ kWarpXSeed, x, z, warp_log2_, 3) * w / 32768 + fbm(s_.seed ^ kRagXSeed, x, z, 5, 2) * kRag / 32768,
                z + fbm(s_.seed ^ kWarpZSeed, x, z, warp_log2_, 3) * w / 32768 + fbm(s_.seed ^ kRagZSeed, x, z, 5, 2) * kRag / 32768};
    }

    // The region centers near a warped point: the grid cells around it.
    template <typename Fn>
    void around(std::int64_t qx, std::int64_t qz, Fn&& fn) const {
        const auto ci = static_cast<std::int32_t>(std::clamp<std::int64_t>(qx / spacing_, 0, grid_ - 1));
        const auto cj = static_cast<std::int32_t>(std::clamp<std::int64_t>(qz / spacing_, 0, grid_ - 1));
        for (std::int32_t j = std::max(0, cj - 2); j <= std::min(grid_ - 1, cj + 2); ++j) {
            for (std::int32_t i = std::max(0, ci - 2); i <= std::min(grid_ - 1, ci + 2); ++i) {
                const auto id = static_cast<std::uint32_t>(j * grid_ + i);
                const Region& r = regions_[id];
                const std::int64_t dx = qx - r.x;
                const std::int64_t dz = qz - r.z;
                fn(id, dx * dx + dz * dz);
            }
        }
    }

    [[nodiscard]] std::uint32_t nearest(std::int32_t x, std::int32_t z) const {
        const auto [qx, qz] = warped(x, z);
        std::uint32_t best = 0;
        std::int64_t best_d = INT64_MAX;
        around(qx, qz, [&](std::uint32_t id, std::int64_t d2) {
            if (d2 < best_d) {
                best_d = d2;
                best = id;
            }
        });
        return best;
    }

    // Which region each square's middle is in.
    bool find_owners() {
        out_.region_owner.assign(static_cast<std::size_t>(side_) * static_cast<std::size_t>(side_), 0);
        for (std::int32_t bz = 0; bz < side_; ++bz) {
            for (std::int32_t bx = 0; bx < side_; ++bx) {
                const std::uint32_t id = nearest(std::min(n_ - 1, bx * kOwnerBlock + kOwnerBlock / 2),
                                                 std::min(n_ - 1, bz * kOwnerBlock + kOwnerBlock / 2));
                out_.region_owner[static_cast<std::size_t>(bz * side_ + bx)] = static_cast<std::uint16_t>(id + 1);
                ++regions_[id].blocks;
            }
            if ((bz & 63) == 0 && !report(bz * 20 / side_)) {
                return false;
            }
        }
        return true;
    }

    // Regions that share a border.
    void find_neighbors() {
        std::vector<std::pair<std::uint32_t, std::uint32_t>> pairs;
        const auto link = [&](std::uint16_t a, std::uint16_t b) {
            if (a != b) {
                pairs.emplace_back(std::min(a, b) - 1u, std::max(a, b) - 1u);
            }
        };
        for (std::int32_t bz = 0; bz < side_; ++bz) {
            for (std::int32_t bx = 0; bx < side_; ++bx) {
                const std::uint16_t here = out_.region_owner[static_cast<std::size_t>(bz * side_ + bx)];
                if (bx + 1 < side_) {
                    link(here, out_.region_owner[static_cast<std::size_t>(bz * side_ + bx + 1)]);
                }
                if (bz + 1 < side_) {
                    link(here, out_.region_owner[static_cast<std::size_t>((bz + 1) * side_ + bx)]);
                }
            }
        }
        std::sort(pairs.begin(), pairs.end());
        pairs.erase(std::unique(pairs.begin(), pairs.end()), pairs.end());
        for (const auto& [a, b] : pairs) {
            regions_[a].neighbors.push_back(b);
            regions_[b].neighbors.push_back(a);
        }
    }

    [[nodiscard]] bool touches(const Region& r, Role role) const {
        return std::any_of(r.neighbors.begin(), r.neighbors.end(), [&](std::uint32_t id) { return regions_[id].role == role; });
    }

    // How many of each role, then where: mountains in chains, plateaus and
    // basins alone, hills around the mountains first.
    void assign_roles() {
        Rng rng(s_.seed ^ kRoleSeed, 39);
        std::vector<std::uint32_t> on_map;  // The land regions on the map.
        for (std::uint32_t id = 0; id < regions_.size(); ++id) {
            if (regions_[id].blocks > 0 && regions_[id].role != Role::Sea) {
                on_map.push_back(id);
            }
        }
        const auto m = static_cast<std::int32_t>(on_map.size());
        const std::int32_t percent = by_percent(s_.landforms, 0, 30, 45, 60);
        const std::int32_t others = m * percent / 100;
        const std::int32_t share = by_percent(s_.relief, 5, 20, 35, 60);
        std::int32_t mountains = others * share / 100;
        std::int32_t plateaus = std::max(m >= 8 && s_.landforms > 0 ? 1 : 0, others * 15 / 100);
        // Lakes lie in the basins: "Lakes" gives more or fewer of them.
        std::int32_t basins = std::max(m >= 6 && s_.lakes > 0 ? 1 : 0, others * 10 * s_.lakes / 10000);
        std::int32_t hills = std::max(0, others - mountains - plateaus - basins);

        // A random plain region passing `ok`, or none.
        const auto pick = [&](const auto& ok) -> std::int64_t {
            std::vector<std::uint32_t> list;
            for (const std::uint32_t id : on_map) {
                if (regions_[id].role == Role::Plain && ok(regions_[id])) {
                    list.push_back(id);
                }
            }
            return list.empty() ? -1 : static_cast<std::int64_t>(list[rng.below(static_cast<std::uint32_t>(list.size()))]);
        };
        const auto any = [](const Region&) { return true; };

        // Chains of two to four regions, heading one way.
        while (mountains > 0) {
            const std::int64_t first = pick(any);
            if (first < 0) {
                break;
            }
            const Angle dir = rng.angle();
            const std::int64_t dx = cos(dir).raw();
            const std::int64_t dz = sin(dir).raw();
            auto cur = static_cast<std::uint32_t>(first);
            const std::int32_t length = rng.range(2, 4);
            chains_.emplace_back();
            for (std::int32_t k = 0; k < length && mountains > 0; ++k) {
                regions_[cur].role = Role::Mountains;
                chains_.back().push_back(cur);
                --mountains;
                std::int64_t best = 0;
                std::int64_t next = -1;
                for (const std::uint32_t nb : regions_[cur].neighbors) {
                    const Region& r = regions_[nb];
                    const std::int64_t along = (r.x - regions_[cur].x) * dx + (r.z - regions_[cur].z) * dz;
                    if (r.role == Role::Plain && r.blocks > 0 && along > best) {
                        best = along;
                        next = nb;
                    }
                }
                if (next < 0) {
                    break;
                }
                cur = static_cast<std::uint32_t>(next);
            }
        }
        for (; plateaus > 0; --plateaus) {
            const std::int64_t id = pick([&](const Region& r) {
                return !touches(r, Role::Plateau) && !touches(r, Role::Basin) && !touches(r, Role::Sea);
            });
            if (id < 0) {
                break;
            }
            regions_[static_cast<std::size_t>(id)].role = Role::Plateau;
        }
        for (; basins > 0; --basins) {
            const std::int64_t id = pick([&](const Region& r) {
                return !touches(r, Role::Basin) && !touches(r, Role::Plateau) && !touches(r, Role::Sea);
            });
            if (id < 0) {
                break;
            }
            regions_[static_cast<std::size_t>(id)].role = Role::Basin;
        }
        for (; hills > 0; --hills) {
            std::int64_t id = pick([&](const Region& r) { return touches(r, Role::Mountains); });
            if (id < 0) {
                id = pick(any);
            }
            if (id < 0) {
                break;
            }
            regions_[static_cast<std::size_t>(id)].role = Role::Hills;
        }
    }

    // How tall the relief may be for the regions' size, 32768..65536
    // (1/65536): half with regions of 150 m, all from 300 m. Small regions
    // with the heights of big ones were all cliff and ramp.
    [[nodiscard]] std::int64_t scale() const {
        return std::clamp<std::int64_t>(static_cast<std::int64_t>(spacing_) * 65536 / 300, 32768, 65536);
    }
    // A height `above` millimeters over the plains, scaled.
    [[nodiscard]] std::int32_t over_plain(std::int64_t above) const {
        return static_cast<std::int32_t>(21000 + above * scale() / 65536);
    }

    // Each role's base height and bumps; "Relief" makes them gentler or
    // steeper.
    void set_heights() {
        Rng rng(s_.seed ^ kRoleSeed, 40);
        const bool low = s_.relief <= 60;
        const bool high = s_.relief >= 150;
        for (Region& r : regions_) {
            switch (r.role) {
                case Role::Plain:
                    r.height = 21000 + rng.range(-800, 800);
                    r.rough = 1800;
                    r.bumps = 250;
                    break;
                case Role::Hills:
                    r.height = over_plain((low ? 4000 : 6000) + rng.range(-1500, 1500));
                    r.rough = low ? 3500 : (high ? 6000 : 5000);
                    r.bumps = low ? 1500 : (high ? 3000 : 2500);
                    break;
                case Role::Mountains:
                    r.height = over_plain((high ? 25000 : 17000) + rng.range(0, 6000));
                    r.rough = low ? 7000 : (high ? 12000 : 9000);
                    r.bumps = low ? 6000 : (high ? 12000 : 9000);
                    break;
                case Role::Plateau:
                    r.height = over_plain(27000 + rng.range(0, 14000));
                    r.rough = 700;
                    r.bumps = 250;
                    break;
                case Role::Basin:
                    r.height = 13500 + rng.range(-500, 500);
                    r.rough = 900;
                    r.bumps = 200;
                    break;
                case Role::Sea:
                    r.height = sea_mm_ - rng.range(4000, 8000);
                    r.rough = 1500;
                    r.bumps = 300;
                    break;
            }
        }
    }

    // Region i is landform i.
    void record_regions() {
        out_.landforms.clear();
        for (const Region& r : regions_) {
            Landform l;
            l.kind = role_kind(r.role);
            l.points.push_back({std::clamp(r.x, 0, n_), std::clamp(r.z, 0, n_)});
            l.width = spacing_;
            out_.landforms.push_back(std::move(l));
        }
        out_.structure_owner.assign(out_.region_owner.size(), 0);
        // The open sea, for the squares under it that belong to a land region.
        if (sea_mm_ > 0) {
            Landform sea;
            sea.kind = LandformKind::Sea;
            sea.points.push_back({n_ / 2, n_ / 2});
            sea.width = n_;
            out_.landforms.push_back(std::move(sea));
            sea_owner_ = static_cast<std::uint16_t>(out_.landforms.size());
        }
        out_.sea_mm = sea_mm_;
    }

    // --- Level 0: the sea ------------------------------------------------------------

    static constexpr std::int32_t kSeaLevel = 19000;  // Millimeters: plains stand 2 m above it.

    // Where the sea is: around the islands on a map type with islands;
    // otherwise, per "Sea", along one side, a corner or two opposite sides.
    // The regions there are sea.
    void plan_sea() {
        Rng rng(s_.seed ^ kSeaSeed, 41);
        if (island_type_) {
            const std::int32_t towns = std::clamp<std::int32_t>(s_.players, 1, 12);
            out_.islands = worldgen::island_layout(
                s_.seed, n_, towns,
                std::min<std::int32_t>(s_.islands_per_town(), worldgen::max_islands_per_town(s_.size, s_.players)));
            sea_mm_ = kSeaLevel;
            for (Region& r : regions_) {
                if (island_land(std::clamp(r.x, 0, n_), std::clamp(r.z, 0, n_)) < 32768) {
                    r.role = Role::Sea;
                }
            }
            return;
        }
        if (s_.sea == Sea::None) {
            return;
        }
        sea_mm_ = kSeaLevel;
        // One side; or two: opposite ones one time in three, else a corner.
        const std::uint32_t pattern = rng.below(100);
        const std::uint32_t first = rng.below(4);
        std::vector<std::uint32_t> sides{first};
        if (s_.sea == Sea::TwoSides) {
            sides.push_back(pattern >= 67 ? first ^ 1u : first < 2 ? 2 + rng.below(2) : rng.below(2));
        }
        std::array<std::int32_t, 4> width{};  // West, east, north, south.
        // With two sides of sea each one reaches in less, so land stays the most.
        for (const std::uint32_t side : sides) {
            width[side] = n_ * (sides.size() == 1 ? rng.range(12, 22) : rng.range(10, 16)) / 100;
        }
        for (Region& r : regions_) {
            const std::int32_t edge[4] = {r.x, n_ - r.x, r.z, n_ - r.z};
            for (std::size_t k = 0; k < 4; ++k) {
                if (width[k] > 0 && edge[k] < width[k]) {
                    r.role = Role::Sea;
                }
            }
        }
    }

    // A coast's gulfs (land regions the sea takes), peninsulas (sea regions
    // that stay land) and islets off it.
    void shape_coast() {
        if (sea_mm_ == 0 || island_type_) {
            return;
        }
        Rng rng(s_.seed ^ kSeaSeed, 42);
        const auto land = [](const Region& r) { return r.role != Role::Sea; };
        const auto candidates = [&](const auto& ok) {
            std::vector<std::uint32_t> list;
            for (std::uint32_t id = 0; id < regions_.size(); ++id) {
                if (regions_[id].blocks > 0 && ok(regions_[id])) {
                    list.push_back(id);
                }
            }
            return list;
        };
        for (std::uint32_t k = rng.below(3); k > 0; --k) {
            const auto list = candidates([&](const Region& r) {
                return (r.role == Role::Plain || r.role == Role::Hills) && touches(r, Role::Sea) && !touches(r, Role::Plateau) &&
                       !touches(r, Role::Basin);
            });
            if (list.empty()) {
                break;
            }
            const std::uint32_t id = list[rng.below(static_cast<std::uint32_t>(list.size()))];
            regions_[id].role = Role::Sea;
            gulfs_.push_back(id);
        }
        for (std::uint32_t k = rng.below(3); k > 0; --k) {
            const auto list = candidates([&](const Region& r) {
                return r.role == Role::Sea && std::any_of(r.neighbors.begin(), r.neighbors.end(), [&](std::uint32_t nb) { return land(regions_[nb]); }) &&
                       touches(r, Role::Sea);
            });
            if (list.empty()) {
                break;
            }
            const std::uint32_t id = list[rng.below(static_cast<std::uint32_t>(list.size()))];
            if (std::find(gulfs_.begin(), gulfs_.end(), id) != gulfs_.end()) {
                continue;
            }
            regions_[id].role = Role::Plain;
            peninsulas_.push_back(id);
        }
        for (std::uint32_t k = rng.below(4); k > 0; --k) {
            const auto list = candidates([&](const Region& r) {
                return r.role == Role::Sea && std::none_of(r.neighbors.begin(), r.neighbors.end(), [&](std::uint32_t nb) { return land(regions_[nb]); });
            });
            if (list.empty()) {
                break;
            }
            const Region& r = regions_[list[rng.below(static_cast<std::uint32_t>(list.size()))]];
            islets_.push_back({std::clamp(r.x, 0, n_), std::clamp(r.z, 0, n_), rng.range(20, std::max(21, std::min(60, spacing_ / 4)))});
        }
    }

    // How much of a point is island or islet land, 0..65536: all of it
    // within 70 % of the radius, none past 130 %, with shores bent into
    // bays and capes.
    [[nodiscard]] std::int64_t island_land(std::int32_t x, std::int32_t z) const {
        std::int64_t best = 0;
        const auto check = [&](std::int32_t cx, std::int32_t cz, std::int32_t radius) {
            const std::int64_t reach = static_cast<std::int64_t>(radius) * 2;
            if (radius <= 0 || std::abs(static_cast<std::int64_t>(x) - cx) > reach || std::abs(static_cast<std::int64_t>(z) - cz) > reach) {
                return;
            }
            const int cell = std::max(3, log2_ceil(radius) - 1);
            const std::int64_t w = static_cast<std::int64_t>(radius) * 35 / 100;
            const std::int64_t qx = x + fbm(s_.seed ^ kShoreSeed, x, z, cell, 3) * w / 32768 - cx;
            const std::int64_t qz = z + fbm(s_.seed ^ kShoreSeed ^ 1u, x, z, cell, 3) * w / 32768 - cz;
            const auto d = static_cast<std::int64_t>(isqrt(static_cast<std::uint64_t>(qx * qx + qz * qz)));
            const std::int64_t u = (static_cast<std::int64_t>(radius) * 130 / 100 - d) * 65536 / std::max<std::int64_t>(1, radius * 60 / 100);
            best = std::max(best, smooth(u));
        };
        // Between two islands there is always a channel of sea: a point
        // belongs to the nearest island, measured in radii of each, and
        // the land ends before the line where two of them meet.
        std::int64_t nearest = INT64_MAX, second = INT64_MAX, nearest_radius = 0, second_radius = 0;
        for (const worldgen::Island& island : out_.islands) {
            check(island.x, island.z, island.radius);
            const std::int64_t reach = static_cast<std::int64_t>(island.radius) * 2;
            const std::int64_t dx = static_cast<std::int64_t>(x) - island.x;
            const std::int64_t dz = static_cast<std::int64_t>(z) - island.z;
            if (island.radius <= 0 || std::abs(dx) > reach || std::abs(dz) > reach) {
                continue;
            }
            const std::int64_t k = static_cast<std::int64_t>(isqrt(static_cast<std::uint64_t>(dx * dx + dz * dz))) * 1024 / island.radius;
            if (k < nearest) {
                second = nearest;
                second_radius = nearest_radius;
                nearest = k;
                nearest_radius = island.radius;
            } else if (k < second) {
                second = k;
                second_radius = island.radius;
            }
        }
        if (second != INT64_MAX) {
            // Meters to that line, about; no land within half a channel
            // of it, all of it a channel away.
            const std::int64_t half = std::max<std::int64_t>(10, n_ / 128);
            const std::int64_t to_line = (second - nearest) * std::min(nearest_radius, second_radius) / 2048;
            best = best * smooth((to_line - half) * 65536 / half) / 65536;
        }
        for (const Disc& islet : islets_) {
            check(islet.x, islet.z, islet.radius);
        }
        return best;
    }

    // The sea's squares, and the names of what the sea made: gulfs,
    // peninsulas, islets and islands. The structures placed later can
    // take these squares.
    void own_water() {
        if (sea_mm_ == 0) {
            return;
        }
        const auto corners = static_cast<std::size_t>(side_ + 1);
        std::vector<std::uint16_t> gulf(regions_.size(), 0);
        std::vector<std::uint16_t> peninsula(regions_.size(), 0);
        for (const std::uint32_t id : gulfs_) {
            gulf[id] = record(LandformKind::Gulf, {{regions_[id].x, regions_[id].z}}, spacing_);
        }
        for (const std::uint32_t id : peninsulas_) {
            peninsula[id] = record(LandformKind::Peninsula, {{regions_[id].x, regions_[id].z}}, spacing_);
        }
        std::vector<std::uint16_t> islets;
        for (const Disc& d : islets_) {
            islets.push_back(record(LandformKind::Islet, {{d.x, d.z}}, d.radius * 2));
        }
        std::vector<std::uint16_t> islands;
        for (const worldgen::Island& is : out_.islands) {
            islands.push_back(record(LandformKind::Island, {{is.x, is.z}}, is.radius * 2));
        }
        for (std::int32_t bz = 0; bz < side_; ++bz) {
            for (std::int32_t bx = 0; bx < side_; ++bx) {
                const auto sq = static_cast<std::size_t>(bz * side_ + bx);
                const std::size_t c = static_cast<std::size_t>(bz) * corners + static_cast<std::size_t>(bx);
                const std::int64_t land = (static_cast<std::int64_t>(land_[c]) + land_[c + 1] + land_[c + corners] + land_[c + corners + 1]) / 4;
                const std::uint32_t region = out_.region_owner[sq] - 1u;
                const std::int32_t x = bx * kOwnerBlock + kOwnerBlock / 2;
                const std::int32_t z = bz * kOwnerBlock + kOwnerBlock / 2;
                if (land < 32768) {
                    if (regions_[region].role != Role::Sea) {
                        out_.region_owner[sq] = sea_owner_;
                    }
                    out_.structure_owner[sq] = gulf[region];
                    continue;
                }
                if (peninsula[region] != 0) {
                    out_.structure_owner[sq] = peninsula[region];
                }
                // The islet or island it is on: the nearest by its size.
                std::int64_t best = INT64_MAX;
                const auto nearest = [&](std::int32_t cx, std::int32_t cz, std::int32_t radius, std::uint16_t owner) {
                    const std::int64_t dx = x - cx;
                    const std::int64_t dz = z - cz;
                    const std::int64_t d = static_cast<std::int64_t>(isqrt(static_cast<std::uint64_t>(dx * dx + dz * dz))) * 65536 /
                                           std::max(1, radius);
                    if (d < best && d < 2 * 65536) {
                        best = d;
                        out_.structure_owner[sq] = owner;
                    }
                };
                for (std::size_t i = 0; i < islets_.size(); ++i) {
                    nearest(islets_[i].x, islets_[i].z, islets_[i].radius, islets[i]);
                }
                for (std::size_t i = 0; i < out_.islands.size(); ++i) {
                    nearest(out_.islands[i].x, out_.islands[i].z, out_.islands[i].radius, islands[i]);
                }
            }
        }
    }

    // --- Heights -----------------------------------------------------------------

    // Base height and bumps at the corners of the squares: the regions
    // around each corner blended by how close it is to their borders. The
    // blend is wide between most regions, and a narrow cliff around a
    // plateau.
    // What the regions around a point make of it.
    struct Sample {
        std::int64_t base = 0;   // Height, millimeters.
        std::int64_t rough = 0;  // Broad swells.
        std::int64_t bumps = 0;  // Small bumps.
        std::int64_t mountain = 0;  // Share of mountains, 0..65536.
        std::int64_t land = 0;      // Share of land, 0..65536.
        bool cliff = false;  // A plateau's rim is near enough to need every vertex.
    };
    static constexpr std::int64_t kCliffBand = 6;  // Meters over which a plateau's rim drops.

    // The regions around a point blended by how close it is to their
    // borders: widely between most regions, over a narrow cliff around a
    // plateau.
    [[nodiscard]] Sample sample(std::int32_t x, std::int32_t z) const {
        struct Near {
            std::uint32_t id;
            std::int64_t d2;
        };
        std::array<Near, 25> near{};
        std::size_t count = 0;
        const std::int64_t smooth_band = spacing_ * 35 / 100;
        const auto [qx, qz] = warped(x, z);
        std::int64_t best = INT64_MAX;
        std::uint32_t first = 0;
        around(qx, qz, [&](std::uint32_t id, std::int64_t d2) {
            near[count++] = {id, d2};
            if (d2 < best) {
                best = d2;
                first = id;
            }
        });
        const auto d1 = static_cast<std::int64_t>(isqrt(static_cast<std::uint64_t>(best)));
        const bool plateau1 = regions_[first].role == Role::Plateau;
        Sample out;
        std::int64_t total = 0;
        for (std::size_t k = 0; k < count; ++k) {
            const Near& c = near[k];
            const Region& r = regions_[c.id];
            const bool rim = (r.role == Role::Plateau) != plateau1;
            const std::int64_t band = rim ? kCliffBand : smooth_band;
            // Past the border's band the region has no say (a rim a square
            // and a half away still marks the point).
            const std::int64_t reach = d1 + 2 * std::max<std::int64_t>(band, rim ? kCliffBand + kOwnerBlock * 3 / 2 : 0);
            if (c.d2 > reach * reach) {
                continue;
            }
            const std::int64_t e = (static_cast<std::int64_t>(isqrt(static_cast<std::uint64_t>(c.d2))) - d1) / 2;
            out.cliff = out.cliff || (rim && e <= kCliffBand + kOwnerBlock * 3 / 2);
            const std::int64_t w = std::max<std::int64_t>(0, (band - e) * 65536 / band);
            total += w;
            // On a map of islands their shapes make the sea: a sea
            // region under an island is low plain.
            const bool shore = island_type_ && r.role == Role::Sea;
            out.base += w * (shore ? 21000 : r.height);
            out.rough += w * (shore ? 1800 : r.rough);
            out.bumps += w * (shore ? 250 : r.bumps);
            out.mountain += r.role == Role::Mountains ? w : 0;
            out.land += r.role == Role::Sea ? 0 : w;
        }
        out.base /= total;
        out.land = out.land * 65536 / total;
        // Islands and islets: land where their shapes are, sea around.
        if (island_type_ || !islets_.empty()) {
            const std::int64_t shape = island_land(x, z);
            const std::int64_t floor = sea_mm_ - 6000;
            if (island_type_) {
                out.base = floor + (out.base - floor) * shape / 65536;
                out.land = shape;
            } else if (shape > out.land) {
                out.base = std::max<std::int64_t>(out.base, floor + (21500 - floor) * shape / 65536);
                out.land = shape;
            }
        }
        out.rough = out.rough / total * out.land / 65536;
        out.bumps = out.bumps / total * std::max<std::int64_t>(out.land, 16384) / 65536;
        out.mountain = out.mountain * 65536 / total * out.land / 65536;
        return out;
    }

    // The regions' blend at the corners of the squares; the vertices in
    // between are interpolated, but for those near a plateau's rim.
    bool base_field() {
        const auto corners = static_cast<std::size_t>(side_ + 1);
        base_.assign(corners * corners, 0);
        rough_.assign(corners * corners, 0);
        bumps_.assign(corners * corners, 0);
        mountain_.assign(corners * corners, 0);
        land_.assign(corners * corners, 65536);
        cliff_.assign(corners * corners, 0);
        for (std::int32_t cz = 0; cz <= side_; ++cz) {
            for (std::int32_t cx = 0; cx <= side_; ++cx) {
                const Sample p = sample(std::min(n_, cx * kOwnerBlock), std::min(n_, cz * kOwnerBlock));
                const std::size_t i = static_cast<std::size_t>(cz) * corners + static_cast<std::size_t>(cx);
                base_[i] = static_cast<std::int32_t>(p.base);
                rough_[i] = static_cast<std::int32_t>(p.rough);
                bumps_[i] = static_cast<std::int32_t>(p.bumps);
                mountain_[i] = static_cast<std::int32_t>(p.mountain);
                land_[i] = static_cast<std::int32_t>(p.land);
                cliff_[i] = p.cliff ? 1 : 0;
            }
            if ((cz & 63) == 0 && !report(20 + cz * 30 / (side_ + 1))) {
                return false;
            }
        }
        return true;
    }

    // Every vertex: the base between its square's corners (or its own, by a
    // plateau's rim, so the cliff follows the rim without steps), with
    // broad swells (water drains along them instead of pooling in every
    // hollow) and bumps as big as the regions there allow, and tiny ones
    // everywhere so water does not run in straight lines.
    bool vertices() {
        out_.h.assign(static_cast<std::size_t>(v_) * static_cast<std::size_t>(v_), 0);
        const auto corners = static_cast<std::size_t>(side_ + 1);
        for (std::int32_t z = 0; z < v_; ++z) {
            FbmRow swell(s_.seed ^ kDetailSeed, z, 9, 3);
            FbmRow bump(s_.seed ^ kBumpSeed, z, 6, 3);
            FbmRow micro(s_.seed ^ kMicroSeed, z, 4, 2);
            const std::int32_t cz = std::min(z / kOwnerBlock, side_ - 1);
            const std::int64_t fz = static_cast<std::int64_t>(z - cz * kOwnerBlock) * 65536 / kOwnerBlock;
            for (std::int32_t x = 0; x < v_; ++x) {
                const std::int32_t cx = std::min(x / kOwnerBlock, side_ - 1);
                const std::int64_t fx = static_cast<std::int64_t>(x - cx * kOwnerBlock) * 65536 / kOwnerBlock;
                const std::size_t i00 = static_cast<std::size_t>(cz) * corners + static_cast<std::size_t>(cx);
                const std::size_t i01 = i00 + corners;
                const auto lerp2 = [&](const std::vector<std::int32_t>& f) {
                    const std::int64_t a = f[i00] + (((f[i00 + 1] - f[i00]) * fx) >> 16);
                    const std::int64_t b = f[i01] + (((f[i01 + 1] - f[i01]) * fx) >> 16);
                    return a + (((b - a) * fz) >> 16);
                };
                std::int64_t base = 0;
                std::int64_t rough = 0;
                std::int64_t bumps = 0;
                if ((cliff_[i00] | cliff_[i00 + 1] | cliff_[i01] | cliff_[i01 + 1]) != 0) {
                    const Sample p = sample(x, z);
                    base = p.base;
                    rough = p.rough;
                    bumps = p.bumps;
                } else {
                    base = lerp2(base_);
                    rough = lerp2(rough_);
                    bumps = lerp2(bumps_);
                }
                const std::int64_t h = base + swell.at(x) * rough / 32768 + bump.at(x) * bumps / 32768 + micro.at(x) * 400 / 32768;
                out_.h[static_cast<std::size_t>(z) * static_cast<std::size_t>(v_) + static_cast<std::size_t>(x)] =
                    static_cast<std::int32_t>(std::max<std::int64_t>(1000, h));
            }
            if ((z & 63) == 0 && !report(50 + z * 25 / v_)) {
                return false;
            }
        }
        return true;
    }

    // --- Level 2: structures -----------------------------------------------------

    struct Pt {
        std::int32_t x = 0;
        std::int32_t z = 0;
    };

    // The region a cell is in (its square's owner), or none off the map.
    [[nodiscard]] std::int64_t region_of(std::int32_t x, std::int32_t z) const {
        if (x < 0 || z < 0 || x >= n_ || z >= n_) {
            return -1;
        }
        // The open sea's squares are no region's.
        const std::int64_t id = static_cast<std::int64_t>(out_.region_owner[static_cast<std::size_t>((z / kOwnerBlock) * side_ + x / kOwnerBlock)]) - 1;
        return id < static_cast<std::int64_t>(regions_.size()) ? id : -1;
    }
    [[nodiscard]] std::int32_t& h(std::int32_t x, std::int32_t z) {
        return out_.h[static_cast<std::size_t>(z) * static_cast<std::size_t>(v_) + static_cast<std::size_t>(x)];
    }
    [[nodiscard]] std::int32_t ground(Pt p) {
        return h(std::clamp(p.x, 0, n_), std::clamp(p.z, 0, n_));
    }
    // A point moved onto the map, a few meters from its border (where a
    // river can start).
    [[nodiscard]] Pt inside(Pt p) const {
        constexpr std::int32_t kMargin = 16;
        return {std::clamp(p.x, kMargin, n_ - kMargin), std::clamp(p.z, kMargin, n_ - kMargin)};
    }
    [[nodiscard]] static Pt toward(const Region& a, const Region& b, std::int32_t percent) {
        return {a.x + (b.x - a.x) * percent / 100, a.z + (b.z - a.z) * percent / 100};
    }

    // A wandering line from a to b: `pieces` segments, each bend moved up to
    // `wander` meters to either side.
    [[nodiscard]] static std::vector<Pt> wander(Rng& rng, Pt a, Pt b, std::int32_t pieces, std::int32_t wander_m) {
        std::vector<Pt> line{a};
        const std::int64_t dx = b.x - a.x;
        const std::int64_t dz = b.z - a.z;
        const auto len = static_cast<std::int64_t>(isqrt(static_cast<std::uint64_t>(dx * dx + dz * dz)));
        for (std::int32_t k = 1; k < pieces; ++k) {
            const std::int64_t off = len > 0 ? rng.range(-wander_m, wander_m) : 0;
            line.push_back({static_cast<std::int32_t>(a.x + dx * k / pieces - (len > 0 ? dz * off / len : 0)),
                            static_cast<std::int32_t>(a.z + dz * k / pieces + (len > 0 ? dx * off / len : 0))});
        }
        line.push_back(b);
        return line;
    }

    // Calls fn(x, z, distance in 1/16 m, how far along the line 0..65536)
    // for the vertices within `reach` meters of the line, each once (for the
    // nearest of its segment and the two beside it).
    template <typename Fn>
    void along(const std::vector<Pt>& line, std::int32_t reach, Fn&& fn) {
        if (line.size() < 2) {
            return;
        }
        std::vector<std::int64_t> start(line.size(), 0);  // Length before each point, 1/16 m.
        for (std::size_t k = 1; k < line.size(); ++k) {
            const std::int64_t dx = line[k].x - line[k - 1].x;
            const std::int64_t dz = line[k].z - line[k - 1].z;
            start[k] = start[k - 1] + static_cast<std::int64_t>(isqrt(static_cast<std::uint64_t>((dx * dx + dz * dz) * 256)));
        }
        const std::int64_t total = std::max<std::int64_t>(1, start.back());
        // Squared distance (1/256 m^2) to segment k, and the length along it (1/16 m).
        const auto seg = [&](std::size_t k, std::int64_t px, std::int64_t pz, std::int64_t& at) {
            const std::int64_t ax = line[k].x * 16, az = line[k].z * 16;
            const std::int64_t dx = line[k + 1].x * 16 - ax, dz = line[k + 1].z * 16 - az;
            const std::int64_t len2 = dx * dx + dz * dz;
            std::int64_t t = len2 > 0 ? ((px - ax) * dx + (pz - az) * dz) * 65536 / len2 : 0;
            t = std::clamp<std::int64_t>(t, 0, 65536);
            const std::int64_t qx = ax + dx * t / 65536 - px;
            const std::int64_t qz = az + dz * t / 65536 - pz;
            at = start[k] + (start[k + 1] - start[k]) * t / 65536;
            return qx * qx + qz * qz;
        };
        const std::int64_t reach16 = static_cast<std::int64_t>(reach) * 16;
        for (std::size_t k = 0; k + 1 < line.size(); ++k) {
            const std::int32_t x0 = std::max(0, std::min(line[k].x, line[k + 1].x) - reach);
            const std::int32_t x1 = std::min(v_ - 1, std::max(line[k].x, line[k + 1].x) + reach);
            const std::int32_t z0 = std::max(0, std::min(line[k].z, line[k + 1].z) - reach);
            const std::int32_t z1 = std::min(v_ - 1, std::max(line[k].z, line[k + 1].z) + reach);
            for (std::int32_t z = z0; z <= z1; ++z) {
                for (std::int32_t x = x0; x <= x1; ++x) {
                    std::int64_t at = 0;
                    const std::int64_t d2 = seg(k, x * 16, z * 16, at);
                    if (d2 > reach16 * reach16) {
                        continue;
                    }
                    // Only for the nearest segment around it (ties to the first).
                    std::int64_t other = 0;
                    if ((k > 0 && seg(k - 1, x * 16, z * 16, other) <= d2) ||
                        (k + 2 < line.size() && seg(k + 1, x * 16, z * 16, other) < d2)) {
                        continue;
                    }
                    fn(x, z, static_cast<std::int64_t>(isqrt(static_cast<std::uint64_t>(d2))), at * 65536 / total);
                }
            }
        }
    }

    // Marks the squares whose middle is within `reach` meters of the line
    // (and passes `ok`) as owned by landform `owner` (index + 1).
    template <typename Ok>
    void own(const std::vector<Pt>& line, std::int32_t reach, std::uint16_t owner, Ok&& ok) {
        const std::int64_t r2 = static_cast<std::int64_t>(reach) * reach;
        for (std::size_t k = 0; k + 1 < line.size(); ++k) {
            const std::int32_t bx0 = std::max(0, (std::min(line[k].x, line[k + 1].x) - reach) / kOwnerBlock);
            const std::int32_t bx1 = std::min(side_ - 1, (std::max(line[k].x, line[k + 1].x) + reach) / kOwnerBlock);
            const std::int32_t bz0 = std::max(0, (std::min(line[k].z, line[k + 1].z) - reach) / kOwnerBlock);
            const std::int32_t bz1 = std::min(side_ - 1, (std::max(line[k].z, line[k + 1].z) + reach) / kOwnerBlock);
            const std::int64_t ax = line[k].x, az = line[k].z;
            const std::int64_t dx = line[k + 1].x - ax, dz = line[k + 1].z - az;
            const std::int64_t len2 = dx * dx + dz * dz;
            for (std::int32_t bz = bz0; bz <= bz1; ++bz) {
                for (std::int32_t bx = bx0; bx <= bx1; ++bx) {
                    const std::int64_t px = bx * kOwnerBlock + kOwnerBlock / 2;
                    const std::int64_t pz = bz * kOwnerBlock + kOwnerBlock / 2;
                    const std::int64_t t = len2 > 0 ? std::clamp<std::int64_t>(((px - ax) * dx + (pz - az) * dz) * 65536 / len2, 0, 65536) : 0;
                    const std::int64_t qx = ax + dx * t / 65536 - px;
                    const std::int64_t qz = az + dz * t / 65536 - pz;
                    const auto sq = static_cast<std::size_t>(bz * side_ + bx);
                    const std::uint32_t region = out_.region_owner[sq] - 1u;
                    if (qx * qx + qz * qz <= r2 && region < regions_.size() && ok(region)) {
                        out_.structure_owner[sq] = owner;
                    }
                }
            }
        }
    }

    // Records a structure; its owner number for the squares.
    std::uint16_t record(LandformKind kind, const std::vector<Pt>& line, std::int32_t width) {
        Landform l;
        l.kind = kind;
        l.width = width;
        for (const Pt& p : line) {
            l.points.push_back({p.x, p.z});
        }
        out_.landforms.push_back(std::move(l));
        return static_cast<std::uint16_t>(out_.landforms.size());
    }

    [[nodiscard]] static std::int64_t smooth(std::int64_t u) {
        u = std::clamp<std::int64_t>(u, 0, 65536);
        return (((u * u) >> 16) * (3 * 65536 - 2 * u)) >> 16;
    }

    // The amount of `role` near a vertex, 0..65536 (from the base field).
    [[nodiscard]] std::int64_t share(const std::vector<std::int32_t>& field, std::int32_t x, std::int32_t z) const {
        const auto corners = static_cast<std::size_t>(side_ + 1);
        const std::int32_t cx = std::min(x / kOwnerBlock, side_ - 1);
        const std::int32_t cz = std::min(z / kOwnerBlock, side_ - 1);
        const std::int64_t fx = static_cast<std::int64_t>(x - cx * kOwnerBlock) * 65536 / kOwnerBlock;
        const std::int64_t fz = static_cast<std::int64_t>(z - cz * kOwnerBlock) * 65536 / kOwnerBlock;
        const std::size_t i00 = static_cast<std::size_t>(cz) * corners + static_cast<std::size_t>(cx);
        const std::size_t i01 = i00 + corners;
        const std::int64_t a = field[i00] + (((field[i00 + 1] - field[i00]) * fx) >> 16);
        const std::int64_t b = field[i01] + (((field[i01 + 1] - field[i01]) * fx) >> 16);
        return a + (((b - a) * fz) >> 16);
    }

    bool structures() {
        Rng rng(s_.seed ^ kStructSeed, 40);
        crests(rng);
        if (!report(80)) {
            return false;
        }
        plateau_rims(rng);
        valleys(rng);
        if (!report(90)) {
            return false;
        }
        canyons(rng);
        return true;
    }

    // Mountains: a crest along each chain, with peaks and spurs, and
    // sometimes a pass where it dips.
    void crests(Rng& rng) {
        const bool low = s_.relief <= 60;
        const bool high = s_.relief >= 150;
        for (const std::vector<std::uint32_t>& chain : chains_) {
            std::vector<Pt> spine;
            const Region& first = regions_[chain.front()];
            const Region& last = regions_[chain.back()];
            if (chain.size() == 1) {
                const Angle dir = rng.angle();
                const std::int32_t r = spacing_ * 45 / 100;
                const auto ox = static_cast<std::int32_t>((static_cast<std::int64_t>(cos(dir).raw()) * r) >> 16);
                const auto oz = static_cast<std::int32_t>((static_cast<std::int64_t>(sin(dir).raw()) * r) >> 16);
                spine = {{first.x - ox, first.z - oz}, {first.x + ox, first.z + oz}};
            } else {
                // Past both ends a little, through every region's middle.
                spine.push_back(toward(first, regions_[chain[1]], -35));
                for (const std::uint32_t id : chain) {
                    spine.push_back({regions_[id].x, regions_[id].z});
                }
                spine.push_back(toward(last, regions_[chain[chain.size() - 2]], -35));
            }
            std::vector<Pt> line{spine.front()};
            for (std::size_t k = 1; k < spine.size(); ++k) {
                const std::vector<Pt> piece = wander(rng, spine[k - 1], spine[k], 3, spacing_ / 10);
                line.insert(line.end(), piece.begin() + 1, piece.end());
            }
            const std::int32_t half = spacing_ * 45 / 100;
            const std::int64_t peak =
                (low ? rng.range(25000, 40000) : (high ? rng.range(65000, 110000) : rng.range(40000, 65000))) * scale() / 65536;
            // A pass: where along it, and how wide (1/65536 of the line).
            const bool pass = rng.below(100) < 70;
            const std::int64_t pass_at = rng.range(30, 70) * 65536 / 100;
            std::int64_t length16 = 0;
            for (std::size_t k = 1; k < line.size(); ++k) {
                const std::int64_t dx = line[k].x - line[k - 1].x, dz = line[k].z - line[k - 1].z;
                length16 += static_cast<std::int64_t>(isqrt(static_cast<std::uint64_t>((dx * dx + dz * dz) * 256)));
            }
            const std::int64_t pass_w = std::max<std::int64_t>(1, 60 * 16 * 65536 / std::max<std::int64_t>(1, length16));
            along(line, half, [&](std::int32_t x, std::int32_t z, std::int64_t d16, std::int64_t at) {
                const std::int64_t mountain = share(mountain_, x, z) * share(land_, x, z) / 65536;
                if (mountain <= 0) {
                    return;
                }
                const std::int64_t u = smooth(65536 - d16 * 65536 / (half * 16));
                const std::int64_t taper = std::min<std::int64_t>({65536, at * 5, (65536 - at) * 5});
                const std::int64_t n = fbm(s_.seed ^ kPeakSeed, x, z, 6, 3);
                const std::int64_t ridged = 32768 - (n < 0 ? -n : n);  // High on the ridges.
                std::int64_t height = peak * u / 65536 * taper / 65536 * (36000 + ridged * 29536 / 32768) / 65536;
                if (pass) {
                    const std::int64_t off = at > pass_at ? at - pass_at : pass_at - at;
                    height -= height * 65 / 100 * smooth(65536 - off * 65536 / pass_w) / 65536;
                }
                h(x, z) += static_cast<std::int32_t>(height * mountain / 65536);
            });
            const auto in_mountains = [&](std::uint32_t id) { return regions_[id].role == Role::Mountains; };
            own(line, half * 35 / 100, record(LandformKind::Crest, line, half * 70 / 100), in_mountains);
            if (pass && length16 > 0) {
                // The pass's stretch of the line.
                std::vector<Pt> saddle;
                std::int64_t walked = 0;
                for (std::size_t k = 1; k < line.size(); ++k) {
                    const std::int64_t dx = line[k].x - line[k - 1].x, dz = line[k].z - line[k - 1].z;
                    walked += static_cast<std::int64_t>(isqrt(static_cast<std::uint64_t>((dx * dx + dz * dz) * 256)));
                    const std::int64_t at = walked * 65536 / length16;
                    if ((at > pass_at ? at - pass_at : pass_at - at) < pass_w) {
                        saddle.push_back(line[k]);
                    }
                }
                if (saddle.empty()) {
                    saddle.push_back(line[line.size() / 2]);
                }
                if (saddle.size() == 1) {
                    saddle.push_back(saddle.front());
                }
                own(saddle, half * 45 / 100, record(LandformKind::Pass, saddle, half), in_mountains);
            }
        }
    }

    // Plateaus: the rim is a cliff, but for a ramp up from one side.
    void plateau_rims(Rng& rng) {
        for (std::uint32_t id = 0; id < regions_.size(); ++id) {
            const Region& p = regions_[id];
            if (p.role != Role::Plateau || p.blocks == 0) {
                continue;
            }
            // The cliff: plateau squares next to squares of another region.
            const std::uint16_t cliff = record(LandformKind::Cliff, {{p.x, p.z}}, spacing_);
            for (std::int32_t bz = 0; bz < side_; ++bz) {
                for (std::int32_t bx = 0; bx < side_; ++bx) {
                    const auto sq = static_cast<std::size_t>(bz * side_ + bx);
                    if (out_.region_owner[sq] != id + 1) {
                        continue;
                    }
                    bool edge = false;
                    for (std::int32_t dz = -1; dz <= 1 && !edge; ++dz) {
                        for (std::int32_t dx = -1; dx <= 1; ++dx) {
                            const std::int32_t x = bx + dx, z = bz + dz;
                            if (x >= 0 && z >= 0 && x < side_ && z < side_ && out_.region_owner[static_cast<std::size_t>(z * side_ + x)] != id + 1) {
                                edge = true;
                                break;
                            }
                        }
                    }
                    if (edge) {
                        out_.structure_owner[sq] = cliff;
                    }
                }
            }
            // The ramp, toward a neighbor that is not a plateau or a basin.
            std::vector<std::uint32_t> sides;
            for (const std::uint32_t nb : p.neighbors) {
                if (regions_[nb].blocks > 0 && regions_[nb].role != Role::Plateau && regions_[nb].role != Role::Basin &&
                    regions_[nb].role != Role::Mountains) {
                    sides.push_back(nb);
                }
            }
            if (sides.empty()) {
                continue;
            }
            const Region& to = regions_[sides[rng.below(static_cast<std::uint32_t>(sides.size()))]];
            // Cut into the plateau: from inside its top down to just past
            // its rim, climbing 1 m every 4 m where the plateau is wide
            // enough (steeper on a small one).
            const std::int64_t dx = to.x - p.x;
            const std::int64_t dz = to.z - p.z;
            const auto dist = std::max<std::int64_t>(1, static_cast<std::int64_t>(isqrt(static_cast<std::uint64_t>(dx * dx + dz * dz))));
            const auto at = [&](std::int64_t along) {
                return inside({static_cast<std::int32_t>(p.x + dx * along / dist), static_cast<std::int32_t>(p.z + dz * along / dist)});
            };
            std::int64_t rim = 0;
            while (rim < dist && region_of(at(rim).x, at(rim).z) == id) {
                rim += 4;
            }
            const Pt foot = at(rim + 20);
            const std::int64_t foot_h = ground(foot);
            const std::int64_t rise = std::max<std::int64_t>(0, p.height - foot_h);
            const Pt top = at(std::max<std::int64_t>(0, rim - rise * 4 / 1000));
            const std::int64_t top_h = ground(top);
            const std::int32_t half = std::clamp(spacing_ * 6 / 100, 8, 20) + rng.range(-2, 2);
            const std::vector<Pt> line{top, foot};
            const std::int32_t kSides = std::clamp(spacing_ * 8 / 100, 10, 24);  // Meters its sides take to ease into the ground.
            along(line, half + kSides, [&](std::int32_t x, std::int32_t z, std::int64_t d16, std::int64_t at) {
                const std::int64_t target = top_h + (foot_h - top_h) * at / 65536;
                // Flat across its width, easing into the ground at the sides.
                const std::int64_t w = d16 <= half * 16 ? 65536 : smooth(65536 - (d16 - half * 16) * 65536 / (kSides * 16));
                std::int32_t& v = h(x, z);
                v += static_cast<std::int32_t>((target - v) * w / 65536);
            });
            own(line, half + 4, record(LandformKind::Ramp, line, half * 2), [](std::uint32_t) { return true; });
        }
    }

    // Valleys: U-shaped, from inside hills or mountains down to a lower
    // neighbor, only within those two regions.
    void valleys(Rng& rng) {
        std::vector<std::uint32_t> from;
        for (std::uint32_t id = 0; id < regions_.size(); ++id) {
            const Region& r = regions_[id];
            if ((r.role == Role::Hills || r.role == Role::Mountains) && r.blocks > 0 &&
                std::any_of(r.neighbors.begin(), r.neighbors.end(), [&](std::uint32_t nb) {
                    return regions_[nb].blocks > 0 && (regions_[nb].role == Role::Plain || regions_[nb].role == Role::Basin);
                })) {
                from.push_back(id);
            }
        }
        const std::int32_t percent = by_percent(s_.landforms, 0, 15, 30, 45);
        auto count = static_cast<std::int32_t>(from.size()) * percent / 100;
        if (count == 0 && !from.empty() && s_.landforms > Amount::Low) {
            count = 1;
        }
        for (std::int32_t i = 0; i < count && !from.empty(); ++i) {
            const std::size_t pick = rng.below(static_cast<std::uint32_t>(from.size()));
            const std::uint32_t id = from[pick];
            from.erase(from.begin() + static_cast<std::ptrdiff_t>(pick));
            const Region& r = regions_[id];
            std::vector<std::uint32_t> exits;
            for (const std::uint32_t nb : r.neighbors) {
                if (regions_[nb].blocks > 0 && (regions_[nb].role == Role::Plain || regions_[nb].role == Role::Basin)) {
                    exits.push_back(nb);
                }
            }
            const std::uint32_t exit = exits[rng.below(static_cast<std::uint32_t>(exits.size()))];
            const Region& e = regions_[exit];
            // In mountains it starts on a flank, off the crest through the middle.
            const Pt head = inside(r.role == Role::Mountains ? toward(r, e, 30) : toward(r, e, -20));
            const Pt mouth = toward(r, e, 95);
            const std::int32_t length = static_cast<std::int32_t>(isqrt(static_cast<std::uint64_t>(
                static_cast<std::int64_t>(mouth.x - head.x) * (mouth.x - head.x) + static_cast<std::int64_t>(mouth.z - head.z) * (mouth.z - head.z))));
            const std::vector<Pt> line = wander(rng, head, mouth, 6, std::max(4, length / 12));
            const std::int32_t half = std::clamp(spacing_ * rng.range(20, 32) / 100, 40, 160);
            const std::int64_t depth = rng.range(6000, 12000);
            const std::int64_t head_floor = ground(head) - depth;
            const std::int64_t mouth_floor = std::min<std::int64_t>(head_floor, ground(mouth) - 500);
            const auto mine = [&](std::int32_t x, std::int32_t z) {
                const std::int64_t reg = region_of(std::min(x, n_ - 1), std::min(z, n_ - 1));
                return reg == id || reg == exit;
            };
            along(line, half, [&](std::int32_t x, std::int32_t z, std::int64_t d16, std::int64_t at) {
                if (!mine(x, z)) {
                    return;
                }
                const std::int64_t floor = head_floor + (mouth_floor - head_floor) * at / 65536;
                const std::int64_t w16 = half * 16;
                const std::int64_t target = floor + depth * 2 * d16 * d16 / (w16 * w16);
                const std::int64_t blend = d16 * 2 < w16 ? 65536 : smooth((w16 - d16) * 65536 / (w16 / 2));
                std::int32_t& v = h(x, z);
                if (v > target) {
                    v -= static_cast<std::int32_t>((v - target) * blend / 65536);
                }
            });
            own(line, half * 60 / 100, record(LandformKind::Valley, line, half * 2),
                [&](std::uint32_t reg) { return reg == id || reg == exit; });
            if (rng.below(100) < 60) {
                out_.river_sources.push_back({head.x, head.z});
            }
        }
    }

    static constexpr std::int32_t kCanyonPlateauBlocks = 200;

    // Canyons: few, narrow, with sheer walls, from inside a plateau out to a
    // lower neighbor; most carry a river.
    void canyons(Rng& rng) {
        std::vector<std::uint32_t> plateaus;
        for (std::uint32_t id = 0; id < regions_.size(); ++id) {
            // Room for a canyon: a plateau of 1.3 ha or more.
            if (regions_[id].role == Role::Plateau && regions_[id].blocks >= kCanyonPlateauBlocks) {
                plateaus.push_back(id);
            }
        }
        // Few: a canyon for some of the plateaus, at least one if there are any.
        const std::int32_t percent = by_percent(s_.landforms, 0, 15, 25, 40);
        std::int32_t count = static_cast<std::int32_t>(plateaus.size()) * percent / 100;
        if (count == 0 && !plateaus.empty() && s_.landforms > Amount::Low) {
            count = 1;
        }
        for (std::int32_t i = 0; i < count && !plateaus.empty(); ++i) {
            const std::size_t pick = rng.below(static_cast<std::uint32_t>(plateaus.size()));
            const std::uint32_t id = plateaus[pick];
            plateaus.erase(plateaus.begin() + static_cast<std::ptrdiff_t>(pick));
            const Region& p = regions_[id];
            std::vector<std::uint32_t> exits;
            for (const std::uint32_t nb : p.neighbors) {
                const Role role = regions_[nb].role;
                if (regions_[nb].blocks > 0 && (role == Role::Plain || role == Role::Hills || role == Role::Basin)) {
                    exits.push_back(nb);
                }
            }
            if (exits.empty()) {
                continue;
            }
            const std::uint32_t exit = exits[rng.below(static_cast<std::uint32_t>(exits.size()))];
            const Region& e = regions_[exit];
            // It starts deep in the plateau, on the side away from its exit,
            // but never past the plateau's far rim.
            Pt head = inside({p.x, p.z});
            for (std::int32_t back = 30; back >= 0; back -= 5) {
                const Pt at = inside(toward(p, e, -back));
                if (region_of(at.x, at.z) == id) {
                    head = at;
                    break;
                }
            }
            const Pt mouth = toward(p, e, 90);
            const std::int32_t length = static_cast<std::int32_t>(isqrt(static_cast<std::uint64_t>(
                static_cast<std::int64_t>(mouth.x - head.x) * (mouth.x - head.x) + static_cast<std::int64_t>(mouth.z - head.z) * (mouth.z - head.z))));
            const std::vector<Pt> line = wander(rng, head, mouth, 10, std::max(4, length / 14));
            // As wide as the regions allow: narrow on small maps.
            const std::int32_t half = std::clamp(spacing_ * 7 / 100, 9, 20) + rng.range(-2, 2);
            const std::int64_t top = p.height;
            const std::int64_t mouth_floor = ground(mouth) - 800;
            const std::int64_t head_floor = std::max(mouth_floor + 1000, top - (top - mouth_floor) * rng.range(55, 75) / 100);
            along(line, half, [&](std::int32_t x, std::int32_t z, std::int64_t d16, std::int64_t at) {
                const std::int64_t reg = region_of(std::min(x, n_ - 1), std::min(z, n_ - 1));
                if (reg != id && reg != exit) {
                    return;
                }
                const std::int64_t floor = head_floor + (mouth_floor - head_floor) * at / 65536;
                const std::int64_t w16 = half * 16;
                // A flat bottom, then walls straight up.
                std::int32_t& v = h(x, z);
                const std::int64_t target = d16 * 100 < w16 * 55 ? floor : floor + (v - floor) * (d16 * 100 - w16 * 55) / (w16 * 45);
                if (v > target) {
                    v = static_cast<std::int32_t>(target);
                }
            });
            own(line, half + 6, record(LandformKind::Canyon, line, half * 2), [&](std::uint32_t reg) { return reg == id || reg == exit; });
            if (rng.below(100) < 75) {
                out_.river_sources.push_back({head.x, head.z});
            }
        }
    }
};

}  // namespace

std::int32_t region_spacing(std::int32_t n) {
    return std::clamp(n / 7, 150, 900);
}

bool shape(const MapSettings& s, std::int32_t n, bool islands, const Progress& progress, Ground& out) {
    out = Ground{};
    Shaper shaper(s, n, islands, progress, out);
    return shaper.run();
}

}  // namespace sc::sim::hier
