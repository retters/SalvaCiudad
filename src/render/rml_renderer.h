// RmlUi's render interface on the SDL GPU API (phases 117 and 118, section
// 7.14).
//
// RmlUi hands over geometry and effects while it renders a context; nothing
// reaches the GPU then. Everything is recorded as commands (draws, clip mask
// writes, layers, compositions with filters, saved layers); render() then
// uploads the frame's vertices and new textures and replays the commands
// into the interface's own textures, before the frame's main pass, and
// composite() lays the result over the swapchain inside it, after the old
// interface and before the developer tools.
//
// The effects follow RmlUi's GL3 renderer: layers are textures the size of
// the window, clip masks live in a stencil buffer shared by all of them, and
// filters (opacity, blur, drop shadow, color matrices, mask images) run
// between postprocessing textures. One exception, the glass: a backdrop
// filter does not blur what lies behind each element. The scene's finished
// picture is blurred once per frame, at half resolution or less, with the
// engine's blur (shaders/blur.frag.hlsl) and every glass element shows that,
// so many windows cost the same blur as one (D-11802). With the simple glass
// there is no backdrop at all.
//
// Without a GPU device (the tests) the commands are still recorded and
// counted; nothing is drawn.
#pragma once

#include <array>
#include <cstdint>
#include <unordered_map>
#include <vector>

#include <SDL3/SDL_gpu.h>

#include <RmlUi/Core/RenderInterface.h>

#include "render/gpu_device.h"

namespace sc {

// The pure parts of the effects, kept apart so the tests can check them.
namespace rml_fx {

constexpr float kMaxSigma = 64.0f;       // Larger blurs are clamped (pixels).
constexpr float kMaxOffset = 1000.0f;    // Drop-shadow offsets, pixels.
constexpr float kMaxSinglePassSigma = 3.0f;

// RmlUi's blur: the picture is halved `levels` times and then blurred with
// `sigma` (in the reduced pixels), as RmlUi's GL3 renderer does.
struct BlurPlan {
    int levels = 0;
    float sigma = 0.0f;
};
[[nodiscard]] BlurPlan blur_plan(float sigma);
// The four normalized weights (center first) of the seven-tap blur.
[[nodiscard]] std::array<float, 4> blur_weights(float sigma);

// The shared backdrop blur: the scene halved `levels` times (1 to
// kMaxBackdropLevels), then `passes` horizontal and vertical rounds of the
// engine's nine-tap blur, `step` reduced pixels apart, for a blur of `sigma`
// full-resolution pixels.
constexpr int kMaxBackdropLevels = 3;
struct BackdropPlan {
    int levels = 0;
    int passes = 0;
    float step = 0.0f;
};
[[nodiscard]] BackdropPlan backdrop_plan(float sigma);
[[nodiscard]] constexpr int half(int n) { return n > 1 ? (n + 1) / 2 : 1; }

}  // namespace rml_fx

enum class GlassMode { Full, Simple };

class RmlRenderer final : public Rml::RenderInterface {
public:
    RmlRenderer() = default;
    ~RmlRenderer() override;
    RmlRenderer(const RmlRenderer&) = delete;
    RmlRenderer& operator=(const RmlRenderer&) = delete;

    // `atlas` is the glyph atlas texture (red channel coverage), drawn for
    // the font engine's texture handle `atlas_handle`.
    bool create(GpuDevice& gpu, SDL_GPUTexture* atlas, Rml::TextureHandle atlas_handle);
    void destroy();

    void set_glass(GlassMode mode) { glass_ = mode; }
    [[nodiscard]] GlassMode glass() const { return glass_; }

    // Forgets the last frame's commands; call before Rml::Context::Render().
    void begin_frame(int width, int height);

    // True if the last recorded frame has glass to show over the scene: the
    // scene then keeps its finished picture as a texture for render().
    [[nodiscard]] bool wants_backdrop() const { return glass_ == GlassMode::Full && stats_.backdrops > 0; }

    // Uploads the frame and replays it into the interface's textures, outside
    // any pass. `backdrop` is the scene's finished picture (or null: no glass
    // this frame). False if nothing is to be composited.
    bool render(SDL_GPUCommandBuffer* cmd, SDL_GPUTexture* backdrop);
    // Lays the interface over the swapchain, inside the main pass.
    void composite(SDL_GPUCommandBuffer* cmd, SDL_GPURenderPass* pass);

    struct Stats {
        int draws = 0;           // Geometry and shader draws.
        int layers = 0;          // The most layers at once, the base one included.
        int composites = 0;      // Layer compositions (filters, shadows, glass).
        int clip_writes = 0;     // Geometry written to the clip mask.
        int backdrops = 0;       // Glass elements.
        int backdrop_blurs = 0;  // Times the scene was blurred for them (0 or 1).
        int saved_layers = 0;    // Layers kept as textures (box shadows).
        int passes = 0;          // Render passes of the last replay.
    };
    [[nodiscard]] const Stats& stats() const { return stats_; }
    [[nodiscard]] int draw_count() const { return stats_.draws; }

