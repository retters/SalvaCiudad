#include "render/scene_renderer.h"

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstring>

#include <SDL3/SDL_error.h>

#include "core/log.h"
#include "shaders/blur_frag_dxil.h"
#include "shaders/mesh_frag_dxil.h"
#include "shaders/mesh_vert_dxil.h"
#include "shaders/shadow_frag_dxil.h"
#include "shaders/shadow_vert_dxil.h"
#include "shaders/skinned_shadow_vert_dxil.h"
#include "shaders/skinned_vert_dxil.h"
#include "shaders/sky_frag_dxil.h"
#include "shaders/sky_vert_dxil.h"

namespace sc::render {

namespace {

constexpr int kMaxCascades = 3;

// GPU layout of an instance; matches InstanceData in scene_common.hlsli.
struct GpuInstance {
    float row0[4];
    float row1[4];
    float row2[4];
    float tint[4];
};
static_assert(sizeof(GpuInstance) == 64);

// Vertex of an animated model; matches the skinned shaders' input.
struct SkinnedVertex {
    float px, py, pz;
    float nx, ny, nz;
    float u, v;
    std::uint8_t joints[4];
    std::uint8_t weights[4];
};
static_assert(sizeof(SkinnedVertex) == 40);

// Matches CharacterData in skinning.hlsli.
struct GpuCharacter {
    float row0[4];
    float row1[4];
    float row2[4];
    std::uint32_t anim[4];  // First bone matrix of the clip, frames, joints, palette.
    float extra[4];         // Frame position.
};
static_assert(sizeof(GpuCharacter) == 80);

struct DrawUniforms {
    std::int32_t draw[4];  // Palette slot, or -1.
};

// Matches MeshDrawUniforms in mesh.vert.hlsl.
struct MeshDrawUniforms {
    std::int32_t draw[4];   // Building palette slot of this primitive, or -1.
    float base_color[4];    // Its material color, which the palette replaces.
};

// Material names recolored per character, in palette slot order.
constexpr const char* kPaletteSlotNames[kPaletteSlots] = {"skin", "hair", "top", "bottom", "shoes", "belt", "hat", "apron"};

int palette_slot(const std::string& material) {
    for (std::size_t i = 0; i < kPaletteSlots; ++i) {
        if (material == kPaletteSlotNames[i]) {
            return static_cast<int>(i);
        }
    }
    return -1;
}

// Material names recolored per building, in slot order.
constexpr const char* kBuildingSlotNames[kBuildingPaletteSlots] = {"var_roof", "var_roof_dark", "var_walls",
                                                                   "var_shutter"};

int building_slot(const std::string& material) {
    for (std::size_t i = 0; i < kBuildingPaletteSlots; ++i) {
        if (material == kBuildingSlotNames[i]) {
            return static_cast<int>(i);
        }
    }
    return -1;
}

void affine_rows(math::Vec3 p, float yaw, float scale, float row0[4], float row1[4], float row2[4]) {
    const float c = std::cos(yaw) * scale;
    const float s = std::sin(yaw) * scale;
    row0[0] = c;
    row0[1] = 0.0f;
    row0[2] = s;
    row0[3] = p.x;
    row1[0] = 0.0f;
    row1[1] = scale;
    row1[2] = 0.0f;
    row1[3] = p.y;
    row2[0] = -s;
    row2[1] = 0.0f;
    row2[2] = c;
    row2[3] = p.z;
}

struct MeshVertexUniforms {
    math::Mat4 view_proj;
};

struct SceneUniforms {
    math::Mat4 cascade_matrix[kMaxCascades];
    float cascade_split[4];
    float sun_direction[4];
    float sun_color[4];
    float sky_ambient[4];
    float ground_ambient[4];
    float fog_color[4];
    float camera_position[4];
    float shadow_params[4];
    float war_params[4];
};

// A rectangle of fog-of-war texels waiting to go to the GPU.
struct WarUpload {
    bool ceiling = false;             // The ceiling texture (2 bytes a texel), else the fog (1).
    std::uint32_t x = 0, z = 0, w = 0, d = 0;
    std::vector<std::uint8_t> bytes;  // Row by row, w * d texels.
};

std::uint32_t align_up(std::uint32_t v, std::uint32_t a) {
    return (v + a - 1) / a * a;
}

struct MaterialUniforms {
    float base_color[4];
};

struct SkyUniforms {
    math::Mat4 inverse_view_proj;
    float sun_direction[4];
    float zenith_color[4];
    float horizon_color[4];
    float sun_color[4];
};

void set4(float out[4], math::Vec3 v, float w) {
    out[0] = v.x;
    out[1] = v.y;
    out[2] = v.z;
    out[3] = w;
}

SDL_GPUSampleCount to_sample_count(int samples) {
    switch (samples) {
        case 8: return SDL_GPU_SAMPLECOUNT_8;
        case 4: return SDL_GPU_SAMPLECOUNT_4;
        case 2: return SDL_GPU_SAMPLECOUNT_2;
        default: return SDL_GPU_SAMPLECOUNT_1;
    }
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
        log::error("scene: SDL_CreateGPUShader failed: {}", SDL_GetError());
    }
    return shader;
}

struct GpuMaterial {
    float base_color[4] = {1, 1, 1, 1};
    SDL_GPUTexture* texture = nullptr;  // Not owned; points into GpuModel::textures or the white texture.
};

// Instances of a model grouped by 64 m region, and regions by groups of
// 16 x 16, so culling can skip whole regions and groups at once (a
// colossal map has 65 536 regions).
constexpr float kBucketSize = 64.0f;
constexpr std::int64_t kBucketsPerGroup = 16;

struct Bucket {
    std::uint32_t first = 0;  // Index into the model's instances.
    std::uint32_t count = 0;
    math::Vec3 center;
    float radius = 0.0f;
};

struct BucketGroup {
    std::uint32_t first = 0;  // Index into the model's buckets.
    std::uint32_t count = 0;
    math::Vec3 center;
    float radius = 0.0f;
};

std::int64_t floor_div(std::int64_t a, std::int64_t b) {
    return a >= 0 ? a / b : -((-a + b - 1) / b);
}

struct GpuModel {
    SDL_GPUBuffer* vertices = nullptr;
    SDL_GPUBuffer* indices = nullptr;
    std::vector<ModelPrimitive> primitives;
    std::vector<GpuMaterial> materials;
    std::vector<int> slots;  // Building palette slot of each material, or -1.
    std::vector<SDL_GPUTexture*> textures;
    float radius = 1.0f;
    std::uint64_t triangles = 0;
    std::vector<Instance> instances;     // In the caller's order.
    std::vector<std::uint32_t> order;    // Region-sorted position -> index in `instances`.
    std::vector<std::uint32_t> slot_of;  // Index in `instances` -> region-sorted position.
    std::vector<Bucket> buckets;
    std::vector<BucketGroup> groups;
    std::uint32_t base = 0;              // First slot in the GPU instance buffer.
    std::uint32_t capacity = 0;          // Slots reserved there.
    bool dirty = true;                   // Whole range must be rebuilt.
    std::vector<std::uint32_t> changed;  // Sorted positions updated one by one.
    ModelClass model_class = ModelClass::Normal;
};

struct Range {
    std::uint32_t first = 0;
    std::uint32_t count = 0;
};

struct ClipInfo {
    std::uint32_t first = 0;  // Matrix index relative to the model's base.
    std::uint32_t frames = 1;
    float fps = 30.0f;
};

// A body or an accessory; accessories borrow the body's bones and clips.
struct GpuSkinned {
    SDL_GPUBuffer* vertices = nullptr;
    SDL_GPUBuffer* indices = nullptr;
    std::vector<ModelPrimitive> primitives;
    std::vector<GpuMaterial> materials;
    std::vector<int> slots;  // Palette slot per material, or -1.
    float radius = 1.0f;
    std::uint64_t triangles = 0;
    std::uint32_t body = 0;              // Itself for a body.
    std::uint32_t accessory_bit = ~0u;   // ~0 for a body.
    // Body only:
    std::uint32_t joint_count = 0;
    std::uint32_t bone_base = 0;
    std::vector<ClipInfo> clips;
    std::vector<std::string> clip_names;
    std::vector<std::string> joint_names;
    std::vector<math::Vec3> joint_rest_positions;
    std::uint32_t accessory_count = 0;
};

}  // namespace

float draw_distance_for_level(int level) {
    constexpr float kDistances[] = {300.0f, 600.0f, 1200.0f, 2500.0f};
    return kDistances[std::clamp(level, 0, 3)];
}

float vegetation_distance_for_level(int level) {
    constexpr float kDistances[] = {70.0f, 130.0f, 220.0f, 350.0f};
    return kDistances[std::clamp(level, 0, 3)];
}

float grass_distance_for_level(int level) {
    constexpr float kDistances[] = {20.0f, 35.0f, 50.0f, 70.0f};
    return kDistances[std::clamp(level, 0, 3)];
}

int shadow_cascades_for_level(int level) {
    return std::clamp(level, 0, 3);
}

int shadow_map_size_for_level(int level) {
    constexpr int kSizes[] = {0, 1024, 2048, 2048};
    return kSizes[std::clamp(level, 0, 3)];
}

float shadow_distance_for_level(int level) {
    constexpr float kDistances[] = {0.0f, 120.0f, 250.0f, 400.0f};
    return kDistances[std::clamp(level, 0, 3)];
}

int msaa_samples_for_level(int level) {
    constexpr int kSamples[] = {1, 2, 4, 8};
    return kSamples[std::clamp(level, 0, 3)];
}

void compute_cascade_splits(float near_z, float max_distance, int count, float out[3]) {
    constexpr float kLambda = 0.75f;  // 1 = fully logarithmic.
    for (int i = 0; i < kMaxCascades; ++i) {
        out[i] = max_distance;
    }
    for (int i = 1; i <= count; ++i) {
        const float t = static_cast<float>(i) / static_cast<float>(count);
        const float log_split = near_z * std::pow(max_distance / near_z, t);
        const float uniform_split = near_z + (max_distance - near_z) * t;
        out[i - 1] = math::lerp(uniform_split, log_split, kLambda);
    }
}

struct SceneRenderer::Impl {
    SDL_GPUDevice* device = nullptr;
    SDL_GPUTextureFormat swapchain_format = SDL_GPU_TEXTUREFORMAT_INVALID;
    SDL_GPUTextureFormat depth_format = SDL_GPU_TEXTUREFORMAT_D32_FLOAT;

    SDL_GPUGraphicsPipeline* mesh_pipeline = nullptr;
    SDL_GPUGraphicsPipeline* sky_pipeline = nullptr;
    SDL_GPUGraphicsPipeline* shadow_pipeline = nullptr;
    SDL_GPUSampler* base_sampler = nullptr;
    SDL_GPUSampler* shadow_sampler = nullptr;
    SDL_GPUTexture* white = nullptr;
    SDL_GPUTexture* shadow_map = nullptr;
    SDL_GPUTexture* color_msaa = nullptr;
    SDL_GPUTexture* depth = nullptr;
    // Pause blur: the scene goes to post_a, is blurred across into post_b
    // and down into the swapchain.
    SDL_GPUGraphicsPipeline* blur_pipeline = nullptr;
    SDL_GPUSampler* clamp_sampler = nullptr;
    SDL_GPUTexture* post_a = nullptr;
    SDL_GPUTexture* post_b = nullptr;
    std::uint32_t post_w = 0;
    std::uint32_t post_h = 0;
    std::uint32_t target_w = 0;
    std::uint32_t target_h = 0;

