#include "render/scene_renderer.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstring>

#include <SDL3/SDL_error.h>

#include "core/log.h"
#include "shaders/mesh_frag_dxil.h"
#include "shaders/mesh_vert_dxil.h"
#include "shaders/shadow_frag_dxil.h"
#include "shaders/shadow_vert_dxil.h"
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
};

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

struct GpuModel {
    SDL_GPUBuffer* vertices = nullptr;
    SDL_GPUBuffer* indices = nullptr;
    std::vector<ModelPrimitive> primitives;
    std::vector<GpuMaterial> materials;
    std::vector<SDL_GPUTexture*> textures;
    float radius = 1.0f;
    std::uint64_t triangles = 0;
    std::vector<Instance> instances;
};

struct Range {
    std::uint32_t first = 0;
    std::uint32_t count = 0;
};

}  // namespace

float draw_distance_for_level(int level) {
    constexpr float kDistances[] = {300.0f, 600.0f, 1200.0f, 2500.0f};
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
    std::uint32_t target_w = 0;
    std::uint32_t target_h = 0;

    SDL_GPUBuffer* instance_buffer = nullptr;  // Storage: all instances.
    std::uint32_t instance_capacity = 0;
    bool instances_dirty = true;
    SDL_GPUBuffer* visible_buffer = nullptr;   // Vertex: visible indices.
    std::uint32_t visible_capacity = 0;
    SDL_GPUTransferBuffer* transfer = nullptr;
    std::uint32_t transfer_capacity = 0;

    std::vector<GpuModel> models;
    std::vector<std::uint32_t> visible;  // Global instance indices.
    std::vector<GpuInstance> gpu_instances;

    GraphicsSettings graphics;
    int samples = 1;
    int cascades = 0;
    int shadow_size = 0;
    float draw_distance = 1200.0f;

    ~Impl() { release_all(); }

    void release_targets() {
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
        mesh_pipeline = sky_pipeline = shadow_pipeline = nullptr;
    }

    void release_all() {
        if (device == nullptr) {
            return;
        }
        release_targets();
        release_pipelines();
        for (GpuModel& m : models) {
            SDL_ReleaseGPUBuffer(device, m.vertices);
            SDL_ReleaseGPUBuffer(device, m.indices);
            for (SDL_GPUTexture* t : m.textures) {
                SDL_ReleaseGPUTexture(device, t);
            }
        }
        models.clear();
        SDL_ReleaseGPUSampler(device, base_sampler);
        SDL_ReleaseGPUSampler(device, shadow_sampler);
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
        SDL_GPUShader* mesh_vs = make_shader(device, kMeshVertDxil, kMeshVertDxil_size, SDL_GPU_SHADERSTAGE_VERTEX, 0, 1, 1);
        SDL_GPUShader* mesh_fs = make_shader(device, kMeshFragDxil, kMeshFragDxil_size, SDL_GPU_SHADERSTAGE_FRAGMENT, 2, 0, 2);
        SDL_GPUShader* sky_vs = make_shader(device, kSkyVertDxil, kSkyVertDxil_size, SDL_GPU_SHADERSTAGE_VERTEX, 0, 0, 0);
        SDL_GPUShader* sky_fs = make_shader(device, kSkyFragDxil, kSkyFragDxil_size, SDL_GPU_SHADERSTAGE_FRAGMENT, 0, 0, 1);
        SDL_GPUShader* shadow_vs = make_shader(device, kShadowVertDxil, kShadowVertDxil_size, SDL_GPU_SHADERSTAGE_VERTEX, 0, 1, 1);
        SDL_GPUShader* shadow_fs = make_shader(device, kShadowFragDxil, kShadowFragDxil_size, SDL_GPU_SHADERSTAGE_FRAGMENT, 0, 0, 0);
        const bool shaders_ok = mesh_vs && mesh_fs && sky_vs && sky_fs && shadow_vs && shadow_fs;

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
        }
        for (SDL_GPUShader* s : {mesh_vs, mesh_fs, sky_vs, sky_fs, shadow_vs, shadow_fs}) {
            SDL_ReleaseGPUShader(device, s);
        }
        if (mesh_pipeline == nullptr || sky_pipeline == nullptr || shadow_pipeline == nullptr) {
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

    void rebuild_instance_data() {
        gpu_instances.clear();
        for (const GpuModel& m : models) {
            for (const Instance& inst : m.instances) {
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
                set4(g.tint, inst.tint, 1.0f);
                gpu_instances.push_back(g);
            }
        }
    }

    // Appends the visible instances of each model to `visible` and returns
    // one range per model.
    std::vector<Range> cull(const math::Frustum& frustum, const math::Vec3* eye, float max_distance) {
        std::vector<Range> ranges(models.size());
        std::uint32_t global = 0;
        const float max_d2 = max_distance * max_distance;
        for (std::size_t mi = 0; mi < models.size(); ++mi) {
            const GpuModel& m = models[mi];
            ranges[mi].first = static_cast<std::uint32_t>(visible.size());
            for (const Instance& inst : m.instances) {
                const float r = m.radius * inst.scale;
                bool keep = frustum.sphere_visible(inst.position, r);
                if (keep && eye != nullptr) {
                    const math::Vec3 d = inst.position - *eye;
                    const float reach = std::sqrt(max_d2) + r;
                    keep = math::dot(d, d) <= reach * reach;
                }
                if (keep) {
                    visible.push_back(global);
                }
                ++global;
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
    d.samples = samples;
    d.cascades = cascades;
    d.shadow_size = shadow_size;
    stats_.msaa_samples = samples;
    stats_.shadow_cascades = cascades;
    stats_.shadow_map_size = shadow_size;
    stats_.draw_distance = d.draw_distance;

    bool ok = true;
    if (shadows_changed) {
        ok = d.create_shadow_map() && ok;
    }
    if (pipelines_changed) {
        d.release_targets();
        ok = d.create_pipelines() && ok;
    }
    log::info("scene: msaa {}x, shadows {} cascade(s) at {} px, draw distance {} m", samples, cascades, shadow_size,
              d.draw_distance);
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
    }
    m.primitives = data.primitives;
    m.radius = std::max(0.01f, data.radius);
    m.triangles = data.indices.size() / 3;
    id = static_cast<ModelId>(d.models.size());
    d.models.push_back(std::move(m));
    return true;
}

void SceneRenderer::set_instances(ModelId model, std::span<const Instance> instances) {
    if (model < impl_->models.size()) {
        impl_->models[model].instances.assign(instances.begin(), instances.end());
        impl_->instances_dirty = true;
    }
}

void SceneRenderer::clear_instances() {
    for (GpuModel& m : impl_->models) {
        m.instances.clear();
    }
    impl_->instances_dirty = true;
}

bool SceneRenderer::render(GpuFrame& frame, const SceneView& view, const Lighting& lighting) {
    Impl& d = *impl_;
    stats_ = RenderStats{0, 0, 0, 0, 0, 0.0f, d.samples, d.cascades, d.shadow_size, d.draw_distance};
    if (frame.target == nullptr || d.mesh_pipeline == nullptr || !d.ensure_targets(frame.width, frame.height)) {
        return false;
    }
    const auto t0 = std::chrono::steady_clock::now();
    const float draw_distance = view.draw_distance_override > 0.0f ? view.draw_distance_override : d.draw_distance;
    stats_.draw_distance = draw_distance;

    // Camera matrices.
    const math::Mat4 proj = math::perspective_reverse_z(view.fov_y, view.aspect, view.near_z, draw_distance);
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

    // Culling.
    d.visible.clear();
    const std::vector<Range> main_ranges = d.cull(frustum, &view.eye, draw_distance);
    std::vector<Range> shadow_ranges[kMaxCascades];
    for (int c = 0; c < d.cascades; ++c) {
        shadow_ranges[c] = d.cull(math::Frustum::from_matrix(cascade_vp[c]), nullptr, 0.0f);
    }
    stats_.cull_ms = std::chrono::duration<float, std::milli>(std::chrono::steady_clock::now() - t0).count();

    // Uploads: instances when the scene changed, visible indices always.
    if (d.instances_dirty) {
        d.rebuild_instance_data();
    }
    stats_.instances_total = static_cast<std::uint32_t>(d.gpu_instances.size());
    const auto instance_bytes = static_cast<std::uint32_t>(d.gpu_instances.size() * sizeof(GpuInstance));
    const auto visible_bytes = static_cast<std::uint32_t>(d.visible.size() * sizeof(std::uint32_t));
    const std::uint32_t upload_instances = d.instances_dirty ? instance_bytes : 0;
    if (!d.ensure_transfer(upload_instances + visible_bytes + 16) ||
        !d.ensure_buffer(d.visible_buffer, d.visible_capacity, visible_bytes + 16, SDL_GPU_BUFFERUSAGE_VERTEX) ||
        !d.ensure_buffer(d.instance_buffer, d.instance_capacity, instance_bytes + 64,
                         SDL_GPU_BUFFERUSAGE_GRAPHICS_STORAGE_READ)) {
        return false;
    }
    if (upload_instances + visible_bytes > 0) {
        auto* mapped = static_cast<std::uint8_t*>(SDL_MapGPUTransferBuffer(d.device, d.transfer, true));
        if (mapped == nullptr) {
            return false;
        }
        std::memcpy(mapped, d.visible.data(), visible_bytes);
        if (upload_instances > 0) {
            std::memcpy(mapped + visible_bytes, d.gpu_instances.data(), upload_instances);
        }
        SDL_UnmapGPUTransferBuffer(d.device, d.transfer);
        SDL_GPUCopyPass* copy = SDL_BeginGPUCopyPass(frame.cmd);
        if (visible_bytes > 0) {
            const SDL_GPUTransferBufferLocation src{d.transfer, 0};
            const SDL_GPUBufferRegion dst{d.visible_buffer, 0, visible_bytes};
            SDL_UploadToGPUBuffer(copy, &src, &dst, true);
        }
        if (upload_instances > 0) {
            const SDL_GPUTransferBufferLocation src{d.transfer, visible_bytes};
            const SDL_GPUBufferRegion dst{d.instance_buffer, 0, upload_instances};
            SDL_UploadToGPUBuffer(copy, &src, &dst, false);
            d.instances_dirty = false;
        }
        SDL_EndGPUCopyPass(copy);
    }

    // Draws every model's visible instances; `with_materials` binds colors.
    const auto draw_models = [&](SDL_GPURenderPass* pass, const std::vector<Range>& ranges, bool with_materials) {
        SDL_BindGPUVertexStorageBuffers(pass, 0, &d.instance_buffer, 1);
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
                    const GpuMaterial& mat = m.materials[std::min<std::size_t>(p.material, m.materials.size() - 1)];
                    MaterialUniforms mu{};
                    std::copy(std::begin(mat.base_color), std::end(mat.base_color), mu.base_color);
                    SDL_PushGPUFragmentUniformData(frame.cmd, 1, &mu, sizeof(mu));
                    const SDL_GPUTextureSamplerBinding bindings[2] = {{mat.texture, d.base_sampler},
                                                                      {d.shadow_map, d.shadow_sampler}};
                    SDL_BindGPUFragmentSamplers(pass, 0, bindings, 2);
                }
                SDL_DrawGPUIndexedPrimitives(pass, p.index_count, r.count, p.first_index, 0, 0);
                ++stats_.draw_calls;
                stats_.triangles += static_cast<std::uint64_t>(p.index_count / 3) * r.count;
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
        SDL_EndGPURenderPass(pass);
    }

    // Main pass.
    SDL_GPUColorTargetInfo ct{};
    const math::Vec3 horizon = lighting.horizon_color;
    ct.clear_color = SDL_FColor{horizon.x, horizon.y, horizon.z, 1.0f};
    ct.load_op = SDL_GPU_LOADOP_CLEAR;
    if (d.samples > 1) {
        ct.texture = d.color_msaa;
        ct.resolve_texture = frame.target;
        ct.store_op = SDL_GPU_STOREOP_RESOLVE;
    } else {
        ct.texture = frame.target;
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
    set4(su.fog_color, lighting.horizon_color, 3.32f / (draw_distance * draw_distance));
    set4(su.camera_position, view.eye, static_cast<float>(d.cascades));
    su.shadow_params[0] = d.shadow_size > 0 ? 1.0f / static_cast<float>(d.shadow_size) : 0.0f;
    su.shadow_params[1] = 0.0002f;
    SDL_BindGPUGraphicsPipeline(pass, d.mesh_pipeline);
    const MeshVertexUniforms mv{view_proj};
    SDL_PushGPUVertexUniformData(frame.cmd, 0, &mv, sizeof(mv));
    SDL_PushGPUFragmentUniformData(frame.cmd, 0, &su, sizeof(su));
    draw_models(pass, main_ranges, true);
    for (const Range& r : main_ranges) {
        stats_.instances_drawn += r.count;
    }
    SDL_EndGPURenderPass(pass);
    return true;
}

}  // namespace sc::render
