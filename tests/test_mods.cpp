#include <doctest.h>

#include <algorithm>
#include <filesystem>
#include <string>

#include "core/json.h"
#include "mods/defs.h"
#include "mods/mod_library.h"
#include "mods/mod_manifest.h"
#include "mods/mod_settings.h"
#include "script/lua_sandbox.h"
#include "script/map_script.h"
#include "sim/worldgen.h"
#include "test_util.h"

extern "C" {
#include <lua.h>
}

using namespace sc;

namespace {

const std::filesystem::path kBuiltin = std::filesystem::path(SC_SOURCE_DIR) / "data" / "mods";

std::string manifest(std::string_view id, std::string_view extra = {}) {
    return std::string(R"({"schemaVersion": 1, "id": ")") + std::string(id) +
           R"(", "name": "mod.x", "version": "1.0.0", "gameVersion": ">=0.1.0")" + std::string(extra) + "}";
}

// A user mod folder with a manifest and optional files.
void make_mod(const test::TempDir& dir, std::string_view id, std::string_view extra = {},
              std::initializer_list<std::pair<const char*, std::string_view>> files = {}) {
    const std::filesystem::path root = dir.path() / std::string(id);
    std::filesystem::create_directories(root);
    test::write_text(root / "mod.json", manifest(id, extra));
    for (const auto& [name, content] : files) {
        std::filesystem::create_directories((root / name).parent_path());
        test::write_text(root / name, content);
    }
}

std::string all_errors(const mods::ModLibrary& lib) {
    std::string out;
    for (const mods::ModInfo& m : lib.mods()) {
        for (const std::string& e : m.errors) {
            out += m.manifest.id + ": " + e + "\n";
        }
    }
    return out;
}

mods::ModLibrary library_with(const test::TempDir& user, const std::vector<std::string>& enabled) {
    mods::ModLibrary lib;
    lib.scan(kBuiltin, user.path(), mods::Version{0, 7, 0});
    lib.select(enabled);
    return lib;
}

}  // namespace

