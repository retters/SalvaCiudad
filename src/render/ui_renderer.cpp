#include "render/ui_renderer.h"

#include <algorithm>
#include <cmath>
#include <cstring>

#include <SDL3/SDL_error.h>

#include "core/log.h"
#include "shaders/ui_frag_dxil.h"
#include "shaders/ui_vert_dxil.h"

namespace sc {

namespace {

struct UiUniforms {
    float screen_w;
    float screen_h;
    float unused0;
    float unused1;
};

SDL_GPUShader* create_shader(SDL_GPUDevice* device, const std::uint8_t* code, std::size_t size,
                             SDL_GPUShaderStage stage, std::uint32_t samplers, std::uint32_t uniform_buffers) {
    SDL_GPUShaderCreateInfo info{};
    info.code = code;
    info.code_size = size;
    info.entrypoint = "main";
    info.format = SDL_GPU_SHADERFORMAT_DXIL;
    info.stage = stage;
    info.num_samplers = samplers;
    info.num_uniform_buffers = uniform_buffers;
    SDL_GPUShader* shader = SDL_CreateGPUShader(device, &info);
    if (shader == nullptr) {
        log::error("ui renderer: SDL_CreateGPUShader failed: {}", SDL_GetError());
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

UiRenderer::~UiRenderer() {
    destroy();
}

bool UiRenderer::create(GpuDevice& gpu, int atlas_size) {
    device_ = gpu.device();
    atlas_size_ = atlas_size;
    if ((gpu.shader_format() & SDL_GPU_SHADERFORMAT_DXIL) == 0) {
        log::error("ui renderer: the GPU device does not accept DXIL shaders");
        return false;
    }

    SDL_GPUShader* vs = create_shader(device_, kUiVertDxil, kUiVertDxil_size, SDL_GPU_SHADERSTAGE_VERTEX, 0, 1);
    SDL_GPUShader* fs = create_shader(device_, kUiFragDxil, kUiFragDxil_size, SDL_GPU_SHADERSTAGE_FRAGMENT, 1, 1);
    if (vs == nullptr || fs == nullptr) {
        SDL_ReleaseGPUShader(device_, vs);
        SDL_ReleaseGPUShader(device_, fs);
        return false;
    }

    SDL_GPUVertexBufferDescription vb{};
    vb.slot = 0;
    vb.pitch = sizeof(ui::Vertex);
    vb.input_rate = SDL_GPU_VERTEXINPUTRATE_VERTEX;

    SDL_GPUVertexAttribute attributes[3]{};
    attributes[0] = {0, 0, SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2, offsetof(ui::Vertex, x)};
    attributes[1] = {1, 0, SDL_GPU_VERTEXELEMENTFORMAT_FLOAT2, offsetof(ui::Vertex, u)};
    attributes[2] = {2, 0, SDL_GPU_VERTEXELEMENTFORMAT_UBYTE4_NORM, offsetof(ui::Vertex, r)};

    SDL_GPUColorTargetDescription target{};
    target.format = gpu.swapchain_format();
    target.blend_state.enable_blend = true;
    target.blend_state.src_color_blendfactor = SDL_GPU_BLENDFACTOR_SRC_ALPHA;
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
        log::error("ui renderer: SDL_CreateGPUGraphicsPipeline failed: {}", SDL_GetError());
        return false;
    }

    SDL_GPUTextureCreateInfo ti{};
    ti.type = SDL_GPU_TEXTURETYPE_2D;
    ti.format = SDL_GPU_TEXTUREFORMAT_R8_UNORM;
    ti.usage = SDL_GPU_TEXTUREUSAGE_SAMPLER;
    ti.width = static_cast<std::uint32_t>(atlas_size);
    ti.height = static_cast<std::uint32_t>(atlas_size);
    ti.layer_count_or_depth = 1;
    ti.num_levels = 1;
    atlas_ = SDL_CreateGPUTexture(device_, &ti);
    if (atlas_ == nullptr) {
        log::error("ui renderer: SDL_CreateGPUTexture failed: {}", SDL_GetError());
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
    if (sampler_ == nullptr) {
        log::error("ui renderer: SDL_CreateGPUSampler failed: {}", SDL_GetError());
        return false;
    }
    return true;
}

void UiRenderer::destroy() {
    if (device_ == nullptr) {
        return;
    }
    SDL_ReleaseGPUGraphicsPipeline(device_, pipeline_);
    SDL_ReleaseGPUTexture(device_, atlas_);
    for (auto& [id, image] : images_) {
        SDL_ReleaseGPUTexture(device_, image.texture);
    }
    images_.clear();
    SDL_ReleaseGPUSampler(device_, sampler_);
    SDL_ReleaseGPUBuffer(device_, vertex_buffer_);
    SDL_ReleaseGPUBuffer(device_, index_buffer_);
    SDL_ReleaseGPUTransferBuffer(device_, transfer_);
    pipeline_ = nullptr;
    atlas_ = nullptr;
    sampler_ = nullptr;
    vertex_buffer_ = nullptr;
    index_buffer_ = nullptr;
    transfer_ = nullptr;
    vertex_capacity_ = index_capacity_ = transfer_capacity_ = 0;
    device_ = nullptr;
}

bool UiRenderer::ensure_buffer(SDL_GPUBuffer*& buffer, std::uint32_t& capacity, std::uint32_t needed,
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
        log::error("ui renderer: SDL_CreateGPUBuffer failed: {}", SDL_GetError());
    }
    return buffer != nullptr;
}

bool UiRenderer::ensure_transfer(std::uint32_t needed) {
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
        log::error("ui renderer: SDL_CreateGPUTransferBuffer failed: {}", SDL_GetError());
    }
    return transfer_ != nullptr;
}

bool UiRenderer::set_image(std::uint32_t id, int width, int height, std::vector<std::uint8_t> rgba) {
    if (id == 0 || width < 1 || height < 1 || width > kMaxImageSize || height > kMaxImageSize ||
        rgba.size() != static_cast<std::size_t>(width) * static_cast<std::size_t>(height) * 4) {
        return false;
    }
    Image& image = images_[id];
    if (image.texture != nullptr && (image.width != width || image.height != height)) {
        SDL_ReleaseGPUTexture(device_, image.texture);
        image.texture = nullptr;
    }
    image.width = width;
    image.height = height;
    image.pending = std::move(rgba);
    return true;
}

bool UiRenderer::upload_images(SDL_GPUCommandBuffer* cmd) {
    for (auto& [id, image] : images_) {
        if (image.pending.empty() || device_ == nullptr) {
            continue;
        }
        if (image.texture == nullptr) {
            SDL_GPUTextureCreateInfo ti{};
            ti.type = SDL_GPU_TEXTURETYPE_2D;
            ti.format = SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM;
            ti.usage = SDL_GPU_TEXTUREUSAGE_SAMPLER;
            ti.width = static_cast<std::uint32_t>(image.width);
            ti.height = static_cast<std::uint32_t>(image.height);
            ti.layer_count_or_depth = 1;
            ti.num_levels = 1;
            image.texture = SDL_CreateGPUTexture(device_, &ti);
            if (image.texture == nullptr) {
                log::error("ui renderer: cannot create an image: {}", SDL_GetError());
                image.pending.clear();
                continue;
            }
        }
        SDL_GPUTransferBufferCreateInfo tb{};
        tb.usage = SDL_GPU_TRANSFERBUFFERUSAGE_UPLOAD;
        tb.size = static_cast<std::uint32_t>(image.pending.size());
        SDL_GPUTransferBuffer* transfer = SDL_CreateGPUTransferBuffer(device_, &tb);
        void* mapped = transfer != nullptr ? SDL_MapGPUTransferBuffer(device_, transfer, false) : nullptr;
        if (mapped == nullptr) {
            log::error("ui renderer: cannot upload an image: {}", SDL_GetError());
            SDL_ReleaseGPUTransferBuffer(device_, transfer);
            return false;
        }
        std::memcpy(mapped, image.pending.data(), image.pending.size());
        SDL_UnmapGPUTransferBuffer(device_, transfer);
        SDL_GPUCopyPass* copy = SDL_BeginGPUCopyPass(cmd);
        SDL_GPUTextureTransferInfo src{};
        src.transfer_buffer = transfer;
        src.pixels_per_row = static_cast<std::uint32_t>(image.width);
        src.rows_per_layer = static_cast<std::uint32_t>(image.height);
        SDL_GPUTextureRegion dst{};
        dst.texture = image.texture;
        dst.w = static_cast<std::uint32_t>(image.width);
        dst.h = static_cast<std::uint32_t>(image.height);
        dst.d = 1;
        SDL_UploadToGPUTexture(copy, &src, &dst, false);
        SDL_EndGPUCopyPass(copy);
        // Released now, freed by SDL once the copy is done.
        SDL_ReleaseGPUTransferBuffer(device_, transfer);
        image.pending.clear();
        image.pending.shrink_to_fit();
    }
    return true;
}

bool UiRenderer::upload(SDL_GPUCommandBuffer* cmd, const ui::DrawList& list, ui::GlyphAtlas& atlas) {
    geometry_ready_ = false;
    if (!upload_images(cmd)) {
        return false;
    }
    const ui::AtlasRegion dirty = atlas.take_dirty();
    const auto vertex_bytes = static_cast<std::uint32_t>(list.vertices().size() * sizeof(ui::Vertex));
    const auto index_bytes = static_cast<std::uint32_t>(list.indices().size() * sizeof(std::uint32_t));
    const auto atlas_bytes = static_cast<std::uint32_t>(dirty.w * dirty.h);
    if (vertex_bytes == 0 && atlas_bytes == 0) {
        return true;
    }
    if (!ensure_transfer(vertex_bytes + index_bytes + atlas_bytes) ||
        (vertex_bytes > 0 &&
         (!ensure_buffer(vertex_buffer_, vertex_capacity_, vertex_bytes, SDL_GPU_BUFFERUSAGE_VERTEX) ||
          !ensure_buffer(index_buffer_, index_capacity_, index_bytes, SDL_GPU_BUFFERUSAGE_INDEX)))) {
        return false;
    }

    // Cycling lets the GPU keep reading last frame's data while we write.
    auto* mapped = static_cast<std::uint8_t*>(SDL_MapGPUTransferBuffer(device_, transfer_, true));
    if (mapped == nullptr) {
        log::error("ui renderer: SDL_MapGPUTransferBuffer failed: {}", SDL_GetError());
        return false;
    }
    std::memcpy(mapped, list.vertices().data(), vertex_bytes);
    std::memcpy(mapped + vertex_bytes, list.indices().data(), index_bytes);
    const std::uint32_t atlas_offset = vertex_bytes + index_bytes;
    for (int row = 0; row < dirty.h; ++row) {
        std::memcpy(mapped + atlas_offset + static_cast<std::uint32_t>(row * dirty.w),
                    atlas.pixels() + static_cast<std::size_t>(dirty.y + row) * static_cast<std::size_t>(atlas.size()) +
                        static_cast<std::size_t>(dirty.x),
                    static_cast<std::size_t>(dirty.w));
    }
    SDL_UnmapGPUTransferBuffer(device_, transfer_);

    SDL_GPUCopyPass* copy = SDL_BeginGPUCopyPass(cmd);
    if (vertex_bytes > 0) {
        SDL_GPUTransferBufferLocation src{transfer_, 0};
        SDL_GPUBufferRegion dst{vertex_buffer_, 0, vertex_bytes};
        SDL_UploadToGPUBuffer(copy, &src, &dst, true);
        src.offset = vertex_bytes;
        dst = {index_buffer_, 0, index_bytes};
        SDL_UploadToGPUBuffer(copy, &src, &dst, true);
        geometry_ready_ = true;
    }
    if (atlas_bytes > 0) {
        SDL_GPUTextureTransferInfo src{};
        src.transfer_buffer = transfer_;
        src.offset = atlas_offset;
        src.pixels_per_row = static_cast<std::uint32_t>(dirty.w);
        src.rows_per_layer = static_cast<std::uint32_t>(dirty.h);
        SDL_GPUTextureRegion dst{};
        dst.texture = atlas_;
        dst.x = static_cast<std::uint32_t>(dirty.x);
        dst.y = static_cast<std::uint32_t>(dirty.y);
        dst.w = static_cast<std::uint32_t>(dirty.w);
        dst.h = static_cast<std::uint32_t>(dirty.h);
        dst.d = 1;
        SDL_UploadToGPUTexture(copy, &src, &dst, false);
    }
    SDL_EndGPUCopyPass(copy);
    return true;
}

void UiRenderer::draw(SDL_GPUCommandBuffer* cmd, SDL_GPURenderPass* pass, const ui::DrawList& list) {
    if (!geometry_ready_ || list.indices().empty()) {
        return;
    }
    SDL_BindGPUGraphicsPipeline(pass, pipeline_);
    const UiUniforms uniforms{list.width(), list.height(), 0.0f, 0.0f};
    SDL_PushGPUVertexUniformData(cmd, 0, &uniforms, sizeof(uniforms));
    const SDL_GPUBufferBinding vb{vertex_buffer_, 0};
    SDL_BindGPUVertexBuffers(pass, 0, &vb, 1);
    const SDL_GPUBufferBinding ib{index_buffer_, 0};
    SDL_BindGPUIndexBuffer(pass, &ib, SDL_GPU_INDEXELEMENTSIZE_32BIT);
    // The texture of each command: the atlas, or one of the images.
    std::uint32_t bound = ~0u;
    for (const ui::DrawCommand& dc : list.commands()) {
        if (dc.index_count == 0 || dc.clip.w <= 0.0f || dc.clip.h <= 0.0f) {
            continue;
        }
        if (dc.image != bound) {
            SDL_GPUTexture* texture = atlas_;
            if (dc.image != 0) {
                const auto it = images_.find(dc.image);
                if (it == images_.end() || it->second.texture == nullptr) {
                    continue;  // Not uploaded (yet).
                }
                texture = it->second.texture;
            }
            const SDL_GPUTextureSamplerBinding tex{texture, sampler_};
            SDL_BindGPUFragmentSamplers(pass, 0, &tex, 1);
            const UiUniforms mode{dc.image != 0 ? 1.0f : 0.0f, 0.0f, 0.0f, 0.0f};
            SDL_PushGPUFragmentUniformData(cmd, 0, &mode, sizeof(mode));
            bound = dc.image;
        }
        const SDL_Rect scissor{static_cast<int>(std::floor(dc.clip.x)), static_cast<int>(std::floor(dc.clip.y)),
                               static_cast<int>(std::ceil(dc.clip.w)), static_cast<int>(std::ceil(dc.clip.h))};
        SDL_SetGPUScissor(pass, &scissor);
        SDL_DrawGPUIndexedPrimitives(pass, dc.index_count, 1, dc.first_index, 0, 0);
    }
}

}  // namespace sc
