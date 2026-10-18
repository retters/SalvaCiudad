#include "render/rml_renderer.h"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstring>

#include <SDL3/SDL_error.h>

#include <RmlUi/Core/Core.h>
#include <RmlUi/Core/DecorationTypes.h>
#include <RmlUi/Core/Dictionary.h>
#include <RmlUi/Core/FileInterface.h>

#include "core/log.h"
#include "shaders/blur_frag_dxil.h"
#include "shaders/rml_blur_frag_dxil.h"
#include "shaders/rml_frag_dxil.h"
#include "shaders/rml_gradient_frag_dxil.h"
#include "shaders/rml_post_frag_dxil.h"
#include "shaders/rml_quad_vert_dxil.h"
#include "shaders/rml_vert_dxil.h"
#include "stb_image.h"

namespace sc {

namespace rml_fx {

BlurPlan blur_plan(float sigma) {
    // RmlUi's GL3 renderer: halve until one pass of at most three pixels does.
    constexpr int kMaxLevels = 10;
    BlurPlan plan;
    if (!(sigma > 0.0f)) {
        return plan;
    }
    sigma = std::min(sigma, kMaxSigma);
    const int ratio = static_cast<int>(sigma * (2.0f / kMaxSinglePassSigma));
    int levels = 0;
    while (levels < kMaxLevels && (2 << levels) <= ratio) {
        ++levels;
    }
    plan.levels = levels;
    plan.sigma = std::clamp(sigma / static_cast<float>(1 << levels), 0.0f, kMaxSinglePassSigma);
    return plan;
}

std::array<float, 4> blur_weights(float sigma) {
    std::array<float, 4> w{};
    float total = 0.0f;
    for (int i = 0; i < 4; ++i) {
        if (std::abs(sigma) < 0.1f) {
            w[static_cast<std::size_t>(i)] = i == 0 ? 1.0f : 0.0f;
        } else {
            w[static_cast<std::size_t>(i)] = std::exp(-static_cast<float>(i * i) / (2.0f * sigma * sigma));
        }
        total += (i == 0 ? 1.0f : 2.0f) * w[static_cast<std::size_t>(i)];
    }
    for (float& x : w) {
        x /= total;
    }
    return w;
}

BackdropPlan backdrop_plan(float sigma) {
    // The engine's nine taps are a Gaussian of about 1.8 taps. Taps more than
    // 1.5 reduced pixels apart leave streaks, so the picture is halved again
    // until one or two rounds do (each round multiplies the blur by about the
    // square root of 2); at the smallest size, up to four rounds.
    constexpr float kTapSigma = 1.8f;
    constexpr float kMaxStep = 1.5f;
    constexpr int kMaxPasses = 4;
    BackdropPlan plan;
    if (!(sigma > 0.0f)) {
        return plan;
    }
    sigma = std::min(sigma, kMaxSigma);
    for (int levels = 1; levels <= kMaxBackdropLevels; ++levels) {
        const float one = sigma / (kTapSigma * static_cast<float>(1 << levels));
        int passes = 1;
        while (passes < kMaxPasses && one / std::sqrt(static_cast<float>(passes)) > kMaxStep) {
            ++passes;
        }
        if (passes <= 2 || levels == kMaxBackdropLevels) {
            plan.levels = levels;
            plan.passes = passes;
            plan.step = std::min(one / std::sqrt(static_cast<float>(passes)), kMaxStep);
            return plan;
        }
    }
    return plan;
}

}  // namespace rml_fx

namespace {

struct VertexUniforms {
    float transform[16];
    float translation[2];
    float unused[2];
};

struct FragmentUniforms {
    float mode;
    float unused[3];
};

struct QuadUniforms {
    float uv_transform[4];
};

struct PostUniforms {
    float mode = 0.0f;
    float factor = 1.0f;
    float unused[2]{};
    float color[4]{};
    float limits[4]{};
    float matrix[16]{1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1};
};

struct BlurUniforms {
    float weights[4];
    float limits[4];
    float offset[2];
    float unused[2];
};

struct GradientUniforms {
    int func;
    int num_stops;
    float p[2];
    float v[2];
    float unused[2];
    float stop_colors[RmlRenderer::kMaxStops][4];
    float stop_positions[RmlRenderer::kMaxStops];
};

constexpr float kModeColor = 0.0f;
constexpr float kModeTexture = 1.0f;
constexpr float kModeAtlas = 2.0f;

constexpr float kPostCopy = 0.0f;
constexpr float kPostMatrix = 1.0f;
constexpr float kPostShadow = 2.0f;
constexpr float kPostMask = 3.0f;

constexpr SDL_GPUTextureFormat kLayerFormat = SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM;

SDL_GPUShader* create_shader(SDL_GPUDevice* device, const std::uint8_t* code, std::size_t size,
                             SDL_GPUShaderStage stage, std::uint32_t samplers) {
    SDL_GPUShaderCreateInfo info{};
    info.code = code;
    info.code_size = size;
    info.entrypoint = "main";
    info.format = SDL_GPU_SHADERFORMAT_DXIL;
    info.stage = stage;
    info.num_samplers = samplers;
    info.num_uniform_buffers = 1;
    SDL_GPUShader* shader = SDL_CreateGPUShader(device, &info);
    if (shader == nullptr) {
        log::error("rml renderer: SDL_CreateGPUShader failed: {}", SDL_GetError());
    }
    return shader;
}

std::uint32_t grow(std::uint32_t needed) {
    std::uint32_t cap = 64u * 1024u;
    while (cap < needed) {
        cap *= 2;
    }
    return cap;
}

bool finite(float x) {
    return std::isfinite(x);
}

bool finite(Rml::Vector2f v) {
    return std::isfinite(v.x) && std::isfinite(v.y);
}

void to_float(Rml::ColourbPremultiplied c, float out[4]) {
    for (int i = 0; i < 4; ++i) {
        out[i] = static_cast<float>(c[i]) / 255.0f;
    }
}

bool empty(const SDL_Rect& r) {
    return r.w <= 0 || r.h <= 0;
}

// Texture coordinates of a rectangle's pixel centers, clamped inside it.
void limits_of(const SDL_Rect& r, int width, int height, float out[4]) {
    out[0] = (static_cast<float>(r.x) + 0.5f) / static_cast<float>(width);
    out[1] = (static_cast<float>(r.y) + 0.5f) / static_cast<float>(height);
    out[2] = (static_cast<float>(r.x + r.w) - 0.5f) / static_cast<float>(width);
    out[3] = (static_cast<float>(r.y + r.h) - 0.5f) / static_cast<float>(height);
}

}  // namespace

RmlRenderer::~RmlRenderer() {
    destroy();
}

bool RmlRenderer::create(GpuDevice& gpu, SDL_GPUTexture* atlas, Rml::TextureHandle atlas_handle) {
    device_ = gpu.device();
    atlas_ = atlas;
    atlas_handle_ = atlas_handle;
    for (const SDL_GPUTextureFormat f : {SDL_GPU_TEXTUREFORMAT_D24_UNORM_S8_UINT, SDL_GPU_TEXTUREFORMAT_D32_FLOAT_S8_UINT}) {
        if (SDL_GPUTextureSupportsFormat(device_, f, SDL_GPU_TEXTURETYPE_2D, SDL_GPU_TEXTUREUSAGE_DEPTH_STENCIL_TARGET)) {
            stencil_format_ = f;
            break;
        }
    }
    if (stencil_format_ == SDL_GPU_TEXTUREFORMAT_INVALID) {
        log::error("rml renderer: no stencil format");
        device_ = nullptr;
        return false;
    }
    SDL_GPUSamplerCreateInfo si{};
    si.min_filter = SDL_GPU_FILTER_LINEAR;
    si.mag_filter = SDL_GPU_FILTER_LINEAR;
    si.mipmap_mode = SDL_GPU_SAMPLERMIPMAPMODE_NEAREST;
    si.address_mode_u = SDL_GPU_SAMPLERADDRESSMODE_CLAMP_TO_EDGE;
    si.address_mode_v = SDL_GPU_SAMPLERADDRESSMODE_CLAMP_TO_EDGE;
    si.address_mode_w = SDL_GPU_SAMPLERADDRESSMODE_CLAMP_TO_EDGE;
    sampler_ = SDL_CreateGPUSampler(device_, &si);
    si.address_mode_u = SDL_GPU_SAMPLERADDRESSMODE_REPEAT;
    si.address_mode_v = SDL_GPU_SAMPLERADDRESSMODE_REPEAT;
    si.address_mode_w = SDL_GPU_SAMPLERADDRESSMODE_REPEAT;
    repeat_sampler_ = SDL_CreateGPUSampler(device_, &si);
    if (sampler_ == nullptr || repeat_sampler_ == nullptr || !create_pipelines(gpu.swapchain_format())) {
        log::error("rml renderer: cannot create its pipelines: {}", SDL_GetError());
        destroy();
        return false;
    }
    return true;
}

bool RmlRenderer::create_pipelines(SDL_GPUTextureFormat swapchain_format) {
    SDL_GPUShader* vs = create_shader(device_, kRmlVertDxil, kRmlVertDxil_size, SDL_GPU_SHADERSTAGE_VERTEX, 0);
    SDL_GPUShader* quad = create_shader(device_, kRmlQuadVertDxil, kRmlQuadVertDxil_size, SDL_GPU_SHADERSTAGE_VERTEX, 0);
    SDL_GPUShader* fs = create_shader(device_, kRmlFragDxil, kRmlFragDxil_size, SDL_GPU_SHADERSTAGE_FRAGMENT, 1);
    SDL_GPUShader* gradient =
        create_shader(device_, kRmlGradientFragDxil, kRmlGradientFragDxil_size, SDL_GPU_SHADERSTAGE_FRAGMENT, 0);
    SDL_GPUShader* post = create_shader(device_, kRmlPostFragDxil, kRmlPostFragDxil_size, SDL_GPU_SHADERSTAGE_FRAGMENT, 2);
    SDL_GPUShader* blur = create_shader(device_, kRmlBlurFragDxil, kRmlBlurFragDxil_size, SDL_GPU_SHADERSTAGE_FRAGMENT, 1);
    SDL_GPUShader* engine_blur = create_shader(device_, kBlurFragDxil, kBlurFragDxil_size, SDL_GPU_SHADERSTAGE_FRAGMENT, 1);
    const auto release = [&] {
        for (SDL_GPUShader* s : {vs, quad, fs, gradient, post, blur, engine_blur}) {
            SDL_ReleaseGPUShader(device_, s);
        }
    };
    if (vs == nullptr || quad == nullptr || fs == nullptr || gradient == nullptr || post == nullptr || blur == nullptr ||
        engine_blur == nullptr) {
        release();
        return false;
    }

    SDL_GPUVertexBufferDescription vb{};
    vb.slot = 0;
    vb.pitch = sizeof(Rml::Vertex);
    vb.input_rate = SDL_GPU_VERTEXINPUTRATE_VERTEX;
    SDL_GPUVertexAttribute attributes[3]{};
    attributes[0] = {0, 0, SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2, offsetof(Rml::Vertex, position)};
    attributes[1] = {1, 0, SDL_GPU_VERTEXELEMENTFORMAT_UBYTE4_NORM, offsetof(Rml::Vertex, colour)};
    attributes[2] = {2, 0, SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2, offsetof(Rml::Vertex, tex_coord)};

    enum class Blend { Replace, Over, NoColor };
    enum class Stencil { None, Off, Test, Replace, Increment };
    const auto make = [&](SDL_GPUShader* v, SDL_GPUShader* f, bool vertices, SDL_GPUTextureFormat format, Blend blend,
                          Stencil stencil) -> SDL_GPUGraphicsPipeline* {
        SDL_GPUColorTargetDescription target{};
        target.format = format;
        if (blend == Blend::Over) {
            // RmlUi works with premultiplied alpha.
            target.blend_state.enable_blend = true;
            target.blend_state.src_color_blendfactor = SDL_GPU_BLENDFACTOR_ONE;
            target.blend_state.dst_color_blendfactor = SDL_GPU_BLENDFACTOR_ONE_MINUS_SRC_ALPHA;
            target.blend_state.color_blend_op = SDL_GPU_BLENDOP_ADD;
            target.blend_state.src_alpha_blendfactor = SDL_GPU_BLENDFACTOR_ONE;
            target.blend_state.dst_alpha_blendfactor = SDL_GPU_BLENDFACTOR_ONE_MINUS_SRC_ALPHA;
            target.blend_state.alpha_blend_op = SDL_GPU_BLENDOP_ADD;
        } else if (blend == Blend::NoColor) {
            target.blend_state.enable_color_write_mask = true;
            target.blend_state.color_write_mask = 0;
        }
        SDL_GPUGraphicsPipelineCreateInfo pi{};
        pi.vertex_shader = v;
        pi.fragment_shader = f;
        if (vertices) {
            pi.vertex_input_state.vertex_buffer_descriptions = &vb;
            pi.vertex_input_state.num_vertex_buffers = 1;
            pi.vertex_input_state.vertex_attributes = attributes;
            pi.vertex_input_state.num_vertex_attributes = 3;
        }
        pi.primitive_type = SDL_GPU_PRIMITIVETYPE_TRIANGLELIST;
        pi.rasterizer_state.fill_mode = SDL_GPU_FILLMODE_FILL;
        pi.rasterizer_state.cull_mode = SDL_GPU_CULLMODE_NONE;
        pi.target_info.color_target_descriptions = &target;
        pi.target_info.num_color_targets = 1;
        if (stencil != Stencil::None) {
            pi.target_info.has_depth_stencil_target = true;
            pi.target_info.depth_stencil_format = stencil_format_;
            SDL_GPUStencilOpState op{};
            op.fail_op = SDL_GPU_STENCILOP_KEEP;
            op.depth_fail_op = SDL_GPU_STENCILOP_KEEP;
            op.pass_op = SDL_GPU_STENCILOP_KEEP;
            op.compare_op = SDL_GPU_COMPAREOP_ALWAYS;
            if (stencil == Stencil::Test) {
                op.compare_op = SDL_GPU_COMPAREOP_EQUAL;
            } else if (stencil == Stencil::Replace) {
                op.pass_op = SDL_GPU_STENCILOP_REPLACE;
            } else if (stencil == Stencil::Increment) {
                op.pass_op = SDL_GPU_STENCILOP_INCREMENT_AND_CLAMP;
            }
            pi.depth_stencil_state.enable_stencil_test = stencil != Stencil::Off;
            pi.depth_stencil_state.front_stencil_state = op;
            pi.depth_stencil_state.back_stencil_state = op;
            pi.depth_stencil_state.compare_mask = 0xFF;
            pi.depth_stencil_state.write_mask = (stencil == Stencil::Replace || stencil == Stencil::Increment) ? 0xFF : 0;
        }
        return SDL_CreateGPUGraphicsPipeline(device_, &pi);
    };

    pipelines_[kGeometry] = make(vs, fs, true, kLayerFormat, Blend::Over, Stencil::Off);
    pipelines_[kGeometryClip] = make(vs, fs, true, kLayerFormat, Blend::Over, Stencil::Test);
    pipelines_[kGradient] = make(vs, gradient, true, kLayerFormat, Blend::Over, Stencil::Off);
    pipelines_[kGradientClip] = make(vs, gradient, true, kLayerFormat, Blend::Over, Stencil::Test);
    pipelines_[kClipReplace] = make(vs, fs, true, kLayerFormat, Blend::NoColor, Stencil::Replace);
    pipelines_[kClipIncrement] = make(vs, fs, true, kLayerFormat, Blend::NoColor, Stencil::Increment);
    pipelines_[kCopy] = make(quad, post, false, kLayerFormat, Blend::Replace, Stencil::Off);
    pipelines_[kCopyClip] = make(quad, post, false, kLayerFormat, Blend::Replace, Stencil::Test);
    pipelines_[kBlend] = make(quad, post, false, kLayerFormat, Blend::Over, Stencil::Off);
    pipelines_[kBlendClip] = make(quad, post, false, kLayerFormat, Blend::Over, Stencil::Test);
    pipelines_[kPost] = make(quad, post, false, kLayerFormat, Blend::Replace, Stencil::Off);
    pipelines_[kBlur] = make(quad, blur, false, kLayerFormat, Blend::Replace, Stencil::Off);
    pipelines_[kHalfCopy] = make(quad, post, false, kLayerFormat, Blend::Replace, Stencil::None);
    pipelines_[kHalfBlur] = make(quad, engine_blur, false, kLayerFormat, Blend::Replace, Stencil::None);
    pipelines_[kFinal] = make(quad, post, false, swapchain_format, Blend::Over, Stencil::None);
    release();
    return std::all_of(pipelines_.begin(), pipelines_.end(), [](SDL_GPUGraphicsPipeline* p) { return p != nullptr; });
}

void RmlRenderer::release_targets() {
    for (SDL_GPUTexture* t : layers_) {
        SDL_ReleaseGPUTexture(device_, t);
    }
    layers_.clear();
    for (SDL_GPUTexture*& t : post_) {
        SDL_ReleaseGPUTexture(device_, t);
        t = nullptr;
    }
    for (auto& level : down_) {
        for (SDL_GPUTexture*& t : level) {
            SDL_ReleaseGPUTexture(device_, t);
            t = nullptr;
        }
    }
    SDL_ReleaseGPUTexture(device_, mask_);
    SDL_ReleaseGPUTexture(device_, stencil_);
    mask_ = nullptr;
    stencil_ = nullptr;
    target_w_ = target_h_ = 0;
}

void RmlRenderer::destroy() {
    if (device_ == nullptr) {
        return;
    }
    for (SDL_GPUGraphicsPipeline*& p : pipelines_) {
        SDL_ReleaseGPUGraphicsPipeline(device_, p);
        p = nullptr;
    }
    for (auto& [handle, t] : textures_) {
        if (!t.external) {
            SDL_ReleaseGPUTexture(device_, t.texture);
        }
        t.texture = nullptr;
    }
    textures_.clear();
    geometries_.clear();
    release_targets();
    SDL_ReleaseGPUSampler(device_, sampler_);
    SDL_ReleaseGPUSampler(device_, repeat_sampler_);
    SDL_ReleaseGPUBuffer(device_, vertex_buffer_);
    SDL_ReleaseGPUBuffer(device_, index_buffer_);
    SDL_ReleaseGPUTransferBuffer(device_, transfer_);
    sampler_ = nullptr;
    repeat_sampler_ = nullptr;
    vertex_buffer_ = nullptr;
    index_buffer_ = nullptr;
    transfer_ = nullptr;
    vertex_capacity_ = index_capacity_ = transfer_capacity_ = 0;
    device_ = nullptr;
}

// --- Recording -------------------------------------------------------------

void RmlRenderer::begin_frame(int width, int height) {
    width_ = std::max(width, 1);
    height_ = std::max(height, 1);
    transforms_.clear();
    transforms_.push_back(Rml::Matrix4f::ProjectOrtho(0.0f, static_cast<float>(width_), static_cast<float>(height_),
                                                      0.0f, -10000.0f, 10000.0f));
    transform_ = 0;
    scissor_on_ = false;
    clip_on_ = false;
    clip_ref_ = 0;
    top_ = 0;
    frame_vertices_.clear();
    frame_indices_.clear();
    commands_.clear();
    frame_filters_.clear();
    gradients_.clear();
    backdrop_sigma_ = 0.0f;
    stats_ = Stats{};
    stats_.layers = 1;
    replayed_ = false;
}

SDL_Rect RmlRenderer::current_scissor() const {
    return scissor_on_ ? scissor_ : SDL_Rect{0, 0, width_, height_};
}

Rml::CompiledGeometryHandle RmlRenderer::CompileGeometry(Rml::Span<const Rml::Vertex> vertices,
                                                         Rml::Span<const int> indices) {
    const Rml::CompiledGeometryHandle handle = next_geometry_++;
    Geometry& g = geometries_[handle];
    g.vertices.assign(vertices.begin(), vertices.end());
    g.indices.assign(indices.begin(), indices.end());
    return handle;
}

void RmlRenderer::record_draw(Rml::CompiledGeometryHandle geometry, Rml::Vector2f translation,
                              Rml::TextureHandle texture, int gradient) {
    const auto it = geometries_.find(geometry);
    if (it == geometries_.end() || it->second.indices.empty()) {
        return;
    }
    const Geometry& g = it->second;
    const auto base = static_cast<std::uint32_t>(frame_vertices_.size());
    Command c;
    c.op = Op::Draw;
    c.layer = top_;
    c.scissor = current_scissor();
    c.clip = clip_on_;
    c.ref = clip_ref_;
    c.first_index = static_cast<std::uint32_t>(frame_indices_.size());
    c.index_count = static_cast<std::uint32_t>(g.indices.size());
    c.texture = texture;
    c.translation = translation;
    c.transform = transform_;
    c.gradient = gradient;
    frame_vertices_.insert(frame_vertices_.end(), g.vertices.begin(), g.vertices.end());
    for (const int i : g.indices) {
        frame_indices_.push_back(base + static_cast<std::uint32_t>(i));
    }
    commands_.push_back(c);
    ++stats_.draws;
}

void RmlRenderer::RenderGeometry(Rml::CompiledGeometryHandle geometry, Rml::Vector2f translation,
                                 Rml::TextureHandle texture) {
    record_draw(geometry, translation, texture, -1);
}

void RmlRenderer::ReleaseGeometry(Rml::CompiledGeometryHandle geometry) {
    geometries_.erase(geometry);
}

Rml::TextureHandle RmlRenderer::add_texture(std::vector<std::uint8_t> rgba, int width, int height) {
    const Rml::TextureHandle handle = next_texture_++;
    Texture& t = textures_[handle];
    t.width = width;
    t.height = height;
    t.pending = std::move(rgba);
    return handle;
}

Rml::TextureHandle RmlRenderer::LoadTexture(Rml::Vector2i& texture_dimensions, const Rml::String& source) {
    if (source.starts_with("ext/")) {
        const External& e = externals_[source.substr(4)];
        const Rml::TextureHandle handle = next_texture_++;
        Texture& t = textures_[handle];
        t.texture = e.texture;
        t.width = e.width;
        t.height = e.height;
        t.external = true;
        pictures_[source].push_back(handle);
        texture_dimensions = Rml::Vector2i(e.width, e.height);
        return handle;
    }
    if (source.starts_with("live/")) {
        const std::string name = source.substr(5);
        const Live& l = live_[name];
        const Rml::TextureHandle handle = add_texture(l.rgba, l.width, l.height);
        pictures_[source].push_back(handle);
        texture_dimensions = Rml::Vector2i(l.width, l.height);
        return handle;
    }
    if (source.starts_with("thumbs/")) {
        // A picture the game renders: empty until it comes.
        const std::string key = source.substr(7);
        if (key.empty() || key.size() > 200) {
            return 0;
        }
        const Rml::TextureHandle handle = next_texture_++;
        Texture& t = textures_[handle];
        t.width = kPictureSize;
        t.height = kPictureSize;
        pictures_[key].push_back(handle);
        picture_requests_.push_back(key);
        texture_dimensions = Rml::Vector2i(kPictureSize, kPictureSize);
        return handle;
    }
    Rml::FileInterface* files = Rml::GetFileInterface();
    Rml::String bytes;
    if (files == nullptr || !files->LoadFile(source, bytes) || bytes.empty() ||
        bytes.size() > static_cast<std::size_t>(64 * 1024 * 1024)) {
        return 0;
    }
    int w = 0;
    int h = 0;
    int channels = 0;
    stbi_uc* pixels = stbi_load_from_memory(reinterpret_cast<const stbi_uc*>(bytes.data()), static_cast<int>(bytes.size()),
                                            &w, &h, &channels, 4);
    if (pixels == nullptr || w < 1 || h < 1 || w > kMaxTextureSize || h > kMaxTextureSize) {
        stbi_image_free(pixels);
        log::warn("rml renderer: cannot decode image '{}'", source);
        return 0;
    }
    const std::size_t count = static_cast<std::size_t>(w) * static_cast<std::size_t>(h);
    std::vector<std::uint8_t> rgba(count * 4);
    for (std::size_t i = 0; i < count; ++i) {
        const std::uint32_t a = pixels[i * 4 + 3];
        for (std::size_t c = 0; c < 3; ++c) {
            rgba[i * 4 + c] = static_cast<std::uint8_t>((pixels[i * 4 + c] * a + 127) / 255);
        }
        rgba[i * 4 + 3] = static_cast<std::uint8_t>(a);
    }
    stbi_image_free(pixels);
    texture_dimensions = Rml::Vector2i(w, h);
    return add_texture(std::move(rgba), w, h);
}

Rml::TextureHandle RmlRenderer::GenerateTexture(Rml::Span<const Rml::byte> source, Rml::Vector2i source_dimensions) {
    const int w = source_dimensions.x;
    const int h = source_dimensions.y;
    if (w < 1 || h < 1 || w > kMaxTextureSize || h > kMaxTextureSize ||
        source.size() != static_cast<std::size_t>(w) * static_cast<std::size_t>(h) * 4) {
        return 0;
    }
    return add_texture(std::vector<std::uint8_t>(source.begin(), source.end()), w, h);
}

std::vector<std::string> RmlRenderer::take_picture_requests() {
    std::vector<std::string> out;
    out.swap(picture_requests_);
    return out;
}

void RmlRenderer::provide_picture(const std::string& key, const std::vector<std::uint8_t>& rgba) {
    const auto it = pictures_.find(key);
    if (it == pictures_.end() ||
        rgba.size() != static_cast<std::size_t>(kPictureSize) * static_cast<std::size_t>(kPictureSize) * 4) {
        return;
    }
    // Handles RmlUi released meanwhile are dropped.
    std::erase_if(it->second, [this](Rml::TextureHandle h) { return !textures_.contains(h); });
    for (const Rml::TextureHandle h : it->second) {
        Texture& t = textures_[h];
        if (t.texture == nullptr && t.pending.empty()) {
            t.pending = rgba;
        }
    }
    if (it->second.empty()) {
        pictures_.erase(it);
    }
}

void RmlRenderer::set_live_image(const std::string& name, int width, int height,
                                 const std::vector<std::uint8_t>& rgba) {
    if (width < 1 || height < 1 || width > kMaxTextureSize || height > kMaxTextureSize ||
        rgba.size() != static_cast<std::size_t>(width) * static_cast<std::size_t>(height) * 4) {
        return;
    }
    Live& l = live_[name];
    l.width = width;
    l.height = height;
    l.rgba = rgba;
    const auto it = pictures_.find("live/" + name);
    if (it == pictures_.end()) {
        return;
    }
    std::erase_if(it->second, [this](Rml::TextureHandle h) { return !textures_.contains(h); });
    for (const Rml::TextureHandle h : it->second) {
        Texture& t = textures_[h];
        if (t.width != width || t.height != height) {
            if (device_ != nullptr) {
                SDL_ReleaseGPUTexture(device_, t.texture);
            }
            t.texture = nullptr;
            t.width = width;
            t.height = height;
        }
        t.pending = rgba;
    }
}

void RmlRenderer::set_external_texture(const std::string& name, SDL_GPUTexture* texture, int width, int height) {
    External& e = externals_[name];
    e.texture = texture;
    e.width = std::max(width, 1);
    e.height = std::max(height, 1);
    const auto it = pictures_.find("ext/" + name);
    if (it == pictures_.end()) {
        return;
    }
    std::erase_if(it->second, [this](Rml::TextureHandle h) { return !textures_.contains(h); });
    for (const Rml::TextureHandle h : it->second) {
        textures_[h].texture = texture;
    }
}

void RmlRenderer::ReleaseTexture(Rml::TextureHandle texture) {
    const auto it = textures_.find(texture);
    if (it == textures_.end()) {
        return;  // Also the atlas, which belongs to the old interface's renderer.
    }
    if (device_ != nullptr && !it->second.external) {
        SDL_ReleaseGPUTexture(device_, it->second.texture);
    }
    textures_.erase(it);
}

void RmlRenderer::EnableScissorRegion(bool enable) {
    scissor_on_ = enable;
}

void RmlRenderer::SetScissorRegion(Rml::Rectanglei region) {
    const int x0 = std::clamp(region.Left(), 0, width_);
    const int y0 = std::clamp(region.Top(), 0, height_);
    const int x1 = std::clamp(region.Right(), x0, width_);
    const int y1 = std::clamp(region.Bottom(), y0, height_);
    scissor_ = SDL_Rect{x0, y0, x1 - x0, y1 - y0};
}

void RmlRenderer::EnableClipMask(bool enable) {
    clip_on_ = enable;
}

void RmlRenderer::record_clip_clear(std::uint8_t value) {
    // The stencil inside the scissor takes `value`: a rectangle over the
    // whole window, drawn into the stencil only.
    const auto base = static_cast<std::uint32_t>(frame_vertices_.size());
    const float w = static_cast<float>(width_);
    const float h = static_cast<float>(height_);
    for (const Rml::Vector2f p : {Rml::Vector2f{0, 0}, Rml::Vector2f{w, 0}, Rml::Vector2f{w, h}, Rml::Vector2f{0, h}}) {
        frame_vertices_.push_back({p, Rml::ColourbPremultiplied(), Rml::Vector2f{}});
    }
    Command c;
    c.op = Op::ClipClear;
    c.layer = top_;
    c.scissor = current_scissor();
    c.ref = value;
    c.first_index = static_cast<std::uint32_t>(frame_indices_.size());
    c.index_count = 6;
    for (const std::uint32_t i : {0u, 1u, 2u, 0u, 2u, 3u}) {
        frame_indices_.push_back(base + i);
    }
    commands_.push_back(c);
}

void RmlRenderer::RenderToClipMask(Rml::ClipMaskOperation operation, Rml::CompiledGeometryHandle geometry,
                                   Rml::Vector2f translation) {
    // As RmlUi's GL3 renderer: Set and SetInverse clear and write, Intersect
    // counts up; afterwards the draws pass where the stencil equals clip_ref_.
    std::uint8_t write = 1;
    bool increment = false;
    switch (operation) {
    case Rml::ClipMaskOperation::Set:
        record_clip_clear(0);
        clip_ref_ = 1;
        break;
    case Rml::ClipMaskOperation::SetInverse:
        record_clip_clear(1);
        write = 0;
        clip_ref_ = 1;
        break;
    case Rml::ClipMaskOperation::Intersect:
        increment = true;
        clip_ref_ = static_cast<std::uint8_t>(std::min(clip_ref_ + 1, 255));
        break;
    }
    const std::size_t before = commands_.size();
    record_draw(geometry, translation, 0, -1);
    if (commands_.size() == before) {
        return;
    }
    Command& c = commands_.back();
    c.op = Op::ClipDraw;
    c.ref = write;
    c.increment = increment;
    c.clip = false;
    --stats_.draws;
    ++stats_.clip_writes;
}

void RmlRenderer::SetTransform(const Rml::Matrix4f* transform) {
    if (transform == nullptr) {
        transform_ = 0;
        return;
    }
    transforms_.push_back(transforms_.front() * *transform);
    transform_ = static_cast<int>(transforms_.size() - 1);
}

Rml::LayerHandle RmlRenderer::PushLayer() {
    if (top_ + 1 >= kMaxLayers) {
        log::warn("rml renderer: more than {} layers; drawing into the last one", kMaxLayers);
        return static_cast<Rml::LayerHandle>(top_);
    }
    ++top_;
    Command c;
    c.op = Op::PushLayer;
    c.layer = top_;
    commands_.push_back(c);
    stats_.layers = std::max(stats_.layers, top_ + 1);
    return static_cast<Rml::LayerHandle>(top_);
}

void RmlRenderer::PopLayer() {
    if (top_ > 0) {
        --top_;
    }
}

void RmlRenderer::CompositeLayers(Rml::LayerHandle source, Rml::LayerHandle destination, Rml::BlendMode blend_mode,
                                  Rml::Span<const Rml::CompiledFilterHandle> filters) {
    const int src = static_cast<int>(source);
    const int dst = static_cast<int>(destination);
    if (src < 0 || dst < 0 || src >= kMaxLayers || dst >= kMaxLayers) {
        return;
    }
    Command c;
    c.op = Op::Composite;
    c.source = src;
    c.layer = dst;
    c.replace = blend_mode == Rml::BlendMode::Replace;
    c.scissor = current_scissor();
    c.clip = clip_on_;
    c.ref = clip_ref_;
    // RmlUi composes a backdrop from a lower layer into a new one; other
    // compositions go from the top layer down.
    c.backdrop = src < dst;
    if (c.backdrop) {
        ++stats_.backdrops;
        if (glass_ == GlassMode::Simple) {
            return;
        }
        stats_.backdrop_blurs = 1;
    }
    c.first_filter = static_cast<std::uint32_t>(frame_filters_.size());
    for (const Rml::CompiledFilterHandle h : filters) {
        const auto it = filters_.find(h);
        if (it == filters_.end()) {
            continue;
        }
        if (c.backdrop && it->second.type == FilterType::Blur) {
            // The shared blur of the scene stands for it.
            backdrop_sigma_ = std::max(backdrop_sigma_, it->second.value);
            continue;
        }
        frame_filters_.push_back(it->second);
    }
    c.filter_count = static_cast<std::uint32_t>(frame_filters_.size()) - c.first_filter;
    commands_.push_back(c);
    ++stats_.composites;
}

Rml::TextureHandle RmlRenderer::SaveLayerAsTexture() {
    const SDL_Rect r = current_scissor();
    if (empty(r) || r.w > kMaxTextureSize || r.h > kMaxTextureSize) {
        return 0;
    }
    const Rml::TextureHandle handle = next_texture_++;
    Texture& t = textures_[handle];
    t.width = r.w;
    t.height = r.h;
    if (device_ != nullptr) {
        SDL_GPUTextureCreateInfo ti{};
        ti.type = SDL_GPU_TEXTURETYPE_2D;
        ti.format = kLayerFormat;
        ti.usage = SDL_GPU_TEXTUREUSAGE_SAMPLER;
        ti.width = static_cast<std::uint32_t>(r.w);
        ti.height = static_cast<std::uint32_t>(r.h);
        ti.layer_count_or_depth = 1;
        ti.num_levels = 1;
        t.texture = SDL_CreateGPUTexture(device_, &ti);
        if (t.texture == nullptr) {
            log::error("rml renderer: cannot create a texture: {}", SDL_GetError());
        }
    }
    Command c;
    c.op = Op::SaveTexture;
    c.layer = top_;
    c.scissor = r;
    c.saved = handle;
    commands_.push_back(c);
    ++stats_.saved_layers;
    return handle;
}

Rml::CompiledFilterHandle RmlRenderer::SaveLayerAsMaskImage() {
    Command c;
    c.op = Op::SaveMask;
    c.layer = top_;
    c.scissor = current_scissor();
    commands_.push_back(c);
    const Rml::CompiledFilterHandle handle = next_effect_++;
    filters_[handle].type = FilterType::MaskImage;
    return handle;
}

Rml::CompiledFilterHandle RmlRenderer::CompileFilter(const Rml::String& name, const Rml::Dictionary& parameters) {
    // As RmlUi's GL3 renderer, with every number checked: a value that is not
    // finite refuses the filter, and big ones are clamped.
    Filter f;
    const auto matrix_rows = [&f](std::array<std::array<float, 3>, 3> rows) {
        f.type = FilterType::ColorMatrix;
        f.matrix = Rml::Matrix4f::FromRows({rows[0][0], rows[0][1], rows[0][2], 0.0f},
                                           {rows[1][0], rows[1][1], rows[1][2], 0.0f},
                                           {rows[2][0], rows[2][1], rows[2][2], 0.0f}, {0.0f, 0.0f, 0.0f, 1.0f});
    };
    const float value = Rml::Get(parameters, "value", 1.0f);
    if (!finite(value)) {
        return 0;
    }
    if (name == "opacity") {
        f.type = FilterType::Opacity;
        f.value = std::clamp(value, 0.0f, 1.0f);
    } else if (name == "blur" || name == "drop-shadow") {
        const float sigma = Rml::Get(parameters, "sigma", name == "blur" ? 1.0f : 0.0f);
        if (!finite(sigma)) {
            return 0;
        }
        f.type = name == "blur" ? FilterType::Blur : FilterType::DropShadow;
        f.value = std::clamp(sigma, 0.0f, rml_fx::kMaxSigma);
        if (f.type == FilterType::DropShadow) {
            const Rml::Vector2f offset = Rml::Get(parameters, "offset", Rml::Vector2f(0.0f));
            if (!finite(offset)) {
                return 0;
            }
            f.offset = {std::clamp(offset.x, -rml_fx::kMaxOffset, rml_fx::kMaxOffset),
                        std::clamp(offset.y, -rml_fx::kMaxOffset, rml_fx::kMaxOffset)};
            f.color = Rml::Get(parameters, "color", Rml::Colourb()).ToPremultiplied();
        }
    } else if (name == "brightness") {
        const float v = std::clamp(value, 0.0f, 16.0f);
        f.type = FilterType::ColorMatrix;
        f.matrix = Rml::Matrix4f::Diag(v, v, v, 1.0f);
    } else if (name == "contrast") {
        const float v = std::clamp(value, 0.0f, 16.0f);
        const float gray = 0.5f - 0.5f * v;
        f.type = FilterType::ColorMatrix;
        f.matrix = Rml::Matrix4f::Diag(v, v, v, 1.0f);
        f.matrix.SetColumn(3, Rml::Vector4f(gray, gray, gray, 1.0f));
    } else if (name == "invert") {
        const float v = std::clamp(value, 0.0f, 1.0f);
        const float inverted = 1.0f - 2.0f * v;
        f.type = FilterType::ColorMatrix;
        f.matrix = Rml::Matrix4f::Diag(inverted, inverted, inverted, 1.0f);
        f.matrix.SetColumn(3, Rml::Vector4f(v, v, v, 1.0f));
    } else if (name == "grayscale") {
        const float v = std::clamp(value, 0.0f, 1.0f);
        const float r = 1.0f - v;
        const float gx = v * 0.2126f;
        const float gy = v * 0.7152f;
        const float gz = v * 0.0722f;
        matrix_rows({{{gx + r, gy, gz}, {gx, gy + r, gz}, {gx, gy, gz + r}}});
    } else if (name == "sepia") {
        const float v = std::clamp(value, 0.0f, 1.0f);
        const float r = 1.0f - v;
        matrix_rows({{{0.393f * v + r, 0.769f * v, 0.189f * v},
                      {0.349f * v, 0.686f * v + r, 0.168f * v},
                      {0.272f * v, 0.534f * v, 0.131f * v + r}}});
    } else if (name == "hue-rotate") {
        const float s = std::sin(value);
        const float c = std::cos(value);
        matrix_rows({{{0.213f + 0.787f * c - 0.213f * s, 0.715f - 0.715f * c - 0.715f * s, 0.072f - 0.072f * c + 0.928f * s},
                      {0.213f - 0.213f * c + 0.143f * s, 0.715f + 0.285f * c + 0.140f * s, 0.072f - 0.072f * c - 0.283f * s},
                      {0.213f - 0.213f * c - 0.787f * s, 0.715f - 0.715f * c + 0.715f * s, 0.072f + 0.928f * c + 0.072f * s}}});
    } else if (name == "saturate") {
        const float v = std::clamp(value, 0.0f, 16.0f);
        matrix_rows({{{0.213f + 0.787f * v, 0.715f - 0.715f * v, 0.072f - 0.072f * v},
                      {0.213f - 0.213f * v, 0.715f + 0.285f * v, 0.072f - 0.072f * v},
                      {0.213f - 0.213f * v, 0.715f - 0.715f * v, 0.072f + 0.928f * v}}});
    } else {
        log::warn("rml renderer: unsupported filter '{}'", name);
        return 0;
    }
    const Rml::CompiledFilterHandle handle = next_effect_++;
    filters_[handle] = f;
    return handle;
}

void RmlRenderer::ReleaseFilter(Rml::CompiledFilterHandle filter) {
    filters_.erase(filter);
}

Rml::CompiledShaderHandle RmlRenderer::CompileShader(const Rml::String& name, const Rml::Dictionary& parameters) {
    Gradient g;
    if (name == "linear-gradient") {
        g.func = 0;
        g.p = Rml::Get(parameters, "p0", Rml::Vector2f(0.0f));
        g.v = Rml::Get(parameters, "p1", Rml::Vector2f(0.0f)) - g.p;
    } else if (name == "radial-gradient") {
        g.func = 1;
        g.p = Rml::Get(parameters, "center", Rml::Vector2f(0.0f));
        const Rml::Vector2f radius = Rml::Get(parameters, "radius", Rml::Vector2f(1.0f));
        if (!(radius.x > 0.0f) || !(radius.y > 0.0f)) {
            return 0;
        }
        g.v = Rml::Vector2f(1.0f) / radius;
    } else if (name == "conic-gradient") {
        g.func = 2;
        g.p = Rml::Get(parameters, "center", Rml::Vector2f(0.0f));
        const float angle = Rml::Get(parameters, "angle", 0.0f);
        g.v = {std::cos(angle), std::sin(angle)};
    } else {
        log::warn("rml renderer: unsupported shader '{}'", name);
        return 0;
    }
    if (Rml::Get(parameters, "repeating", false)) {
        g.func += 3;
    }
    const auto it = parameters.find("color_stop_list");
    if (it == parameters.end() || it->second.GetType() != Rml::Variant::COLORSTOPLIST || !finite(g.p) || !finite(g.v)) {
        return 0;
    }
    const Rml::ColorStopList& stops = it->second.GetReference<Rml::ColorStopList>();
    g.stops = std::min(static_cast<int>(stops.size()), kMaxStops);
    if (g.stops < 1) {
        return 0;
    }
    for (int i = 0; i < g.stops; ++i) {
        const Rml::ColorStop& stop = stops[static_cast<std::size_t>(i)];
        if (stop.position.unit != Rml::Unit::NUMBER || !finite(stop.position.number)) {
            return 0;
        }
        g.positions[static_cast<std::size_t>(i)] = stop.position.number;
        to_float(stop.color, g.colors[static_cast<std::size_t>(i)].data());
    }
    const Rml::CompiledShaderHandle handle = next_effect_++;
    shaders_[handle] = g;
    return handle;
}

void RmlRenderer::RenderShader(Rml::CompiledShaderHandle shader, Rml::CompiledGeometryHandle geometry,
                               Rml::Vector2f translation, Rml::TextureHandle texture) {
    const auto it = shaders_.find(shader);
    if (it == shaders_.end()) {
        return;
    }
    gradients_.push_back(it->second);
    record_draw(geometry, translation, texture, static_cast<int>(gradients_.size()) - 1);
}

void RmlRenderer::ReleaseShader(Rml::CompiledShaderHandle shader) {
    shaders_.erase(shader);
}

// --- GPU -------------------------------------------------------------------

bool RmlRenderer::ensure_buffers(std::uint32_t vertex_bytes, std::uint32_t index_bytes) {
    const auto ensure = [this](SDL_GPUBuffer*& buffer, std::uint32_t& capacity, std::uint32_t needed,
                               SDL_GPUBufferUsageFlags usage) {
        if (buffer != nullptr && capacity >= needed) {
            return true;
        }
        SDL_ReleaseGPUBuffer(device_, buffer);
        SDL_GPUBufferCreateInfo bi{};
        bi.usage = usage;
        bi.size = grow(needed);
        buffer = SDL_CreateGPUBuffer(device_, &bi);
        capacity = buffer != nullptr ? bi.size : 0;
        if (buffer == nullptr) {
            log::error("rml renderer: SDL_CreateGPUBuffer failed: {}", SDL_GetError());
        }
        return buffer != nullptr;
    };
    if (!ensure(vertex_buffer_, vertex_capacity_, vertex_bytes, SDL_GPU_BUFFERUSAGE_VERTEX) ||
        !ensure(index_buffer_, index_capacity_, index_bytes, SDL_GPU_BUFFERUSAGE_INDEX)) {
        return false;
    }
    const std::uint32_t needed = vertex_bytes + index_bytes;
    if (transfer_ != nullptr && transfer_capacity_ >= needed) {
        return true;
    }
    SDL_ReleaseGPUTransferBuffer(device_, transfer_);
    SDL_GPUTransferBufferCreateInfo ti{};
    ti.usage = SDL_GPU_TRANSFERBUFFERUSAGE_UPLOAD;
    ti.size = grow(needed);
    transfer_ = SDL_CreateGPUTransferBuffer(device_, &ti);
    transfer_capacity_ = transfer_ != nullptr ? ti.size : 0;
    if (transfer_ == nullptr) {
        log::error("rml renderer: SDL_CreateGPUTransferBuffer failed: {}", SDL_GetError());
    }
    return transfer_ != nullptr;
}

bool RmlRenderer::ensure_targets(int layers) {
    if (target_w_ != width_ || target_h_ != height_) {
        release_targets();
    }
    const auto make = [this](int w, int h, SDL_GPUTextureFormat format, SDL_GPUTextureUsageFlags usage) {
        SDL_GPUTextureCreateInfo ti{};
        ti.type = SDL_GPU_TEXTURETYPE_2D;
        ti.format = format;
        ti.usage = usage;
        ti.width = static_cast<std::uint32_t>(w);
        ti.height = static_cast<std::uint32_t>(h);
        ti.layer_count_or_depth = 1;
        ti.num_levels = 1;
        SDL_GPUTexture* t = SDL_CreateGPUTexture(device_, &ti);
        if (t == nullptr) {
            log::error("rml renderer: cannot create a target: {}", SDL_GetError());
        }
        return t;
    };
    constexpr SDL_GPUTextureUsageFlags kTarget = SDL_GPU_TEXTUREUSAGE_COLOR_TARGET | SDL_GPU_TEXTUREUSAGE_SAMPLER;
    target_w_ = width_;
    target_h_ = height_;
    while (static_cast<int>(layers_.size()) < layers) {
        SDL_GPUTexture* t = make(width_, height_, kLayerFormat, kTarget);
        if (t == nullptr) {
            return false;
        }
        layers_.push_back(t);
    }
    if (stencil_ == nullptr) {
        stencil_ = make(width_, height_, stencil_format_, SDL_GPU_TEXTUREUSAGE_DEPTH_STENCIL_TARGET);
    }
    for (SDL_GPUTexture*& t : post_) {
        if (t == nullptr) {
            t = make(width_, height_, kLayerFormat, kTarget);
        }
    }
    bool ok = stencil_ != nullptr && std::all_of(post_.begin(), post_.end(), [](SDL_GPUTexture* t) { return t != nullptr; });
    const bool masks = std::any_of(commands_.begin(), commands_.end(), [](const Command& c) { return c.op == Op::SaveMask; });
    if (ok && masks && mask_ == nullptr) {
        mask_ = make(width_, height_, kLayerFormat, kTarget);
        ok = mask_ != nullptr;
    }
    if (ok && stats_.backdrop_blurs > 0) {
        int w = width_;
        int h = height_;
        for (auto& level : down_) {
            w = rml_fx::half(w);
            h = rml_fx::half(h);
            for (SDL_GPUTexture*& t : level) {
                if (t == nullptr) {
                    t = make(w, h, kLayerFormat, kTarget);
                    ok = ok && t != nullptr;
                }
            }
        }
    }
    return ok;
}

bool RmlRenderer::upload(SDL_GPUCommandBuffer* cmd) {
    // New textures first, each with its own transfer buffer (they are rare).
    for (auto& [handle, t] : textures_) {
        if (t.pending.empty()) {
            continue;
        }
        if (t.texture == nullptr) {
            SDL_GPUTextureCreateInfo ti{};
            ti.type = SDL_GPU_TEXTURETYPE_2D;
            ti.format = kLayerFormat;
            ti.usage = SDL_GPU_TEXTUREUSAGE_SAMPLER;
            ti.width = static_cast<std::uint32_t>(t.width);
            ti.height = static_cast<std::uint32_t>(t.height);
            ti.layer_count_or_depth = 1;
            ti.num_levels = 1;
            t.texture = SDL_CreateGPUTexture(device_, &ti);
            if (t.texture == nullptr) {
                log::error("rml renderer: cannot create a texture: {}", SDL_GetError());
                t.pending.clear();
                continue;
            }
        }
        SDL_GPUTransferBufferCreateInfo tb{};
        tb.usage = SDL_GPU_TRANSFERBUFFERUSAGE_UPLOAD;
        tb.size = static_cast<std::uint32_t>(t.pending.size());
        SDL_GPUTransferBuffer* transfer = SDL_CreateGPUTransferBuffer(device_, &tb);
        void* mapped = transfer != nullptr ? SDL_MapGPUTransferBuffer(device_, transfer, false) : nullptr;
        if (mapped == nullptr) {
            log::error("rml renderer: cannot upload a texture: {}", SDL_GetError());
            SDL_ReleaseGPUTransferBuffer(device_, transfer);
            return false;
        }
        std::memcpy(mapped, t.pending.data(), t.pending.size());
        SDL_UnmapGPUTransferBuffer(device_, transfer);
        SDL_GPUCopyPass* copy = SDL_BeginGPUCopyPass(cmd);
        SDL_GPUTextureTransferInfo src{};
        src.transfer_buffer = transfer;
        src.pixels_per_row = static_cast<std::uint32_t>(t.width);
        src.rows_per_layer = static_cast<std::uint32_t>(t.height);
        SDL_GPUTextureRegion dst{};
        dst.texture = t.texture;
        dst.w = static_cast<std::uint32_t>(t.width);
        dst.h = static_cast<std::uint32_t>(t.height);
        dst.d = 1;
        SDL_UploadToGPUTexture(copy, &src, &dst, false);
        SDL_EndGPUCopyPass(copy);
        SDL_ReleaseGPUTransferBuffer(device_, transfer);
        t.pending.clear();
        t.pending.shrink_to_fit();
    }
    if (frame_indices_.empty()) {
        return true;
    }
    const auto vertex_bytes = static_cast<std::uint32_t>(frame_vertices_.size() * sizeof(Rml::Vertex));
    const auto index_bytes = static_cast<std::uint32_t>(frame_indices_.size() * sizeof(std::uint32_t));
    if (!ensure_buffers(vertex_bytes, index_bytes)) {
        return false;
    }
    auto* mapped = static_cast<std::uint8_t*>(SDL_MapGPUTransferBuffer(device_, transfer_, true));
    if (mapped == nullptr) {
        log::error("rml renderer: SDL_MapGPUTransferBuffer failed: {}", SDL_GetError());
        return false;
    }
    std::memcpy(mapped, frame_vertices_.data(), vertex_bytes);
    std::memcpy(mapped + vertex_bytes, frame_indices_.data(), index_bytes);
    SDL_UnmapGPUTransferBuffer(device_, transfer_);
    SDL_GPUCopyPass* copy = SDL_BeginGPUCopyPass(cmd);
    SDL_GPUTransferBufferLocation src{transfer_, 0};
    SDL_GPUBufferRegion dst{vertex_buffer_, 0, vertex_bytes};
    SDL_UploadToGPUBuffer(copy, &src, &dst, true);
    src.offset = vertex_bytes;
    dst = {index_buffer_, 0, index_bytes};
    SDL_UploadToGPUBuffer(copy, &src, &dst, true);
    SDL_EndGPUCopyPass(copy);
    return true;
}

SDL_GPURenderPass* RmlRenderer::target(SDL_GPUTexture* texture, bool clear) {
    if (pass_ != nullptr && pass_target_ == texture && !clear) {
        return pass_;
    }
    end_pass();
    SDL_GPUColorTargetInfo ct{};
    ct.texture = texture;
    ct.clear_color = SDL_FColor{0.0f, 0.0f, 0.0f, 0.0f};
    ct.load_op = clear ? SDL_GPU_LOADOP_CLEAR : SDL_GPU_LOADOP_LOAD;
    ct.store_op = SDL_GPU_STOREOP_STORE;
    // Everything the size of the window shares the stencil; the reduced
    // backdrop textures go without it.
    bool full = true;
    for (const auto& level : down_) {
        full = full && texture != level[0] && texture != level[1];
    }
    SDL_GPUDepthStencilTargetInfo ds{};
    ds.texture = stencil_;
    ds.load_op = SDL_GPU_LOADOP_DONT_CARE;
    ds.store_op = SDL_GPU_STOREOP_DONT_CARE;
    ds.stencil_load_op = stencil_cleared_ ? SDL_GPU_LOADOP_LOAD : SDL_GPU_LOADOP_CLEAR;
    ds.stencil_store_op = SDL_GPU_STOREOP_STORE;
    ds.clear_stencil = 0;
    pass_ = SDL_BeginGPURenderPass(cmd_, &ct, 1, full ? &ds : nullptr);
    pass_target_ = texture;
    if (pass_ != nullptr) {
        stencil_cleared_ = stencil_cleared_ || full;
        ++stats_.passes;
    } else {
        log::error("rml renderer: cannot begin a pass: {}", SDL_GetError());
    }
    return pass_;
}

void RmlRenderer::end_pass() {
    if (pass_ != nullptr) {
        SDL_EndGPURenderPass(pass_);
        pass_ = nullptr;
        pass_target_ = nullptr;
    }
}

void RmlRenderer::fullscreen(SDL_GPUTexture* source, Pipe pipe, const SDL_Rect& scissor, Rml::Vector2f uv_scale,
                             Rml::Vector2f uv_offset) {
    if (pass_ == nullptr || empty(scissor)) {
        return;
    }
    SDL_BindGPUGraphicsPipeline(pass_, pipelines_[pipe]);
    const QuadUniforms qu{{uv_scale.x, uv_scale.y, uv_offset.x, uv_offset.y}};
    SDL_PushGPUVertexUniformData(cmd_, 0, &qu, sizeof(qu));
    SDL_PushGPUFragmentUniformData(cmd_, 0, uniforms_.data(), uniforms_size_);
    const SDL_GPUTextureSamplerBinding tex[2] = {{source, sampler_}, {mask_ != nullptr ? mask_ : source, sampler_}};
    SDL_BindGPUFragmentSamplers(pass_, 0, tex, pipe == kBlur || pipe == kHalfBlur ? 1 : 2);
    SDL_SetGPUScissor(pass_, &scissor);
    SDL_DrawGPUPrimitives(pass_, 3, 1, 0, 0);
}

void RmlRenderer::push_post(float mode, float factor, const float color[4], const float limits[4],
                            const float* matrix) {
    PostUniforms u;
    u.mode = mode;
    u.factor = factor;
    if (color != nullptr) {
        std::memcpy(u.color, color, sizeof(u.color));
    }
    if (limits != nullptr) {
        std::memcpy(u.limits, limits, sizeof(u.limits));
    }
    if (matrix != nullptr) {
        std::memcpy(u.matrix, matrix, sizeof(u.matrix));
    }
    set_uniforms(&u, sizeof(u));
}

void RmlRenderer::set_uniforms(const void* data, std::uint32_t size) {
    uniforms_size_ = std::min(size, static_cast<std::uint32_t>(uniforms_.size()));
    std::memcpy(uniforms_.data(), data, uniforms_size_);
}

void RmlRenderer::render_blur(float sigma, int source_destination, int temp, const SDL_Rect& window) {
    // RmlUi's GL3 blur: halve, blur down and across, and scale back up.
    const rml_fx::BlurPlan plan = rml_fx::blur_plan(sigma);
    SDL_GPUTexture* sd = post_[static_cast<std::size_t>(source_destination)];
    SDL_GPUTexture* tmp = post_[static_cast<std::size_t>(temp)];
    int x0 = window.x;
    int y0 = window.y;
    int x1 = window.x + window.w;
    int y1 = window.y + window.h;
    const Rml::Vector2f odd = {width_ % 2 == 1 ? 1.0f - 1.0f / static_cast<float>(width_) : 1.0f,
                               height_ % 2 == 1 ? 1.0f - 1.0f / static_cast<float>(height_) : 1.0f};
    const SDL_GPUViewport half_view{0.0f, 0.0f, static_cast<float>(width_ / 2), static_cast<float>(height_ / 2),
                                    0.0f, 1.0f};
    for (int i = 0; i < plan.levels; ++i) {
        x0 = (x0 + 1) / 2;
        y0 = (y0 + 1) / 2;
        x1 = std::max(x1 / 2, x0);
        y1 = std::max(y1 / 2, y0);
        const bool from_source = i % 2 == 0;
        if (target(from_source ? tmp : sd, false) == nullptr) {
            return;
        }
        SDL_SetGPUViewport(pass_, &half_view);
        push_post(kPostCopy, 1.0f, nullptr, nullptr, nullptr);
        fullscreen(from_source ? sd : tmp, kCopy, SDL_Rect{x0, y0, x1 - x0, y1 - y0}, odd);
        end_pass();  // The next pass starts with the full viewport again.
    }
    const SDL_Rect reduced{x0, y0, x1 - x0, y1 - y0};
    if (plan.levels % 2 == 0) {
        if (target(tmp, false) == nullptr) {
            return;
        }
        push_post(kPostCopy, 1.0f, nullptr, nullptr, nullptr);
        fullscreen(sd, kCopy, reduced);
    }
    BlurUniforms bu{};
    const std::array<float, 4> w = rml_fx::blur_weights(plan.sigma);
    std::memcpy(bu.weights, w.data(), sizeof(bu.weights));
    limits_of(reduced, width_, height_, bu.limits);
    // Down: tmp into sd.
    if (target(sd, false) == nullptr) {
        return;
    }
    bu.offset[0] = 0.0f;
    bu.offset[1] = 1.0f / static_cast<float>(height_);
    set_uniforms(&bu, sizeof(bu));
    fullscreen(tmp, kBlur, reduced);
    // Across: sd into tmp, with a clear border of one pixel so the scaling up
    // does not pull in what lies around.
    if (target(tmp, false) == nullptr) {
        return;
    }
    push_post(kPostCopy, 0.0f, nullptr, nullptr, nullptr);
    const int bx = std::max(reduced.x - 1, 0);
    const int by = std::max(reduced.y - 1, 0);
    fullscreen(sd, kCopy,
               SDL_Rect{bx, by, std::min(reduced.x + reduced.w + 1, width_) - bx,
                        std::min(reduced.y + reduced.h + 1, height_) - by});
    bu.offset[0] = 1.0f / static_cast<float>(width_);
    bu.offset[1] = 0.0f;
    set_uniforms(&bu, sizeof(bu));
    fullscreen(sd, kBlur, reduced);
    // Back up to the window, by an exact power of two.
    if (target(sd, false) == nullptr) {
        return;
    }
    const float scale = 1.0f / static_cast<float>(1 << plan.levels);
    push_post(kPostCopy, 1.0f, nullptr, nullptr, nullptr);
    fullscreen(tmp, kCopy, window, {scale, scale});
}

void RmlRenderer::apply_filters(const Command& c) {
    for (std::uint32_t i = 0; i < c.filter_count; ++i) {
        const Filter& f = frame_filters_[c.first_filter + i];
        switch (f.type) {
        case FilterType::Opacity:
            if (target(post_[static_cast<std::size_t>(secondary_)], false) == nullptr) {
                return;
            }
            push_post(kPostCopy, f.value, nullptr, nullptr, nullptr);
            fullscreen(post_[static_cast<std::size_t>(primary_)], kCopy, c.scissor);
            std::swap(primary_, secondary_);
            break;
        case FilterType::Blur:
            render_blur(f.value, primary_, secondary_, c.scissor);
            break;
        case FilterType::DropShadow: {
            if (target(post_[static_cast<std::size_t>(secondary_)], false) == nullptr) {
                return;
            }
            float color[4];
            to_float(f.color, color);
            float limits[4];
            limits_of(c.scissor, width_, height_, limits);
            push_post(kPostShadow, 1.0f, color, limits, nullptr);
            fullscreen(post_[static_cast<std::size_t>(primary_)], kPost, c.scissor, {1.0f, 1.0f},
                       {-f.offset.x / static_cast<float>(width_), -f.offset.y / static_cast<float>(height_)});
            if (f.value >= 0.5f) {
                render_blur(f.value, secondary_, tertiary_, c.scissor);
            }
            if (target(post_[static_cast<std::size_t>(secondary_)], false) == nullptr) {
                return;
            }
            push_post(kPostCopy, 1.0f, nullptr, nullptr, nullptr);
            fullscreen(post_[static_cast<std::size_t>(primary_)], kBlend, c.scissor);
            std::swap(primary_, secondary_);
            break;
        }
        case FilterType::ColorMatrix:
            if (target(post_[static_cast<std::size_t>(secondary_)], false) == nullptr) {
                return;
            }
            push_post(kPostMatrix, 1.0f, nullptr, nullptr, f.matrix.data());
            fullscreen(post_[static_cast<std::size_t>(primary_)], kPost, c.scissor);
            std::swap(primary_, secondary_);
            break;
        case FilterType::MaskImage:
            if (mask_ == nullptr || target(post_[static_cast<std::size_t>(secondary_)], false) == nullptr) {
                break;
            }
            push_post(kPostMask, 1.0f, nullptr, nullptr, nullptr);
            fullscreen(post_[static_cast<std::size_t>(primary_)], kPost, c.scissor);
            std::swap(primary_, secondary_);
            break;
        }
    }
}

bool RmlRenderer::blur_backdrop(SDL_GPUTexture* scene) {
    // Once per frame, whatever the number of glass elements: the scene halved
    // as many times as the blur needs, then the engine's blur across and down
    // (D-11802).
    const rml_fx::BackdropPlan plan = rml_fx::backdrop_plan(backdrop_sigma_);
    if (plan.levels < 1) {
        return false;
    }
    int w = width_;
    int h = height_;
    SDL_GPUTexture* from = scene;
    for (int l = 0; l < plan.levels; ++l) {
        w = rml_fx::half(w);
        h = rml_fx::half(h);
        if (target(down_[static_cast<std::size_t>(l)][0], false) == nullptr) {
            return false;
        }
        push_post(kPostCopy, 1.0f, nullptr, nullptr, nullptr);
        fullscreen(from, kHalfCopy, SDL_Rect{0, 0, w, h});
        from = down_[static_cast<std::size_t>(l)][0];
    }
    const auto& last = down_[static_cast<std::size_t>(plan.levels - 1)];
    const SDL_Rect all{0, 0, w, h};
    for (int i = 0; i < plan.passes; ++i) {
        const float across[4] = {plan.step / static_cast<float>(w), 0.0f, 0.0f, 0.0f};
        const float down[4] = {0.0f, plan.step / static_cast<float>(h), 0.0f, 0.0f};
        if (target(last[1], false) == nullptr) {
            return false;
        }
        set_uniforms(across, sizeof(across));
        fullscreen(last[0], kHalfBlur, all);
        if (target(last[0], false) == nullptr) {
            return false;
        }
        set_uniforms(down, sizeof(down));
        fullscreen(last[1], kHalfBlur, all);
    }
    end_pass();
    backdrop_ = last[0];
    return true;
}

SDL_GPUTexture* RmlRenderer::texture_of(Rml::TextureHandle handle, float& mode) const {
    if (handle == 0) {
        mode = kModeColor;
        return atlas_;  // Bound but not read.
    }
    if (handle == atlas_handle_) {
        mode = kModeAtlas;
        return atlas_;
    }
    const auto it = textures_.find(handle);
    if (it == textures_.end()) {
        return nullptr;
    }
    mode = kModeTexture;
    return it->second.texture;
}

bool RmlRenderer::render(SDL_GPUCommandBuffer* cmd, SDL_GPUTexture* backdrop) {
    replayed_ = false;
    if (device_ == nullptr || stats_.draws == 0) {
        return false;
    }
    if (!upload(cmd) || !ensure_targets(stats_.layers)) {
        return false;
    }
    cmd_ = cmd;
    stencil_cleared_ = false;
    primary_ = 0;
    secondary_ = 1;
    tertiary_ = 2;
    stats_.passes = 0;
    backdrop_ready_ = backdrop != nullptr && stats_.backdrop_blurs > 0 && down_[0][0] != nullptr &&
                      blur_backdrop(backdrop);
    // The base layer starts clear.
    if (target(layers_[0], true) == nullptr) {
        cmd_ = nullptr;
        return false;
    }
    const SDL_GPUBufferBinding vb{vertex_buffer_, 0};
    const SDL_GPUBufferBinding ib{index_buffer_, 0};
    for (const Command& c : commands_) {
        if (c.layer < 0 || c.layer >= static_cast<int>(layers_.size())) {
            continue;
        }
        SDL_GPUTexture* layer = layers_[static_cast<std::size_t>(c.layer)];
        switch (c.op) {
        case Op::Draw:
        case Op::ClipClear:
        case Op::ClipDraw: {
            if (empty(c.scissor)) {
                break;
            }
            float mode = kModeColor;
            SDL_GPUTexture* texture = texture_of(c.op == Op::Draw ? c.texture : 0, mode);
            if (texture == nullptr || target(layer, false) == nullptr) {
                break;
            }
            Pipe pipe = c.clip ? kGeometryClip : kGeometry;
            if (c.op != Op::Draw) {
                pipe = c.increment ? kClipIncrement : kClipReplace;
            } else if (c.gradient >= 0) {
                pipe = c.clip ? kGradientClip : kGradient;
            }
            SDL_BindGPUGraphicsPipeline(pass_, pipelines_[pipe]);
            SDL_BindGPUVertexBuffers(pass_, 0, &vb, 1);
            SDL_BindGPUIndexBuffer(pass_, &ib, SDL_GPU_INDEXELEMENTSIZE_32BIT);
            VertexUniforms vu{};
            const Rml::Matrix4f& m = c.op == Op::ClipClear ? transforms_.front()
                                                             : transforms_[static_cast<std::size_t>(c.transform)];
            std::memcpy(vu.transform, m.data(), sizeof(vu.transform));
            vu.translation[0] = c.translation.x;
            vu.translation[1] = c.translation.y;
            SDL_PushGPUVertexUniformData(cmd, 0, &vu, sizeof(vu));
            if (c.op == Op::Draw && c.gradient >= 0) {
                const Gradient& g = gradients_[static_cast<std::size_t>(c.gradient)];
                GradientUniforms gu{};
                gu.func = g.func;
                gu.num_stops = g.stops;
                gu.p[0] = g.p.x;
                gu.p[1] = g.p.y;
                gu.v[0] = g.v.x;
                gu.v[1] = g.v.y;
                std::memcpy(gu.stop_colors, g.colors.data(), sizeof(gu.stop_colors));
                std::memcpy(gu.stop_positions, g.positions.data(), sizeof(gu.stop_positions));
                SDL_PushGPUFragmentUniformData(cmd, 0, &gu, sizeof(gu));
            } else {
                const FragmentUniforms fu{mode, {0.0f, 0.0f, 0.0f}};
                SDL_PushGPUFragmentUniformData(cmd, 0, &fu, sizeof(fu));
                const SDL_GPUTextureSamplerBinding tex{texture, mode == kModeTexture ? repeat_sampler_ : sampler_};
                SDL_BindGPUFragmentSamplers(pass_, 0, &tex, 1);
            }
            SDL_SetGPUScissor(pass_, &c.scissor);
            SDL_SetGPUStencilReference(pass_, c.ref);
            SDL_DrawGPUIndexedPrimitives(pass_, c.index_count, 1, c.first_index, 0, 0);
            break;
        }
        case Op::PushLayer:
            (void)target(layer, true);
            break;
        case Op::Composite: {
            if (empty(c.scissor) || (c.backdrop && !backdrop_ready_) ||
                c.source >= static_cast<int>(layers_.size())) {
                break;
            }
            // The source into the primary postprocessing texture, the
            // filters there, and the result into the destination layer.
            if (target(post_[static_cast<std::size_t>(primary_)], false) == nullptr) {
                break;
            }
            push_post(kPostCopy, 1.0f, nullptr, nullptr, nullptr);
            fullscreen(c.backdrop ? backdrop_ : layers_[static_cast<std::size_t>(c.source)], kCopy, c.scissor);
            apply_filters(c);
            if (target(layer, false) == nullptr) {
                break;
            }
            push_post(kPostCopy, 1.0f, nullptr, nullptr, nullptr);
            const Pipe pipe = c.replace ? (c.clip ? kCopyClip : kCopy) : (c.clip ? kBlendClip : kBlend);
            SDL_SetGPUStencilReference(pass_, c.ref);
            fullscreen(post_[static_cast<std::size_t>(primary_)], pipe, c.scissor);
            break;
        }
        case Op::SaveTexture: {
            const auto it = textures_.find(c.saved);
            if (it == textures_.end() || it->second.texture == nullptr || empty(c.scissor)) {
                break;
            }
            end_pass();
            SDL_GPUCopyPass* copy = SDL_BeginGPUCopyPass(cmd);
            SDL_GPUTextureLocation src{};
            src.texture = layer;
            src.x = static_cast<std::uint32_t>(c.scissor.x);
            src.y = static_cast<std::uint32_t>(c.scissor.y);
            SDL_GPUTextureLocation dst{};
            dst.texture = it->second.texture;
            SDL_CopyGPUTextureToTexture(copy, &src, &dst, static_cast<std::uint32_t>(c.scissor.w),
                                        static_cast<std::uint32_t>(c.scissor.h), 1, false);
            SDL_EndGPUCopyPass(copy);
            break;
        }
        case Op::SaveMask:
            if (mask_ == nullptr || empty(c.scissor) || target(mask_, false) == nullptr) {
                break;
            }
            push_post(kPostCopy, 1.0f, nullptr, nullptr, nullptr);
            fullscreen(layer, kCopy, c.scissor);
            break;
        }
    }
    end_pass();
    cmd_ = nullptr;
    replayed_ = true;
    return true;
}

void RmlRenderer::composite(SDL_GPUCommandBuffer* cmd, SDL_GPURenderPass* pass) {
    if (!replayed_ || layers_.empty() || pass == nullptr) {
        return;
    }
    SDL_BindGPUGraphicsPipeline(pass, pipelines_[kFinal]);
    const QuadUniforms qu{{1.0f, 1.0f, 0.0f, 0.0f}};
    SDL_PushGPUVertexUniformData(cmd, 0, &qu, sizeof(qu));
    PostUniforms u;
    SDL_PushGPUFragmentUniformData(cmd, 0, &u, sizeof(u));
    const SDL_GPUTextureSamplerBinding tex[2] = {{layers_[0], sampler_}, {layers_[0], sampler_}};
    SDL_BindGPUFragmentSamplers(pass, 0, tex, 2);
    const SDL_Rect all{0, 0, width_, height_};
    SDL_SetGPUScissor(pass, &all);
    SDL_DrawGPUPrimitives(pass, 3, 1, 0, 0);
}

}  // namespace sc
