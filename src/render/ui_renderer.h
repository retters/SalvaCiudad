// Draws a ui::DrawList with the SDL GPU API: one pipeline, the glyph atlas
// as the only texture, and one draw call per clip rectangle.
#pragma once

#include <cstdint>

#include <SDL3/SDL_gpu.h>

#include "render/gpu_device.h"
#include "ui/draw_list.h"
#include "ui/glyph_atlas.h"

namespace sc {

class UiRenderer {
public:
    UiRenderer() = default;
    ~UiRenderer();
    UiRenderer(const UiRenderer&) = delete;
    UiRenderer& operator=(const UiRenderer&) = delete;

    bool create(GpuDevice& gpu, int atlas_size);
    void destroy();

    // Copies the geometry and the changed part of the atlas to the GPU.
    // Must run before the render pass that calls draw().
    bool upload(SDL_GPUCommandBuffer* cmd, const ui::DrawList& list, ui::GlyphAtlas& atlas);

    void draw(SDL_GPUCommandBuffer* cmd, SDL_GPURenderPass* pass, const ui::DrawList& list);

private:
    bool ensure_buffer(SDL_GPUBuffer*& buffer, std::uint32_t& capacity, std::uint32_t needed,
                       SDL_GPUBufferUsageFlags usage);
    bool ensure_transfer(std::uint32_t needed);

    SDL_GPUDevice* device_ = nullptr;
    SDL_GPUGraphicsPipeline* pipeline_ = nullptr;
    SDL_GPUTexture* atlas_ = nullptr;
    SDL_GPUSampler* sampler_ = nullptr;
    SDL_GPUBuffer* vertex_buffer_ = nullptr;
    SDL_GPUBuffer* index_buffer_ = nullptr;
    SDL_GPUTransferBuffer* transfer_ = nullptr;
    std::uint32_t vertex_capacity_ = 0;  // Bytes.
    std::uint32_t index_capacity_ = 0;
    std::uint32_t transfer_capacity_ = 0;
    int atlas_size_ = 0;
    bool geometry_ready_ = false;
};

}  // namespace sc
