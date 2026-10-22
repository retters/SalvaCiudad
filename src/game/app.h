// Application: owns the window, the GPU, the settings, the interface and the
// main loop, and provides the services the menus use.
#pragma once

#include <array>
#include <cstdint>
#include <filesystem>
#include <memory>
#include <optional>
#include <string>
#include <vector>

#include <SDL3/SDL_events.h>

#include "game/camera.h"
#include "game/dev_tools.h"
#include "game/game_session.h"
#include "game/game_clock.h"
#include "game/map_generation.h"
#include "game/map_scene.h"
#include "game/occluders.h"
#include "game/perf_window.h"
#include "game/services.h"
#include "game/sound_director.h"
#include "game/settings.h"
#include "game/map_report.h"
#include "game/terrain_names.h"
#include "game/walkers.h"
#include "game/ui_host.h"
#include "game/village_view.h"
#include "platform/paths.h"
#include "platform/window.h"
#include "render/debug_overlay.h"
#include "render/gpu_device.h"
#include "game/model_studio.h"
#include "render/rml_renderer.h"
#include "render/scene_renderer.h"
#include "render/ui_renderer.h"
#include "ui/context.h"
#include "ui/font_library.h"
#include "ui/glyph_atlas.h"
#include "ui/rml/rml_test_window.h"
#include "ui/rml/rml_ui.h"
#include "ui/text.h"

namespace sc {

class App final : public Services {
public:
    // `instance` 0 is the normal game; 1..8 use their own data folder and
    // network port (for trying multiplayer on one computer).
    // `replay` (phase 38, `--reporte <folder>`): shows the map and view of a
    // map report, saves a screenshot of it in that folder and quits.
    explicit App(int instance = 0, bool loopback = false, std::filesystem::path replay = {});
    ~App() override;
    App(const App&) = delete;
    App& operator=(const App&) = delete;

    int run();

