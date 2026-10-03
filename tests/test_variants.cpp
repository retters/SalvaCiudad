#include <doctest.h>

#include <algorithm>
#include <filesystem>
#include <memory>
#include <set>
#include <string>
#include <vector>

#include "game/map_scene.h"
#include "game/variants.h"
#include "mods/mod_library.h"
#include "sim/game.h"
#include "sim/worldgen.h"
#include "test_util.h"

using namespace sc;

namespace {

const std::filesystem::path kBuiltin = std::filesystem::path(SC_SOURCE_DIR) / "data" / "mods";
const std::filesystem::path kTestModels = std::filesystem::path(SC_SOURCE_DIR) / "tests" / "data_models_test";

// A user mod "vt" with `defs` (the "defs" list of a definition file) and
// three model files: a.glb, b.glb and c.glb.
mods::BuildResult build_with(const test::TempDir& dir, std::string_view defs, mods::ModLibrary& lib) {
    const std::filesystem::path root = dir / "vt";
    std::filesystem::create_directories(root / "defs");
    std::filesystem::create_directories(root / "models");
    test::write_text(root / "mod.json", R"({"schemaVersion": 1, "id": "vt", "name": "mod.x", "version": "1.0.0",
        "gameVersion": ">=0.1.0", "dependencies": ["core"]})");
    for (const char* name : {"a.glb", "b.glb", "c.glb"}) {
        std::filesystem::copy_file(kTestModels / "test_house.glb", root / "models" / name,
                                   std::filesystem::copy_options::overwrite_existing);
    }
    test::write_text(root / "defs" / "t.json", std::string(R"({"schemaVersion": 1, "defs": [)") + std::string(defs) + "]}");
    lib.scan(kBuiltin, dir.path(), mods::Version{0, 7, 0});
    lib.select({"vt"});
    return lib.build();
}

std::string errors_of(const mods::ModLibrary& lib, std::string_view mod) {
    const mods::ModInfo* m = lib.find(mod);
    std::string out;
    for (const std::string& e : m != nullptr ? m->errors : std::vector<std::string>{}) {
        out += e + "\n";
    }
    return out;
}

constexpr const char* kShed = R"({"type": "building", "id": "vt:shed", "name": "b.shed", "kind": "decoration",
    "size": [2, 2], "cost": {"core:log": 1}, )";

}  // namespace

