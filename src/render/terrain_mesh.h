// Faceted terrain meshes: each 64 m chunk is triangulated adaptively (a
// right-triangulated irregular network, "RTIN") so flat ground gets large
// facets and shores, slopes and ridges get small ones. Vertices are nudged
// off the grid so facets look irregular. Pure CPU work, done once per map
// on the generation thread (decision D-626).
#pragma once

#include <array>
#include <cstdint>
#include <vector>

namespace sc::render {

inline constexpr int kFacetLods = 3;

// What kind of ground a cell is, for placing small facets where it changes:
// facets never span an edge between two different classes.
enum class GroundClass : std::uint8_t { Soft, Sand, Water, Rock };

struct FacetSettings {
    float max_error_m;   // Largest height error allowed inside a facet.
    int max_leg;         // Largest facet leg, in cells (a power of two).
    bool split_classes;  // Keep facets inside one ground class.
};

// Level of detail settings, closest first.
[[nodiscard]] const FacetSettings& facet_settings(int lod);

struct ChunkLod {
    std::uint32_t first_vertex = 0;
    std::uint32_t first_index = 0;
    std::uint32_t index_count = 0;
    std::uint32_t first_face = 0;  // Into face_colors; facets follow the index order.
};

struct FacetMeshes {
    std::int32_t cells = 0;                   // Map side.
    std::vector<float> positions;             // x, y, z per vertex, world meters.
    std::vector<std::uint16_t> indices;       // Per chunk, relative to its first vertex.
    std::vector<std::uint32_t> face_colors;   // One RGBA8 (sRGB) per facet, skirts included.
    std::vector<std::array<ChunkLod, kFacetLods>> chunks;  // Row-major chunks.
    // Decorative mountains around the map, in tiles (one level of detail),
    // with each tile's bounding box (min x, min y, min z, max x, max y, max z).
    std::vector<ChunkLod> backdrop;
    std::vector<std::array<float, 6>> backdrop_bounds;

    [[nodiscard]] std::size_t triangle_count(int lod) const;
};

// Builds all chunks. `heights_cm` has (cells + 1)^2 vertices; `classes`
// and `cell_colors` (RGBA8, sRGB) have cells^2 entries. Each facet takes
// the color of the cell at its center, a little varied. `seed` varies the
// nudges and shades.
[[nodiscard]] FacetMeshes build_facet_meshes(std::int32_t cells, const std::vector<std::uint16_t>& heights_cm,
                                             const std::vector<std::uint8_t>& classes,
                                             const std::vector<std::uint32_t>& cell_colors, std::uint32_t seed);

// Adds a ring of mountains outside the map, rising from the height of the
// map's edge: grass low, rock on the slopes, snow on the peaks. Decoration
// only (decision D-628). With `sea_m` (0 or more), a flat open sea at that
// height instead (the map of islands).
void add_backdrop(FacetMeshes& meshes, std::int32_t cells, const std::vector<std::uint16_t>& heights_cm,
                  std::uint32_t seed, float sea_m = -1.0f);

}  // namespace sc::render
