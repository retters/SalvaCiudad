#include <doctest.h>

#include <algorithm>
#include <cstring>
#include <ostream>

#include "core/file_io.h"
#include "render/model.h"
#include "test_util.h"

using namespace sc;
using namespace sc::render;

namespace {

const std::filesystem::path kModels = std::filesystem::path(SC_SOURCE_DIR) / "tests" / "data_models_test";

ModelLoadResult load_file(std::string_view name) {
    const auto r = fs::read_file(kModels / name, model_limits::kMaxFileBytes);
    REQUIRE(r.error == fs::IoError::None);
    return load_glb({reinterpret_cast<const std::uint8_t*>(r.data.data()), r.data.size()});
}

void put_u32(std::vector<std::uint8_t>& out, std::uint32_t v) {
    for (int i = 0; i < 4; ++i) {
        out.push_back(static_cast<std::uint8_t>(v >> (8 * i)));
    }
}

// Builds a .glb from a JSON text and an optional binary chunk.
std::vector<std::uint8_t> make_glb(std::string json, const std::vector<std::uint8_t>& bin) {
    while (json.size() % 4 != 0) {
        json += ' ';
    }
    std::vector<std::uint8_t> padded_bin = bin;
    while (padded_bin.size() % 4 != 0) {
        padded_bin.push_back(0);
    }
    std::vector<std::uint8_t> out;
    const std::size_t total = 12 + 8 + json.size() + (padded_bin.empty() ? 0 : 8 + padded_bin.size());
    put_u32(out, 0x46546C67);
    put_u32(out, 2);
    put_u32(out, static_cast<std::uint32_t>(total));
    put_u32(out, static_cast<std::uint32_t>(json.size()));
    put_u32(out, 0x4E4F534A);
    out.insert(out.end(), json.begin(), json.end());
    if (!padded_bin.empty()) {
        put_u32(out, static_cast<std::uint32_t>(padded_bin.size()));
        put_u32(out, 0x004E4942);
        out.insert(out.end(), padded_bin.begin(), padded_bin.end());
    }
    return out;
}

// One triangle (3 positions) plus 3 uint16 indices.
std::vector<std::uint8_t> triangle_bin(std::uint16_t i0, std::uint16_t i1, std::uint16_t i2) {
    const float pos[9] = {0, 0, 0, 1, 0, 0, 0, 0, 1};
    std::vector<std::uint8_t> bin(sizeof(pos));
    std::memcpy(bin.data(), pos, sizeof(pos));
    for (const std::uint16_t i : {i0, i1, i2}) {
        bin.push_back(static_cast<std::uint8_t>(i));
        bin.push_back(static_cast<std::uint8_t>(i >> 8));
    }
    return bin;
}

std::string triangle_json(const char* buffer_extra = "") {
    return std::string(R"({"asset":{"version":"2.0"},"scene":0,"scenes":[{"nodes":[0]}],"nodes":[{"mesh":0}],
        "meshes":[{"primitives":[{"attributes":{"POSITION":0},"indices":1}]}],
        "accessors":[{"bufferView":0,"componentType":5126,"count":3,"type":"VEC3","min":[0,0,0],"max":[1,0,1]},
                     {"bufferView":1,"componentType":5123,"count":3,"type":"SCALAR"}],
        "bufferViews":[{"buffer":0,"byteOffset":0,"byteLength":36},{"buffer":0,"byteOffset":36,"byteLength":6}],
        "buffers":[{"byteLength":42)") + buffer_extra + "}]}";
}

}  // namespace

