// The model viewer (phase 30): a developer tool apart from the game. It
// lists the models of a mod by category and group, shows them with the
// game's renderer, and points out models nothing uses and definitions whose
// model is missing. It never changes a file.
#pragma once

#include <array>
#include <cstdint>
#include <filesystem>
#include <map>
#include <memory>
#include <optional>
#include <set>
#include <string>
#include <vector>

#include <SDL3/SDL_events.h>
#include <SDL3/SDL_video.h>

#include "mods/mod_library.h"
#include "platform/paths.h"
#include "render/gpu_device.h"
#include "render/scene_renderer.h"
#include "sim/climate.h"
#include "viewer/model_catalog.h"

namespace sc::viewer {

// A camera that circles a point: the left button turns it, the right or
// middle button moves the point, the wheel comes closer.
struct OrbitCamera {
    math::Vec3 target;
    float yaw = 0.6f;     // Radians around the vertical.
    float pitch = 0.35f;  // Radians above the horizon.
    float distance = 12.0f;

    [[nodiscard]] math::Vec3 eye() const;
    [[nodiscard]] math::Mat4 view() const;
    void rotate(float dx_px, float dy_px);
    void pan(float dx_px, float dy_px, float view_height_px);
    void zoom(float notches);
};

inline constexpr float kFovY = 40.0f;  // Degrees.

class ViewerApp {
public:
    // `studies_dir`: a folder of models in study to offer beside the mods;
    // empty for the default (see default_studies_dir).
    explicit ViewerApp(std::filesystem::path studies_dir = {});
    ~ViewerApp();
    ViewerApp(const ViewerApp&) = delete;
    ViewerApp& operator=(const ViewerApp&) = delete;

    int run();

private:
    // A model file on the GPU.
    struct Loaded {
        bool ok = false;
        std::string error;  // English, from the loader.
        ModelStats stats;
        math::Vec3 bounds_min;
        math::Vec3 bounds_max;
        render::ModelId model = kNone;   // Rigid models.
        render::SkinnedId body = kNone;  // Bodies, and accessories on a body.
        std::uint32_t accessories = 0;   // Accessories: the mask that shows it.
        std::uint32_t clip = 0;          // Bodies: idle, or the first clip.
        // Bodies: the skeleton, to draw it over the model (phase 45).
        std::vector<int> joint_parent;
        std::vector<math::Vec3> joint_rest;               // Model space.
        std::vector<std::vector<math::Mat4>> clip_skin;   // Per clip: frames * joints.
        std::filesystem::file_time_type time{};
        std::uintmax_t bytes = 0;
    };
    static constexpr std::uint32_t kNone = ~0u;

    // What is on screen: a whole group or one model.
    struct Selection {
        std::optional<std::size_t> group;
        std::optional<std::size_t> model;  // Set when one model is shown alone.
    };

    bool init();
    void shutdown();
    void load_languages();
    bool init_imgui();
    void apply_ui_scale();
    // Reads the mods again and rebuilds the catalog for `mod_`.
    void load_catalog();
    [[nodiscard]] std::filesystem::path builtin_mods_dir() const;
    // art/studies/animals of the source tree this viewer was built from, if
    // it is there; empty otherwise.
    [[nodiscard]] std::filesystem::path default_studies_dir() const;
    // Whether the folder of models in study can be shown.
    [[nodiscard]] bool has_studies() const;
    // Whether one model is shown alone: picked in a group, or the only one of its group.
    [[nodiscard]] bool one_shown() const;
    // The clip a body plays now: the chosen one or its idle.
    [[nodiscard]] std::uint32_t shown_clip(const Loaded& l) const;
    void frame();
    void handle_event(const SDL_Event& event);
    void render_frame(float dt);

