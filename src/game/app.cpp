#include "game/app.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <ctime>
#include <string_view>

#include <SDL3/SDL_filesystem.h>
#include <SDL3/SDL_init.h>
#include <SDL3/SDL_keyboard.h>
#include <SDL3/SDL_locale.h>
#include <SDL3/SDL_messagebox.h>
#include <SDL3/SDL_misc.h>
#include <SDL3/SDL_platform.h>
#include <SDL3/SDL_timer.h>

#include "core/log.h"
#include "core/text.h"
#include "embedded/lang_en.h"
#include "i18n/translator.h"
#include "mods/mod_settings.h"
#include "core/file_io.h"
#include "version.h"

#include <SDL3/SDL_keyboard.h>

namespace sc {

using i18n::tr;

namespace {

// Settings changes are saved in groups, a little after the last change, and
// always on exit.
constexpr std::uint64_t kSettingsSaveDelayNs = 2'000'000'000;

// While minimized, wake up this often to keep the simulation ticking.
constexpr std::int32_t kMinimizedWaitMs = 50;

constexpr int kAtlasSize = 2048;

// Objects in the renderer test scene (phase 3 acceptance: 50 000).
constexpr std::size_t kTestSceneInstances = 50'000;

// Animated villagers around the scene center (phase 4 acceptance: 2000).
constexpr std::size_t kTestCrowd = 2'000;
constexpr float kTestCrowdRadius = 70.0f;


// Game ticks in a minute at x1 (autosave interval is set in minutes).
constexpr std::uint64_t kTicksPerMinute = 600;

// Blur behind the pause, in pixels at 1080p.
constexpr float kPauseBlur = 3.0f;

// The light of each season (presentation only).
render::Lighting seasonal_lighting(sim::Season season) {
    render::Lighting l;
    switch (season) {
        case sim::Season::Spring: break;
        case sim::Season::Summer:
            l.sun_color = {2.2f, 2.02f, 1.72f};
            break;
        case sim::Season::Autumn:
            l.sun_color = {2.1f, 1.78f, 1.38f};
            l.horizon_color = {0.62f, 0.72f, 0.82f};
            l.sky_ambient = {0.44f, 0.5f, 0.6f};
            break;
        case sim::Season::Winter:
            l.sun_color = {1.65f, 1.72f, 1.85f};
            l.sky_ambient = {0.5f, 0.58f, 0.72f};
            l.zenith_color = {0.22f, 0.42f, 0.72f};
            l.horizon_color = {0.74f, 0.82f, 0.9f};
            break;
        case sim::Season::Count: break;
    }
    return l;
}

// Pixels from the window edge where edge scrolling starts.
constexpr float kEdgeScrollPx = 3.0f;

std::string_view builtin_base_language() {
    return {reinterpret_cast<const char*>(kLangEn), kLangEn_size};
}

// The user's preferred interface languages, for example {"es-MX", "en"}.
std::vector<std::string> preferred_languages() {
    std::vector<std::string> out;
    int count = 0;
    SDL_Locale** locales = SDL_GetPreferredLocales(&count);
    for (int i = 0; locales != nullptr && i < count; ++i) {
        if (locales[i] == nullptr || locales[i]->language == nullptr) {
            continue;
        }
        std::string code = locales[i]->language;
        if (locales[i]->country != nullptr && locales[i]->country[0] != '\0') {
            code += '-';
            code += locales[i]->country;
        }
        if (text::is_valid_language_setting(code)) {
            out.push_back(code);
        }
    }
    SDL_free(locales);
    return out;
}

}  // namespace

App::App(int instance, bool loopback) : text_(atlas_), ui_(text_), instance_(instance), loopback_(loopback) {}

App::~App() = default;

int App::run() {
    if (!init()) {
        shutdown();
        return 1;
    }
    last_frame_ns_ = SDL_GetTicksNS();
    while (running_) {
        frame();
    }
    shutdown();
    return 0;
}

void App::load_languages() {
    const char* base = SDL_GetBasePath();
    const std::filesystem::path lang_dir =
        base != nullptr ? text::path_from_utf8(base) / "data" / "lang" : std::filesystem::path{};
    const int skipped = i18n::translator().load(lang_dir, builtin_base_language());
    if (skipped > 0) {
        log::warn("i18n: {} language file(s) skipped", skipped);
    }
}

void App::fatal_error(const char* text_key) {
    const std::string title = tr("error.fatal.title");
    const std::string body = tr(text_key);
    log::error("fatal: {}", text_key);
    if (!SDL_ShowSimpleMessageBox(SDL_MESSAGEBOX_ERROR, title.c_str(), body.c_str(), window_.sdl())) {
        std::fprintf(stderr, "%s\n", body.c_str());
    }
}

bool App::init() {
    (void)SDL_SetAppMetadata("SalvaCiudad", SC_VERSION_STRING, "io.github.salva.salvaciudad");
    // Texts first, so even early errors can be shown in the player's language.
    load_languages();
    (void)i18n::translator().set_language(i18n::translator().resolve("auto", preferred_languages()));

    if (!SDL_Init(SDL_INIT_VIDEO | SDL_INIT_EVENTS)) {
        std::fprintf(stderr, "SDL_Init failed: %s\n", SDL_GetError());
        fatal_error("error.fatal.sdl");
        return false;
    }
    sdl_ready_ = true;

    paths_ = resolve_data_paths();
    if (!paths_) {
        fatal_error("error.fatal.dataFolder");
        return false;
    }
    if (instance_ > 0) {
        // Its own settings, saves and logs, next to the normal ones.
        paths_->user_dir /= "instance-" + std::to_string(instance_);
        std::error_code ec;
        std::filesystem::create_directories(paths_->user_dir, ec);
        if (ec) {
            fatal_error("error.fatal.dataFolder");
            return false;
        }
    }

    log::Options log_options;
#ifndef NDEBUG
    log_options.echo_to_stderr = true;
    log_options.min_level = log::Level::Debug;
#endif
    if (!log::open(paths_->logs_dir(), log_options)) {
        std::fprintf(stderr, "Cannot open the log file; continuing without it\n");
    }
    log::info("SalvaCiudad {} starting on {}", SC_VERSION_STRING, SDL_GetPlatform());
    log::info("data: {} mode", paths_->portable ? "portable" : "per-user");
    // Log the language files now that the log is open.
    load_languages();

    settings_.emplace(paths_->settings_file());
    const SettingsLoadReport report = settings_->load();
    if (report.created_default && instance_ > 0) {
        // Extra instances start in a small window, side by side.
        DisplaySettings& d = settings_->settings().display;
        d.mode = WindowMode::Windowed;
        d.window_width = 1024;
        d.window_height = 640;
        d.window_x = 40 + (instance_ - 1) % 3 * 60;
        d.window_y = 40 + (instance_ - 1) * 40;
    }
    load_mods();
    apply_language();

    if (!fonts_.load(paths_->game_data_dir() / "fonts")) {
        fatal_error("error.fatal.fonts");
        return false;
    }
    apply_font();

    const DisplaySettings& display = settings_->settings().display;
    if (display.mode != WindowMode::Windowed) {
        last_fullscreen_mode_ = display.mode;
    }
    if (!window_.create(tr("app.name").c_str(), display)) {
        fatal_error("error.fatal.window");
        return false;
    }
    if (!gpu_.create(window_.sdl(), display.vsync) || !ui_renderer_.create(gpu_, kAtlasSize)) {
        fatal_error("error.fatal.gpu");
        return false;
    }

    // The 3D scene is optional: without it the menus still work.
    if (scene_.create(gpu_, settings_->settings().graphics)) {
        const std::filesystem::path models = pack_->dir(mods::kCoreModId) / "models";
        scene_ok_ = test_scene_.load(scene_, models / "props", kTestSceneInstances);
        // Every race's bodies (phase 19), humans first.
        std::vector<std::string> bodies{"human"};
        for (const sim::RaceDef& r : pack_->content.races) {
            if (std::find(bodies.begin(), bodies.end(), r.body) == bodies.end()) {
                bodies.push_back(r.body);
            }
        }
        if (scene_ok_ && crowd_.load(scene_, models / "characters", bodies)) {
            crowd_.spawn(kTestCrowd, 2026, kTestCrowdRadius);
        }
    }
    if (scene_ok_ && !map_scene_.load_models(scene_, *pack_)) {
        log::warn("map: no feature models; maps will show bare ground");
    }
    if (scene_ok_) {
        village_.load(scene_, *pack_);
        village_.set_bodies(&crowd_.bodies(), static_cast<std::uint32_t>(make_villager_palettes().size()));
    }
    if (!scene_ok_) {
        log::warn("scene: 3D view unavailable, menus only");
    }
    reset_camera_to_test_scene();
    if (!debug_.create(window_.sdl(), gpu_)) {
        log::warn("debug overlay unavailable");
    }

    host_ = std::make_unique<UiHost>(*this);
    if (report.quarantined) {
        host_->add_notice(tr("notice.settings.quarantined", text::path_to_utf8(report.quarantine_path.filename())));
    }
    if (report.read_only) {
        host_->add_notice(tr("notice.settings.readOnly"));
    }
    if (report.ignored_fields > 0) {
        host_->add_notice(i18n::tr_n("notice.settings.ignored", report.ignored_fields));
    }
    return true;
}

void App::shutdown() {
    map_job_.cancel();
    close_network();
    if (settings_) {
        save_settings_if_due(true);
    }
    host_.reset();
    if (gpu_.device() != nullptr) {
        (void)SDL_WaitForGPUIdle(gpu_.device());
    }
    debug_.destroy();
    scene_.destroy();
    ui_renderer_.destroy();
    gpu_.destroy();
    window_.destroy();
    if (sdl_ready_) {
        SDL_Quit();
        sdl_ready_ = false;
    }
    log::info("SalvaCiudad stopped");
    log::close();
}

// --- Services ------------------------------------------------------------

void App::settings_changed() {
    if (settings_dirty_since_ns_ == 0) {
        settings_dirty_since_ns_ = SDL_GetTicksNS();
    }
}

bool App::apply_display(const DisplaySettings& display) {
    if (window_.apply(display)) {
        if (display.mode != WindowMode::Windowed) {
            last_fullscreen_mode_ = display.mode;
        }
        return true;
    }
    (void)window_.apply(settings_->settings().display);
    return false;
}

void App::apply_vsync() {
    vsync_pending_ = true;
}

void App::apply_pending_vsync() {
    if (!vsync_pending_) {
        return;
    }
    vsync_pending_ = false;
    bool& vsync = settings_->settings().display.vsync;
    if (!gpu_.set_vsync(vsync)) {
        // Keep the mode that works.
        log::warn("gpu: cannot change vsync; keeping it {}", !vsync ? "on" : "off");
        vsync = !vsync;
        (void)gpu_.set_vsync(vsync);
        settings_changed();
    }
}

void App::apply_graphics() {
    if (scene_ok_) {
        (void)scene_.apply_settings(settings_->settings().graphics);
    }
}

void App::apply_language() {
    auto& t = i18n::translator();
    (void)t.set_language(t.resolve(settings_->settings().language, preferred_languages()));
    if (window_.sdl() != nullptr) {
        (void)SDL_SetWindowTitle(window_.sdl(), tr("app.name").c_str());
    }
}

void App::apply_font() {
    const ui::FontFamily* family = fonts_.ui_family(settings_->settings().ui.font);
    const ui::Font* regular = family != nullptr ? family->regular.get() : nullptr;
    const ui::Font* bold = family != nullptr && family->bold ? family->bold.get() : regular;
    text_.set_font(ui::FontRole::Regular, regular);
    text_.set_font(ui::FontRole::Bold, bold);
    text_.set_font(ui::FontRole::Logo, fonts_.logo());
}

std::vector<std::string> App::monitor_names() {
    std::vector<std::string> names;
    int count = 0;
    SDL_DisplayID* displays = SDL_GetDisplays(&count);
    for (int i = 0; displays != nullptr && i < count; ++i) {
        const char* name = SDL_GetDisplayName(displays[i]);
        if (name != nullptr && text::is_safe_display_text(name, settings_limits::kMaxMonitorNameBytes)) {
            names.emplace_back(name);
        }
    }
    SDL_free(displays);
    return names;
}

std::vector<Resolution> App::fullscreen_resolutions(const std::string& monitor) {
    std::vector<Resolution> list;
    int count = 0;
    SDL_DisplayMode** modes = SDL_GetFullscreenDisplayModes(find_display(monitor), &count);
    for (int i = 0; modes != nullptr && i < count; ++i) {
        const Resolution r{modes[i]->w, modes[i]->h};
        if (r.width >= settings_limits::kMinWindowSize && std::find(list.begin(), list.end(), r) == list.end()) {
            list.push_back(r);
        }
    }
    SDL_free(modes);
    std::sort(list.begin(), list.end(), [](const Resolution& a, const Resolution& b) {
        return a.width != b.width ? a.width > b.width : a.height > b.height;
    });
    return list;
}

void App::open_folder(const std::filesystem::path& dir) {
    std::string url = "file:///" + text::path_to_utf8(dir);
    std::replace(url.begin(), url.end(), '\\', '/');
    if (!SDL_OpenURL(url.c_str())) {
        log::warn("could not open a folder: {}", SDL_GetError());
    }
}

void App::open_data_folder() {
    open_folder(paths_->user_dir);
}

void App::open_mods_folder() {
    open_folder(paths_->user_mods_dir());
}

void App::load_mods() {
    const mods::Version game{SC_VERSION_MAJOR, SC_VERSION_MINOR, SC_VERSION_PATCH};
    mod_library_.scan(paths_->game_data_dir() / "mods", paths_->user_mods_dir(), game);
    mod_library_.select(mods::load_selection(paths_->user_dir / "mods.json").enabled);
    auto pack = std::make_shared<mods::BuildResult>(mod_library_.build());
    auto& t = i18n::translator();
    t.clear_mod_texts();
    for (const std::filesystem::path& file : pack->language_files) {
        const fs::ReadResult r = fs::read_file(file, i18n::catalog_limits::kMaxFileBytes);
        if (r.error == fs::IoError::None) {
            (void)t.add_mod_texts(r.data, text::path_to_utf8(file));
        }
    }
    sound_.load(*pack);
    pack_ = std::move(pack);
}

void App::apply_mods(const std::vector<std::string>& enabled) {
    (void)mods::save_selection(paths_->user_dir / "mods.json", mods::ModSelection{enabled});
    leave_map();
    load_mods();
    apply_language();
    if (scene_ok_) {
        (void)map_scene_.load_models(scene_, *pack_);
        village_.load(scene_, *pack_);
    }
}

// --- Loop ----------------------------------------------------------------

float App::ui_scale() const {
    float dpi = SDL_GetWindowDisplayScale(window_.sdl());
    if (!(dpi > 0.0f)) {
        dpi = 1.0f;
    }
    const double factor = settings_->settings().display.ui_scale;
    return dpi * static_cast<float>(factor > 0.0 ? factor : 1.0);
}

void App::cycle_window_mode() {
    DisplaySettings d = settings_->settings().display;
    d.mode = window_.mode() == WindowMode::Windowed     ? WindowMode::Borderless
             : window_.mode() == WindowMode::Borderless ? WindowMode::Fullscreen
                                                        : WindowMode::Windowed;
    if (apply_display(d)) {
        settings_->settings().display.mode = d.mode;
        settings_changed();
    }
}

void App::handle_event(const SDL_Event& event) {
    const float density = window_.sdl() != nullptr ? SDL_GetWindowPixelDensity(window_.sdl()) : 1.0f;
    debug_.process_event(event);
    switch (event.type) {
        case SDL_EVENT_QUIT:
            running_ = false;
            return;
        case SDL_EVENT_MOUSE_MOTION:
            if (mouse_captured_) {
                // First person: the pointer is hidden; motion turns the view.
                camera_look_dx_ += event.motion.xrel;
                camera_look_dy_ += event.motion.yrel;
                return;
            }
            input_.mouse_x = event.motion.x * density;
            input_.mouse_y = event.motion.y * density;
            if (middle_down_ || right_down_) {
                camera_drag_px_ += event.motion.xrel * density;
                camera_drag_py_ += event.motion.yrel * density;
            }
            return;
        case SDL_EVENT_MOUSE_BUTTON_DOWN:
            if (event.button.button == SDL_BUTTON_MIDDLE) {
                middle_down_ = true;
            }
            if (event.button.button == SDL_BUTTON_RIGHT) {
                right_down_ = true;
                right_press_x_ = input_.mouse_x;
                right_press_y_ = input_.mouse_y;
            }
            if (event.button.button == SDL_BUTTON_LEFT) {
                input_.mouse_down = true;
                input_.mouse_pressed = true;
                press_x_ = input_.mouse_x;
                press_y_ = input_.mouse_y;
            }
            return;
        case SDL_EVENT_MOUSE_BUTTON_UP:
            if (event.button.button == SDL_BUTTON_MIDDLE) {
                middle_down_ = false;
            }
            if (event.button.button == SDL_BUTTON_RIGHT) {
                right_down_ = false;
                right_clicked_ = std::abs(input_.mouse_x - right_press_x_) <= 6.0f &&
                                 std::abs(input_.mouse_y - right_press_y_) <= 6.0f;
            }
            if (event.button.button == SDL_BUTTON_LEFT) {
                input_.mouse_down = false;
                input_.mouse_released = true;
            }
            return;
        case SDL_EVENT_MOUSE_WHEEL:
            input_.wheel += event.wheel.y;
            camera_wheel_ += event.wheel.y;
            return;
        case SDL_EVENT_WINDOW_MOUSE_LEAVE:
            input_.mouse_x = -1.0f;
            input_.mouse_y = -1.0f;
            return;
        case SDL_EVENT_TEXT_INPUT:
            if (event.text.text != nullptr && input_.text.size() < 256) {
                input_.text += event.text.text;
            }
            return;
        case SDL_EVENT_KEY_DOWN: {
            input_.keys.push_back(event.key.scancode);
            if (ui_.typing()) {
                return;  // Typing in a text field: no shortcuts.
            }
            if (event.key.repeat || (host_ && host_->wants_keyboard())) {
                return;
            }
            // Alt+Enter is a fixed system-style shortcut, not rebindable.
            if (event.key.key == SDLK_RETURN && (event.key.mod & SDL_KMOD_ALT) != 0) {
                DisplaySettings d = settings_->settings().display;
                d.mode = window_.mode() == WindowMode::Windowed ? last_fullscreen_mode_ : WindowMode::Windowed;
                if (apply_display(d)) {
                    settings_->settings().display.mode = d.mode;
                    settings_changed();
                }
            } else if (settings_->settings().input.bindings.matches(Action::UiToggleFullscreen, event.key.scancode)) {
                cycle_window_mode();
            } else if (event.key.scancode == SDL_SCANCODE_F3 && (event.key.mod & SDL_KMOD_CTRL) != 0) {
                // Developer tools: a fixed shortcut, like Alt+Enter.
                dev_tools_.toggle();
            } else if (settings_->settings().input.bindings.matches(Action::UiDebugOverlay, event.key.scancode)) {
                debug_.toggle();
            } else if (settings_->settings().input.bindings.matches(Action::CameraCycleMode, event.key.scancode) &&
                       host_ && interactive_scene()) {
                camera_.set_mode(next_camera_mode(camera_.mode()));
            }
            return;
        }
        default:
            break;
    }
    if (event.type >= SDL_EVENT_WINDOW_FIRST && event.type <= SDL_EVENT_WINDOW_LAST) {
        if (window_.track_event(event, settings_->settings().display)) {
            settings_changed();
        }
    }
}

void App::save_settings_if_due(bool force) {
    if (settings_dirty_since_ns_ == 0) {
        return;
    }
    if (!force && SDL_GetTicksNS() - settings_dirty_since_ns_ < kSettingsSaveDelayNs) {
        return;
    }
    settings_dirty_since_ns_ = 0;
    (void)settings_->save();
}

void App::update_camera(float dt) {
    const UiHost::SceneMode mode = host_->scene_mode();
    CameraInput in;
    if (interactive_scene()) {
        const InputSettings& s = settings_->settings().input;
        const bool* keys = SDL_GetKeyboardState(nullptr);
        const auto held = [&](Action a) {
            for (std::size_t slot = 0; slot < kKeysPerAction; ++slot) {
                const SDL_Scancode k = s.bindings.key(a, slot);
                if (k != SDL_SCANCODE_UNKNOWN && keys != nullptr && keys[k]) {
                    return true;
                }
            }
            return false;
        };
        // Keys typed into a developer tool's text field do not move the camera.
        const bool focused = (SDL_GetWindowFlags(window_.sdl()) & SDL_WINDOW_INPUT_FOCUS) != 0 &&
                             !debug_.wants_keyboard();
        if (focused) {
            in.move_forward = (held(Action::CameraForward) ? 1.0f : 0.0f) - (held(Action::CameraBack) ? 1.0f : 0.0f);
            in.move_right = (held(Action::CameraRight) ? 1.0f : 0.0f) - (held(Action::CameraLeft) ? 1.0f : 0.0f);
            in.rotate = (held(Action::CameraRotateRight) ? 1.0f : 0.0f) - (held(Action::CameraRotateLeft) ? 1.0f : 0.0f);
            float zoom_keys = (held(Action::CameraZoomIn) ? 1.0f : 0.0f) - (held(Action::CameraZoomOut) ? 1.0f : 0.0f);
            in.zoom_steps = (camera_wheel_ + zoom_keys * dt * 8.0f) * (s.invert_zoom ? -1.0f : 1.0f);
            const CameraMode cam = camera_.mode();
            if (cam == CameraMode::FirstPerson) {
                in.look_dx = camera_look_dx_;
                in.look_dy = camera_look_dy_;
            } else {
                in.drag_rotate_px = camera_drag_px_;
                if (cam == CameraMode::ThirdPerson) {
                    in.drag_pitch_px = camera_drag_py_;
                }
            }
            // Edge scrolling (aerial view only), while the pointer is inside the window.
            int w = 0;
            int h = 0;
            SDL_GetWindowSizeInPixels(window_.sdl(), &w, &h);
            const float mx = input_.mouse_x;
            const float my = input_.mouse_y;
            if (cam == CameraMode::Aerial && s.edge_scroll && mx >= 0.0f && my >= 0.0f && !middle_down_ &&
                !right_down_) {
                if (mx <= kEdgeScrollPx) in.move_right -= 1.0f;
                if (mx >= static_cast<float>(w) - 1.0f - kEdgeScrollPx) in.move_right += 1.0f;
                if (my <= kEdgeScrollPx) in.move_forward += 1.0f;
                if (my >= static_cast<float>(h) - 1.0f - kEdgeScrollPx) in.move_forward -= 1.0f;
            }
            in.move_forward = std::clamp(in.move_forward, -1.0f, 1.0f);
            in.move_right = std::clamp(in.move_right, -1.0f, 1.0f);
        }
        // Moving stops following the selected villager; turning does not.
        if (following_ && (in.move_forward != 0.0f || in.move_right != 0.0f)) {
            following_ = false;
        }
    } else if (mode == UiHost::SceneMode::MenuBackground) {
        in.rotate = 0.025f;  // A slow turn behind the menus.
    }
    camera_wheel_ = 0.0f;
    camera_drag_px_ = 0.0f;
    camera_drag_py_ = 0.0f;
    camera_look_dx_ = 0.0f;
    camera_look_dy_ = 0.0f;
    const bool walkers = mode == UiHost::SceneMode::TestScene || mode == UiHost::SceneMode::Map;
    const bool follow = following_ && selected_ && walkers;
    if (!walkers) {
        following_ = false;
        selected_.reset();
    }
    if (follow) {
        camera_.set_follow(crowd_.position(*selected_), crowd_.scale(*selected_));
    } else {
        camera_.set_follow(std::nullopt);
    }
    // In first person, the followed villager is where the eyes are.
    crowd_.set_hidden(follow && camera_.mode() == CameraMode::FirstPerson ? selected_ : std::nullopt);
    // Debug stress view: the whole test scene on screen at once.
    const bool stress = mode == UiHost::SceneMode::TestScene && debug_.stress_view();
    if (stress != stress_view_active_) {
        stress_view_active_ = stress;
        camera_.set_max_distance_override(stress ? 2600.0f : 0.0f);
        camera_.set_distance(stress ? 2600.0f : 120.0f);
    }
    const InputSettings& s = settings_->settings().input;
    const CameraSpeeds speeds{static_cast<float>(s.camera_pan_speed), static_cast<float>(s.camera_rotate_speed),
                              static_cast<float>(s.camera_zoom_speed)};
    camera_.update(in, interactive_scene() ? speeds : CameraSpeeds{}, dt);
}

void App::update_frame_stats(float dt) {
    debug_info_.frame_ms = dt * 1000.0f;
    fps_window_s_ += dt;
    ++fps_window_frames_;
    if (fps_window_s_ >= 0.5f) {
        debug_info_.fps = static_cast<float>(fps_window_frames_) / fps_window_s_;
        fps_window_s_ = 0.0f;
        fps_window_frames_ = 0;
    }
    // In the test scene, log the average every few seconds so performance
    // can be checked without watching the screen.
    if (interactive_scene()) {
        perf_log_s_ += dt;
        ++perf_log_frames_;
        if (perf_log_s_ >= 5.0f) {
            const render::RenderStats& st = scene_.stats();
            log::info("perf: {:.1f} FPS average, {} of {} instances drawn, {} draw calls, {:.2f} M triangles, "
                      "cull {:.2f} ms, {} terrain chunks, {} water chunks",
                      static_cast<float>(perf_log_frames_) / perf_log_s_, st.instances_drawn, st.instances_total,
                      st.draw_calls, static_cast<double>(st.triangles) / 1e6, st.cull_ms, st.terrain_chunks,
                      st.water_chunks);
            perf_log_s_ = 0.0f;
            perf_log_frames_ = 0;
        }
    } else {
        perf_log_s_ = 0.0f;
        perf_log_frames_ = 0;
    }
}

void App::render_frame(float dt) {
    GpuFrame frame;
    if (!gpu_.begin_frame(frame)) {
        return;
    }
    if (frame.target != nullptr) {
        // 3D scene first, straight into the swapchain.
        bool scene_drawn = false;
        update_mouse_capture();
        if (scene_ok_ && host_->scene_mode() != UiHost::SceneMode::None) {
            handle_scene_click(frame.width, frame.height);
            update_camera(dt);
            if (session_ && host_->scene_mode() == UiHost::SceneMode::Map) {
                // The season: trees, hats and light.
                const sim::Game& g = session_->game();
                const sim::Season season = g.calendar().season;
                map_scene_.set_season(scene_, g.map(), g.content(), season, g.snow() > 25);
                map_scene_.update_sky(scene_, dt * static_cast<float>(host_->game_paused() ? 0 : 1));
                village_.set_season(season);
                lighting_ = seasonal_lighting(season);
                update_placement(frame.width, frame.height);
                const int speed = host_->game_paused() ? 0 : clock_.speed();
                village_.set_view(camera_.target().x, camera_.target().z, session_->town());
                village_.update(scene_, map_scene_, session_->game(), static_cast<float>(clock_.interpolation()), dt,
                                speed);
            } else {
                crowd_.update(scene_, dt);
            }
            render::SceneView view;
            view.view = camera_.view();
            view.eye = camera_.eye();
            view.fov_y = math::radians(Camera::kFovY);
            view.near_z = camera_.near_z();
            view.aspect = static_cast<float>(frame.width) / static_cast<float>(std::max(1u, frame.height));
            view.draw_distance_override = stress_view_active_ ? 5000.0f : 0.0f;
            // Zoomed out past the normal limit over a map: the whole ground
            // stays visible (temporary, decision D-615).
            if (map_ && host_->scene_mode() == UiHost::SceneMode::Map && camera_.distance() > Camera::kMaxDistance) {
                view.terrain_distance = camera_.distance() * 2.5f + static_cast<float>(map_->map.size);
            }
            view.time = static_cast<float>(static_cast<double>(SDL_GetTicksNS() % 3'600'000'000'000ull) * 1e-9);
            if (session_ && host_->game_paused() && host_->scene_mode() == UiHost::SceneMode::Map) {
                view.blur = kPauseBlur;
            }
            if (session_ && host_->scene_mode() == UiHost::SceneMode::Map) {
                view.snow = static_cast<float>(session_->game().snow()) / static_cast<float>(sim::village::kMaxSnow);
                // The water freezes over below -3 °C, as fishing stops (sim).
                const float t = static_cast<float>(session_->game().temperature());
                view.ice = t <= -3.0f ? std::min(1.0f, (-t - 2.0f) / 3.0f) : 0.0f;
            }
            scene_drawn = scene_.render(frame, view, lighting_);
        }

        // Interface on top.
        const Settings& s = settings_->settings();
        ui_.set_tooltips(s.ui.show_tooltips, s.ui.tooltip_delay_ms);
        ui_.begin_frame(input_, static_cast<float>(frame.width), static_cast<float>(frame.height), ui_scale(),
                        SDL_GetTicksNS(), atlas_.white_u(), atlas_.white_v());
        // The developer tools pick and place in the world before drawing.
        DevContext dev = dev_context(frame.width, frame.height);
        dev_tools_.update(dev);
        if (debug_.wants_keyboard()) {
            input_.keys.clear();  // Typing in a tool, not in the game.
        }
        // Markers belong to the 3D view, under the interface.
        if (scene_drawn && host_->scene_mode() == UiHost::SceneMode::Map && !session_) {
            draw_start_markers(frame.width, frame.height);
        }
        if (scene_drawn && session_ && host_->scene_mode() == UiHost::SceneMode::Map) {
            // A marker over the selected villager or building.
            const sim::Game& g = session_->game();
            const GameSession::Interaction& sel = session_->ui();
            if (const sim::Villager* v = g.villagers().get(sel.selected_villager)) {
                const math::Vec3 p = village_.villager_position(g, *v, static_cast<float>(clock_.interpolation()));
                draw_marker(frame.width, frame.height, p + math::Vec3{0.0f, 2.3f, 0.0f}, ui_.theme().accent);
            } else if (const sim::Building* b = g.buildings().get(sel.selected_building)) {
                draw_marker(frame.width, frame.height, village_.building_top(g, *b), ui_.theme().accent);
            }
        }
        if (scene_drawn && (host_->scene_mode() == UiHost::SceneMode::TestScene ||
                            host_->scene_mode() == UiHost::SceneMode::Map)) {
            draw_scene_markers(frame.width, frame.height);
        }
        if (scene_drawn) {
            if (const auto m = dev_tools_.hovered_marker(dev)) {
                draw_marker(frame.width, frame.height, *m, ui_.theme().text);
            }
            if (const auto m = dev_tools_.selected_marker(dev)) {
                draw_marker(frame.width, frame.height, *m, ui_.theme().danger);
            }
        }
        host_->frame(ui_);
        ui_.end_frame();

        debug_info_.backend = gpu_.driver_name();
        debug_info_.width = frame.width;
        debug_info_.height = frame.height;
        debug_info_.ui_scale = ui_scale();
        debug_info_.scene_drawn = scene_drawn;
        debug_info_.scene = scene_.stats();
        debug_info_.camera_distance = camera_.distance();
        debug_info_.camera_x = camera_.target().x;
        debug_info_.camera_z = camera_.target().z;
        if (session_) {
            const sim::Game& g = session_->game();
            debug_info_.sim_tick = g.tick();
            // The full hash serializes the game: only now and then.
            if (debug_.visible() && g.tick() % 50 == 0) {
                debug_info_.sim_hash = g.hash();
            }
            debug_info_.sim_entities = g.registry().alive_count();
        } else {
            debug_info_.sim_tick = sim_.tick();
            debug_info_.sim_hash = sim_.last_hash();
            debug_info_.sim_entities = sim_.world().registry().alive_count();
        }
        debug_.build(debug_info_, [&] { dev_tools_.draw(dev); }, dev_tools_.visible());

        const bool uploaded = ui_renderer_.upload(frame.cmd, ui_.draw(), atlas_);
        debug_.prepare(frame.cmd);
        SDL_GPUColorTargetInfo target{};
        target.texture = frame.target;
        const ui::Color bg = ui_.theme().background;
        target.clear_color = SDL_FColor{static_cast<float>(bg.r) / 255.0f, static_cast<float>(bg.g) / 255.0f,
                                        static_cast<float>(bg.b) / 255.0f, 1.0f};
        target.load_op = scene_drawn ? SDL_GPU_LOADOP_LOAD : SDL_GPU_LOADOP_CLEAR;
        target.store_op = SDL_GPU_STOREOP_STORE;
        SDL_GPURenderPass* pass = SDL_BeginGPURenderPass(frame.cmd, &target, 1, nullptr);
        if (pass != nullptr) {
            if (uploaded) {
                ui_renderer_.draw(frame.cmd, pass, ui_.draw());
            }
            debug_.render(frame.cmd, pass);
            SDL_EndGPURenderPass(pass);
        }
    }
    (void)gpu_.end_frame(frame);
}

void App::frame() {
    input_.mouse_pressed = false;
    input_.mouse_released = false;
    right_clicked_ = false;
    input_.wheel = 0.0f;
    input_.keys.clear();
    input_.text.clear();
    // Text arrives only while a field has the keyboard.
    if (window_.sdl() != nullptr && ui_.typing() != SDL_TextInputActive(window_.sdl())) {
        if (ui_.typing()) {
            (void)SDL_StartTextInput(window_.sdl());
        } else {
            (void)SDL_StopTextInput(window_.sdl());
        }
    }

    SDL_Event event;
    if (window_.minimized()) {
        if (SDL_WaitEventTimeout(&event, kMinimizedWaitMs)) {
            handle_event(event);
        }
    }
    while (SDL_PollEvent(&event)) {
        handle_event(event);
    }

    const std::uint64_t now = SDL_GetTicksNS();
    const std::uint64_t elapsed = now - last_frame_ns_;
    last_frame_ns_ = now;

    update_network(now / 1'000'000ull);
    if (net_ && session_ && session_->networked()) {
        clock_.set_speed(net_->speed());
    }
    const int ticks = clock_.advance(static_cast<std::int64_t>(elapsed));
    if (net_ && session_ && session_->networked()) {
        (void)net_->advance(ticks, now / 1'000'000ull);
        autosave_if_due();
    } else if (session_) {
        // A menu over a single-player game stops it.
        if (host_ && !host_->game_paused()) {
            for (int i = 0; i < ticks; ++i) {
                session_->step();
            }
            autosave_if_due();
        }
    } else {
        for (int i = 0; i < ticks; ++i) {
            sim_.step();
        }
    }

    if (session_ && host_) {
        report_game_events();
    }
    const float dt = static_cast<float>(elapsed) * 1e-9f;
    update_frame_stats(dt);
    update_sound(dt);
    if (!window_.minimized()) {
        render_frame(dt);
    }
    apply_pending_vsync();
    save_settings_if_due(false);

    const DisplaySettings& display = settings_->settings().display;
    if (display.fps_limit > 0 && !display.vsync) {
        const std::uint64_t budget = 1'000'000'000ull / static_cast<std::uint64_t>(display.fps_limit);
        const std::uint64_t spent = SDL_GetTicksNS() - now;
        if (spent < budget) {
            SDL_DelayPrecise(budget - spent);
        }
    }
}

}  // namespace sc

