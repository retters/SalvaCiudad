// Draws a ui::DrawList with the SDL GPU API: one pipeline, the glyph atlas
// and a few RGBA images (the minimap) as textures, and one draw call per
// clip rectangle and texture.
#pragma once

#include <cstdint>
#include <map>
#include <vector>

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

    // An RGBA image (width x height x 4 bytes) that draw commands can use
    // by `id` (not 0); replaces the previous one with that id. Goes up to
    // the GPU with the next upload(). False for a bad size.
    bool set_image(std::uint32_t id, int width, int height, std::vector<std::uint8_t> rgba);
    static constexpr int kMaxImageSize = 2048;
    // A texture somebody else owns (the picture of a camera window), drawn
    // by `id` like an image; null takes it away. Set it every frame the
    // texture may have changed: this renderer does not keep it alive.
    void set_external_image(std::uint32_t id, SDL_GPUTexture* texture);

    // The glyph atlas on the GPU and its sampler, shared with RmlUi's renderer.
    [[nodiscard]] SDL_GPUTexture* atlas_texture() const { return atlas_; }
    [[nodiscard]] SDL_GPUSampler* sampler() const { return sampler_; }

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

    struct Image {
        SDL_GPUTexture* texture = nullptr;
        int width = 0;
        int height = 0;
        std::vector<std::uint8_t> pending;  // Pixels waiting for the next upload.
        bool external = false;              // Not ours to release.
    };
    std::map<std::uint32_t, Image> images_;
    bool upload_images(SDL_GPUCommandBuffer* cmd);
};

}  // namespace sc
