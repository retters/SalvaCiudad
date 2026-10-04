#include "game/app.h"

#include "game/day_light.h"

#include <algorithm>
#include <array>
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
#include "game/build_info.h"
#include "game/menu_backgrounds.h"
#include "embedded/lang_en.h"
#include "i18n/translator.h"
#include "mods/mod_settings.h"
#include "core/file_io.h"
#include "core/png.h"
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


// Game ticks in a minute at x1 (autosave interval is set in minutes).
constexpr std::uint64_t kTicksPerMinute = 600;

// Blur behind a menu over the game, in pixels at 1080p.
constexpr float kMenuBlur = 3.0f;
// How far the camera turns from the middle of the map behind the menus.
constexpr float kMenuCameraDistance = 80.0f;

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

App::App(int instance, bool loopback, std::filesystem::path replay)
    : text_(atlas_), ui_(text_), instance_(instance), loopback_(loopback), replay_dir_(std::move(replay)) {}

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
    return replay_exit_code_;
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
    log::info("SalvaCiudad {} starting on {}", full_version(), SDL_GetPlatform());
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
    if (!replay_dir_.empty() && !load_replay(pack_ ? &pack_->content : nullptr)) {
        return false;
    }
    // The map behind the menu is made while the window and the rest load.
    load_menu_seeds();
    start_menu_background();

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
        const std::filesystem::path core = pack_->dir(mods::kCoreModId);
        scene_ok_ = true;
        // Every race's characters (phase 57).
        if (!walkers_.load(scene_, core, pack_->content)) {
            log::warn("villagers: no character models; people will not be drawn");
        }
    }
    if (scene_ok_ && !map_scene_.load_models(scene_, *pack_)) {
        log::warn("map: no feature models; maps will show bare ground");
    }
    if (scene_ok_) {
        village_.load(scene_, *pack_);
        village_.set_cast(&walkers_.cast());
    }
    if (!scene_ok_) {
        log::warn("scene: 3D view unavailable, menus only");
    }
    reset_camera_to_menu();
    if (!debug_.create(window_.sdl(), gpu_)) {
        log::warn("debug overlay unavailable");
    }

    host_ = std::make_unique<UiHost>(*this);
    if (replay_) {
        // The window in pixels as in the report, whatever the screen's scale.
        int pw = 0;
        int ph = 0;
        int lw = 0;
        int lh = 0;
        if (SDL_GetWindowSizeInPixels(window_.sdl(), &pw, &ph) && SDL_GetWindowSize(window_.sdl(), &lw, &lh) && pw > 0 &&
            ph > 0 && (static_cast<std::uint32_t>(pw) != replay_->view.width || static_cast<std::uint32_t>(ph) != replay_->view.height)) {
            (void)SDL_SetWindowSize(window_.sdl(), static_cast<int>(std::lround(static_cast<double>(replay_->view.width) * lw / pw)),
                                    static_cast<int>(std::lround(static_cast<double>(replay_->view.height) * lh / ph)));
        }
        if (!scene_ok_) {
            log::error("report: the 3D view is not available");
            return false;
        }
        sim::GameRules rules;
        rules.fog = sim::FogMode::None;
        host_->generate(replay_->map, rules);
        replay_step_ = ReplayStep::Generating;
    }
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
    // The audio stream too: SDL_Quit frees it, and the sound director
    // would destroy it again when the app goes.
    sound_.shutdown();
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
    hide_menu_background();
    load_mods();
    apply_language();
    if (scene_ok_) {
        (void)map_scene_.load_models(scene_, *pack_);
        village_.load(scene_, *pack_);
    }
    start_menu_background();  // With the new mods' trees and rocks.
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
            if (marking_.active || replay_) {
                // Marking a report takes the keys; showing one ignores them.
                input_.keys.pop_back();
                if (marking_.active && !event.key.repeat) {
                    marking_key(event.key.scancode);
                }
                return;
            }
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
            } else if (event.key.scancode == SDL_SCANCODE_F12 && (event.key.mod & SDL_KMOD_CTRL) != 0) {
                // A map report (phase 38): a fixed shortcut, like Ctrl+F3.
                begin_marking();
            } else if (event.key.scancode == SDL_SCANCODE_F3 && (event.key.mod & SDL_KMOD_CTRL) != 0) {
                // Developer tools: a fixed shortcut, like Alt+Enter.
                dev_tools_.toggle();
            } else if (dev_tools_.visible() && !map_ && replay_dir_.empty() &&
                       (event.key.scancode == SDL_SCANCODE_F5 || event.key.scancode == SDL_SCANCODE_F6)) {
                // Developer tools, in the menus: F5 another map behind them,
                // from a new seed; F6 keeps this one's seed in the user's list.
                if (event.key.scancode == SDL_SCANCODE_F5) {
                    hide_menu_background();
                    start_menu_background(SDL_GetPerformanceCounter() * 0x9E3779B97F4A7C15ull >> 20);
                } else if (menu_map_ && host_) {
                    const std::filesystem::path file = paths_->user_dir / menu_backgrounds::kFileName;
                    const bool ok = menu_backgrounds::add(file, menu_seed_);
                    load_menu_seeds();
                    log::info("menu: seed {} {} {}", menu_seed_, ok ? "saved in" : "could not be saved in",
                              text::path_to_utf8(file));
                    host_->toast(tr(ok ? "menu.background.saved" : "menu.background.notSaved", std::to_string(menu_seed_)));
                }
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
    // Showing a report changes the window and the sound only for itself.
    if (settings_dirty_since_ns_ == 0 || !replay_dir_.empty()) {
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
    } else if (mode == UiHost::SceneMode::MenuBackground) {
        in.rotate = 0.025f;  // A slow turn behind the menus.
    }
    camera_wheel_ = 0.0f;
    camera_drag_px_ = 0.0f;
    camera_drag_py_ = 0.0f;
    camera_look_dx_ = 0.0f;
    camera_look_dy_ = 0.0f;
    follow_villager(in);
    const InputSettings& s = settings_->settings().input;
    const CameraSpeeds speeds{static_cast<float>(s.camera_pan_speed), static_cast<float>(s.camera_rotate_speed),
                              static_cast<float>(s.camera_zoom_speed)};
    camera_.update(in, interactive_scene() ? speeds : CameraSpeeds{}, dt);
    show_anchor(dt);
}

// Phase 61: the camera keeps on the villager it follows, until the anchor
// is moved by hand or the villager is gone.
void App::follow_villager(const CameraInput& in) {
    if (!session_ || !map_ || replay_) {
        followed_shown_ = {};
        return;
    }
    GameSession::Interaction& ui = session_->ui();
    // What the interface asks about the developer tools' people.
    if (!ui.walker_info) {
        ui.walker_info = [this](std::uint32_t i) {
            GameSession::Interaction::WalkerInfo info;
            if (i < walkers_.size()) {
                info.there = true;
                info.model = walkers_.info(i).model;
                info.x = walkers_.position(i).x;
                info.z = walkers_.position(i).z;
            }
            return info;
        };
    }
    std::optional<VillageView::Standing> at;
    if (ui.followed_walker != 0) {
        if (in.move_forward != 0.0f || in.move_right != 0.0f || ui.followed_walker > walkers_.size() ||
            ui.followed_villager.valid()) {
            ui.followed_walker = 0;
        } else {
            at = VillageView::Standing{walkers_.position(ui.followed_walker - 1), walkers_.height(ui.followed_walker - 1) / 1.8f};
            if (camera_.mode() == CameraMode::Aerial && !camera_.following()) {
                camera_.set_mode(CameraMode::ThirdPerson);
            }
        }
    }
    if (ui.followed_villager.valid()) {
        if (in.move_forward != 0.0f || in.move_right != 0.0f) {
            ui.followed_villager = {};  // Walking the anchor away lets go.
        } else {
            at = village_.standing(session_->game(), ui.followed_villager, static_cast<float>(clock_.interpolation()));
            if (!at) {
                ui.followed_villager = {};
            }
        }
    }
    if (at) {
        if (ui.followed_villager != followed_shown_ && camera_.mode() == CameraMode::Aerial) {
            camera_.set_mode(CameraMode::ThirdPerson);  // Following starts close to it.
        }
        camera_.set_follow(at->feet, at->height);
    } else if (camera_.following()) {
        camera_.set_follow(std::nullopt);
    }
    followed_shown_ = ui.followed_villager;
    // Seen from its eyes, it is not drawn.
    village_.set_hidden_villager(at && camera_.mode() == CameraMode::FirstPerson ? ui.followed_villager : sim::EntityId{});
}

// The ghost of the anchor: in third person, when nobody is followed.
void App::show_anchor(float dt) {
    if (!session_ || !map_ || replay_ || camera_.mode() != CameraMode::ThirdPerson || camera_.following()) {
        village_.set_anchor_ghost(std::nullopt);
        anchor_known_ = false;
        return;
    }
    const math::Vec3 target = camera_.target();
    const math::Vec3 feet{target.x, map_surface_height(map_->map, target.x, target.z), target.z};
    VillageView::AnchorGhost ghost;
    ghost.feet = feet;
    const math::Vec3 fwd = camera_.forward_on_ground();
    ghost.yaw = std::atan2(fwd.x, fwd.z);
    if (anchor_known_ && dt > 1e-4f) {
        const float moved = math::length(math::Vec3{feet.x - anchor_last_.x, 0.0f, feet.z - anchor_last_.z});
        ghost.speed = std::min(moved / dt, 6.0f);  // No faster than a run, however fast the anchor flies.
    }
    anchor_last_ = feet;
    anchor_known_ = true;
    village_.set_anchor_ghost(ghost);
}