namespace sc {

bool App::interactive_scene() const {
    if (!host_) {
        return false;
    }
    const UiHost::SceneMode mode = host_->scene_mode();
    return (mode == UiHost::SceneMode::TestScene || mode == UiHost::SceneMode::Map) && !host_->scene_paused();
}

void App::reset_camera_to_test_scene() {
    camera_.set_ground({});
    camera_.set_max_distance_override(0.0f);
    camera_.set_mode(CameraMode::Aerial);
    camera_.set_bounds(-kTestSceneHalfSize, -kTestSceneHalfSize, kTestSceneHalfSize, kTestSceneHalfSize);
    camera_.set_target({0.0f, 0.0f, 0.0f});
    camera_.set_yaw(0.6f);
    camera_.set_distance(80.0f);
    camera_.snap();
}

void App::start_map_generation(const sim::MapSettings& settings, const sim::GameRules& rules) {
    pending_rules_ = rules;
    log::info("map: generating seed {} size {} with {} start(s)", settings.seed, sim::map_cells(settings.size),
              settings.players);
    map_job_.start(settings, pack_);
}

bool App::enter_generated_map() {
    std::unique_ptr<GeneratedMap> generated = map_job_.take();
    if (!generated || !scene_ok_) {
        return false;
    }
    leave_map();
    dev_tools_.reset();
    test_scene_.set_visible(scene_, false);
    if (!map_scene_.show(scene_, generated->visuals)) {
        test_scene_.set_visible(scene_, true);
        return false;
    }
    if (!generated->script_errors.empty() && host_) {
        std::string body = tr("mods.scriptErrors.body");
        for (const std::string& e : generated->script_errors) {
            body += "\n- " + e.substr(0, 300);
        }
        host_->show_message(tr("mods.scriptErrors.title"), body);
    }
    // The renderer keeps its own copy; free this one.
    generated->visuals = MapVisuals{};
    map_ = std::move(generated);
    const sim::MapData* map = &map_->map;
    const float size = static_cast<float>(map->size);
    camera_.set_mode(CameraMode::Aerial);
    camera_.set_ground([map](float x, float z) { return map_surface_height(*map, x, z); });
    camera_.set_bounds(0.0f, 0.0f, size, size);
    // For now the camera can back off until the whole map fits (D-615).
    camera_.set_max_distance_override(size * 1.6f);
    const float sx = map->starts.empty() ? size * 0.5f : static_cast<float>(map->starts[0].x.raw()) / 65536.0f;
    const float sz = map->starts.empty() ? size * 0.5f : static_cast<float>(map->starts[0].z.raw()) / 65536.0f;
    camera_.set_target({sx, map_surface_height(*map, sx, sz), sz});
    camera_.set_yaw(0.6f);
    camera_.set_distance(110.0f);
    camera_.snap();
    map_scene_.show_sky(scene_, *map);
    selected_.reset();
    following_ = false;
    // A village game on it (phase 8); its own stream of random numbers.
    const std::shared_ptr<const sim::Content> content(pack_, &pack_->content);
    if (net_start_ && net_) {
        const net::Start st = *net_start_;
        net_start_.reset();
        auto session = std::make_unique<GameSession>(
            content, *map, sim::GameSetup{st.players, st.config.seed, st.config.shared_town, st.config.rules},
            net_->local_slot());
        session->attach(net_.get());
        session->game().set_dev_commands(false);  // Not in network games (decision D-910).
        start_session(std::move(session));
        net_->game_built(&session_->game(), net::map_hash(*map));
        return true;
    }
    start_session(std::make_unique<GameSession>(
        content, *map, sim::GameSetup{1, map->settings.seed ^ 0x5A17C1DAull, false, pending_rules_}));
    return true;
}

void App::leave_map() {
    if (!map_) {
        return;
    }
    dev_tools_.reset();
    village_.end(scene_);
    session_.reset();
    lighting_ = render::Lighting{};
    clock_.set_speed(1);
    map_scene_.hide(scene_);
    test_scene_.set_visible(scene_, true);
    crowd_.set_area({}, {});
    crowd_.spawn(kTestCrowd, 2026, kTestCrowdRadius);
    selected_.reset();
    following_ = false;
    reset_camera_to_test_scene();
    map_.reset();
}

DevContext App::dev_context(std::uint32_t width, std::uint32_t height) {
    DevContext ctx;
    if (!dev_tools_.visible() || !scene_ok_ || !host_ || !interactive_scene()) {
        return ctx;
    }
    const bool on_map = host_->scene_mode() == UiHost::SceneMode::Map && map_;
    ctx.map = on_map ? &map_->map : nullptr;
    ctx.content = pack_ ? &pack_->content : nullptr;
    ctx.scene = on_map ? &map_scene_ : nullptr;
    ctx.renderer = &scene_;
    ctx.crowd = &crowd_;
    ctx.camera = &camera_;
    ctx.session = on_map ? session_.get() : nullptr;
    const float x = input_.mouse_x;
    const float y = input_.mouse_y;
    if (x >= 0.0f && y >= 0.0f && !debug_.wants_mouse() && !mouse_captured_) {
        const math::Mat4 inv = math::inverse(camera_view_proj(width, height));
        const float nx = x / static_cast<float>(width) * 2.0f - 1.0f;
        const float ny = 1.0f - y / static_cast<float>(height) * 2.0f;
        const math::Vec3 near_point = inv.transform_point({nx, ny, 1.0f});
        const math::Vec3 far_point = inv.transform_point({nx, ny, 0.01f});
        ctx.ray_valid = true;
        ctx.ray_origin = near_point;
        ctx.ray_dir = math::normalize(far_point - near_point);
        // A click, not the end of a drag.
        ctx.clicked = input_.mouse_released && std::abs(x - press_x_) <= 6.0f && std::abs(y - press_y_) <= 6.0f;
    }
    return ctx;
}

void App::draw_marker(std::uint32_t width, std::uint32_t height, math::Vec3 at, ui::Color color) {
    const math::Vec4 clip = camera_view_proj(width, height) * math::Vec4{at.x, at.y, at.z, 1.0f};
    if (clip.w <= 0.01f) {
        return;
    }
    const float sx = (clip.x / clip.w * 0.5f + 0.5f) * static_cast<float>(width);
    const float sy = (0.5f - clip.y / clip.w * 0.5f) * static_cast<float>(height);
    const float r = ui_.s(10.0f);
    ui::DrawList& dl = ui_.draw();
    dl.triangle(sx - r - 2, sy - r * 1.6f - 2, sx + r + 2, sy - r * 1.6f - 2, sx, sy + 2, ui::Color::rgb(0x000000, 150));
    dl.triangle(sx - r, sy - r * 1.6f, sx + r, sy - r * 1.6f, sx, sy, color);
}

void App::draw_start_markers(std::uint32_t width, std::uint32_t height) {
    if (!map_) {
        return;
    }
    ui::DrawList& dl = ui_.draw();
    const math::Mat4 view_proj = camera_view_proj(width, height);
    const ui::TextStyle st = ui_.style(ui_.theme().body, ui::FontRole::Bold);
    const float r = ui_.s(13.0f);
    for (std::size_t i = 0; i < map_->map.starts.size(); ++i) {
        const sim::StartPosition& s = map_->map.starts[i];
        const float x = static_cast<float>(s.x.raw()) / 65536.0f;
        const float z = static_cast<float>(s.z.raw()) / 65536.0f;
        const math::Vec3 p{x, map_surface_height(map_->map, x, z) + 6.0f, z};
        const math::Vec4 clip = view_proj * math::Vec4{p.x, p.y, p.z, 1.0f};
        if (clip.w <= 0.01f) {
            continue;
        }
        const float sx = std::round((clip.x / clip.w * 0.5f + 0.5f) * static_cast<float>(width));
        const float sy = std::round((0.5f - clip.y / clip.w * 0.5f) * static_cast<float>(height));
        if (sx < -r || sy < -r || sx > static_cast<float>(width) + r || sy > static_cast<float>(height) + r) {
            continue;
        }
        // A numbered banner with a pointer down to the spot.
        dl.triangle(sx - r * 0.6f, sy + r - 1, sx + r * 0.6f, sy + r - 1, sx, sy + r * 1.8f, ui_.theme().accent);
        dl.rect({sx - r - 2, sy - r - 2, 2 * r + 4, 2 * r + 4}, ui::Color::rgb(0x000000, 150));
        dl.rect({sx - r, sy - r, 2 * r, 2 * r}, ui_.theme().accent);
        const std::string number = std::to_string(i + 1);
        const float tw = ui_.text().measure(st, number);
        const float th = ui_.text().line_height(st);
        ui_.text().draw(dl, st, std::round(sx - tw * 0.5f), std::round(sy - th * 0.5f), number,
                        ui::Color::rgb(0x1E1A14));
    }
}

math::Mat4 App::camera_view_proj(std::uint32_t width, std::uint32_t height) const {
    const float aspect = static_cast<float>(width) / static_cast<float>(std::max(1u, height));
    // The far plane does not change where things land on screen.
    return camera_.projection(aspect, 1000.0f) * camera_.view();
}

void App::update_mouse_capture() {
    // First person in the test scene looks around with a captured pointer,
    // unless the statistics window needs it.
    const bool focused = window_.sdl() != nullptr && (SDL_GetWindowFlags(window_.sdl()) & SDL_WINDOW_INPUT_FOCUS) != 0;
    const bool want = scene_ok_ && host_ && interactive_scene() && camera_.mode() == CameraMode::FirstPerson &&
                      focused && !debug_.visible() && !dev_tools_.visible();
    if (want != mouse_captured_) {
        if (SDL_SetWindowRelativeMouseMode(window_.sdl(), want)) {
            mouse_captured_ = want;
        } else {
            log::warn("cannot change the mouse capture: {}", SDL_GetError());
        }
        camera_look_dx_ = 0.0f;
        camera_look_dy_ = 0.0f;
    }
}

void App::handle_scene_click(std::uint32_t width, std::uint32_t height) {
    if (!interactive_scene() || !input_.mouse_released || debug_.wants_mouse() || dev_tools_.visible()) {
        return;
    }
    // A click, not the end of a drag.
    float x = input_.mouse_x;
    float y = input_.mouse_y;
    if (mouse_captured_) {
        x = static_cast<float>(width) * 0.5f;  // First person aims with the center.
        y = static_cast<float>(height) * 0.5f;
    } else if (std::abs(x - press_x_) > 6.0f || std::abs(y - press_y_) > 6.0f || x < 0.0f) {
        return;
    }
    const math::Mat4 inv = math::inverse(camera_view_proj(width, height));
    const float nx = x / static_cast<float>(width) * 2.0f - 1.0f;
    const float ny = 1.0f - y / static_cast<float>(height) * 2.0f;
    const math::Vec3 near_point = inv.transform_point({nx, ny, 1.0f});
    const math::Vec3 far_point = inv.transform_point({nx, ny, 0.01f});
    if (session_ && host_->scene_mode() == UiHost::SceneMode::Map) {
        handle_game_click(width, height, near_point, math::normalize(far_point - near_point));
        return;
    }
    const std::optional<std::size_t> hit = crowd_.pick(near_point, far_point - near_point);
    // In first person while following, the viewer's own body cannot be picked.
    if (hit && !(following_ && camera_.mode() == CameraMode::FirstPerson && hit == selected_)) {
        selected_ = hit;
        following_ = true;
    } else if (!hit) {
        selected_.reset();
        following_ = false;
    }
}

void App::draw_scene_markers(std::uint32_t width, std::uint32_t height) {
    ui::DrawList& dl = ui_.draw();
    const ui::Color accent = ui_.theme().accent;
    if (camera_.mode() == CameraMode::FirstPerson) {
        // A small cross in the middle of the screen.
        const float cx = std::round(static_cast<float>(width) * 0.5f);
        const float cy = std::round(static_cast<float>(height) * 0.5f);
        const float len = std::round(ui_.s(8.0f));
        const float th = std::max(2.0f, std::round(ui_.s(2.0f)));
        const ui::Color shadow = ui::Color::rgb(0x000000, 140);
        dl.rect({cx - len - 1, cy - th / 2 - 1, 2 * len + 2, th + 2}, shadow);
        dl.rect({cx - th / 2 - 1, cy - len - 1, th + 2, 2 * len + 2}, shadow);
        dl.rect({cx - len, cy - th / 2, 2 * len, th}, ui_.theme().text);
        dl.rect({cx - th / 2, cy - len, th, 2 * len}, ui_.theme().text);
    }
    if (!selected_ || (following_ && camera_.mode() == CameraMode::FirstPerson)) {
        return;
    }
    // A marker pointing down at the selected villager's head.
    const math::Vec3 head = crowd_.position(*selected_) + math::Vec3{0.0f, 2.15f * crowd_.scale(*selected_), 0.0f};
    const math::Vec4 clip = camera_view_proj(width, height) * math::Vec4{head.x, head.y, head.z, 1.0f};
    if (clip.w <= 0.01f) {
        return;
    }
    const float sx = (clip.x / clip.w * 0.5f + 0.5f) * static_cast<float>(width);
    const float sy = (0.5f - clip.y / clip.w * 0.5f) * static_cast<float>(height);
    const float r = ui_.s(11.0f);
    dl.triangle(sx - r - 2, sy - r * 1.6f - 2, sx + r + 2, sy - r * 1.6f - 2, sx, sy + 2, ui::Color::rgb(0x000000, 150));
    dl.triangle(sx - r, sy - r * 1.6f, sx + r, sy - r * 1.6f, sx, sy, following_ ? accent : ui_.theme().text);
}

}  // namespace sc