TEST_SUITE("mods") {
    TEST_CASE("versions and ranges") {
        mods::Version v;
        CHECK(mods::parse_version("1.2.3", v));
        CHECK(v == mods::Version{1, 2, 3});
        CHECK_FALSE(mods::parse_version("1.2", v));
        CHECK_FALSE(mods::parse_version("1.2.x", v));
        CHECK_FALSE(mods::parse_version("-1.2.3", v));
        mods::VersionRange r;
        REQUIRE(mods::parse_range(">=0.7.0 <1.0.0", r));
        CHECK(r.contains({0, 7, 0}));
        CHECK(r.contains({0, 9, 9}));
        CHECK_FALSE(r.contains({1, 0, 0}));
        CHECK_FALSE(r.contains({0, 6, 9}));
        CHECK_FALSE(mods::parse_range("=1.0.0", r));
        CHECK(mods::is_valid_mod_id("my_mod2"));
        CHECK_FALSE(mods::is_valid_mod_id("My-Mod"));
        CHECK_FALSE(mods::is_valid_mod_id(""));
        CHECK(mods::is_valid_def_id("core:house"));
        CHECK_FALSE(mods::is_valid_def_id("house"));
        CHECK_FALSE(mods::is_valid_def_id("core:House"));
    }

    TEST_CASE("manifests are validated") {
        mods::ModManifest m;
        std::vector<std::string> errors;
        CHECK(mods::parse_manifest(manifest("abc", R"(, "dependencies": ["core"], "affectsSimulation": false)"), m, errors));
        CHECK(m.id == "abc");
        CHECK_FALSE(m.affects_simulation);
        CHECK(m.dependencies == std::vector<std::string>{"core"});
        errors.clear();
        CHECK_FALSE(mods::parse_manifest(R"({"schemaVersion": 1, "id": "Bad Id"})", m, errors));
        CHECK(errors.size() >= 3);
        errors.clear();
        CHECK_FALSE(mods::parse_manifest("{not json", m, errors));
    }

    TEST_CASE("mod files stay inside the mod") {
        const std::filesystem::path dir = "C:/mods/x";
        CHECK_FALSE(mods::mod_file(dir, "models/a.glb").empty());
        CHECK(mods::mod_file(dir, "../other/a.glb").empty());
        CHECK(mods::mod_file(dir, "models/../../a.glb").empty());
        CHECK(mods::mod_file(dir, "/etc/passwd").empty());
        CHECK(mods::mod_file(dir, "C:/Windows/a").empty());
        CHECK(mods::mod_file(dir, "models\\a.glb").empty());
        CHECK(mods::mod_file(dir, "").empty());
    }

    TEST_CASE("the base game loads without errors") {
        const mods::BuildResult& pack = test::core_pack();
        const sim::Content& c = pack.content;
        CHECK(pack.load_order == std::vector<std::string>{"core"});
        CHECK(c.resources.size() >= 5);
        CHECK(c.buildings.size() >= 5);
        CHECK(c.flora.species.size() == 21);
        CHECK(c.flora.biomes.size() == 6);
        CHECK(c.flora.map_types.size() == 6);
        CHECK(c.find_building("core:house") != sim::kNoDef);
        CHECK(c.feature(sim::FeatureKind::Stone) != nullptr);
        CHECK(c.hash != 0);
        mods::ModLibrary lib;
        lib.scan(kBuiltin, {}, mods::Version{0, 7, 0});
        lib.select({});
        (void)lib.build();
        CHECK_MESSAGE(all_errors(lib).empty(), all_errors(lib));
    }

    TEST_CASE("a mod adds, patches and removes definitions") {
        test::TempDir user;
        make_mod(user, "extra", "", {{"defs/a.json", R"({"schemaVersion": 1, "defs": [
            {"type": "resource", "id": "extra:gold", "name": "resource.gold", "category": "good"},
            {"type": "building", "patch": "core:house", "residents": 8},
            {"type": "building", "remove": "core:firewood_splitter"},
            {"type": "recipe", "remove": "core:split_firewood"}
        ]})"}});
        mods::ModLibrary lib = library_with(user, {"extra"});
        const mods::BuildResult r = lib.build();
        CHECK_MESSAGE(all_errors(lib).empty(), all_errors(lib));
        CHECK(r.load_order == std::vector<std::string>{"core", "extra"});
        CHECK(r.content.find_resource("extra:gold") != sim::kNoDef);
        const sim::DefIndex house = r.content.find_building("core:house");
        REQUIRE(house != sim::kNoDef);
        CHECK(r.content.buildings[house].residents == 8);
        CHECK(r.content.find_building("core:firewood_splitter") == sim::kNoDef);
        CHECK(r.content.hash != test::core_content().hash);
    }

    TEST_CASE("a mod with errors is switched off and the rest still load") {
        test::TempDir user;
        make_mod(user, "broken", "", {{"defs/a.json", R"({"schemaVersion": 1, "defs": [
            {"type": "resource", "id": "broken:x", "name": "r", "category": "nonsense"},
            {"type": "building", "id": "broken:hut", "name": "b", "kind": "house", "model": "../../evil.glb"}
        ]})"}});
        make_mod(user, "fine", "", {{"defs/a.json", R"({"schemaVersion": 1, "defs": [
            {"type": "resource", "id": "fine:salt", "name": "r", "category": "good"}]})"}});
        make_mod(user, "needy", R"(, "dependencies": ["broken"])");
        mods::ModLibrary lib = library_with(user, {"broken", "fine", "needy"});
        const mods::BuildResult r = lib.build();
        CHECK(r.load_order == std::vector<std::string>{"core", "fine"});
        CHECK(r.content.find_resource("fine:salt") != sim::kNoDef);
        CHECK(r.content.find_resource("broken:x") == sim::kNoDef);
        const mods::ModInfo* broken = lib.find("broken");
        REQUIRE(broken != nullptr);
        CHECK_FALSE(broken->loaded);
        CHECK(broken->errors.size() >= 2);
        const mods::ModInfo* needy = lib.find("needy");
        REQUIRE(needy != nullptr);
        CHECK_FALSE(needy->loaded);
        CHECK_FALSE(needy->errors.empty());
    }

    TEST_CASE("load order follows dependencies and rejects cycles") {
        test::TempDir user;
        make_mod(user, "a", R"(, "loadAfter": ["b"])");
        make_mod(user, "b");
        make_mod(user, "c", R"(, "loadAfter": ["d"])");
        make_mod(user, "d", R"(, "loadAfter": ["c"])");
        mods::ModLibrary lib = library_with(user, {"a", "b", "c", "d"});
        const mods::BuildResult r = lib.build();
        CHECK(r.load_order == std::vector<std::string>{"core", "b", "a"});
        CHECK_FALSE(lib.find("c")->errors.empty());
        CHECK_FALSE(lib.find("d")->errors.empty());
    }

    TEST_CASE("wrong game versions and duplicate ids are rejected") {
        test::TempDir user;
        const std::filesystem::path root = user.path() / "future";
        std::filesystem::create_directories(root);
        test::write_text(root / "mod.json", R"({"schemaVersion": 1, "id": "future", "name": "m", "version": "1.0.0", "gameVersion": ">=9.0.0"})");
        make_mod(user, "core");
        mods::ModLibrary lib = library_with(user, {"future"});
        (void)lib.build();
        CHECK_FALSE(lib.find("future")->errors.empty());
        CHECK_FALSE(lib.find("future")->loaded);
        // The user's "core" does not replace the built-in one.
        CHECK(lib.find("core")->builtin);
    }

    TEST_CASE("the choice of mods is saved and read back") {
        test::TempDir dir;
        const std::filesystem::path file = dir / "mods.json";
        CHECK(mods::load_selection(file).enabled.empty());
        REQUIRE(mods::save_selection(file, {{"b", "a"}}));
        CHECK(mods::load_selection(file).enabled == std::vector<std::string>{"b", "a"});
        test::write_text(file, "{broken");
        CHECK(mods::load_selection(file).enabled.empty());
        CHECK(dir.count_entries() == 1);  // Quarantined, not deleted.
    }
}