// Phase 66: with an explorer selected, a right click on the map or on the
// minimap sends it there.
void App::order_explorer(int width, int height) {
    const GameSession::Interaction& ui = session_->ui();
    const sim::Game& game = session_->game();
    const sim::Villager* v = game.villagers().get(ui.selected_villager);
    const sim::Building* job = v != nullptr ? game.buildings().get(v->job) : nullptr;
    if (v == nullptr || job == nullptr || v->owner != session_->town() ||
        game.content().buildings[job->def].work != sim::WorkKind::Explore) {
        return;
    }
    std::optional<math::Vec3> to;
    const float mx = input_.mouse_x;
    const float my = input_.mouse_y;
    const std::array<float, 4>& mini = ui.minimap;
    if (mini[2] > 0.0f && mx >= mini[0] && my >= mini[1] && mx < mini[0] + mini[2] && my < mini[1] + mini[3]) {
        const auto size = static_cast<float>(game.map().size);
        to = math::Vec3{(mx - mini[0]) / mini[2] * size, 0.0f, (my - mini[1]) / mini[3] * size};
    } else if (!ui.over_hud(mx, my)) {
        math::Vec3 origin;
        math::Vec3 dir;
        if (interactive_scene() && mouse_ray(width, height, origin, dir)) {
            to = ground_hit(game.map(), origin, dir);
        }
    }
    if (!to) {
        return;
    }
    sim::Command c;
    c.type = sim::CommandType::MoveVillager;
    c.entity = ui.selected_villager;
    const float edge = static_cast<float>(game.map().size - 1);
    c.position = {sim::Fixed::from_ratio(static_cast<std::int32_t>(std::clamp(to->x, 0.0f, edge) * 16.0f), 16),
                  sim::Fixed::from_ratio(static_cast<std::int32_t>(std::clamp(to->z, 0.0f, edge) * 16.0f), 16)};
    session_->issue(c);
}

void App::update_camera_windows() {
    const bool playing = session_ && map_ && !replay_ && host_->scene_mode() == UiHost::SceneMode::Map;
    for (int slot = 0; slot < kCameraWindows; ++slot) {
        ui_renderer_.set_external_image(kCameraImageId + static_cast<std::uint32_t>(slot),
                                        playing ? scene_.inset_texture(slot) : nullptr);
    }
    if (!playing) {
        return;
    }
    const sim::Game& g = session_->game();
    const float alpha = static_cast<float>(clock_.interpolation());
    auto& windows = session_->ui().camera_windows;
    // Where each one looks; a window whose thing is gone or under the fog closes.
    std::array<std::optional<math::Vec3>, kCameraWindows> targets;
    for (int slot = 0; slot < kCameraWindows; ++slot) {
        GameSession::Interaction::CameraWindow& w = windows[static_cast<std::size_t>(slot)];
        if (!w.open) {
            continue;
        }
        std::optional<math::Vec3> at;
        switch (w.kind) {
            case 0:
                if (const sim::Building* b = g.buildings().get(w.entity); b != nullptr && village_.building_shown(g, *b)) {
                    const math::Vec3 top = village_.building_top(g, *b);
                    const float ground = map_surface_height(g.map(), top.x, top.z);
                    at = math::Vec3{top.x, ground + (top.y - 1.0f - ground) * 0.5f, top.z};
                }
                break;
            case 1:
                if (const auto standing = village_.standing(g, w.entity, alpha)) {
                    at = standing->feet + math::Vec3{0.0f, 1.2f * standing->height, 0.0f};
                }
                break;
            case 2:
                if (village_.feature_shown(g, w.entity.index)) {
                    const math::Vec3 top = village_.feature_top(g, w.entity.index);
                    const float ground = map_surface_height(g.map(), top.x, top.z);
                    at = math::Vec3{top.x, ground + (top.y - 1.0f - ground) * 0.6f, top.z};
                }
                break;
            case 4:
                if (w.entity.index < walkers_.size()) {
                    at = walkers_.position(w.entity.index) + math::Vec3{0.0f, 1.2f, 0.0f};
                }
                break;
            default:
                if (const sim::Creature* c = g.creatures().get(w.entity);
                    c != nullptr && c->state != sim::CreatureState::Travel) {
                    const math::Vec3 p = village_.creature_position(g, *c, alpha);
                    if (village_.mover_shown(g, c->kind == sim::CreatureKind::Soldier, c->town, p.x, p.z)) {
                        at = p + math::Vec3{0.0f, 0.9f, 0.0f};
                    }
                }
                break;
        }
        if (!at) {
            w.open = false;
        }
        targets[static_cast<std::size_t>(slot)] = at;
    }
    const int slot = static_cast<int>(camera_window_turn_++ % static_cast<std::uint32_t>(kCameraWindows));
    const GameSession::Interaction::CameraWindow& w = windows[static_cast<std::size_t>(slot)];
    if (!w.open || !targets[static_cast<std::size_t>(slot)]) {
        return;
    }
    const math::Vec3 target = *targets[static_cast<std::size_t>(slot)];
    const float cp = std::cos(w.pitch);
    math::Vec3 eye = target + math::Vec3{std::sin(w.yaw) * cp, std::sin(w.pitch), std::cos(w.yaw) * cp} * w.distance;
    eye.y = std::max(eye.y, map_surface_height(g.map(), eye.x, eye.z) + 0.5f);
    render::InsetView view;
    view.view = math::look_at(eye, target, {0.0f, 1.0f, 0.0f});
    view.eye = eye;
    view.fov_y = math::radians(50.0f);
    view.near_z = 0.2f;
    // Far enough to give the thing its surroundings, near enough to be cheap.
    view.distance = std::clamp(w.distance * 8.0f, 120.0f, 400.0f);
    scene_.request_inset(slot, view);
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
    // On a map, log the average every few seconds so performance
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
        update_replay();
        // Marking a report, or capturing one: the camera stays still.
        const bool still = world_only();
        if (scene_ok_ && host_->scene_mode() != UiHost::SceneMode::None) {
            if (!still) {
                handle_scene_click(frame.width, frame.height);
                update_camera(dt);
            }
            if (session_ && host_->scene_mode() == UiHost::SceneMode::Map) {
                // The season: trees, hats and light (a report's, when showing one).
                const sim::Game& g = session_->game();
                const sim::Calendar cal = g.calendar();
                const sim::Season season = replay_ ? replay_->view.season : cal.season;
                // The trees turn over the first days of a season, each at
                // its own time; a new game starts with them already turned.
                const sim::Calendar first = sim::calendar(g.rules().climate, 0);
                const bool turned = replay_ || (cal.year == first.year && cal.season == first.season);
                const TreeCalendar when = turned ? TreeCalendar{season, kTurnSteps}
                                                 : tree_calendar(season, cal.season_progress);
                const bool snowy = replay_ ? replay_->view.snow * static_cast<float>(sim::village::kMaxSnow) > 25.0f : g.snow() > 25;
                map_scene_.set_season(scene_, g.map(), g.content(), when, snowy);
                map_scene_.update_sky(scene_, dt * static_cast<float>(host_->game_paused() ? 0 : 1));
                lighting_ = seasonal_lighting(season);
                night_ = 0.0f;
                // While the towns are being founded (phase 74) it is plain day:
                // nobody chooses a site in the dark of the first dawn.
                if (const sim::DayNightSettings& cycle = g.rules().day_night;
                    cycle.enabled() && !replay_ && !g.awaiting_founders()) {
                    const bool night = g.day_time().night;
                    const float progress = day_progress(cycle, g.tick(), static_cast<float>(clock_.interpolation()));
                    lighting_ = day_lighting(lighting_, night, progress);
                    night_ = 1.0f - daylight(night, progress);
                }
                if (!still) {
                    update_placement(frame.width, frame.height);
                }
                const float speed = host_->game_paused() ? 0.0f : speed::multiplier(clock_.speed());
                village_.set_view(camera_.target().x, camera_.target().z, session_->town());
                update_war_fog();
                village_.set_fog(&session_->fog());
                // What the eye is inside of and, in third person, what
                // stands between it and the point it turns around.
                occluders_.update(scene_, session_->game(), village_, map_scene_, camera_.eye(),
                                  camera_.mode() == CameraMode::ThirdPerson ? std::optional<math::Vec3>(camera_.target())
                                                                            : std::nullopt,
                                  dt);
                village_.update(scene_, map_scene_, session_->game(), static_cast<float>(clock_.interpolation()), dt,
                                speed);
                // People placed with the developer tools walk among them.
                if (walkers_.size() > 0) {
                    walkers_.update(scene_, dt, village_.characters());
                }
                // The lights of the night, lit as the daylight goes.
                night_lights_.clear();
                if (night_ > 0.0f) {
                    village_.lights(session_->game(), true, night_lights_);
                }
                scene_.set_lights(night_lights_, night_, camera_.target());
            } else if (menu_game_ && menu_map_ && !map_) {
                // Behind the menus: the map's own animals, at the game's pace.
                village_.set_view(camera_.target().x, camera_.target().z, 0);
                village_.update(scene_, map_scene_, *menu_game_, static_cast<float>(clock_.interpolation()), dt,
                                speed::multiplier(clock_.speed()));
                map_scene_.update_sky(scene_, dt);
            }
            render::SceneView view;
            view.view = camera_.view();
            view.eye = camera_.eye();
            view.fov_y = math::radians(Camera::kFovY);
            view.near_z = camera_.near_z();
            view.aspect = static_cast<float>(frame.width) / static_cast<float>(std::max(1u, frame.height));
            view_width_ = frame.width;
            view_height_ = std::max(1u, frame.height);
            // Zoomed out past the normal limit over a map: the whole ground
            // stays visible (temporary, decision D-615).
            if (map_ && host_->scene_mode() == UiHost::SceneMode::Map && camera_.distance() > Camera::kMaxDistance) {
                view.terrain_distance = camera_.distance() * 2.5f + static_cast<float>(map_->map.size);
            }
            view.time = static_cast<float>(static_cast<double>(SDL_GetTicksNS() % 3'600'000'000'000ull) * 1e-9);
            if (session_ && host_->scene_paused()) {
                view.blur = kMenuBlur;
            }
            if (session_ && host_->scene_mode() == UiHost::SceneMode::Map) {
                view.snow = static_cast<float>(session_->game().snow()) / static_cast<float>(sim::village::kMaxSnow);
                // The water freezes over below -3 °C, as fishing stops (sim).
                const float t = static_cast<float>(session_->game().temperature());
                view.ice = t <= -3.0f ? std::min(1.0f, (-t - 2.0f) / 3.0f) : 0.0f;
                if (replay_) {
                    view.snow = replay_->view.snow;
                    view.ice = 0.0f;
                }
            }
            update_camera_windows();
            scene_drawn = scene_.render(frame, view, lighting_);
        }

        // Interface on top.
        const Settings& s = settings_->settings();
        ui_.set_tooltips(s.ui.show_tooltips, s.ui.tooltip_delay_ms);
        ui_.begin_frame(input_, static_cast<float>(frame.width), static_cast<float>(frame.height), ui_scale(),
                        SDL_GetTicksNS(), atlas_.white_u(), atlas_.white_v());
        // The developer tools pick and place in the world before drawing.
        DevContext dev = still ? DevContext{} : dev_context(frame.width, frame.height);
        if (!still) {
            dev_tools_.update(dev);
        }
        if (debug_.wants_keyboard()) {
            input_.keys.clear();  // Typing in a tool, not in the game.
        }
        // Markers belong to the 3D view, under the interface.
        if (still) {
            // Only the world, and the strokes over it while marking.
            update_marking();
            draw_marking();
        } else if (scene_drawn && host_->scene_mode() == UiHost::SceneMode::Map &&
                   (!session_ || (!replay_ && choosing_site(session_->game(), session_->ui(), session_->local_player())))) {
            // The map alone, or a town to found (phase 74): the suggested sites.
            draw_start_markers(frame.width, frame.height);
        }
        if (!still && scene_drawn && session_ && host_->scene_mode() == UiHost::SceneMode::Map) {
            // A marker over the selected villager or building.
            const sim::Game& g = session_->game();
            const GameSession::Interaction& sel = session_->ui();
            if (const sim::Villager* v = g.villagers().get(sel.selected_villager)) {
                const math::Vec3 p = village_.villager_position(g, *v, static_cast<float>(clock_.interpolation()));
                draw_marker(frame.width, frame.height, p + math::Vec3{0.0f, 2.3f, 0.0f}, ui_.theme().accent);
            } else if (const sim::Building* b = g.buildings().get(sel.selected_building)) {
                draw_marker(frame.width, frame.height, village_.building_top(g, *b), ui_.theme().accent);
            } else if (const sim::Creature* c = g.creatures().get(sel.selected_creature)) {
                const math::Vec3 p = village_.creature_position(g, *c, static_cast<float>(clock_.interpolation()));
                draw_marker(frame.width, frame.height, p + math::Vec3{0.0f, 2.3f, 0.0f}, ui_.theme().accent);
            } else if (sel.selected_walker != 0 && sel.selected_walker <= walkers_.size()) {
                draw_marker(frame.width, frame.height,
                            walkers_.position(sel.selected_walker - 1) + math::Vec3{0.0f, 2.3f, 0.0f}, ui_.theme().accent);
            } else if (sel.selected_node != 0 && village_.feature_shown(g, sel.selected_node - 1)) {
                draw_marker(frame.width, frame.height, village_.feature_top(g, sel.selected_node - 1), ui_.theme().accent);
            }
        }
        if (!still && scene_drawn && host_->scene_mode() == UiHost::SceneMode::Map) {
            draw_supply_markers(frame.width, frame.height);
            draw_scene_markers(frame.width, frame.height);
        }
        if (!still && scene_drawn) {
            if (const auto m = dev_tools_.hovered_marker(dev)) {
                draw_marker(frame.width, frame.height, *m, ui_.theme().text);
            }
            if (const auto m = dev_tools_.selected_marker(dev)) {
                draw_marker(frame.width, frame.height, *m, ui_.theme().danger);
            }
        }
        if (!still) {
            host_->frame(ui_);
        }
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
            debug_info_.sim_tick = menu_game_ ? menu_game_->tick() : 0;
            debug_info_.sim_hash = 0;
            debug_info_.sim_entities = menu_game_ ? menu_game_->registry().alive_count() : 0;
        }
        update_cursor_info(frame.width, frame.height);
        if (still) {
            debug_.skip_frame();
        } else {
            debug_.build(debug_info_, [&] { dev_tools_.draw(dev); }, dev_tools_.visible());
        }

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
        // A report's screenshot: this frame, read back from the GPU.
        const bool mark = marking_.active && marking_.capture;
        if (scene_drawn && (mark || replay_step_ == ReplayStep::Capture)) {
            FrameCapture capture;
            (void)gpu_.end_frame_captured(frame, capture);
            if (mark) {
                save_report(capture);
            } else {
                finish_replay(capture);
            }
            return;
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
    const std::uint64_t dropped_before = clock_.dropped_ticks();
    const int ticks = clock_.advance(static_cast<std::int64_t>(elapsed));
    // A machine that cannot keep the speed up goes one step down instead of
    // losing ticks quietly (alone; with others the host does it).
    if (session_ && !session_->networked() && host_ && !replay_) {
        slow_frames_ = clock_.dropped_ticks() > dropped_before ? slow_frames_ + 1 : 0;
        if (slow_frames_ >= kSlowFramesToLower && clock_.speed() > speed::kNormal) {
            clock_.set_speed(speed::slower(clock_.speed()));
            slow_frames_ = 0;
            host_->toast(tr("hud.speed.lowered", speed_text(clock_.speed())));
        }
    }
    if (net_ && session_ && session_->networked()) {
        (void)net_->advance(ticks, now / 1'000'000ull);
        autosave_if_due();
    } else if (session_) {
        // A menu over a single-player game stops it.
        if (host_ && !host_->game_paused()) {
            if (session_->game().awaiting_founders()) {
                // Phase 74: no time goes by until the town is founded, at
                // any speed and in pause; the step only runs the orders.
                session_->step();
            } else {
                for (int i = 0; i < ticks; ++i) {
                    session_->step();
                }
            }
            autosave_if_due();
        }
    } else if (menu_game_) {
        for (int i = 0; i < ticks; ++i) {
            menu_game_->step();
        }
    }
    update_menu_background();

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
    return mode == UiHost::SceneMode::Map && !host_->scene_paused();
}