namespace sc {

bool App::mouse_ray(std::uint32_t width, std::uint32_t height, math::Vec3& origin, math::Vec3& dir) const {
    const float x = input_.mouse_x;
    const float y = input_.mouse_y;
    if (x < 0.0f || y < 0.0f || mouse_captured_) {
        return false;
    }
    const math::Mat4 inv = math::inverse(camera_view_proj(width, height));
    const float nx = x / static_cast<float>(width) * 2.0f - 1.0f;
    const float ny = 1.0f - y / static_cast<float>(height) * 2.0f;
    origin = inv.transform_point({nx, ny, 1.0f});
    dir = math::normalize(inv.transform_point({nx, ny, 0.01f}) - origin);
    return true;
}

void App::update_placement(std::uint32_t width, std::uint32_t height) {
    GameSession::Interaction& ui = session_->ui();
    const sim::Game& game = session_->game();
    ui.hover_valid = false;
    if (right_clicked_ && ui.placing != sim::kNoDef) {
        ui.placing = sim::kNoDef;  // Right click cancels.
    }
    math::Vec3 origin;
    math::Vec3 dir;
    // Marking out a field: press on a corner, drag, release.
    if (ui.field_farm.valid()) {
        village_.set_ghost(std::nullopt);
        if (right_clicked_ || game.buildings().get(ui.field_farm) == nullptr) {
            ui.field_farm = {};
            ui.field_dragging = false;
            village_.set_field_ghost(std::nullopt);
            return;
        }
        std::optional<math::Vec3> hit;
        if (interactive_scene() && mouse_ray(width, height, origin, dir) && !ui.over_hud(input_.mouse_x, input_.mouse_y)) {
            hit = ground_hit(game.map(), origin, dir);
        }
        if (!hit) {
            if (!ui.field_dragging) {
                village_.set_field_ghost(std::nullopt);
            }
            return;
        }
        const auto cx = static_cast<std::int32_t>(std::floor(hit->x));
        const auto cz = static_cast<std::int32_t>(std::floor(hit->z));
        if (input_.mouse_pressed) {
            ui.field_dragging = true;
            ui.drag_x = cx;
            ui.drag_z = cz;
        }
        // The rectangle between the corner and the cursor (a small square
        // before dragging), limited to the allowed sizes.
        std::int32_t x0 = ui.field_dragging ? std::min(ui.drag_x, cx) : cx;
        std::int32_t z0 = ui.field_dragging ? std::min(ui.drag_z, cz) : cz;
        std::int32_t w = ui.field_dragging ? std::abs(cx - ui.drag_x) + 1 : sim::kMinFieldSide;
        std::int32_t d = ui.field_dragging ? std::abs(cz - ui.drag_z) + 1 : sim::kMinFieldSide;
        w = std::clamp(w, sim::kMinFieldSide, sim::kMaxFieldSide);
        d = std::clamp(d, sim::kMinFieldSide, sim::kMaxFieldSide);
        if (ui.field_dragging && cx < ui.drag_x) {
            x0 = ui.drag_x - w + 1;
        }
        if (ui.field_dragging && cz < ui.drag_z) {
            z0 = ui.drag_z - d + 1;
        }
        ui.hover_valid = true;
        ui.hover_error = game.can_place_field(session_->local_player(), ui.field_farm, x0, z0, w, d);
        village_.set_field_ghost(VillageView::FieldGhost{x0, z0, w, d, ui.hover_error == sim::PlaceError::None});
        if (ui.field_dragging && input_.mouse_released) {
            ui.field_dragging = false;
            if (ui.hover_error == sim::PlaceError::None) {
                sim::Command c;
                c.type = sim::CommandType::PlaceField;
                c.entity = ui.field_farm;
                c.position = {sim::Fixed::from_int(x0), sim::Fixed::from_int(z0)};
                c.value = w | (d << 8);
                session_->issue(c);
                if ((SDL_GetModState() & SDL_KMOD_SHIFT) == 0) {
                    ui.field_farm = {};
                    village_.set_field_ghost(std::nullopt);
                }
            }
        }
        return;
    }
    village_.set_field_ghost(std::nullopt);
    if (ui.placing == sim::kNoDef || ui.placing >= game.content().buildings.size() || !interactive_scene() ||
        !mouse_ray(width, height, origin, dir) || ui.over_hud(input_.mouse_x, input_.mouse_y)) {
        village_.set_ghost(std::nullopt);
        return;
    }
    const std::optional<math::Vec3> hit = ground_hit(game.map(), origin, dir);
    if (!hit) {
        village_.set_ghost(std::nullopt);
        return;
    }
    std::int32_t w = 0;
    std::int32_t d = 0;
    sim::Game::footprint(game.content().buildings[ui.placing], ui.rotation, w, d);
    ui.hover_valid = true;
    ui.hover_x = static_cast<std::int32_t>(std::lround(hit->x - static_cast<float>(w) * 0.5f));
    ui.hover_z = static_cast<std::int32_t>(std::lround(hit->z - static_cast<float>(d) * 0.5f));
    ui.hover_error = game.can_place(session_->town(), ui.placing, ui.hover_x, ui.hover_z, ui.rotation);
    // Walls go in lines: press at one end, release at the other.
    const sim::BuildingDef& pd = game.content().buildings[ui.placing];
    if (pd.kind == sim::BuildingKind::Defense && !pd.trap && w == 2 && d == 2) {
        if (input_.mouse_pressed) {
            ui.line_dragging = true;
            ui.drag_x = ui.hover_x;
            ui.drag_z = ui.hover_z;
        }
        if (ui.line_dragging) {
            // Along the longer side, every 2 m.
            const bool along_x = std::abs(ui.hover_x - ui.drag_x) >= std::abs(ui.hover_z - ui.drag_z);
            const std::int32_t end_x = along_x ? ui.hover_x : ui.drag_x;
            const std::int32_t end_z = along_x ? ui.drag_z : ui.hover_z;
            ui.hover_x = end_x;
            ui.hover_z = end_z;
            ui.hover_error = game.can_place(session_->town(), ui.placing, end_x, end_z, ui.rotation);
            if (input_.mouse_released) {
                ui.line_dragging = false;
                const std::int32_t steps = std::max(std::abs(end_x - ui.drag_x), std::abs(end_z - ui.drag_z)) / 2;
                for (std::int32_t k = 0; k <= std::min(steps, 100); ++k) {
                    const std::int32_t x = ui.drag_x + (along_x ? (end_x > ui.drag_x ? 2 * k : -2 * k) : 0);
                    const std::int32_t z = ui.drag_z + (along_x ? 0 : (end_z > ui.drag_z ? 2 * k : -2 * k));
                    if (game.can_place(session_->town(), ui.placing, x, z, 0) != sim::PlaceError::None) {
                        continue;
                    }
                    sim::Command c;
                    c.type = sim::CommandType::PlaceBuilding;
                    c.def = ui.placing;
                    c.position = {sim::Fixed::from_int(x), sim::Fixed::from_int(z)};
                    session_->issue(c);
                }
                if ((SDL_GetModState() & SDL_KMOD_SHIFT) == 0) {
                    ui.placing = sim::kNoDef;
                    village_.set_ghost(std::nullopt);
                    return;
                }
            }
        }
    }
    VillageView::Ghost ghost;
    ghost.def = ui.placing;
    ghost.x = ui.hover_x;
    ghost.z = ui.hover_z;
    ghost.rotation = ui.rotation;
    ghost.allowed = ui.hover_error == sim::PlaceError::None;
    village_.set_ghost(ghost);
}

void App::handle_game_click(std::uint32_t width, std::uint32_t height, math::Vec3 origin, math::Vec3 dir) {
    (void)width;
    (void)height;
    GameSession::Interaction& ui = session_->ui();
    if (ui.over_hud(input_.mouse_x, input_.mouse_y) || ui.field_farm.valid()) {
        return;  // Fields are marked by dragging (update_placement).
    }
    const sim::Game& game = session_->game();
    if (ui.rally_mode) {
        ui.rally_mode = false;
        if (const std::optional<math::Vec3> hit = ground_hit(game.map(), origin, dir)) {
            sim::Command c;
            c.type = sim::CommandType::ArmyOrder;
            c.value = 0;
            c.position = {sim::Fixed::from_ratio(static_cast<std::int32_t>(std::lround(hit->x * 100.0f)), 100),
                          sim::Fixed::from_ratio(static_cast<std::int32_t>(std::lround(hit->z * 100.0f)), 100)};
            session_->issue(c);
        }
        return;
    }
    if (ui.placing != sim::kNoDef) {
        const sim::BuildingDef& pd = game.content().buildings[ui.placing];
        if (pd.kind == sim::BuildingKind::Defense && !pd.trap && pd.width == 2 && pd.depth == 2) {
            return;  // Walls are placed by dragging (update_placement).
        }
        if (ui.hover_valid && ui.hover_error == sim::PlaceError::None) {
            sim::Command c;
            c.type = sim::CommandType::PlaceBuilding;
            c.def = ui.placing;
            c.position = {sim::Fixed::from_int(ui.hover_x), sim::Fixed::from_int(ui.hover_z)};
            c.value = ui.rotation;
            session_->issue(c);
            // Shift keeps placing more of the same.
            if ((SDL_GetModState() & SDL_KMOD_SHIFT) == 0) {
                ui.placing = sim::kNoDef;
                village_.set_ghost(std::nullopt);
            }
        }
        return;
    }
    const float alpha = static_cast<float>(clock_.interpolation());
    ui.selected_villager = {};
    ui.selected_building = {};
    if (const auto v = village_.pick_villager(game, origin, dir, alpha)) {
        ui.selected_villager = *v;
    } else if (const auto b = village_.pick_building(game, origin, dir)) {
        ui.selected_building = *b;
    }
}

void App::start_session(std::unique_ptr<GameSession> session) {
    session_ = std::move(session);
    const sim::Game& game = session_->game();
    // The sample village and the test crowd make way for the real town.
    map_scene_.hide_sample_village(scene_);
    crowd_.spawn(0, 1, 1.0f);
    village_.begin(scene_, map_scene_, session_->game());
    clock_.set_speed(1);
    next_autosave_tick_ =
        game.tick() + static_cast<std::uint64_t>(std::max(1, settings_->settings().gameplay.autosave_minutes)) * kTicksPerMinute;
    if (const sim::Building* tc = game.buildings().get(game.player(session_->town()).town_center)) {
        const float x = static_cast<float>(tc->x) + static_cast<float>(tc->width) * 0.5f;
        const float z = static_cast<float>(tc->z) + static_cast<float>(tc->depth) * 0.5f;
        camera_.set_target({x, map_surface_height(game.map(), x, z), z});
        camera_.set_distance(70.0f);
        camera_.snap();
        // Separate maps: the camera stays over the player's own map.
        const sim::Game::Region r = game.region(session_->town());
        camera_.set_bounds(static_cast<float>(r.x), static_cast<float>(r.z), static_cast<float>(r.x + r.size),
                           static_cast<float>(r.z + r.size));
    }
}

void App::write_save(const std::string& stem, const std::string& name, bool quiet) {
    if (!session_ || !paths_) {
        return;
    }
    const save::SaveData data = session_->make_save(name, mod_library_);
    const std::filesystem::path file = paths_->saves_dir() / (stem + save::kExtension);
    const bool ok = save::write_file(file, data);
    if (ok) {
        log::info("save: game saved ({} bytes of game state)", data.find("GAME")->data.size());
    }
    if (host_ && (!ok || !quiet)) {
        if (ok) {
            host_->toast(tr("save.done"));
        } else {
            host_->show_message(tr("save.failed.title"), tr("save.failed.body"));
        }
    }
}

void App::save_game() {
    if (!session_) {
        return;
    }
    const sim::Game& game = session_->game();
    const std::string name = tr("save.name", static_cast<int>(game.calendar().year),
                                game.population(session_->town()));
    // One file per save, named by the real time.
    const std::time_t now = std::time(nullptr);
    std::tm local{};
    (void)localtime_s(&local, &now);
    char stamp[32];
    (void)std::strftime(stamp, sizeof(stamp), "save-%Y%m%d-%H%M%S", &local);
    write_save(stamp, name, false);
}

void App::autosave_if_due() {
    // Every few minutes of game time (0 = off), rotating over a few files.
    const GameplaySettings& g = settings_->settings().gameplay;
    if (!session_ || g.autosave_minutes <= 0 || session_->game().tick() < next_autosave_tick_) {
        return;
    }
    next_autosave_tick_ = session_->game().tick() + static_cast<std::uint64_t>(g.autosave_minutes) * kTicksPerMinute;
    autosave_slot_ = autosave_slot_ % std::max(1, g.autosave_keep) + 1;
    const sim::Game& game = session_->game();
    write_save("autosave-" + std::to_string(autosave_slot_),
               tr("save.autoName", static_cast<int>(game.calendar().year),
                  game.population(session_->town())),
               true);
}

std::vector<save::Entry> App::list_saves() {
    return paths_ ? save::list(paths_->saves_dir()) : std::vector<save::Entry>{};
}

bool App::load_game(const std::filesystem::path& file) {
    if (!scene_ok_ || !host_) {
        return false;
    }
    save::SaveData data;
    const save::LoadError err = save::read_file(file, data);
    const std::shared_ptr<const sim::Content> content(pack_, &pack_->content);
    std::unique_ptr<GameSession> loaded;
    GameSession::LoadResult result = GameSession::LoadResult::Unreadable;
    if (err == save::LoadError::NewerSchema) {
        result = GameSession::LoadResult::OtherVersion;
    } else if (err == save::LoadError::None) {
        result = GameSession::load(data, content, loaded);
    }
    if (result != GameSession::LoadResult::Ok) {
        log::warn("save: cannot load a game (error {}, result {})", static_cast<int>(err), static_cast<int>(result));
        host_->show_message(tr("load.failed.title"), tr(load_result_key(result)));
        return false;
    }
    if (session_ && session_->networked()) {
        host_->show_message(tr("load.failed.title"), tr("load.error.network"));
        return false;
    }
    leave_map();
    if (!show_map_of(loaded->game().map())) {
        host_->show_message(tr("load.failed.title"), tr("load.error.damaged"));
        return false;
    }
    start_session(std::move(loaded));
    host_->show_game();
    host_->toast(tr("load.done"));
    return true;
}

}  // namespace sc

