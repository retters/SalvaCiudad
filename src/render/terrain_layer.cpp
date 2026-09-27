#include "render/terrain_layer.h"

#include <algorithm>
#include <cmath>
#include <cstring>

#include <SDL3/SDL_error.h>

#include "core/log.h"
#include "shaders/grass_vert_dxil.h"
#include "shaders/terrain_vert_dxil.h"
#include "shaders/water_frag_dxil.h"
#include "shaders/water_vert_dxil.h"

namespace sc::render {

namespace {

// Matches ChunkData in terrain_common.hlsli.
struct GpuChunk {
    std::int32_t origin[4];
    float bounds[4];
};
static_assert(sizeof(GpuChunk) == 32);

struct TerrainUniforms {
    math::Mat4 view_proj;
    std::int32_t map[4];  // Vertices per side, cells per side.
};

struct LodUniforms {
    std::int32_t lod[4];  // Vertex step, color mip level.
};

struct MaterialUniforms {
    float base_color[4];
};

struct WaterUniforms {
    float sun_direction[4];
    float sun_color[4];
    float fog_color[4];
    float camera_position[4];
    float shallow_color[4];
    float deep_color[4];
};

struct GridVertex {
    float x, skirt, z;
};

struct GrassUniforms {
    math::Mat4 view_proj;
    std::int32_t map[4];  // Vertices per side, cells per side, tufts per grid side.
    float grid[4];        // First cell (x, z), spacing, far distance.
    float camera[4];      // Eye and time.
};

// Meters between grass tufts.
constexpr float kGrassSpacing = 0.55f;

// Water keeps more detail than the ground far away, so rivers do not break
// up: at most a step of 2 cells.
constexpr int kMaxWaterLod = 1;

// Distances (meters) where each level of detail ends.
constexpr float kLodDistances[kTerrainLods - 1] = {140.0f, 280.0f, 560.0f, 1120.0f};

void set4(float out[4], math::Vec3 v, float w) {
    out[0] = v.x;
    out[1] = v.y;
    out[2] = v.z;
    out[3] = w;
}

SDL_GPUShader* make_shader(SDL_GPUDevice* device, const std::uint8_t* code, std::size_t size, SDL_GPUShaderStage stage,
                           std::uint32_t samplers, std::uint32_t storage_buffers, std::uint32_t uniform_buffers) {
    SDL_GPUShaderCreateInfo info{};
    info.code = code;
    info.code_size = size;
    info.entrypoint = "main";
    info.format = SDL_GPU_SHADERFORMAT_DXIL;
    info.stage = stage;
    info.num_samplers = samplers;
    info.num_storage_buffers = storage_buffers;
    info.num_uniform_buffers = uniform_buffers;
    SDL_GPUShader* shader = SDL_CreateGPUShader(device, &info);
    if (shader == nullptr) {
        log::error("terrain: SDL_CreateGPUShader failed: {}", SDL_GetError());
    }
    return shader;
}

int log2_int(int v) {
    int r = 0;
    while (v > 1) {
        v /= 2;
        ++r;
    }
    return r;
}

}  // namespace

bool TerrainData::valid() const {
    if (cells < kTerrainChunk || cells % kTerrainChunk != 0 || cells > 8192) {
        return false;
    }
    const auto n = static_cast<std::size_t>(cells);
    if (heights.size() != (n + 1) * (n + 1) || water.size() != n * n) {
        return false;
    }
    if (color_size < 1 || color_size > 8192 || (color_size & (color_size - 1)) != 0) {
        return false;
    }
    const auto c = static_cast<std::size_t>(color_size);
    return colors.size() == c * c * 4;
}

int terrain_lod_for_distance(float distance) {
    int lod = 0;
    while (lod < kTerrainLods - 1 && distance >= kLodDistances[lod]) {
        ++lod;
    }
    return lod;
}

TerrainLayer::~TerrainLayer() {
    release();
}

void TerrainLayer::release() {
    if (device_ == nullptr) {
        return;
    }
    release_map();
    SDL_ReleaseGPUGraphicsPipeline(device_, ground_pipeline_);
    SDL_ReleaseGPUGraphicsPipeline(device_, water_pipeline_);
    SDL_ReleaseGPUGraphicsPipeline(device_, grass_pipeline_);
    ground_pipeline_ = water_pipeline_ = grass_pipeline_ = nullptr;
    SDL_ReleaseGPUBuffer(device_, grass_mesh_.vertices);
    SDL_ReleaseGPUBuffer(device_, grass_mesh_.indices);
    grass_mesh_ = Grid{};
    SDL_ReleaseGPUSampler(device_, color_sampler_);
    color_sampler_ = nullptr;
    for (Grid& g : grids_) {
        SDL_ReleaseGPUBuffer(device_, g.vertices);
        SDL_ReleaseGPUBuffer(device_, g.indices);
        g = Grid{};
    }
    SDL_ReleaseGPUBuffer(device_, list_buffer_);
    SDL_ReleaseGPUTransferBuffer(device_, list_transfer_);
    list_buffer_ = nullptr;
    list_transfer_ = nullptr;
    list_capacity_ = list_transfer_capacity_ = 0;
    device_ = nullptr;
}

void TerrainLayer::release_map() {
    if (device_ == nullptr) {
        return;
    }
    SDL_ReleaseGPUBuffer(device_, heights_);
    SDL_ReleaseGPUBuffer(device_, water_);
    SDL_ReleaseGPUBuffer(device_, chunk_buffer_);
    SDL_ReleaseGPUTexture(device_, colors_);
    heights_ = water_ = chunk_buffer_ = nullptr;
    colors_ = nullptr;
    chunks_.clear();
    cells_ = 0;
    color_size_ = 0;
}

void TerrainLayer::clear() {
    release_map();
}

bool TerrainLayer::create_pipelines(SDL_GPUDevice* device, SDL_GPUTextureFormat color, SDL_GPUTextureFormat depth,
                                    SDL_GPUSampleCount samples, SDL_GPUShader* ground_fragment) {
    device_ = device;
    SDL_ReleaseGPUGraphicsPipeline(device_, ground_pipeline_);
    SDL_ReleaseGPUGraphicsPipeline(device_, water_pipeline_);
    SDL_ReleaseGPUGraphicsPipeline(device_, grass_pipeline_);
    ground_pipeline_ = water_pipeline_ = grass_pipeline_ = nullptr;
    if (color_sampler_ == nullptr) {
        SDL_GPUSamplerCreateInfo si{};
        si.min_filter = SDL_GPU_FILTER_LINEAR;
        si.mag_filter = SDL_GPU_FILTER_LINEAR;
        si.mipmap_mode = SDL_GPU_SAMPLERMIPMAPMODE_LINEAR;
        si.address_mode_u = si.address_mode_v = si.address_mode_w = SDL_GPU_SAMPLERADDRESSMODE_CLAMP_TO_EDGE;
        si.max_lod = 1000.0f;
        color_sampler_ = SDL_CreateGPUSampler(device_, &si);
    }
    if (grids_[0].vertices == nullptr && !create_grids()) {
        return false;
    }
    if (grass_mesh_.vertices == nullptr && !create_grass_mesh()) {
        log::warn("terrain: cannot upload the grass mesh: {}", SDL_GetError());
    }

    SDL_GPUShader* ground_vs =
        make_shader(device_, kTerrainVertDxil, kTerrainVertDxil_size, SDL_GPU_SHADERSTAGE_VERTEX, 1, 2, 2);
    SDL_GPUShader* water_vs = make_shader(device_, kWaterVertDxil, kWaterVertDxil_size, SDL_GPU_SHADERSTAGE_VERTEX, 0, 3, 1);
    SDL_GPUShader* water_fs =
        make_shader(device_, kWaterFragDxil, kWaterFragDxil_size, SDL_GPU_SHADERSTAGE_FRAGMENT, 0, 0, 1);
    SDL_GPUShader* grass_vs = make_shader(device_, kGrassVertDxil, kGrassVertDxil_size, SDL_GPU_SHADERSTAGE_VERTEX, 1, 2, 1);

    if (ground_vs != nullptr && water_vs != nullptr && water_fs != nullptr && ground_fragment != nullptr &&
        color_sampler_ != nullptr) {
        SDL_GPUVertexBufferDescription buffers[2]{};
        buffers[0] = {0, sizeof(GridVertex), SDL_GPU_VERTEXINPUTRATE_VERTEX, 0};
        buffers[1] = {1, sizeof(std::uint32_t), SDL_GPU_VERTEXINPUTRATE_INSTANCE, 0};
        SDL_GPUVertexAttribute attrs[2]{};
        attrs[0] = {0, 0, SDL_GPU_VERTEXELEMENTFORMAT_FLOAT3, 0};
        attrs[1] = {1, 1, SDL_GPU_VERTEXELEMENTFORMAT_UINT, 0};

        SDL_GPUColorTargetDescription target{};
        target.format = color;

        SDL_GPUGraphicsPipelineCreateInfo gi{};
        gi.vertex_shader = ground_vs;
        gi.fragment_shader = ground_fragment;
        gi.vertex_input_state = {buffers, 2, attrs, 2};
        gi.primitive_type = SDL_GPU_PRIMITIVETYPE_TRIANGLELIST;
        // Skirts face outwards on every side; drawing both faces is simpler
        // than orienting them, and the ground's back faces are never seen.
        gi.rasterizer_state.cull_mode = SDL_GPU_CULLMODE_NONE;
        gi.multisample_state.sample_count = samples;
        gi.depth_stencil_state.enable_depth_test = true;
        gi.depth_stencil_state.enable_depth_write = true;
        gi.depth_stencil_state.compare_op = SDL_GPU_COMPAREOP_GREATER;  // Reversed Z.
        gi.target_info.color_target_descriptions = &target;
        gi.target_info.num_color_targets = 1;
        gi.target_info.depth_stencil_format = depth;
        gi.target_info.has_depth_stencil_target = true;
        ground_pipeline_ = SDL_CreateGPUGraphicsPipeline(device_, &gi);

        SDL_GPUColorTargetDescription blended = target;
        blended.blend_state.enable_blend = true;
        blended.blend_state.src_color_blendfactor = SDL_GPU_BLENDFACTOR_SRC_ALPHA;
        blended.blend_state.dst_color_blendfactor = SDL_GPU_BLENDFACTOR_ONE_MINUS_SRC_ALPHA;
        blended.blend_state.color_blend_op = SDL_GPU_BLENDOP_ADD;
        blended.blend_state.src_alpha_blendfactor = SDL_GPU_BLENDFACTOR_ONE;
        blended.blend_state.dst_alpha_blendfactor = SDL_GPU_BLENDFACTOR_ONE_MINUS_SRC_ALPHA;
        blended.blend_state.alpha_blend_op = SDL_GPU_BLENDOP_ADD;
        SDL_GPUGraphicsPipelineCreateInfo wi = gi;
        wi.vertex_shader = water_vs;
        wi.fragment_shader = water_fs;
        wi.depth_stencil_state.enable_depth_write = false;
        wi.target_info.color_target_descriptions = &blended;
        water_pipeline_ = SDL_CreateGPUGraphicsPipeline(device_, &wi);

        // Grass: one vertex stream, placed by the instance index.
        SDL_GPUGraphicsPipelineCreateInfo gr = gi;
        gr.vertex_shader = grass_vs;
        gr.vertex_input_state = {buffers, 1, attrs, 1};
        grass_pipeline_ = grass_vs != nullptr ? SDL_CreateGPUGraphicsPipeline(device_, &gr) : nullptr;
        if (grass_pipeline_ == nullptr) {
            log::warn("terrain: grass unavailable: {}", SDL_GetError());
        }
    }
    for (SDL_GPUShader* s : {ground_vs, water_vs, water_fs, grass_vs}) {
        SDL_ReleaseGPUShader(device_, s);
    }
    if (ground_pipeline_ == nullptr || water_pipeline_ == nullptr) {
        log::error("terrain: pipeline creation failed: {}", SDL_GetError());
        return false;
    }
    return true;
}

// A tuft of seven blades, each a thin triangle leaning outward; y goes from
// 0 at the root to 1 at the tip before scaling.
bool TerrainLayer::create_grass_mesh() {
    std::vector<GridVertex> verts;
    std::vector<std::uint16_t> indices;
    constexpr int kBlades = 7;
    for (int b = 0; b < kBlades; ++b) {
        const float a = static_cast<float>(b) * 2.399963f;
        const float c = std::cos(a);
        const float s = std::sin(a);
        const float out = 0.06f + 0.03f * static_cast<float>(b % 3);
        const float height = 0.32f + 0.07f * static_cast<float>((b * 5) % 4);
        const float half = 0.035f;
        const auto base = static_cast<std::uint16_t>(verts.size());
        verts.push_back({c * out - s * half, 0.0f, s * out + c * half});
        verts.push_back({c * out + s * half, 0.0f, s * out - c * half});
        verts.push_back({c * (out + 0.12f), height, s * (out + 0.12f)});
        indices.insert(indices.end(), {base, static_cast<std::uint16_t>(base + 1), static_cast<std::uint16_t>(base + 2)});
    }
    // The tip's y is the blade height; the shader reads it as 0..1 for
    // shading, which stays close enough.
    grass_mesh_.vertices = upload(verts.data(), static_cast<std::uint32_t>(verts.size() * sizeof(GridVertex)),
                                  SDL_GPU_BUFFERUSAGE_VERTEX);
    grass_mesh_.indices = upload(indices.data(), static_cast<std::uint32_t>(indices.size() * sizeof(std::uint16_t)),
                                 SDL_GPU_BUFFERUSAGE_INDEX);
    grass_mesh_.index_count = static_cast<std::uint32_t>(indices.size());
    return grass_mesh_.vertices != nullptr && grass_mesh_.indices != nullptr;
}

bool TerrainLayer::create_grids() {
    for (int lod = 0; lod < kTerrainLods; ++lod) {
        const int step = 1 << lod;
        const int n = kTerrainChunk / step;  // Quads per side.
        std::vector<GridVertex> verts;
        std::vector<std::uint16_t> indices;
        const auto vertex = [&](int i, int j) { return static_cast<std::uint16_t>(j * (n + 1) + i); };
        for (int j = 0; j <= n; ++j) {
            for (int i = 0; i <= n; ++i) {
                verts.push_back({static_cast<float>(i * step), 0.0f, static_cast<float>(j * step)});
            }
        }
        for (int j = 0; j < n; ++j) {
            for (int i = 0; i < n; ++i) {
                const std::uint16_t a = vertex(i, j);
                const std::uint16_t b = vertex(i + 1, j);
                const std::uint16_t c = vertex(i, j + 1);
                const std::uint16_t d = vertex(i + 1, j + 1);
                indices.insert(indices.end(), {a, c, b, b, c, d});
            }
        }
        // Skirts: each border edge gets a strip hanging below it.
        const auto skirt_edge = [&](auto edge_vertex) {
            const auto base = static_cast<std::uint16_t>(verts.size());
            for (int k = 0; k <= n; ++k) {
                GridVertex v = verts[edge_vertex(k)];
                v.skirt = 1.0f;
                verts.push_back(v);
            }
            for (int k = 0; k < n; ++k) {
                const std::uint16_t top0 = edge_vertex(k);
                const std::uint16_t top1 = edge_vertex(k + 1);
                const auto low0 = static_cast<std::uint16_t>(base + k);
                const auto low1 = static_cast<std::uint16_t>(base + k + 1);
                indices.insert(indices.end(), {top0, low0, top1, top1, low0, low1});
            }
        };
        skirt_edge([&](int k) { return vertex(k, 0); });
        skirt_edge([&](int k) { return vertex(k, n); });
        skirt_edge([&](int k) { return vertex(0, k); });
        skirt_edge([&](int k) { return vertex(n, k); });

        Grid& g = grids_[lod];
        g.vertices = upload(verts.data(), static_cast<std::uint32_t>(verts.size() * sizeof(GridVertex)),
                            SDL_GPU_BUFFERUSAGE_VERTEX);
        g.indices = upload(indices.data(), static_cast<std::uint32_t>(indices.size() * sizeof(std::uint16_t)),
                           SDL_GPU_BUFFERUSAGE_INDEX);
        g.index_count = static_cast<std::uint32_t>(indices.size());
        if (g.vertices == nullptr || g.indices == nullptr) {
            log::error("terrain: cannot upload the ground grids: {}", SDL_GetError());
            return false;
        }
    }
    return true;
}

// One-off upload through its own transfer buffer, released once the GPU is
// done with it, so a big map does not leave a big staging buffer behind.
SDL_GPUBuffer* TerrainLayer::upload(const void* data, std::uint32_t size, SDL_GPUBufferUsageFlags usage) {
    SDL_GPUBufferCreateInfo info{};
    info.usage = usage;
    info.size = size;
    SDL_GPUBuffer* buffer = SDL_CreateGPUBuffer(device_, &info);
    SDL_GPUTransferBufferCreateInfo ti{};
    ti.usage = SDL_GPU_TRANSFERBUFFERUSAGE_UPLOAD;
    ti.size = size;
    SDL_GPUTransferBuffer* transfer = SDL_CreateGPUTransferBuffer(device_, &ti);
    void* mapped = transfer != nullptr ? SDL_MapGPUTransferBuffer(device_, transfer, false) : nullptr;
    SDL_GPUCommandBuffer* cmd = nullptr;
    bool ok = buffer != nullptr && mapped != nullptr;
    if (ok) {
        std::memcpy(mapped, data, size);
        SDL_UnmapGPUTransferBuffer(device_, transfer);
        cmd = SDL_AcquireGPUCommandBuffer(device_);
        ok = cmd != nullptr;
    }
    if (ok) {
        SDL_GPUCopyPass* copy = SDL_BeginGPUCopyPass(cmd);
        const SDL_GPUTransferBufferLocation src{transfer, 0};
        const SDL_GPUBufferRegion dst{buffer, 0, size};
        SDL_UploadToGPUBuffer(copy, &src, &dst, false);
        SDL_EndGPUCopyPass(copy);
        ok = SDL_SubmitGPUCommandBuffer(cmd);
    }
    SDL_ReleaseGPUTransferBuffer(device_, transfer);
    if (!ok) {
        SDL_ReleaseGPUBuffer(device_, buffer);
        return nullptr;
    }
    return buffer;
}

SDL_GPUTexture* TerrainLayer::upload_colors(const TerrainData& data) {
    const auto size = static_cast<std::uint32_t>(data.color_size);
    SDL_GPUTextureCreateInfo info{};
    info.type = SDL_GPU_TEXTURETYPE_2D;
    info.format = SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM_SRGB;
    info.usage = SDL_GPU_TEXTUREUSAGE_SAMPLER | SDL_GPU_TEXTUREUSAGE_COLOR_TARGET;
    info.width = info.height = size;
    info.layer_count_or_depth = 1;
    info.num_levels = static_cast<std::uint32_t>(log2_int(data.color_size) + 1);
    SDL_GPUTexture* texture = SDL_CreateGPUTexture(device_, &info);
    const auto bytes = static_cast<std::uint32_t>(data.colors.size());
    SDL_GPUTransferBufferCreateInfo ti{};
    ti.usage = SDL_GPU_TRANSFERBUFFERUSAGE_UPLOAD;
    ti.size = bytes;
    SDL_GPUTransferBuffer* transfer = texture != nullptr ? SDL_CreateGPUTransferBuffer(device_, &ti) : nullptr;
    void* mapped = transfer != nullptr ? SDL_MapGPUTransferBuffer(device_, transfer, false) : nullptr;
    SDL_GPUCommandBuffer* cmd = nullptr;
    bool ok = mapped != nullptr;
    if (ok) {
        std::memcpy(mapped, data.colors.data(), bytes);
        SDL_UnmapGPUTransferBuffer(device_, transfer);
        cmd = SDL_AcquireGPUCommandBuffer(device_);
        ok = cmd != nullptr;
    }
    if (ok) {
        SDL_GPUCopyPass* copy = SDL_BeginGPUCopyPass(cmd);
        SDL_GPUTextureTransferInfo src{};
        src.transfer_buffer = transfer;
        src.pixels_per_row = size;
        src.rows_per_layer = size;
        SDL_GPUTextureRegion dst{};
        dst.texture = texture;
        dst.w = size;
        dst.h = size;
        dst.d = 1;
        SDL_UploadToGPUTexture(copy, &src, &dst, false);
        SDL_EndGPUCopyPass(copy);
        if (info.num_levels > 1) {
            SDL_GenerateMipmapsForGPUTexture(cmd, texture);
        }
        ok = SDL_SubmitGPUCommandBuffer(cmd);
    }
    SDL_ReleaseGPUTransferBuffer(device_, transfer);
    if (!ok) {
        log::error("terrain: cannot upload the ground colors: {}", SDL_GetError());
        SDL_ReleaseGPUTexture(device_, texture);
        return nullptr;
    }
    return texture;
}

bool TerrainLayer::set(SDL_GPUDevice* device, const TerrainData& data) {
    device_ = device;
    release_map();
    if (!data.valid()) {
        log::error("terrain: invalid terrain data");
        return false;
    }
    const std::int32_t n = data.cells;
    const std::int32_t v = n + 1;

    // Heights and water go up as they are: two 16-bit values per word.
    std::vector<std::uint16_t> padded = data.heights;
    if (padded.size() % 2 != 0) {
        padded.push_back(0);
    }
    heights_ = upload(padded.data(), static_cast<std::uint32_t>(padded.size() * sizeof(std::uint16_t)),
                      SDL_GPU_BUFFERUSAGE_GRAPHICS_STORAGE_READ);
    water_ = upload(data.water.data(), static_cast<std::uint32_t>(data.water.size() * sizeof(std::uint16_t)),
                    SDL_GPU_BUFFERUSAGE_GRAPHICS_STORAGE_READ);
    colors_ = upload_colors(data);

    // Chunk bounds for culling.
    const std::int32_t per_side = n / kTerrainChunk;
    std::vector<GpuChunk> gpu_chunks;
    gpu_chunks.reserve(static_cast<std::size_t>(per_side) * static_cast<std::size_t>(per_side));
    for (std::int32_t cz = 0; cz < per_side; ++cz) {
        for (std::int32_t cx = 0; cx < per_side; ++cx) {
            const std::int32_t ox = cx * kTerrainChunk;
            const std::int32_t oz = cz * kTerrainChunk;
            std::uint16_t lo = 0xFFFF;
            std::uint16_t hi = 0;
            for (std::int32_t z = oz; z <= oz + kTerrainChunk; ++z) {
                for (std::int32_t x = ox; x <= ox + kTerrainChunk; ++x) {
                    const std::uint16_t h = data.heights[static_cast<std::size_t>(z) * static_cast<std::size_t>(v) +
                                                         static_cast<std::size_t>(x)];
                    lo = std::min(lo, h);
                    hi = std::max(hi, h);
                }
            }
            bool wet = false;
            for (std::int32_t z = oz; z < oz + kTerrainChunk; ++z) {
                for (std::int32_t x = ox; x < ox + kTerrainChunk; ++x) {
                    const std::uint16_t w = data.water[static_cast<std::size_t>(z) * static_cast<std::size_t>(n) +
                                                       static_cast<std::size_t>(x)];
                    if (w != 0) {
                        wet = true;
                        hi = std::max(hi, w);
                    }
                }
            }
            // Skirts hang up to 9 m below the lowest vertex.
            const float low = static_cast<float>(lo) * 0.01f - 9.0f;
            const float high = static_cast<float>(hi) * 0.01f;
            Chunk c;
            const float half = static_cast<float>(kTerrainChunk) * 0.5f;
            c.center = {static_cast<float>(ox) + half, (low + high) * 0.5f, static_cast<float>(oz) + half};
            const float half_h = (high - low) * 0.5f;
            c.radius = std::sqrt(2.0f * half * half + half_h * half_h);
            c.water = wet;
            chunks_.push_back(c);
            gpu_chunks.push_back({{ox, oz, 0, 0}, {low, high, wet ? 1.0f : 0.0f, 0.0f}});
        }
    }
    chunk_buffer_ = upload(gpu_chunks.data(), static_cast<std::uint32_t>(gpu_chunks.size() * sizeof(GpuChunk)),
                           SDL_GPU_BUFFERUSAGE_GRAPHICS_STORAGE_READ);
    if (heights_ == nullptr || water_ == nullptr || colors_ == nullptr || chunk_buffer_ == nullptr) {
        log::error("terrain: cannot upload the map: {}", SDL_GetError());
        release_map();
        return false;
    }
    cells_ = n;
    color_size_ = data.color_size;
    log::info("terrain: {} x {} m in {} chunks", n, n, chunks_.size());
    return true;
}

bool TerrainLayer::prepare(SDL_GPUCommandBuffer* cmd, const math::Frustum& frustum, math::Vec3 eye,
                           float draw_distance) {
    stats_ = TerrainStats{};
    lists_.clear();
    for (int lod = 0; lod < kTerrainLods; ++lod) {
        ground_ranges_[lod] = {};
        water_ranges_[lod] = {};
    }
    if (cells_ == 0) {
        return true;
    }
    // Level of detail of each visible chunk (-1: not visible).
    std::vector<std::int8_t> chosen(chunks_.size(), -1);
    const float half = static_cast<float>(kTerrainChunk) * 0.5f;
    for (std::size_t i = 0; i < chunks_.size(); ++i) {
        const Chunk& c = chunks_[i];
        if (!frustum.sphere_visible(c.center, c.radius)) {
            continue;
        }
        // Distance from the eye to the chunk's box.
        const float dx = std::max(std::abs(eye.x - c.center.x) - half, 0.0f);
        const float dz = std::max(std::abs(eye.z - c.center.z) - half, 0.0f);
        const float horizontal = std::sqrt(dx * dx + dz * dz);
        if (horizontal > draw_distance) {
            continue;
        }
        const float dy = std::max(std::abs(eye.y - c.center.y) - (c.radius - half), 0.0f);
        chosen[i] = static_cast<std::int8_t>(terrain_lod_for_distance(std::sqrt(horizontal * horizontal + dy * dy)));
    }
    for (int lod = 0; lod < kTerrainLods; ++lod) {
        ground_ranges_[lod].first = static_cast<std::uint32_t>(lists_.size());
        for (std::size_t i = 0; i < chunks_.size(); ++i) {
            if (chosen[i] == lod) {
                lists_.push_back(static_cast<std::uint32_t>(i));
            }
        }
        ground_ranges_[lod].count = static_cast<std::uint32_t>(lists_.size()) - ground_ranges_[lod].first;
    }
    for (int lod = 0; lod <= kMaxWaterLod; ++lod) {
        water_ranges_[lod].first = static_cast<std::uint32_t>(lists_.size());
        for (std::size_t i = 0; i < chunks_.size(); ++i) {
            if (chosen[i] >= 0 && chunks_[i].water && std::min<int>(chosen[i], kMaxWaterLod) == lod) {
                lists_.push_back(static_cast<std::uint32_t>(i));
            }
        }
        water_ranges_[lod].count = static_cast<std::uint32_t>(lists_.size()) - water_ranges_[lod].first;
    }
    if (lists_.empty()) {
        return true;
    }

    const auto bytes = static_cast<std::uint32_t>(lists_.size() * sizeof(std::uint32_t));
    if (list_buffer_ == nullptr || list_capacity_ < bytes) {
        SDL_ReleaseGPUBuffer(device_, list_buffer_);
        SDL_GPUBufferCreateInfo info{};
        info.usage = SDL_GPU_BUFFERUSAGE_VERTEX;
        info.size = std::max<std::uint32_t>(bytes * 2, 16u * 1024u);
        list_buffer_ = SDL_CreateGPUBuffer(device_, &info);
        list_capacity_ = list_buffer_ != nullptr ? info.size : 0;
    }
    if (list_transfer_ == nullptr || list_transfer_capacity_ < bytes) {
        SDL_ReleaseGPUTransferBuffer(device_, list_transfer_);
        SDL_GPUTransferBufferCreateInfo info{};
        info.usage = SDL_GPU_TRANSFERBUFFERUSAGE_UPLOAD;
        info.size = std::max<std::uint32_t>(bytes * 2, 16u * 1024u);
        list_transfer_ = SDL_CreateGPUTransferBuffer(device_, &info);
        list_transfer_capacity_ = list_transfer_ != nullptr ? info.size : 0;
    }
    if (list_buffer_ == nullptr || list_transfer_ == nullptr) {
        log::error("terrain: cannot create the chunk lists: {}", SDL_GetError());
        lists_.clear();
        return false;
    }
    void* mapped = SDL_MapGPUTransferBuffer(device_, list_transfer_, true);
    if (mapped == nullptr) {
        lists_.clear();
        return false;
    }
    std::memcpy(mapped, lists_.data(), bytes);
    SDL_UnmapGPUTransferBuffer(device_, list_transfer_);
    SDL_GPUCopyPass* copy = SDL_BeginGPUCopyPass(cmd);
    const SDL_GPUTransferBufferLocation src{list_transfer_, 0};
    const SDL_GPUBufferRegion dst{list_buffer_, 0, bytes};
    SDL_UploadToGPUBuffer(copy, &src, &dst, true);
    SDL_EndGPUCopyPass(copy);
    return true;
}

void TerrainLayer::draw_ground(SDL_GPUCommandBuffer* cmd, SDL_GPURenderPass* pass, const math::Mat4& view_proj,
                               SDL_GPUTexture* detail, SDL_GPUSampler* detail_sampler, SDL_GPUTexture* shadow_map,
                               SDL_GPUSampler* shadow_sampler) {
    if (cells_ == 0 || lists_.empty() || ground_pipeline_ == nullptr) {
        return;
    }
    SDL_BindGPUGraphicsPipeline(pass, ground_pipeline_);
    const TerrainUniforms tu{view_proj, {cells_ + 1, cells_, 0, 0}};
    SDL_PushGPUVertexUniformData(cmd, 0, &tu, sizeof(tu));
    const SDL_GPUTextureSamplerBinding color_binding{colors_, color_sampler_};
    SDL_BindGPUVertexSamplers(pass, 0, &color_binding, 1);
    SDL_GPUBuffer* storage[2] = {heights_, chunk_buffer_};
    SDL_BindGPUVertexStorageBuffers(pass, 0, storage, 2);
    const SDL_GPUTextureSamplerBinding fragment[2] = {{detail, detail_sampler}, {shadow_map, shadow_sampler}};
    SDL_BindGPUFragmentSamplers(pass, 0, fragment, 2);
    const MaterialUniforms mu{{1.0f, 1.0f, 1.0f, 1.0f}};
    SDL_PushGPUFragmentUniformData(cmd, 1, &mu, sizeof(mu));
    // The color texture may be smaller than the map: fewer mip levels to skip.
    const int color_shrink = log2_int(cells_ / color_size_);
    for (int lod = 0; lod < kTerrainLods; ++lod) {
        const Range r = ground_ranges_[lod];
        if (r.count == 0) {
            continue;
        }
        const LodUniforms lu{{1 << lod, std::max(0, lod - color_shrink), 0, 0}};
        SDL_PushGPUVertexUniformData(cmd, 1, &lu, sizeof(lu));
        const Grid& g = grids_[lod];
        const SDL_GPUBufferBinding vbs[2] = {{g.vertices, 0}, {list_buffer_, r.first * 4u}};
        SDL_BindGPUVertexBuffers(pass, 0, vbs, 2);
        const SDL_GPUBufferBinding ib{g.indices, 0};
        SDL_BindGPUIndexBuffer(pass, &ib, SDL_GPU_INDEXELEMENTSIZE_16BIT);
        SDL_DrawGPUIndexedPrimitives(pass, g.index_count, r.count, 0, 0, 0);
        ++stats_.draw_calls;
        stats_.chunks_drawn += r.count;
        stats_.triangles += static_cast<std::uint64_t>(g.index_count / 3) * r.count;
    }
}

void TerrainLayer::draw_grass(SDL_GPUCommandBuffer* cmd, SDL_GPURenderPass* pass, const math::Mat4& view_proj,
                              math::Vec3 eye, float time, float distance, SDL_GPUTexture* white,
                              SDL_GPUSampler* sampler, SDL_GPUTexture* shadow_map, SDL_GPUSampler* shadow_sampler) {
    if (cells_ == 0 || grass_pipeline_ == nullptr || grass_mesh_.vertices == nullptr || distance <= 0.0f) {
        return;
    }
    // Nothing to see when the eye is far above the ground below it.
    const std::int32_t per_side = cells_ / kTerrainChunk;
    const std::int32_t cx = std::clamp(static_cast<std::int32_t>(eye.x) / kTerrainChunk, 0, per_side - 1);
    const std::int32_t cz = std::clamp(static_cast<std::int32_t>(eye.z) / kTerrainChunk, 0, per_side - 1);
    const Chunk& below = chunks_[static_cast<std::size_t>(cz * per_side + cx)];
    if (eye.y - (below.center.y + below.radius) > distance) {
        return;
    }
    const auto side = static_cast<std::int32_t>(std::ceil(2.0f * distance / kGrassSpacing));
    const float first_x = std::floor((eye.x - distance) / kGrassSpacing) * kGrassSpacing;
    const float first_z = std::floor((eye.z - distance) / kGrassSpacing) * kGrassSpacing;
    GrassUniforms gu{};
    gu.view_proj = view_proj;
    gu.map[0] = cells_ + 1;
    gu.map[1] = cells_;
    gu.map[2] = side;
    gu.grid[0] = first_x;
    gu.grid[1] = first_z;
    gu.grid[2] = kGrassSpacing;
    gu.grid[3] = distance;
    set4(gu.camera, eye, time);
    SDL_BindGPUGraphicsPipeline(pass, grass_pipeline_);
    SDL_PushGPUVertexUniformData(cmd, 0, &gu, sizeof(gu));
    const SDL_GPUTextureSamplerBinding color_binding{colors_, color_sampler_};
    SDL_BindGPUVertexSamplers(pass, 0, &color_binding, 1);
    SDL_GPUBuffer* storage[2] = {heights_, water_};
    SDL_BindGPUVertexStorageBuffers(pass, 0, storage, 2);
    const SDL_GPUTextureSamplerBinding fragment[2] = {{white, sampler}, {shadow_map, shadow_sampler}};
    SDL_BindGPUFragmentSamplers(pass, 0, fragment, 2);
    const MaterialUniforms mu{{1.0f, 1.0f, 1.0f, 1.0f}};
    SDL_PushGPUFragmentUniformData(cmd, 1, &mu, sizeof(mu));
    const SDL_GPUBufferBinding vb{grass_mesh_.vertices, 0};
    SDL_BindGPUVertexBuffers(pass, 0, &vb, 1);
    const SDL_GPUBufferBinding ib{grass_mesh_.indices, 0};
    SDL_BindGPUIndexBuffer(pass, &ib, SDL_GPU_INDEXELEMENTSIZE_16BIT);
    const auto count = static_cast<std::uint32_t>(side * side);
    SDL_DrawGPUIndexedPrimitives(pass, grass_mesh_.index_count, count, 0, 0, 0);
    ++stats_.draw_calls;
    stats_.grass_tufts = count;
    stats_.triangles += static_cast<std::uint64_t>(grass_mesh_.index_count / 3) * count;
}

void TerrainLayer::draw_water(SDL_GPUCommandBuffer* cmd, SDL_GPURenderPass* pass, const math::Mat4& view_proj,
                              const WaterLook& look) {
    if (cells_ == 0 || lists_.empty() || water_pipeline_ == nullptr) {
        return;
    }
    bool any = false;
    for (const Range& r : water_ranges_) {
        any = any || r.count > 0;
    }
    if (!any) {
        return;
    }
    SDL_BindGPUGraphicsPipeline(pass, water_pipeline_);
    const TerrainUniforms tu{view_proj, {cells_ + 1, cells_, 0, 0}};
    SDL_PushGPUVertexUniformData(cmd, 0, &tu, sizeof(tu));
    SDL_GPUBuffer* storage[3] = {heights_, water_, chunk_buffer_};
    SDL_BindGPUVertexStorageBuffers(pass, 0, storage, 3);
    WaterUniforms wu{};
    set4(wu.sun_direction, look.sun_direction, 0.0f);
    set4(wu.sun_color, look.sun_color, 1.0f);
    set4(wu.fog_color, look.fog_color, look.fog_density);
    set4(wu.camera_position, look.eye, look.time);
    set4(wu.shallow_color, {0.10f, 0.32f, 0.34f}, 1.0f);
    set4(wu.deep_color, {0.02f, 0.10f, 0.16f}, 1.0f);
    SDL_PushGPUFragmentUniformData(cmd, 0, &wu, sizeof(wu));
    for (int lod = 0; lod <= kMaxWaterLod; ++lod) {
        const Range r = water_ranges_[lod];
        if (r.count == 0) {
            continue;
        }
        const Grid& g = grids_[lod];
        const SDL_GPUBufferBinding vbs[2] = {{g.vertices, 0}, {list_buffer_, r.first * 4u}};
        SDL_BindGPUVertexBuffers(pass, 0, vbs, 2);
        const SDL_GPUBufferBinding ib{g.indices, 0};
        SDL_BindGPUIndexBuffer(pass, &ib, SDL_GPU_INDEXELEMENTSIZE_16BIT);
        SDL_DrawGPUIndexedPrimitives(pass, g.index_count, r.count, 0, 0, 0);
        ++stats_.draw_calls;
        stats_.water_chunks_drawn += r.count;
        stats_.triangles += static_cast<std::uint64_t>(g.index_count / 3) * r.count;
    }
}

}  // namespace sc::render