    // Services.
    Settings& settings() override { return settings_->settings(); }
    void settings_changed() override;
    bool apply_display(const DisplaySettings& display) override;
    void apply_vsync() override;
    void apply_graphics() override;
    bool scene_available() const override { return scene_ok_; }
    CameraMode camera_mode() const override { return camera_.mode(); }
    void apply_language() override;
    void apply_font() override;
    std::vector<std::string> monitor_names() override;
    std::vector<Resolution> fullscreen_resolutions(const std::string& monitor) override;
    const ui::FontLibrary& fonts() const override { return fonts_; }
    std::vector<UiStyleChoice> ui_styles() const override;
    rml::RmlUi* rml() override { return rml_.ready() ? &rml_ : nullptr; }
    void set_hud_image(const std::string& name, int width, int height, const std::vector<std::uint8_t>& rgba) override {
        rml_renderer_.set_live_image(name, width, height, rgba);
    }
    void open_data_folder() override;
    mods::ModLibrary& mod_library() override { return mod_library_; }
    void apply_mods(const std::vector<std::string>& enabled) override;
    void open_mods_folder() override;
    const sim::Content* content() const override { return pack_ ? &pack_->content : nullptr; }
    void request_quit() override { running_ = false; }
    void start_map_generation(const sim::MapSettings& settings, const sim::GameRules& rules,
                              bool start_towns = false) override;
    MapGenStatus map_generation_status() const override { return map_job_.status(); }
    void cancel_map_generation() override { map_job_.cancel(); }
    bool enter_generated_map() override;
    void leave_map() override;
    const sim::MapData* current_map() const override { return map_ ? &map_->map : nullptr; }
    GameSession* session() override { return session_.get(); }
    int game_speed() const override;
    void set_game_speed(int speed) override;
    int max_game_speed() const override;
    void save_game() override;
    std::vector<save::Entry> list_saves() override;
    bool load_game(const std::filesystem::path& file) override;
    bool host_game(const sim::MapSettings& map, const sim::GameRules& rules) override;
    bool join_game(const std::string& address, std::uint16_t port) override;
    void leave_network() override;
    bool open_game(std::uint8_t access) override;
    void set_access(std::uint8_t access) override;
    [[nodiscard]] bool hosting() const override;
    void watch_game() override;
    void play_game(int then) override;
    bool load_game_as_host(const std::filesystem::path& file) override;
    [[nodiscard]] int saved_access() const override;
    net::NetSession* net() override { return net_.get(); }
    void set_lan_search(bool on) override;
    std::vector<net::LanGame> lan_games() override;
    std::string player_name() const override;

private:
    bool init();
    void shutdown();
    void load_languages();
    // Finds the mods, builds the content with the chosen ones and loads
    // their texts and models.
    void load_mods();
    void open_folder(const std::filesystem::path& dir);
    void fatal_error(const char* text_key);
    void handle_event(const SDL_Event& event);
    void frame();
    void render_frame(float dt);
    void update_camera(float dt);
    void update_frame_stats(float dt);
    void handle_scene_click(std::uint32_t width, std::uint32_t height);
    // A village game: the ghost of the building being placed, and clicks.
    void update_placement(std::uint32_t width, std::uint32_t height);
    void update_founding(std::uint32_t width, std::uint32_t height);
    void handle_game_click(std::uint32_t width, std::uint32_t height, math::Vec3 origin, math::Vec3 dir);
    // The mouse ray into the world; false when the mouse is outside.
    bool mouse_ray(std::uint32_t width, std::uint32_t height, math::Vec3& origin, math::Vec3& dir) const;
    // The statistics window's "under the cursor" (phase 37), while it is open.
    void update_cursor_info(std::uint32_t width, std::uint32_t height);
    // The ray through a point of the window.
    bool screen_ray(std::uint32_t width, std::uint32_t height, float x, float y, math::Vec3& origin, math::Vec3& dir) const;
    // Map reports (phase 38): marking with Ctrl+F12, and `--reporte`.
    void begin_marking();
    void end_marking();
    // A key while marking; true if it was used.
    void marking_key(SDL_Scancode key);
    void update_marking();
    void draw_marking();
    void save_report(const FrameCapture& capture);
    [[nodiscard]] bool world_only() const;
    // How far a ray from the camera looks for the ground (the statistics
    // window and map reports).
    [[nodiscard]] float far_pick() const;
    bool load_replay(const sim::Content* content);
    void update_replay();
    void finish_replay(const FrameCapture& capture);
    // Shows a game (new or loaded) on its map, with the camera at its town.
    void start_session(std::unique_ptr<GameSession> session);
    void autosave_if_due();
    // Multiplayer.
    bool ensure_enet();
    void update_network(std::uint64_t now_ms);
    void handle_net_event(const net::NetEvent& e);
    void report_game_events();  // Toasts for fires and outbreaks in the local town.
    [[nodiscard]] std::string town_name(std::uint8_t player) const;
    void focus_camera(float x, float z) override;
    void update_sound(float dt);
    [[nodiscard]] std::array<float, 3> camera_view() const override {
        return {camera_.target().x, camera_.target().z, camera_.distance()};
    }
    [[nodiscard]] const std::vector<mods::ModScript>* mod_scripts() const override {
        return pack_ ? &pack_->scripts : nullptr;
    }
    [[nodiscard]] int overlay() const override { return overlay_; }
    void set_overlay(int layer) override;
    [[nodiscard]] CameraGround camera_ground() const override;
    void set_ui_image(std::uint32_t id, int width, int height, std::vector<std::uint8_t> rgba) override {
        (void)ui_renderer_.set_image(id, width, height, std::move(rgba));
    }
    std::uint32_t view_width_ = 1;   // The last frame's size, for camera_ground().
    std::uint32_t view_height_ = 1;
    int overlay_ = 0;
    SoundDirector sound_;  // Phase 18.
    bool sound_started_ = false;
    // Phase 32: the fog of war the renderer shows (mode, grid side and the
    // view's generation), so it changes only when the game's fog does.
    int war_mode_shown_ = 0;
    std::int32_t war_side_shown_ = 0;
    std::uint32_t war_generation_shown_ = 0;
    void update_war_fog();
    void apply_snapshot(std::vector<std::uint8_t> state);
    void close_network();
    [[nodiscard]] net::LocalInfo local_info() const;
    [[nodiscard]] std::string seat_name(std::uint8_t slot) const;
    [[nodiscard]] std::uint16_t game_port() const { return static_cast<std::uint16_t>(net::kDefaultPort + instance_); }
    // Shows a game's map (loaded or received) with a fresh view.
    bool show_map_of(const sim::MapData& map);
    void write_save(const std::string& stem, const std::string& name, bool quiet);
    void draw_scene_markers(std::uint32_t width, std::uint32_t height);
    void draw_start_markers(std::uint32_t width, std::uint32_t height);
    void draw_supply_markers(std::uint32_t width, std::uint32_t height);
    void draw_marker(std::uint32_t width, std::uint32_t height, math::Vec3 at, ui::Color color);
    [[nodiscard]] DevContext dev_context(std::uint32_t width, std::uint32_t height);
    // The map behind the menus (phase 50).
    void load_menu_seeds();
    // Starts making the map of `seed`, or of one of the list if empty.
    void start_menu_background(std::optional<std::uint64_t> seed = {});
    // Shows the map once it is made, and takes it away under a game's map.
    void update_menu_background();
    void hide_menu_background();
    void reset_camera_to_menu();
    // True in the views the player moves the camera in.
    [[nodiscard]] bool interactive_scene() const;
    void update_mouse_capture();
    [[nodiscard]] math::Mat4 camera_view_proj(std::uint32_t width, std::uint32_t height) const;
    void cycle_window_mode();
    void apply_pending_vsync();
    void save_settings_if_due(bool force);
    [[nodiscard]] float ui_scale() const;