namespace sc {

bool App::show_map_of(const sim::MapData& source) {
    // The map is shown from its own copy.
    auto generated = std::make_unique<GeneratedMap>();
    generated->map = source;
    generated->visuals = build_map_visuals(generated->map, pack_->content);
    test_scene_.set_visible(scene_, false);
    if (!map_scene_.show(scene_, generated->visuals)) {
        test_scene_.set_visible(scene_, true);
        return false;
    }
    generated->visuals = MapVisuals{};
    map_ = std::move(generated);
    const sim::MapData* map = &map_->map;
    const float size = static_cast<float>(map->size);
    camera_.set_mode(CameraMode::Aerial);
    camera_.set_ground([map](float x, float z) { return map_surface_height(*map, x, z); });
    camera_.set_bounds(0.0f, 0.0f, size, size);
    camera_.set_max_distance_override(size * 1.6f);
    camera_.set_yaw(0.6f);
    map_scene_.show_sky(scene_, *map);
    return true;
}

int App::game_speed() const {
    return net_ && session_ && session_->networked() ? net_->speed() : clock_.speed();
}

void App::set_game_speed(int speed) {
    if (net_ && session_ && session_->networked()) {
        net_->request_speed(speed);  // Pause at once; the rest by vote.
    } else {
        clock_.set_speed(speed);
    }
}

std::string App::player_name() const {
    const std::string& name = settings_->settings().gameplay.player_name;
    return net::valid_name(name) ? name : tr("net.defaultName", instance_ + 1);
}

net::LocalInfo App::local_info() const {
    net::LocalInfo info;
    info.game_version = SC_VERSION_STRING;
    info.content_hash = pack_->content.hash;
    for (const mods::ModInfo& m : mod_library_.mods()) {
        if (m.loaded && m.manifest.affects_simulation) {
            info.mods.push_back({m.manifest.id, mods::version_text(m.manifest.version), m.hash});
        }
    }
    info.name = player_name();
    return info;
}

bool App::ensure_enet() {
    if (!enet_) {
        enet_ = std::make_unique<net::EnetLibrary>();
    }
    return enet_->ok();
}

bool App::host_game(const sim::MapSettings& map, const sim::GameRules& rules) {
    close_network();
    if (!ensure_enet()) {
        return false;
    }
    link_ = std::make_unique<net::EnetLink>();
    if (!link_->listen(game_port(), sim::kMaxPlayers - 1, loopback_)) {
        link_.reset();
        return false;
    }
    auto host = std::make_unique<net::NetHost>(*link_, local_info());
    net::GameConfig config;
    config.map = map;
    config.shared_town = true;
    config.seed = map.seed * 0x9E3779B97F4A7C15ull ^ 0x5A17C1DAull;
    config.rules = rules;
    host->set_config(config);
    net_ = std::move(host);
    if (!loopback_) {
        lan_announce_ = std::make_unique<net::LanDiscovery>();
        (void)lan_announce_->announce(game_port());
    }
    log::info("net: hosting on port {}", game_port());
    return true;
}

bool App::join_game(const std::string& address, std::uint16_t port) {
    close_network();
    if (!ensure_enet()) {
        return false;
    }
    link_ = std::make_unique<net::EnetLink>();
    if (!link_->connect(address, port)) {
        link_.reset();
        host_->show_message(tr("net.connectFailed.title"), tr("net.connectFailed.body"));
        return false;
    }
    net_ = std::make_unique<net::NetClient>(*link_, link_->server(), local_info());
    log::info("net: joining a game on port {}", port);
    return true;
}

void App::close_network() {
    if (net_ && session_ && session_->networked()) {
        leave_map();
    }
    net_.reset();
    net_start_.reset();
    if (link_) {
        link_->close();
        link_.reset();
    }
    lan_announce_.reset();
}

void App::leave_network() {
    close_network();
}

void App::set_lan_search(bool on) {
    if (on && !loopback_ && ensure_enet()) {
        lan_search_ = std::make_unique<net::LanDiscovery>();
        if (!lan_search_->search()) {
            lan_search_.reset();
        }
    } else {
        lan_search_.reset();
    }
}

std::vector<net::LanGame> App::lan_games() {
    return lan_search_ ? lan_search_->games() : std::vector<net::LanGame>{};
}

std::string App::seat_name(std::uint8_t slot) const {
    if (net_) {
        for (const net::LobbyPlayer& p : net_->lobby().players) {
            if (p.slot == slot) {
                return p.name;
            }
        }
    }
    return tr("net.defaultName", slot + 1);
}

void App::update_network(std::uint64_t now_ms) {
    if (lan_search_) {
        lan_search_->update(now_ms);
    }
    if (lan_announce_ && net_) {
        lan_announce_->set_game(player_name(), static_cast<std::uint8_t>(net_->lobby().players.size()),
                                net_->state() == net::NetSession::State::Playing);
        lan_announce_->update(now_ms);
    }
    if (!net_) {
        return;
    }
    net_->poll(now_ms);
    if (std::optional<net::Start> st = net_->take_start()) {
        net_start_ = *st;
        leave_map();
        start_map_generation(st->config.map, st->config.rules);
    }
    if (std::optional<std::vector<std::uint8_t>> snap = net_->take_snapshot()) {
        apply_snapshot(std::move(*snap));
    }
    for (const net::NetEvent& e : net_->take_events()) {
        handle_net_event(e);
        if (!net_) {
            return;  // The event closed the network.
        }
    }
}

void App::apply_snapshot(std::vector<std::uint8_t> state) {
    const std::shared_ptr<const sim::Content> content(pack_, &pack_->content);
    auto game = std::make_unique<sim::Game>(content, sim::MapData{}, 0, 0);
    sim::BinaryReader r(state);
    if (!game->load(r, content) || !r.at_end()) {
        log::error("net: the host's game could not be loaded");
        host_->show_message(tr("net.lost.title"), tr("net.snapshotFailed"));
        close_network();
        return;
    }
    if (session_ && session_->networked()) {
        // A resynchronization: same map, the host's state.
        village_.end(scene_);
        session_->replace_game(std::move(game));
        map_scene_.refresh_features(scene_, session_->game().map(), pack_->content);
        village_.begin(scene_, map_scene_, session_->game());
    } else {
        // Joining a game already started.
        leave_map();
        if (!show_map_of(game->map())) {
            host_->show_message(tr("net.lost.title"), tr("net.snapshotFailed"));
            close_network();
            return;
        }
        auto session = std::make_unique<GameSession>(std::move(game), net_->local_slot());
        session->attach(net_.get());
        start_session(std::move(session));
    }
    net_->snapshot_loaded(&session_->game());
}

std::string App::town_name(std::uint8_t player) const {
    if (net_) {
        for (const net::LobbyPlayer& p : net_->lobby().players) {
            if (p.slot == player) {
                return p.name;
            }
        }
    }
    return tr("hud.trade.town", static_cast<int>(player) + 1);
}

void App::update_sound(float dt) {
    if (!sound_started_) {
        sound_started_ = true;
        (void)sound_.start();
    }
    sound_.set_volumes(settings_->settings().audio);
    if (input_.mouse_pressed) {
        sound_.ui_click();  // Every click: the interface or the world.
    }
    if (session_ && host_->scene_mode() == UiHost::SceneMode::Map) {
        sound_.update(session_->game(), camera_.target().x, camera_.target().z, camera_.distance(), host_->game_paused(),
                      dt * static_cast<float>(std::max(1, clock_.speed())));
    } else {
        sound_.stop();
    }
}

void App::focus_camera(float x, float z) {
    if (!map_) {
        return;
    }
    const sim::MapData& m = map_->map;
    camera_.set_target({x, map_surface_height(m, x, z), z});
    following_ = false;
}

void App::set_overlay(int layer) {
    overlay_ = std::clamp(layer, 0, 8);
    village_.set_overlay(overlay_);
}

void App::report_game_events() {
    sim::Game& game = session_->game();
    const sim::Content& content = game.content();
    for (const sim::Game::Event& e : game.take_events()) {
        if (e.owner != session_->town() && e.kind != sim::Game::Event::Kind::TownLost &&
            e.kind != sim::Game::Event::Kind::GameOver) {
            continue;
        }
        const std::string place = e.entity.valid() && game.buildings().get(e.entity) != nullptr
                                      ? tr(content.buildings[game.buildings().get(e.entity)->def].name_key)
                                      : std::string();
        std::string text;
        switch (e.kind) {
            case sim::Game::Event::Kind::FireStarted: text = tr("event.fire", place); break;
            case sim::Game::Event::Kind::BurnedDown: text = tr("event.burnedDown", place); break;
            case sim::Game::Event::Kind::Outbreak:
                if (e.value < content.diseases.size()) {
                    text = tr("event.outbreak", tr(content.diseases[e.value].name_key));
                }
                break;
            case sim::Game::Event::Kind::MerchantArrived: text = tr("event.merchantArrived"); break;
            case sim::Game::Event::Kind::MerchantLeft: text = tr("event.merchantLeft"); break;
            case sim::Game::Event::Kind::OfferReceived: text = tr("event.offerReceived", town_name(e.other)); break;
            case sim::Game::Event::Kind::OfferAnswered:
                text = tr(e.value == 1 ? "event.offerAccepted" : "event.offerDeclined", town_name(e.other));
                break;
            case sim::Game::Event::Kind::CaravanArrived: text = tr("event.caravanArrived", town_name(e.other)); break;
            case sim::Game::Event::Kind::RaidStarted: text = tr("event.raid", static_cast<int>(e.value)); break;
            case sim::Game::Event::Kind::UnitTrained:
                if (e.value < content.units.size()) {
                    text = tr("event.unitTrained", tr(content.units[e.value].name_key));
                }
                break;
            case sim::Game::Event::Kind::TownLost: text = tr("event.townLost", town_name(e.owner)); break;
            case sim::Game::Event::Kind::GameOver: break;  // The end panel shows it.
            case sim::Game::Event::Kind::Attacked: {
                static constexpr const char* kKeys[] = {"event.attacked.deer", "event.attacked.boar", "event.attacked.wolf",
                                                        "event.attacked.bear", "event.attacked.raider"};
                text = tr(kKeys[e.value % std::size(kKeys)]);
                break;
            }
            case sim::Game::Event::Kind::Born: text = tr("event.born"); break;
            case sim::Game::Event::Kind::Died: text = tr("event.died"); break;
        }
        if (e.kind != sim::Game::Event::Kind::GameOver) {
            sound_.event(e.kind);
        }
        if (!text.empty()) {
            const bool has_pos = e.at.x != sim::Fixed{} || e.at.z != sim::Fixed{};
            host_->notify(std::move(text), has_pos, static_cast<float>(e.at.x.raw()) / 65536.0f,
                          static_cast<float>(e.at.z.raw()) / 65536.0f, game.calendar(), SDL_GetTicksNS());
        }
    }
}

void App::handle_net_event(const net::NetEvent& e) {
    using Kind = net::NetEvent::Kind;
    switch (e.kind) {
        case Kind::PlayerJoined: host_->toast(tr("net.joined", seat_name(e.slot))); break;
        case Kind::PlayerLeft: host_->toast(tr("net.left", seat_name(e.slot))); break;
        case Kind::PlayerRejoined: host_->toast(tr("net.rejoined", seat_name(e.slot))); break;
        case Kind::WrongMap: host_->toast(tr("net.wrongMap", seat_name(e.slot))); break;
        case Kind::VoteFailed: host_->toast(tr("net.voteFailed")); break;
        case Kind::Resynced: host_->toast(tr("net.resynced")); break;
        case Kind::Desync: {
            host_->toast(tr("net.desync", seat_name(e.slot)));
            if (net_->role() == net::NetSession::Role::Host && paths_) {
                // A report for whoever looks into it.
                const std::string text = "SalvaCiudad " + std::string(SC_VERSION_STRING) + "\ndesync with seat " +
                                         std::to_string(e.slot) + " at tick " + std::to_string(e.value) +
                                         "\ndifferent parts: " + e.detail + "\n";
                const std::filesystem::path file =
                    paths_->logs_dir() / ("desync-" + std::to_string(e.value) + "-seat" + std::to_string(e.slot) + ".txt");
                (void)fs::write_file_atomic(file, text);
            }
            break;
        }
        case Kind::SpeedChanged: {
            const char* key = e.reason == net::SpeedReason::Pause        ? "net.paused"
                              : e.reason == net::SpeedReason::SlowPlayer ? "net.slowPlayer"
                                                                          : "net.speed";
            host_->toast(tr(key, seat_name(e.slot), e.value));
            break;
        }
        case Kind::Rejected: {
            std::string body;
            switch (e.reject.reason) {
                case net::RejectReason::Version:
                    body = tr("net.rejected.version", e.reject.host_version, std::string(SC_VERSION_STRING));
                    break;
                case net::RejectReason::Mods: {
                    // What the host has that we do not, and the other way round.
                    const net::LocalInfo mine = local_info();
                    std::string missing;
                    std::string extra;
                    for (const net::ModRef& m : e.reject.host_mods) {
                        if (std::find(mine.mods.begin(), mine.mods.end(), m) == mine.mods.end()) {
                            missing += "\n- " + m.id + " " + m.version;
                        }
                    }
                    for (const net::ModRef& m : mine.mods) {
                        if (std::find(e.reject.host_mods.begin(), e.reject.host_mods.end(), m) == e.reject.host_mods.end()) {
                            extra += "\n- " + m.id + " " + m.version;
                        }
                    }
                    body = tr("net.rejected.mods", missing.empty() ? tr("net.rejected.none") : missing,
                              extra.empty() ? tr("net.rejected.none") : extra);
                    break;
                }
                case net::RejectReason::Full: body = tr("net.rejected.full"); break;
                case net::RejectReason::BadName: body = tr("net.rejected.name"); break;
                default: body = tr("net.rejected.protocol"); break;
            }
            host_->show_message(tr("net.rejected.title"), body);
            close_network();
            break;
        }
        case Kind::ConnectionLost:
            host_->show_message(tr("net.lost.title"), tr("net.lost.body"));
            close_network();
            break;
    }
}

}  // namespace sc
