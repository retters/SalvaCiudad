#include <doctest.h>

#include <algorithm>
#include <map>
#include <memory>
#include <optional>

#include "game/terrain_names.h"
#include "sim/game.h"
#include "sim/worldgen.h"
#include "sim/worldgen_hier.h"
#include "test_util.h"

using namespace sc;
using sim::LandformKind;

namespace {

sim::MapSettings hier_settings(std::uint64_t seed, sim::MapSize size) {
    sim::MapSettings s;
    s.seed = seed;
    s.size = size;
    s.players = 2;
    s.sea = sim::Sea::None;
    s.generator = sim::MapGenerator::Hierarchical;
    return s;
}

sim::MapData generate(const sim::MapSettings& s) {
    std::optional<sim::MapData> m = sim::generate_map(s, sc::test::core_content());
    REQUIRE(m.has_value());
    return std::move(*m);
}

bool is_region(LandformKind k) {
    return k == LandformKind::Plain || k == LandformKind::Hills || k == LandformKind::Mountains ||
           k == LandformKind::Plateau || k == LandformKind::Basin;
}

// How many squares of the map each region kind covers.
std::map<LandformKind, std::int64_t> region_squares(const sim::MapData& m) {
    std::map<LandformKind, std::int64_t> out;
    for (const std::uint16_t owner : m.region_owner) {
        ++out[m.landforms[owner - 1u].kind];
    }
    return out;
}

std::shared_ptr<const sim::Content> shared_content() {
    return std::shared_ptr<const sim::Content>(std::shared_ptr<const sim::Content>{}, &sc::test::core_content());
}

}  // namespace