TEST_SUITE("mods") {
    TEST_CASE("the example mod loads and its map rule runs") {
        mods::ModLibrary lib;
        lib.scan(kBuiltin, std::filesystem::path(SC_SOURCE_DIR) / "tools", mods::Version{0, 7, 0});
        lib.select({"example"});
        const mods::BuildResult pack = lib.build();
        CHECK_MESSAGE(all_errors(lib).empty(), all_errors(lib));
        REQUIRE(pack.load_order == std::vector<std::string>{"core", "example"});
        const sim::DefIndex shrine = pack.content.find_building("example:shrine");
        REQUIRE(shrine != sim::kNoDef);
        CHECK(pack.content.buildings[shrine].desirability == 10);
        CHECK(pack.content.buildings[pack.content.find_building("core:storehouse")].storage == 800);
        CHECK(pack.content.find_resource("example:amber") != sim::kNoDef);
        CHECK(pack.language_files.size() == 4);  // core and example, en and es.
        sim::MapSettings s;
        s.seed = 5;
        s.size = sim::MapSize::Small;
        s.players = 2;
        script::MapScripts scripts(pack.scripts, pack.content);
        const auto with = sim::generate_map(s, pack.content, {}, &scripts);
        const auto without = sim::generate_map(s, pack.content);
        REQUIRE(with.has_value());
        CHECK(scripts.errors().empty());
        std::size_t extra_stones = 0;
        for (const sim::MapFeature& f : with->features) {
            extra_stones += f.type == sim::FeatureType::Stone;
        }
        for (const sim::MapFeature& f : without->features) {
            extra_stones -= f.type == sim::FeatureType::Stone;
        }
        CHECK(extra_stones > 12);  // Two circles of 12, minus any in water.
    }

    TEST_CASE("every mod language file has the same keys in each language") {
        for (const std::filesystem::path& dir : {kBuiltin / "core", std::filesystem::path(SC_SOURCE_DIR) / "tools" / "example_mod"}) {
            const auto keys = [&](const char* code) {
                json::ParseResult p = json::parse_object(test::read_text(dir / "lang" / (std::string(code) + ".json")));
                REQUIRE(p.error == json::ParseError::None);
                std::vector<std::string> out;
                yyjson_mut_val* strings = yyjson_mut_obj_get(yyjson_mut_doc_get_root(p.doc.get()), "strings");
                std::size_t i = 0, max = 0;
                yyjson_mut_val* k = nullptr;
                yyjson_mut_val* v = nullptr;
                yyjson_mut_obj_foreach(strings, i, max, k, v) {
                    out.emplace_back(yyjson_mut_get_str(k));
                }
                std::sort(out.begin(), out.end());
                return out;
            };
            CHECK(keys("en") == keys("es"));
        }
    }
}

