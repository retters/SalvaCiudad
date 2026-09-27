#include <doctest.h>

#include <algorithm>
#include <filesystem>
#include <string>

#include "core/file_io.h"
#include "game/builtin_models.h"
#include "mods/mod_library.h"
#include "render/model.h"
#include "viewer/model_catalog.h"

using namespace sc;

namespace {

const std::filesystem::path kBuiltin = std::filesystem::path(SC_SOURCE_DIR) / "data" / "mods";
const std::filesystem::path kFixtureMods = std::filesystem::path(SC_TEST_FIXTURES_DIR) / "mods";

// The catalog the viewer shows for core plus `mod` (none: core alone).
viewer::Catalog catalog_for(const char* mod = nullptr) {
    mods::ModLibrary lib;
    lib.scan(kBuiltin, kFixtureMods, mods::Version{0, 7, 0});
    lib.select(mod != nullptr ? std::vector<std::string>{mod} : std::vector<std::string>{});
    const mods::BuildResult pack = lib.build();
    std::vector<viewer::ModFolder> folders;
    for (const mods::ModInfo& m : lib.mods()) {
        if (m.manifest.id == mods::kCoreModId || (mod != nullptr && m.manifest.id == mod)) {
            folders.push_back({m.manifest.id, m.dir});
        }
    }
    return viewer::build_catalog(folders, pack.model_refs);
}

const viewer::CatalogGroup* group(const viewer::Catalog& c, std::string_view id) {
    for (const viewer::CatalogGroup& g : c.groups) {
        if (g.id == id) {
            return &g;
        }
    }
    return nullptr;
}

render::ModelData load(const char* file) {
    const fs::ReadResult r =
        fs::read_file(std::filesystem::path(SC_SOURCE_DIR) / "tests" / "data_models_test" / file, 1u << 20);
    REQUIRE(r.error == fs::IoError::None);
    render::ModelLoadResult m = render::load_glb({reinterpret_cast<const std::uint8_t*>(r.data.data()), r.data.size()});
    REQUIRE(m.ok);
    return std::move(m.model);
}

}  // namespace

TEST_SUITE("viewer") {
    TEST_CASE("the catalog lists every model of core by category") {
        const viewer::Catalog c = catalog_for();
        CHECK_FALSE(c.truncated);
        CHECK(c.missing.empty());
        std::size_t files = 0;
        for (const auto& e : std::filesystem::recursive_directory_iterator(kBuiltin / "core" / "models")) {
            files += e.is_regular_file() && e.path().extension() == ".glb";
        }
        CHECK(c.models.size() == files);
        // Every model is in exactly one group, and its group says so.
        std::size_t grouped = 0;
        for (std::size_t g = 0; g < c.groups.size(); ++g) {
            for (const std::size_t m : c.groups[g].models) {
                CHECK(c.models[m].group == g);
                ++grouped;
            }
        }
        CHECK(grouped == c.models.size());
        // Groups come by category.
        for (std::size_t g = 1; g < c.groups.size(); ++g) {
            CHECK(c.groups[g - 1].category <= c.groups[g].category);
        }
        const viewer::CatalogModel* house = c.find("core", "models/buildings/house.glb");
        REQUIRE(house != nullptr);
        CHECK(house->category == viewer::Category::Buildings);
        REQUIRE(house->uses.size() == 1);
        CHECK(house->uses[0].kind == "building");
        CHECK(house->uses[0].id == "core:house");
        CHECK(c.find("core", "models/animals/wolf.glb")->category == viewer::Category::Animals);
        CHECK(c.find("core", "models/characters/elf_female.glb")->category == viewer::Category::Characters);
        CHECK(c.find("core", "models/props/cloud.glb")->category == viewer::Category::Props);
    }

    TEST_CASE("variants are grouped: tree sizes, bodies and the code's hats") {
        const viewer::Catalog c = catalog_for();
        // A species' sizes, smallest first.
        const viewer::CatalogGroup* oak = group(c, "core:oak");
        REQUIRE(oak != nullptr);
        CHECK(oak->category == viewer::Category::Trees);
        REQUIRE(oak->models.size() == 3);
        CHECK(c.models[oak->models[0]].path == "models/props/tree_oak_small.glb");
        CHECK(c.models[oak->models[2]].path == "models/props/tree_oak_large.glb");
        // A race's two bodies.
        const viewer::CatalogGroup* human = group(c, "core:human");
        REQUIRE(human != nullptr);
        CHECK(human->models.size() == 2);
        // Models the code loads by name are used, grouped by their use.
        const viewer::CatalogGroup* hats = group(c, "code:hat");
        REQUIRE(hats != nullptr);
        CHECK(hats->models.size() == std::size(builtin_models::kHats));
        const viewer::CatalogGroup* cloud = group(c, "code:cloud");
        REQUIRE(cloud != nullptr);
        CHECK(cloud->models.size() == 1);
        for (const builtin_models::Use& use : builtin_models::kAll) {
            const viewer::CatalogModel* m = c.find("core", use.path);
            REQUIRE_MESSAGE(m != nullptr, use.path);
            CHECK(m->used());
        }
    }

    TEST_CASE("a mod's unused model and a definition's missing model are found") {
        const viewer::Catalog c = catalog_for("viewer_test");
        const viewer::CatalogModel* spare = c.find("viewer_test", "models/props/spare_rock.glb");
        REQUIRE(spare != nullptr);
        CHECK_FALSE(spare->used());
        CHECK(spare->category == viewer::Category::Props);
        // The mod is left out for its error, but its models still count.
        const viewer::CatalogModel* shed = c.find("viewer_test", "models/buildings/shed.glb");
        REQUIRE(shed != nullptr);
        CHECK(shed->used());
        REQUIRE(c.missing.size() == 1);
        CHECK(c.missing[0].def_id == "viewer_test:hut");
        CHECK(c.missing[0].mod == "viewer_test");
        CHECK(c.missing[0].path == "models/buildings/hut.glb");
        CHECK(c.unused_count() >= 1);
        // Core's models are not blamed for the mod.
        CHECK(c.find("core", "models/buildings/house.glb")->used());
    }

    TEST_CASE("the model card matches the test models") {
        const viewer::ModelStats tree = viewer::model_stats(load("test_tree.glb"));
        CHECK(tree.draw_calls == 2);
        CHECK(tree.materials == 2);  // The default one is not used.
        CHECK(tree.textures == 0);
        CHECK(tree.size.y == doctest::Approx(5.4f));
        CHECK_FALSE(tree.skinned);
        const render::ModelData house_data = load("test_house.glb");
        const viewer::ModelStats house = viewer::model_stats(house_data);
        CHECK(house.textures == 1);
        CHECK(house.largest_texture == 32);
        CHECK(house.vertices == house_data.vertices.size());
        CHECK(house.triangles * 3 == house_data.indices.size());
    }

    TEST_CASE("a body's card lists its skeleton and animations") {
        const fs::ReadResult r = fs::read_file(kBuiltin / "core" / "models" / "characters" / "human_male.glb", 16u << 20);
        REQUIRE(r.error == fs::IoError::None);
        const render::ModelLoadResult m =
            render::load_glb({reinterpret_cast<const std::uint8_t*>(r.data.data()), r.data.size()});
        REQUIRE(m.ok);
        const viewer::ModelStats s = viewer::model_stats(m.model);
        CHECK(s.skinned);
        CHECK(s.joints == 17);
        CHECK(std::find(s.clips.begin(), s.clips.end(), "walk") != s.clips.end());
    }
}