    SDL_GPUBuffer* instance_buffer = nullptr;  // Storage: all instances.
    std::uint32_t instance_capacity = 0;
    bool layout_dirty = true;   // Some model outgrew its room: lay out again.
    bool full_upload = true;    // The whole instance buffer must be sent.
    SDL_GPUBuffer* visible_buffer = nullptr;   // Vertex: visible indices.
    std::uint32_t visible_capacity = 0;
    SDL_GPUTransferBuffer* transfer = nullptr;
    std::uint32_t transfer_capacity = 0;

    std::vector<GpuModel> models;
    std::vector<std::uint32_t> visible;  // Global instance indices.
    std::vector<GpuInstance> gpu_instances;

    // Characters.
    SDL_GPUGraphicsPipeline* skinned_pipeline = nullptr;
    SDL_GPUGraphicsPipeline* skinned_shadow_pipeline = nullptr;
    std::vector<GpuSkinned> skinned;
    std::vector<float> bone_rows;  // Three float4 rows per matrix.
    bool bones_dirty = false;
    SDL_GPUBuffer* bone_buffer = nullptr;
    std::uint32_t bone_capacity = 0;
    std::vector<float> palette_data = std::vector<float>(kPaletteSlots * 4, 1.0f);
    bool palettes_dirty = true;
    SDL_GPUBuffer* palette_buffer = nullptr;
    std::uint32_t palette_capacity = 0;
    // Always room for every palette an instance can name, so the shader
    // never reads past the end.
    std::vector<float> building_palette_data =
        std::vector<float>(std::size_t{kMaxBuildingPalettes} * kBuildingPaletteSlots * 4, 1.0f);
    bool building_palettes_dirty = true;
    SDL_GPUBuffer* building_palette_buffer = nullptr;
    std::uint32_t building_palette_capacity = 0;
    std::vector<CharacterInstance> characters;
    std::vector<GpuCharacter> gpu_characters;
    SDL_GPUBuffer* character_buffer = nullptr;
    std::uint32_t character_capacity = 0;

    GraphicsSettings graphics;
    int samples = 1;
    int cascades = 0;
    int shadow_size = 0;
    float draw_distance = 1200.0f;
    float vegetation_distance = 220.0f;
    float draw_distance_now = 1200.0f;  // This frame's draw distance (models).

    TerrainLayer terrain;

    // Fog of war (phase 32) and its ceiling (phase 34).
    SDL_GPUTexture* war_fog = nullptr;
    SDL_GPUTexture* war_ceiling = nullptr;
    int war_mode = 0;
    std::int32_t war_side = 0;
    std::int32_t war_ceiling_side = 0;
    float war_meters = 1.0f;  // Meters both textures span per side.
    float war_band = 0.0f;
    std::vector<WarUpload> war_uploads;

    void release_war() {
        SDL_ReleaseGPUTexture(device, war_fog);
        SDL_ReleaseGPUTexture(device, war_ceiling);
        war_fog = war_ceiling = nullptr;
        war_mode = 0;
        war_side = war_ceiling_side = 0;
        war_band = 0.0f;
        war_uploads.clear();
    }

    SDL_GPUTexture* make_war_texture(std::int32_t side, SDL_GPUTextureFormat format) {
        SDL_GPUTextureCreateInfo info{};
        info.type = SDL_GPU_TEXTURETYPE_2D;
        info.format = format;
        info.usage = SDL_GPU_TEXTUREUSAGE_SAMPLER;
        info.width = info.height = static_cast<std::uint32_t>(side);
        info.layer_count_or_depth = 1;
        info.num_levels = 1;
        SDL_GPUTexture* t = SDL_CreateGPUTexture(device, &info);
        if (t == nullptr) {
            log::error("scene: cannot create a fog of war texture: {}", SDL_GetError());
        }
        return t;
    }

    // The fog of war and its ceiling for the lit shaders; white (in sight,
    // no ceiling) when there is none.
    [[nodiscard]] std::array<SDL_GPUTextureSamplerBinding, 2> war_bindings() const {
        return {SDL_GPUTextureSamplerBinding{war_fog != nullptr ? war_fog : white, clamp_sampler},
                SDL_GPUTextureSamplerBinding{war_ceiling != nullptr ? war_ceiling : white, clamp_sampler}};
    }

    void war_params(float out[4]) const {
        const bool on = war_fog != nullptr && war_mode > 0;
        out[0] = 1.0f / std::max(1.0f, war_meters);
        out[1] = on ? static_cast<float>(war_mode) : 0.0f;
        out[2] = on && war_ceiling != nullptr ? war_band : 0.0f;
        out[3] = 0.0f;
    }

    ~Impl() { release_all(); }

    void release_post() {
        SDL_ReleaseGPUTexture(device, post_a);
        SDL_ReleaseGPUTexture(device, post_b);
        post_a = post_b = nullptr;
        post_w = post_h = 0;
    }

    bool ensure_post(std::uint32_t w, std::uint32_t h) {
        if (w == post_w && h == post_h && post_a != nullptr) {
            return true;
        }
        release_post();
        SDL_GPUTextureCreateInfo info{};
        info.type = SDL_GPU_TEXTURETYPE_2D;
        info.width = w;
        info.height = h;
        info.layer_count_or_depth = 1;
        info.num_levels = 1;
        info.sample_count = SDL_GPU_SAMPLECOUNT_1;
        info.format = swapchain_format;
        info.usage = SDL_GPU_TEXTUREUSAGE_COLOR_TARGET | SDL_GPU_TEXTUREUSAGE_SAMPLER;
        post_a = SDL_CreateGPUTexture(device, &info);
        post_b = SDL_CreateGPUTexture(device, &info);
        if (post_a == nullptr || post_b == nullptr) {
            log::warn("scene: cannot create the blur targets: {}", SDL_GetError());
            release_post();
            return false;
        }
        post_w = w;
        post_h = h;
        return true;
    }

    void release_targets() {
        release_post();
        SDL_ReleaseGPUTexture(device, color_msaa);
        SDL_ReleaseGPUTexture(device, depth);
        color_msaa = nullptr;
        depth = nullptr;
        target_w = target_h = 0;
    }

    void release_pipelines() {
        SDL_ReleaseGPUGraphicsPipeline(device, mesh_pipeline);
        SDL_ReleaseGPUGraphicsPipeline(device, sky_pipeline);
        SDL_ReleaseGPUGraphicsPipeline(device, shadow_pipeline);
        SDL_ReleaseGPUGraphicsPipeline(device, skinned_pipeline);
        SDL_ReleaseGPUGraphicsPipeline(device, skinned_shadow_pipeline);
        SDL_ReleaseGPUGraphicsPipeline(device, blur_pipeline);
        blur_pipeline = nullptr;
        mesh_pipeline = sky_pipeline = shadow_pipeline = nullptr;
        skinned_pipeline = skinned_shadow_pipeline = nullptr;
    }

    void release_all() {
        if (device == nullptr) {
            return;
        }
        release_targets();
        release_pipelines();
        release_war();
        terrain.release();
        for (GpuModel& m : models) {
            SDL_ReleaseGPUBuffer(device, m.vertices);
            SDL_ReleaseGPUBuffer(device, m.indices);
            for (SDL_GPUTexture* t : m.textures) {
                SDL_ReleaseGPUTexture(device, t);
            }
        }
        models.clear();
        for (GpuSkinned& m : skinned) {
            SDL_ReleaseGPUBuffer(device, m.vertices);
            SDL_ReleaseGPUBuffer(device, m.indices);
        }
        skinned.clear();
        SDL_ReleaseGPUBuffer(device, bone_buffer);
        SDL_ReleaseGPUBuffer(device, palette_buffer);
        SDL_ReleaseGPUBuffer(device, character_buffer);
        SDL_ReleaseGPUBuffer(device, building_palette_buffer);
        bone_buffer = palette_buffer = character_buffer = building_palette_buffer = nullptr;
        bone_capacity = palette_capacity = character_capacity = building_palette_capacity = 0;
        building_palettes_dirty = true;
        SDL_ReleaseGPUSampler(device, base_sampler);
        SDL_ReleaseGPUSampler(device, shadow_sampler);
        SDL_ReleaseGPUSampler(device, clamp_sampler);
        clamp_sampler = nullptr;
        SDL_ReleaseGPUTexture(device, white);
        SDL_ReleaseGPUTexture(device, shadow_map);
        SDL_ReleaseGPUBuffer(device, instance_buffer);
        SDL_ReleaseGPUBuffer(device, visible_buffer);
        SDL_ReleaseGPUTransferBuffer(device, transfer);
        base_sampler = shadow_sampler = nullptr;
        white = shadow_map = nullptr;
        instance_buffer = visible_buffer = nullptr;
        transfer = nullptr;
        instance_capacity = visible_capacity = transfer_capacity = 0;
        device = nullptr;
    }

    // --- Upload helpers ---------------------------------------------------

    bool ensure_transfer(std::uint32_t size) {
        if (transfer != nullptr && transfer_capacity >= size) {
            return true;
        }
        SDL_ReleaseGPUTransferBuffer(device, transfer);
        SDL_GPUTransferBufferCreateInfo info{};
        info.usage = SDL_GPU_TRANSFERBUFFERUSAGE_UPLOAD;
        info.size = std::max<std::uint32_t>(size, 1u << 20) * 2;
        transfer = SDL_CreateGPUTransferBuffer(device, &info);
        transfer_capacity = transfer != nullptr ? info.size : 0;
        if (transfer == nullptr) {
            log::error("scene: SDL_CreateGPUTransferBuffer failed: {}", SDL_GetError());
        }
        return transfer != nullptr;
    }

    bool ensure_buffer(SDL_GPUBuffer*& buffer, std::uint32_t& capacity, std::uint32_t size, SDL_GPUBufferUsageFlags usage) {
        if (buffer != nullptr && capacity >= size) {
            return true;
        }
        SDL_ReleaseGPUBuffer(device, buffer);
        SDL_GPUBufferCreateInfo info{};
        info.usage = usage;
        info.size = std::max<std::uint32_t>(size, 64u * 1024u) * 2;
        buffer = SDL_CreateGPUBuffer(device, &info);
        capacity = buffer != nullptr ? info.size : 0;
        if (buffer == nullptr) {
            log::error("scene: SDL_CreateGPUBuffer failed: {}", SDL_GetError());
        }
        return buffer != nullptr;
    }

    // One-off upload in its own command buffer (used when loading models).
    SDL_GPUBuffer* upload_static_buffer(const void* data, std::uint32_t size, SDL_GPUBufferUsageFlags usage) {
        SDL_GPUBufferCreateInfo info{};
        info.usage = usage;
        info.size = size;
        SDL_GPUBuffer* buffer = SDL_CreateGPUBuffer(device, &info);
        if (buffer == nullptr || !ensure_transfer(size)) {
            SDL_ReleaseGPUBuffer(device, buffer);
            return nullptr;
        }
        void* mapped = SDL_MapGPUTransferBuffer(device, transfer, true);
        if (mapped == nullptr) {
            SDL_ReleaseGPUBuffer(device, buffer);
            return nullptr;
        }
        std::memcpy(mapped, data, size);
        SDL_UnmapGPUTransferBuffer(device, transfer);
        SDL_GPUCommandBuffer* cmd = SDL_AcquireGPUCommandBuffer(device);
        if (cmd == nullptr) {
            SDL_ReleaseGPUBuffer(device, buffer);
            return nullptr;
        }
        SDL_GPUCopyPass* copy = SDL_BeginGPUCopyPass(cmd);
        const SDL_GPUTransferBufferLocation src{transfer, 0};
        const SDL_GPUBufferRegion dst{buffer, 0, size};
        SDL_UploadToGPUBuffer(copy, &src, &dst, false);
        SDL_EndGPUCopyPass(copy);
        if (!SDL_SubmitGPUCommandBuffer(cmd)) {
            SDL_ReleaseGPUBuffer(device, buffer);
            return nullptr;
        }
        return buffer;
    }