TEST_SUITE("model") {
    TEST_CASE("the test models load with their materials") {
        const ModelLoadResult tree = load_file("test_tree.glb");
        REQUIRE(tree.ok);
        CHECK(tree.model.primitives.size() == 2);
        CHECK(tree.model.materials.size() == 3);  // Two plus the default.
        CHECK(tree.model.indices.size() % 3 == 0);
        CHECK(tree.model.bounds_max.y == doctest::Approx(5.4f));
        CHECK(tree.model.radius > 5.0f);

        const ModelLoadResult house = load_file("test_house.glb");
        REQUIRE(house.ok);
        REQUIRE(house.model.textures.size() == 1);
        CHECK(house.model.textures[0].width == 32);
        CHECK(house.model.textures[0].rgba.size() == 32u * 32u * 4u);
        CHECK(house.model.materials[0].texture == 0);

        const ModelLoadResult rock = load_file("test_rock.glb");
        REQUIRE(rock.ok);
        for (const ModelVertex& v : rock.model.vertices) {
            CHECK(std::abs(v.nx * v.nx + v.ny * v.ny + v.nz * v.nz - 1.0f) < 1e-3f);
        }
    }

    TEST_CASE("a minimal triangle loads and gets computed normals") {
        const auto glb = make_glb(triangle_json(), triangle_bin(0, 1, 2));
        const ModelLoadResult r = load_glb(glb);
        REQUIRE(r.ok);
        CHECK(r.model.vertices.size() == 3);
        // Counter-clockwise seen from below: (1,0,0) x (0,0,1) points down.
        CHECK(r.model.vertices[0].ny == doctest::Approx(-1.0f));
    }

    TEST_CASE("broken and hostile files are rejected") {
        CHECK_FALSE(load_glb({}).ok);
        const std::vector<std::uint8_t> garbage(1000, 0x5A);
        CHECK_FALSE(load_glb(garbage).ok);

        auto glb = make_glb(triangle_json(), triangle_bin(0, 1, 2));
        glb.resize(glb.size() - 10);  // Truncated.
        CHECK_FALSE(load_glb(glb).ok);

        // An index past the last vertex.
        CHECK_FALSE(load_glb(make_glb(triangle_json(), triangle_bin(0, 1, 7))).ok);

        // External files are never read.
        const auto external = make_glb(triangle_json(R"(,"uri":"C:/Windows/win.ini")"), {});
        CHECK_FALSE(load_glb(external).ok);

        // No binary chunk at all.
        CHECK_FALSE(load_glb(make_glb(triangle_json(), {})).ok);
    }
}

namespace {

const std::filesystem::path kData = std::filesystem::path(SC_SOURCE_DIR) / "data" / "mods" / "core" / "models";

ModelLoadResult load_data(std::string_view name) {
    const auto r = fs::read_file(kData / name, model_limits::kMaxFileBytes);
    REQUIRE(r.error == fs::IoError::None);
    return load_glb({reinterpret_cast<const std::uint8_t*>(r.data.data()), r.data.size()});
}

// A triangle skinned to a one-joint skeleton, with one joint index `bad`.
std::vector<std::uint8_t> skinned_triangle(std::uint8_t bad) {
    std::vector<std::uint8_t> bin = triangle_bin(0, 1, 2);  // 36 bytes of positions, 6 of indices.
    bin.push_back(0);
    bin.push_back(0);  // Align to 44.
    for (int v = 0; v < 3; ++v) {
        bin.insert(bin.end(), {static_cast<std::uint8_t>(v == 2 ? bad : 0), 0, 0, 0});
    }
    const float w[4] = {1, 0, 0, 0};
    for (int v = 0; v < 3; ++v) {
        const auto* b = reinterpret_cast<const std::uint8_t*>(w);
        bin.insert(bin.end(), b, b + sizeof(w));
    }
    return bin;
}

const char* kSkinnedJson = R"({"asset":{"version":"2.0"},"scene":0,"scenes":[{"nodes":[0,1]}],
    "nodes":[{"mesh":0,"skin":0},{"name":"root"}],
    "skins":[{"joints":[1]}],
    "meshes":[{"primitives":[{"attributes":{"POSITION":0,"JOINTS_0":2,"WEIGHTS_0":3},"indices":1}]}],
    "accessors":[{"bufferView":0,"componentType":5126,"count":3,"type":"VEC3","min":[0,0,0],"max":[1,0,1]},
                 {"bufferView":1,"componentType":5123,"count":3,"type":"SCALAR"},
                 {"bufferView":2,"componentType":5121,"count":3,"type":"VEC4"},
                 {"bufferView":3,"componentType":5126,"count":3,"type":"VEC4"}],
    "bufferViews":[{"buffer":0,"byteOffset":0,"byteLength":36},{"buffer":0,"byteOffset":36,"byteLength":6},
                   {"buffer":0,"byteOffset":44,"byteLength":12},{"buffer":0,"byteOffset":56,"byteLength":48}],
    "buffers":[{"byteLength":104}]})";

}  // namespace