    // Interface.
    void draw_ui(float width, float height);
    void draw_catalog_tab();
    void draw_review_tab();
    void draw_card(float width, float height);
    void draw_model_card(const CatalogModel& m);
    void draw_animation_controls(const Loaded& l);
    // Lines between the joints of the model shown alone, at this frame.
    void draw_skeleton();
    void draw_status(float width, float height);
    [[nodiscard]] std::string group_label(const CatalogGroup& g) const;
    [[nodiscard]] std::string use_label(const Use& u) const;
    [[nodiscard]] bool group_passes_filter(const CatalogGroup& g) const;
    // The catalog list as shown now: filtered, sorted and opened.
    [[nodiscard]] std::vector<CatalogRow> catalog_rows() const;
    // Moves the cursor with a key; a group or model under it is shown at once.
    void navigate_catalog(NavKey key);
    void set_open(const CatalogRow& row, bool open);

    // Scene.
    void select(Selection selection);
    [[nodiscard]] std::vector<std::size_t> shown_models() const;
    Loaded& load_model(const std::string& mod, const std::string& path, const std::filesystem::path& file);
    // Registers a hat, beard or apron on its own copy of a body.
    bool load_accessory(Loaded& out, const render::ModelData& data, const std::string& path);
    void layout_scene();
    void frame_camera();
    void update_scene(float dt);
    void check_reload(float dt);
    [[nodiscard]] math::Vec3 tint_for(const CatalogModel& m, std::size_t index) const;

    std::optional<DataPaths> paths_;
    SDL_Window* window_ = nullptr;
    GpuDevice gpu_;
    render::SceneRenderer scene_;
    bool scene_ok_ = false;
    bool imgui_ok_ = false;
    bool sdl_ready_ = false;
    bool running_ = true;
    std::string font_data_;  // The interface font; ImGui reads it while it runs.
    float ui_scale_ = 0.0f;
    std::uint64_t last_frame_ns_ = 0;

    // Content.
    mods::ModLibrary library_;
    std::unique_ptr<mods::BuildResult> pack_;
    std::string mod_ = mods::kCoreModId;  // The mod being looked at, or kStudiesMod.
    std::filesystem::path studies_dir_;   // Models in study; may be empty.
    bool studies_resolved_ = false;       // The folder given on the command line was looked up.
    std::filesystem::path mods_dir_;      // Where the built-in mods are read from.
    Catalog catalog_;
    std::map<std::string, Loaded> loaded_;  // By "<mod>/<path>".

    // What is shown.
    Selection selection_;
    struct Placed {
        std::size_t model = 0;  // Into catalog_.models.
        math::Vec3 position;
    };
    std::vector<Placed> placed_;
    std::vector<render::ModelId> shown_rigid_;  // Their instances, to clear them.
    render::ModelId ground_ = kNone;
    std::vector<render::CharacterInstance> characters_;
    float anim_time_ = 0.0f;
    float spin_ = 0.0f;
    float reload_timer_ = 0.0f;
    std::string status_;  // Last reload or error.
    float status_time_ = 0.0f;

    // The catalog list: what is open and the keyboard cursor.
    std::array<bool, static_cast<std::size_t>(Category::Count)> category_open_{true, true, true, true, true, true};
    std::set<std::size_t> open_groups_;
    CatalogRow cursor_;
    bool scroll_to_cursor_ = false;
    bool catalog_tab_ = true;  // The Models tab is the one shown.

    // Options.
    char search_[64] = {};
    bool only_unused_ = false;
    bool only_single_ = false;
    bool show_reference_ = true;
    bool show_ground_ = true;
    bool turntable_ = false;
    int season_ = 1;  // sim::Season; summer.
    bool snowy_ = false;
    int lod_ = 0;  // render::SceneRenderer::LodMode.
    std::uint32_t palette_ = 0;
    std::uint32_t palette_count_ = 1;
    std::uint32_t building_palette_ = 0;
    std::uint32_t building_palette_count_ = 0;
    int clip_ = -1;  // -1: each body's idle.
    // Animation review (phase 45).
    float play_speed_ = 1.0f;     // 0.25 to 2.
    bool paused_ = false;
    bool moving_ground_ = true;   // The ground runs under a clip that has a speed.
    bool show_skeleton_ = false;

    OrbitCamera camera_;
    bool rotating_ = false;
    bool panning_ = false;
    std::uint32_t view_width_ = 1;
    std::uint32_t view_height_ = 1;
};

}  // namespace sc::viewer
