#include "sim/worldgen_hier.h"

#include <algorithm>
#include <utility>

#include "sim/fixed.h"
#include "sim/noise.h"
#include "sim/rng.h"

namespace sc::sim::hier {

namespace {

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

enum class Role : std::uint8_t { Plain, Hills, Mountains, Plateau, Basin };

LandformKind role_kind(Role r) {
    switch (r) {
        case Role::Hills: return LandformKind::Hills;
        case Role::Mountains: return LandformKind::Mountains;
        case Role::Plateau: return LandformKind::Plateau;
        case Role::Basin: return LandformKind::Basin;
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
    Shaper(const MapSettings& s, std::int32_t n, const Progress& progress, Ground& out)
        : s_(s), n_(n), v_(n + 1), progress_(progress), out_(out), spacing_(region_spacing(n)),
          grid_((n + spacing_ - 1) / spacing_), warp_log2_(log2_ceil(spacing_) - 1), side_((n + kOwnerBlock - 1) / kOwnerBlock) {}

    bool run() {
        place_regions();
        if (!find_owners()) {
            return false;
        }
        find_neighbors();
        assign_roles();
        set_heights();
        record_regions();
        if (!base_field() || !vertices()) {
            return false;
        }
        return report(100);
    }

private:
    const MapSettings& s_;
    std::int32_t n_;
    std::int32_t v_;
    const Progress& progress_;
    Ground& out_;
    std::int32_t spacing_;
    std::int32_t grid_;       // Region centers per side.
    int warp_log2_;
    std::int32_t side_;       // Owner squares per side.
    std::vector<Region> regions_;
    // Base height and bump amplitude at the corners of the owner squares,
    // (side + 1)^2, millimeters.
    std::vector<std::int32_t> base_;
    std::vector<std::int32_t> rough_;
    std::vector<std::int32_t> bumps_;

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
        std::vector<std::uint32_t> on_map;
        for (std::uint32_t id = 0; id < regions_.size(); ++id) {
            if (regions_[id].blocks > 0) {
                on_map.push_back(id);
            }
        }
        const auto m = static_cast<std::int32_t>(on_map.size());
        const std::int32_t percent = s_.landforms == Amount::Low ? 30 : (s_.landforms == Amount::High ? 60 : 45);
        const std::int32_t others = m * percent / 100;
        const std::int32_t share = s_.relief == Relief::Low ? 20 : (s_.relief == Relief::Mountainous ? 55 : 35);
        std::int32_t mountains = others * share / 100;
        std::int32_t plateaus = std::max(m >= 8 ? 1 : 0, others * 15 / 100);
        std::int32_t basins = std::max(m >= 6 ? 1 : 0, others * 10 / 100);
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
            for (std::int32_t k = 0; k < length && mountains > 0; ++k) {
                regions_[cur].role = Role::Mountains;
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
            const std::int64_t id = pick([&](const Region& r) { return !touches(r, Role::Plateau) && !touches(r, Role::Basin); });
            if (id < 0) {
                break;
            }
            regions_[static_cast<std::size_t>(id)].role = Role::Plateau;
        }
        for (; basins > 0; --basins) {
            const std::int64_t id = pick([&](const Region& r) { return !touches(r, Role::Basin) && !touches(r, Role::Plateau); });
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

    // Each role's base height and bumps; "Relief" makes them gentler or
    // steeper.
    void set_heights() {
        Rng rng(s_.seed ^ kRoleSeed, 40);
        const bool low = s_.relief == Relief::Low;
        const bool high = s_.relief == Relief::Mountainous;
        for (Region& r : regions_) {
            switch (r.role) {
                case Role::Plain:
                    r.height = 21000 + rng.range(-800, 800);
                    r.rough = 1800;
                    r.bumps = 250;
                    break;
                case Role::Hills:
                    r.height = (low ? 25000 : 27000) + rng.range(-1500, 1500);
                    r.rough = low ? 3500 : (high ? 6000 : 5000);
                    r.bumps = low ? 1500 : (high ? 3000 : 2500);
                    break;
                case Role::Mountains:
                    r.height = (high ? 46000 : 38000) + rng.range(0, 6000);
                    r.rough = low ? 7000 : (high ? 12000 : 9000);
                    r.bumps = low ? 6000 : (high ? 12000 : 9000);
                    break;
                case Role::Plateau:
                    r.height = 48000 + rng.range(0, 14000);
                    r.rough = 700;
                    r.bumps = 250;
                    break;
                case Role::Basin:
                    r.height = 13500 + rng.range(-500, 500);
                    r.rough = 900;
                    r.bumps = 200;
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
    }

    // --- Heights -----------------------------------------------------------------

    // Base height and bumps at the corners of the squares: the regions
    // around each corner blended by how close it is to their borders. The
    // blend is wide between most regions, and a narrow cliff around a
    // plateau.
    bool base_field() {
        const auto corners = static_cast<std::size_t>(side_ + 1);
        base_.assign(corners * corners, 0);
        rough_.assign(corners * corners, 0);
        bumps_.assign(corners * corners, 0);
        const std::int64_t smooth_band = spacing_ * 35 / 100;
        constexpr std::int64_t kCliffBand = 6;
        struct Near {
            std::uint32_t id;
            std::int64_t d2;
        };
        std::vector<Near> near;
        for (std::int32_t cz = 0; cz <= side_; ++cz) {
            for (std::int32_t cx = 0; cx <= side_; ++cx) {
                const std::int32_t x = std::min(n_, cx * kOwnerBlock);
                const std::int32_t z = std::min(n_, cz * kOwnerBlock);
                const auto [qx, qz] = warped(x, z);
                near.clear();
                std::int64_t best = INT64_MAX;
                std::uint32_t first = 0;
                around(qx, qz, [&](std::uint32_t id, std::int64_t d2) {
                    near.push_back({id, d2});
                    if (d2 < best) {
                        best = d2;
                        first = id;
                    }
                });
                const auto d1 = static_cast<std::int64_t>(isqrt(static_cast<std::uint64_t>(best)));
                const bool plateau1 = regions_[first].role == Role::Plateau;
                std::int64_t total = 0;
                std::int64_t h = 0;
                std::int64_t rough = 0;
                std::int64_t bumps = 0;
                for (const Near& c : near) {
                    const Region& r = regions_[c.id];
                    const std::int64_t band = (r.role == Role::Plateau) != plateau1 ? kCliffBand : smooth_band;
                    // Past the border's band the region has no say.
                    const std::int64_t reach = d1 + 2 * band;
                    if (c.d2 > reach * reach) {
                        continue;
                    }
                    const std::int64_t e = (static_cast<std::int64_t>(isqrt(static_cast<std::uint64_t>(c.d2))) - d1) / 2;
                    const std::int64_t w = std::max<std::int64_t>(0, (band - e) * 65536 / band);
                    total += w;
                    h += w * r.height;
                    rough += w * r.rough;
                    bumps += w * r.bumps;
                }
                const std::size_t i = static_cast<std::size_t>(cz) * corners + static_cast<std::size_t>(cx);
                base_[i] = static_cast<std::int32_t>(h / total);
                rough_[i] = static_cast<std::int32_t>(rough / total);
                bumps_[i] = static_cast<std::int32_t>(bumps / total);
            }
            if ((cz & 63) == 0 && !report(20 + cz * 30 / (side_ + 1))) {
                return false;
            }
        }
        return true;
    }

    // Every vertex: the base between its square's corners, with broad
    // swells (water drains along them instead of pooling in every hollow)
    // and bumps as big as the regions there allow, and tiny ones everywhere
    // so water does not run in straight lines.
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
                const std::int64_t h = lerp2(base_) + swell.at(x) * lerp2(rough_) / 32768 + bump.at(x) * lerp2(bumps_) / 32768 +
                                       micro.at(x) * 400 / 32768;
                out_.h[static_cast<std::size_t>(z) * static_cast<std::size_t>(v_) + static_cast<std::size_t>(x)] =
                    static_cast<std::int32_t>(std::max<std::int64_t>(1000, h));
            }
            if ((z & 63) == 0 && !report(50 + z * 50 / v_)) {
                return false;
            }
        }
        return true;
    }
};

}  // namespace

std::int32_t region_spacing(std::int32_t n) {
    return std::clamp(n / 7, 150, 900);
}

bool shape(const MapSettings& s, std::int32_t n, const Progress& progress, Ground& out) {
    out = Ground{};
    Shaper shaper(s, n, progress, out);
    return shaper.run();
}

}  // namespace sc::sim::hier