TEST_SUITE("model") {
    TEST_CASE("the characters have a skeleton, baked animations and what the game reads from them") {
        for (const char* file : {"characters/adventurer_man.glb", "characters/dwarf_woman.glb", "characters/orc.glb"}) {
            const ModelLoadResult r = load_data(file);
            REQUIRE_MESSAGE(r.ok, file << ": " << r.error);
            const ModelData& m = r.model;
            CHECK(m.skinned());
            CHECK(m.joint_names.size() >= 17);
            CHECK(m.skin.size() == m.vertices.size());
            for (const JointWeights& jw : m.skin) {
                CHECK(jw.weights[0] + jw.weights[1] + jw.weights[2] + jw.weights[3] == 255);
                for (const std::uint8_t j : jw.joints) {
                    CHECK(j < m.joint_names.size());
                }
            }
            const auto clip = [&](const char* name) -> const ModelClip& {
                const int i = m.clip_index(name);
                REQUIRE_MESSAGE(i >= 0, name);
                return m.clips[static_cast<std::size_t>(i)];
            };
            CHECK(clip("idle").frame_count == 90);
            CHECK(clip("walk").frame_count == 16);
            for (const ModelClip& c : m.clips) {
                CHECK(c.skin.size() == static_cast<std::size_t>(c.frame_count) * m.joint_names.size());
            }
            // Walking and running say how fast, so the feet do not slide.
            CHECK(clip("walk").speed > 0.5f);
            CHECK(clip("run").speed > clip("walk").speed);
            CHECK(clip("idle").speed == 0.0f);
            // The tools: which one and in which hand; the cast plays once.
            CHECK(clip("chop").prop == "axe:hand.R");
            CHECK(clip("shoot").prop == "bow:hand.L");
            CHECK(clip("fish_stand").prop == "rod:hand.R");
            CHECK(clip("work").prop == "hammer:hand.R");
            CHECK(clip("idle").prop.empty());
            CHECK_FALSE(clip("fish_cast").loops);
            CHECK(clip("walk").loops);
            // The hands tell their length, to put the grip at their middle.
            REQUIRE(m.joint_length.size() == m.joint_names.size());
            for (const char* hand : {"hand.L", "hand.R"}) {
                const int j = m.joint_index(hand);
                REQUIRE(j >= 0);
                CHECK(m.joint_length[static_cast<std::size_t>(j)] > 0.05f);
                CHECK(m.joint_length[static_cast<std::size_t>(j)] < 0.4f);
            }
            CHECK(m.joint_length[static_cast<std::size_t>(m.joint_index("head"))] == 0.0f);
        }
    }

    TEST_CASE("tools and props are rigid models; a tool says where it is held") {
        for (const char* file : {"tools/axe.glb", "tools/bow.glb", "tools/rod.glb", "tools/hammer.glb",
                                 "trees/pine_bloom.glb", "props/rock.glb", "props/house_small.glb"}) {
            const ModelLoadResult r = load_data(file);
            REQUIRE_MESSAGE(r.ok, file << ": " << r.error);
            CHECK_FALSE(r.model.skinned());
            CHECK_FALSE(r.model.primitives.empty());
        }
        // The axe is held 0.36 m up its handle (written with Z up, read with Y up).
        const ModelLoadResult axe = load_data("tools/axe.glb");
        CHECK(axe.model.grip.x == doctest::Approx(0.0f));
        CHECK(axe.model.grip.y == doctest::Approx(0.36f).epsilon(0.01));
        CHECK(axe.model.grip.z == doctest::Approx(0.0f));
        // A model that does not say is held by its origin.
        const ModelLoadResult rock = load_data("props/rock.glb");
        CHECK(rock.model.grip.y == 0.0f);
    }

    TEST_CASE("a skinned model with a joint index past the skeleton is rejected") {
        const ModelLoadResult ok = load_glb(make_glb(kSkinnedJson, skinned_triangle(0)));
        REQUIRE_MESSAGE(ok.ok, ok.error);
        CHECK(ok.model.joint_names.size() == 1);
        CHECK(ok.model.joint_names[0] == "root");
        CHECK_FALSE(load_glb(make_glb(kSkinnedJson, skinned_triangle(3))).ok);
    }

    TEST_CASE("a rigged zoo animal loads with its skeleton and five clips") {
        // Built by art/blender/zoo_build.py (phase 44); copied here as a fixture.
        const ModelLoadResult r = load_file("animal_pig.glb");
        REQUIRE_MESSAGE(r.ok, r.error);
        const ModelData& m = r.model;
        CHECK(m.skinned());
        CHECK(m.joint_names.size() == 21);
        CHECK(m.joint_index("body") >= 0);
        CHECK(m.joint_index("foot.HR") >= 0);
        CHECK(m.skin.size() == m.vertices.size());
        for (const JointWeights& jw : m.skin) {
            CHECK(jw.weights[0] + jw.weights[1] + jw.weights[2] + jw.weights[3] == 255);
        }
        const std::pair<const char*, int> clips[] = {{"idle", 90}, {"walk", 16}, {"run", 14}, {"eat", 90}, {"die", 45}};
        for (const auto& [name, frames] : clips) {
            const int c = m.clip_index(name);
            REQUIRE_MESSAGE(c >= 0, name);
            CHECK(m.clips[static_cast<std::size_t>(c)].frame_count == frames);
        }
        // Phase 45: the speeds saved in the skeleton's extras, and the bones' parents.
        CHECK(m.clips[static_cast<std::size_t>(m.clip_index("walk"))].speed == doctest::Approx(0.7f));
        CHECK(m.clips[static_cast<std::size_t>(m.clip_index("run"))].speed == doctest::Approx(1.6f));
        CHECK(m.clips[static_cast<std::size_t>(m.clip_index("idle"))].speed == 0.0f);
        REQUIRE(m.joint_parent.size() == m.joint_names.size());
        CHECK(m.joint_parent[static_cast<std::size_t>(m.joint_index("body"))] == -1);
        CHECK(m.joint_parent[static_cast<std::size_t>(m.joint_index("chest"))] == m.joint_index("body"));
        CHECK(m.joint_parent[static_cast<std::size_t>(m.joint_index("foot.HR"))] == m.joint_index("leg_lower.HR"));
        CHECK(m.bounds_min.y == doctest::Approx(0.0f).epsilon(0.001));
    }

    TEST_CASE("the game's animals are rigged, with the speeds of their walk and run") {
        // Phase 47: art/blender/build_all.py builds them from the zoo specs.
        for (const char* file : {"animals/deer.glb", "animals/boar.glb", "animals/wolf.glb", "animals/bear.glb"}) {
            const ModelLoadResult r = load_data(file);
            REQUIRE_MESSAGE(r.ok, file << ": " << r.error);
            const ModelData& m = r.model;
            CHECK(m.skinned());
            for (const char* name : {"idle", "walk", "run", "eat", "die"}) {
                CHECK_MESSAGE(m.clip_index(name) >= 0, file << " " << name);
            }
            const float walk = m.clips[static_cast<std::size_t>(std::max(0, m.clip_index("walk")))].speed;
            const float run = m.clips[static_cast<std::size_t>(std::max(0, m.clip_index("run")))].speed;
            CHECK(walk > 0.5f);
            CHECK(run > walk * 2.0f);
            CHECK(m.bounds_min.y == doctest::Approx(0.0f).epsilon(0.001));
        }
    }

    TEST_CASE("a tree's far version is the same tree in about 300 triangles") {
        // Phase 52: art/blender/far_tree.py makes it from the finished model.
        for (const char* state : {"bloom", "autumn", "bare"}) {
            const std::string name = std::string("trees/cherry_1_") + state;
            const ModelLoadResult near_model = load_data((name + ".glb").c_str());
            const ModelLoadResult far_model = load_data((name + "_far.glb").c_str());
            REQUIRE_MESSAGE(near_model.ok, name << ": " << near_model.error);
            REQUIRE_MESSAGE(far_model.ok, name << "_far: " << far_model.error);
            const std::size_t far_triangles = far_model.model.indices.size() / 3;
            CHECK(far_triangles >= 100);
            CHECK(far_triangles <= 330);
            CHECK(far_triangles * 4 < near_model.model.indices.size() / 3);
            // As tall and as wide, within a fifth: it takes the other's place.
            const float near_h = near_model.model.bounds_max.y - near_model.model.bounds_min.y;
            const float far_h = far_model.model.bounds_max.y - far_model.model.bounds_min.y;
            CHECK(far_h == doctest::Approx(near_h).epsilon(0.2));
            const float near_w = near_model.model.bounds_max.x - near_model.model.bounds_min.x;
            const float far_w = far_model.model.bounds_max.x - far_model.model.bounds_min.x;
            CHECK(far_w == doctest::Approx(near_w).epsilon(0.25));
            CHECK(far_model.model.bounds_min.y == doctest::Approx(0.0f).epsilon(0.01).scale(1.0));
        }
    }

    TEST_CASE("the study models that have been generated load, skeletons and clips included") {
        // art/studies is not versioned: the Blender scripts write it (phases 46
        // and 48). Whatever is there must load; a checkout without it skips this.
        std::size_t loaded = 0;
        std::size_t skinned = 0;
        for (const char* folder : {"animals", "people", "weapons", "trees", "tripo"}) {
            const std::filesystem::path dir = std::filesystem::path(SC_SOURCE_DIR) / "art" / "studies" / folder;
            std::error_code ec;
            if (!std::filesystem::is_directory(dir, ec)) {
                continue;
            }
            for (const std::filesystem::directory_entry& entry : std::filesystem::directory_iterator(dir, ec)) {
                if (entry.path().extension() != ".glb") {
                    continue;
                }
                const std::string name = entry.path().filename().string();
                const auto file = fs::read_file(entry.path(), model_limits::kMaxFileBytes);
                REQUIRE_MESSAGE(file.error == fs::IoError::None, name);
                const ModelLoadResult r =
                    load_glb({reinterpret_cast<const std::uint8_t*>(file.data.data()), file.data.size()});
                REQUIRE_MESSAGE(r.ok, name << ": " << r.error);
                ++loaded;
                const ModelData& m = r.model;
                CHECK_MESSAGE(!m.primitives.empty(), name);
                if (!m.skinned()) {
                    continue;
                }
                ++skinned;
                CHECK_MESSAGE(m.joint_names.size() <= model_limits::kMaxJoints, name);
                CHECK_MESSAGE(!m.clips.empty(), name);
                CHECK_MESSAGE(m.clip_index("idle") >= 0, name);
                CHECK_MESSAGE(m.skin.size() == m.vertices.size(), name);
                bool weights_ok = true;
                for (const JointWeights& jw : m.skin) {
                    weights_ok = weights_ok && jw.weights[0] + jw.weights[1] + jw.weights[2] + jw.weights[3] == 255;
                    for (const std::uint8_t j : jw.joints) {
                        weights_ok = weights_ok && j < m.joint_names.size();
                    }
                }
                CHECK_MESSAGE(weights_ok, name);
                for (const ModelClip& c : m.clips) {
                    CHECK_MESSAGE(c.skin.size() == static_cast<std::size_t>(c.frame_count) * m.joint_names.size(), name);
                    // A clip that moves along the ground says how fast.
                    if (c.name == "walk" || c.name == "run") {
                        CHECK_MESSAGE(c.speed > 0.0f, name << " " << c.name);
                    }
                }
            }
        }
        MESSAGE("study models loaded: " << loaded << ", with a skeleton: " << skinned);
    }
}
