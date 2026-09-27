// The map's ground and water. Heights and water levels live on the GPU in
// storage buffers; the ground is drawn with a few shared grid meshes (one
// per level of detail) placed on 64 m chunks, so a huge map costs little
// memory and each frame only uploads the list of visible chunks.
#pragma once

#include <cstdint>
#include <vector>

#include <SDL3/SDL_gpu.h>

#include "math/vec.h"

namespace sc::render {

// Cells per side of a chunk. Map sizes are multiples of it.
inline constexpr std::int32_t kTerrainChunk = 64;
// Levels of detail: vertex step 1, 2, 4, 8 and 16 cells.
inline constexpr int kTerrainLods = 5;

struct TerrainData {
    std::int32_t cells = 0;              // Per side (1 cell = 1 m); a multiple of kTerrainChunk.
    std::vector<std::uint16_t> heights;  // (cells + 1)^2 vertices, centimeters.
    std::vector<std::uint16_t> water;    // cells^2: water surface in centimeters, 0 = dry.
    std::int32_t color_size = 0;         // Texels per side of the ground colors.
    std::vector<std::uint8_t> colors;    // color_size^2 RGBA, sRGB.

    [[nodiscard]] bool valid() const;
};

// Level of detail for a chunk at `distance` meters: 0 (full) to 4.
[[nodiscard]] int terrain_lod_for_distance(float distance);

struct TerrainStats {
    std::uint32_t chunks_drawn = 0;
    std::uint32_t water_chunks_drawn = 0;
    std::uint64_t triangles = 0;
    std::uint32_t draw_calls = 0;
};

class TerrainLayer {
public:
    TerrainLayer() = default;
    ~TerrainLayer();
    TerrainLayer(const TerrainLayer&) = delete;
    TerrainLayer& operator=(const TerrainLayer&) = delete;

    // Pipelines for the given targets; call again when the sample count
    // changes. `ground_fragment` is the scene's lit mesh shader.
    bool create_pipelines(SDL_GPUDevice* device, SDL_GPUTextureFormat color, SDL_GPUTextureFormat depth,
                          SDL_GPUSampleCount samples, SDL_GPUShader* ground_fragment);
    void release();

    // Uploads a map; replaces the previous one. Returns false on invalid
    // data or GPU errors (the layer is then empty).
    bool set(SDL_GPUDevice* device, const TerrainData& data);
    void clear();
    [[nodiscard]] bool has_terrain() const { return cells_ > 0; }

    // Chooses the visible chunks and their level of detail, and uploads the
    // lists in a copy pass of `cmd`.
    bool prepare(SDL_GPUCommandBuffer* cmd, const math::Frustum& frustum, math::Vec3 eye, float draw_distance);

    // Draws the ground in the current pass. The scene's fragment uniforms
    // (slot 0) must already be pushed.
    void draw_ground(SDL_GPUCommandBuffer* cmd, SDL_GPURenderPass* pass, const math::Mat4& view_proj,
                     SDL_GPUTexture* detail, SDL_GPUSampler* detail_sampler, SDL_GPUTexture* shadow_map,
                     SDL_GPUSampler* shadow_sampler);

    struct WaterLook {
        math::Vec3 sun_direction;
        math::Vec3 sun_color;
        math::Vec3 fog_color;
        float fog_density = 0.0f;
        math::Vec3 eye;
        float time = 0.0f;
    };
    // Draws the water surfaces; call after everything opaque.
    void draw_water(SDL_GPUCommandBuffer* cmd, SDL_GPURenderPass* pass, const math::Mat4& view_proj,
                    const WaterLook& look);

    [[nodiscard]] const TerrainStats& stats() const { return stats_; }

private:
    struct Chunk {
        math::Vec3 center;
        float radius = 0.0f;
        bool water = false;
    };
    struct Grid {
        SDL_GPUBuffer* vertices = nullptr;
        SDL_GPUBuffer* indices = nullptr;
        std::uint32_t index_count = 0;
    };
    struct Range {
        std::uint32_t first = 0;
        std::uint32_t count = 0;
    };

    bool create_grids();
    void release_map();
    SDL_GPUBuffer* upload(const void* data, std::uint32_t size, SDL_GPUBufferUsageFlags usage);
    SDL_GPUTexture* upload_colors(const TerrainData& data);

    SDL_GPUDevice* device_ = nullptr;
    SDL_GPUGraphicsPipeline* ground_pipeline_ = nullptr;
    SDL_GPUGraphicsPipeline* water_pipeline_ = nullptr;
    SDL_GPUSampler* color_sampler_ = nullptr;
    Grid grids_[kTerrainLods];

    std::int32_t cells_ = 0;
    std::int32_t color_size_ = 0;
    SDL_GPUBuffer* heights_ = nullptr;
    SDL_GPUBuffer* water_ = nullptr;
    SDL_GPUBuffer* chunk_buffer_ = nullptr;
    SDL_GPUTexture* colors_ = nullptr;
    std::vector<Chunk> chunks_;

    // Per frame: visible chunk indices, ground lists then water lists.
    std::vector<std::uint32_t> lists_;
    Range ground_ranges_[kTerrainLods];
    Range water_ranges_[kTerrainLods];
    SDL_GPUBuffer* list_buffer_ = nullptr;
    std::uint32_t list_capacity_ = 0;
    SDL_GPUTransferBuffer* list_transfer_ = nullptr;
    std::uint32_t list_transfer_capacity_ = 0;

    TerrainStats stats_;
};

}  // namespace sc::render