TEST_SUITE("worldgen_hier") {
    TEST_CASE("the generator is a setting of the map, kept in saves") {
        sim::MapSettings s = hier_settings(5, sim::MapSize::Small);
        sim::BinaryWriter w;
        s.write(w);
        sim::MapSettings back;
        sim::BinaryReader r(w.bytes());
        REQUIRE(sim::MapSettings::read(r, back));
        CHECK(back == s);
        // An unknown generator is refused.
        std::vector<std::uint8_t> bytes = w.bytes();
        bytes.back() = static_cast<std::uint8_t>(sim::MapGenerator::Count);
        sim::BinaryReader bad(bytes);
        CHECK_FALSE(sim::MapSettings::read(bad, back));
        // A classic map is named as before there was a choice.
        sim::MapSettings classic = s;
        classic.generator = sim::MapGenerator::Classic;
        sim::BinaryWriter identity;
        classic.write_identity(identity);
        sim::BinaryWriter full;
        classic.write(full);
        CHECK(identity.bytes().size() + 1 == full.bytes().size());
    }

    TEST_CASE("every square of a hierarchical map is in one region, the same each time") {
        const sim::MapData m = generate(hier_settings(11, sim::MapSize::Medium));
        CHECK(m.generator_version == sim::hier::kVersion);
        const auto side = static_cast<std::size_t>(m.owner_side());
        REQUIRE(m.region_owner.size() == side * side);
        REQUIRE(m.structure_owner.size() == side * side);
        for (const std::uint16_t owner : m.region_owner) {
            REQUIRE(owner >= 1);
            REQUIRE(owner <= m.landforms.size());
            CHECK(is_region(m.landforms[owner - 1u].kind));
        }
        // Several kinds of region, most of it plain.
        const auto squares = region_squares(m);
        CHECK(squares.size() >= 3);
        CHECK(squares.at(LandformKind::Plain) * 3 >= static_cast<std::int64_t>(m.region_owner.size()));
        // The same settings, the same map.
        const sim::MapData again = generate(hier_settings(11, sim::MapSize::Medium));
        CHECK(again.checksum() == m.checksum());
        CHECK(again.region_owner == m.region_owner);
        // Another generator, another map.
        sim::MapSettings classic = hier_settings(11, sim::MapSize::Medium);
        classic.generator = sim::MapGenerator::Classic;
        CHECK(generate(classic).checksum() != m.checksum());
    }

    TEST_CASE("the options change how many regions are not plains") {
        std::int64_t few = 0;
        std::int64_t many = 0;
        std::int64_t mountains_low = 0;
        std::int64_t mountains_high = 0;
        for (std::uint64_t seed = 20; seed < 24; ++seed) {
            sim::MapSettings s = hier_settings(seed, sim::MapSize::Medium);
            s.landforms = sim::Amount::Low;
            s.relief = sim::Relief::Low;
            auto low = region_squares(generate(s));
            for (const auto& [k, n] : low) {
                few += k == LandformKind::Plain ? 0 : n;
            }
            mountains_low += low[LandformKind::Mountains];
            s.landforms = sim::Amount::High;
            s.relief = sim::Relief::Mountainous;
            auto high = region_squares(generate(s));
            for (const auto& [k, n] : high) {
                many += k == LandformKind::Plain ? 0 : n;
            }
            mountains_high += high[LandformKind::Mountains];
        }
        CHECK(many > few);
        CHECK(mountains_high > mountains_low);
    }

    TEST_CASE("plateaus stand above the land around them on a cliff") {
        int measured = 0;
        int good = 0;
        for (std::uint64_t seed = 30; seed < 36; ++seed) {
            const sim::MapData m = generate(hier_settings(seed, sim::MapSize::Medium));
            for (std::size_t i = 0; i < m.landforms.size(); ++i) {
                const sim::Landform& l = m.landforms[i];
                if (l.kind != LandformKind::Plateau) {
                    continue;
                }
                // Its squares against the squares of other regions next to it.
                const std::int32_t side = m.owner_side();
                std::int64_t top = 0, top_n = 0, low = 0, low_n = 0;
                for (std::int32_t bz = 1; bz + 1 < side; ++bz) {
                    for (std::int32_t bx = 1; bx + 1 < side; ++bx) {
                        const auto at = [&](std::int32_t x, std::int32_t z) { return m.region_owner[static_cast<std::size_t>(z * side + x)]; };
                        const std::int32_t h = m.height_cm(bx * sim::kOwnerBlock + 4, bz * sim::kOwnerBlock + 4);
                        const bool mine = at(bx, bz) == i + 1;
                        // Squares well inside, and squares just outside.
                        bool inside = mine;
                        bool beside = false;
                        for (int dz = -3; dz <= 3; ++dz) {
                            for (int dx = -3; dx <= 3; ++dx) {
                                const std::int32_t x = std::clamp(bx + dx, 0, side - 1);
                                const std::int32_t z = std::clamp(bz + dz, 0, side - 1);
                                inside = inside && at(x, z) == i + 1;
                                beside = beside || (!mine && at(x, z) == i + 1);
                            }
                        }
                        if (inside) {
                            top += h;
                            ++top_n;
                        } else if (beside && m.landforms[at(bx, bz) - 1u].kind != LandformKind::Mountains) {
                            low += h;
                            ++low_n;
                        }
                    }
                }
                if (top_n >= 10 && low_n >= 10) {
                    ++measured;
                    good += top / top_n >= low / low_n + 1500 ? 1 : 0;
                }
            }
        }
        MESSAGE(good << " of " << measured << " plateaus stand above their surroundings");
        CHECK(measured > 0);
        CHECK(good * 10 >= measured * 8);
    }

    TEST_CASE("the names under the cursor are the map's own") {
        const sim::MapData m = generate(hier_settings(12, sim::MapSize::Small));
        TerrainNames names;
        for (std::int32_t z = 3; z < m.size; z += 37) {
            for (std::int32_t x = 5; x < m.size; x += 41) {
                const CellDescription d = names.describe(m, x, z);
                REQUIRE(d.region.has_value());
                CHECK(*d.region == m.landforms[m.owner_at(m.region_owner, x, z) - 1u].kind);
            }
        }
    }

    TEST_CASE("a hierarchical game saves and loads its regions") {
        const sim::MapData map = generate(hier_settings(13, sim::MapSize::Small));
        sim::Game g(shared_content(), map, 1, 21);
        sim::BinaryWriter w;
        g.save(w);
        sim::Game back(shared_content(), sim::MapData{}, 0, 0);
        sim::BinaryReader r(w.bytes());
        REQUIRE(back.load(r, shared_content()));
        CHECK(back.map().settings.generator == sim::MapGenerator::Hierarchical);
        CHECK(back.map().region_owner == map.region_owner);
        CHECK(back.map().structure_owner == map.structure_owner);
        CHECK(back.map().checksum() == map.checksum());
    }

    TEST_CASE("separate hierarchical maps keep each region's owners") {
        sim::MapSettings s = hier_settings(14, sim::MapSize::Small);
        s.separate = true;
        const sim::MapData world = generate(s);
        REQUIRE(world.region_owner.size() == static_cast<std::size_t>(world.owner_side()) * world.owner_side());
        const std::int32_t t = world.region_size();
        // Both players' squares name a region inside their own map.
        for (const std::int32_t player : {0, 1}) {
            const std::int32_t cx = (player % 2) * t + t / 2;
            const std::int32_t cz = t / 2;
            const std::uint16_t owner = world.owner_at(world.region_owner, cx, cz);
            REQUIRE(owner >= 1);
            const auto& p = world.landforms[owner - 1u].points[0];
            CHECK(p[0] >= player * t);
            CHECK(p[0] <= player * t + t);
        }
    }
}