    SDL_GPUTexture* upload_texture(const ModelTexture& tex) {
        std::uint32_t levels = 1;
        for (int s = std::max(tex.width, tex.height); s > 1; s /= 2) {
            ++levels;
        }
        SDL_GPUTextureCreateInfo info{};
        info.type = SDL_GPU_TEXTURETYPE_2D;
        info.format = SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM_SRGB;
        info.usage = SDL_GPU_TEXTUREUSAGE_SAMPLER | SDL_GPU_TEXTUREUSAGE_COLOR_TARGET;
        info.width = static_cast<std::uint32_t>(tex.width);
        info.height = static_cast<std::uint32_t>(tex.height);
        info.layer_count_or_depth = 1;
        info.num_levels = levels;
        SDL_GPUTexture* texture = SDL_CreateGPUTexture(device, &info);
        const auto size = static_cast<std::uint32_t>(tex.rgba.size());
        if (texture == nullptr || !ensure_transfer(size)) {
            log::error("scene: cannot create a model texture: {}", SDL_GetError());
            SDL_ReleaseGPUTexture(device, texture);
            return nullptr;
        }
        void* mapped = SDL_MapGPUTransferBuffer(device, transfer, true);
        if (mapped == nullptr) {
            SDL_ReleaseGPUTexture(device, texture);
            return nullptr;
        }
        std::memcpy(mapped, tex.rgba.data(), size);
        SDL_UnmapGPUTransferBuffer(device, transfer);
        SDL_GPUCommandBuffer* cmd = SDL_AcquireGPUCommandBuffer(device);
        if (cmd == nullptr) {
            SDL_ReleaseGPUTexture(device, texture);
            return nullptr;
        }
        SDL_GPUCopyPass* copy = SDL_BeginGPUCopyPass(cmd);
        SDL_GPUTextureTransferInfo src{};
        src.transfer_buffer = transfer;
        src.pixels_per_row = info.width;
        src.rows_per_layer = info.height;
        SDL_GPUTextureRegion dst{};
        dst.texture = texture;
        dst.w = info.width;
        dst.h = info.height;
        dst.d = 1;
        SDL_UploadToGPUTexture(copy, &src, &dst, false);
        SDL_EndGPUCopyPass(copy);
        if (levels > 1) {
            SDL_GenerateMipmapsForGPUTexture(cmd, texture);
        }
        if (!SDL_SubmitGPUCommandBuffer(cmd)) {
            SDL_ReleaseGPUTexture(device, texture);
            return nullptr;
        }
        return texture;
    }

    // --- Resources that depend on the settings ----------------------------

    bool create_shadow_map() {
        SDL_ReleaseGPUTexture(device, shadow_map);
        SDL_GPUTextureCreateInfo info{};
        info.type = SDL_GPU_TEXTURETYPE_2D_ARRAY;
        info.format = depth_format;
        info.usage = SDL_GPU_TEXTUREUSAGE_DEPTH_STENCIL_TARGET | SDL_GPU_TEXTUREUSAGE_SAMPLER;
        // With shadows off, a 1x1 map keeps the shader binding valid.
        info.width = info.height = static_cast<std::uint32_t>(std::max(1, shadow_size));
        info.layer_count_or_depth = static_cast<std::uint32_t>(std::max(1, cascades));
        info.num_levels = 1;
        shadow_map = SDL_CreateGPUTexture(device, &info);
        if (shadow_map == nullptr) {
            log::error("scene: cannot create the shadow map: {}", SDL_GetError());
        }
        return shadow_map != nullptr;
    }

    bool create_pipelines() {
        release_pipelines();
        SDL_GPUShader* mesh_vs = make_shader(device, kMeshVertDxil, kMeshVertDxil_size, SDL_GPU_SHADERSTAGE_VERTEX, 0, 2, 2);
        SDL_GPUShader* mesh_fs = make_shader(device, kMeshFragDxil, kMeshFragDxil_size, SDL_GPU_SHADERSTAGE_FRAGMENT, 4, 0, 2);
        SDL_GPUShader* sky_vs = make_shader(device, kSkyVertDxil, kSkyVertDxil_size, SDL_GPU_SHADERSTAGE_VERTEX, 0, 0, 0);
        SDL_GPUShader* sky_fs = make_shader(device, kSkyFragDxil, kSkyFragDxil_size, SDL_GPU_SHADERSTAGE_FRAGMENT, 0, 0, 1);
        SDL_GPUShader* shadow_vs = make_shader(device, kShadowVertDxil, kShadowVertDxil_size, SDL_GPU_SHADERSTAGE_VERTEX, 0, 1, 1);
        SDL_GPUShader* shadow_fs = make_shader(device, kShadowFragDxil, kShadowFragDxil_size, SDL_GPU_SHADERSTAGE_FRAGMENT, 0, 0, 0);
        SDL_GPUShader* skinned_vs = make_shader(device, kSkinnedVertDxil, kSkinnedVertDxil_size, SDL_GPU_SHADERSTAGE_VERTEX, 0, 3, 2);
        SDL_GPUShader* skinned_shadow_vs =
            make_shader(device, kSkinnedShadowVertDxil, kSkinnedShadowVertDxil_size, SDL_GPU_SHADERSTAGE_VERTEX, 0, 2, 1);
        SDL_GPUShader* blur_fs = make_shader(device, kBlurFragDxil, kBlurFragDxil_size, SDL_GPU_SHADERSTAGE_FRAGMENT, 1, 0, 1);
        const bool shaders_ok =
            mesh_vs && mesh_fs && sky_vs && sky_fs && shadow_vs && shadow_fs && skinned_vs && skinned_shadow_vs;

        SDL_GPUVertexBufferDescription buffers[2]{};
        buffers[0] = {0, sizeof(ModelVertex), SDL_GPU_VERTEXINPUTRATE_VERTEX, 0};
        buffers[1] = {1, sizeof(std::uint32_t), SDL_GPU_VERTEXINPUTRATE_INSTANCE, 0};
        SDL_GPUVertexAttribute attrs[4]{};
        attrs[0] = {0, 0, SDL_GPU_VERTEXELEMENTFORMAT_FLOAT3, offsetof(ModelVertex, px)};
        attrs[1] = {1, 0, SDL_GPU_VERTEXELEMENTFORMAT_FLOAT3, offsetof(ModelVertex, nx)};
        attrs[2] = {2, 0, SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2, offsetof(ModelVertex, u)};
        attrs[3] = {3, 1, SDL_GPU_VERTEXELEMENTFORMAT_UINT, 0};

        SDL_GPUColorTargetDescription color{};
        color.format = swapchain_format;

        if (shaders_ok) {
            SDL_GPUGraphicsPipelineCreateInfo pi{};
            pi.vertex_shader = mesh_vs;
            pi.fragment_shader = mesh_fs;
            pi.vertex_input_state = {buffers, 2, attrs, 4};
            pi.primitive_type = SDL_GPU_PRIMITIVETYPE_TRIANGLELIST;
            pi.rasterizer_state.cull_mode = SDL_GPU_CULLMODE_BACK;
            pi.rasterizer_state.front_face = SDL_GPU_FRONTFACE_COUNTER_CLOCKWISE;
            pi.multisample_state.sample_count = to_sample_count(samples);
            pi.depth_stencil_state.enable_depth_test = true;
            pi.depth_stencil_state.enable_depth_write = true;
            pi.depth_stencil_state.compare_op = SDL_GPU_COMPAREOP_GREATER;  // Reversed Z.
            pi.target_info.color_target_descriptions = &color;
            pi.target_info.num_color_targets = 1;
            pi.target_info.depth_stencil_format = depth_format;
            pi.target_info.has_depth_stencil_target = true;
            mesh_pipeline = SDL_CreateGPUGraphicsPipeline(device, &pi);

            SDL_GPUGraphicsPipelineCreateInfo si{};
            si.vertex_shader = sky_vs;
            si.fragment_shader = sky_fs;
            si.primitive_type = SDL_GPU_PRIMITIVETYPE_TRIANGLELIST;
            si.multisample_state.sample_count = to_sample_count(samples);
            si.target_info = pi.target_info;
            sky_pipeline = SDL_CreateGPUGraphicsPipeline(device, &si);

            SDL_GPUGraphicsPipelineCreateInfo sh{};
            sh.vertex_shader = shadow_vs;
            sh.fragment_shader = shadow_fs;
            sh.vertex_input_state = {buffers, 2, attrs, 4};
            sh.primitive_type = SDL_GPU_PRIMITIVETYPE_TRIANGLELIST;
            // Both faces cast shadows, so thin and open meshes do too.
            sh.rasterizer_state.cull_mode = SDL_GPU_CULLMODE_NONE;
            sh.rasterizer_state.enable_depth_bias = true;
            sh.rasterizer_state.depth_bias_constant_factor = -2.0f;  // Reversed Z: push away from the sun.
            sh.rasterizer_state.depth_bias_slope_factor = -2.5f;
            sh.depth_stencil_state.enable_depth_test = true;
            sh.depth_stencil_state.enable_depth_write = true;
            sh.depth_stencil_state.compare_op = SDL_GPU_COMPAREOP_GREATER;
            sh.target_info.depth_stencil_format = depth_format;
            sh.target_info.has_depth_stencil_target = true;
            shadow_pipeline = SDL_CreateGPUGraphicsPipeline(device, &sh);

            // Characters: the skinned vertex layout, same lighting.
            SDL_GPUVertexBufferDescription sbuffers[2]{};
            sbuffers[0] = {0, sizeof(SkinnedVertex), SDL_GPU_VERTEXINPUTRATE_VERTEX, 0};
            sbuffers[1] = {1, sizeof(std::uint32_t), SDL_GPU_VERTEXINPUTRATE_INSTANCE, 0};
            SDL_GPUVertexAttribute sattrs[6]{};
            sattrs[0] = {0, 0, SDL_GPU_VERTEXELEMENTFORMAT_FLOAT3, offsetof(SkinnedVertex, px)};
            sattrs[1] = {1, 0, SDL_GPU_VERTEXELEMENTFORMAT_FLOAT3, offsetof(SkinnedVertex, nx)};
            sattrs[2] = {2, 0, SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2, offsetof(SkinnedVertex, u)};
            sattrs[3] = {3, 0, SDL_GPU_VERTEXELEMENTFORMAT_UBYTE4, offsetof(SkinnedVertex, joints)};
            sattrs[4] = {4, 0, SDL_GPU_VERTEXELEMENTFORMAT_UBYTE4_NORM, offsetof(SkinnedVertex, weights)};
            sattrs[5] = {5, 1, SDL_GPU_VERTEXELEMENTFORMAT_UINT, 0};

            SDL_GPUGraphicsPipelineCreateInfo ci = pi;
            ci.vertex_shader = skinned_vs;
            ci.vertex_input_state = {sbuffers, 2, sattrs, 6};
            skinned_pipeline = SDL_CreateGPUGraphicsPipeline(device, &ci);

            SDL_GPUGraphicsPipelineCreateInfo cs = sh;
            cs.vertex_shader = skinned_shadow_vs;
            cs.vertex_input_state = {sbuffers, 2, sattrs, 6};
            skinned_shadow_pipeline = SDL_CreateGPUGraphicsPipeline(device, &cs);

            // Pause blur: full-screen, one sample, no depth. Optional.
            if (blur_fs != nullptr) {
                SDL_GPUGraphicsPipelineCreateInfo bi{};
                bi.vertex_shader = sky_vs;
                bi.fragment_shader = blur_fs;
                bi.primitive_type = SDL_GPU_PRIMITIVETYPE_TRIANGLELIST;
                bi.target_info.color_target_descriptions = &color;
                bi.target_info.num_color_targets = 1;
                blur_pipeline = SDL_CreateGPUGraphicsPipeline(device, &bi);
            }

            // The ground shares the lit fragment shader.
            if (!terrain.create_pipelines(device, swapchain_format, depth_format, to_sample_count(samples), mesh_fs)) {
                log::warn("scene: terrain unavailable");
            }
        }
        for (SDL_GPUShader* s : {mesh_vs, mesh_fs, sky_vs, sky_fs, shadow_vs, shadow_fs, skinned_vs, skinned_shadow_vs, blur_fs}) {
            SDL_ReleaseGPUShader(device, s);
        }
        if (mesh_pipeline == nullptr || sky_pipeline == nullptr || shadow_pipeline == nullptr ||
            skinned_pipeline == nullptr || skinned_shadow_pipeline == nullptr) {
            log::error("scene: pipeline creation failed: {}", SDL_GetError());
            return false;
        }
        return true;
    }

