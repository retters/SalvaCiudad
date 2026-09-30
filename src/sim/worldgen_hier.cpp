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
constexpr std::uint64_t kStructSeed = 0x4849455253545239ull;
constexpr std::uint64_t kPeakSeed = 0x484945525045414bull;

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
        if (!base_field() || !vertices() || !structures()) {
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
    std::vector<std::vector<std::uint32_t>> chains_;  // Mountain regions, in chains.
    // Base height and bump amplitude at the corners of the owner squares,
    // (side + 1)^2, millimeters.
    std::vector<std::int32_t> base_;
    std::vector<std::int32_t> rough_;
    std::vector<std::int32_t> bumps_;
    std::vector<std::int32_t> mountain_;  // How much of it is mountains, 0..65536.

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
        mountain_.assign(corners * corners, 0);
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
                std::int64_t mountain = 0;
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
                    mountain += r.role == Role::Mountains ? w : 0;
                }
                const std::size_t i = static_cast<std::size_t>(cz) * corners + static_cast<std::size_t>(cx);
                base_[i] = static_cast<std::int32_t>(h / total);
                rough_[i] = static_cast<std::int32_t>(rough / total);
                bumps_[i] = static_cast<std::int32_t>(bumps / total);
                mountain_[i] = static_cast<std::int32_t>(mountain * 65536 / total);
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
        return static_cast<std::int64_t>(out_.region_owner[static_cast<std::size_t>((z / kOwnerBlock) * side_ + x / kOwnerBlock)]) - 1;
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
                    if (qx * qx + qz * qz <= r2 && ok(out_.region_owner[sq] - 1u)) {
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
        const bool low = s_.relief == Relief::Low;
        const bool high = s_.relief == Relief::Mountainous;
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
            const std::int64_t peak = low ? rng.range(25000, 40000) : (high ? rng.range(65000, 110000) : rng.range(40000, 65000));
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
                const std::int64_t mountain = share(mountain_, x, z);
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
            const Pt top = toward(p, to, 30);
            const Pt foot = toward(p, to, 85);
            const std::int64_t top_h = ground(top);
            const std::int64_t foot_h = ground(foot);
            const std::int32_t half = rng.range(16, 24);
            const std::vector<Pt> line{top, foot};
            along(line, half + 10, [&](std::int32_t x, std::int32_t z, std::int64_t d16, std::int64_t at) {
                const std::int64_t target = top_h + (foot_h - top_h) * at / 65536;
                // Flat across its width, easing into the ground at the sides.
                const std::int64_t w = d16 <= half * 16 ? 65536 : smooth(65536 - (d16 - half * 16) * 65536 / (10 * 16));
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
        const std::int32_t percent = s_.landforms == Amount::Low ? 15 : (s_.landforms == Amount::High ? 45 : 30);
        auto count = static_cast<std::int32_t>(from.size()) * percent / 100;
        if (count == 0 && !from.empty() && s_.landforms != Amount::Low) {
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

    // Canyons: few, narrow, with sheer walls, from inside a plateau out to a
    // lower neighbor; most carry a river.
    void canyons(Rng& rng) {
        std::vector<std::uint32_t> plateaus;
        for (std::uint32_t id = 0; id < regions_.size(); ++id) {
            if (regions_[id].role == Role::Plateau && regions_[id].blocks > 0) {
                plateaus.push_back(id);
            }
        }
        // Few: a canyon for some of the plateaus, at least one if there are any.
        const std::int32_t percent = s_.landforms == Amount::Low ? 15 : (s_.landforms == Amount::High ? 40 : 25);
        std::int32_t count = static_cast<std::int32_t>(plateaus.size()) * percent / 100;
        if (count == 0 && !plateaus.empty() && s_.landforms != Amount::Low) {
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
            const std::int32_t half = rng.range(14, 22);
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

bool shape(const MapSettings& s, std::int32_t n, const Progress& progress, Ground& out) {
    out = Ground{};
    Shaper shaper(s, n, progress, out);
    return shaper.run();
}

}  // namespace sc::sim::hier
