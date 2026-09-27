#include <doctest.h>

#include <cmath>
#include <vector>

#include "render/terrain_mesh.h"

using namespace sc::render;

namespace {

struct Ground {
    std::int32_t cells = 128;
    std::vector<std::uint16_t> heights;
    std::vector<std::uint8_t> classes;
    std::vector<std::uint32_t> colors;
};

Ground flat_ground(std::int32_t cells) {
    Ground g;
    g.cells = cells;
    g.heights.assign(static_cast<std::size_t>(cells + 1) * static_cast<std::size_t>(cells + 1), 2000);
    g.classes.assign(static_cast<std::size_t>(cells) * static_cast<std::size_t>(cells), 0);
    g.colors.assign(g.classes.size(), 0xFF40A060u);
    return g;
}

Ground bumpy_ground(std::int32_t cells) {
    Ground g = flat_ground(cells);
    for (std::int32_t z = 0; z <= cells; ++z) {
        for (std::int32_t x = 0; x <= cells; ++x) {
            const double h = 2000.0 + 300.0 * std::sin(x * 0.37) * std::cos(z * 0.23) + 150.0 * std::sin(x * 1.3 + z);
            g.heights[static_cast<std::size_t>(z) * static_cast<std::size_t>(cells + 1) + static_cast<std::size_t>(x)] =
                static_cast<std::uint16_t>(h);
        }
    }
    return g;
}

FacetMeshes build(const Ground& g) {
    return build_facet_meshes(g.cells, g.heights, g.classes, g.colors, 7);
}

}  // namespace

TEST_SUITE("terrain_mesh") {
    TEST_CASE("meshes are well formed") {
        const Ground g = bumpy_ground(128);
        const FacetMeshes m = build(g);
        REQUIRE(m.chunks.size() == 4);
        std::size_t faces = 0;
        for (const auto& chunk : m.chunks) {
            for (int lod = 0; lod < kFacetLods; ++lod) {
                const ChunkLod& part = chunk[static_cast<std::size_t>(lod)];
                REQUIRE(part.index_count % 3 == 0);
                CHECK(part.index_count > 0);
                CHECK(part.first_face == faces);
                faces += part.index_count / 3;
                // Every index points at a vertex of this part.
                const std::size_t vertices = m.positions.size() / 3 - part.first_vertex;
                for (std::uint32_t i = 0; i < part.index_count; ++i) {
                    CHECK(m.indices[part.first_index + i] < vertices);
                }
            }
        }
        CHECK(m.face_colors.size() == faces);
        // Vertices stay on the map (nudges are small) and on the ground.
        for (std::size_t k = 0; k + 2 < m.positions.size(); k += 3) {
            CHECK(m.positions[k] >= -0.01f);
            CHECK(m.positions[k] <= 128.01f);
            CHECK(m.positions[k + 2] >= -0.01f);
            CHECK(m.positions[k + 2] <= 128.01f);
        }
    }

    TEST_CASE("detail follows the relief and the level") {
        const FacetMeshes flat = build(flat_ground(128));
        const FacetMeshes bumpy = build(bumpy_ground(128));
        // Flat ground only splits down to the largest facet size.
        CHECK(flat.triangle_count(0) < bumpy.triangle_count(0));
        CHECK(bumpy.triangle_count(2) < bumpy.triangle_count(1));
        CHECK(bumpy.triangle_count(1) < bumpy.triangle_count(0));
    }

    TEST_CASE("facets stay inside one kind of ground") {
        Ground plain = flat_ground(128);
        Ground shore = plain;
        // A diagonal band of water across the map.
        for (std::int32_t z = 0; z < 128; ++z) {
            for (std::int32_t x = 0; x < 128; ++x) {
                if (std::abs(x - z) < 6) {
                    shore.classes[static_cast<std::size_t>(z) * 128u + static_cast<std::size_t>(x)] =
                        static_cast<std::uint8_t>(GroundClass::Water);
                }
            }
        }
        const FacetMeshes a = build(plain);
        const FacetMeshes b = build(shore);
        CHECK(b.triangle_count(0) > a.triangle_count(0) * 2);
        // The far level ignores it.
        CHECK(b.triangle_count(2) == a.triangle_count(2));
    }

    TEST_CASE("the same input gives the same meshes") {
        const Ground g = bumpy_ground(128);
        const FacetMeshes a = build(g);
        const FacetMeshes b = build(g);
        CHECK(a.positions == b.positions);
        CHECK(a.indices == b.indices);
        CHECK(a.face_colors == b.face_colors);
    }

    TEST_CASE("bad input gives nothing") {
        Ground g = flat_ground(128);
        g.colors.pop_back();
        CHECK(build(g).chunks.empty());
        CHECK(build_facet_meshes(100, std::vector<std::uint16_t>(101 * 101), std::vector<std::uint8_t>(100 * 100),
                                 std::vector<std::uint32_t>(100 * 100), 1)
                  .chunks.empty());
    }

    TEST_CASE("the mountains stay outside the map") {
        const Ground g = flat_ground(128);
        FacetMeshes m = build(g);
        const std::size_t before = m.indices.size();
        add_backdrop(m, g.cells, g.heights, 3);
        REQUIRE(!m.backdrop.empty());
        CHECK(m.backdrop.size() == m.backdrop_bounds.size());
        CHECK(m.indices.size() > before);
        for (const ChunkLod& tile : m.backdrop) {
            for (std::uint32_t t = 0; t < tile.index_count; t += 3) {
                float cx = 0.0f;
                float cz = 0.0f;
                for (std::uint32_t k = 0; k < 3; ++k) {
                    const std::size_t v = (tile.first_vertex + m.indices[tile.first_index + t + k]) * 3u;
                    cx += m.positions[v] / 3.0f;
                    cz += m.positions[v + 2] / 3.0f;
                }
                const bool inside = cx > 1.0f && cx < 127.0f && cz > 1.0f && cz < 127.0f;
                CHECK_FALSE(inside);
            }
        }
    }
}
