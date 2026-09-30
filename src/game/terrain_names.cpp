#include "game/terrain_names.h"

#include <algorithm>
#include <cmath>
#include <limits>

#include "i18n/translator.h"

namespace sc {

using i18n::tr;

namespace {

// How far past its line (or its center) a landform may show: the
// generator bends some shapes by noise (decision D-3703).
double reach(const sim::Landform& l) {
    const double half = l.width / 2.0;
    switch (l.kind) {
        case sim::LandformKind::Island: return half * 1.7;
        case sim::LandformKind::Plateau: return half * 4.0 / 3.0 + 10.0;
        case sim::LandformKind::Islet: return half + 10.0;
        case sim::LandformKind::River: return half + 2.0;
        default: return half;
    }
}

// Distance in meters from (x, z) to the landform's line, or to its point.
double distance(const sim::Landform& l, double x, double z) {
    if (l.points.size() == 1) {
        return std::hypot(x - l.points[0][0], z - l.points[0][1]);
    }
    double best = std::numeric_limits<double>::max();
    for (std::size_t k = 0; k + 1 < l.points.size(); ++k) {
        const double ax = l.points[k][0], az = l.points[k][1];
        const double bx = l.points[k + 1][0], bz = l.points[k + 1][1];
        const double dx = bx - ax, dz = bz - az;
        const double len2 = dx * dx + dz * dz;
        const double t = len2 > 0.0 ? std::clamp(((x - ax) * dx + (z - az) * dz) / len2, 0.0, 1.0) : 0.0;
        best = std::min(best, std::hypot(x - (ax + dx * t), z - (az + dz * t)));
    }
    return best;
}

// Meters with one decimal, in the active language's way.
std::string meters(std::int32_t cm) {
    const bool negative = cm < 0;
    const std::int32_t a = std::abs(cm);
    const std::int32_t tenths = (a + 5) / 10;
    return (negative ? "-" : "") + i18n::translator().format_int(tenths / 10) +
           i18n::translator().active().decimal_separator + std::to_string(tenths % 10);
}

}  // namespace

void TerrainNames::build(const sim::MapData& map) {
    landforms_ = map.landforms.data();
    count_ = map.landforms.size();
    side_ = std::max(1, (map.size + kBucket - 1) / kBucket);
    buckets_.assign(static_cast<std::size_t>(side_) * static_cast<std::size_t>(side_), {});
    for (std::size_t i = 0; i < map.landforms.size(); ++i) {
        const sim::Landform& l = map.landforms[i];
        if (l.kind == sim::LandformKind::Coast || l.points.empty()) {
            continue;  // The coast is found from the sea itself.
        }
        const double r = reach(l);
        const auto index = static_cast<std::uint32_t>(i);
        // Each segment's box, grown by the reach; a landform once per square.
        const std::size_t segments = std::max<std::size_t>(1, l.points.size() - 1);
        for (std::size_t k = 0; k < segments; ++k) {
            const auto& a = l.points[k];
            const auto& b = l.points[std::min(k + 1, l.points.size() - 1)];
            const auto square = [&](double v) {
                return std::clamp(static_cast<std::int32_t>(std::floor(v / kBucket)), 0, side_ - 1);
            };
            const std::int32_t x0 = square(std::min(a[0], b[0]) - r), x1 = square(std::max(a[0], b[0]) + r);
            const std::int32_t z0 = square(std::min(a[1], b[1]) - r), z1 = square(std::max(a[1], b[1]) + r);
            for (std::int32_t z = z0; z <= z1; ++z) {
                for (std::int32_t x = x0; x <= x1; ++x) {
                    auto& bucket = buckets_[static_cast<std::size_t>(z) * static_cast<std::size_t>(side_) + static_cast<std::size_t>(x)];
                    if (bucket.empty() || bucket.back() != index) {
                        bucket.push_back(index);
                    }
                }
            }
        }
    }
}

CellDescription TerrainNames::describe(const sim::MapData& map, std::int32_t cx, std::int32_t cz) {
    CellDescription d;
    d.cx = cx;
    d.cz = cz;
    if (cx < 0 || cz < 0 || cx >= map.size || cz >= map.size || map.water.empty()) {
        return d;
    }
    if (landforms_ != map.landforms.data() || count_ != map.landforms.size() || buckets_.empty() ||
        side_ != std::max(1, (map.size + kBucket - 1) / kBucket)) {
        build(map);
    }
    d.inside = true;
    const auto cell = [&](std::int32_t x, std::int32_t z) {
        return static_cast<std::size_t>(z) * static_cast<std::size_t>(map.size) + static_cast<std::size_t>(x);
    };
    const std::size_t c = cell(cx, cz);
    const std::int32_t h00 = map.height_cm(cx, cz), h10 = map.height_cm(cx + 1, cz), h01 = map.height_cm(cx, cz + 1),
                       h11 = map.height_cm(cx + 1, cz + 1);
    d.height_cm = h00;
    d.slope_pct = std::max({h00, h10, h01, h11}) - std::min({h00, h10, h01, h11});
    d.terrain = map.terrain_at(cx, cz);
    d.biome = map.biome_at(cx, cz);
    d.fertility_pct = c < map.fertility.size() ? map.fertility[c] * 100 / 255 : 0;

    // The sea: water at the level of the region's sea.
    const auto region = static_cast<std::size_t>(map.region_at(cx, cz));
    const std::uint16_t sea = region < map.sea_levels.size() ? map.sea_levels[region] : 0;
    const auto is_sea = [&](std::int32_t x, std::int32_t z) {
        return sea != 0 && map.water[cell(x, z)] == sea;
    };
    const double px = cx + 0.5;
    const double pz = cz + 0.5;
    const auto& bucket = buckets_[static_cast<std::size_t>(std::min(cz / kBucket, side_ - 1)) * static_cast<std::size_t>(side_) +
                                  static_cast<std::size_t>(std::min(cx / kBucket, side_ - 1))];
    if (map.water[c] != 0) {
        d.water_depth_cm = std::max(0, static_cast<std::int32_t>(map.water[c]) - h00);
        if (is_sea(cx, cz)) {
            d.water = WaterKind::Sea;
        } else {
            d.water = WaterKind::Lake;
            for (const std::uint32_t i : bucket) {
                const sim::Landform& l = map.landforms[i];
                if (l.kind == sim::LandformKind::River && distance(l, px, pz) <= reach(l)) {
                    d.water = WaterKind::River;
                    break;
                }
            }
        }
    } else if (sea != 0) {
        // The coast: dry land with the sea this close.
        constexpr std::int32_t kCoast = 12;
        for (std::int32_t z = std::max(0, cz - kCoast); z <= std::min(map.size - 1, cz + kCoast) && !d.coast; ++z) {
            for (std::int32_t x = std::max(0, cx - kCoast); x <= std::min(map.size - 1, cx + kCoast); ++x) {
                if (is_sea(x, z)) {
                    d.coast = true;
                    break;
                }
            }
        }
    }

    // A hierarchical map says exactly what is where.
    if (!map.region_owner.empty()) {
        const auto name = [&](const std::vector<std::uint16_t>& grid) -> std::optional<sim::LandformKind> {
            const std::uint16_t owner = map.owner_at(grid, cx, cz);
            if (owner == 0 || owner > map.landforms.size()) {
                return std::nullopt;
            }
            return map.landforms[owner - 1u].kind;
        };
        d.region = name(map.region_owner);
        if (const std::optional<sim::LandformKind> structure = name(map.structure_owner)) {
            d.landforms.push_back(*structure);
        }
        return d;
    }
    const bool dry = d.water == WaterKind::None;
    const bool at_sea = d.water == WaterKind::Sea;
    for (const std::uint32_t i : bucket) {
        const sim::Landform& l = map.landforms[i];
        const double dist = distance(l, px, pz);
        const double r = reach(l);
        bool here = false;
        switch (l.kind) {
            case sim::LandformKind::Gulf:
            case sim::LandformKind::Trench:
            case sim::LandformKind::Ridge: here = at_sea && dist <= r; break;
            case sim::LandformKind::Peninsula:
            case sim::LandformKind::Cape:
            case sim::LandformKind::Islet: here = dry && dist <= r; break;
            case sim::LandformKind::Plateau:
            case sim::LandformKind::Valley:
            case sim::LandformKind::Range:
            case sim::LandformKind::Canyon: here = !at_sea && dist <= r; break;
            case sim::LandformKind::Island: here = dry && dist <= r; break;
            default: break;
        }
        if (here) {
            d.landforms.push_back(l.kind);
        }
    }
    std::sort(d.landforms.begin(), d.landforms.end());
    d.landforms.erase(std::unique(d.landforms.begin(), d.landforms.end()), d.landforms.end());
    return d;
}

const char* landform_key(sim::LandformKind kind) {
    switch (kind) {
        case sim::LandformKind::Coast: return "landform.coast";
        case sim::LandformKind::Gulf: return "landform.gulf";
        case sim::LandformKind::Peninsula: return "landform.peninsula";
        case sim::LandformKind::Islet: return "landform.islet";
        case sim::LandformKind::Trench: return "landform.trench";
        case sim::LandformKind::Ridge: return "landform.ridge";
        case sim::LandformKind::Plateau: return "landform.plateau";
        case sim::LandformKind::Valley: return "landform.valley";
        case sim::LandformKind::Range: return "landform.range";
        case sim::LandformKind::Canyon: return "landform.canyon";
        case sim::LandformKind::Cape: return "landform.cape";
        case sim::LandformKind::River: return "landform.river";
        case sim::LandformKind::Island: return "landform.island";
        case sim::LandformKind::Plain: return "landform.plain";
        case sim::LandformKind::Hills: return "landform.hills";
        case sim::LandformKind::Mountains: return "landform.mountains";
        case sim::LandformKind::Basin: return "landform.basin";
        case sim::LandformKind::Crest: return "landform.crest";
        case sim::LandformKind::Pass: return "landform.pass";
        case sim::LandformKind::Cliff: return "landform.cliff";
        case sim::LandformKind::Ramp: return "landform.ramp";
        case sim::LandformKind::Count: break;
    }
    return "landform.coast";
}

const char* water_key(WaterKind kind) {
    switch (kind) {
        case WaterKind::River: return "landform.river";
        case WaterKind::Lake: return "landform.lake";
        case WaterKind::Sea: return "landform.sea";
        case WaterKind::None: break;
    }
    return "landform.none";
}

const char* terrain_key(sim::Terrain terrain) {
    switch (terrain) {
        case sim::Terrain::Grass: return "terrain.grass";
        case sim::Terrain::Meadow: return "terrain.meadow";
        case sim::Terrain::ForestFloor: return "terrain.forestFloor";
        case sim::Terrain::Sand: return "terrain.sand";
        case sim::Terrain::Rock: return "terrain.rock";
        case sim::Terrain::Clay: return "terrain.clay";
        case sim::Terrain::Water: return "terrain.water";
        case sim::Terrain::Count: break;
    }
    return "terrain.grass";
}

std::vector<std::string> describe_lines(const CellDescription& d, const sim::Content* content) {
    if (!d.inside) {
        return {tr("cursor.outside")};
    }
    const std::string biome = content != nullptr && d.biome < content->flora.biomes.size()
                                  ? tr(content->flora.biomes[d.biome].name_key)
                                  : std::string("?");
    std::vector<std::string> lines = {
        tr("cursor.cell", d.cx, d.cz),
        tr("cursor.ground", tr(terrain_key(d.terrain)), biome),
        tr("cursor.height", meters(d.height_cm), d.slope_pct),
        tr("cursor.fertility", d.fertility_pct),
    };
    if (d.water != WaterKind::None) {
        lines.push_back(tr("cursor.water", tr(water_key(d.water)), meters(d.water_depth_cm)));
    }
    if (d.region) {
        lines.push_back(tr("cursor.region", tr(landform_key(*d.region))));
    }
    std::string names;
    const auto add = [&](const char* key) { names += (names.empty() ? "" : ", ") + tr(key); };
    if (d.coast) {
        add("landform.coast");
    }
    for (const sim::LandformKind k : d.landforms) {
        add(landform_key(k));
    }
    lines.push_back(tr("cursor.landforms", names.empty() ? tr("landform.none") : names));
    return lines;
}

}  // namespace sc
