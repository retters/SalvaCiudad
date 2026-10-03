#include <doctest.h>

#include <algorithm>
#include <filesystem>
#include <set>
#include <string>

#include "core/file_io.h"
#include "game/builtin_models.h"
#include "game/people.h"
#include "render/model.h"
#include "sim/worldgen.h"
#include "test_util.h"

using namespace sc;

namespace {

const std::filesystem::path kCore = std::filesystem::path(SC_SOURCE_DIR) / "data" / "mods" / "core";

render::ModelData load(const std::string& rel) {
    const fs::ReadResult r = fs::read_file(kCore / rel, 16u << 20);
    REQUIRE_MESSAGE(r.error == fs::IoError::None, rel);
    render::ModelLoadResult m = render::load_glb({reinterpret_cast<const std::uint8_t*>(r.data.data()), r.data.size()});
    REQUIRE_MESSAGE(m.ok, rel << ": " << m.error);
    return std::move(m.model);
}

// A body with round numbers: every clip a second long but the cast.
people::Body test_body() {
    people::Body b;
    for (std::size_t a = 0; a < people::kActs; ++a) {
        b.clip[a] = static_cast<std::uint32_t>(a);
        b.length[a] = 1.0f;
    }
    b.length[static_cast<std::size_t>(people::Act::FishCast)] = 0.5f;
    b.tools[static_cast<std::size_t>(people::Act::Chop)] = 1u;
    b.walk_speed = 1.5f;
    b.run_speed = 3.0f;
    return b;
}

render::ModelMaterial material(const char* name, float r, float g, float b) {
    render::ModelMaterial m;
    m.name = name;
    m.base_color[0] = r;
    m.base_color[1] = g;
    m.base_color[2] = b;
    return m;
}

}  // namespace

