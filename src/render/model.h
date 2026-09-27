// Loading of binary glTF (.glb) models into CPU-side data ready for the GPU.
// The file is untrusted input: sizes, counts and indices are checked, and
// only data inside the file itself is used (no external URIs).
#pragma once

#include <cstddef>
#include <cstdint>
#include <span>
#include <string>
#include <vector>

#include "math/vec.h"

namespace sc::render {

struct ModelVertex {
    float px, py, pz;
    float nx, ny, nz;
    float u, v;
};

struct ModelTexture {
    int width = 0;
    int height = 0;
    std::vector<std::uint8_t> rgba;
};

struct ModelMaterial {
    float base_color[4] = {1, 1, 1, 1};
    int texture = -1;  // Index into ModelData::textures, or -1.
};

struct ModelPrimitive {
    std::uint32_t first_index = 0;
    std::uint32_t index_count = 0;
    std::uint32_t material = 0;
};

struct ModelData {
    std::vector<ModelVertex> vertices;
    std::vector<std::uint32_t> indices;
    std::vector<ModelPrimitive> primitives;
    std::vector<ModelMaterial> materials;
    std::vector<ModelTexture> textures;
    math::Vec3 bounds_min;
    math::Vec3 bounds_max;
    // Sphere around the model origin that contains every vertex.
    float radius = 0.0f;
};

namespace model_limits {
inline constexpr std::size_t kMaxFileBytes = 64u * 1024u * 1024u;
inline constexpr std::size_t kMaxVertices = 2'000'000;
inline constexpr std::size_t kMaxIndices = 6'000'000;
inline constexpr std::size_t kMaxPrimitives = 256;
inline constexpr std::size_t kMaxTextures = 16;
inline constexpr int kMaxTextureSize = 4096;
}  // namespace model_limits

struct ModelLoadResult {
    bool ok = false;
    std::string error;  // English, for the log.
    ModelData model;
};

[[nodiscard]] ModelLoadResult load_glb(std::span<const std::uint8_t> file);

}  // namespace sc::render
