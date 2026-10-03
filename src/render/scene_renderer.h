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
    // Building palette (phase 31): 0 keeps the model's own colors; n takes
    // palette n - 1 for the materials named after its slots.
    std::uint32_t palette = 0;
    // Phase 34: shows as a silhouette through the fog of war, however low.
    bool landmark = false;
    // Phase 52: which of the model's looks it is drawn with (0: the model
    // itself; see SceneRenderer::set_model_looks).
    std::uint8_t look = 0;
    // Phase 61: how see-through it is drawn, in quarters (0 to kMaxFade).
    std::uint8_t fade = 0;
};
inline constexpr std::uint8_t kMaxFade = 3;
inline constexpr float kCarriedReach = 4.0f;

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
    // Phase 67: those of `accessories` not drawn from far away (what a
    // villager carries): only up to kCarriedReach times the distance at
    // which the body turns to its far version, and never in the shadows.
    std::uint32_t near_only = 0;
    // How see-through it is drawn, in quarters (0 to kMaxFade); a faded
    // character casts no shadow.
    std::uint8_t fade = 0;
};

// Colors for the palette slots (skin, hair, top, bottom, shoes, belt, hat,
// apron), linear RGB.
inline constexpr std::size_t kPaletteSlots = 8;
struct Palette {
    math::Vec3 colors[kPaletteSlots];
};

// The color a palette slot replaces in a model: that of its material named
// as the slot ("skin"), or of the first one that starts with it
// ("skin_light"). False if the model has no material of that slot.
[[nodiscard]] bool palette_reference(const ModelData& model, std::size_t slot, math::Vec3& color);

// Colors for the building palette slots (var_roof, var_roof_dark,
// var_walls, var_shutter), linear RGB. Models name a material after a slot
// to have it recolored per instance.
inline constexpr std::size_t kBuildingPaletteSlots = 4;
inline constexpr std::uint32_t kMaxBuildingPalettes = 256;
struct BuildingPalette {
    math::Vec3 colors[kBuildingPaletteSlots];
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
    // Snow on the ground and on what faces up, 0..1 (phase 10); the grass
    // hides under it.
    float snow = 0.0f;
    // Ice over the water, 0..1 (phase 18): whiter and still.
    float ice = 0.0f;
};

struct RenderStats {
    std::uint32_t draw_calls = 0;
    std::uint32_t instances_drawn = 0;
    std::uint32_t shadow_instances = 0;
    std::uint64_t triangles = 0;
    std::uint32_t instances_total = 0;
    std::uint32_t instances_far = 0;  // Drawn with their far version (phase 52).
    std::uint32_t characters_drawn = 0;
    std::uint32_t characters_far = 0;  // Of those, with their far version (phase 57).
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

// Phase 64: a small second view of the scene, drawn into a texture of its
// own for a camera window: with the main view's shadows where they reach,
// without grass, and only as far as `distance`.
struct InsetView {
    math::Mat4 view;
    math::Vec3 eye;
    float fov_y = 0.9f;
    float near_z = 0.2f;
    float distance = 200.0f;
};
inline constexpr int kInsetWidth = 320;
inline constexpr int kInsetHeight = 200;
inline constexpr int kInsets = 2;

using ModelId = std::uint32_t;
inline constexpr ModelId kNoFarModel = ~0u;
inline constexpr std::size_t kMaxLooks = 4;
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
    // Phase 52. The looks of a model: other models its instances can be
    // drawn as, chosen by Instance::look (1 is looks[0]; an instance whose
    // look is not there is drawn as the model itself). At most kMaxLooks - 1.
    // A tree's states of the year are looks: changing one costs nothing.
    void set_model_looks(ModelId model, std::span<const ModelId> looks);
    // The far version of a model: drawn in its place where it is small on
    // screen, and always in the shadows. kNoFarModel takes it away.
    void set_far_model(ModelId model, ModelId far_model);
    // Changes only the look of one instance (by its index in the last
    // set_instances list).
    void set_instance_look(ModelId model, std::uint32_t index, std::uint8_t look);
    // For the model viewer: every model with a far version drawn near, or far.
    enum class LodMode : std::uint8_t { Auto, Near, Far };
    void set_lod_mode(LodMode mode);
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
    // The far version of a body (phase 57): the same skeleton with a
    // simpler mesh and no clips of its own. A character lower on screen
    // than the level of detail's pixels is drawn with it, and so are all
    // the shadows.
    bool set_far_body(const ModelData& data, SkinnedId body);
    // A rigid model pinned to a bone of `body`, in the body's bind pose: its
    // origin goes to the start of the bone. Returns the accessory bit.
    bool add_accessory(const ModelData& data, SkinnedId body, std::string_view bone, std::uint32_t& bit);
    // The same, placed by `placement`: where the model's points are in the
    // body's bind pose (a tool turned to lie along a hand).
    bool add_accessory(const ModelData& data, SkinnedId body, std::string_view bone, const math::Mat4& placement,
                       std::uint32_t& bit);
    [[nodiscard]] int clip_index(SkinnedId body, std::string_view name) const;
    [[nodiscard]] float clip_duration(SkinnedId body, std::uint32_t clip) const;
    void set_palettes(std::span<const Palette> palettes);
    // The palettes an Instance's `palette` picks (at most kMaxBuildingPalettes).
    void set_building_palettes(std::span<const BuildingPalette> palettes);
    // Replaces the characters to draw; call every frame they move.
    void set_characters(std::span<const CharacterInstance> characters);

    // Fog of war (phase 32): `mode` 1 (static) or 2 (dynamic) over a grid of
    // `side` x `side` texels of `cell` meters from the map's corner; 0 turns
    // it off. The texels start unexplored; update_war_fog() fills them.
    bool set_war_fog(int mode, std::int32_t side, float cell);
    // Sends the rectangle x, z, w, d (in texels) of `texels`, the whole grid
    // row by row (side * side values: 0 unexplored, 128 explored, 255 in
    // sight), with the next frame.
    void update_war_fog(std::span<const std::uint8_t> texels, std::int32_t x, std::int32_t z, std::int32_t w,
                        std::int32_t d);
    // Phase 34: what stands higher than `heights` (centimeters, `side` x
    // `side` texels over the same area as the fog) shows through the fog,
    // fully `band` meters over it. Empty turns it off.
    bool set_war_ceiling(std::span<const std::uint16_t> heights, std::int32_t side, float band);

    // Draws inset `slot` (0 to kInsets - 1) with the next render(), after
    // the main view. One inset a frame: the last one asked for.
    void request_inset(int slot, const InsetView& view);
    // The picture of an inset, kInsetWidth x kInsetHeight; null until it
    // has been drawn (and again after the quality settings change).
    [[nodiscard]] SDL_GPUTexture* inset_texture(int slot) const;

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
// A model with a far version changes to it when it is lower than this many
// pixels on screen (by the vegetation quality level).
[[nodiscard]] float lod_pixels_for_level(int level);
[[nodiscard]] float grass_distance_for_level(int level);
[[nodiscard]] int shadow_cascades_for_level(int level);
[[nodiscard]] int shadow_map_size_for_level(int level);
[[nodiscard]] float shadow_distance_for_level(int level);
[[nodiscard]] int msaa_samples_for_level(int level);

// Cascade end distances between `near_z` and `max_distance`, blending
// logarithmic and uniform splits.
void compute_cascade_splits(float near_z, float max_distance, int count, float out[3]);

}  // namespace sc::render