    bool ensure_targets(std::uint32_t w, std::uint32_t h) {
        if (w == target_w && h == target_h && depth != nullptr) {
            return true;
        }
        release_targets();
        SDL_GPUTextureCreateInfo info{};
        info.type = SDL_GPU_TEXTURETYPE_2D;
        info.width = w;
        info.height = h;
        info.layer_count_or_depth = 1;
        info.num_levels = 1;
        info.sample_count = to_sample_count(samples);
        info.format = depth_format;
        info.usage = SDL_GPU_TEXTUREUSAGE_DEPTH_STENCIL_TARGET;
        depth = SDL_CreateGPUTexture(device, &info);
        if (samples > 1) {
            info.format = swapchain_format;
            info.usage = SDL_GPU_TEXTUREUSAGE_COLOR_TARGET;
            color_msaa = SDL_CreateGPUTexture(device, &info);
        }
        if (depth == nullptr || (samples > 1 && color_msaa == nullptr)) {
            log::error("scene: cannot create render targets: {}", SDL_GetError());
            release_targets();
            return false;
        }
        target_w = w;
        target_h = h;
        return true;
    }

    // --- Per frame ---------------------------------------------------------

    // Orders each model's instances by region and records the regions.
    static void build_buckets(GpuModel& m) {
        m.buckets.clear();
        m.groups.clear();
        // Group first, then region, so each group's regions are together.
        const auto key = [&](std::uint32_t idx) {
            const Instance& inst = m.instances[idx];
            const auto bx = static_cast<std::int64_t>(std::floor(inst.position.x / kBucketSize));
            const auto bz = static_cast<std::int64_t>(std::floor(inst.position.z / kBucketSize));
            const std::int64_t group =
                floor_div(bz, kBucketsPerGroup) * (std::int64_t{1} << 32) + floor_div(bx, kBucketsPerGroup);
            return std::pair{group, bz * (std::int64_t{1} << 32) + bx};
        };
        m.order.resize(m.instances.size());
        for (std::uint32_t k = 0; k < m.order.size(); ++k) {
            m.order[k] = k;
        }
        std::stable_sort(m.order.begin(), m.order.end(), [&](std::uint32_t a, std::uint32_t b) { return key(a) < key(b); });
        m.slot_of.resize(m.order.size());
        for (std::uint32_t k = 0; k < m.order.size(); ++k) {
            m.slot_of[m.order[k]] = k;
        }
        std::size_t i = 0;
        std::int64_t last_group = 0;
        while (i < m.order.size()) {
            const std::pair<std::int64_t, std::int64_t> k = key(m.order[i]);
            std::size_t j = i;
            math::Vec3 lo = m.instances[m.order[i]].position;
            math::Vec3 hi = lo;
            while (j < m.order.size() && key(m.order[j]) == k) {
                const math::Vec3 p = m.instances[m.order[j]].position;
                lo = {std::min(lo.x, p.x), std::min(lo.y, p.y), std::min(lo.z, p.z)};
                hi = {std::max(hi.x, p.x), std::max(hi.y, p.y), std::max(hi.z, p.z)};
                ++j;
            }
            Bucket b;
            b.first = static_cast<std::uint32_t>(i);
            b.count = static_cast<std::uint32_t>(j - i);
            b.center = (lo + hi) * 0.5f;
            for (std::size_t n = i; n < j; ++n) {
                const Instance& inst = m.instances[m.order[n]];
                // Room for small moves of updated instances.
                b.radius = std::max(b.radius, math::length(inst.position - b.center) + m.radius * inst.scale + 2.0f);
            }
            if (m.groups.empty() || k.first != last_group) {
                BucketGroup g;
                g.first = static_cast<std::uint32_t>(m.buckets.size());
                m.groups.push_back(g);
                last_group = k.first;
            }
            ++m.groups.back().count;
            m.buckets.push_back(b);
            i = j;
        }
        // Each group's sphere holds its regions' spheres.
        for (BucketGroup& g : m.groups) {
            math::Vec3 lo = m.buckets[g.first].center;
            math::Vec3 hi = lo;
            for (std::uint32_t n = g.first; n < g.first + g.count; ++n) {
                const Bucket& b = m.buckets[n];
                lo = {std::min(lo.x, b.center.x - b.radius), std::min(lo.y, b.center.y - b.radius),
                      std::min(lo.z, b.center.z - b.radius)};
                hi = {std::max(hi.x, b.center.x + b.radius), std::max(hi.y, b.center.y + b.radius),
                      std::max(hi.z, b.center.z + b.radius)};
            }
            g.center = (lo + hi) * 0.5f;
            for (std::uint32_t n = g.first; n < g.first + g.count; ++n) {
                const Bucket& b = m.buckets[n];
                g.radius = std::max(g.radius, math::length(b.center - g.center) + b.radius);
            }
        }
    }

    static GpuInstance to_gpu(const Instance& inst) {
        const float c = std::cos(inst.yaw) * inst.scale;
        const float s = std::sin(inst.yaw) * inst.scale;
        GpuInstance g{};
        g.row0[0] = c;
        g.row0[2] = s;
        g.row0[3] = inst.position.x;
        g.row1[1] = inst.scale;
        g.row1[3] = inst.position.y;
        g.row2[0] = -s;
        g.row2[2] = c;
        g.row2[3] = inst.position.z;
        // The palette number rides in the tint's unused fourth channel.
        set4(g.tint, inst.tint, static_cast<float>(std::min(inst.palette, kMaxBuildingPalettes)));
        return g;
    }

    // Brings gpu_instances up to date and lists what must be uploaded, as
    // (first slot, count) ranges.
    std::vector<std::pair<std::uint32_t, std::uint32_t>> prepare_instances() {
        std::vector<std::pair<std::uint32_t, std::uint32_t>> ranges;
        if (layout_dirty) {
            std::uint32_t base = 0;
            for (GpuModel& m : models) {
                const auto count = static_cast<std::uint32_t>(m.instances.size());
                m.base = base;
                m.capacity = count + count / 4 + 16;
                m.dirty = true;
                base += m.capacity;
            }
            gpu_instances.assign(base, GpuInstance{});
            layout_dirty = false;
            full_upload = true;
        }
        for (GpuModel& m : models) {
            if (m.dirty) {
                build_buckets(m);
                for (std::uint32_t k = 0; k < m.order.size(); ++k) {
                    gpu_instances[m.base + k] = to_gpu(m.instances[m.order[k]]);
                }
                if (!full_upload && !m.order.empty()) {
                    ranges.emplace_back(m.base, static_cast<std::uint32_t>(m.order.size()));
                }
                m.dirty = false;
                m.changed.clear();
            }
            for (const std::uint32_t k : m.changed) {
                gpu_instances[m.base + k] = to_gpu(m.instances[m.order[k]]);
                if (!full_upload) {
                    ranges.emplace_back(m.base + k, 1u);
                }
            }
            m.changed.clear();
        }
        if (full_upload) {
            ranges.clear();
            if (!gpu_instances.empty()) {
                ranges.emplace_back(0u, static_cast<std::uint32_t>(gpu_instances.size()));
            }
        }
        return ranges;
    }

    void rebuild_character_data() {
        gpu_characters.clear();
        for (const CharacterInstance& c : characters) {
            GpuCharacter g{};
            affine_rows(c.position, c.yaw, c.scale, g.row0, g.row1, g.row2);
            const GpuSkinned& body = skinned[c.body];
            const ClipInfo clip = body.clips.empty() ? ClipInfo{} : body.clips[std::min<std::size_t>(c.clip, body.clips.size() - 1)];
            g.anim[0] = body.bone_base + clip.first;
            g.anim[1] = clip.frames;
            g.anim[2] = body.joint_count;
            g.anim[3] = std::min<std::uint32_t>(c.palette, static_cast<std::uint32_t>(palette_data.size() / (kPaletteSlots * 4)) - 1);
            const float frames = static_cast<float>(clip.frames);
            float pos = std::fmod(std::max(0.0f, c.time) * clip.fps, frames);
            if (!std::isfinite(pos)) {
                pos = 0.0f;
            }
            g.extra[0] = pos;
            gpu_characters.push_back(g);
        }
    }

    // Visible characters, then one range per skinned model (a body or an
    // accessory) listing the characters that draw it.
    std::vector<Range> cull_characters(const math::Frustum& frustum, const math::Vec3* eye, float max_distance) {
        std::vector<std::uint32_t> seen;
        const float max_d2 = max_distance * max_distance;
        for (std::size_t i = 0; i < characters.size(); ++i) {
            const CharacterInstance& c = characters[i];
            const float r = skinned[c.body].radius * c.scale;
            bool keep = frustum.sphere_visible(c.position, r);
            if (keep && eye != nullptr) {
                const math::Vec3 d = c.position - *eye;
                keep = math::dot(d, d) <= max_d2;
            }
            if (keep) {
                seen.push_back(static_cast<std::uint32_t>(i));
            }
        }
        std::vector<Range> ranges(skinned.size());
        for (std::size_t mi = 0; mi < skinned.size(); ++mi) {
            const GpuSkinned& m = skinned[mi];
            ranges[mi].first = static_cast<std::uint32_t>(visible.size());
            for (const std::uint32_t i : seen) {
                const CharacterInstance& c = characters[i];
                const bool draws = m.accessory_bit == ~0u ? c.body == mi
                                                          : c.body == m.body && ((c.accessories >> m.accessory_bit) & 1u) != 0;
                if (draws) {
                    visible.push_back(i);
                }
            }
            ranges[mi].count = static_cast<std::uint32_t>(visible.size()) - ranges[mi].first;
        }
        return ranges;
    }

    SDL_GPUBuffer* upload_skinned_vertices(const std::vector<SkinnedVertex>& v) {
        return upload_static_buffer(v.data(), static_cast<std::uint32_t>(v.size() * sizeof(SkinnedVertex)),
                                    SDL_GPU_BUFFERUSAGE_VERTEX);
    }

    bool add_skinned(const ModelData& data, const std::vector<SkinnedVertex>& verts, GpuSkinned& m) {
        m.vertices = upload_skinned_vertices(verts);
        m.indices = upload_static_buffer(data.indices.data(),
                                         static_cast<std::uint32_t>(data.indices.size() * sizeof(std::uint32_t)),
                                         SDL_GPU_BUFFERUSAGE_INDEX);
        if (m.vertices == nullptr || m.indices == nullptr) {
            SDL_ReleaseGPUBuffer(device, m.vertices);
            SDL_ReleaseGPUBuffer(device, m.indices);
            log::error("scene: cannot upload a character model: {}", SDL_GetError());
            return false;
        }
        for (const ModelMaterial& mat : data.materials) {
            GpuMaterial g;
            const int slot = palette_slot(mat.name);
            // A recolored material takes its color from the palette only.
            for (int c = 0; c < 4; ++c) {
                g.base_color[c] = slot >= 0 ? 1.0f : mat.base_color[c];
            }
            g.texture = white;
            m.materials.push_back(g);
            m.slots.push_back(slot);
        }
        m.primitives = data.primitives;
        m.triangles = data.indices.size() / 3;
        return true;
    }

