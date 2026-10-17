#include "render/rml_renderer.h"

#include <algorithm>
#include <cstddef>
#include <cstring>

#include <SDL3/SDL_error.h>

#include <RmlUi/Core/Core.h>
#include <RmlUi/Core/FileInterface.h>

#include "core/log.h"
#include "shaders/rml_frag_dxil.h"
#include "shaders/rml_vert_dxil.h"
#include "stb_image.h"

namespace sc {

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

constexpr float kModeColor = 0.0f;
constexpr float kModeTexture = 1.0f;
constexpr float kModeAtlas = 2.0f;

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

}  // namespace

RmlRenderer::~RmlRenderer() {
    destroy();
}

bool RmlRenderer::create(GpuDevice& gpu, SDL_GPUTexture* atlas, SDL_GPUSampler* sampler,
                         Rml::TextureHandle atlas_handle) {
    device_ = gpu.device();
    atlas_ = atlas;
    sampler_ = sampler;
    atlas_handle_ = atlas_handle;
    SDL_GPUShader* vs = create_shader(device_, kRmlVertDxil, kRmlVertDxil_size, SDL_GPU_SHADERSTAGE_VERTEX, 0);
    SDL_GPUShader* fs = create_shader(device_, kRmlFragDxil, kRmlFragDxil_size, SDL_GPU_SHADERSTAGE_FRAGMENT, 1);
    if (vs == nullptr || fs == nullptr) {
        SDL_ReleaseGPUShader(device_, vs);
        SDL_ReleaseGPUShader(device_, fs);
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

    // RmlUi works with premultiplied alpha.
    SDL_GPUColorTargetDescription target{};
    target.format = gpu.swapchain_format();
    target.blend_state.enable_blend = true;
    target.blend_state.src_color_blendfactor = SDL_GPU_BLENDFACTOR_ONE;
    target.blend_state.dst_color_blendfactor = SDL_GPU_BLENDFACTOR_ONE_MINUS_SRC_ALPHA;
    target.blend_state.color_blend_op = SDL_GPU_BLENDOP_ADD;
    target.blend_state.src_alpha_blendfactor = SDL_GPU_BLENDFACTOR_ONE;
    target.blend_state.dst_alpha_blendfactor = SDL_GPU_BLENDFACTOR_ONE_MINUS_SRC_ALPHA;
    target.blend_state.alpha_blend_op = SDL_GPU_BLENDOP_ADD;

    SDL_GPUGraphicsPipelineCreateInfo pi{};
    pi.vertex_shader = vs;
    pi.fragment_shader = fs;
    pi.vertex_input_state.vertex_buffer_descriptions = &vb;
    pi.vertex_input_state.num_vertex_buffers = 1;
    pi.vertex_input_state.vertex_attributes = attributes;
    pi.vertex_input_state.num_vertex_attributes = 3;
    pi.primitive_type = SDL_GPU_PRIMITIVETYPE_TRIANGLELIST;
    pi.rasterizer_state.fill_mode = SDL_GPU_FILLMODE_FILL;
    pi.rasterizer_state.cull_mode = SDL_GPU_CULLMODE_NONE;
    pi.target_info.color_target_descriptions = &target;
    pi.target_info.num_color_targets = 1;
    pipeline_ = SDL_CreateGPUGraphicsPipeline(device_, &pi);
    SDL_ReleaseGPUShader(device_, vs);
    SDL_ReleaseGPUShader(device_, fs);
    if (pipeline_ == nullptr) {
        log::error("rml renderer: SDL_CreateGPUGraphicsPipeline failed: {}", SDL_GetError());
        return false;
    }
    return true;
}

void RmlRenderer::destroy() {
    if (device_ == nullptr) {
        return;
    }
    SDL_ReleaseGPUGraphicsPipeline(device_, pipeline_);
    for (auto& [handle, t] : textures_) {
        SDL_ReleaseGPUTexture(device_, t.texture);
    }
    textures_.clear();
    geometries_.clear();
    SDL_ReleaseGPUBuffer(device_, vertex_buffer_);
    SDL_ReleaseGPUBuffer(device_, index_buffer_);
    SDL_ReleaseGPUTransferBuffer(device_, transfer_);
    pipeline_ = nullptr;
    vertex_buffer_ = nullptr;
    index_buffer_ = nullptr;
    transfer_ = nullptr;
    vertex_capacity_ = index_capacity_ = transfer_capacity_ = 0;
    device_ = nullptr;
}

void RmlRenderer::begin_frame(int width, int height) {
    width_ = width;
    height_ = height;
    transforms_.clear();
    transforms_.push_back(Rml::Matrix4f::ProjectOrtho(0.0f, static_cast<float>(width), static_cast<float>(height),
                                                      0.0f, -10000.0f, 10000.0f));
    transform_ = 0;
    scissor_on_ = false;
    frame_vertices_.clear();
    frame_indices_.clear();
    draws_.clear();
    geometry_ready_ = false;
}

Rml::CompiledGeometryHandle RmlRenderer::CompileGeometry(Rml::Span<const Rml::Vertex> vertices,
                                                         Rml::Span<const int> indices) {
    const Rml::CompiledGeometryHandle handle = next_geometry_++;
    Geometry& g = geometries_[handle];
    g.vertices.assign(vertices.begin(), vertices.end());
    g.indices.assign(indices.begin(), indices.end());
    return handle;
}

void RmlRenderer::RenderGeometry(Rml::CompiledGeometryHandle geometry, Rml::Vector2f translation,
                                 Rml::TextureHandle texture) {
    const auto it = geometries_.find(geometry);
    if (it == geometries_.end() || it->second.indices.empty()) {
        return;
    }
    const Geometry& g = it->second;
    const auto base = static_cast<std::uint32_t>(frame_vertices_.size());
    Draw d;
    d.first_index = static_cast<std::uint32_t>(frame_indices_.size());
    d.index_count = static_cast<std::uint32_t>(g.indices.size());
    d.texture = texture;
    d.translation = translation;
    d.scissor = scissor_on_ ? scissor_ : SDL_Rect{0, 0, width_, height_};
    d.transform = transform_;
    frame_vertices_.insert(frame_vertices_.end(), g.vertices.begin(), g.vertices.end());
    for (const int i : g.indices) {
        frame_indices_.push_back(base + static_cast<std::uint32_t>(i));
    }
    draws_.push_back(d);
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

void RmlRenderer::ReleaseTexture(Rml::TextureHandle texture) {
    const auto it = textures_.find(texture);
    if (it == textures_.end()) {
        return;  // Also the atlas, which belongs to the old interface's renderer.
    }
    if (device_ != nullptr) {
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

void RmlRenderer::SetTransform(const Rml::Matrix4f* transform) {
    if (transform == nullptr) {
        transform_ = 0;
        return;
    }
    transforms_.push_back(transforms_.front() * *transform);
    transform_ = static_cast<int>(transforms_.size() - 1);
}

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

bool RmlRenderer::upload(SDL_GPUCommandBuffer* cmd) {
    geometry_ready_ = false;
    if (device_ == nullptr) {
        return false;
    }
    // New textures first, each with its own transfer buffer (they are rare).
    for (auto& [handle, t] : textures_) {
        if (t.pending.empty()) {
            continue;
        }
        if (t.texture == nullptr) {
            SDL_GPUTextureCreateInfo ti{};
            ti.type = SDL_GPU_TEXTURETYPE_2D;
            ti.format = SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM;
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
    geometry_ready_ = true;
    return true;
}

void RmlRenderer::draw(SDL_GPUCommandBuffer* cmd, SDL_GPURenderPass* pass) {
    if (!geometry_ready_ || draws_.empty()) {
        return;
    }
    SDL_BindGPUGraphicsPipeline(pass, pipeline_);
    const SDL_GPUBufferBinding vb{vertex_buffer_, 0};
    SDL_BindGPUVertexBuffers(pass, 0, &vb, 1);
    const SDL_GPUBufferBinding ib{index_buffer_, 0};
    SDL_BindGPUIndexBuffer(pass, &ib, SDL_GPU_INDEXELEMENTSIZE_32BIT);
    for (const Draw& d : draws_) {
        if (d.scissor.w <= 0 || d.scissor.h <= 0) {
            continue;
        }
        SDL_GPUTexture* texture = atlas_;
        float mode = kModeColor;
        if (d.texture == atlas_handle_) {
            mode = kModeAtlas;
        } else if (d.texture != 0) {
            const auto it = textures_.find(d.texture);
            if (it == textures_.end() || it->second.texture == nullptr) {
                continue;
            }
            texture = it->second.texture;
            mode = kModeTexture;
        }
        VertexUniforms vu{};
        std::memcpy(vu.transform, transforms_[static_cast<std::size_t>(d.transform)].data(), sizeof(vu.transform));
        vu.translation[0] = d.translation.x;
        vu.translation[1] = d.translation.y;
        SDL_PushGPUVertexUniformData(cmd, 0, &vu, sizeof(vu));
        const FragmentUniforms fu{mode, {0.0f, 0.0f, 0.0f}};
        SDL_PushGPUFragmentUniformData(cmd, 0, &fu, sizeof(fu));
        const SDL_GPUTextureSamplerBinding tex{texture, sampler_};
        SDL_BindGPUFragmentSamplers(pass, 0, &tex, 1);
        SDL_SetGPUScissor(pass, &d.scissor);
        SDL_DrawGPUIndexedPrimitives(pass, d.index_count, 1, d.first_index, 0, 0);
    }
}

}  // namespace sc
