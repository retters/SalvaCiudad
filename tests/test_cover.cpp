#include <doctest.h>

#include <algorithm>
#include <array>
#include <cmath>
#include <filesystem>
#include <memory>
#include <optional>
#include <string>

#include "core/file_io.h"
#include "game/ground_cover.h"
#include "render/model.h"
#include "sim/game.h"
#include "sim/worldgen.h"
#include "test_util.h"

using namespace sc;

namespace {

using cover::Kind;
using cover::When;

const sim::Content& content() {
    return test::core_content();
}

std::uint8_t biome(std::string_view id) {
    const int b = content().flora.find_biome(id);
    REQUIRE(b >= 0);
    return static_cast<std::uint8_t>(b);
}

// A flat, dry map of one ground and one biome, `size` cells a side.
sim::MapData flat(sim::Terrain terrain, std::string_view biome_id, std::int32_t size = 128) {
    sim::MapData m;
    m.size = size;
    const auto cells = static_cast<std::size_t>(size) * static_cast<std::size_t>(size);
    m.heights.assign(static_cast<std::size_t>(size + 1) * static_cast<std::size_t>(size + 1), 1000);
    m.water.assign(cells, 0);
    m.terrain.assign(cells, static_cast<std::uint8_t>(terrain));
    m.fertility.assign(cells, 128);
    m.biome.assign(cells, biome(biome_id));
    return m;
}

When at(sim::Season season, bool snow = false, bool frozen = false) {
    When w;
    w.season = season;
    w.snow = snow;
    w.frozen = frozen;
    return w;
}

// How many squares of the map have each kind of adornment.
std::array<int, cover::kKinds> count(const sim::MapData& map, const When& when) {
    std::array<int, cover::kKinds> out{};
    for (std::int32_t sz = 0; sz < map.size / cover::kSquare; ++sz) {
        for (std::int32_t sx = 0; sx < map.size / cover::kSquare; ++sx) {
            if (const auto item = cover::item_at(map, content(), when, sx, sz)) {
                ++out[static_cast<std::size_t>(item->kind)];
            }
        }
    }
    return out;
}

int of(const std::array<int, cover::kKinds>& counts, Kind kind) {
    return counts[static_cast<std::size_t>(kind)];
}

int flowers(const std::array<int, cover::kKinds>& c) {
    return of(c, Kind::FlowersRed) + of(c, Kind::FlowersYellow) + of(c, Kind::FlowersBlue) + of(c, Kind::FlowersWhite) +
           of(c, Kind::FlowersMixed) + of(c, Kind::Sunflowers) + of(c, Kind::AlpineFlowers);
}

}  // namespace