    // Appends the visible instances of each model to `visible` and returns
    // one range per model. Instances farther than `max_distance` from the
    // eye are skipped (0: no limit), and small vegetation stops at the
    // vegetation distance. Whole regions are tested first.
    std::vector<Range> cull(const math::Frustum& frustum, math::Vec3 eye, float max_distance, bool shadows) {
        std::vector<Range> ranges(models.size());
        for (std::size_t mi = 0; mi < models.size(); ++mi) {
            const GpuModel& m = models[mi];
            ranges[mi].first = static_cast<std::uint32_t>(visible.size());
            if (shadows && m.model_class == ModelClass::Sky) {
                ranges[mi].count = 0;
                continue;
            }
            float limit = max_distance > 0.0f ? max_distance : 1e30f;
            if (m.model_class == ModelClass::SmallVegetation) {
                limit = std::min(limit, vegetation_distance);
            } else if (m.model_class == ModelClass::Normal && !shadows) {
                limit = std::min(limit, draw_distance_now);
            }
            for (const BucketGroup& g : m.groups) {
                if (!frustum.sphere_visible(g.center, g.radius) || math::length(g.center - eye) - g.radius > limit) {
                    continue;
                }
                for (std::uint32_t bi = g.first; bi < g.first + g.count; ++bi) {
                    const Bucket& b = m.buckets[bi];
                    if (!frustum.sphere_visible(b.center, b.radius) || math::length(b.center - eye) - b.radius > limit) {
                        continue;
                    }
                    for (std::uint32_t n = b.first; n < b.first + b.count; ++n) {
                        const Instance& inst = m.instances[m.order[n]];
                        const float r = m.radius * inst.scale;
                        if (inst.scale <= 0.0f || !frustum.sphere_visible(inst.position, r)) {
                            continue;
                        }
                        const math::Vec3 d = inst.position - eye;
                        const float reach = limit + r;
                        if (math::dot(d, d) <= reach * reach) {
                            visible.push_back(m.base + n);
                        }
                    }
                }
            }
            ranges[mi].count = static_cast<std::uint32_t>(visible.size()) - ranges[mi].first;
        }
        return ranges;
    }
};

SceneRenderer::SceneRenderer() : impl_(std::make_unique<Impl>()) {}

SceneRenderer::~SceneRenderer() = default;

bool SceneRenderer::create(GpuDevice& gpu, const GraphicsSettings& graphics) {
    Impl& d = *impl_;
    d.device = gpu.device();
    d.swapchain_format = gpu.swapchain_format();
    if (!SDL_GPUTextureSupportsFormat(d.device, SDL_GPU_TEXTUREFORMAT_D32_FLOAT, SDL_GPU_TEXTURETYPE_2D,
                                      SDL_GPU_TEXTUREUSAGE_DEPTH_STENCIL_TARGET | SDL_GPU_TEXTUREUSAGE_SAMPLER)) {
        log::error("scene: the GPU has no 32-bit depth format");
        return false;
    }

    SDL_GPUSamplerCreateInfo si{};
    si.min_filter = SDL_GPU_FILTER_LINEAR;
    si.mag_filter = SDL_GPU_FILTER_LINEAR;
    si.mipmap_mode = SDL_GPU_SAMPLERMIPMAPMODE_LINEAR;
    si.address_mode_u = si.address_mode_v = si.address_mode_w = SDL_GPU_SAMPLERADDRESSMODE_REPEAT;
    si.enable_anisotropy = true;
    si.max_anisotropy = 8.0f;
    si.max_lod = 1000.0f;
    d.base_sampler = SDL_CreateGPUSampler(d.device, &si);

    SDL_GPUSamplerCreateInfo sh{};
    sh.min_filter = SDL_GPU_FILTER_LINEAR;
    sh.mag_filter = SDL_GPU_FILTER_LINEAR;
    sh.address_mode_u = sh.address_mode_v = sh.address_mode_w = SDL_GPU_SAMPLERADDRESSMODE_CLAMP_TO_EDGE;
    sh.enable_compare = true;
    sh.compare_op = SDL_GPU_COMPAREOP_GREATER_OR_EQUAL;
    d.shadow_sampler = SDL_CreateGPUSampler(d.device, &sh);

    SDL_GPUSamplerCreateInfo cl{};
    cl.min_filter = SDL_GPU_FILTER_LINEAR;
    cl.mag_filter = SDL_GPU_FILTER_LINEAR;
    cl.address_mode_u = cl.address_mode_v = cl.address_mode_w = SDL_GPU_SAMPLERADDRESSMODE_CLAMP_TO_EDGE;
    d.clamp_sampler = SDL_CreateGPUSampler(d.device, &cl);

    ModelTexture white;
    white.width = white.height = 1;
    white.rgba = {255, 255, 255, 255};
    d.white = d.upload_texture(white);
    if (d.base_sampler == nullptr || d.shadow_sampler == nullptr || d.white == nullptr) {
        log::error("scene: cannot create samplers: {}", SDL_GetError());
        return false;
    }
    d.graphics.shadows = -1;  // Force apply_settings to build everything.
    return apply_settings(graphics);
}

void SceneRenderer::destroy() {
    impl_->release_all();
}

bool SceneRenderer::apply_settings(const GraphicsSettings& graphics) {
    Impl& d = *impl_;
    if (d.device == nullptr) {
        return false;
    }
    int samples = msaa_samples_for_level(graphics.antialiasing);
    while (samples > 1 && !SDL_GPUTextureSupportsSampleCount(d.device, d.swapchain_format, to_sample_count(samples))) {
        samples /= 2;
    }
    const int cascades = shadow_cascades_for_level(graphics.shadows);
    const int shadow_size = shadow_map_size_for_level(graphics.shadows);
    const bool pipelines_changed = samples != d.samples || d.mesh_pipeline == nullptr;
    const bool shadows_changed = cascades != d.cascades || shadow_size != d.shadow_size || d.shadow_map == nullptr;
    d.graphics = graphics;
    d.draw_distance = draw_distance_for_level(graphics.draw_distance);
    d.vegetation_distance = vegetation_distance_for_level(graphics.vegetation);
    d.samples = samples;
    d.cascades = cascades;
    d.shadow_size = shadow_size;
    stats_.msaa_samples = samples;
    stats_.shadow_cascades = cascades;
    stats_.shadow_map_size = shadow_size;
    stats_.draw_distance = d.draw_distance;
    stats_.vegetation_distance = d.vegetation_distance;

    bool ok = true;
    if (shadows_changed) {
        ok = d.create_shadow_map() && ok;
    }
    if (pipelines_changed) {
        d.release_targets();
        ok = d.create_pipelines() && ok;
    }
    log::info("scene: msaa {}x, shadows {} cascade(s) at {} px, draw distance {} m, vegetation {} m", samples,
              cascades, shadow_size, d.draw_distance, d.vegetation_distance);
    return ok;
}

bool SceneRenderer::add_model(const ModelData& data, ModelId& id) {
    Impl& d = *impl_;
    GpuModel m;
    m.vertices = d.upload_static_buffer(data.vertices.data(),
                                        static_cast<std::uint32_t>(data.vertices.size() * sizeof(ModelVertex)),
                                        SDL_GPU_BUFFERUSAGE_VERTEX);
    m.indices = d.upload_static_buffer(data.indices.data(),
                                       static_cast<std::uint32_t>(data.indices.size() * sizeof(std::uint32_t)),
                                       SDL_GPU_BUFFERUSAGE_INDEX);
    if (m.vertices == nullptr || m.indices == nullptr) {
        SDL_ReleaseGPUBuffer(d.device, m.vertices);
        SDL_ReleaseGPUBuffer(d.device, m.indices);
        log::error("scene: cannot upload a model: {}", SDL_GetError());
        return false;
    }
    for (const ModelTexture& t : data.textures) {
        m.textures.push_back(d.upload_texture(t));
    }
    for (const ModelMaterial& mat : data.materials) {
        GpuMaterial g;
        std::copy(std::begin(mat.base_color), std::end(mat.base_color), g.base_color);
        g.texture = (mat.texture >= 0 && static_cast<std::size_t>(mat.texture) < m.textures.size() &&
                     m.textures[static_cast<std::size_t>(mat.texture)] != nullptr)
                        ? m.textures[static_cast<std::size_t>(mat.texture)]
                        : d.white;
        m.materials.push_back(g);
        m.slots.push_back(building_slot(mat.name));
    }
    m.primitives = data.primitives;
    m.radius = std::max(0.01f, data.radius);
    m.triangles = data.indices.size() / 3;
    id = static_cast<ModelId>(d.models.size());
    d.models.push_back(std::move(m));
    return true;
}

void SceneRenderer::set_model_class(ModelId model, ModelClass model_class) {
    if (model < impl_->models.size()) {
        impl_->models[model].model_class = model_class;
    }
}

bool SceneRenderer::set_terrain(const TerrainData& data) {
    Impl& d = *impl_;
    return d.device != nullptr && d.terrain.set(d.device, data);
}

void SceneRenderer::clear_terrain() {
    impl_->terrain.clear();
}

void SceneRenderer::set_instances(ModelId model, std::span<const Instance> instances) {
    if (model < impl_->models.size()) {
        GpuModel& m = impl_->models[model];
        m.instances.assign(instances.begin(), instances.end());
        m.dirty = true;
        if (m.instances.size() > m.capacity) {
            impl_->layout_dirty = true;
        }
    }
}

void SceneRenderer::update_instance(ModelId model, std::uint32_t index, const Instance& instance) {
    if (model >= impl_->models.size()) {
        return;
    }
    GpuModel& m = impl_->models[model];
    if (index >= m.instances.size()) {
        return;
    }
    m.instances[index] = instance;
    if (!m.dirty && index < m.slot_of.size()) {
        m.changed.push_back(m.slot_of[index]);
    }
}

bool SceneRenderer::add_skinned_model(const ModelData& data, SkinnedId& id) {
    Impl& d = *impl_;
    if (!data.skinned() || data.clips.empty() || data.skin.size() != data.vertices.size()) {
        log::error("scene: a character model needs a skeleton and animations");
        return false;
    }
    std::vector<SkinnedVertex> verts;
    verts.reserve(data.vertices.size());
    for (std::size_t i = 0; i < data.vertices.size(); ++i) {
        const ModelVertex& v = data.vertices[i];
        SkinnedVertex sv{v.px, v.py, v.pz, v.nx, v.ny, v.nz, v.u, v.v, {}, {}};
        std::copy(std::begin(data.skin[i].joints), std::end(data.skin[i].joints), sv.joints);
        std::copy(std::begin(data.skin[i].weights), std::end(data.skin[i].weights), sv.weights);
        verts.push_back(sv);
    }
    GpuSkinned m;
    if (!d.add_skinned(data, verts, m)) {
        return false;
    }
    m.joint_count = static_cast<std::uint32_t>(data.joint_names.size());
    m.bone_base = static_cast<std::uint32_t>(d.bone_rows.size() / 12);
    std::uint32_t first = 0;
    for (const ModelClip& clip : data.clips) {
        m.clips.push_back({first, static_cast<std::uint32_t>(clip.frame_count), clip.fps});
        m.clip_names.push_back(clip.name);
        for (const math::Mat4& mat : clip.skin) {
            for (int r = 0; r < 3; ++r) {
                for (int c = 0; c < 4; ++c) {
                    d.bone_rows.push_back(mat.m[c][r]);
                }
            }
        }
        first += static_cast<std::uint32_t>(clip.skin.size());
    }
    d.bones_dirty = true;
    m.joint_names = data.joint_names;
    for (const math::Mat4& rest : data.joint_rest) {
        m.joint_rest_positions.push_back({rest.m[3][0], rest.m[3][1], rest.m[3][2]});
    }
    // Room for the model to bend and swing its arms.
    m.radius = std::max(0.5f, data.radius * 1.15f);
    id = static_cast<SkinnedId>(d.skinned.size());
    m.body = id;
    d.skinned.push_back(std::move(m));
    return true;
}

