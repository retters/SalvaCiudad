// RmlUi's render interface on the SDL GPU API (phase 117, section 7.14).
//
// RmlUi hands over geometry while it renders a context; nothing reaches the
// GPU then. Each draw is recorded with its geometry, translation, texture,
// scissor and transform; afterwards upload() copies the frame's vertices and
// any new texture in one copy pass, and draw() replays the records inside the
// render pass, after the old interface and before the developer tools.
//
// Not yet here (phase 118): clip masks, layers, filters and shaders, so
// rounded clipping, box shadows and backdrop blur do not draw.
#pragma once

#include <cstdint>
#include <unordered_map>
#include <vector>

#include <SDL3/SDL_gpu.h>

#include <RmlUi/Core/RenderInterface.h>

#include "render/gpu_device.h"

namespace sc {

class RmlRenderer final : public Rml::RenderInterface {
public:
    RmlRenderer() = default;
    ~RmlRenderer() override;
    RmlRenderer(const RmlRenderer&) = delete;
    RmlRenderer& operator=(const RmlRenderer&) = delete;

    // `atlas` is the glyph atlas texture (red channel coverage), drawn for
    // the font engine's texture handle `atlas_handle`.
    bool create(GpuDevice& gpu, SDL_GPUTexture* atlas, SDL_GPUSampler* sampler, Rml::TextureHandle atlas_handle);
    void destroy();

    // Forgets the last frame's draws; call before Rml::Context::Render().
    void begin_frame(int width, int height);
    // Copies the frame's geometry and new textures to the GPU; before the render pass.
    bool upload(SDL_GPUCommandBuffer* cmd);
    void draw(SDL_GPUCommandBuffer* cmd, SDL_GPURenderPass* pass);

    [[nodiscard]] int draw_count() const { return static_cast<int>(draws_.size()); }
    [[nodiscard]] std::size_t vertex_count() const { return frame_vertices_.size(); }

    Rml::CompiledGeometryHandle CompileGeometry(Rml::Span<const Rml::Vertex> vertices,
                                                Rml::Span<const int> indices) override;
    void RenderGeometry(Rml::CompiledGeometryHandle geometry, Rml::Vector2f translation,
                        Rml::TextureHandle texture) override;
    void ReleaseGeometry(Rml::CompiledGeometryHandle geometry) override;
    Rml::TextureHandle LoadTexture(Rml::Vector2i& texture_dimensions, const Rml::String& source) override;
    Rml::TextureHandle GenerateTexture(Rml::Span<const Rml::byte> source, Rml::Vector2i source_dimensions) override;
    void ReleaseTexture(Rml::TextureHandle texture) override;
    void EnableScissorRegion(bool enable) override;
    void SetScissorRegion(Rml::Rectanglei region) override;
    void SetTransform(const Rml::Matrix4f* transform) override;

    static constexpr int kMaxTextureSize = 4096;

private:
    struct Geometry {
        std::vector<Rml::Vertex> vertices;
        std::vector<int> indices;
    };
    struct Texture {
        SDL_GPUTexture* texture = nullptr;
        int width = 0;
        int height = 0;
        std::vector<std::uint8_t> pending;  // Premultiplied RGBA waiting for upload.
    };
    struct Draw {
        std::uint32_t first_index = 0;
        std::uint32_t index_count = 0;
        Rml::TextureHandle texture = 0;
        Rml::Vector2f translation{};
        SDL_Rect scissor{};
        int transform = 0;  // Index into transforms_.
    };

    Rml::TextureHandle add_texture(std::vector<std::uint8_t> rgba, int width, int height);
    bool ensure_buffers(std::uint32_t vertex_bytes, std::uint32_t index_bytes);

    SDL_GPUDevice* device_ = nullptr;
    SDL_GPUGraphicsPipeline* pipeline_ = nullptr;
    SDL_GPUTexture* atlas_ = nullptr;
    SDL_GPUSampler* sampler_ = nullptr;
    Rml::TextureHandle atlas_handle_ = 0;

    std::unordered_map<Rml::CompiledGeometryHandle, Geometry> geometries_;
    Rml::CompiledGeometryHandle next_geometry_ = 1;
    std::unordered_map<Rml::TextureHandle, Texture> textures_;
    Rml::TextureHandle next_texture_ = 1000;

    int width_ = 0;
    int height_ = 0;
    bool scissor_on_ = false;
    SDL_Rect scissor_{};
    std::vector<Rml::Matrix4f> transforms_;  // [0] is the projection alone.
    int transform_ = 0;
    std::vector<Rml::Vertex> frame_vertices_;
    std::vector<std::uint32_t> frame_indices_;
    std::vector<Draw> draws_;
    bool geometry_ready_ = false;

    SDL_GPUBuffer* vertex_buffer_ = nullptr;
    SDL_GPUBuffer* index_buffer_ = nullptr;
    SDL_GPUTransferBuffer* transfer_ = nullptr;
    std::uint32_t vertex_capacity_ = 0;
    std::uint32_t index_capacity_ = 0;
    std::uint32_t transfer_capacity_ = 0;
};

}  // namespace sc
