#include "viewer/viewer_app.h"

#include <algorithm>
#include <cfloat>
#include <cmath>
#include <cstdio>

#include <imgui.h>
#include <imgui_internal.h>
#include <imgui_impl_sdl3.h>
#include <imgui_impl_sdlgpu3.h>

#include <SDL3/SDL_filesystem.h>
#include <SDL3/SDL_init.h>
#include <SDL3/SDL_locale.h>
#include <SDL3/SDL_messagebox.h>
#include <SDL3/SDL_timer.h>

#include "core/file_io.h"
#include "core/log.h"
#include "core/text.h"
#include "embedded/lang_en.h"
#include "game/builtin_models.h"
#include "game/map_scene.h"
#include "game/test_scene.h"
#include "i18n/translator.h"
#include "version.h"

namespace sc::viewer {

using i18n::tr;

namespace {

constexpr int kWindowWidth = 1600;
constexpr int kWindowHeight = 900;
constexpr float kPanelWidth = 340.0f;  // Each side panel, before the UI scale.
constexpr float kFontSize = 17.0f;
constexpr float kGroundHalfSize = 150.0f;
constexpr float kReloadCheckSeconds = 0.5f;
constexpr float kStatusSeconds = 6.0f;
constexpr float kGap = 1.5f;  // Meters between models side by side.

// The reference villager beside what is shown.
const std::string kReferenceBody = sim::race_body_file("human", false);

// Hats, beards and aprons are shown on a body: on which one and where.
struct AccessoryPlace {
    std::string_view path;
    const char* bone;
    bool female;
};
constexpr AccessoryPlace kAccessories[] = {
    {builtin_models::kHats[0], builtin_models::kHeadBone, false},
    {builtin_models::kHats[1], builtin_models::kHeadBone, false},
    {builtin_models::kBeard, builtin_models::kHeadBone, false},
    {builtin_models::kApronMale, builtin_models::kHipsBone, false},
    {builtin_models::kApronFemale, builtin_models::kHipsBone, true},
};

std::string_view builtin_base_language() {
    return {reinterpret_cast<const char*>(kLangEn), kLangEn_size};
}

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

// A flat ground with a line every meter and a stronger one every 5 m.
render::ModelData make_grid_ground(float half_size) {
    render::ModelData m;
    constexpr float kRepeat = 5.0f;  // Meters per texture repeat.
    for (const float z : {-half_size, half_size}) {
        for (const float x : {-half_size, half_size}) {
            m.vertices.push_back({x, 0.0f, z, 0.0f, 1.0f, 0.0f, x / kRepeat, z / kRepeat});
        }
    }
    m.indices = {0, 2, 1, 1, 2, 3};
    render::ModelTexture tex;
    constexpr int kSize = 160;  // 32 texels per meter.
    tex.width = tex.height = kSize;
    for (int y = 0; y < kSize; ++y) {
        for (int x = 0; x < kSize; ++x) {
            const bool major = x < 2 || y < 2;
            const bool minor = x % 32 == 0 || y % 32 == 0;
            const std::uint8_t v = major ? 96 : minor ? 128 : 170;
            tex.rgba.insert(tex.rgba.end(), {v, static_cast<std::uint8_t>(v + 8), static_cast<std::uint8_t>(v - 6), 255});
        }
    }
    m.textures.push_back(std::move(tex));
    render::ModelMaterial mat;
    mat.texture = 0;
    m.materials.push_back(mat);
    m.primitives.push_back({0, static_cast<std::uint32_t>(m.indices.size()), 0});
    m.bounds_min = {-half_size, 0.0f, -half_size};
    m.bounds_max = {half_size, 0.0f, half_size};
    m.radius = half_size * 1.5f;
    return m;
}

std::optional<render::ModelData> read_model(const std::filesystem::path& file, std::string& error) {
    const fs::ReadResult r = fs::read_file(file, render::model_limits::kMaxFileBytes);
    if (r.error != fs::IoError::None) {
        error = "cannot read the file";
        return std::nullopt;
    }
    render::ModelLoadResult m = render::load_glb({reinterpret_cast<const std::uint8_t*>(r.data.data()), r.data.size()});
    if (!m.ok) {
        error = m.error;
        return std::nullopt;
    }
    return std::move(m.model);
}

const AccessoryPlace* accessory_place(std::string_view mod, std::string_view path) {
    if (mod != mods::kCoreModId) {
        return nullptr;
    }
    for (const AccessoryPlace& a : kAccessories) {
        if (a.path == path) {
            return &a;
        }
    }
    return nullptr;
}

bool contains_text(std::string_view haystack, std::string_view needle) {
    if (needle.empty()) {
        return true;
    }
    const auto low = [](char c) { return c >= 'A' && c <= 'Z' ? static_cast<char>(c - 'A' + 'a') : c; };
    return std::search(haystack.begin(), haystack.end(), needle.begin(), needle.end(),
                       [&](char a, char b) { return low(a) == low(b); }) != haystack.end();
}

std::string file_name(std::string_view path) {
    const std::size_t slash = path.rfind('/');
    return std::string(slash == std::string_view::npos ? path : path.substr(slash + 1));
}

}  // namespace

// --- Camera -----------------------------------------------------------------

math::Vec3 OrbitCamera::eye() const {
    const float c = std::cos(pitch);
    return target + math::Vec3{c * std::sin(yaw), std::sin(pitch), c * std::cos(yaw)} * distance;
}

math::Mat4 OrbitCamera::view() const {
    return math::look_at(eye(), target, {0.0f, 1.0f, 0.0f});
}

void OrbitCamera::rotate(float dx_px, float dy_px) {
    yaw -= dx_px * 0.008f;
    pitch = std::clamp(pitch + dy_px * 0.006f, math::radians(-10.0f), math::radians(85.0f));
}

void OrbitCamera::pan(float dx_px, float dy_px, float view_height_px) {
    // One pixel moves the point as much as it covers on screen.
    const float per_px = 2.0f * distance * std::tan(math::radians(kFovY) * 0.5f) / std::max(1.0f, view_height_px);
    const math::Vec3 forward = math::normalize(target - eye());
    const math::Vec3 right = math::normalize(math::cross(forward, {0.0f, 1.0f, 0.0f}));
    const math::Vec3 up = math::cross(right, forward);
    target = target - right * (dx_px * per_px) + up * (dy_px * per_px);
}

void OrbitCamera::zoom(float notches) {
    distance = std::clamp(distance * std::pow(0.88f, notches), 0.5f, 400.0f);
}

// --- Application --------------------------------------------------------------

ViewerApp::ViewerApp() = default;
ViewerApp::~ViewerApp() = default;

int ViewerApp::run() {
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

void ViewerApp::load_languages() {
    const char* base = SDL_GetBasePath();
    const std::filesystem::path lang_dir =
        base != nullptr ? text::path_from_utf8(base) / "data" / "lang" : std::filesystem::path{};
    (void)i18n::translator().load(lang_dir, builtin_base_language());
}

bool ViewerApp::init() {
    (void)SDL_SetAppMetadata("SalvaCiudad model viewer", SC_VERSION_STRING, "io.github.salva.salvaciudad.models");
    load_languages();
    const std::string language = i18n::translator().resolve("auto", preferred_languages());
    (void)i18n::translator().set_language(language);
    if (!SDL_Init(SDL_INIT_VIDEO | SDL_INIT_EVENTS)) {
        std::fprintf(stderr, "SDL_Init failed: %s\n", SDL_GetError());
        return false;
    }
    sdl_ready_ = true;
    paths_ = resolve_data_paths();
    if (!paths_) {
        (void)SDL_ShowSimpleMessageBox(SDL_MESSAGEBOX_ERROR, tr("viewer.title").c_str(),
                                       tr("error.fatal.dataFolder").c_str(), nullptr);
        return false;
    }
    // Its own log folder: the game's log must not be rotated by the viewer.
    log::Options log_options;
#ifndef NDEBUG
    log_options.echo_to_stderr = true;
    log_options.min_level = log::Level::Debug;
#endif
    (void)log::open(paths_->logs_dir() / "viewer", log_options);
    log::info("model viewer {} starting", SC_VERSION_STRING);
    // Again, to log the language files now that the log is open.
    load_languages();
    (void)i18n::translator().set_language(language);

    window_ = SDL_CreateWindow(tr("viewer.title").c_str(), kWindowWidth, kWindowHeight,
                               SDL_WINDOW_RESIZABLE | SDL_WINDOW_HIGH_PIXEL_DENSITY);
    if (window_ == nullptr || !gpu_.create(window_, true)) {
        (void)SDL_ShowSimpleMessageBox(SDL_MESSAGEBOX_ERROR, tr("viewer.title").c_str(),
                                       tr("error.fatal.gpu").c_str(), window_);
        return false;
    }
    GraphicsSettings graphics;
    graphics.apply_preset(QualityPreset::Ultra);
    scene_ok_ = scene_.create(gpu_, graphics);
    if (!scene_ok_) {
        (void)SDL_ShowSimpleMessageBox(SDL_MESSAGEBOX_ERROR, tr("viewer.title").c_str(),
                                       tr("error.fatal.gpu").c_str(), window_);
        return false;
    }
    if (!init_imgui()) {
        return false;
    }
    // The first framing needs the view's size.
    int width = 0;
    int height = 0;
    if (SDL_GetWindowSizeInPixels(window_, &width, &height) && width > 0 && height > 0) {
        view_width_ = static_cast<std::uint32_t>(width);
        view_height_ = static_cast<std::uint32_t>(height);
    }
    const std::vector<render::Palette> palettes = make_villager_palettes();
    palette_count_ = static_cast<std::uint32_t>(palettes.size());
    scene_.set_palettes(palettes);
    if (!scene_.add_model(make_grid_ground(kGroundHalfSize), ground_)) {
        ground_ = kNone;
    }
    load_catalog();
    return true;
}

bool ViewerApp::init_imgui() {
    IMGUI_CHECKVERSION();
    ImGui::CreateContext();
    ImGuiIO& io = ImGui::GetIO();
    // Never write imgui.ini next to the program or in the working folder.
    io.IniFilename = nullptr;
    io.LogFilename = nullptr;
    ImGui::StyleColorsDark();
    // The game's interface font, which has every letter of every language.
    const fs::ReadResult font =
        fs::read_file(paths_->game_data_dir() / "fonts" / "ui" / "AlegreyaSans-Regular.ttf", 8u * 1024u * 1024u);
    if (font.error == fs::IoError::None) {
        font_data_ = font.data;
        ImFontConfig config;
        config.FontDataOwnedByAtlas = false;
        (void)io.Fonts->AddFontFromMemoryTTF(font_data_.data(), static_cast<int>(font_data_.size()), kFontSize,
                                             &config);
    } else {
        log::warn("viewer: interface font unavailable; using ImGui's own");
    }
    if (!ImGui_ImplSDL3_InitForSDLGPU(window_)) {
        log::error("viewer: ImGui SDL3 backend failed");
        return false;
    }
    ImGui_ImplSDLGPU3_InitInfo init{};
    init.Device = gpu_.device();
    init.ColorTargetFormat = gpu_.swapchain_format();
    init.MSAASamples = SDL_GPU_SAMPLECOUNT_1;
    if (!ImGui_ImplSDLGPU3_Init(&init)) {
        log::error("viewer: ImGui GPU backend failed");
        ImGui_ImplSDL3_Shutdown();
        return false;
    }
    imgui_ok_ = true;
    apply_ui_scale();
    return true;
}

void ViewerApp::apply_ui_scale() {
    float scale = SDL_GetWindowDisplayScale(window_);
    if (!(scale > 0.0f)) {
        scale = 1.0f;
    }
    if (scale == ui_scale_) {
        return;
    }
    ui_scale_ = scale;
    ImGuiStyle& style = ImGui::GetStyle();
    style = ImGuiStyle();
    ImGui::StyleColorsDark(&style);
    style.WindowRounding = 4.0f;
    style.FrameRounding = 3.0f;
    style.ScaleAllSizes(scale);
    style.FontScaleDpi = scale;
}

void ViewerApp::shutdown() {
    if (gpu_.device() != nullptr) {
        (void)SDL_WaitForGPUIdle(gpu_.device());
    }
    if (imgui_ok_) {
        ImGui_ImplSDLGPU3_Shutdown();
        ImGui_ImplSDL3_Shutdown();
        imgui_ok_ = false;
    }
    if (ImGui::GetCurrentContext() != nullptr) {
        ImGui::DestroyContext();
    }
    scene_.destroy();
    gpu_.destroy();
    if (window_ != nullptr) {
        SDL_DestroyWindow(window_);
        window_ = nullptr;
    }
    if (sdl_ready_) {
        SDL_Quit();
        sdl_ready_ = false;
    }
    log::info("model viewer stopped");
    log::close();
}

std::filesystem::path ViewerApp::builtin_mods_dir() const {
#ifdef SC_VIEWER_SOURCE_DATA
    // Built from a source tree: read the mods where the Blender scripts
    // write them, so a model shows as soon as its script runs again.
    std::filesystem::path source = text::path_from_utf8(SC_VIEWER_SOURCE_DATA) / "mods";
    source.make_preferred();
    std::error_code ec;
    if (std::filesystem::is_directory(source / mods::kCoreModId, ec)) {
        return source;
    }
#endif
    return paths_->game_data_dir() / "mods";
}

void ViewerApp::load_catalog() {
    const mods::Version game{SC_VERSION_MAJOR, SC_VERSION_MINOR, SC_VERSION_PATCH};
    mods_dir_ = builtin_mods_dir();
    library_.scan(mods_dir_, paths_->user_mods_dir(), game);
    if (library_.find(mod_) == nullptr) {
        mod_ = mods::kCoreModId;
    }
    library_.select(mod_ == mods::kCoreModId ? std::vector<std::string>{} : std::vector<std::string>{mod_});
    pack_ = std::make_unique<mods::BuildResult>(library_.build());
    // The mods' texts, for the names of the definitions.
    auto& t = i18n::translator();
    t.clear_mod_texts();
    for (const std::filesystem::path& file : pack_->language_files) {
        const fs::ReadResult r = fs::read_file(file, i18n::catalog_limits::kMaxFileBytes);
        if (r.error == fs::IoError::None) {
            (void)t.add_mod_texts(r.data, text::path_to_utf8(file));
        }
    }
    std::vector<ModFolder> folders;
    for (const mods::ModInfo& m : library_.mods()) {
        if (m.manifest.id == mods::kCoreModId || m.manifest.id == mod_) {
            folders.push_back({m.manifest.id, m.dir});
        }
    }
    catalog_ = build_catalog(folders, pack_->model_refs);
    open_groups_.clear();  // Group numbers changed.
    log::info("viewer: {} models in {} groups for '{}' from {}, {} unused, {} missing", catalog_.models.size(),
              catalog_.groups.size(), mod_, text::path_to_utf8(mods_dir_), catalog_.unused_count(),
              catalog_.missing.size());
    // The first type of the list, as it is shown.
    std::optional<std::size_t> first;
    for (const CatalogRow& row : catalog_rows()) {
        if (row.kind == RowKind::Group) {
            first = row.group;
            break;
        }
    }
    select(first ? Selection{first, std::nullopt} : Selection{});
    frame_camera();
}

// --- Loop -------------------------------------------------------------------

void ViewerApp::frame() {
    SDL_Event event;
    const bool minimized = (SDL_GetWindowFlags(window_) & SDL_WINDOW_MINIMIZED) != 0;
    if (minimized && SDL_WaitEventTimeout(&event, 100)) {
        handle_event(event);
    }
    while (SDL_PollEvent(&event)) {
        handle_event(event);
    }
    const std::uint64_t now = SDL_GetTicksNS();
    const float dt = std::min(0.1f, static_cast<float>(now - last_frame_ns_) * 1e-9f);
    last_frame_ns_ = now;
    check_reload(dt);
    if (!minimized) {
        render_frame(dt);
    }
}

void ViewerApp::handle_event(const SDL_Event& event) {
    if (imgui_ok_) {
        ImGui_ImplSDL3_ProcessEvent(&event);
    }
    const bool ui_mouse = imgui_ok_ && ImGui::GetIO().WantCaptureMouse;
    const bool ui_keys = imgui_ok_ && ImGui::GetIO().WantTextInput;
    switch (event.type) {
        case SDL_EVENT_QUIT:
        case SDL_EVENT_WINDOW_CLOSE_REQUESTED: running_ = false; break;
        case SDL_EVENT_WINDOW_DISPLAY_SCALE_CHANGED: apply_ui_scale(); break;
        case SDL_EVENT_MOUSE_BUTTON_DOWN:
            if (!ui_mouse) {
                rotating_ = rotating_ || event.button.button == SDL_BUTTON_LEFT;
                panning_ = panning_ || event.button.button == SDL_BUTTON_RIGHT ||
                           event.button.button == SDL_BUTTON_MIDDLE;
            }
            break;
        case SDL_EVENT_MOUSE_BUTTON_UP:
            if (event.button.button == SDL_BUTTON_LEFT) {
                rotating_ = false;
            } else {
                panning_ = false;
            }
            break;
        case SDL_EVENT_MOUSE_MOTION:
            if (rotating_) {
                camera_.rotate(event.motion.xrel, event.motion.yrel);
            } else if (panning_) {
                // Motion is in window points; the view height in pixels.
                const float density = SDL_GetWindowPixelDensity(window_) > 0.0f ? SDL_GetWindowPixelDensity(window_) : 1.0f;
                camera_.pan(event.motion.xrel * density, event.motion.yrel * density,
                            static_cast<float>(view_height_));
            }
            break;
        case SDL_EVENT_MOUSE_WHEEL:
            if (!ui_mouse) {
                camera_.zoom(event.wheel.y);
            }
            break;
        case SDL_EVENT_KEY_DOWN:
            if (ui_keys) {
                break;
            }
            // The catalog list: W A S D or the arrows (also the keypad's),
            // held down to repeat.
            if (catalog_tab_) {
                switch (event.key.key) {
                    case SDLK_UP:
                    case SDLK_KP_8:
                    case SDLK_W: navigate_catalog(NavKey::Up); break;
                    case SDLK_DOWN:
                    case SDLK_KP_2:
                    case SDLK_S: navigate_catalog(NavKey::Down); break;
                    case SDLK_LEFT:
                    case SDLK_KP_4:
                    case SDLK_A: navigate_catalog(NavKey::Left); break;
                    case SDLK_RIGHT:
                    case SDLK_KP_6:
                    case SDLK_D: navigate_catalog(NavKey::Right); break;
                    default: break;
                }
            }
            if (!event.key.repeat) {
                if (event.key.key == SDLK_F) {
                    frame_camera();
                } else if (event.key.key == SDLK_F5) {
                    load_catalog();
                }
            }
            break;
        default: break;
    }
}

void ViewerApp::render_frame(float dt) {
    GpuFrame frame;
    if (!gpu_.begin_frame(frame)) {
        return;
    }
    if (frame.target != nullptr) {
        view_width_ = std::max(1u, frame.width);
        view_height_ = std::max(1u, frame.height);
        update_scene(dt);
        render::SceneView view;
        view.view = camera_.view();
        view.eye = camera_.eye();
        view.fov_y = math::radians(kFovY);
        view.near_z = std::clamp(camera_.distance * 0.01f, 0.05f, 1.0f);
        view.aspect = static_cast<float>(view_width_) / static_cast<float>(view_height_);
        view.time = anim_time_;
        view.snow = snowy_ ? 1.0f : 0.0f;
        const bool scene_drawn = scene_.render(frame, view, render::Lighting{});

        ImGui_ImplSDLGPU3_NewFrame();
        ImGui_ImplSDL3_NewFrame();
        ImGui::NewFrame();
        const ImVec2 size = ImGui::GetIO().DisplaySize;
        draw_ui(size.x, size.y);
        ImGui::Render();
        ImDrawData* draw = ImGui::GetDrawData();
        ImGui_ImplSDLGPU3_PrepareDrawData(draw, frame.cmd);
        SDL_GPUColorTargetInfo target{};
        target.texture = frame.target;
        target.clear_color = SDL_FColor{0.1f, 0.1f, 0.12f, 1.0f};
        target.load_op = scene_drawn ? SDL_GPU_LOADOP_LOAD : SDL_GPU_LOADOP_CLEAR;
        target.store_op = SDL_GPU_STOREOP_STORE;
        SDL_GPURenderPass* pass = SDL_BeginGPURenderPass(frame.cmd, &target, 1, nullptr);
        if (pass != nullptr) {
            ImGui_ImplSDLGPU3_RenderDrawData(draw, frame.cmd, pass);
            SDL_EndGPURenderPass(pass);
        }
    }
    (void)gpu_.end_frame(frame);
}

// --- Scene ------------------------------------------------------------------

ViewerApp::Loaded& ViewerApp::load_model(const std::string& mod, const std::string& path,
                                         const std::filesystem::path& file) {
    const std::string key = mod + "/" + path;
    const auto found = loaded_.find(key);
    if (found != loaded_.end()) {
        return found->second;
    }
    Loaded& out = loaded_[key];
    std::error_code ec;
    out.time = std::filesystem::last_write_time(file, ec);
    out.bytes = std::filesystem::file_size(file, ec);
    const std::optional<render::ModelData> data = read_model(file, out.error);
    if (!data) {
        log::warn("viewer: {} rejected: {}", key, out.error);
        return out;
    }
    out.stats = model_stats(*data);
    out.bounds_min = data->bounds_min;
    out.bounds_max = data->bounds_max;
    if (accessory_place(mod, path) != nullptr) {
        out.ok = load_accessory(out, *data, path);
    } else if (data->skinned()) {
        out.ok = !data->clips.empty() && scene_.add_skinned_model(*data, out.body);
        out.clip = data->clip_index("idle") >= 0 ? static_cast<std::uint32_t>(data->clip_index("idle")) : 0u;
        if (!out.ok && data->clips.empty()) {
            out.error = "a skeleton without animations";
        }
    } else {
        out.ok = scene_.add_model(*data, out.model);
    }
    if (!out.ok && out.error.empty()) {
        out.error = "the GPU refused it";
    }
    return out;
}

bool ViewerApp::load_accessory(Loaded& out, const render::ModelData& data, const std::string& path) {
    const AccessoryPlace* place = accessory_place(mods::kCoreModId, path);
    const std::filesystem::path core = library_.find(mods::kCoreModId) != nullptr
                                           ? library_.find(mods::kCoreModId)->dir
                                           : std::filesystem::path{};
    std::string error;
    const std::optional<render::ModelData> body =
        read_model(core / sim::race_body_file("human", place->female), error);
    std::uint32_t bit = 0;
    if (!body || body->clip_index("idle") < 0 || !scene_.add_skinned_model(*body, out.body) ||
        !scene_.add_accessory(data, out.body, place->bone, bit)) {
        out.error = "no body to wear it";
        return false;
    }
    out.accessories = 1u << bit;
    out.clip = static_cast<std::uint32_t>(body->clip_index("idle"));
    // The body counts in the size, so it stands where the accessory is shown.
    out.bounds_min = body->bounds_min;
    out.bounds_max = body->bounds_max;
    return true;
}

std::vector<std::size_t> ViewerApp::shown_models() const {
    if (selection_.model) {
        return {*selection_.model};
    }
    if (selection_.group && *selection_.group < catalog_.groups.size()) {
        return catalog_.groups[*selection_.group].models;
    }
    return {};
}

void ViewerApp::select(Selection selection) {
    selection_ = selection;
    clip_ = -1;
    if (selection.group && *selection.group < catalog_.groups.size()) {
        const CatalogGroup& g = catalog_.groups[*selection.group];
        cursor_ = {RowKind::Group, g.category, *selection.group, 0, g.models.size() > 1, false};
        category_open_[static_cast<std::size_t>(g.category)] = true;
        if (selection.model && g.models.size() > 1) {
            cursor_.kind = RowKind::Model;
            cursor_.model = *selection.model;
            open_groups_.insert(*selection.group);
        }
        scroll_to_cursor_ = true;
    }
    layout_scene();
}

void ViewerApp::layout_scene() {
    placed_.clear();
    std::vector<std::size_t> models = shown_models();
    // The row: each model beside the previous one, with the reference
    // villager first.
    float x = 0.0f;
    const auto place = [&](std::size_t model, const Loaded& l) {
        const float width = std::max(0.3f, l.bounds_max.x - l.bounds_min.x);
        placed_.push_back({model, {x - l.bounds_min.x, 0.0f, 0.0f}});
        x += width + kGap;
    };
    for (const std::size_t m : models) {
        const CatalogModel& cm = catalog_.models[m];
        const Loaded& l = load_model(cm.mod, cm.path, cm.file);
        if (l.ok) {
            place(m, l);
        }
    }
    // Center the row on the origin.
    const float shift = (x - kGap) * 0.5f;
    for (Placed& p : placed_) {
        p.position.x -= shift;
    }
}

void ViewerApp::frame_camera() {
    math::Vec3 lo{-1.0f, 0.0f, -1.0f};
    math::Vec3 hi{1.0f, 1.8f, 1.0f};
    bool any = false;
    for (const Placed& p : placed_) {
        const CatalogModel& cm = catalog_.models[p.model];
        const auto it = loaded_.find(cm.mod + "/" + cm.path);
        if (it == loaded_.end() || !it->second.ok) {
            continue;
        }
        const math::Vec3 a = p.position + it->second.bounds_min;
        const math::Vec3 b = p.position + it->second.bounds_max;
        if (!any) {
            lo = a;
            hi = b;
            any = true;
        }
        lo = {std::min(lo.x, a.x), std::min(lo.y, a.y), std::min(lo.z, a.z)};
        hi = {std::max(hi.x, b.x), std::max(hi.y, b.y), std::max(hi.z, b.z)};
    }
    if (show_reference_ && any) {
        lo.x -= 1.4f;  // The reference villager.
        hi.y = std::max(hi.y, 1.8f);
    }
    const math::Vec3 center = (lo + hi) * 0.5f;
    const float radius = std::max(0.5f, math::length(hi - lo) * 0.5f);
    camera_.target = center;
    camera_.yaw = -0.55f;  // From the front left, where the reference villager stands.
    camera_.pitch = 0.3f;
    // The side panels cover part of the window: fit into the middle.
    const float aspect = static_cast<float>(view_width_) / static_cast<float>(view_height_);
    const float free = std::clamp(1.0f - 2.0f * kPanelWidth * ui_scale_ / static_cast<float>(view_width_), 0.3f, 1.0f);
    const float half_fov = math::radians(kFovY) * 0.5f;
    const float fit_v = radius / std::sin(half_fov);
    const float fit_h = radius / std::sin(std::atan(std::tan(half_fov) * aspect * free));
    camera_.distance = std::clamp(std::max(fit_v, fit_h) * 1.05f, 1.0f, 400.0f);
}

math::Vec3 ViewerApp::tint_for(const CatalogModel& m, std::size_t index) const {
    if (m.category != Category::Trees && m.category != Category::Props) {
        return {1.0f, 1.0f, 1.0f};
    }
    bool evergreen = false;
    for (const Use& u : m.uses) {
        for (const sim::SpeciesDef& sp : pack_->content.flora.species) {
            evergreen = evergreen || (u.kind == "species" && sp.id == u.id && sp.evergreen);
        }
    }
    const bool tree = m.category == Category::Trees;
    return season_tint(1.0f, tree, evergreen, static_cast<std::uint32_t>(index), static_cast<sim::Season>(season_),
                       snowy_);
}

void ViewerApp::update_scene(float dt) {
    anim_time_ += dt;
    if (turntable_) {
        spin_ += dt * 0.4f;
    }
    for (const render::ModelId id : shown_rigid_) {
        scene_.set_instances(id, {});
    }
    shown_rigid_.clear();
    characters_.clear();
    if (ground_ != kNone) {
        const render::Instance g{};
        scene_.set_instances(ground_, show_ground_ ? std::span<const render::Instance>(&g, 1)
                                                   : std::span<const render::Instance>());
    }
    for (std::size_t i = 0; i < placed_.size(); ++i) {
        const Placed& p = placed_[i];
        const CatalogModel& cm = catalog_.models[p.model];
        const Loaded& l = loaded_[cm.mod + "/" + cm.path];
        if (!l.ok) {
            continue;
        }
        if (l.model != kNone) {
            render::Instance inst;
            inst.position = p.position;
            inst.yaw = spin_;
            inst.tint = tint_for(cm, i);
            scene_.set_instances(l.model, {&inst, 1});
            shown_rigid_.push_back(l.model);
        } else if (l.body != kNone) {
            render::CharacterInstance c;
            c.position = p.position;
            c.yaw = spin_;
            c.body = l.body;
            const bool chosen = clip_ >= 0 && selection_.model.has_value() && l.accessories == 0 &&
                                static_cast<std::size_t>(clip_) < l.stats.clips.size();
            c.clip = chosen ? static_cast<std::uint32_t>(clip_) : l.clip;
            c.time = anim_time_;
            c.palette = palette_ % palette_count_;
            c.accessories = l.accessories;
            characters_.push_back(c);
        }
    }
    // The reference villager, to the left of the row.
    if (show_reference_ && !placed_.empty()) {
        const std::filesystem::path core = library_.find(mods::kCoreModId) != nullptr
                                               ? library_.find(mods::kCoreModId)->dir
                                               : std::filesystem::path{};
        const Loaded& ref = load_model(mods::kCoreModId, kReferenceBody, core / kReferenceBody);
        if (ref.ok && ref.body != kNone) {
            const CatalogModel& first = catalog_.models[placed_.front().model];
            const Loaded& fl = loaded_[first.mod + "/" + first.path];
            render::CharacterInstance c;
            c.position = {placed_.front().position.x + fl.bounds_min.x - 0.8f, 0.0f, 0.0f};
            c.yaw = 0.0f;
            c.body = ref.body;
            c.clip = ref.clip;
            c.time = anim_time_;
            c.palette = 0;
            characters_.push_back(c);
        }
    }
    scene_.set_characters(characters_);
}

void ViewerApp::check_reload(float dt) {
    reload_timer_ += dt;
    status_time_ = std::max(0.0f, status_time_ - dt);
    if (reload_timer_ < kReloadCheckSeconds) {
        return;
    }
    reload_timer_ = 0.0f;
    // Files that changed on disk are loaded again. The old copy stays on the
    // GPU until the viewer closes (the renderer cannot free one model).
    std::vector<std::string> changed;
    for (const auto& [key, l] : loaded_) {
        const std::size_t slash = key.find('/');
        const mods::ModInfo* mod = library_.find(key.substr(0, slash));
        if (mod == nullptr) {
            continue;
        }
        std::error_code ec;
        const std::filesystem::path file = mods::mod_file(mod->dir, key.substr(slash + 1));
        const auto time = std::filesystem::last_write_time(file, ec);
        const std::uintmax_t bytes = ec ? 0 : std::filesystem::file_size(file, ec);
        if (!ec && (time != l.time || bytes != l.bytes)) {
            changed.push_back(key);
        }
    }
    for (const std::string& key : changed) {
        const Loaded& old = loaded_[key];
        if (old.model != kNone) {
            scene_.set_instances(old.model, {});
            std::erase(shown_rigid_, old.model);
        }
        loaded_.erase(key);
        log::info("viewer: reloading {}", key);
        status_ = tr("viewer.status.reloaded", file_name(key));
        status_time_ = kStatusSeconds;
    }
    if (!changed.empty()) {
        layout_scene();
    }
}

// --- Interface --------------------------------------------------------------

std::string ViewerApp::group_label(const CatalogGroup& g) const {
    std::string label;
    if (!g.name_key.empty() && i18n::translator().has(g.name_key)) {
        label = tr(g.name_key);
    } else if (g.id.starts_with("code:")) {
        const std::string key = "viewer.code." + g.id.substr(5);
        label = i18n::translator().has(key) ? tr(key) : g.id.substr(5);
    } else {
        const std::size_t colon = g.id.rfind(':');
        label = colon == std::string::npos ? g.id : g.id.substr(colon + 1);
    }
    return label;
}

std::string ViewerApp::use_label(const Use& u) const {
    const std::string kind = tr("viewer.use." + u.kind);
    if (u.kind == "code") {
        const std::string key = "viewer.code." + u.id;
        return kind + ": " + (i18n::translator().has(key) ? tr(key) : u.id);
    }
    const std::string name = !u.name_key.empty() && i18n::translator().has(u.name_key) ? tr(u.name_key) + " " : "";
    return kind + ": " + name + "(" + u.id + ")";
}

bool ViewerApp::group_passes_filter(const CatalogGroup& g) const {
    if (only_single_ && g.models.size() != 1) {
        return false;
    }
    bool any_unused = false;
    bool matches = contains_text(group_label(g), search_) || contains_text(g.id, search_);
    for (const std::size_t m : g.models) {
        any_unused = any_unused || !catalog_.models[m].used();
        matches = matches || contains_text(catalog_.models[m].path, search_);
    }
    return matches && (!only_unused_ || any_unused);
}

void ViewerApp::draw_ui(float width, float height) {
    const float panel = kPanelWidth * ui_scale_;
    const ImGuiWindowFlags fixed = ImGuiWindowFlags_NoMove | ImGuiWindowFlags_NoResize | ImGuiWindowFlags_NoCollapse;
    ImGui::SetNextWindowPos({0.0f, 0.0f});
    ImGui::SetNextWindowSize({panel, height});
    const std::string title = tr("viewer.panel.catalog") + "###catalog";
    if (ImGui::Begin(title.c_str(), nullptr, fixed)) {
        // The mod and the language.
        const mods::ModInfo* current = library_.find(mod_);
        const std::string mod_name = current != nullptr && i18n::translator().has(current->manifest.name_key)
                                         ? tr(current->manifest.name_key)
                                         : mod_;
        ImGui::SetNextItemWidth(-FLT_MIN);
        const std::string mod_combo = tr("viewer.mod") + ": " + mod_name;
        if (ImGui::BeginCombo("##mod", mod_combo.c_str())) {
            for (const mods::ModInfo& m : library_.mods()) {
                const std::string name =
                    (i18n::translator().has(m.manifest.name_key) ? tr(m.manifest.name_key) : m.manifest.id) + "  (" +
                    m.manifest.id + ")";
                if (ImGui::Selectable(name.c_str(), m.manifest.id == mod_) && m.manifest.id != mod_) {
                    mod_ = m.manifest.id;
                    load_catalog();
                    ImGui::EndCombo();
                    ImGui::End();
                    return;
                }
            }
            ImGui::EndCombo();
        }
        if (ImGui::BeginTabBar("##tabs")) {
            catalog_tab_ = false;
            if (ImGui::BeginTabItem(tr("viewer.tab.models").c_str())) {
                catalog_tab_ = true;
                draw_catalog_tab();
                ImGui::EndTabItem();
            }
            const std::string review = tr("viewer.tab.review") + "###review";
            if (ImGui::BeginTabItem(review.c_str())) {
                draw_review_tab();
                ImGui::EndTabItem();
            }
            ImGui::EndTabBar();
        }
    }
    ImGui::End();
    draw_card(width, height);
    draw_status(width, height);
}

std::vector<CatalogRow> ViewerApp::catalog_rows() const {
    std::vector<CatalogRow> rows;
    for (std::size_t c = 0; c < static_cast<std::size_t>(Category::Count); ++c) {
        const auto category = static_cast<Category>(c);
        std::vector<std::size_t> groups;
        for (std::size_t g = 0; g < catalog_.groups.size(); ++g) {
            const CatalogGroup& group = catalog_.groups[g];
            if (group.category == category && catalog_.models[group.models.front()].mod == mod_ &&
                group_passes_filter(group)) {
                groups.push_back(g);
            }
        }
        if (groups.empty()) {
            continue;
        }
        // By the name shown, which depends on the language.
        std::vector<std::string> labels(catalog_.groups.size());
        for (const std::size_t g : groups) {
            labels[g] = group_label(catalog_.groups[g]);
        }
        std::stable_sort(groups.begin(), groups.end(), [&](std::size_t a, std::size_t b) { return labels[a] < labels[b]; });
        const bool open = category_open_[c];
        rows.push_back({RowKind::Category, category, 0, 0, true, open});
        if (!open) {
            continue;
        }
        for (const std::size_t g : groups) {
            const CatalogGroup& group = catalog_.groups[g];
            const bool several = group.models.size() > 1;
            const bool group_open = several && open_groups_.contains(g);
            rows.push_back({RowKind::Group, category, g, 0, several, group_open});
            for (std::size_t i = 0; group_open && i < group.models.size(); ++i) {
                rows.push_back({RowKind::Model, category, g, group.models[i], false, false});
            }
        }
    }
    return rows;
}

void ViewerApp::set_open(const CatalogRow& row, bool open) {
    if (row.kind == RowKind::Category) {
        category_open_[static_cast<std::size_t>(row.category)] = open;
    } else if (row.kind == RowKind::Group && open) {
        open_groups_.insert(row.group);
    } else if (row.kind == RowKind::Group) {
        open_groups_.erase(row.group);
    }
}

void ViewerApp::navigate_catalog(NavKey key) {
    const std::vector<CatalogRow> rows = catalog_rows();
    if (rows.empty()) {
        return;
    }
    // Where the cursor is; if its line is hidden now, start at the top.
    std::size_t at = 0;
    bool found = false;
    for (std::size_t i = 0; i < rows.size() && !found; ++i) {
        if (rows[i].same(cursor_)) {
            at = i;
            found = true;
        }
    }
    const NavResult r = navigate(rows, at, key);
    if (r.toggle != NavResult::Toggle::None) {
        set_open(rows[at], r.toggle == NavResult::Toggle::Open);
        cursor_ = rows[at];
        scroll_to_cursor_ = true;
        return;
    }
    const CatalogRow& row = found ? rows[r.cursor] : rows.front();
    cursor_ = row;
    scroll_to_cursor_ = true;
    // A group or a model is shown at once.
    if (row.kind == RowKind::Group && (selection_.group != row.group || selection_.model)) {
        select({row.group, std::nullopt});
        frame_camera();
    } else if (row.kind == RowKind::Model && selection_.model != row.model) {
        select({row.group, row.model});
        frame_camera();
    }
}

void ViewerApp::draw_catalog_tab() {
    ImGui::SetNextItemWidth(-FLT_MIN);
    const std::string hint = tr("viewer.search");
    ImGui::InputTextWithHint("##search", hint.c_str(), search_, sizeof(search_));
    ImGui::Checkbox(tr("viewer.filter.unused").c_str(), &only_unused_);
    ImGui::Checkbox(tr("viewer.filter.single").c_str(), &only_single_);
    ImGui::PushStyleColor(ImGuiCol_Text, ImGui::GetStyleColorVec4(ImGuiCol_TextDisabled));
    ImGui::TextWrapped("%s", tr("viewer.keys").c_str());
    ImGui::PopStyleColor();
    ImGui::Separator();
    // How many types and models each category shows.
    std::array<std::size_t, static_cast<std::size_t>(Category::Count)> type_count{};
    std::array<std::size_t, static_cast<std::size_t>(Category::Count)> model_count{};
    for (const CatalogGroup& group : catalog_.groups) {
        if (catalog_.models[group.models.front()].mod == mod_ && group_passes_filter(group)) {
            ++type_count[static_cast<std::size_t>(group.category)];
            model_count[static_cast<std::size_t>(group.category)] += group.models.size();
        }
    }
    ImGui::BeginChild("##list");
    const std::vector<CatalogRow> rows = catalog_rows();
    for (const CatalogRow& row : rows) {
        const bool at_cursor = row.same(cursor_);
        const std::size_t c = static_cast<std::size_t>(row.category);
        if (row.kind == RowKind::Category) {
            const std::string header = tr(category_key(row.category)) + "  " +
                                       tr("viewer.count", type_count[c], model_count[c]) + "###cat" + std::to_string(c);
            ImGui::SetNextItemOpen(row.open);
            // The cursor on a header: a lighter bar with a frame.
            if (at_cursor) {
                ImGui::PushStyleColor(ImGuiCol_Header, ImGui::GetStyleColorVec4(ImGuiCol_HeaderActive));
                ImGui::PushStyleColor(ImGuiCol_Border, ImVec4(1.0f, 1.0f, 1.0f, 0.8f));
                ImGui::PushStyleVar(ImGuiStyleVar_FrameBorderSize, std::max(1.0f, ui_scale_));
            }
            const bool open = ImGui::CollapsingHeader(header.c_str());
            if (at_cursor) {
                ImGui::PopStyleVar();
                ImGui::PopStyleColor(2);
            }
            if (open != row.open) {
                set_open(row, open);
                cursor_ = row;
            }
        } else if (row.kind == RowKind::Group) {
            const CatalogGroup& group = catalog_.groups[row.group];
            bool unused = false;
            for (const std::size_t m : group.models) {
                unused = unused || !catalog_.models[m].used();
            }
            ImGui::PushID(static_cast<int>(row.group));
            ImGuiTreeNodeFlags flags = ImGuiTreeNodeFlags_OpenOnArrow | ImGuiTreeNodeFlags_SpanAvailWidth |
                                       ImGuiTreeNodeFlags_NoTreePushOnOpen;
            if (at_cursor) {
                flags |= ImGuiTreeNodeFlags_Selected;
            }
            if (!row.expandable) {
                flags |= ImGuiTreeNodeFlags_Leaf;
            }
            std::string label = group_label(group);
            if (group.models.size() > 1) {
                label += "  (" + std::to_string(group.models.size()) + ")";
            }
            if (unused) {
                label += "  " + tr("viewer.unusedMark");
                ImGui::PushStyleColor(ImGuiCol_Text, ImVec4(1.0f, 0.72f, 0.3f, 1.0f));
            }
            if (row.expandable) {
                ImGui::SetNextItemOpen(row.open);
            }
            const bool open = ImGui::TreeNodeEx("##group", flags, "%s", label.c_str());
            if (unused) {
                ImGui::PopStyleColor();
            }
            if (row.expandable && open != row.open) {
                set_open(row, open);
            } else if (ImGui::IsItemClicked()) {
                select({row.group, std::nullopt});
                frame_camera();
            }
            ImGui::PopID();
        } else {
            const CatalogModel& cm = catalog_.models[row.model];
            std::string name = file_name(cm.path);
            if (!cm.used()) {
                name += "  " + tr("viewer.unusedMark");
            }
            ImGui::PushID(static_cast<int>(row.model));
            ImGui::Indent();
            if (ImGui::Selectable(name.c_str(), at_cursor)) {
                select({row.group, row.model});
                frame_camera();
            }
            ImGui::Unindent();
            ImGui::PopID();
        }
        if (at_cursor && scroll_to_cursor_) {
            ImGui::ScrollToItem(ImGuiScrollFlags_KeepVisibleEdgeY);
            scroll_to_cursor_ = false;
        }
    }
    ImGui::EndChild();
}

void ViewerApp::draw_review_tab() {
    ImGui::BeginChild("##review");
    // Models nothing uses.
    std::vector<std::size_t> unused;
    for (std::size_t m = 0; m < catalog_.models.size(); ++m) {
        if (!catalog_.models[m].used() && catalog_.models[m].mod == mod_) {
            unused.push_back(m);
        }
    }
    const std::string unused_title = tr("viewer.review.unused", unused.size()) + "###unused";
    if (ImGui::CollapsingHeader(unused_title.c_str(), ImGuiTreeNodeFlags_DefaultOpen)) {
        ImGui::TextWrapped("%s", tr("viewer.review.unusedHelp").c_str());
        for (const std::size_t m : unused) {
            ImGui::PushID(static_cast<int>(m));
            if (ImGui::Selectable(catalog_.models[m].path.c_str(), selection_.model == m)) {
                select({catalog_.models[m].group, m});
                frame_camera();
            }
            ImGui::PopID();
        }
    }
    // Definitions whose model is not there.
    std::vector<const mods::ModelRef*> missing;
    for (const mods::ModelRef& r : catalog_.missing) {
        if (r.mod == mod_ || r.def_id.starts_with(mod_ + ":")) {
            missing.push_back(&r);
        }
    }
    const std::string missing_title = tr("viewer.review.missing", missing.size()) + "###missing";
    if (ImGui::CollapsingHeader(missing_title.c_str(), ImGuiTreeNodeFlags_DefaultOpen)) {
        for (const mods::ModelRef* r : missing) {
            ImGui::TextColored(ImVec4(1.0f, 0.45f, 0.4f, 1.0f), "%s", r->def_id.c_str());
            ImGui::Indent();
            ImGui::TextWrapped("%s", tr("viewer.review.missingFile", r->mod + "/" + r->path).c_str());
            ImGui::Unindent();
        }
    }
    // Things with a single model.
    std::vector<std::size_t> single;
    std::size_t groups = 0;
    for (std::size_t g = 0; g < catalog_.groups.size(); ++g) {
        const CatalogGroup& group = catalog_.groups[g];
        if (catalog_.models[group.models.front()].mod != mod_) {
            continue;
        }
        ++groups;
        if (group.models.size() == 1) {
            single.push_back(g);
        }
    }
    const std::string single_title = tr("viewer.review.single", single.size(), groups) + "###single";
    if (ImGui::CollapsingHeader(single_title.c_str())) {
        for (const std::size_t g : single) {
            ImGui::PushID(static_cast<int>(g));
            const std::string label = group_label(catalog_.groups[g]) + "  —  " +
                                      tr(category_key(catalog_.groups[g].category));
            if (ImGui::Selectable(label.c_str(), selection_.group == g)) {
                select({g, std::nullopt});
                frame_camera();
            }
            ImGui::PopID();
        }
    }
    // The mod's own errors.
    if (const mods::ModInfo* m = library_.find(mod_); m != nullptr) {
        const std::string errors_title = tr("viewer.review.errors", m->errors.size()) + "###errors";
        if (ImGui::CollapsingHeader(errors_title.c_str(), m->errors.empty() ? 0 : ImGuiTreeNodeFlags_DefaultOpen)) {
            for (const std::string& e : m->errors) {
                ImGui::TextWrapped("%s", e.c_str());
            }
        }
    }
    if (catalog_.truncated) {
        ImGui::TextColored(ImVec4(1.0f, 0.45f, 0.4f, 1.0f), "%s", tr("viewer.review.truncated").c_str());
    }
    ImGui::Separator();
    ImGui::TextDisabled("%s", tr("viewer.review.folder").c_str());
    ImGui::TextWrapped("%s", text::path_to_utf8(mods_dir_).c_str());
    ImGui::TextWrapped("%s", text::path_to_utf8(paths_->user_mods_dir()).c_str());
    ImGui::EndChild();
}

void ViewerApp::draw_card(float width, float height) {
    const float panel = kPanelWidth * ui_scale_;
    ImGui::SetNextWindowPos({width - panel, 0.0f});
    ImGui::SetNextWindowSize({panel, height});
    const std::string title = tr("viewer.panel.card") + "###card";
    if (!ImGui::Begin(title.c_str(), nullptr,
                      ImGuiWindowFlags_NoMove | ImGuiWindowFlags_NoResize | ImGuiWindowFlags_NoCollapse)) {
        ImGui::End();
        return;
    }
    const std::vector<std::size_t> shown = shown_models();
    if (shown.empty()) {
        ImGui::TextWrapped("%s", tr("viewer.card.empty").c_str());
    } else if (selection_.group && !selection_.model && catalog_.groups[*selection_.group].models.size() == 1) {
        draw_model_card(catalog_.models[shown.front()]);
    } else if (selection_.group && !selection_.model) {
        const CatalogGroup& g = catalog_.groups[*selection_.group];
        ImGui::TextWrapped("%s", group_label(g).c_str());
        ImGui::TextDisabled("%s", g.id.c_str());
        ImGui::Text("%s", tr("viewer.card.variants", g.models.size()).c_str());
        ImGui::Separator();
        if (ImGui::BeginTable("##variants", 3, ImGuiTableFlags_SizingStretchProp | ImGuiTableFlags_RowBg)) {
            ImGui::TableSetupColumn(tr("viewer.card.file").c_str());
            ImGui::TableSetupColumn(tr("viewer.card.triangles").c_str());
            ImGui::TableSetupColumn(tr("viewer.card.drawCalls").c_str());
            ImGui::TableHeadersRow();
            for (const std::size_t m : g.models) {
                const CatalogModel& cm = catalog_.models[m];
                const Loaded& l = loaded_[cm.mod + "/" + cm.path];
                ImGui::TableNextRow();
                ImGui::TableNextColumn();
                ImGui::PushID(static_cast<int>(m));
                if (ImGui::Selectable(file_name(cm.path).c_str(), false, ImGuiSelectableFlags_SpanAllColumns)) {
                    select({*selection_.group, m});
                    frame_camera();
                }
                ImGui::PopID();
                ImGui::TableNextColumn();
                ImGui::Text("%s", i18n::translator().format_int(static_cast<std::int64_t>(l.stats.triangles)).c_str());
                ImGui::TableNextColumn();
                ImGui::Text("%zu", l.stats.draw_calls);
            }
            ImGui::EndTable();
        }
        ImGui::TextWrapped("%s", tr("viewer.card.pickOne").c_str());
    } else {
        draw_model_card(catalog_.models[*selection_.model]);
    }

    // What the view shows.
    ImGui::Separator();
    ImGui::TextDisabled("%s", tr("viewer.view.title").c_str());
    ImGui::Checkbox(tr("viewer.view.reference").c_str(), &show_reference_);
    ImGui::Checkbox(tr("viewer.view.ground").c_str(), &show_ground_);
    ImGui::Checkbox(tr("viewer.view.turntable").c_str(), &turntable_);
    bool trees = false;
    bool bodies = false;
    for (const std::size_t m : shown) {
        trees = trees || catalog_.models[m].category == Category::Trees ||
                catalog_.models[m].category == Category::Props;
        bodies = bodies || catalog_.models[m].category == Category::Characters;
    }
    if (trees) {
        const std::string seasons[] = {tr("hud.season.spring"), tr("hud.season.summer"), tr("hud.season.autumn"),
                                       tr("hud.season.winter")};
        ImGui::SetNextItemWidth(-FLT_MIN);
        const std::string season_label = tr("viewer.view.season") + ": " + seasons[season_];
        if (ImGui::BeginCombo("##season", season_label.c_str())) {
            for (int s = 0; s < 4; ++s) {
                if (ImGui::Selectable(seasons[s].c_str(), s == season_)) {
                    season_ = s;
                }
            }
            ImGui::EndCombo();
        }
        ImGui::Checkbox(tr("viewer.view.snow").c_str(), &snowy_);
    }
    if (bodies) {
        const std::string palette = tr("viewer.view.palette", palette_ % palette_count_ + 1, palette_count_);
        if (ImGui::Button(palette.c_str())) {
            palette_ = (palette_ * 7u + 13u) % palette_count_;
        }
    }
    if (ImGui::Button(tr("viewer.view.frame").c_str())) {
        frame_camera();
    }
    ImGui::SameLine();
    if (ImGui::Button(tr("viewer.view.reload").c_str())) {
        load_catalog();
    }
    // The language.
    ImGui::Separator();
    const auto languages = i18n::translator().available();
    ImGui::SetNextItemWidth(-FLT_MIN);
    const std::string language = tr("viewer.language") + ": " + i18n::translator().active().native_name;
    if (ImGui::BeginCombo("##language", language.c_str())) {
        for (const i18n::LanguageInfo* l : languages) {
            if (ImGui::Selectable(l->native_name.c_str(), l->code == i18n::translator().active().code)) {
                (void)i18n::translator().set_language(l->code);
                SDL_SetWindowTitle(window_, tr("viewer.title").c_str());
            }
        }
        ImGui::EndCombo();
    }
    ImGui::End();
}

void ViewerApp::draw_model_card(const CatalogModel& m) {
    const Loaded& l = loaded_[m.mod + "/" + m.path];
    ImGui::TextWrapped("%s", file_name(m.path).c_str());
    ImGui::TextDisabled("%s/%s", m.mod.c_str(), m.path.c_str());
    ImGui::Text("%s: %s", tr("viewer.card.category").c_str(), tr(category_key(m.category)).c_str());
    ImGui::Separator();
    ImGui::TextDisabled("%s", tr("viewer.card.usedBy").c_str());
    if (m.uses.empty()) {
        ImGui::TextColored(ImVec4(1.0f, 0.72f, 0.3f, 1.0f), "%s", tr("viewer.card.unused").c_str());
    }
    for (const Use& u : m.uses) {
        ImGui::BulletText("%s", use_label(u).c_str());
    }
    ImGui::Separator();
    if (!l.ok) {
        ImGui::TextColored(ImVec4(1.0f, 0.45f, 0.4f, 1.0f), "%s", tr("viewer.card.broken").c_str());
        ImGui::TextWrapped("%s", l.error.c_str());
        return;
    }
    const ModelStats& s = l.stats;
    const auto& t = i18n::translator();
    const auto row = [](const std::string& name, const std::string& value) {
        ImGui::TableNextRow();
        ImGui::TableNextColumn();
        ImGui::TextUnformatted(name.c_str());
        ImGui::TableNextColumn();
        ImGui::TextUnformatted(value.c_str());
    };
    if (ImGui::BeginTable("##stats", 2, ImGuiTableFlags_SizingStretchProp)) {
        row(tr("viewer.card.triangles"), t.format_int(static_cast<std::int64_t>(s.triangles)));
        row(tr("viewer.card.vertices"), t.format_int(static_cast<std::int64_t>(s.vertices)));
        row(tr("viewer.card.drawCalls"), std::to_string(s.draw_calls));
        row(tr("viewer.card.materials"), std::to_string(s.materials));
        row(tr("viewer.card.textures"),
            s.textures == 0 ? tr("viewer.card.none") : tr("viewer.card.textureSize", s.textures, s.largest_texture));
        char size[64];
        std::snprintf(size, sizeof(size), "%.2f × %.2f × %.2f m", static_cast<double>(s.size.x),
                      static_cast<double>(s.size.y), static_cast<double>(s.size.z));
        row(tr("viewer.card.size"), size);
        row(tr("viewer.card.fileSize"), tr("viewer.card.kb", static_cast<std::int64_t>((l.bytes + 1023) / 1024)));
        if (s.skinned) {
            row(tr("viewer.card.joints"), std::to_string(s.joints));
        }
        ImGui::EndTable();
    }
    ImGui::TextWrapped("%s", tr("viewer.card.drawCallsHelp").c_str());
    // A body's animations.
    if (s.skinned && !s.clips.empty() && l.accessories == 0) {
        ImGui::SetNextItemWidth(-FLT_MIN);
        const std::string current = clip_ >= 0 && static_cast<std::size_t>(clip_) < s.clips.size()
                                        ? s.clips[static_cast<std::size_t>(clip_)]
                                        : s.clips[l.clip];
        const std::string label = tr("viewer.card.animation") + ": " + current;
        if (ImGui::BeginCombo("##clip", label.c_str())) {
            for (std::size_t c = 0; c < s.clips.size(); ++c) {
                if (ImGui::Selectable(s.clips[c].c_str(), current == s.clips[c])) {
                    clip_ = static_cast<int>(c);
                }
            }
            ImGui::EndCombo();
        }
    }
    if (l.accessories != 0) {
        ImGui::TextWrapped("%s", tr("viewer.card.onBody").c_str());
    }
}

void ViewerApp::draw_status(float width, float height) {
    const float panel = kPanelWidth * ui_scale_;
    ImGui::SetNextWindowPos({panel + 8.0f * ui_scale_, height - 8.0f * ui_scale_}, ImGuiCond_Always, {0.0f, 1.0f});
    ImGui::SetNextWindowSizeConstraints({0.0f, 0.0f}, {std::max(100.0f, width - 2.0f * panel - 16.0f * ui_scale_), height});
    ImGui::SetNextWindowBgAlpha(0.6f);
    const ImGuiWindowFlags flags = ImGuiWindowFlags_NoDecoration | ImGuiWindowFlags_AlwaysAutoResize |
                                   ImGuiWindowFlags_NoMove | ImGuiWindowFlags_NoFocusOnAppearing |
                                   ImGuiWindowFlags_NoNav | ImGuiWindowFlags_NoInputs;
    if (ImGui::Begin("##status", nullptr, flags)) {
        ImGui::TextUnformatted(tr("viewer.controls").c_str());
        if (status_time_ > 0.0f && !status_.empty()) {
            ImGui::TextColored(ImVec4(0.55f, 0.9f, 0.55f, 1.0f), "%s", status_.c_str());
        }
    }
    ImGui::End();
}

}  // namespace sc::viewer