bool SceneRenderer::add_accessory(const ModelData& data, SkinnedId body, std::string_view bone, std::uint32_t& bit) {
    Impl& d = *impl_;
    if (body >= d.skinned.size() || d.skinned[body].accessory_bit != ~0u || data.skinned()) {
        log::error("scene: an accessory must be a rigid model pinned to a body");
        return false;
    }
    GpuSkinned& owner = d.skinned[body];
    int joint = -1;
    for (std::size_t j = 0; j < owner.joint_names.size(); ++j) {
        if (owner.joint_names[j] == bone) {
            joint = static_cast<int>(j);
        }
    }
    if (joint < 0 || owner.accessory_count >= 32) {
        log::error("scene: no bone '{}' for an accessory, or too many accessories", bone);
        return false;
    }
    // Move the accessory to the bone in the bind pose; the bone's skin
    // matrix then carries it along with the animation.
    const math::Vec3 at = owner.joint_rest_positions[static_cast<std::size_t>(joint)];
    std::vector<SkinnedVertex> verts;
    for (const ModelVertex& v : data.vertices) {
        verts.push_back({v.px + at.x, v.py + at.y, v.pz + at.z, v.nx, v.ny, v.nz, v.u, v.v,
                         {static_cast<std::uint8_t>(joint), 0, 0, 0}, {255, 0, 0, 0}});
    }
    GpuSkinned m;
    if (!d.add_skinned(data, verts, m)) {
        return false;
    }
    m.radius = owner.radius;
    m.body = body;
    m.accessory_bit = owner.accessory_count++;
    bit = m.accessory_bit;
    d.skinned.push_back(std::move(m));
    return true;
}

int SceneRenderer::clip_index(SkinnedId body, std::string_view name) const {
    const Impl& d = *impl_;
    if (body >= d.skinned.size()) {
        return -1;
    }
    const std::vector<std::string>& names = d.skinned[body].clip_names;
    for (std::size_t i = 0; i < names.size(); ++i) {
        if (names[i] == name) {
            return static_cast<int>(i);
        }
    }
    return -1;
}

float SceneRenderer::clip_duration(SkinnedId body, std::uint32_t clip) const {
    const Impl& d = *impl_;
    if (body >= d.skinned.size() || clip >= d.skinned[body].clips.size()) {
        return 0.0f;
    }
    const ClipInfo& c = d.skinned[body].clips[clip];
    return static_cast<float>(c.frames) / c.fps;
}

void SceneRenderer::set_palettes(std::span<const Palette> palettes) {
    Impl& d = *impl_;
    d.palette_data.clear();
    for (const Palette& p : palettes) {
        for (const math::Vec3& c : p.colors) {
            d.palette_data.insert(d.palette_data.end(), {c.x, c.y, c.z, 1.0f});
        }
    }
    if (d.palette_data.empty()) {
        d.palette_data.assign(kPaletteSlots * 4, 1.0f);
    }
    d.palettes_dirty = true;
}

void SceneRenderer::set_building_palettes(std::span<const BuildingPalette> palettes) {
    Impl& d = *impl_;
    d.building_palette_data.assign(std::size_t{kMaxBuildingPalettes} * kBuildingPaletteSlots * 4, 1.0f);
    for (std::size_t i = 0; i < palettes.size() && i < kMaxBuildingPalettes; ++i) {
        for (std::size_t s = 0; s < kBuildingPaletteSlots; ++s) {
            const math::Vec3& c = palettes[i].colors[s];
            float* out = &d.building_palette_data[(i * kBuildingPaletteSlots + s) * 4];
            out[0] = c.x;
            out[1] = c.y;
            out[2] = c.z;
        }
    }
    d.building_palettes_dirty = true;
}

void SceneRenderer::set_characters(std::span<const CharacterInstance> characters) {
    Impl& d = *impl_;
    d.characters.clear();
    for (const CharacterInstance& c : characters) {
        // Only bodies can be characters; anything else is dropped.
        if (c.body < d.skinned.size() && d.skinned[c.body].accessory_bit == ~0u) {
            d.characters.push_back(c);
        }
    }
}

void SceneRenderer::clear_instances() {
    for (GpuModel& m : impl_->models) {
        m.instances.clear();
        m.dirty = true;
    }
}

bool SceneRenderer::set_war_fog(int mode, std::int32_t side, float cell) {
    Impl& d = *impl_;
    if (d.device == nullptr) {
        return false;
    }
    if (mode <= 0 || side <= 0 || cell <= 0.0f) {
        d.release_war();
        return true;
    }
    if (d.war_fog == nullptr || d.war_side != side) {
        d.release_war();
        d.war_fog = d.make_war_texture(side, SDL_GPU_TEXTUREFORMAT_R8_UNORM);
        if (d.war_fog == nullptr) {
            return false;
        }
        d.war_side = side;
        // Unexplored until told otherwise.
        const std::vector<std::uint8_t> zero(static_cast<std::size_t>(side) * static_cast<std::size_t>(side), 0);
        update_war_fog(zero, 0, 0, side, side);
    }
    d.war_mode = std::min(mode, 2);
    d.war_meters = static_cast<float>(side) * cell;
    return true;
}

void SceneRenderer::update_war_fog(std::span<const std::uint8_t> texels, std::int32_t x, std::int32_t z, std::int32_t w,
                                   std::int32_t d_rows) {
    Impl& d = *impl_;
    const std::int32_t side = d.war_side;
    if (d.war_fog == nullptr || texels.size() != static_cast<std::size_t>(side) * static_cast<std::size_t>(side) ||
        x < 0 || z < 0 || w <= 0 || d_rows <= 0 || x + w > side || z + d_rows > side) {
        return;
    }
    WarUpload u;
    u.x = static_cast<std::uint32_t>(x);
    u.z = static_cast<std::uint32_t>(z);
    u.w = static_cast<std::uint32_t>(w);
    u.d = static_cast<std::uint32_t>(d_rows);
    u.bytes.resize(static_cast<std::size_t>(w) * static_cast<std::size_t>(d_rows));
    for (std::int32_t row = 0; row < d_rows; ++row) {
        const std::size_t from = static_cast<std::size_t>(z + row) * static_cast<std::size_t>(side) + static_cast<std::size_t>(x);
        std::memcpy(u.bytes.data() + static_cast<std::size_t>(row) * static_cast<std::size_t>(w), texels.data() + from,
                    static_cast<std::size_t>(w));
    }
    d.war_uploads.push_back(std::move(u));
}

bool SceneRenderer::set_war_ceiling(std::span<const std::uint16_t> heights, std::int32_t side, float band) {
    Impl& d = *impl_;
    if (d.device == nullptr) {
        return false;
    }
    SDL_ReleaseGPUTexture(d.device, d.war_ceiling);
    d.war_ceiling = nullptr;
    d.war_ceiling_side = 0;
    d.war_band = 0.0f;
    std::erase_if(d.war_uploads, [](const WarUpload& u) { return u.ceiling; });
    if (side <= 0 || heights.size() != static_cast<std::size_t>(side) * static_cast<std::size_t>(side) || band <= 0.0f) {
        return true;
    }
    d.war_ceiling = d.make_war_texture(side, SDL_GPU_TEXTUREFORMAT_R16_UNORM);
    if (d.war_ceiling == nullptr) {
        return false;
    }
    d.war_ceiling_side = side;
    d.war_band = band;
    WarUpload u;
    u.ceiling = true;
    u.w = u.d = static_cast<std::uint32_t>(side);
    u.bytes.resize(heights.size() * 2);
    std::memcpy(u.bytes.data(), heights.data(), u.bytes.size());
    d.war_uploads.push_back(std::move(u));
    return true;
}

