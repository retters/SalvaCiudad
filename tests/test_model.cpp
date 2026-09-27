#include <doctest.h>

#include <cstring>

#include "core/file_io.h"
#include "render/model.h"
#include "test_util.h"

using namespace sc;
using namespace sc::render;

namespace {

const std::filesystem::path kModels = std::filesystem::path(SC_SOURCE_DIR) / "data" / "models" / "test";

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