    // Rml::RenderInterface.
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
    void EnableClipMask(bool enable) override;
    void RenderToClipMask(Rml::ClipMaskOperation operation, Rml::CompiledGeometryHandle geometry,
                          Rml::Vector2f translation) override;
    void SetTransform(const Rml::Matrix4f* transform) override;
    Rml::LayerHandle PushLayer() override;
    void CompositeLayers(Rml::LayerHandle source, Rml::LayerHandle destination, Rml::BlendMode blend_mode,
                         Rml::Span<const Rml::CompiledFilterHandle> filters) override;
    void PopLayer() override;
    Rml::TextureHandle SaveLayerAsTexture() override;
    Rml::CompiledFilterHandle SaveLayerAsMaskImage() override;
    Rml::CompiledFilterHandle CompileFilter(const Rml::String& name, const Rml::Dictionary& parameters) override;
    void ReleaseFilter(Rml::CompiledFilterHandle filter) override;
    Rml::CompiledShaderHandle CompileShader(const Rml::String& name, const Rml::Dictionary& parameters) override;
    void RenderShader(Rml::CompiledShaderHandle shader, Rml::CompiledGeometryHandle geometry,
                      Rml::Vector2f translation, Rml::TextureHandle texture) override;
    void ReleaseShader(Rml::CompiledShaderHandle shader) override;

    static constexpr int kMaxTextureSize = 4096;
    static constexpr int kMaxLayers = 16;
    static constexpr int kMaxStops = 16;

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
    enum class FilterType : std::uint8_t { Opacity, Blur, DropShadow, ColorMatrix, MaskImage };
    struct Filter {
        FilterType type = FilterType::Opacity;
        float value = 1.0f;  // Opacity, or the blur's sigma.
        Rml::ColourbPremultiplied color;
        Rml::Vector2f offset;
        Rml::Matrix4f matrix = Rml::Matrix4f::Identity();
    };
    struct Gradient {
        int func = 0;  // 0 linear, 1 radial, 2 conic; +3 repeating.
        Rml::Vector2f p;
        Rml::Vector2f v;
        int stops = 0;
        std::array<float, kMaxStops> positions{};
        std::array<std::array<float, 4>, kMaxStops> colors{};
    };
    enum class Op : std::uint8_t { Draw, ClipClear, ClipDraw, PushLayer, Composite, SaveTexture, SaveMask };
    struct Command {
        Op op = Op::Draw;
        int layer = 0;         // The layer drawn into (Draw, Clip*, PushLayer, Save*).
        SDL_Rect scissor{};
        bool clip = false;     // The clip mask is tested (Draw, Composite).
        std::uint8_t ref = 0;  // Stencil value: tested, or written (Clip*).
        // Draw and ClipDraw.
        std::uint32_t first_index = 0;
        std::uint32_t index_count = 0;
        Rml::TextureHandle texture = 0;
        Rml::Vector2f translation{};
        int transform = 0;
        int gradient = -1;            // Index into gradients_, for a shader draw.
        bool increment = false;       // ClipDraw: increment instead of replace.
        // Composite.
        int source = 0;
        bool replace = false;
        bool backdrop = false;
        std::uint32_t first_filter = 0;
        std::uint32_t filter_count = 0;
        // SaveTexture.
        Rml::TextureHandle saved = 0;
    };

    // Pipelines. Those of the "layer" family draw into a layer or
    // postprocessing texture with the shared stencil attached.
    enum Pipe : int {
        kGeometry,          // RmlUi's geometry, blended.
        kGeometryClip,      // The same, inside the clip mask.
        kGradient,
        kGradientClip,
        kClipReplace,       // Writes the reference to the stencil.
        kClipIncrement,     // Adds one to the stencil.
        kCopy,              // Full screen, replacing (copies, opacity, clears).
        kCopyClip,
        kBlend,             // Full screen, blended over.
        kBlendClip,
        kPost,              // Color matrix, drop shadow, mask (replacing).
        kBlur,              // RmlUi's seven-tap blur (replacing).
        kHalfCopy,          // Backdrop: down to half resolution (no stencil).
        kHalfBlur,          // Backdrop: the engine's blur (no stencil).
        kFinal,             // The interface over the swapchain.
        kPipeCount
    };

    Rml::TextureHandle add_texture(std::vector<std::uint8_t> rgba, int width, int height);
    [[nodiscard]] SDL_Rect current_scissor() const;
    void record_draw(Rml::CompiledGeometryHandle geometry, Rml::Vector2f translation, Rml::TextureHandle texture,
                     int gradient);
    void record_clip_clear(std::uint8_t value);