void App::reset_camera_to_menu() {
    camera_.set_max_distance_override(0.0f);
    camera_.set_mode(CameraMode::Aerial);
    camera_.set_follow(std::nullopt);
    if (menu_map_) {
        // Turning slowly around the middle of the map.
        const sim::MapData* map = &menu_map_->map;
        const float size = static_cast<float>(map->size);
        camera_.set_ground([map](float x, float z) { return map_surface_height(*map, x, z); });
        camera_.set_bounds(0.0f, 0.0f, size, size);
        camera_.set_target({size * 0.5f, map_surface_height(*map, size * 0.5f, size * 0.5f), size * 0.5f});
        camera_.set_distance(kMenuCameraDistance);
    } else {
        camera_.set_ground({});
        camera_.set_bounds(0.0f, 0.0f, 1.0f, 1.0f);
        camera_.set_target({0.0f, 0.0f, 0.0f});
        camera_.set_distance(kMenuCameraDistance);
    }
    camera_.set_yaw(0.6f);
    camera_.snap();
}

void App::load_menu_seeds() {
    menu_seeds_ = menu_backgrounds::load(paths_->game_data_dir() / menu_backgrounds::kFileName);
    menu_user_seeds_ = menu_backgrounds::load(paths_->user_dir / menu_backgrounds::kFileName);
}

void App::start_menu_background(std::optional<std::uint64_t> seed) {
    if (!pack_ || !replay_dir_.empty()) {
        return;  // A report shows its own map and nothing else.
    }
    // Any of the list; the clock only chooses which, nothing in a game.
    menu_seed_ = seed ? *seed : menu_backgrounds::choose(menu_seeds_, menu_user_seeds_, SDL_GetPerformanceCounter() / 16);
    menu_started_ns_ = SDL_GetTicksNS();
    menu_job_.start(menu_backgrounds::settings_for(menu_seed_), pack_);
}

void App::update_menu_background() {
    if (!scene_ok_ || map_ || menu_map_ || menu_job_.status().state != MapGenStatus::State::Done) {
        return;
    }
    std::unique_ptr<GeneratedMap> generated = menu_job_.take();
    if (!generated || !map_scene_.show(scene_, generated->visuals)) {
        return;
    }
    generated->visuals = MapVisuals{};  // The renderer keeps its own copy.
    menu_map_ = std::move(generated);
    map_scene_.show_sky(scene_, menu_map_->map);
    // A game without towns: only the wildlife of the map.
    const std::shared_ptr<const sim::Content> content(pack_, &pack_->content);
    menu_game_ = std::make_unique<sim::Game>(content, menu_map_->map,
                                             sim::GameSetup{0, menu_seed_ ^ 0x5A17C1DAull, false, sim::GameRules{}});
    village_.set_fog(nullptr);
    village_.begin(scene_, map_scene_, *menu_game_);
    lighting_ = render::Lighting{};
    night_ = 0.0f;
    scene_.set_lights({}, 0.0f, {});
    clock_.set_speed(speed::kNormal);
    reset_camera_to_menu();
    log::info("menu: background map of seed {} shown {:.2f} s after it was asked for", menu_seed_,
              static_cast<double>(SDL_GetTicksNS() - menu_started_ns_) / 1e9);
}

void App::hide_menu_background() {
    menu_job_.cancel();
    if (!menu_map_) {
        return;
    }
    village_.end(scene_);
    map_scene_.hide(scene_);
    menu_game_.reset();
    menu_map_.reset();
}