TEST_SUITE("variants") {
    TEST_CASE("a definition lists its variants; one model still works") {
        test::TempDir dir;
        mods::ModLibrary lib;
        const mods::BuildResult pack = build_with(dir,
                                                  std::string(kShed) + R"("models": ["models/a.glb", "models/b.glb"],
            "levels": [{"work": 10, "models": ["models/c.glb"]}, {"work": 10}]},
            {"type": "building", "id": "vt:hut", "name": "b.hut", "kind": "decoration", "size": [2, 2],
             "cost": {"core:log": 1}, "model": "models/c.glb"})",
                                                  lib);
        CHECK_MESSAGE(errors_of(lib, "vt").empty(), errors_of(lib, "vt"));
        const sim::DefIndex shed = pack.content.find_building("vt:shed");
        REQUIRE(shed != sim::kNoDef);
        const sim::BuildingDef& s = pack.content.buildings[shed];
        CHECK(s.models == std::vector<std::string>{"models/a.glb", "models/b.glb"});
        REQUIRE(s.levels.size() == 2);
        CHECK(s.levels[0].models == std::vector<std::string>{"models/c.glb"});
        CHECK(s.levels[1].models.empty());
        const sim::DefIndex hut = pack.content.find_building("vt:hut");
        REQUIRE(hut != sim::kNoDef);
        CHECK(pack.content.buildings[hut].models == std::vector<std::string>{"models/c.glb"});
        // The viewer sees every file of the definition, levels included.
        std::size_t shed_refs = 0;
        for (const mods::ModelRef& r : pack.model_refs) {
            shed_refs += r.def_id == "vt:shed" && r.exists;
        }
        CHECK(shed_refs == 3);
        // Core's own variants.
        const sim::BuildingDef& house = pack.content.buildings[pack.content.find_building("core:house")];
        CHECK(house.models.size() == 3);
        for (const sim::LevelDef& level : house.levels) {
            CHECK(level.models.size() == 3);
        }
        CHECK(pack.content.feature(sim::FeatureType::Stone)->models.size() == 3);
    }

    TEST_CASE("bad lists of models are rejected") {
        const char* bad[] = {
            R"("model": "models/a.glb", "models": ["models/b.glb"]})",  // Both.
            R"("models": []})",                                        // Empty.
            R"("models": ["models/a.glb", "models/a.glb"]})",          // Twice.
            R"("models": ["models/a.glb", 3]})",                       // Not a path.
            R"("models": "models/a.glb"})",                            // Not a list.
            R"("models": ["models/a.glb", "models/missing.glb"]})",    // Missing file.
            R"("models": ["../vt/models/a.glb"]})",                    // Outside the mod.
            R"("models": ["models/a.glb","models/b.glb","models/c.glb","m/4","m/5","m/6","m/7","m/8","m/9"]})",
        };
        for (const char* tail : bad) {
            test::TempDir dir;
            mods::ModLibrary lib;
            const mods::BuildResult pack = build_with(dir, std::string(kShed) + tail, lib);
            CHECK_MESSAGE(pack.content.find_building("vt:shed") == sim::kNoDef, tail);
            CHECK_MESSAGE(!errors_of(lib, "vt").empty(), tail);
        }
    }

    TEST_CASE("a mod adds variants to a core building with a patch") {
        test::TempDir dir;
        mods::ModLibrary lib;
        // The patch replaces the list: core's files come from core's folder
        // only while core owns the definition, so the mod lists its own.
        const mods::BuildResult pack = build_with(
            dir, R"({"type": "building", "patch": "core:well", "models": ["models/a.glb", "models/b.glb"]})", lib);
        CHECK_MESSAGE(errors_of(lib, "vt").empty(), errors_of(lib, "vt"));
        const sim::BuildingDef& well = pack.content.buildings[pack.content.find_building("core:well")];
        CHECK(well.models.size() == 2);
        CHECK(well.mod == "vt");
    }

    TEST_CASE("a patch of a house's models keeps core's level models") {
        test::TempDir dir;
        mods::ModLibrary lib;
        const mods::BuildResult pack =
            build_with(dir, R"({"type": "building", "patch": "core:house", "models": ["models/a.glb"]})", lib);
        CHECK_MESSAGE(errors_of(lib, "vt").empty(), errors_of(lib, "vt"));
        const sim::BuildingDef& house = pack.content.buildings[pack.content.find_building("core:house")];
        CHECK(house.mod == "vt");
        REQUIRE(!house.levels.empty());
        CHECK(house.levels[0].models_mod == "core");
        CHECK(house.levels[0].models.size() == 3);
    }

    TEST_CASE("the variant and the palette depend only on the place") {
        std::set<std::size_t> seen;
        std::set<std::uint32_t> palettes;
        const std::size_t count = make_building_palettes().size();
        CHECK(count > 1);
        CHECK(count <= render::kMaxBuildingPalettes);
        for (std::int32_t x = 0; x < 40; ++x) {
            for (std::int32_t z = 0; z < 40; ++z) {
                const std::uint32_t key = place_key(x, z);
                CHECK(key == place_key(x, z));
                const std::size_t v = pick_variant(key, 3);
                REQUIRE(v < 3);
                seen.insert(v);
                const std::uint32_t p = pick_building_palette(key, count);
                REQUIRE(p >= 1);
                REQUIRE(p <= count);
                palettes.insert(p);
            }
        }
        CHECK(seen.size() == 3);                 // Every variant shows up.
        CHECK(palettes.size() > count * 3 / 4);  // And most palettes.
        CHECK(pick_variant(12345, 1) == 0);
        CHECK(pick_variant(12345, 0) == 0);
        CHECK(pick_building_palette(12345, 0) == 0);
    }

    TEST_CASE("map features spread over their variants, the same on every load") {
        const sim::Content& content = test::core_content();
        sim::MapSettings s;
        s.seed = 7;
        s.size = sim::MapSize::Small;
        s.players = 1;
        const std::optional<sim::MapData> map = sim::generate_map(s, content);
        REQUIRE(map.has_value());
        const sim::FeatureDef* stone = content.feature(sim::FeatureType::Stone);
        REQUIRE(stone != nullptr);
        std::set<std::size_t> slots;
        for (const sim::MapFeature& f : map->features) {
            if (f.type != sim::FeatureType::Stone) {
                continue;
            }
            const std::size_t slot = visual_slot(content, f);
            CHECK(slot >= feature_slot(content, sim::FeatureType::Stone, 0));
            CHECK(slot < feature_slot(content, sim::FeatureType::Stone, stone->models.size()));
            CHECK(slot < visual_slot_count(content));
            slots.insert(slot);
        }
        CHECK(slots.size() == stone->models.size());
        // The instances are grouped by those slots.
        const auto instances = build_feature_instances(*map, content);
        CHECK(instances.size() == visual_slot_count(content));
    }

    TEST_CASE("the looks never change the simulation") {
        // The same game with every variant list cut to one model.
        const auto full = std::shared_ptr<const sim::Content>(std::shared_ptr<const sim::Content>{},
                                                              &test::core_content());
        auto plain = std::make_shared<sim::Content>(test::core_content());
        for (sim::BuildingDef& b : plain->buildings) {
            b.models.resize(1);
            for (sim::LevelDef& l : b.levels) {
                l.models.clear();
            }
        }
        for (sim::FeatureDef& f : plain->features) {
            f.models.resize(std::min<std::size_t>(f.models.size(), 1));
        }
        sim::MapSettings s;
        s.seed = 21;
        s.size = sim::MapSize::Small;
        s.sea = sim::Sea::None;
        s.players = 1;
        const std::optional<sim::MapData> a_map = sim::generate_map(s, *full);
        const std::optional<sim::MapData> b_map = sim::generate_map(s, *plain);
        REQUIRE(a_map.has_value());
        REQUIRE(b_map.has_value());
        sim::Game a(full, *a_map, 1, 5);
        sim::Game b(plain, *b_map, 1, 5);
        for (int i = 0; i < 600; ++i) {
            a.step();
            b.step();
        }
        CHECK(a.hash() == b.hash());
    }

    // --- Phase 51: tree models by state ---------------------------------------

    TEST_CASE("a species lists its models by state; an evergreen only the first") {
        test::TempDir dir;
        mods::ModLibrary lib;
        const mods::BuildResult pack = build_with(dir,
            R"({"type": "species", "id": "vt:leafy", "name": "s.leafy", "sizes": ["small", "large"],
                "models": {"bloom": ["models/a.glb", {"model": "models/b.glb", "far": "models/c.glb"}],
                           "autumn": ["models/b.glb"], "bare": ["models/c.glb"]}},
               {"type": "species", "id": "vt:green", "name": "s.green", "sizes": ["medium"],
                "models": {"bloom": ["models/a.glb"]}})", lib);
        REQUIRE_MESSAGE(errors_of(lib, "vt").empty(), errors_of(lib, "vt"));
        const sim::Flora& flora = pack.content.flora;
        const int leafy = flora.find_species("vt:leafy");
        const int green = flora.find_species("vt:green");
        REQUIRE(leafy >= 0);
        REQUIRE(green >= 0);
        const sim::SpeciesDef& l = flora.species[static_cast<std::size_t>(leafy)];
        CHECK(l.state_models[0] == std::vector<std::string>{"models/a.glb", "models/b.glb"});
        CHECK(l.state_models[1] == std::vector<std::string>{"models/b.glb"});
        CHECK(l.state_models[2] == std::vector<std::string>{"models/c.glb"});
        // The far versions, one entry per file ("" without one).
        CHECK(l.state_far[0] == std::vector<std::string>{"", "models/c.glb"});
        CHECK(l.state_far[1] == std::vector<std::string>{""});
        const sim::SpeciesDef& g = flora.species[static_cast<std::size_t>(green)];
        CHECK(g.state_models[1].empty());
        CHECK(tree_model_file(g, sim::TreeState::Bare) == "models/a.glb");
        CHECK(tree_model_file(l, sim::TreeState::Bare) == "models/c.glb");
    }

    TEST_CASE("bad models by state are rejected") {
        const char* kHead = R"({"type": "species", "id": "vt:t", "name": "s.t", "sizes": ["small"], )";
        for (const char* tail : {
                 R"("models": ["models/a.glb"]})",                                       // A list is for other things.
                 R"("models": {"autumn": ["models/a.glb"]}})",                            // No bloom.
                 R"("models": {"bloom": []}})",
                 R"("models": {"bloom": ["models/a.glb"], "spring": ["models/b.glb"]}})",  // Unknown state.
                 R"("models": {"bloom": ["models/a.glb", "models/a.glb"]}})",
                 R"("models": {"bloom": ["models/missing.glb"]}})",
                 R"("models": {"bloom": "models/a.glb"}})",
                 R"("model": "models/a"})",                                               // The form before phase 51.
                 R"("models": {"bloom": [{"model": "models/a.glb"}]}})",                        // A pair needs its far file.
                 R"("models": {"bloom": [{"model": "models/a.glb", "far": "models/missing.glb"}]}})",
                 R"("models": {"bloom": [{"model": "models/a.glb", "far": "models/b.glb", "x": 1}]}})",
             }) {
            test::TempDir dir;
            mods::ModLibrary lib;
            const mods::BuildResult pack = build_with(dir, std::string(kHead) + tail, lib);
            CHECK_MESSAGE(pack.content.flora.find_species("vt:t") < 0, tail);
            CHECK_MESSAGE(!errors_of(lib, "vt").empty(), tail);
        }
    }

    TEST_CASE("trees turn with the season, each at its own step") {
        using sim::Season;
        using sim::TreeState;
        // The calendar: the turn takes the first fifth of the season.
        CHECK(tree_calendar(Season::Autumn, 0).turn == 0);
        CHECK(tree_calendar(Season::Autumn, kTurnProgress / 2).turn == kTurnSteps / 2);
        CHECK(tree_calendar(Season::Autumn, kTurnProgress).turn == kTurnSteps);
        CHECK(tree_calendar(Season::Autumn, 999).turn == kTurnSteps);
        CHECK(TreeCalendar{}.turn == kTurnSteps);

        std::vector<sim::MapFeature> trees(400);
        for (std::size_t i = 0; i < trees.size(); ++i) {
            trees[i].type = sim::FeatureType::Tree;
            trees[i].x = sim::Fixed::from_ratio(static_cast<std::int32_t>(i * 37 + 5), 3);
            trees[i].z = sim::Fixed::from_ratio(static_cast<std::int32_t>(i * 91 + 11), 7);
        }
        const auto count = [&](TreeCalendar when, TreeState state) {
            std::size_t n = 0;
            for (const sim::MapFeature& f : trees) {
                n += tree_state(f, when) == state ? 1u : 0u;
            }
            return n;
        };
        // Before the turn starts, all are still in the state of summer; then
        // more and more turn; at the end, all have.
        CHECK(count({Season::Autumn, 0}, TreeState::Bloom) == trees.size());
        std::size_t last = 0;
        for (int turn = 1; turn <= kTurnSteps; ++turn) {
            const std::size_t turned = count({Season::Autumn, turn}, TreeState::Autumn);
            CHECK(turned > last);
            CHECK(turned + count({Season::Autumn, turn}, TreeState::Bloom) == trees.size());
            last = turned;
        }
        CHECK(last == trees.size());
        // In the first days of autumn there are trees in both states.
        const std::size_t early = count({Season::Autumn, kTurnSteps / 2}, TreeState::Autumn);
        CHECK(early > trees.size() / 4);
        CHECK(early < trees.size() * 3 / 4);
        // Winter bares them, spring brings the leaves back, summer changes nothing.
        CHECK(count({Season::Winter, 0}, TreeState::Autumn) == trees.size());
        CHECK(count({Season::Winter, kTurnSteps}, TreeState::Bare) == trees.size());
        CHECK(count({Season::Spring, 0}, TreeState::Bare) == trees.size());
        CHECK(count({Season::Spring, kTurnSteps}, TreeState::Bloom) == trees.size());
        CHECK(count({Season::Summer, 0}, TreeState::Bloom) == trees.size());
        // A tree turns once and stays.
        for (const sim::MapFeature& f : trees) {
            bool turned = false;
            for (int turn = 0; turn <= kTurnSteps; ++turn) {
                const bool now = tree_state(f, {Season::Autumn, turn}) == TreeState::Autumn;
                CHECK((now || !turned));
                turned = now;
            }
        }
    }

    TEST_CASE("a tree keeps its slot and changes its look; the cherry of core has four variants") {
        const sim::Content& content = test::core_content();
        const int cherry = content.flora.find_species("core:cherry");
        REQUIRE(cherry >= 0);
        const sim::SpeciesDef& sp = content.flora.species[static_cast<std::size_t>(cherry)];
        for (std::size_t st = 0; st < sim::kTreeStates; ++st) {
            CHECK(sp.state_models[st].size() == 4);
        }
        sim::MapFeature f;
        f.type = sim::FeatureType::Tree;
        f.species = static_cast<std::uint8_t>(cherry);
        f.size = static_cast<std::uint8_t>(sim::TreeSize::Medium);
        f.x = sim::Fixed::from_int(40);
        f.z = sim::Fixed::from_int(90);
        const auto c = static_cast<std::size_t>(cherry);
        CHECK(visual_slot(content, f) >= tree_variant_slot(c, 0));
        CHECK(visual_slot(content, f) < tree_variant_slot(c, 4));
        CHECK(visual_slot(content, f) < tree_slot_count(content));
        CHECK(tree_look(content, f, {sim::Season::Summer, kTurnSteps}) == 0);
        CHECK(tree_look(content, f, {sim::Season::Autumn, kTurnSteps}) == 1);
        CHECK(tree_look(content, f, {sim::Season::Winter, kTurnSteps}) == 2);
        CHECK(tree_look(content, f, {sim::Season::Winter, 0}) == 1);  // Its turn has not come.
        // Phase 52: every state has its far version.
        for (std::size_t st = 0; st < sim::kTreeStates; ++st) {
            REQUIRE(sp.state_far[st].size() == 4);
            CHECK_FALSE(sp.state_far[st][0].empty());
        }
        // An evergreen looks the same all year.
        const int pine = content.flora.find_species("core:pine");
        REQUIRE(pine >= 0);
        f.species = static_cast<std::uint8_t>(pine);
        CHECK(visual_slot(content, f) == tree_variant_slot(static_cast<std::size_t>(pine), 0));
        CHECK(tree_look(content, f, {sim::Season::Winter, kTurnSteps}) == 0);
        // A tree keeps its own colors all year (only the snow whitens it);
        // a bush turns.
        sim::MapSettings s;
        s.seed = 7;
        s.size = sim::MapSize::Small;
        const std::optional<sim::MapData> map = sim::generate_map(s, content);
        REQUIRE(map.has_value());
        f.x = sim::Fixed::from_int(100);
        f.z = sim::Fixed::from_int(100);
        f.species = static_cast<std::uint8_t>(cherry);
        const render::Instance summer = feature_instance(*map, f, &content, sim::Season::Summer, false);
        CHECK(feature_instance(*map, f, &content, sim::Season::Autumn, false).tint == summer.tint);
        CHECK(feature_instance(*map, f, &content, sim::Season::Winter, false).tint == summer.tint);
        CHECK_FALSE(feature_instance(*map, f, &content, sim::Season::Winter, true).tint == summer.tint);
        sim::MapFeature bush = f;
        bush.type = sim::FeatureType::BerryBush;
        const render::Instance bush_summer = feature_instance(*map, bush, &content, sim::Season::Summer, false);
        CHECK_FALSE(feature_instance(*map, bush, &content, sim::Season::Autumn, false).tint == bush_summer.tint);
        // The instances of a season carry each tree's look; they stay in the
        // same slots and the same order all year, so a change of state only
        // changes looks.
        const auto summer_all = build_feature_instances(*map, content, {sim::Season::Summer, kTurnSteps}, false);
        // The trees that lose their leaves: those of a species with autumn models.
        std::size_t cherries = 0;
        for (const sim::MapFeature& t : map->features) {
            cherries += t.type == sim::FeatureType::Tree && !content.flora.species[t.species].state_models[1].empty() ? 1u : 0u;
        }
        REQUIRE(cherries > 0);
        for (const int turn : {0, kTurnSteps / 2, kTurnSteps}) {
            const auto autumn_all = build_feature_instances(*map, content, {sim::Season::Autumn, turn}, false);
            REQUIRE(autumn_all.size() == summer_all.size());
            std::size_t turned = 0;
            for (std::size_t slot = 0; slot < autumn_all.size(); ++slot) {
                REQUIRE(autumn_all[slot].size() == summer_all[slot].size());
                for (std::size_t i = 0; i < autumn_all[slot].size(); ++i) {
                    CHECK(autumn_all[slot][i].position == summer_all[slot][i].position);
                    CHECK(summer_all[slot][i].look == 0);
                    turned += autumn_all[slot][i].look == 1 ? 1u : 0u;
                }
            }
            CHECK(turned == (turn == 0 ? 0u : turn == kTurnSteps ? cherries : turned));
            CHECK((turn != kTurnSteps / 2 || (turned > 0 && turned < cherries)));
        }
    }
}
