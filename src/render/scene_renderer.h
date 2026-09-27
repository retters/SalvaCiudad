// Draws the 3D world: sky, instanced models lit by the sun with cascaded
// shadows, and fog. Instances live in a storage buffer that changes only
// when the scene changes; each frame only the indices of the visible ones
// are uploaded.
#pragma once

#include <cstdint>
#include <memory>
#include <span>
#include <string_view>
#include <vector>

#include <SDL3/SDL_gpu.h>

#include "game/settings.h"
#include "math/vec.h"
#include "render/gpu_device.h"
#include "render/model.h"
#include "render/terrain_layer.h"

namespace sc::render {

struct Instance {
    math::Vec3 position;
    float yaw = 0.0f;
    float scale = 1.0f;
    math::Vec3 tint{1.0f, 1.0f, 1.0f};
};

// An animated character. Accessories (hats, aprons...) are chosen with a
// bit mask over the accessories registered for its body.
struct CharacterInstance {
    math::Vec3 position;
    float yaw = 0.0f;
    float scale = 1.0f;
    std::uint32_t body = 0;         // SkinnedId of the body.
    std::uint32_t clip = 0;         // Clip index of the body.
    float time = 0.0f;              // Seconds into the clip; loops.
    std::uint32_t palette = 0;
    std::uint32_t accessories = 0;  // Bit i: accessory i of the body.
};

// Colors for the palette slots (skin, hair, top, bottom, shoes, belt, hat,
// apron), linear RGB.
inline constexpr std::size_t kPaletteSlots = 8;
struct Palette {
    math::Vec3 colors[kPaletteSlots];
};

struct Lighting {
    math::Vec3 sun_direction = math::normalize({0.45f, 0.75f, 0.35f});  // Towards the sun.
    // A clear, saturated day as in the low-poly reference (decision D-627).
    math::Vec3 sun_color{2.1f, 1.95f, 1.7f};
    math::Vec3 sky_ambient{0.42f, 0.55f, 0.72f};
    math::Vec3 ground_ambient{0.18f, 0.16f, 0.12f};
    math::Vec3 zenith_color{0.04f, 0.38f, 0.90f};
    math::Vec3 horizon_color{0.50f, 0.78f, 0.95f};
};

struct SceneView {
    math::Mat4 view;
    math::Vec3 eye;
    float fov_y = 0.0f;
    float near_z = 0.1f;
    float aspect = 1.0f;
    float draw_distance_override = 0.0f;  // Debug stress view; 0 uses the settings.
    float time = 0.0f;                    // Seconds, for moving water.
    // The ground and water may reach farther than the models (to see a
    // whole map from high up); 0 = the draw distance.
    float terrain_distance = 0.0f;
    // Blur over the whole scene (the pause), in pixels at 1080p; 0 = sharp.
    float blur = 0.0f;
};

struct RenderStats {
    std::uint32_t draw_calls = 0;
    std::uint32_t instances_drawn = 0;
    std::uint32_t shadow_instances = 0;
    std::uint64_t triangles = 0;
    std::uint32_t instances_total = 0;
    std::uint32_t characters_drawn = 0;
    std::uint32_t characters_total = 0;
    float cull_ms = 0.0f;
    int msaa_samples = 1;
    int shadow_cascades = 0;
    int shadow_map_size = 0;
    float draw_distance = 0.0f;
    float vegetation_distance = 0.0f;
    std::uint32_t grass_tufts = 0;
    std::uint32_t terrain_chunks = 0;
    std::uint32_t water_chunks = 0;
};

using ModelId = std::uint32_t;
using SkinnedId = std::uint32_t;

// How far a model is drawn: normal models up to the draw distance; small
// vegetation (bushes, herbs) only up to the vegetation distance. Sky
// decorations (clouds) cast no shadows.
enum class ModelClass : std::uint8_t { Normal, SmallVegetation, Sky };

class SceneRenderer {
public:
    SceneRenderer();
    ~SceneRenderer();
    SceneRenderer(const SceneRenderer&) = delete;
    SceneRenderer& operator=(const SceneRenderer&) = delete;

    bool create(GpuDevice& gpu, const GraphicsSettings& graphics);
    void destroy();

    // Recreates what depends on the quality settings, if they changed.
    bool apply_settings(const GraphicsSettings& graphics);

    // Uploads a model; returns false on GPU errors.
    bool add_model(const ModelData& data, ModelId& id);
    void set_model_class(ModelId model, ModelClass model_class);
    // Replaces a model's instances. Only that model's part of the GPU
    // buffer is rebuilt (unless it outgrows its room).
    void set_instances(ModelId model, std::span<const Instance> instances);
    // Changes one instance (by its index in the last set_instances list)
    // without rebuilding anything: for a felled tree or a building that
    // rises. An instance with scale 0 is not drawn. The position should
    // stay within a few meters, so its region stays right.
    void update_instance(ModelId model, std::uint32_t index, const Instance& instance);
    void clear_instances();

    // The map's ground and water. Returns false on invalid data or GPU
    // errors; the scene then has no terrain.
    bool set_terrain(const TerrainData& data);
    void clear_terrain();

    // Animated bodies. Returns false if the model has no skeleton or clips.
    bool add_skinned_model(const ModelData& data, SkinnedId& id);
    // A rigid model pinned to a bone of `body`, in the body's bind pose: its
    // origin goes to the start of the bone. Returns the accessory bit.
    bool add_accessory(const ModelData& data, SkinnedId body, std::string_view bone, std::uint32_t& bit);
    [[nodiscard]] int clip_index(SkinnedId body, std::string_view name) const;
    [[nodiscard]] float clip_duration(SkinnedId body, std::uint32_t clip) const;
    void set_palettes(std::span<const Palette> palettes);
    // Replaces the characters to draw; call every frame they move.
    void set_characters(std::span<const CharacterInstance> characters);

    // Records the shadow passes and the main pass into the frame. The
    // swapchain ends up holding the (resolved) scene.
    bool render(GpuFrame& frame, const SceneView& view, const Lighting& lighting);

    [[nodiscard]] const RenderStats& stats() const { return stats_; }

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
    RenderStats stats_;
};

// Levels from GraphicsSettings, in the units the renderer uses.
[[nodiscard]] float draw_distance_for_level(int level);
[[nodiscard]] float vegetation_distance_for_level(int level);
[[nodiscard]] float grass_distance_for_level(int level);
[[nodiscard]] int shadow_cascades_for_level(int level);
[[nodiscard]] int shadow_map_size_for_level(int level);
[[nodiscard]] float shadow_distance_for_level(int level);
[[nodiscard]] int msaa_samples_for_level(int level);

// Cascade end distances between `near_z` and `max_distance`, blending
// logarithmic and uniform splits.
void compute_cascade_splits(float near_z, float max_distance, int count, float out[3]);

}  // namespace sc::render