void App::start_map_generation(const sim::MapSettings& settings, const sim::GameRules& rules, bool start_towns) {
    pending_rules_ = rules;
    pending_start_towns_ = start_towns;
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
    cursor_names_.reset();
    cursor_key_ = {};
    hide_menu_background();
    if (!map_scene_.show(scene_, generated->visuals)) {
        start_menu_background();
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
    walkers_.set_ground([map](float x, float z) { return map_surface_height(*map, x, z); });
    camera_.set_bounds(0.0f, 0.0f, size, size);
    // For now the camera can back off until the whole map fits (D-615).
    camera_.set_max_distance_override(size * 1.6f);
    // Over a suggested site: each seat its own, to begin with.
    const std::size_t site = map->starts.empty() || !net_start_ || !net_ ? 0 : net_->local_slot() % map->starts.size();
    const float sx = map->starts.empty() ? size * 0.5f : static_cast<float>(map->starts[site].x.raw()) / 65536.0f;
    const float sz = map->starts.empty() ? size * 0.5f : static_cast<float>(map->starts[site].z.raw()) / 65536.0f;
    camera_.set_target({sx, map_surface_height(*map, sx, sz), sz});
    camera_.set_yaw(0.6f);
    camera_.set_distance(110.0f);
    camera_.snap();
    map_scene_.show_sky(scene_, *map);
    // A village game on it (phase 8); its own stream of random numbers.
    const std::shared_ptr<const sim::Content> content(pack_, &pack_->content);
    if (net_start_ && net_) {
        const net::Start st = *net_start_;
        net_start_.reset();
        // Nobody has a town yet: each seat founds its own (phase 74). The
        // seats carry their players' names and colors (phase 75).
        sim::GameSetup setup{st.players, st.config.seed, st.config.shared_town, st.config.rules, false, {}};
        setup.access = net::lobby_access(st.config);
        setup.seats.resize(st.players);
        for (const net::LobbyPlayer& p : net_->lobby().players) {
            if (p.slot < setup.seats.size() && sim::valid_seat_name(p.name)) {
                setup.seats[p.slot] = {p.name, std::min<std::uint8_t>(p.color, sim::kMaxSeatColor)};
            }
        }
        // Phase 79: without a seat, it watches everything from the start.
        const std::uint8_t slot = net_->local_slot();
        auto session = std::make_unique<GameSession>(content, *map, setup, slot == net::kNoSeat ? std::uint8_t{0} : slot);
        if (slot == net::kNoSeat) {
            session->watch(0, true, GameSession::kNoSeat);
        }
        session->attach(net_.get());
        // The developer tools stay on in network games for now (D-7603, in place of D-910).
        start_session(std::move(session));
        net_->game_built(&session_->game(), net::map_hash(*map));
        return true;
    }
    // The tutorial and the reports start with the town standing.
    start_session(std::make_unique<GameSession>(
        content, *map,
        sim::GameSetup{1, map->settings.seed ^ 0x5A17C1DAull, false, pending_rules_, pending_start_towns_ || replay_,
                       {sim::SeatInfo{sim::valid_seat_name(player_name()) ? player_name() : std::string(), 0}}}));
    return true;
}

void App::leave_map() {
    if (!map_) {
        return;
    }
    dev_tools_.reset();
    cursor_names_.reset();
    cursor_key_ = {};
    village_.set_fog(nullptr);
    (void)scene_.set_war_fog(0, 0, 0.0f);
    war_mode_shown_ = 0;
    war_side_shown_ = 0;
    war_generation_shown_ = 0;
    village_.end(scene_);
    session_.reset();
    lighting_ = render::Lighting{};
    night_ = 0.0f;
    scene_.set_lights({}, 0.0f, {});
    clock_.set_speed(speed::kNormal);
    map_scene_.hide(scene_);
    walkers_.clear();
    walkers_.set_ground({});
    map_.reset();
    // Back to the menus: another map behind them.
    reset_camera_to_menu();
    start_menu_background();
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
    ctx.crowd = &walkers_;
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
        if (session_ && session_->game().site_taken(i)) {
            continue;  // Somebody founded there.
        }
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

void App::draw_supply_markers(std::uint32_t width, std::uint32_t height) {
    if (!session_ || replay_) {
        return;
    }
    // Phase 81: a sign over each of the town's workplaces with nothing left
    // to take, until it finds something again.
    const sim::Game& g = session_->game();
    ui::DrawList& dl = ui_.draw();
    const math::Mat4 view_proj = camera_view_proj(width, height);
    const ui::TextStyle st = ui_.style(ui_.theme().body, ui::FontRole::Bold);
    const float r = ui_.s(10.0f);
    for (const sim::Building& b : g.buildings().data()) {
        if (b.supply != sim::Supply::Exhausted || b.stopped || b.workers.empty() || b.owner != session_->town() ||
            b.state != sim::BuildingState::Complete) {
            continue;
        }
        const math::Vec3 p = village_.building_top(g, b);
        const math::Vec4 clip = view_proj * math::Vec4{p.x, p.y, p.z, 1.0f};
        if (clip.w <= 0.01f) {
            continue;
        }
        const float sx = std::round((clip.x / clip.w * 0.5f + 0.5f) * static_cast<float>(width));
        const float sy = std::round((0.5f - clip.y / clip.w * 0.5f) * static_cast<float>(height)) - r * 2.2f;
        if (sx < -r || sy < -r || sx > static_cast<float>(width) + r || sy > static_cast<float>(height) + r) {
            continue;
        }
        dl.rect({sx - r - 2, sy - r - 2, 2 * r + 4, 2 * r + 4}, ui::Color::rgb(0x000000, 150));
        dl.rect({sx - r, sy - r, 2 * r, 2 * r}, ui_.theme().danger);
        const std::string sign = "!";
        const float tw = ui_.text().measure(st, sign);
        const float th = ui_.text().line_height(st);
        ui_.text().draw(dl, st, std::round(sx - tw * 0.5f), std::round(sy - th * 0.5f), sign, ui::Color::rgb(0xFFFFFF));
    }
}

math::Mat4 App::camera_view_proj(std::uint32_t width, std::uint32_t height) const {
    const float aspect = static_cast<float>(width) / static_cast<float>(std::max(1u, height));
    // The far plane does not change where things land on screen.
    return camera_.projection(aspect, 1000.0f) * camera_.view();
}

void App::update_mouse_capture() {
    // First person looks around with a captured pointer,
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
}

void App::draw_scene_markers(std::uint32_t width, std::uint32_t height) {
    ui::DrawList& dl = ui_.draw();
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
}

}  // namespace sc

namespace sc {

bool App::mouse_ray(std::uint32_t width, std::uint32_t height, math::Vec3& origin, math::Vec3& dir) const {
    if (mouse_captured_) {
        return false;
    }
    return screen_ray(width, height, input_.mouse_x, input_.mouse_y, origin, dir);
}

bool App::screen_ray(std::uint32_t width, std::uint32_t height, float x, float y, math::Vec3& origin,
                     math::Vec3& dir) const {
    if (x < 0.0f || y < 0.0f || width == 0 || height == 0) {
        return false;
    }
    const math::Mat4 inv = math::inverse(camera_view_proj(width, height));
    const float nx = x / static_cast<float>(width) * 2.0f - 1.0f;
    const float ny = 1.0f - y / static_cast<float>(height) * 2.0f;
    origin = inv.transform_point({nx, ny, 1.0f});
    dir = math::normalize(inv.transform_point({nx, ny, 0.01f}) - origin);
    return true;
}

void App::update_cursor_info(std::uint32_t width, std::uint32_t height) {
    math::Vec3 origin;
    math::Vec3 dir;
    std::optional<math::Vec3> hit;
    if (debug_.visible() && map_ && scene_ok_ && host_ && interactive_scene() &&
        host_->scene_mode() == UiHost::SceneMode::Map && !debug_.wants_mouse() && mouse_ray(width, height, origin, dir)) {
        hit = ground_hit(map_->map, origin, dir, far_pick());
    }
    if (!hit) {
        debug_info_.cursor.clear();
        cursor_key_ = {};
        return;
    }
    CursorKey key;
    key.cx = static_cast<std::int32_t>(std::floor(hit->x));
    key.cz = static_cast<std::int32_t>(std::floor(hit->z));
    // Under the fog of war nothing is told (decision D-3704).
    key.shown = !session_ || session_->fog().shows(hit->x, hit->z);
    key.language = i18n::translator().generation();
    key.map = &map_->map;
    if (key == cursor_key_ && !debug_info_.cursor.empty()) {
        return;
    }
    cursor_key_ = key;
    if (!key.shown) {
        debug_info_.cursor = {tr("cursor.unexplored")};
        return;
    }
    debug_info_.cursor = describe_lines(cursor_names_.describe(map_->map, key.cx, key.cz), pack_ ? &pack_->content : nullptr);
}

// Phase 74. The town is not founded yet: the center follows the cursor as
// a ghost; a click fixes the site and the interface asks to confirm.
void App::update_founding(std::uint32_t width, std::uint32_t height) {
    GameSession::Interaction& ui = session_->ui();
    const sim::Game& game = session_->game();
    const std::uint8_t local = session_->local_player();
    ui.placing = sim::kNoDef;
    ui.field_farm = {};
    village_.set_field_ghost(std::nullopt);
    const sim::DefIndex center = game.town_center_def();
    if (center == sim::kNoDef || !choosing_site(game, ui, local)) {
        // The town's first seat founds it; a latecomer, once it says so.
        ui.found_asked = false;
        village_.set_ghost(std::nullopt);
        return;
    }
    // An order that never arrived (the site was taken meanwhile): again.
    constexpr std::uint64_t kLostAfterTurns = 50;
    if (ui.found_sent != 0 && game.turn() > ui.found_sent + kLostAfterTurns) {
        ui.found_sent = 0;
        if (host_) {
            host_->toast(tr("hud.found.failed"));
        }
    }
    if (right_clicked_ && ui.found_sent == 0) {
        ui.found_asked = false;
    }
    VillageView::Ghost ghost;
    ghost.def = center;
    if (ui.found_asked || ui.found_sent != 0) {
        const sim::PlaceError error = game.can_found(local, ui.found_x, ui.found_z, ui.found_rotation);
        if (error != sim::PlaceError::None && ui.found_sent == 0) {
            ui.found_asked = false;  // Somebody took it while the player thought.
        }
        ghost.x = ui.found_x;
        ghost.z = ui.found_z;
        ghost.rotation = ui.found_rotation;
        ghost.allowed = error == sim::PlaceError::None;
        village_.set_ghost(ghost);
        return;
    }
    math::Vec3 origin;
    math::Vec3 dir;
    if (!interactive_scene() || !mouse_ray(width, height, origin, dir) || ui.over_hud(input_.mouse_x, input_.mouse_y)) {
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
    sim::Game::footprint(game.content().buildings[center], ui.rotation, w, d);
    ui.hover_valid = true;
    ui.hover_x = static_cast<std::int32_t>(std::lround(hit->x - static_cast<float>(w) * 0.5f));
    ui.hover_z = static_cast<std::int32_t>(std::lround(hit->z - static_cast<float>(d) * 0.5f));
    ui.hover_error = game.can_found(local, ui.hover_x, ui.hover_z, ui.rotation);
    ghost.x = ui.hover_x;
    ghost.z = ui.hover_z;
    ghost.rotation = ui.rotation;
    ghost.allowed = ui.hover_error == sim::PlaceError::None;
    village_.set_ghost(ghost);
}

void App::update_placement(std::uint32_t width, std::uint32_t height) {
    GameSession::Interaction& ui = session_->ui();
    const sim::Game& game = session_->game();
    ui.hover_valid = false;
    if (!game.founded(session_->local_player())) {
        update_founding(width, height);
        return;
    }
    if (ui.found_asked || ui.found_sent != 0 || ui.found_mode) {
        // Founded (or taken into a town): the ghost of the site goes.
        ui.found_asked = false;
        ui.found_sent = 0;
        ui.found_mode = false;
        village_.set_ghost(std::nullopt);
    }
    if (right_clicked_ && ui.placing != sim::kNoDef) {
        ui.placing = sim::kNoDef;  // Right click cancels.
    } else if (right_clicked_ && !ui.field_farm.valid()) {
        order_explorer(width, height);
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
    if (!game.founded(session_->local_player())) {
        // Phase 74: the click chooses the site; the interface asks.
        if (choosing_site(game, ui, session_->local_player()) && !ui.found_asked && ui.found_sent == 0 &&
            ui.hover_valid && ui.hover_error == sim::PlaceError::None) {
            ui.found_asked = true;
            ui.found_x = ui.hover_x;
            ui.found_z = ui.hover_z;
            ui.found_rotation = ui.rotation;
        }
        return;
    }
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
    ui.clear_selection();
    if (const auto v = village_.pick_villager(game, origin, dir, alpha)) {
        ui.selected_villager = *v;
        // A second click on the same villager right away: follow it.
        const std::uint64_t now = SDL_GetTicksNS();
        if (*v == last_clicked_villager_ && now - last_click_ns_ < kDoubleClickNs) {
            ui.followed_villager = *v;
        }
        last_clicked_villager_ = *v;
        last_click_ns_ = now;
    } else if (const auto b = village_.pick_building(game, origin, dir)) {
        ui.selected_building = *b;
    } else if (const auto c = village_.pick_creature(game, origin, dir, alpha)) {
        ui.selected_creature = *c;
    } else if (const auto w = walkers_.pick(origin, dir)) {
        ui.selected_walker = static_cast<std::uint32_t>(*w) + 1;  // One of the developer tools' people.
    } else if (const auto f = village_.pick_feature(game, origin, dir)) {
        ui.selected_node = *f + 1;
    }
}

void App::update_war_fog() {
    FogView& fog = session_->fog();
    // The seat joined a town, or got its seat (phases 75 to 77): it sees
    // with that town's eyes from now on.
    if (const std::uint8_t group = session_->game().vision_group(session_->local_player());
        group != fog.group() && !session_->view_all()) {
        fog.begin(session_->game(), group);
    }
    fog.update(session_->game());
    const int mode = static_cast<int>(fog.mode());
    if (mode != war_mode_shown_ || fog.side() != war_side_shown_ || fog.generation() != war_generation_shown_) {
        // Another game, or the fog turned on or off: the whole grid again.
        war_mode_shown_ = mode;
        war_side_shown_ = fog.side();
        war_generation_shown_ = fog.generation();
        (void)fog.take_dirty();
        if (mode == 0 || fog.side() <= 0) {
            (void)scene_.set_war_fog(0, 0, 0.0f);
            return;
        }
        if (scene_.set_war_fog(mode, fog.side(), static_cast<float>(sim::kFogCell))) {
            scene_.update_war_fog(fog.texels(), 0, 0, fog.side(), fog.side());
            // Phase 34: what stands high shows through it.
            (void)scene_.set_war_ceiling(fog.ceiling(), fog.ceiling_side(), FogView::kCeilingBand);
        }
        return;
    }
    for (const FogView::Rect& r : fog.take_dirty()) {
        if (mode != 0) {
            scene_.update_war_fog(fog.texels(), r.x, r.z, r.w, r.d);
        }
    }
    // What is now under the fog cannot stay selected.
    GameSession::Interaction& ui = session_->ui();
    const sim::Game& game = session_->game();
    if (const sim::Villager* v = game.villagers().get(ui.selected_villager);
        v != nullptr && !village_.mover_shown(game, true, v->owner, static_cast<float>(v->position.x.raw()) / 65536.0f,
                                              static_cast<float>(v->position.z.raw()) / 65536.0f)) {
        ui.selected_villager = {};
    }
    if (const sim::Building* b = game.buildings().get(ui.selected_building);
        b != nullptr && !village_.building_shown(game, *b)) {
        ui.selected_building = {};
    }
    if (const sim::Creature* c = game.creatures().get(ui.selected_creature);
        c != nullptr && !village_.mover_shown(game, c->kind == sim::CreatureKind::Soldier, c->town,
                                              static_cast<float>(c->position.x.raw()) / 65536.0f,
                                              static_cast<float>(c->position.z.raw()) / 65536.0f)) {
        ui.selected_creature = {};
    }
}

void App::start_session(std::unique_ptr<GameSession> session) {
    session_ = std::move(session);
    const sim::Game& game = session_->game();
    // The sample village makes way for the real town.
    map_scene_.hide_sample_village(scene_);
    walkers_.clear();
    village_.begin(scene_, map_scene_, session_->game());
    clock_.set_speed(speed::kNormal);
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
    if (!session_ || g.autosave_minutes <= 0 || !replay_dir_.empty() || session_->game().tick() < next_autosave_tick_) {
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

GameSession::LoadResult App::read_save(const std::filesystem::path& file, std::unique_ptr<GameSession>& out) {
    save::SaveData data;
    const save::LoadError err = save::read_file(file, data);
    const std::shared_ptr<const sim::Content> content(pack_, &pack_->content);
    GameSession::LoadResult result = GameSession::LoadResult::Unreadable;
    if (err == save::LoadError::NewerSchema) {
        result = GameSession::LoadResult::OtherVersion;
    } else if (err == save::LoadError::None) {
        result = GameSession::load(data, content, out);
    }
    if (result != GameSession::LoadResult::Ok) {
        log::warn("save: cannot load a game (error {}, result {})", static_cast<int>(err), static_cast<int>(result));
        host_->show_message(tr("load.failed.title"), tr(load_result_key(result)));
    } else {
        // The player's own seat, by name (phase 78).
        out->set_local_player(seat_for(out->game(), player_name()));
    }
    return result;
}

bool App::load_game_as_host(const std::filesystem::path& file) {
    if (!scene_ok_ || !host_) {
        return false;
    }
    std::unique_ptr<GameSession> loaded;
    if (read_save(file, loaded) != GameSession::LoadResult::Ok) {
        return false;
    }
    leave_map();
    close_network();
    if (!ensure_enet()) {
        return false;
    }
    link_ = std::make_unique<net::EnetLink>();
    if (!link_->listen(game_port(), sim::kMaxPlayers - 1, loopback_)) {
        link_.reset();
        host_->show_message(tr("lobby.hostFailed.title"), tr("lobby.hostFailed.body"));
        return false;
    }
    sim::Game& game = loaded->game();
    // Whoever loads it hosts it: the only seat that brings others in.
    game.set_host(loaded->local_player());
    // A game of one player that was never opened: hosting it opens it, to
    // join or to found. One that was open keeps what it allowed, and one
    // of several players that its host closed stays closed.
    if (game.access() == 0 && game.player_count() == 1) {
        sim::Command open;
        open.type = sim::CommandType::SetAccess;
        open.player = game.host();
        open.value = sim::access::kAll;
        game.apply(open);
        (void)game.take_events();
    }
    auto host = std::make_unique<net::NetHost>(*link_, local_info());
    net::GameConfig config;
    config.map = game.map().settings;
    config.shared_town = game.shared_town();
    config.rules = game.rules();
    host->adopt_lobby(&game, config, loaded->local_player());
    net_ = std::move(host);
    saved_session_ = std::move(loaded);
    if (!loopback_) {
        lan_announce_ = std::make_unique<net::LanDiscovery>();
        (void)lan_announce_->announce(game_port());
    }
    log::info("net: hosting a saved game on port {}, as seat {}", game_port(), saved_session_->local_player());
    return true;
}

int App::saved_access() const {
    return saved_session_ ? static_cast<int>(saved_session_->game().access()) : -1;
}

bool App::load_game(const std::filesystem::path& file) {
    if (!scene_ok_ || !host_) {
        return false;
    }
    std::unique_ptr<GameSession> loaded;
    if (read_save(file, loaded) != GameSession::LoadResult::Ok) {
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
    hide_menu_background();
    if (!map_scene_.show(scene_, generated->visuals)) {
        start_menu_background();
        return false;
    }
    generated->visuals = MapVisuals{};
    map_ = std::move(generated);
    const sim::MapData* map = &map_->map;
    const float size = static_cast<float>(map->size);
    camera_.set_mode(CameraMode::Aerial);
    camera_.set_ground([map](float x, float z) { return map_surface_height(*map, x, z); });
    walkers_.set_ground([map](float x, float z) { return map_surface_height(*map, x, z); });
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
        net_->request_speed(speed::snap(speed, speed::kMaxNetwork));  // Pause at once; the rest by vote.
    } else {
        clock_.set_speed(speed);
    }
}

int App::max_game_speed() const {
    // Up to x5 with other players: on the network, or a game of several seats.
    return session_ && (session_->networked() || session_->game().player_count() > 1) ? speed::kMaxNetwork : speed::kMax;
}

std::string App::player_name() const {
    const std::string& name = settings_->settings().gameplay.player_name;
    return net::valid_name(name) ? name : tr("net.defaultName", instance_ + 1);
}

net::LocalInfo App::local_info() const {
    net::LocalInfo info;
    info.game_version = std::string(full_version());
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

bool App::open_game(std::uint8_t access) {
    if (!session_ || session_->networked() || replay_) {
        return false;
    }
    close_network();  // A lobby left behind, if any; the game stays.
    if (!ensure_enet()) {
        return false;
    }
    link_ = std::make_unique<net::EnetLink>();
    if (!link_->listen(game_port(), sim::kMaxPlayers - 1, loopback_)) {
        link_.reset();
        return false;
    }
    sim::Game& game = session_->game();
    // Whoever opens it hosts it, from the seat it plays.
    game.set_host(session_->local_player());
    auto host = std::make_unique<net::NetHost>(*link_, local_info());
    net::GameConfig config;
    config.map = game.map().settings;
    config.shared_town = game.shared_town();
    config.rules = game.rules();
    // The speed of now, up to the network's fastest (x5).
    host->adopt(&game, config, clock_.speed(), session_->local_player());
    net_ = std::move(host);
    session_->attach(net_.get());
    clock_.set_speed(net_->speed());
    if (!loopback_) {
        lan_announce_ = std::make_unique<net::LanDiscovery>();
        (void)lan_announce_->announce(game_port());
    }
    set_access(access);
    log::info("net: the game is open to other players on port {}", game_port());
    return true;
}

void App::watch_game() {
    if (net_ && session_ && session_->networked() && !session_->spectating()) {
        net_->request_watch();  // The lobby's answer turns the view (follow_watching).
    }
}

void App::play_game(int then) {
    if (!net_ || !session_ || !session_->networked() || !session_->spectating()) {
        return;
    }
    play_then_ = session_->seat() == GameSession::kNoSeat ? then : kThenNothing;
    net_->request_seat();
}

// Phase 79. Each frame: the view follows what the host says about this
// machine (a player who watches, or plays again), a spectator who got its
// seat asks the founder it chose, and everybody hears who watches.
void App::follow_watching() {
    if (!net_ || !session_ || !session_->networked() || !host_) {
        shown_watchers_.clear();
        shown_watching_ = 0;
        watch_shown_ = false;
        return;
    }
    sim::Game& game = session_->game();
    const std::uint8_t seat = session_->seat();
    if (seat != GameSession::kNoSeat && seat == net_->local_slot()) {
        if (net_->watching() && !session_->spectating()) {
            session_->watch(seat, true, seat);
        } else if (!net_->watching() && session_->spectating()) {
            session_->play(seat);
        }
    }
    if (ask_town_ >= 0 && seat != GameSession::kNoSeat && !session_->spectating() && seat < game.player_count()) {
        if (game.may_request(seat, static_cast<std::uint8_t>(ask_town_))) {
            sim::Command c;
            c.type = sim::CommandType::RequestJoin;
            c.count = static_cast<std::uint16_t>(ask_town_);
            session_->issue(c);
        }
        ask_town_ = -1;
    }
    // Who watches, as the lobby tells it.
    const net::Lobby& lobby = net_->lobby();
    std::uint16_t watching = 0;
    for (const net::LobbyPlayer& p : lobby.players) {
        watching = static_cast<std::uint16_t>(watching | (p.watching && p.slot < sim::kMaxPlayers ? 1u << p.slot : 0u));
    }
    if (watch_shown_) {
        for (const std::string& name : lobby.watchers) {
            if (std::find(shown_watchers_.begin(), shown_watchers_.end(), name) == shown_watchers_.end()) {
                host_->toast(tr("net.watching", name));
            }
        }
        for (const net::LobbyPlayer& p : lobby.players) {
            const std::uint16_t bit = p.slot < sim::kMaxPlayers ? static_cast<std::uint16_t>(1u << p.slot) : 0;
            if ((watching & bit) != (shown_watching_ & bit)) {
                host_->toast(tr((watching & bit) != 0 ? "net.watching" : "net.playing", p.name));
            }
        }
    }
    shown_watchers_ = lobby.watchers;
    shown_watching_ = watching;
    watch_shown_ = true;
}

void App::set_access(std::uint8_t access) {
    sim::Command c;
    c.type = sim::CommandType::SetAccess;
    c.value = access & sim::access::kAll;
    if (saved_session_) {
        // In the lobby of a saved game nobody else has the game yet.
        c.player = saved_session_->game().host();
        saved_session_->game().apply(c);
        (void)saved_session_->game().take_events();
        return;
    }
    if (!hosting()) {
        return;
    }
    session_->issue(c);
}

bool App::hosting() const {
    return net_ && session_ && session_->networked() && net_->role() == net::NetSession::Role::Host;
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
    saved_session_.reset();
    play_then_ = kThenNothing;
    ask_town_ = -1;
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
        start_map_generation(st->config.map, st->config.rules, false);
    }
    if (std::optional<std::vector<std::uint8_t>> snap = net_->take_snapshot()) {
        apply_snapshot(std::move(*snap));
    }
    // Phase 78: the host started the saved game from its lobby.
    if (saved_session_ && net_->state() == net::NetSession::State::Playing) {
        std::unique_ptr<GameSession> session = std::move(saved_session_);
        leave_map();
        if (!show_map_of(session->game().map())) {
            host_->show_message(tr("load.failed.title"), tr("load.error.damaged"));
            close_network();
            return;
        }
        session->attach(net_.get());
        start_session(std::move(session));
        clock_.set_speed(net_->speed());
        host_->show_game();
    }
    for (const net::NetEvent& e : net_->take_events()) {
        handle_net_event(e);
        if (!net_) {
            return;  // The event closed the network.
        }
    }
    follow_watching();
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
        // Phase 79: a spectator has no seat; it looks at everything, by
        // the first town there is.
        const std::uint8_t slot = net_->local_slot();
        const std::uint8_t view = slot == net::kNoSeat ? seat_for(*game, {}) : slot;
        auto session = std::make_unique<GameSession>(std::move(game), view);
        if (slot == net::kNoSeat) {
            session->watch(view, true, GameSession::kNoSeat);
            session->ui().arrival_open = session->game().open();
        }
        session->attach(net_.get());
        start_session(std::move(session));
    }
    net_->snapshot_loaded(&session_->game());
}

std::string App::town_name(std::uint8_t player) const {
    if (session_ && player < session_->game().player_count() && !session_->game().player(player).name.empty()) {
        return session_->game().player(player).name;
    }
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
        sound_.update(session_->game(), &session_->fog(), camera_.target().x, camera_.target().z, camera_.distance(),
                      host_->game_paused(), dt * std::max(speed::multiplier(speed::kMin), speed::multiplier(clock_.speed())));
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
}

Services::CameraGround App::camera_ground() const {
    CameraGround out;
    out.yaw = camera_.yaw();
    const math::Mat4 inv = math::inverse(camera_view_proj(view_width_, view_height_));
    const float ground = camera_.target().y;
    // Corner rays onto the ground at the camera's target height; one that
    // misses it (toward the sky) stops a few times the distance away.
    const float reach = std::max(50.0f, camera_.distance() * 4.0f);
    constexpr float kCorners[4][2] = {{-1.0f, 1.0f}, {1.0f, 1.0f}, {1.0f, -1.0f}, {-1.0f, -1.0f}};
    for (int i = 0; i < 4; ++i) {
        const math::Vec3 near_point = inv.transform_point({kCorners[i][0], kCorners[i][1], 1.0f});
        const math::Vec3 far_point = inv.transform_point({kCorners[i][0], kCorners[i][1], 0.01f});
        const math::Vec3 dir = math::normalize(far_point - near_point);
        float t = reach;
        if (dir.y < -1e-4f) {
            t = std::min(reach, (ground - near_point.y) / dir.y);
        }
        const math::Vec3 at = near_point + dir * std::max(0.0f, t);
        out.corners[static_cast<std::size_t>(i) * 2] = at.x;
        out.corners[static_cast<std::size_t>(i) * 2 + 1] = at.z;
    }
    return out;
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
            e.kind != sim::Game::Event::Kind::GameOver && e.kind != sim::Game::Event::Kind::TownFounded &&
            e.kind != sim::Game::Event::Kind::GameStarted && e.kind != sim::Game::Event::Kind::AccessChanged &&
            e.kind != sim::Game::Event::Kind::SeatAdded && e.kind != sim::Game::Event::Kind::TownJoined &&
            e.kind != sim::Game::Event::Kind::JoinRequested && e.kind != sim::Game::Event::Kind::JoinRefused &&
            e.kind != sim::Game::Event::Kind::JoinCancelled) {
            continue;
        }
        if (e.kind == sim::Game::Event::Kind::AccessChanged) {
            // Phase 76: everybody hears whether newcomers may come in.
            if (session_->networked()) {
                host_->toast(tr((e.value & sim::access::kOpen) != 0 ? "event.access.open" : "event.access.closed"));
            }
            continue;
        }
        if (e.kind == sim::Game::Event::Kind::SeatAdded) {
            continue;  // The network tells who came.
        }
        // Phase 77: joining a town. Everybody hears who joined whom; the
        // founder, who asks; the one who asked, when it is refused.
        const std::uint8_t me = session_->local_player();
        if (e.kind == sim::Game::Event::Kind::TownJoined) {
            if (e.owner == me) {
                if (const sim::Building* tc = game.buildings().get(game.player(e.other).town_center)) {
                    focus_camera(static_cast<float>(tc->x) + static_cast<float>(tc->width) * 0.5f,
                                 static_cast<float>(tc->z) + static_cast<float>(tc->depth) * 0.5f);
                }
                host_->toast(tr("event.joinAccepted", town_name(e.other)));
            } else {
                host_->notify(tr("event.townJoined", town_name(e.owner), town_name(e.other)), false, 0.0f, 0.0f,
                              game.calendar(), SDL_GetTicksNS());
            }
            continue;
        }
        if (e.kind == sim::Game::Event::Kind::JoinRequested || e.kind == sim::Game::Event::Kind::JoinRefused ||
            e.kind == sim::Game::Event::Kind::JoinCancelled) {
            if (e.kind == sim::Game::Event::Kind::JoinRequested && e.other == me) {
                host_->notify(tr("event.joinRequested", town_name(e.owner)), false, 0.0f, 0.0f, game.calendar(),
                              SDL_GetTicksNS());
                sound_.event(sim::Game::Event::Kind::OfferReceived);
            } else if (e.kind == sim::Game::Event::Kind::JoinRefused && e.owner == me) {
                host_->toast(tr("event.joinRefused", town_name(e.other)));
            }
            continue;
        }
        if (e.kind == sim::Game::Event::Kind::TownFounded || e.kind == sim::Game::Event::Kind::GameStarted) {
            // Phase 74. A town founded: everybody is told, and those who
            // share it go there; where others' towns are stays under the fog.
            const bool mine = e.kind == sim::Game::Event::Kind::TownFounded && e.owner == session_->town();
            const float x = static_cast<float>(e.at.x.raw()) / 65536.0f;
            const float z = static_cast<float>(e.at.z.raw()) / 65536.0f;
            if (mine && e.owner != session_->local_player()) {
                focus_camera(x, z);
            }
            if (mine) {
                const sim::Game::Region r = game.region(session_->town());
                camera_.set_bounds(static_cast<float>(r.x), static_cast<float>(r.z), static_cast<float>(r.x + r.size),
                                   static_cast<float>(r.z + r.size));
            }
            // Alone, the player knows: nothing to tell.
            if (session_->networked() && !(mine && e.owner == session_->local_player())) {
                host_->notify(e.kind == sim::Game::Event::Kind::GameStarted ? tr("event.gameStarted")
                                                                            : tr("event.townFounded", town_name(e.owner)),
                              mine, x, z, game.calendar(), SDL_GetTicksNS());
            }
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
            case sim::Game::Event::Kind::AutoTrade:
                text = tr("event.autoTrade", e.tally.sold, e.tally.sold_gold, e.tally.bought, e.tally.bought_gold);
                break;
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
            case sim::Game::Event::Kind::ExplorerBack:
                text = tr(e.value == 0 ? "event.explorerBack.food" : "event.explorerBack.cold");
                break;
            case sim::Game::Event::Kind::Exhausted: text = tr("event.exhausted", place); break;
            case sim::Game::Event::Kind::Born: text = tr("event.born"); break;
            case sim::Game::Event::Kind::Died: text = tr("event.died"); break;
            case sim::Game::Event::Kind::TownFounded:
            case sim::Game::Event::Kind::GameStarted:
            case sim::Game::Event::Kind::SeatAdded:
            case sim::Game::Event::Kind::TownJoined:
            case sim::Game::Event::Kind::JoinRequested:
            case sim::Game::Event::Kind::JoinRefused:
            case sim::Game::Event::Kind::JoinCancelled:
            case sim::Game::Event::Kind::AccessChanged: break;  // Told above.
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
        case Kind::SeatChanged:
            // Phase 79: a spectator asked to play. With a seat, it plays;
            // without, the game had no room or does not take players.
            if (session_ && e.slot != net::kNoSeat) {
                session_->play(e.slot);
                if (play_then_ == -1) {
                    session_->ui().found_mode = true;
                } else if (play_then_ >= 0) {
                    ask_town_ = play_then_;
                }
            } else if (session_ && play_then_ != kThenNothing) {
                host_->toast(tr("net.noSeat"));
            }
            play_then_ = kThenNothing;
            break;
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
                const std::string text = "SalvaCiudad " + std::string(full_version()) + "\ndesync with seat " +
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
            host_->toast(tr(key, seat_name(e.slot), speed_text(e.value)));
            break;
        }
        case Kind::Rejected: {
            std::string body;
            switch (e.reject.reason) {
                case net::RejectReason::Version:
                    // Same version number, other sources: another build (D-3321).
                    body = version_number(e.reject.host_version) == SC_VERSION_STRING
                               ? tr("net.rejected.build", e.reject.host_version, std::string(full_version()))
                               : tr("net.rejected.version", e.reject.host_version, std::string(full_version()));
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
                case net::RejectReason::Closed: body = tr("net.rejected.closed"); break;
                case net::RejectReason::NotStarted: body = tr("net.rejected.notStarted"); break;
                case net::RejectReason::WatchersFull: body = tr("net.rejected.watchersFull"); break;
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

// --- Map reports (phase 38) ---------------------------------------------------

namespace {

constexpr ui::Color kStrokeColor{235, 40, 40, 255};
constexpr std::array<std::uint8_t, 3> kStrokeRgb{235, 40, 40};
constexpr float kStrokeWidth = 4.0f;  // Pixels at interface scale 1.
// Showing a report: time for the view to fill in (terrain, trees, shadows).
constexpr std::uint64_t kReplaySettleNs = 3'000'000'000ull;
constexpr int kReplaySettleFrames = 30;

std::string local_time_iso() {
    const std::time_t t = std::time(nullptr);
    std::tm local{};
#if defined(_WIN32)
    if (localtime_s(&local, &t) != 0) {
        return {};
    }
#else
    if (localtime_r(&t, &local) == nullptr) {
        return {};
    }
#endif
    return std::format("{:04}-{:02}-{:02}T{:02}:{:02}:{:02}", local.tm_year + 1900, local.tm_mon + 1, local.tm_mday,
                       local.tm_hour, local.tm_min, local.tm_sec);
}

}  // namespace

float App::far_pick() const {
    // A zoomed-out view of the whole map reaches far past the usual 4 km.
    const float size = map_ ? static_cast<float>(map_->map.size) : 0.0f;
    return std::max(4000.0f, camera_.distance() * 4.0f + size * 1.5f);
}

bool App::world_only() const {
    return marking_.active || replay_step_ == ReplayStep::Settling || replay_step_ == ReplayStep::Capture;
}

void App::begin_marking() {
    if (marking_.active || replay_ || !scene_ok_ || !host_ || !map_ || !pack_ ||
        host_->scene_mode() != UiHost::SceneMode::Map || !interactive_scene() || host_->scene_paused()) {
        return;
    }
    marking_ = Marking{};
    marking_.active = true;
    math::Vec3 origin;
    math::Vec3 dir;
    if (mouse_ray(view_width_, view_height_, origin, dir)) {
        if (const std::optional<math::Vec3> hit = ground_hit(map_->map, origin, dir, far_pick())) {
            marking_.cursor =
                report::Cell{static_cast<std::int32_t>(std::floor(hit->x)), static_cast<std::int32_t>(std::floor(hit->z))};
        }
    }
    // A game on this computer waits; a network game goes on for the others.
    if (session_ && !session_->networked()) {
        marking_.speed = clock_.speed();
        clock_.set_speed(0);
    }
    log::info("report: marking");
}

void App::end_marking() {
    if (marking_.speed >= 0 && session_ && !session_->networked()) {
        clock_.set_speed(marking_.speed);
    }
    marking_ = Marking{};
}

void App::marking_key(SDL_Scancode key) {
    if (marking_.capture) {
        return;
    }
    switch (key) {
        case SDL_SCANCODE_RETURN:
        case SDL_SCANCODE_KP_ENTER:
            marking_.capture = true;
            marking_.drawing = false;
            break;
        case SDL_SCANCODE_ESCAPE:
            end_marking();
            log::info("report: cancelled");
            break;
        case SDL_SCANCODE_BACKSPACE:
            if (!marking_.strokes.empty()) {
                marking_.strokes.pop_back();
                marking_.drawing = false;
            }
            break;
        case SDL_SCANCODE_DELETE:
            marking_.strokes.clear();
            marking_.drawing = false;
            break;
        default:
            break;
    }
}

void App::update_marking() {
    if (!marking_.active || marking_.capture) {
        return;
    }
    const float x = input_.mouse_x;
    const float y = input_.mouse_y;
    if (input_.mouse_pressed && x >= 0.0f && y >= 0.0f && marking_.strokes.size() < report::kMaxStrokes) {
        marking_.drawing = true;
        marking_.strokes.push_back(report::Stroke{{{x, y}}, {}});
    } else if (marking_.drawing && input_.mouse_down && x >= 0.0f && y >= 0.0f) {
        auto& points = marking_.strokes.back().screen;
        const auto& last = points.back();
        if (std::hypot(x - last[0], y - last[1]) >= 2.0f && points.size() < report::kMaxStrokePoints) {
            points.push_back({x, y});
        }
    }
    if (marking_.drawing && (input_.mouse_released || !input_.mouse_down)) {
        marking_.drawing = false;
    }
}

void App::draw_marking() {
    if (!marking_.active || marking_.capture) {
        return;  // The capture shows only the world.
    }
    ui::DrawList& dl = ui_.draw();
    const float width = ui_.s(kStrokeWidth);
    for (const report::Stroke& st : marking_.strokes) {
        const auto& p = st.screen;
        if (p.size() == 1) {
            dl.rect({p[0][0] - width * 0.5f, p[0][1] - width * 0.5f, width, width}, kStrokeColor);
        }
        for (std::size_t k = 0; k + 1 < p.size(); ++k) {
            dl.line(p[k][0], p[k][1], p[k + 1][0], p[k + 1][1], width, kStrokeColor);
        }
    }
    // What the keys do, along the top.
    const ui::TextStyle style = ui_.style(ui_.theme().body);
    const float line = ui_.text().line_height(style);
    const float pad = ui_.s(8.0f);
    dl.rect({0.0f, 0.0f, ui_.width(), line + 2.0f * pad}, ui_.theme().background.with_alpha(0.8f));
    ui_.label({pad, pad, ui_.width() - 2.0f * pad, line}, tr("report.help"), style, ui_.theme().text, ui::Align::Center);
}

void App::save_report(const FrameCapture& capture) {
    const std::vector<report::Stroke> strokes = marking_.strokes;
    const std::optional<report::Cell> cursor = marking_.cursor;
    end_marking();
    if (capture.rgb.empty() || !map_ || !pack_) {
        host_->toast(tr("report.failed"));
        return;
    }
    const sim::MapData& map = map_->map;
    report::Report r;
    r.created_at = local_time_iso();
    r.game_version = SC_VERSION_STRING;
    r.build_id = std::string(build_id());
    r.content_hash = pack_->content.hash;
    for (const mods::ModInfo& m : mod_library_.mods()) {
        if (m.loaded) {
            r.mods.push_back(m.manifest.id + " " + mods::version_text(m.manifest.version));
        }
    }
    r.map = map.settings;
    r.generator_version = map.generator_version;
    r.map_checksum = map.checksum();
    r.view.mode = camera_.mode();
    r.view.target = camera_.target();
    r.view.yaw = camera_.yaw();
    r.view.pitch = camera_.pitch();
    r.view.distance = camera_.distance();
    r.view.width = capture.width;
    r.view.height = capture.height;
    if (session_) {
        const sim::Game& g = session_->game();
        r.in_game = true;
        r.view.season = g.calendar().season;
        r.view.snow = static_cast<float>(g.snow()) / static_cast<float>(sim::village::kMaxSnow);
        r.fog = session_->fog().game_mode();
    }
    r.cursor = cursor;
    // Each stroke's cells, through the camera that drew the capture.
    const float far = far_pick();
    const auto hit = [&](float x, float y) -> std::optional<math::Vec3> {
        math::Vec3 origin;
        math::Vec3 dir;
        if (!screen_ray(capture.width, capture.height, x, y, origin, dir)) {
            return std::nullopt;
        }
        return ground_hit(map, origin, dir, far);
    };
    for (report::Stroke st : strokes) {
        st.closed = report::closes(st);
        st.cells = report::cells_under(st, hit);
        r.strokes.push_back(std::move(st));
    }

    const std::filesystem::path base = report::base_dir();
    if (!base.empty()) {
        report::prune(base, report::kKeep - 1);
    }
    const std::filesystem::path dir = base.empty() ? base : report::create_folder(base, report::folder_name_now());
    std::vector<std::uint8_t> marked = capture.rgb;
    report::draw_strokes(marked, capture.width, capture.height, r.strokes, kStrokeWidth * ui_scale(), kStrokeRgb);
    const std::string clean_png = png::encode_rgb(capture.rgb, capture.width, capture.height);
    const std::string marked_png = png::encode_rgb(marked, capture.width, capture.height);
    const std::string json_text = report::to_json(r, map, pack_->content, cursor_names_);
    const bool ok = !dir.empty() && !clean_png.empty() && !marked_png.empty() && !json_text.empty() &&
                    fs::write_file_atomic(dir / "captura_limpia.png", clean_png) == fs::IoError::None &&
                    fs::write_file_atomic(dir / "captura.png", marked_png) == fs::IoError::None &&
                    fs::write_file_atomic(dir / report::kFileName, json_text) == fs::IoError::None;
    if (!ok) {
        log::error("report: could not be saved in {}", text::path_to_utf8(dir));
        host_->toast(tr("report.failed"));
        return;
    }
    log::info("report: saved in {} ({} strokes)", text::path_to_utf8(dir), r.strokes.size());
    host_->toast(tr("report.saved", text::path_to_utf8(dir)));
}

bool App::load_replay(const sim::Content* content) {
    const std::filesystem::path file = replay_dir_ / report::kFileName;
    const fs::ReadResult read = fs::read_file(file, report::kMaxFileBytes);
    report::Replay replay;
    std::string error(fs::io_error_name(read.error));
    if (read.error != fs::IoError::None || !report::parse_replay(read.data, content, replay, error)) {
        log::error("report: cannot show {}: {}", text::path_to_utf8(file), error);
        std::fprintf(stderr, "Cannot show the report %s: %s\n", text::path_to_utf8(file).c_str(), error.c_str());
        return false;
    }
    // A window of its own size, without sound; the settings file is not saved.
    Settings& s = settings_->settings();
    s.display.mode = WindowMode::Windowed;
    s.display.window_width = static_cast<int>(replay.view.width);
    s.display.window_height = static_cast<int>(replay.view.height);
    s.audio.master = 0;
    replay_ = replay;
    log::info("report: showing {} (seed {})", text::path_to_utf8(replay_dir_), replay.map.seed);
    return true;
}

void App::update_replay() {
    if (!replay_ || !host_) {
        return;
    }
    const std::uint64_t now = SDL_GetTicksNS();
    switch (replay_step_) {
        case ReplayStep::Generating:
            if (session_ && map_ && host_->scene_mode() == UiHost::SceneMode::Map) {
                const report::View& v = replay_->view;
                camera_.restore(v.mode, v.target, v.yaw, v.pitch, v.distance);
                clock_.set_speed(0);
                // A crowd to measure with: a square of villagers 2 m apart.
                const auto side = static_cast<std::uint32_t>(std::ceil(std::sqrt(static_cast<double>(v.people))));
                for (std::uint32_t i = 0; i < v.people; ++i) {
                    const float x = v.target.x + (static_cast<float>(i % side) - static_cast<float>(side) * 0.5f) * 2.0f;
                    const float z = v.target.z + (static_cast<float>(i / side) - static_cast<float>(side) * 0.5f) * 2.0f;
                    (void)walkers_.add_villager({x, 0.0f, z}, std::nullopt);
                }
                replay_step_ = ReplayStep::Settling;
                replay_since_ns_ = now;
                replay_frames_ = 0;
            } else if (const MapGenStatus::State st = map_generation_status().state;
                       !map_ && st != MapGenStatus::State::Running && st != MapGenStatus::State::Done) {
                log::error("report: the map could not be made");
                replay_step_ = ReplayStep::Done;
                replay_exit_code_ = 1;
                running_ = false;
            }
            break;
        case ReplayStep::Settling:
            if (now - replay_since_ns_ >= kReplaySettleNs / 2) {
                if (replay_measure_ns_ == 0) {
                    replay_measure_ns_ = now;
                    replay_measured_ = 0;
                } else {
                    ++replay_measured_;
                    replay_measured_ns_ = now - replay_measure_ns_;
                }
            }
            if (++replay_frames_ >= kReplaySettleFrames && now - replay_since_ns_ >= kReplaySettleNs) {
                replay_step_ = ReplayStep::Capture;
            }
            break;
        default:
            break;
    }
}

void App::finish_replay(const FrameCapture& capture) {
    replay_step_ = ReplayStep::Done;
    running_ = false;
    const std::string stem = "despues_" + report::folder_name_now();
    const std::string image = png::encode_rgb(capture.rgb, capture.width, capture.height);
    // What differs from when the report was made.
    std::string notes;
    if (map_ && replay_->generator_version != map_->map.generator_version) {
        notes += std::format("Generator version: {} in the report, {} now.\n", replay_->generator_version,
                             map_->map.generator_version);
    }
    if (pack_ && replay_->content_hash != pack_->content.hash) {
        notes += "The mods (or their files) are not the same as in the report.\n";
    }
    if (replay_->build_id != build_id()) {
        notes += std::format("Build: {} in the report, {} now.\n", replay_->build_id, build_id());
    }
    if (capture.width != replay_->view.width || capture.height != replay_->view.height) {
        notes += std::format("Window: {}x{} in the report, {}x{} now.\n", replay_->view.width, replay_->view.height,
                             capture.width, capture.height);
    }
    if (map_) {
        notes += std::format("Map checksum now: {:016x}\n", map_->map.checksum());
    }
    if (replay_measured_ > 0 && replay_measured_ns_ > 0) {
        const double seconds = static_cast<double>(replay_measured_ns_) / 1e9;
        const render::RenderStats& st = scene_.stats();
        notes += std::format("Frames: {} in {:.2f} s, {:.1f} FPS; characters drawn {} of {} ({} far)\n", replay_measured_,
                             seconds, static_cast<double>(replay_measured_) / seconds, st.characters_drawn,
                             st.characters_total, st.characters_far);
        notes += std::format("Objects drawn: {} of {} ({} in their far version); {:.2f} M triangles; {} draw calls; "
                             "culling {:.2f} ms\n",
                             st.instances_drawn, st.instances_total, st.instances_far,
                             static_cast<double>(st.triangles) / 1e6, st.draw_calls, static_cast<double>(st.cull_ms));
    }
    const bool ok = !image.empty() && fs::write_file_atomic(replay_dir_ / (stem + ".png"), image) == fs::IoError::None &&
                    fs::write_file_atomic(replay_dir_ / (stem + ".txt"), notes) == fs::IoError::None;
    if (!ok) {
        log::error("report: could not save the new screenshot in {}", text::path_to_utf8(replay_dir_));
        replay_exit_code_ = 1;
        return;
    }
    log::info("report: saved {}.png", stem);
}

}  // namespace sc
