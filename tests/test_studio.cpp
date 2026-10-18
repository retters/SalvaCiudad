// Phase 120: the keys of the thumbnails and portraits the game renders for
// the interface (the rendering itself needs a GPU and is checked by hand).
#include <doctest.h>

#include <filesystem>
#include <memory>
#include <optional>

#include "game/game_session.h"
#include "game/model_studio.h"
#include "game/save_file.h"
#include "mods/mod_library.h"
#include "sim/worldgen.h"
#include "test_util.h"

using namespace sc;

namespace {

std::shared_ptr<const sim::Content> content() {
    return std::shared_ptr<const sim::Content>(std::shared_ptr<const sim::Content>{}, &sc::test::core_content());
}

}  // namespace

TEST_SUITE("studio") {
    TEST_CASE("thumbnail keys are parsed strictly") {
        const auto b = parse_thumb_key("thumbs/building/core/stonecutter");
        REQUIRE(b.has_value());
        CHECK(b->kind == ThumbKey::Kind::Model);
        CHECK(b->def_type == "building");
        CHECK(b->def_id == "core:stonecutter");
        CHECK(thumb_key("building", "core:stonecutter") == "building/core/stonecutter");
        const auto p = parse_thumb_key("person/core/dark_elf/f/21");
        REQUIRE(p.has_value());
        CHECK(p->kind == ThumbKey::Kind::Person);
        CHECK(p->def_id == "core:dark_elf");
        CHECK(p->female);
        CHECK(p->appearance == 21);
        for (const char* bad : {"", "building/core", "building/core/../x", "house/core/x", "building/Core/x",
                                "person/core/elf/x/1", "person/core/elf/f/", "person/core/elf/f/99999999999",
                                "building/core/stonecutter/extra", "thumbs/person/core/elf/m/1a"}) {
            CHECK_MESSAGE(!parse_thumb_key(bad).has_value(), bad);
        }
    }

    TEST_CASE("a villager's portrait is the same after saving and loading") {
        sim::GameSetup setup;
        setup.seed = 5;
        sim::MapSettings s;
        s.size = sim::MapSize::Small;
        s.seed = 31;
        std::optional<sim::MapData> map = sim::generate_map(s, *content());
        REQUIRE(map.has_value());
        GameSession session(content(), std::move(*map), setup);
        for (int i = 0; i < 50; ++i) {
            session.step();
        }
        mods::ModLibrary none;
        save::SaveData back;
        REQUIRE(save::decode(save::encode(session.make_save("test", none)), back) == save::LoadError::None);
        std::unique_ptr<GameSession> loaded;
        REQUIRE(GameSession::load(back, content(), loaded) == GameSession::LoadResult::Ok);
        const auto& before = session.game().villagers().data();
        const auto& after = loaded->game().villagers().data();
        REQUIRE(before.size() == after.size());
        REQUIRE_FALSE(before.empty());
        for (std::size_t i = 0; i < before.size(); ++i) {
            const std::string key = portrait_key(*content(), before[i]);
            CHECK(key.starts_with("person/core/"));
            CHECK(parse_thumb_key(key).has_value());
            CHECK(key == portrait_key(*content(), after[i]));
        }
    }

    TEST_CASE("a mod's new building has a model to draw its thumbnail from") {
        mods::ModLibrary lib;
        lib.scan(std::filesystem::path(SC_SOURCE_DIR) / "data" / "mods", std::filesystem::path(SC_SOURCE_DIR) / "tools",
                 mods::Version{0, 20, 0});
        lib.select({"example"});
        const mods::BuildResult pack = lib.build();
        const auto shrine = thumb_model_file(pack, "building", "example:shrine");
        REQUIRE(shrine.has_value());
        CHECK(shrine->filename() == "shrine.glb");
        CHECK(std::filesystem::is_regular_file(*shrine));
        CHECK(thumb_model_file(pack, "building", "core:stonecutter").has_value());
        CHECK_FALSE(thumb_model_file(pack, "building", "example:nothing").has_value());
    }
}