TEST_SUITE("cover") {
    TEST_CASE("the same square always has the same adornment, inside it and on the map") {
        const sim::MapData map = flat(sim::Terrain::Meadow, "core:temperate");
        const When spring = at(sim::Season::Spring);
        int items = 0;
        for (std::int32_t sz = -2; sz < map.size / cover::kSquare + 2; ++sz) {
            for (std::int32_t sx = -2; sx < map.size / cover::kSquare + 2; ++sx) {
                const auto a = cover::item_at(map, content(), spring, sx, sz);
                const auto b = cover::item_at(map, content(), spring, sx, sz);
                REQUIRE(a.has_value() == b.has_value());
                if (!a) {
                    continue;
                }
                ++items;
                CHECK(a->kind == b->kind);
                CHECK(a->x == b->x);
                CHECK(a->z == b->z);
                CHECK(a->yaw == b->yaw);
                // Inside its own square, and so inside the map.
                CHECK(a->x >= static_cast<float>(sx * cover::kSquare));
                CHECK(a->x < static_cast<float>((sx + 1) * cover::kSquare));
                CHECK(a->z >= static_cast<float>(sz * cover::kSquare));
                CHECK(a->z < static_cast<float>((sz + 1) * cover::kSquare));
                CHECK(sx >= 0);
                CHECK(sz >= 0);
                CHECK(sx < map.size / cover::kSquare);
                CHECK(sz < map.size / cover::kSquare);
                CHECK(a->scale > 0.7f);
                CHECK(a->scale < 1.3f);
            }
        }
        // A meadow is dressed, but not carpeted: most squares stay plain.
        const int squares = (map.size / cover::kSquare) * (map.size / cover::kSquare);
        CHECK(items > squares / 20);
        CHECK(items < squares / 2);
    }

    TEST_CASE("each ground and each biome has its own") {
        const When spring = at(sim::Season::Spring);
        const When summer = at(sim::Season::Summer);
        // Forest floor: ferns where the biome has them, petals in the flowering forest.
        const auto boreal = count(flat(sim::Terrain::ForestFloor, "core:boreal"), spring);
        CHECK(of(boreal, Kind::Fern) > 0);
        CHECK(of(boreal, Kind::PetalsPink) + of(boreal, Kind::PetalsPurple) == 0);
        CHECK(flowers(boreal) == 0);
        const auto flowering = count(flat(sim::Terrain::ForestFloor, "core:flowering"), spring);
        CHECK(of(flowering, Kind::PetalsPink) > 0);
        CHECK(of(flowering, Kind::PetalsPurple) > 0);
        CHECK(of(flowering, Kind::Fern) > 0);
        const auto savanna_forest = count(flat(sim::Terrain::ForestFloor, "core:savanna"), spring);
        CHECK(of(savanna_forest, Kind::Fern) == 0);
        // Meadows: flowers and tall grass; clover only where the biome has it.
        const auto temperate = count(flat(sim::Terrain::Meadow, "core:temperate"), spring);
        CHECK(flowers(temperate) > 0);
        CHECK(of(temperate, Kind::GrassTall) > 0);
        CHECK(of(temperate, Kind::Clover) > 0);
        CHECK(of(temperate, Kind::AlpineFlowers) == 0);
        CHECK(of(temperate, Kind::Fern) == 0);
        const auto savanna = count(flat(sim::Terrain::Meadow, "core:savanna"), summer);
        CHECK(of(savanna, Kind::Clover) == 0);
        CHECK(of(savanna, Kind::GrassDry) > 0);   // Dry summers.
        CHECK(of(savanna, Kind::GrassTall) == 0);
        CHECK(flowers(savanna) < flowers(count(flat(sim::Terrain::Meadow, "core:flowering"), summer)));
        // The mountain: its own flowers, scree on bare rock, and nothing of the lowlands' on rock.
        const auto alp = count(flat(sim::Terrain::Meadow, "core:mountain"), spring);
        CHECK(of(alp, Kind::AlpineFlowers) > 0);
        CHECK(of(alp, Kind::FlowersRed) == 0);
        const auto rock = count(flat(sim::Terrain::Rock, "core:mountain"), spring);
        CHECK(of(rock, Kind::Scree) > 0);
        CHECK(of(rock, Kind::Crag) == 0);  // Flat ground.
        CHECK(flowers(rock) == 0);
        const auto lowland_rock = count(flat(sim::Terrain::Rock, "core:temperate"), spring);
        CHECK(std::all_of(lowland_rock.begin(), lowland_rock.end(), [](int n) { return n == 0; }));
        // Sand and clay away from water are bare.
        const auto sand = count(flat(sim::Terrain::Sand, "core:temperate"), spring);
        CHECK(std::all_of(sand.begin(), sand.end(), [](int n) { return n == 0; }));
    }

    TEST_CASE("crags stand only where the mountain is too steep to walk") {
        sim::MapData steep = flat(sim::Terrain::Rock, "core:mountain");
        // A slope of one meter up per meter along x.
        for (std::int32_t vz = 0; vz <= steep.size; ++vz) {
            for (std::int32_t vx = 0; vx <= steep.size; ++vx) {
                steep.heights[static_cast<std::size_t>(vz) * static_cast<std::size_t>(steep.size + 1) + static_cast<std::size_t>(vx)] =
                    static_cast<std::uint16_t>(1000 + vx * 100);
            }
        }
        CHECK(of(count(steep, at(sim::Season::Summer)), Kind::Crag) > 0);
        sim::MapData lowland = steep;
        std::fill(lowland.biome.begin(), lowland.biome.end(), biome("core:temperate"));
        CHECK(of(count(lowland, at(sim::Season::Summer)), Kind::Crag) == 0);
    }

    TEST_CASE("the year changes what is there") {
        const sim::MapData meadow = flat(sim::Terrain::Meadow, "core:temperate");
        const auto spring = count(meadow, at(sim::Season::Spring));
        const auto summer = count(meadow, at(sim::Season::Summer));
        const auto autumn = count(meadow, at(sim::Season::Autumn));
        const auto winter = count(meadow, at(sim::Season::Winter, true, true));
        // Flowers come up in spring and are gone by autumn; sunflowers are summer's.
        CHECK(flowers(spring) > 0);
        CHECK(flowers(summer) == flowers(spring));
        CHECK(of(spring, Kind::Sunflowers) == 0);
        CHECK(of(summer, Kind::Sunflowers) > 0);
        CHECK(flowers(autumn) == 0);
        // The grass dries in autumn; clover is of spring and summer.
        CHECK(of(spring, Kind::GrassDry) == 0);
        CHECK(of(autumn, Kind::GrassTall) == 0);
        CHECK(of(autumn, Kind::GrassDry) == of(spring, Kind::GrassTall));
        CHECK(of(autumn, Kind::Clover) == 0);
        // Under the snow there is no plant to see.
        for (std::size_t k = 0; k < cover::kKinds; ++k) {
            CHECK_MESSAGE((winter[k] == 0 || !cover::plant(static_cast<Kind>(k))), k);
        }
        // Petals only while the trees are in bloom.
        const sim::MapData forest = flat(sim::Terrain::ForestFloor, "core:flowering");
        CHECK(of(count(forest, at(sim::Season::Summer)), Kind::PetalsPink) == 0);
    }

    TEST_CASE("water has nothing but ice floes, and its shores their own things") {
        // The left half is water: a lake, or the sea when its level says so.
        sim::MapData lake = flat(sim::Terrain::Grass, "core:temperate", 256);
        for (std::int32_t cz = 0; cz < lake.size; ++cz) {
            for (std::int32_t cx = 0; cx < lake.size / 2; ++cx) {
                lake.water[static_cast<std::size_t>(cz) * static_cast<std::size_t>(lake.size) + static_cast<std::size_t>(cx)] = 1100;
            }
        }
        const auto on_water = [&](const sim::MapData& map, const When& when, Kind allowed) {
            int found = 0;
            for (std::int32_t sz = 0; sz < map.size / cover::kSquare; ++sz) {
                for (std::int32_t sx = 0; sx < map.size / cover::kSquare; ++sx) {
                    const auto item = cover::item_at(map, content(), when, sx, sz);
                    if (item && map.water_at(static_cast<std::int32_t>(item->x), static_cast<std::int32_t>(item->z))) {
                        CHECK(item->kind == allowed);
                        ++found;
                    }
                }
            }
            return found;
        };
        CHECK(on_water(lake, at(sim::Season::Summer), Kind::IceFloe) == 0);
        CHECK(on_water(lake, at(sim::Season::Winter, true, true), Kind::IceFloe) > 0);
        // Reeds by the lake, and only by it.
        const auto summer = count(lake, at(sim::Season::Summer));
        CHECK(of(summer, Kind::Reeds) > 0);
        CHECK(of(summer, Kind::Shells) + of(summer, Kind::Driftwood) + of(summer, Kind::TidePool) == 0);
        for (std::int32_t sz = 0; sz < lake.size / cover::kSquare; ++sz) {
            for (std::int32_t sx = 0; sx < lake.size / cover::kSquare; ++sx) {
                const auto item = cover::item_at(lake, content(), at(sim::Season::Summer), sx, sz);
                if (item && item->kind == Kind::Reeds) {
                    CHECK(item->x < static_cast<float>(lake.size / 2 + 3));
                }
            }
        }
        // The same water as sea, with sand along it: what the tide leaves, and no reeds.
        sim::MapData coast = lake;
        coast.sea_levels.assign(1, 1100);
        for (std::int32_t cz = 0; cz < coast.size; ++cz) {
            for (std::int32_t cx = coast.size / 2; cx < coast.size / 2 + 8; ++cx) {
                coast.terrain[static_cast<std::size_t>(cz) * static_cast<std::size_t>(coast.size) + static_cast<std::size_t>(cx)] =
                    static_cast<std::uint8_t>(sim::Terrain::Sand);
            }
        }
        const auto beach = count(coast, at(sim::Season::Summer));
        CHECK(of(beach, Kind::Shells) > 0);
        CHECK(of(beach, Kind::Driftwood) > 0);
        CHECK(of(beach, Kind::Reeds) == 0);
    }

    TEST_CASE("wild flowers grow in patches on meadows, by the biome") {
        const sim::MapData meadow = flat(sim::Terrain::Meadow, "core:temperate");
        const sim::MapData grass = flat(sim::Terrain::Grass, "core:temperate");
        const sim::MapData rich = flat(sim::Terrain::Meadow, "core:flowering");
        const sim::MapData poor = flat(sim::Terrain::Meadow, "core:savanna");
        long long sum_meadow = 0, sum_grass = 0, sum_rich = 0, sum_poor = 0;
        int with = 0;
        for (std::int32_t cz = 0; cz < meadow.size; ++cz) {
            for (std::int32_t cx = 0; cx < meadow.size; ++cx) {
                const std::int32_t f = sim::wildflowers(meadow, content(), cx, cz);
                CHECK(f >= 0);
                CHECK(f <= 100);
                CHECK(f == sim::wildflowers(meadow, content(), cx, cz));
                // A patch is a square of 8 m: its cells are alike.
                CHECK(f == sim::wildflowers(meadow, content(), cx & ~7, cz & ~7));
                with += f > 0 ? 1 : 0;
                sum_meadow += f;
                sum_grass += sim::wildflowers(grass, content(), cx, cz);
                sum_rich += sim::wildflowers(rich, content(), cx, cz);
                sum_poor += sim::wildflowers(poor, content(), cx, cz);
            }
        }
        const int cells = meadow.size * meadow.size;
        CHECK(with > cells / 4);
        CHECK(with < cells * 6 / 10);
        CHECK(sum_grass < sum_meadow);
        CHECK(sum_grass > 0);
        CHECK(sum_rich > sum_meadow);
        CHECK(sum_poor < sum_meadow);
        // None on rock, forest floor, sand or water, nor outside the map.
        CHECK(sim::wildflowers(flat(sim::Terrain::Rock, "core:temperate"), content(), 5, 5) == 0);
        CHECK(sim::wildflowers(flat(sim::Terrain::ForestFloor, "core:temperate"), content(), 5, 5) == 0);
        CHECK(sim::wildflowers(meadow, content(), -1, 5) == 0);
        CHECK(sim::wildflowers(meadow, content(), 5, meadow.size) == 0);
        sim::MapData wet = meadow;
        std::fill(wet.water.begin(), wet.water.end(), std::uint16_t{1100});
        CHECK(sim::wildflowers(wet, content(), 5, 5) == 0);
    }

    TEST_CASE("snow gathers against walls and snowmen stand by the plaza, outside the buildings") {
        int drifts = 0;
        int snowmen = 0;
        for (std::int32_t i = 0; i < 400; ++i) {
            const std::int32_t x = 10 + i * 7 % 300, z = 20 + i * 13 % 300, w = 3 + i % 6, d = 3 + i % 5;
            for (const auto& item : {cover::drift_by(x, z, w, d), cover::snowman_by(x, z, w, d)}) {
                if (!item) {
                    continue;
                }
                (item->kind == Kind::SnowDrift ? drifts : snowmen) += 1;
                const bool inside = item->x > static_cast<float>(x) && item->x < static_cast<float>(x + w) &&
                                    item->z > static_cast<float>(z) && item->z < static_cast<float>(z + d);
                CHECK_FALSE(inside);
                // And close to it.
                CHECK(item->x > static_cast<float>(x) - 2.0f);
                CHECK(item->x < static_cast<float>(x + w) + 2.0f);
                CHECK(item->z > static_cast<float>(z) - 2.0f);
                CHECK(item->z < static_cast<float>(z + d) + 2.0f);
            }
        }
        CHECK(drifts > 120);   // About half the buildings.
        CHECK(drifts < 280);
        CHECK(snowmen > 80);   // About one in three.
        CHECK(snowmen < 190);
    }

    TEST_CASE("the setting: nothing when off, farther with more, still when low") {
        CHECK(cover::reach(0) == 0.0f);
        CHECK(cover::reach(1) > 0.0f);
        CHECK(cover::reach(2) > cover::reach(1));
        CHECK(cover::reach(3) > cover::reach(2));
        CHECK(cover::reach(9) == cover::reach(3));
        CHECK_FALSE(cover::sways(0));
        CHECK_FALSE(cover::sways(1));
        CHECK(cover::sways(2));
        CHECK(cover::sways(3));
    }

    TEST_CASE("every adornment has its model: light, still and unlit") {
        // The limits are those of art/blender/proposals/game.json: 400 triangles for
        // what the ground is dressed with, 1500 for the few large pieces.
        const std::filesystem::path core = std::filesystem::path(SC_SOURCE_DIR) / "data" / "mods" / "core";
        for (std::size_t k = 0; k < cover::kKinds; ++k) {
            const auto kind = static_cast<Kind>(k);
            const std::string file(cover::model_file(kind));
            const auto bytes = fs::read_file(core / file, render::model_limits::kMaxFileBytes);
            REQUIRE_MESSAGE(bytes.error == fs::IoError::None, file);
            const render::ModelLoadResult r =
                render::load_glb({reinterpret_cast<const std::uint8_t*>(bytes.data.data()), bytes.data.size()});
            REQUIRE_MESSAGE(r.ok, file << ": " << r.error);
            const bool large = kind == Kind::Scree || kind == Kind::Crag || kind == Kind::TidePool || kind == Kind::Snowman ||
                               kind == Kind::BeaverDam;
            CHECK_MESSAGE(r.model.indices.size() / 3 <= (large ? 1500u : 400u), file << ": " << r.model.indices.size() / 3);
            CHECK_MESSAGE(!r.model.skinned(), file);
            CHECK_MESSAGE(r.model.clips.empty(), file);
            for (const render::ModelMaterial& mat : r.model.materials) {
                CHECK_MESSAGE(render::material_glow(mat.name) == 0.0f, file << " " << mat.name);
            }
        }
        // Plants are the kinds snow hides and wind sways; rocks, driftwood and snow are not.
        CHECK(cover::plant(Kind::GrassTall));
        CHECK(cover::plant(Kind::Reeds));
        CHECK(cover::plant(Kind::AlpineFlowers));
        CHECK_FALSE(cover::plant(Kind::Scree));
        CHECK_FALSE(cover::plant(Kind::Driftwood));
        CHECK_FALSE(cover::plant(Kind::Snowman));
    }

    TEST_CASE("dressing the ground never touches the game") {
        sim::MapSettings s;
        s.seed = 11;
        s.size = sim::MapSize::Small;
        auto map = sim::generate_map(s, content());
        REQUIRE(map.has_value());
        sim::GameSetup setup;
        setup.seed = 5;
        sim::Game game(std::shared_ptr<const sim::Content>(std::shared_ptr<const sim::Content>{}, &content()), *map, setup);
        for (int i = 0; i < 50; ++i) {
            game.step();
        }
        const std::uint64_t before = game.hash();
        const std::uint64_t checksum = game.map().checksum();
        // A generated map is dressed too, whatever the season; on water only with ice.
        int items = 0;
        for (const When& when : {cover::when(game), at(sim::Season::Summer), at(sim::Season::Winter, true, true)}) {
            for (std::int32_t sz = 0; sz < game.map().size / cover::kSquare; ++sz) {
                for (std::int32_t sx = 0; sx < game.map().size / cover::kSquare; ++sx) {
                    const auto item = cover::item_at(game.map(), game.content(), when, sx, sz);
                    if (!item) {
                        continue;
                    }
                    ++items;
                    const auto cx = static_cast<std::int32_t>(item->x), cz = static_cast<std::int32_t>(item->z);
                    REQUIRE(cx >= 0);
                    REQUIRE(cz >= 0);
                    REQUIRE(cx < game.map().size);
                    REQUIRE(cz < game.map().size);
                    // (On the water: floes when it freezes and, across a stream, a beaver dam: phase 110.)
                    CHECK((!game.map().water_at(cx, cz) || item->kind == Kind::IceFloe || item->kind == Kind::BeaverDam));
                }
            }
        }
        CHECK(items > 300);
        CHECK(game.hash() == before);
        CHECK(game.map().checksum() == checksum);
    }
}