bool SceneRenderer::render(GpuFrame& frame, const SceneView& view, const Lighting& lighting) {
    Impl& d = *impl_;
    stats_ = RenderStats{};
    stats_.msaa_samples = d.samples;
    stats_.shadow_cascades = d.cascades;
    stats_.shadow_map_size = d.shadow_size;
    stats_.vegetation_distance = d.vegetation_distance;
    if (frame.target == nullptr || d.mesh_pipeline == nullptr || !d.ensure_targets(frame.width, frame.height)) {
        return false;
    }
    const auto t0 = std::chrono::steady_clock::now();
    const float draw_distance = view.draw_distance_override > 0.0f ? view.draw_distance_override : d.draw_distance;
    stats_.draw_distance = draw_distance;
    const float view_distance = std::max(draw_distance, view.terrain_distance);

    // Camera matrices.
    const math::Mat4 proj = math::perspective_reverse_z(view.fov_y, view.aspect, view.near_z, view_distance);
    const math::Mat4 view_proj = proj * view.view;
    const math::Frustum frustum = math::Frustum::from_matrix(view_proj);

    // Cascades: split the view distance and fit a stable box around each slice.
    float splits[kMaxCascades];
    const float shadow_distance = std::min(shadow_distance_for_level(d.graphics.shadows), draw_distance);
    compute_cascade_splits(view.near_z, shadow_distance, d.cascades, splits);
    math::Mat4 cascade_vp[kMaxCascades];
    const math::Vec3 sun = math::normalize(lighting.sun_direction);
    float slice_near = view.near_z;
    for (int c = 0; c < d.cascades; ++c) {
        const float slice_far = splits[c];
        const math::Mat4 slice_proj = math::perspective_reverse_z(view.fov_y, view.aspect, slice_near, slice_far);
        const math::Mat4 inv_slice = math::inverse(slice_proj * view.view);
        math::Vec3 corners[8];
        math::Vec3 center{};
        int k = 0;
        for (const float z : {1.0f, 0.0f}) {
            for (const float y : {-1.0f, 1.0f}) {
                for (const float x : {-1.0f, 1.0f}) {
                    corners[k] = inv_slice.transform_point({x, y, z});
                    center += corners[k];
                    ++k;
                }
            }
        }
        center = center * (1.0f / 8.0f);
        float radius = 0.0f;
        for (const math::Vec3& p : corners) {
            radius = std::max(radius, math::length(p - center));
        }
        radius = std::ceil(radius);  // Stable size while the camera turns.
        const math::Vec3 up = std::abs(sun.y) > 0.99f ? math::Vec3{0, 0, 1} : math::Vec3{0, 1, 0};
        const float back = radius + 300.0f;
        math::Mat4 light_view = math::look_at(center + sun * back, center, up);
        // Snap the center to whole shadow texels so edges do not shimmer.
        const float texel = 2.0f * radius / static_cast<float>(d.shadow_size);
        const math::Vec3 lc = light_view.transform_point(center);
        const float dx = std::floor(lc.x / texel) * texel - lc.x;
        const float dy = std::floor(lc.y / texel) * texel - lc.y;
        light_view = math::translation({dx, dy, 0.0f}) * light_view;
        const math::Mat4 light_proj = math::orthographic_reverse_z(-radius, radius, -radius, radius, 0.1f, back + radius);
        cascade_vp[c] = light_proj * light_view;
        slice_near = slice_far;
    }

    d.draw_distance_now = draw_distance;
    // Culling (instances are grouped by region first, when they changed).
    const std::vector<std::pair<std::uint32_t, std::uint32_t>> instance_ranges = d.prepare_instances();
    d.visible.clear();
    const std::vector<Range> main_ranges = d.cull(frustum, view.eye, view_distance, false);
    const std::vector<Range> main_characters = d.cull_characters(frustum, &view.eye, draw_distance);
    std::vector<Range> shadow_ranges[kMaxCascades];
    std::vector<Range> shadow_characters[kMaxCascades];
    for (int c = 0; c < d.cascades; ++c) {
        const math::Frustum light = math::Frustum::from_matrix(cascade_vp[c]);
        shadow_ranges[c] = d.cull(light, view.eye, 0.0f, true);
        shadow_characters[c] = d.cull_characters(light, nullptr, 0.0f);
    }
    if (!d.terrain.prepare(frame.cmd, frustum, view.eye, view_distance)) {
        log::warn("scene: terrain lists not uploaded this frame");
    }
    stats_.cull_ms = std::chrono::duration<float, std::milli>(std::chrono::steady_clock::now() - t0).count();

    // Uploads, in one transfer: visible indices and characters every frame;
    // instances, bones and palettes when they changed.
    d.rebuild_character_data();
    stats_.instances_total = static_cast<std::uint32_t>(d.gpu_instances.size());
    stats_.characters_total = static_cast<std::uint32_t>(d.gpu_characters.size());
    const auto instance_bytes = static_cast<std::uint32_t>(d.gpu_instances.size() * sizeof(GpuInstance));
    const auto visible_bytes = static_cast<std::uint32_t>(d.visible.size() * sizeof(std::uint32_t));
    const auto character_bytes = static_cast<std::uint32_t>(d.gpu_characters.size() * sizeof(GpuCharacter));
    const auto bone_bytes = static_cast<std::uint32_t>(d.bone_rows.size() * sizeof(float));
    const auto palette_bytes = static_cast<std::uint32_t>(d.palette_data.size() * sizeof(float));
    const auto building_palette_bytes = static_cast<std::uint32_t>(d.building_palette_data.size() * sizeof(float));
    // Fog of war rectangles: rows padded to 256 bytes and each one starting
    // on 512 bytes, as Direct3D 12 wants for texture uploads.
    std::uint32_t war_bytes = 0;
    for (const WarUpload& u : d.war_uploads) {
        const std::uint32_t texel = u.ceiling ? 2u : 1u;
        war_bytes = align_up(war_bytes, 512) + align_up(u.w * texel, 256) * u.d;
    }
    if (!d.war_uploads.empty()) {
        war_bytes += 512;
    }
    std::uint32_t upload_instances = 0;
    for (const auto& [first, count] : instance_ranges) {
        upload_instances += count * static_cast<std::uint32_t>(sizeof(GpuInstance));
    }
    const std::uint32_t upload_bones = d.bones_dirty ? bone_bytes : 0;
    const std::uint32_t upload_palettes = d.palettes_dirty ? palette_bytes : 0;
    constexpr SDL_GPUBufferUsageFlags kStorage = SDL_GPU_BUFFERUSAGE_GRAPHICS_STORAGE_READ;
    // A new (bigger) instance buffer starts empty: everything goes up again.
    const std::uint32_t old_instance_capacity = d.instance_capacity;
    if (!d.ensure_buffer(d.instance_buffer, d.instance_capacity, instance_bytes + 64, kStorage)) {
        return false;
    }
    std::vector<std::pair<std::uint32_t, std::uint32_t>> send_instances = instance_ranges;
    if (d.instance_capacity != old_instance_capacity && !d.gpu_instances.empty()) {
        send_instances.assign(1, {0u, static_cast<std::uint32_t>(d.gpu_instances.size())});
        upload_instances = instance_bytes;
    }
    if (!d.ensure_buffer(d.visible_buffer, d.visible_capacity, visible_bytes + 16, SDL_GPU_BUFFERUSAGE_VERTEX) ||
        !d.ensure_buffer(d.character_buffer, d.character_capacity, character_bytes + 80, kStorage) ||
        !d.ensure_buffer(d.palette_buffer, d.palette_capacity, palette_bytes + 16, kStorage)) {
        return false;
    }
    // A new (bigger) building palette buffer starts empty.
    const std::uint32_t old_building_palette_capacity = d.building_palette_capacity;
    if (!d.ensure_buffer(d.building_palette_buffer, d.building_palette_capacity, building_palette_bytes + 16,
                         kStorage)) {
        return false;
    }
    const std::uint32_t building_palettes_to_upload =
        (d.building_palettes_dirty || d.building_palette_capacity != old_building_palette_capacity)
            ? building_palette_bytes
            : 0;
    // Bones are only ever added, so a larger buffer means a full upload.
    const std::uint32_t old_bone_capacity = d.bone_capacity;
    if (!d.ensure_buffer(d.bone_buffer, d.bone_capacity, bone_bytes + 48, kStorage)) {
        return false;
    }
    const std::uint32_t bones_to_upload =
        (d.bone_capacity != old_bone_capacity || upload_bones > 0) ? bone_bytes : 0;
    const std::uint32_t palettes_to_upload = upload_palettes;
    const std::uint32_t to_send = visible_bytes + upload_instances + character_bytes + bones_to_upload +
                                  palettes_to_upload + building_palettes_to_upload + war_bytes;
    if (to_send > 0) {
        if (!d.ensure_transfer(to_send + 16)) {
            return false;
        }
        auto* mapped = static_cast<std::uint8_t*>(SDL_MapGPUTransferBuffer(d.device, d.transfer, true));
        if (mapped == nullptr) {
            return false;
        }
        std::uint32_t offset = 0;
        // Copy everything into the mapped memory first, then record uploads.
        struct Item {
            const void* data;
            std::uint32_t bytes;
            SDL_GPUBuffer* dst;
            bool cycle;
        };
        // Instance ranges go first, each to its own place in the buffer.
        std::vector<std::pair<std::uint32_t, std::uint32_t>> instance_offsets;  // (transfer offset, bytes)
        for (const auto& [first, count] : send_instances) {
            const auto bytes = count * static_cast<std::uint32_t>(sizeof(GpuInstance));
            std::memcpy(mapped + offset, d.gpu_instances.data() + first, bytes);
            instance_offsets.emplace_back(offset, bytes);
            offset += bytes;
        }
        const Item items[] = {
            {d.visible.data(), visible_bytes, d.visible_buffer, true},
            {d.gpu_characters.data(), character_bytes, d.character_buffer, true},
            {d.bone_rows.data(), bones_to_upload, d.bone_buffer, false},
            {d.palette_data.data(), palettes_to_upload, d.palette_buffer, false},
            {d.building_palette_data.data(), building_palettes_to_upload, d.building_palette_buffer, false},
        };
        std::uint32_t offsets[std::size(items)] = {};
        for (std::size_t i = 0; i < std::size(items); ++i) {
            offsets[i] = offset;
            if (items[i].bytes > 0) {
                std::memcpy(mapped + offset, items[i].data, items[i].bytes);
                offset += items[i].bytes;
            }
        }
        std::vector<std::uint32_t> war_offsets;
        for (const WarUpload& u : d.war_uploads) {
            const std::uint32_t texel = u.ceiling ? 2u : 1u;
            const std::uint32_t pitch = align_up(u.w * texel, 256);
            offset = align_up(offset, 512);
            war_offsets.push_back(offset);
            for (std::uint32_t row = 0; row < u.d; ++row) {
                std::memcpy(mapped + offset + row * pitch, u.bytes.data() + static_cast<std::size_t>(row) * u.w * texel,
                            static_cast<std::size_t>(u.w) * texel);
            }
            offset += pitch * u.d;
        }
        SDL_UnmapGPUTransferBuffer(d.device, d.transfer);
        SDL_GPUCopyPass* copy = SDL_BeginGPUCopyPass(frame.cmd);
        for (std::size_t r = 0; r < send_instances.size(); ++r) {
            const SDL_GPUTransferBufferLocation src{d.transfer, instance_offsets[r].first};
            const SDL_GPUBufferRegion dst{d.instance_buffer,
                                          send_instances[r].first * static_cast<std::uint32_t>(sizeof(GpuInstance)),
                                          instance_offsets[r].second};
            SDL_UploadToGPUBuffer(copy, &src, &dst, false);
        }
        for (std::size_t i = 0; i < std::size(items); ++i) {
            if (items[i].bytes == 0) {
                continue;
            }
            const SDL_GPUTransferBufferLocation src{d.transfer, offsets[i]};
            const SDL_GPUBufferRegion dst{items[i].dst, 0, items[i].bytes};
            SDL_UploadToGPUBuffer(copy, &src, &dst, items[i].cycle);
        }
        for (std::size_t i = 0; i < d.war_uploads.size(); ++i) {
            const WarUpload& u = d.war_uploads[i];
            SDL_GPUTexture* texture = u.ceiling ? d.war_ceiling : d.war_fog;
            if (texture == nullptr) {
                continue;
            }
            const std::uint32_t texel = u.ceiling ? 2u : 1u;
            SDL_GPUTextureTransferInfo src{};
            src.transfer_buffer = d.transfer;
            src.offset = war_offsets[i];
            src.pixels_per_row = align_up(u.w * texel, 256) / texel;
            src.rows_per_layer = u.d;
            SDL_GPUTextureRegion dst{};
            dst.texture = texture;
            dst.x = u.x;
            dst.y = u.z;
            dst.w = u.w;
            dst.h = u.d;
            dst.d = 1;
            SDL_UploadToGPUTexture(copy, &src, &dst, false);
        }
        d.war_uploads.clear();
        SDL_EndGPUCopyPass(copy);
        if (upload_instances > 0) {
            d.full_upload = false;
        }
        if (bones_to_upload > 0) {
            d.bones_dirty = false;
        }
        if (palettes_to_upload > 0) {
            d.palettes_dirty = false;
        }
        if (building_palettes_to_upload > 0) {
            d.building_palettes_dirty = false;
        }
    }

    const std::array<SDL_GPUTextureSamplerBinding, 2> war_bind = d.war_bindings();
    // Draws every model's visible instances; `with_materials` binds colors.
    const auto draw_models = [&](SDL_GPURenderPass* pass, const std::vector<Range>& ranges, bool with_materials) {
        SDL_GPUBuffer* storage[2] = {d.instance_buffer, d.building_palette_buffer};
        SDL_BindGPUVertexStorageBuffers(pass, 0, storage, with_materials ? 2u : 1u);
        for (std::size_t mi = 0; mi < d.models.size(); ++mi) {
            const Range r = ranges[mi];
            if (r.count == 0) {
                continue;
            }
            const GpuModel& m = d.models[mi];
            const SDL_GPUBufferBinding vbs[2] = {{m.vertices, 0}, {d.visible_buffer, r.first * 4u}};
            SDL_BindGPUVertexBuffers(pass, 0, vbs, 2);
            const SDL_GPUBufferBinding ib{m.indices, 0};
            SDL_BindGPUIndexBuffer(pass, &ib, SDL_GPU_INDEXELEMENTSIZE_32BIT);
            for (const ModelPrimitive& p : m.primitives) {
                if (with_materials) {
                    const std::size_t mat_index = std::min<std::size_t>(p.material, m.materials.size() - 1);
                    const GpuMaterial& mat = m.materials[mat_index];
                    MeshDrawUniforms du{};
                    du.draw[0] = m.slots[mat_index];
                    std::copy(std::begin(mat.base_color), std::end(mat.base_color), du.base_color);
                    SDL_PushGPUVertexUniformData(frame.cmd, 1, &du, sizeof(du));
                    MaterialUniforms mu{};
                    std::copy(std::begin(mat.base_color), std::end(mat.base_color), mu.base_color);
                    SDL_PushGPUFragmentUniformData(frame.cmd, 1, &mu, sizeof(mu));
                    const SDL_GPUTextureSamplerBinding bindings[4] = {
                        {mat.texture, d.base_sampler}, {d.shadow_map, d.shadow_sampler}, war_bind[0], war_bind[1]};
                    SDL_BindGPUFragmentSamplers(pass, 0, bindings, 4);
                }
                SDL_DrawGPUIndexedPrimitives(pass, p.index_count, r.count, p.first_index, 0, 0);
                ++stats_.draw_calls;
                stats_.triangles += static_cast<std::uint64_t>(p.index_count / 3) * r.count;
            }
        }
    };

    // Draws the visible characters of every body and accessory.
    const auto draw_characters = [&](SDL_GPURenderPass* pass, const std::vector<Range>& ranges, bool with_materials) {
        SDL_GPUBuffer* storage[3] = {d.character_buffer, d.bone_buffer, d.palette_buffer};
        SDL_BindGPUVertexStorageBuffers(pass, 0, storage, with_materials ? 3u : 2u);
        for (std::size_t mi = 0; mi < d.skinned.size(); ++mi) {
            const Range r = ranges[mi];
            if (r.count == 0) {
                continue;
            }
            const GpuSkinned& m = d.skinned[mi];
            const SDL_GPUBufferBinding vbs[2] = {{m.vertices, 0}, {d.visible_buffer, r.first * 4u}};
            SDL_BindGPUVertexBuffers(pass, 0, vbs, 2);
            const SDL_GPUBufferBinding ib{m.indices, 0};
            SDL_BindGPUIndexBuffer(pass, &ib, SDL_GPU_INDEXELEMENTSIZE_32BIT);
            for (const ModelPrimitive& p : m.primitives) {
                if (with_materials) {
                    const std::size_t mat_index = std::min<std::size_t>(p.material, m.materials.size() - 1);
                    const GpuMaterial& mat = m.materials[mat_index];
                    const DrawUniforms du{{m.slots[mat_index], 0, 0, 0}};
                    SDL_PushGPUVertexUniformData(frame.cmd, 1, &du, sizeof(du));
                    MaterialUniforms mu{};
                    std::copy(std::begin(mat.base_color), std::end(mat.base_color), mu.base_color);
                    SDL_PushGPUFragmentUniformData(frame.cmd, 1, &mu, sizeof(mu));
                    const SDL_GPUTextureSamplerBinding bindings[4] = {
                        {mat.texture, d.base_sampler}, {d.shadow_map, d.shadow_sampler}, war_bind[0], war_bind[1]};
                    SDL_BindGPUFragmentSamplers(pass, 0, bindings, 4);
                }
                SDL_DrawGPUIndexedPrimitives(pass, p.index_count, r.count, p.first_index, 0, 0);
                ++stats_.draw_calls;
                if (with_materials) {
                    stats_.triangles += static_cast<std::uint64_t>(p.index_count / 3) * r.count;
                }
            }
        }
    };

    // Shadow passes.
    for (int c = 0; c < d.cascades; ++c) {
        SDL_GPUDepthStencilTargetInfo dt{};
        dt.texture = d.shadow_map;
        dt.clear_depth = 0.0f;  // Reversed Z: far.
        dt.load_op = SDL_GPU_LOADOP_CLEAR;
        dt.store_op = SDL_GPU_STOREOP_STORE;
        dt.stencil_load_op = SDL_GPU_LOADOP_DONT_CARE;
        dt.stencil_store_op = SDL_GPU_STOREOP_DONT_CARE;
        dt.layer = static_cast<std::uint8_t>(c);
        SDL_GPURenderPass* pass = SDL_BeginGPURenderPass(frame.cmd, nullptr, 0, &dt);
        if (pass == nullptr) {
            return false;
        }
        SDL_BindGPUGraphicsPipeline(pass, d.shadow_pipeline);
        const MeshVertexUniforms su{cascade_vp[c]};
        SDL_PushGPUVertexUniformData(frame.cmd, 0, &su, sizeof(su));
        const std::uint64_t triangles_before = stats_.triangles;
        draw_models(pass, shadow_ranges[c], false);
        stats_.triangles = triangles_before;  // Count only what the player sees.
        for (const Range& r : shadow_ranges[c]) {
            stats_.shadow_instances += r.count;
        }
        if (!d.characters.empty()) {
            SDL_BindGPUGraphicsPipeline(pass, d.skinned_shadow_pipeline);
            SDL_PushGPUVertexUniformData(frame.cmd, 0, &su, sizeof(su));
            draw_characters(pass, shadow_characters[c], false);
        }
        SDL_EndGPURenderPass(pass);
    }

    // Main pass.
    SDL_GPUColorTargetInfo ct{};
    const math::Vec3 horizon = lighting.horizon_color;
    ct.clear_color = SDL_FColor{horizon.x, horizon.y, horizon.z, 1.0f};
    ct.load_op = SDL_GPU_LOADOP_CLEAR;
    const bool blur = view.blur > 0.0f && d.blur_pipeline != nullptr && d.clamp_sampler != nullptr &&
                      d.ensure_post(frame.width, frame.height);
    SDL_GPUTexture* scene_target = blur ? d.post_a : frame.target;
    if (d.samples > 1) {
        ct.texture = d.color_msaa;
        ct.resolve_texture = scene_target;
        ct.store_op = SDL_GPU_STOREOP_RESOLVE;
    } else {
        ct.texture = scene_target;
        ct.store_op = SDL_GPU_STOREOP_STORE;
    }
    SDL_GPUDepthStencilTargetInfo dt{};
    dt.texture = d.depth;
    dt.clear_depth = 0.0f;
    dt.load_op = SDL_GPU_LOADOP_CLEAR;
    dt.store_op = SDL_GPU_STOREOP_DONT_CARE;
    dt.stencil_load_op = SDL_GPU_LOADOP_DONT_CARE;
    dt.stencil_store_op = SDL_GPU_STOREOP_DONT_CARE;
    SDL_GPURenderPass* pass = SDL_BeginGPURenderPass(frame.cmd, &ct, 1, &dt);
    if (pass == nullptr) {
        return false;
    }

    SkyUniforms sky{};
    sky.inverse_view_proj = math::inverse(view_proj);
    set4(sky.sun_direction, sun, 0.0f);
    set4(sky.zenith_color, lighting.zenith_color, 1.0f);
    set4(sky.horizon_color, lighting.horizon_color, 1.0f);
    set4(sky.sun_color, lighting.sun_color, 1.0f);
    SDL_BindGPUGraphicsPipeline(pass, d.sky_pipeline);
    SDL_PushGPUFragmentUniformData(frame.cmd, 0, &sky, sizeof(sky));
    SDL_DrawGPUPrimitives(pass, 3, 1, 0, 0);
    ++stats_.draw_calls;

    SceneUniforms su{};
    for (int c = 0; c < kMaxCascades; ++c) {
        su.cascade_matrix[c] = c < d.cascades ? cascade_vp[c] : math::Mat4::identity();
        su.cascade_split[c] = splits[c];
    }
    set4(su.sun_direction, sun, 0.0f);
    set4(su.sun_color, lighting.sun_color, 1.0f);
    set4(su.sky_ambient, lighting.sky_ambient, 1.0f);
    set4(su.ground_ambient, lighting.ground_ambient, 1.0f);
    // Fog reaches about 90 % at the draw distance: 1 - 2^(-k d^2) = 0.9.
    set4(su.fog_color, lighting.horizon_color, 3.32f / (view_distance * view_distance));
    set4(su.camera_position, view.eye, static_cast<float>(d.cascades));
    su.shadow_params[0] = d.shadow_size > 0 ? 1.0f / static_cast<float>(d.shadow_size) : 0.0f;
    su.shadow_params[1] = 0.0002f;
    su.shadow_params[2] = std::clamp(view.snow, 0.0f, 1.0f);
    d.war_params(su.war_params);
    SDL_PushGPUFragmentUniformData(frame.cmd, 0, &su, sizeof(su));
    d.terrain.draw_ground(frame.cmd, pass, view_proj, d.white, d.base_sampler, d.shadow_map, d.shadow_sampler,
                          war_bind.data());
    // Grass thins out as snow covers it, and is gone under deep snow.
    const float grass_distance = grass_distance_for_level(d.graphics.vegetation) * std::max(0.0f, 1.0f - view.snow * 2.5f);
    if (grass_distance > 1.0f) {
        d.terrain.draw_grass(frame.cmd, pass, view_proj, view.eye, view.time, grass_distance, d.white, d.base_sampler,
                             d.shadow_map, d.shadow_sampler, war_bind.data());
    }
    SDL_BindGPUGraphicsPipeline(pass, d.mesh_pipeline);
    const MeshVertexUniforms mv{view_proj};
    SDL_PushGPUVertexUniformData(frame.cmd, 0, &mv, sizeof(mv));
    draw_models(pass, main_ranges, true);
    for (const Range& r : main_ranges) {
        stats_.instances_drawn += r.count;
    }
    if (!d.characters.empty()) {
        SDL_BindGPUGraphicsPipeline(pass, d.skinned_pipeline);
        SDL_PushGPUVertexUniformData(frame.cmd, 0, &mv, sizeof(mv));
        draw_characters(pass, main_characters, true);
        for (std::size_t mi = 0; mi < d.skinned.size(); ++mi) {
            if (d.skinned[mi].accessory_bit == ~0u) {
                stats_.characters_drawn += main_characters[mi].count;
            }
        }
    }
    // Water last: it is see-through.
    TerrainLayer::WaterLook water;
    water.sun_direction = sun;
    water.sun_color = lighting.sun_color;
    water.fog_color = lighting.horizon_color;
    water.fog_density = su.fog_color[3];
    water.eye = view.eye;
    water.time = view.time;
    water.ice = view.ice;
    water.war = war_bind.data();
    std::copy(std::begin(su.war_params), std::end(su.war_params), water.war_params);
    d.terrain.draw_water(frame.cmd, pass, view_proj, water);
    const TerrainStats& ts = d.terrain.stats();
    stats_.terrain_chunks = ts.chunks_drawn;
    stats_.grass_tufts = ts.grass_tufts;
    stats_.water_chunks = ts.water_chunks_drawn;
    stats_.draw_calls += ts.draw_calls;
    stats_.triangles += ts.triangles;
    SDL_EndGPURenderPass(pass);
    if (blur) {
        // Across into post_b, then down into the swapchain, a little darker.
        const float px = view.blur * static_cast<float>(frame.height) / 1080.0f;
        const struct {
            SDL_GPUTexture* from;
            SDL_GPUTexture* to;
            float step[4];
        } passes[2] = {{d.post_a, d.post_b, {px / static_cast<float>(frame.width), 0.0f, 0.0f, 0.0f}},
                       {d.post_b, frame.target, {0.0f, px / static_cast<float>(frame.height), 0.25f, 0.0f}}};
        for (const auto& bp : passes) {
            SDL_GPUColorTargetInfo bt{};
            bt.texture = bp.to;
            bt.load_op = SDL_GPU_LOADOP_DONT_CARE;
            bt.store_op = SDL_GPU_STOREOP_STORE;
            SDL_GPURenderPass* blur_pass = SDL_BeginGPURenderPass(frame.cmd, &bt, 1, nullptr);
            if (blur_pass == nullptr) {
                return false;
            }
            SDL_BindGPUGraphicsPipeline(blur_pass, d.blur_pipeline);
            const SDL_GPUTextureSamplerBinding binding{bp.from, d.clamp_sampler};
            SDL_BindGPUFragmentSamplers(blur_pass, 0, &binding, 1);
            SDL_PushGPUFragmentUniformData(frame.cmd, 0, bp.step, sizeof(bp.step));
            SDL_DrawGPUPrimitives(blur_pass, 3, 1, 0, 0);
            SDL_EndGPURenderPass(blur_pass);
            ++stats_.draw_calls;
        }
    }
    return true;
}

}  // namespace sc::render