TEST_SUITE("lua") {
    TEST_CASE("the sandbox has no files, no os and integer math") {
        script::LuaSandbox box;
        std::string error;
        REQUIRE(box.open("t", {}, R"(
            function check()
                assert(io == nil and os == nil and debug == nil and package == nil)
                assert(load == nil and loadfile == nil and dofile == nil)
                assert(math.isqrt(49) == 7 and math.abs(-3) == 3 and math.max(1, 5, 2) == 5)
                assert(math.sin_deg(90) == 10000 and math.cos_deg(0) == 10000)
                assert(math.random == nil and math.floor == nil)
                return 42
            end)", error));
        REQUIRE(box.call("check", 0, 1, error));
        CHECK(lua_tointeger(box.state(), -1) == 42);
    }

    TEST_CASE("endless loops and memory bombs are stopped") {
        script::LuaSandbox box;
        std::string error;
        script::SandboxLimits limits;
        limits.instructions_per_call = 100000;
        limits.memory_bytes = 4u * 1024u * 1024u;
        REQUIRE(box.open("t", {}, "function spin() while true do end end\n"
                                  "function eat() local t = {} for i = 1, 100000000 do t[i] = string.rep('x', 100) .. i end end",
                         error, limits));
        CHECK_FALSE(box.call("spin", 0, 0, error));
        CHECK(error.find("instruction limit") != std::string::npos);
        CHECK_FALSE(box.call("eat", 0, 0, error));
        // The state still works afterwards.
        REQUIRE(box.open("t2", {}, "function ok() return 1 end", error, limits));
        CHECK(box.call("ok", 0, 1, error));
    }

    TEST_CASE("syntax errors and require outside the mod fail cleanly") {
        script::LuaSandbox box;
        std::string error;
        CHECK_FALSE(box.open("t", {}, "function (", error));
        CHECK_FALSE(error.empty());
        script::LuaSandbox box2;
        REQUIRE(box2.open("t", {}, "function f() return require('../../secret') end", error));
        CHECK_FALSE(box2.call("f", 0, 1, error));
        CHECK(script::is_valid_module_name("utils.stones"));
        CHECK_FALSE(script::is_valid_module_name("../x"));
        CHECK_FALSE(script::is_valid_module_name("a..b"));
    }

    TEST_CASE("a map rule adds features the same way every time") {
        test::TempDir user;
        make_mod(user, "circle", "", {{"scripts/main.lua", R"(
            function on_map_generated(map)
                local s = map.starts[1]
                for i = 0, 11 do
                    local a = i * 30
                    map.add_feature("stone", s.x + math.cos_deg(a) * 60 // 100, s.z + math.sin_deg(a) * 60 // 100)
                end
                map.add_tree("core:sequoia", "huge", s.x + 9000, s.z)
                -- Too close to the start: refused.
                assert(map.add_feature("stone", s.x, s.z) == false)
            end)"}});
        mods::ModLibrary lib = library_with(user, {"circle"});
        const mods::BuildResult pack = lib.build();
        REQUIRE(pack.scripts.size() == 1);
        sim::MapSettings s;
        s.seed = 99;
        s.size = sim::MapSize::Small;
        const auto run = [&] {
            script::MapScripts scripts(pack.scripts, pack.content);
            auto m = sim::generate_map(s, pack.content, {}, &scripts);
            CHECK(scripts.errors().empty());
            return m;
        };
        const auto plain = sim::generate_map(s, pack.content);
        const auto a = run();
        const auto b = run();
        REQUIRE(plain.has_value());
        REQUIRE(a.has_value());
        REQUIRE(b.has_value());
        CHECK(a->checksum() == b->checksum());
        CHECK(a->features.size() > plain->features.size());
        CHECK(a->features.size() <= plain->features.size() + 13);
    }

    TEST_CASE("a failing map rule is skipped and reported") {
        test::TempDir user;
        make_mod(user, "oops", "", {{"scripts/main.lua", "function on_map_generated(map) error('boom') end"}});
        mods::ModLibrary lib = library_with(user, {"oops"});
        const mods::BuildResult pack = lib.build();
        sim::MapSettings s;
        s.size = sim::MapSize::Small;
        script::MapScripts scripts(pack.scripts, pack.content);
        const auto m = sim::generate_map(s, pack.content, {}, &scripts);
        CHECK(m.has_value());
        REQUIRE(scripts.errors().size() == 1);
        CHECK(scripts.errors()[0].find("boom") != std::string::npos);
    }
}