    bool create_pipelines(SDL_GPUTextureFormat swapchain_format);
    bool ensure_buffers(std::uint32_t vertex_bytes, std::uint32_t index_bytes);
    bool ensure_targets(int layers);
    void release_targets();
    bool upload(SDL_GPUCommandBuffer* cmd);
    bool blur_backdrop(SDL_GPUTexture* scene);

    // Replay helpers.
    SDL_GPURenderPass* target(SDL_GPUTexture* texture, bool clear);
    void end_pass();
    void fullscreen(SDL_GPUTexture* source, Pipe pipe, const SDL_Rect& scissor, Rml::Vector2f uv_scale = {1, 1},
                    Rml::Vector2f uv_offset = {0, 0});
    void push_post(float mode, float factor, const float color[4], const float limits[4], const float* matrix);
    // The fragment uniforms of the next fullscreen(), pushed there after the
    // pipeline is bound.
    void set_uniforms(const void* data, std::uint32_t size);
    void apply_filters(const Command& c);
    void render_blur(float sigma, int source_destination, int temp, const SDL_Rect& window);
    [[nodiscard]] SDL_GPUTexture* texture_of(Rml::TextureHandle handle, float& mode) const;

    SDL_GPUDevice* device_ = nullptr;
    std::array<SDL_GPUGraphicsPipeline*, kPipeCount> pipelines_{};
    SDL_GPUTexture* atlas_ = nullptr;
    SDL_GPUSampler* sampler_ = nullptr;         // Linear, clamped: layers and the atlas.
    SDL_GPUSampler* repeat_sampler_ = nullptr;  // Linear, repeating: images (RmlUi tiles them so).
    Rml::TextureHandle atlas_handle_ = 0;
    SDL_GPUTextureFormat stencil_format_ = SDL_GPU_TEXTUREFORMAT_INVALID;
    GlassMode glass_ = GlassMode::Full;

    std::unordered_map<Rml::CompiledGeometryHandle, Geometry> geometries_;
    Rml::CompiledGeometryHandle next_geometry_ = 1;
    std::unordered_map<Rml::TextureHandle, Texture> textures_;
    Rml::TextureHandle next_texture_ = 1000;
    std::unordered_map<Rml::CompiledFilterHandle, Filter> filters_;
    std::unordered_map<Rml::CompiledShaderHandle, Gradient> shaders_;
    std::uintptr_t next_effect_ = 1;

    // The frame being recorded.
    int width_ = 0;
    int height_ = 0;
    bool scissor_on_ = false;
    SDL_Rect scissor_{};
    bool clip_on_ = false;
    std::uint8_t clip_ref_ = 0;
    int top_ = 0;  // The layer drawn into.
    std::vector<Rml::Matrix4f> transforms_;  // [0] is the projection alone.
    int transform_ = 0;
    std::vector<Rml::Vertex> frame_vertices_;
    std::vector<std::uint32_t> frame_indices_;
    std::vector<Command> commands_;
    std::vector<Filter> frame_filters_;  // Copies: RmlUi may release a filter before the replay.
    std::vector<Gradient> gradients_;
    float backdrop_sigma_ = 0.0f;
    Stats stats_;

    // GPU state.
    SDL_GPUBuffer* vertex_buffer_ = nullptr;
    SDL_GPUBuffer* index_buffer_ = nullptr;
    SDL_GPUTransferBuffer* transfer_ = nullptr;
    std::uint32_t vertex_capacity_ = 0;
    std::uint32_t index_capacity_ = 0;
    std::uint32_t transfer_capacity_ = 0;
    int target_w_ = 0;
    int target_h_ = 0;
    std::vector<SDL_GPUTexture*> layers_;
    std::array<SDL_GPUTexture*, 3> post_{};  // Primary, secondary, tertiary (indices swap).
    SDL_GPUTexture* mask_ = nullptr;
    SDL_GPUTexture* stencil_ = nullptr;
    // The backdrop at half, quarter and eighth size; the blur ends in
    // down_[levels - 1][0].
    std::array<std::array<SDL_GPUTexture*, 2>, rml_fx::kMaxBackdropLevels> down_{};
    SDL_GPUTexture* backdrop_ = nullptr;
    bool backdrop_ready_ = false;
    bool replayed_ = false;

    // While replaying.
    SDL_GPUCommandBuffer* cmd_ = nullptr;
    SDL_GPURenderPass* pass_ = nullptr;
    SDL_GPUTexture* pass_target_ = nullptr;
    bool stencil_cleared_ = false;
    std::array<std::uint8_t, 160> uniforms_{};
    std::uint32_t uniforms_size_ = 0;
    int primary_ = 0;
    int secondary_ = 1;
    int tertiary_ = 2;
};

}  // namespace sc
