// Draws the 3D world: sky, instanced models lit by the sun with cascaded
// shadows, and fog. Instances live in a storage buffer that changes only
// when the scene changes; each frame only the indices of the visible ones
// are uploaded.
#pragma once

#include <cstdint>
#include <memory>
#include <span>
#include <vector>

#include <SDL3/SDL_gpu.h>

#include "game/settings.h"
#include "math/vec.h"
#include "render/gpu_device.h"
#include "render/model.h"

namespace sc::render {

struct Instance {
    math::Vec3 position;
    float yaw = 0.0f;
    float scale = 1.0f;
    math::Vec3 tint{1.0f, 1.0f, 1.0f};
};

struct Lighting {
    math::Vec3 sun_direction = math::normalize({0.45f, 0.75f, 0.35f});  // Towards the sun.
    math::Vec3 sun_color{1.9f, 1.8f, 1.6f};
    math::Vec3 sky_ambient{0.40f, 0.47f, 0.60f};
    math::Vec3 ground_ambient{0.16f, 0.14f, 0.11f};
    math::Vec3 zenith_color{0.16f, 0.30f, 0.60f};
    math::Vec3 horizon_color{0.56f, 0.66f, 0.78f};
};

struct SceneView {
    math::Mat4 view;
    math::Vec3 eye;
    float fov_y = 0.0f;
    float near_z = 0.1f;
    float aspect = 1.0f;
    float draw_distance_override = 0.0f;  // Debug stress view; 0 uses the settings.
};

struct RenderStats {
    std::uint32_t draw_calls = 0;
    std::uint32_t instances_drawn = 0;
    std::uint32_t shadow_instances = 0;
    std::uint64_t triangles = 0;
    std::uint32_t instances_total = 0;
    float cull_ms = 0.0f;
    int msaa_samples = 1;
    int shadow_cascades = 0;
    int shadow_map_size = 0;
    float draw_distance = 0.0f;
};

using ModelId = std::uint32_t;

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
    void set_instances(ModelId model, std::span<const Instance> instances);
    void clear_instances();

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
[[nodiscard]] int shadow_cascades_for_level(int level);
[[nodiscard]] int shadow_map_size_for_level(int level);
[[nodiscard]] float shadow_distance_for_level(int level);
[[nodiscard]] int msaa_samples_for_level(int level);

// Cascade end distances between `near_z` and `max_distance`, blending
// logarithmic and uniform splits.
void compute_cascade_splits(float near_z, float max_distance, int count, float out[3]);

}  // namespace sc::render