TEST_SUITE("people") {
    TEST_CASE("the stride follows the ground covered") {
        const people::Body body = test_body();
        people::Motion m;
        // At the clip's own speed, a second of game is a second of clip.
        people::advance(body, m, people::Act::Walk, 1.5f, 0.25f, 0.25f);
        CHECK(m.act == people::Act::Walk);
        CHECK(m.time == doctest::Approx(0.25f));
        // Slower on the ground, slower in the clip; and it loops.
        people::advance(body, m, people::Act::Walk, 0.75f, 0.5f, 0.5f);
        CHECK(m.time == doctest::Approx(0.5f));
        people::advance(body, m, people::Act::Walk, 1.5f, 0.75f, 0.75f);
        CHECK(m.time == doctest::Approx(0.25f));
        // Well over the walk's speed it runs, at the same point of the stride.
        people::advance(body, m, people::Act::Walk, 3.0f, 0.0f, 0.0f);
        CHECK(m.act == people::Act::Run);
        CHECK(m.time == doctest::Approx(0.25f));
        // Asked to run (fleeing), it runs whatever its speed, slowly if slow.
        people::Motion fleeing;
        people::advance(body, fleeing, people::Act::Run, 1.5f, 0.5f, 0.5f);
        CHECK(fleeing.act == people::Act::Run);
        CHECK(fleeing.time == doctest::Approx(0.25f));
        // A paused game stops the legs.
        people::advance(body, fleeing, people::Act::Run, 1.5f, 0.0f, 0.0f);
        CHECK(fleeing.time == doctest::Approx(0.25f));
    }

    TEST_CASE("work clips start over, play at their own rate and show their tool") {
        const people::Body body = test_body();
        people::Motion m;
        m.time = 0.7f;
        people::advance(body, m, people::Act::Chop, 0.0f, 3.0f * 0.1f, 0.1f);  // Triple speed: still real time.
        CHECK(m.act == people::Act::Chop);
        CHECK(m.time == doctest::Approx(0.1f));
        render::CharacterInstance c;
        people::pose(body, m, c);
        CHECK(c.clip == static_cast<std::uint32_t>(people::Act::Chop));
        CHECK(c.accessories == 1u);
        CHECK(c.time == doctest::Approx(0.1f));
        people::advance(body, m, people::Act::Idle, 0.0f, 0.1f, 0.1f);
        people::pose(body, m, c);
        CHECK(c.accessories == 0u);  // The axe is gone with the clip.
    }

    TEST_CASE("fishing starts with the cast, once") {
        const people::Body body = test_body();
        people::Motion m;
        people::advance(body, m, people::Act::Fish, 0.0f, 0.1f, 0.1f);
        CHECK(m.act == people::Act::FishCast);
        CHECK(m.time == 0.0f);
        people::advance(body, m, people::Act::Fish, 0.0f, 0.3f, 0.3f);
        CHECK(m.act == people::Act::FishCast);
        people::advance(body, m, people::Act::Fish, 0.0f, 0.3f, 0.3f);
        CHECK(m.act == people::Act::Fish);
        for (int i = 0; i < 30; ++i) {
            people::advance(body, m, people::Act::Fish, 0.0f, 0.3f, 0.3f);
            CHECK(m.act == people::Act::Fish);  // It does not cast again.
        }
    }

    TEST_CASE("children are the adult's body, smaller") {
        CHECK(people::scale_of(0, 0) == doctest::Approx(0.55f));
        CHECK(people::scale_of(2, 0) < people::scale_of(4, 0));
        CHECK(people::scale_of(4, 0) < people::scale_of(sim::village::kAdultAgeYears, 0));
        // Adults differ a little in height.
        std::set<int> heights;
        for (std::uint32_t bits = 0; bits < 200; ++bits) {
            const float s = people::scale_of(30, bits);
            CHECK(s >= 0.94f);
            CHECK(s <= 1.06f);
            heights.insert(static_cast<int>(s * 1000.0f));
        }
        CHECK(heights.size() > 5);
    }

    TEST_CASE("a material is recolored by the slot its name starts with") {
        render::ModelData m;
        m.materials = {material("skin_light", 0.8f, 0.4f, 0.2f), material("skin", 0.5f, 0.25f, 0.125f),
                       material("top_shade", 0.1f, 0.2f, 0.3f), material("topaz", 1, 1, 1), material("eye", 0, 0, 0)};
        math::Vec3 color;
        REQUIRE(render::palette_reference(m, people::kSkinSlot, color));
        CHECK(color.x == doctest::Approx(0.5f));  // The one named as the slot, not the first.
        REQUIRE(render::palette_reference(m, people::kTopSlot, color));
        CHECK(color.z == doctest::Approx(0.3f));  // Without one, the first of the slot; "topaz" is not it.
        CHECK_FALSE(render::palette_reference(m, people::kHairSlot, color));
        CHECK_FALSE(render::palette_reference(m, people::kBottomSlot, color));
    }

    TEST_CASE("palettes: the model's own colors first, then every skin, hair and outfit") {
        render::ModelData m;
        m.materials = {material("skin", 0.5f, 0.25f, 0.125f), material("top", 0.1f, 0.2f, 0.3f)};
        const std::uint32_t skins[] = {0xFFFFFF, 0x000000};
        const std::uint32_t hairs[] = {0xFF0000};
        std::uint32_t s = 0, h = 0, o = 0;
        const std::vector<render::Palette> p = people::make_palettes(m, skins, hairs, s, h, o);
        CHECK(s == 3);  // Its own and the two given.
        CHECK(h == 1);  // It has no hair to recolor.
        CHECK(o > 3);
        REQUIRE(p.size() == static_cast<std::size_t>(s) * h * o);
        // The first is the model as it was made.
        CHECK(p[0].colors[people::kSkinSlot].x == doctest::Approx(0.5f));
        CHECK(p[0].colors[people::kTopSlot].z == doctest::Approx(0.3f));
        // Then the outfits of the same skin, then the next skin.
        CHECK(p[1].colors[people::kSkinSlot].x == doctest::Approx(0.5f));
        CHECK(p[1].colors[people::kTopSlot].z != doctest::Approx(0.3f));
        CHECK(p[o].colors[people::kSkinSlot].x == doctest::Approx(1.0f));
        CHECK(p[2 * o].colors[people::kSkinSlot].x == doctest::Approx(0.0f));
        // A body's palette index stays inside its own.
        people::Body body;
        body.first_palette = 100;
        body.skins = s;
        body.hairs = h;
        body.outfits = o;
        std::set<std::uint32_t> seen;
        for (std::uint32_t bits = 0; bits < 5000; ++bits) {
            const std::uint32_t index = people::Cast::palette(body, bits * 7919u);
            CHECK(index >= 100);
            CHECK(index < 100 + body.palette_count());
            seen.insert(index);
        }
        CHECK(seen.size() == body.palette_count());  // And all of them come up.
        // A model with nothing to recolor has one palette.
        render::ModelData plain;
        plain.materials = {material("fur", 1, 1, 1)};
        CHECK(people::make_palettes(plain, skins, hairs, s, h, o).size() == 1);
    }

    TEST_CASE("every character of every people has its clips and known tools") {
        const sim::Content& content = sc::test::core_content();
        std::set<std::string> names;
        for (const sim::RaceDef& race : content.races) {
            names.insert(race.bodies_male.begin(), race.bodies_male.end());
            names.insert(race.bodies_female.begin(), race.bodies_female.end());
        }
        CHECK(names.size() == 17);
        for (const std::string& name : names) {
            CAPTURE(name);
            const render::ModelData m = load(sim::race_body_file(name));
            CHECK(m.skinned());
            CHECK(m.bounds_max.y > 1.0f);
            CHECK(m.bounds_max.y < 2.6f);
            for (const std::string_view clip : people::kActClips) {
                const int i = m.clip_index(clip);
                REQUIRE_MESSAGE(i >= 0, clip);
                const std::string& prop = m.clips[static_cast<std::size_t>(i)].prop;
                if (prop.empty()) {
                    continue;
                }
                // "kind:bone": a tool the game has, in a bone the model has.
                const std::size_t colon = prop.find(':');
                REQUIRE(colon != std::string::npos);
                const std::string kind = prop.substr(0, colon);
                CHECK(std::any_of(std::begin(builtin_models::kTools), std::end(builtin_models::kTools),
                                  [&](const builtin_models::Tool& t) { return t.kind == kind; }));
                const int joint = m.joint_index(prop.substr(colon + 1));
                REQUIRE(joint >= 0);
                CHECK(m.joint_length[static_cast<std::size_t>(joint)] > 0.0f);
            }
            // Something of it can be recolored, or it is the same for everybody.
            math::Vec3 color;
            const bool any = render::palette_reference(m, people::kSkinSlot, color) ||
                             render::palette_reference(m, people::kTopSlot, color);
            CHECK(any);
        }
        for (const builtin_models::Tool& tool : builtin_models::kTools) {
            const render::ModelData m = load(std::string(tool.path));
            CHECK_FALSE(m.skinned());
            CHECK(math::length(m.grip) > 0.05f);  // Held by its handle, not by its end.
        }
    }

    TEST_CASE("what a villager does shows: it hurries when fleeing, chops trees, hammers at work") {
        const sim::Content& content = sc::test::core_content();
        sim::MapSettings s;
        s.seed = 7;
        s.size = sim::MapSize::Small;
        auto map = sim::generate_map(s, content);
        REQUIRE(map.has_value());
        sim::GameSetup setup;
        setup.seed = 3;
        const sim::Game game(std::shared_ptr<const sim::Content>(std::shared_ptr<const sim::Content>{}, &content), *map, setup);
        REQUIRE(game.villagers().size() > 0);
        sim::Villager v = game.villagers().data()[0];
        const auto act = [&](sim::Task task, bool moving) {
            v.task = task;
            return people::act_of(game, v, moving);
        };
        CHECK(act(sim::Task::Idle, false) == people::Act::Idle);
        CHECK(act(sim::Task::Wander, true) == people::Act::Walk);
        CHECK(act(sim::Task::GoGather, true) == people::Act::Walk);
        CHECK(act(sim::Task::Flee, true) == people::Act::Run);
        CHECK(act(sim::Task::GoFire, true) == people::Act::Run);
        CHECK(act(sim::Task::Build, false) == people::Act::Work);
        CHECK(act(sim::Task::Produce, false) == people::Act::Work);
        CHECK(act(sim::Task::Farm, false) == people::Act::Work);
        CHECK(act(sim::Task::Hunt, false) == people::Act::Shoot);
        CHECK(act(sim::Task::Fish, false) == people::Act::Fish);
        CHECK(act(sim::Task::GoBuild, false) == people::Act::Idle);  // Waiting on the way.
        // Gathering: an axe for a tree, the hammer for the rest.
        const auto& features = game.map().features;
        const auto tree = std::find_if(features.begin(), features.end(),
                                       [](const sim::MapFeature& f) { return f.type == sim::FeatureType::Tree; });
        const auto stone = std::find_if(features.begin(), features.end(),
                                        [](const sim::MapFeature& f) { return f.type == sim::FeatureType::Stone; });
        REQUIRE(tree != features.end());
        REQUIRE(stone != features.end());
        v.node = static_cast<std::uint32_t>(tree - features.begin()) + 1;
        CHECK(act(sim::Task::Gather, false) == people::Act::Chop);
        v.node = static_cast<std::uint32_t>(stone - features.begin()) + 1;
        CHECK(act(sim::Task::Gather, false) == people::Act::Work);
    }
}