    std::optional<DataPaths> paths_;
    std::optional<SettingsStore> settings_;
    Window window_;
    GpuDevice gpu_;
    UiRenderer ui_renderer_;
    ui::FontLibrary fonts_;
    ui::GlyphAtlas atlas_;
    ui::TextRenderer text_;
    ui::Context ui_;
    // The player's interface with RmlUi (phases 117 to 127), drawn over the
    // old one; for now only the development test window.
    RmlRenderer rml_renderer_;
    rml::RmlUi rml_;
    rml::TestWindow rml_test_;
    ModelStudio studio_;  // Thumbnails and portraits (phase 120).
    std::string rml_style_;  // The style last given to rml_ (ui.style).
    // data/ui, then the ui folder of each loaded mod.
    [[nodiscard]] std::vector<std::filesystem::path> ui_roots() const;
    std::unique_ptr<UiHost> host_;
    ui::Input input_;
    render::SceneRenderer scene_;
    render::Lighting lighting_;
    // Phase 69: how much of the night there is, 0 (day) to 1, and its lights.
    float night_ = 0.0f;
    std::vector<render::PointLight> night_lights_;
    // The villagers' bodies, and the people placed with the developer tools.
    Walkers walkers_;
    MapScene map_scene_;
    mods::ModLibrary mod_library_;
    std::shared_ptr<const mods::BuildResult> pack_;
    DevTools dev_tools_;
    MapGenerationJob map_job_;
    std::unique_ptr<GeneratedMap> map_;  // The map being shown.
    std::unique_ptr<GameSession> session_;  // The village game on it (phase 8).
    // Multiplayer (phase 9); destroyed in reverse order: the session
    // first, then the link it uses, then ENet.
    int instance_ = 0;
    bool loopback_ = false;  // Multiplayer on this computer only.
    std::unique_ptr<net::EnetLibrary> enet_;
    std::unique_ptr<net::EnetLink> link_;
    std::unique_ptr<net::LanDiscovery> lan_search_;
    std::unique_ptr<net::LanDiscovery> lan_announce_;
    std::unique_ptr<net::NetSession> net_;
    std::optional<net::Start> net_start_;  // The network game whose map is being generated.
    // Phase 79. What a spectator wants once it has a seat (kThenNothing:
    // nothing; -1: to found; else the town to ask), the town whose founder
    // it still has to ask, and what the lobby last said about who watches.
    static constexpr int kThenNothing = -2;
    int play_then_ = kThenNothing;
    int ask_town_ = -1;
    std::vector<std::string> shown_watchers_;
    std::uint16_t shown_watching_ = 0;
    bool watch_shown_ = false;
    void follow_watching();
    // Phase 78: a saved game loaded to be hosted, while its lobby is open.
    std::unique_ptr<GameSession> saved_session_;
    [[nodiscard]] GameSession::LoadResult read_save(const std::filesystem::path& file, std::unique_ptr<GameSession>& out);
    sim::GameRules pending_rules_;         // Rules of the single-player game being generated.
    bool pending_start_towns_ = false;     // Whether it begins with its town standing (the tutorial).
    VillageView village_;
    std::uint64_t next_autosave_tick_ = 0;
    int autosave_slot_ = 0;
    bool right_clicked_ = false;  // Right button released without dragging.
    float right_press_x_ = 0.0f;
    float right_press_y_ = 0.0f;
    bool scene_ok_ = false;
    Camera camera_;
    DebugOverlay debug_;
    DebugInfo debug_info_;
    TerrainNames cursor_names_;
    // The cell described last: redone only when it or the language changes.
    struct CursorKey {
        std::int32_t cx = 0;
        std::int32_t cz = 0;
        bool shown = false;
        std::uint64_t language = 0;
        const sim::MapData* map = nullptr;
        bool operator==(const CursorKey&) const = default;
    };
    CursorKey cursor_key_;
    // Marking a map report: the strokes, and the speed to go back to.
    struct Marking {
        bool active = false;
        bool capture = false;  // Enter pressed: the next frame is captured.
        bool drawing = false;
        std::vector<report::Stroke> strokes;
        std::optional<report::Cell> cursor;
        int speed = -1;  // -1: the game was not paused for it.
    };
    Marking marking_;
    // `--reporte`: the report shown, and how far along.
    enum class ReplayStep : std::uint8_t { None, Generating, Settling, Tour, Capture, Done };
    std::filesystem::path replay_dir_;
    std::optional<report::Replay> replay_;
    ReplayStep replay_step_ = ReplayStep::None;
    std::uint64_t replay_since_ns_ = 0;
    int replay_frames_ = 0;
    // The frames drawn in the second half of the settling, to note the
    // frame rate in the report (phase 47).
    std::uint64_t replay_measure_ns_ = 0;
    int replay_measured_ = 0;
    std::uint64_t replay_measured_ns_ = 0;
    int replay_exit_code_ = 0;
    // Phase 129: the camera's trip of a report, and what each step cost.
    void start_tour(std::uint64_t now);
    void update_tour(std::uint64_t now);
    std::size_t tour_step_ = 0;
    std::uint64_t tour_step_ns_ = 0;
    math::Vec3 tour_origin_;
    report::TourStep tour_from_;
    std::optional<sim::Season> tour_season_;  // The season the tour shows now.
    PerfWindow tour_perf_;
    std::string tour_notes_;
    float camera_wheel_ = 0.0f;   // Wheel notches since the last camera update.
    float camera_drag_px_ = 0.0f;  // Middle-button drag since the last update.
    bool middle_down_ = false;
    bool right_down_ = false;
    float camera_drag_py_ = 0.0f;  // Vertical drag (third person pitch).
    float camera_look_dx_ = 0.0f;  // Relative mouse motion (first person).
    float camera_look_dy_ = 0.0f;
    float press_x_ = 0.0f;         // Where the left button went down.
    float press_y_ = 0.0f;
    bool mouse_captured_ = false;
    float fps_window_s_ = 0.0f;
    int fps_window_frames_ = 0;
    // Phase 129: what each frame cost, logged every few seconds on a map.
    void log_perf(float dt);
    PerfWindow perf_;
    FrameSample sample_;  // This frame's, filled as it goes.
    std::uint64_t perf_relayouts_ = 0;  // The renderer's counters at the last log.
    std::uint64_t perf_sorted_ = 0;
    std::uint64_t perf_bytes_ = 0;
    // Phase 132: where the animals are seen from: the main eye and each
    // camera window's, with how far each draws them.
    std::vector<VillageView::Eye> creature_eyes_;
    std::array<std::optional<VillageView::Eye>, kCameraWindows> inset_eyes_{};
    GameClock clock_;
    // Phase 61: following a villager and the ghost of the camera's anchor.
    void follow_villager(const CameraInput& in);
    void show_anchor(float dt);
    sim::EntityId followed_shown_;
    sim::EntityId last_clicked_villager_;
    std::uint64_t last_click_ns_ = 0;
    static constexpr std::uint64_t kDoubleClickNs = 400'000'000ull;
    math::Vec3 anchor_last_;
    bool anchor_known_ = false;
    // What is in the camera's way, drawn see-through.
    Occluders occluders_;
    // Phase 64: asks the renderer for the picture of a camera window, one a
    // frame in turns (each window moves at half the frame rate).
    void update_camera_windows();
    void order_explorer(int width, int height);
    std::uint32_t camera_window_turn_ = 0;
    // Frames in a row that lost ticks; after a few the speed goes a step down.
    int slow_frames_ = 0;
    static constexpr int kSlowFramesToLower = 20;
    // The map behind the menus: made in its own thread from a seed of the
    // list, with a game without towns on it so its animals live.
    MapGenerationJob menu_job_;
    std::unique_ptr<GeneratedMap> menu_map_;
    std::unique_ptr<sim::Game> menu_game_;
    std::uint64_t menu_seed_ = 0;
    std::uint64_t menu_started_ns_ = 0;
    std::vector<std::uint64_t> menu_seeds_;       // data/menu_backgrounds.json.
    std::vector<std::uint64_t> menu_user_seeds_;  // The user's own file.
    // Vsync changes wait until the frame is submitted: the swapchain cannot
    // be rebuilt while one of its images is in use (decision D-614).
    bool vsync_pending_ = false;
    bool running_ = true;
    bool sdl_ready_ = false;
    std::uint64_t last_frame_ns_ = 0;
    std::uint64_t settings_dirty_since_ns_ = 0;  // 0 = nothing to save.
    WindowMode last_fullscreen_mode_ = WindowMode::Borderless;
};

}  // namespace sc
