#include "game/app.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
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
#include "version.h"

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

// The sample village on a generated map: villagers in the square in the
// middle of a ring of houses (decision D-617).
constexpr std::size_t kSampleVillagers = 40;
constexpr float kSampleVillageRadius = 11.0f;

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

App::App() : text_(atlas_), ui_(text_) {}

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
        scene_ok_ = test_scene_.load(scene_, paths_->game_data_dir() / "models" / "props", kTestSceneInstances);
        if (scene_ok_ && crowd_.load(scene_, paths_->game_data_dir() / "models" / "characters")) {
            crowd_.spawn(kTestCrowd, 2026, kTestCrowdRadius);
        }
    }
    if (scene_ok_ && !map_scene_.load_models(scene_, paths_->game_data_dir() / "models" / "props")) {
        log::warn("map: no feature models; maps will show bare ground");
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

void App::open_data_folder() {
    std::string url = "file:///" + text::path_to_utf8(paths_->user_dir);
    std::replace(url.begin(), url.end(), '\\', '/');
    if (!SDL_OpenURL(url.c_str())) {
        log::warn("could not open the data folder: {}", SDL_GetError());
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
        case SDL_EVENT_KEY_DOWN: {
            input_.keys.push_back(event.key.scancode);
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
            crowd_.update(scene_, dt);
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
        if (scene_drawn && host_->scene_mode() == UiHost::SceneMode::Map) {
            draw_start_markers(frame.width, frame.height);
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
        debug_info_.sim_tick = sim_.tick();
        debug_info_.sim_hash = sim_.last_hash();
        debug_info_.sim_entities = sim_.world().registry().alive_count();
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
    input_.wheel = 0.0f;
    input_.keys.clear();

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

    const int ticks = clock_.advance(static_cast<std::int64_t>(elapsed));
    for (int i = 0; i < ticks; ++i) {
        sim_.step();
    }

    const float dt = static_cast<float>(elapsed) * 1e-9f;
    update_frame_stats(dt);
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

void App::start_map_generation(const sim::MapSettings& settings) {
    log::info("map: generating seed {} size {} with {} start(s)", settings.seed, sim::map_cells(settings.size),
              settings.players);
    map_job_.start(settings);
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
    // A sample village at the first start, to judge sizes (until phase 8).
    const math::Vec3 start{sx, map_surface_height(*map, sx, sz), sz};
    map_scene_.show_sample_village(scene_, *map, start);
    crowd_.set_area(start, [map](float x, float z) { return map_surface_height(*map, x, z); });
    crowd_.spawn(kSampleVillagers, 7, kSampleVillageRadius);
    selected_.reset();
    following_ = false;
    return true;
}

void App::leave_map() {
    if (!map_) {
        return;
    }
    dev_tools_.reset();
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
    ctx.scene = on_map ? &map_scene_ : nullptr;
    ctx.renderer = &scene_;
    ctx.crowd = &crowd_;
    ctx.camera = &camera_;
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
