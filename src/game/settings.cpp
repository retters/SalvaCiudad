#include "game/settings.h"

#include <algorithm>
#include <array>
#include <string>
#include <string_view>
#include <utility>

#include "core/file_io.h"
#include "core/log.h"
#include "core/text.h"

namespace sc {

namespace lim = settings_limits;

const char* window_mode_to_string(WindowMode mode) {
    switch (mode) {
        case WindowMode::Fullscreen: return "fullscreen";
        case WindowMode::Windowed: return "windowed";
        case WindowMode::Borderless: return "borderless";
    }
    return "borderless";
}

const char* quality_preset_to_string(QualityPreset preset) {
    switch (preset) {
        case QualityPreset::Low: return "low";
        case QualityPreset::Medium: return "medium";
        case QualityPreset::High: return "high";
        case QualityPreset::Ultra: return "ultra";
        case QualityPreset::Custom: return "custom";
    }
    return "high";
}

std::optional<QualityPreset> quality_preset_from_string(std::string_view s) {
    if (s == "low") return QualityPreset::Low;
    if (s == "medium") return QualityPreset::Medium;
    if (s == "high") return QualityPreset::High;
    if (s == "ultra") return QualityPreset::Ultra;
    if (s == "custom") return QualityPreset::Custom;
    return std::nullopt;
}

// Host names and IPv4 addresses: letters, digits, dots and dashes.
bool is_valid_address(std::string_view a) {
    if (a.empty() || a.size() > lim::kMaxAddressBytes) {
        return false;
    }
    for (const char c : a) {
        if (!((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '.' || c == '-')) {
            return false;
        }
    }
    return true;
}

namespace {
struct PresetLevels {
    QualityPreset preset;
    int shadows;
    int draw_distance;
    int vegetation;
    int antialiasing;
};
constexpr PresetLevels kPresets[] = {
    {QualityPreset::Low, 0, 0, 0, 0},
    {QualityPreset::Medium, 1, 1, 1, 1},
    {QualityPreset::High, 2, 2, 2, 2},
    {QualityPreset::Ultra, 3, 3, 3, 3},
};
}  // namespace

void GraphicsSettings::apply_preset(QualityPreset p) {
    for (const PresetLevels& levels : kPresets) {
        if (levels.preset == p) {
            preset = p;
            shadows = levels.shadows;
            draw_distance = levels.draw_distance;
            vegetation = levels.vegetation;
            antialiasing = levels.antialiasing;
            return;
        }
    }
    preset = QualityPreset::Custom;
}

QualityPreset GraphicsSettings::matching_preset() const {
    for (const PresetLevels& levels : kPresets) {
        if (levels.shadows == shadows && levels.draw_distance == draw_distance && levels.vegetation == vegetation &&
            levels.antialiasing == antialiasing) {
            return levels.preset;
        }
    }
    return QualityPreset::Custom;
}

std::optional<WindowMode> window_mode_from_string(std::string_view s) {
    if (s == "fullscreen") {
        return WindowMode::Fullscreen;
    }
    if (s == "windowed") {
        return WindowMode::Windowed;
    }
    if (s == "borderless") {
        return WindowMode::Borderless;
    }
    return std::nullopt;
}

namespace {

// Reads fields into a Settings, counting and logging the invalid ones.
class Reader {
public:
    int ignored = 0;

    void count(json::Field f, std::string_view path) {
        if (f == json::Field::Invalid) {
            ++ignored;
            log::warn("settings: ignored invalid field '{}', using its default", path);
        }
    }

    void read_int(yyjson_mut_val* obj, const char* key, std::string_view path, int min, int max, int& out) {
        std::int64_t v = 0;
        const json::Field f = json::get_int(obj, key, min, max, v);
        if (f == json::Field::Ok) {
            out = static_cast<int>(v);
        }
        count(f, path);
    }

    void read_bool(yyjson_mut_val* obj, const char* key, std::string_view path, bool& out) {
        count(json::get_bool(obj, key, out), path);
    }

    yyjson_mut_val* read_section(yyjson_mut_val* root, const char* key) {
        yyjson_mut_val* obj = nullptr;
        const json::Field f = json::get_object(root, key, obj);
        count(f, key);
        return f == json::Field::Ok ? obj : nullptr;
    }
};

void read_display(Reader& r, yyjson_mut_val* obj, DisplaySettings& d) {
    std::string mode;
    json::Field f = json::get_string(obj, "mode", 16, mode);
    if (f == json::Field::Ok) {
        if (const auto m = window_mode_from_string(mode)) {
            d.mode = *m;
        } else {
            f = json::Field::Invalid;
        }
    }
    r.count(f, "display.mode");

    r.count(json::get_string(obj, "monitor", lim::kMaxMonitorNameBytes, d.monitor), "display.monitor");

    // Fullscreen size: both 0 (desktop mode) or both within range.
    int fw = d.fullscreen_width;
    int fh = d.fullscreen_height;
    r.read_int(obj, "fullscreenWidth", "display.fullscreenWidth", 0, lim::kMaxWindowSize, fw);
    r.read_int(obj, "fullscreenHeight", "display.fullscreenHeight", 0, lim::kMaxWindowSize, fh);
    const bool fs_desktop = fw == 0 && fh == 0;
    const bool fs_valid = fw >= lim::kMinWindowSize && fh >= lim::kMinWindowSize / 2;
    if (fs_desktop || fs_valid) {
        d.fullscreen_width = fw;
        d.fullscreen_height = fh;
    } else {
        r.count(json::Field::Invalid, "display.fullscreenWidth/Height");
    }

    r.read_int(obj, "windowWidth", "display.windowWidth", lim::kMinWindowSize, lim::kMaxWindowSize, d.window_width);
    r.read_int(obj, "windowHeight", "display.windowHeight", lim::kMinWindowSize / 2, lim::kMaxWindowSize,
               d.window_height);

    // The position is only meaningful as a pair.
    std::int64_t x = 0;
    std::int64_t y = 0;
    const json::Field fx = json::get_int(obj, "windowX", -lim::kMaxWindowCoordinate, lim::kMaxWindowCoordinate, x);
    const json::Field fy = json::get_int(obj, "windowY", -lim::kMaxWindowCoordinate, lim::kMaxWindowCoordinate, y);
    if (fx == json::Field::Ok && fy == json::Field::Ok) {
        d.window_x = static_cast<int>(x);
        d.window_y = static_cast<int>(y);
    } else if (fx != json::Field::Missing || fy != json::Field::Missing) {
        r.count(json::Field::Invalid, "display.windowX/Y");
    }

    r.read_bool(obj, "windowMaximized", "display.windowMaximized", d.window_maximized);
    r.read_bool(obj, "vsync", "display.vsync", d.vsync);

    int fps = d.fps_limit;
    r.read_int(obj, "fpsLimit", "display.fpsLimit", 0, lim::kMaxFpsLimit, fps);
    if (fps == 0 || fps >= lim::kMinFpsLimit) {
        d.fps_limit = fps;
    } else {
        r.count(json::Field::Invalid, "display.fpsLimit");
    }

    double scale = d.ui_scale;
    const json::Field fs = json::get_double(obj, "uiScale", 0.0, lim::kMaxUiScale, scale);
    if (fs == json::Field::Ok && (scale == 0.0 || scale >= lim::kMinUiScale)) {
        d.ui_scale = scale;
    } else {
        r.count(fs == json::Field::Missing ? fs : json::Field::Invalid, "display.uiScale");
    }
}

void read_audio(Reader& r, yyjson_mut_val* obj, AudioSettings& a) {
    r.read_int(obj, "master", "audio.master", 0, 100, a.master);
    r.read_int(obj, "effects", "audio.effects", 0, 100, a.effects);
    r.read_int(obj, "ambient", "audio.ambient", 0, 100, a.ambient);
    r.read_int(obj, "music", "audio.music", 0, 100, a.music);
    r.read_int(obj, "ui", "audio.ui", 0, 100, a.ui);
}

void read_double(Reader& r, yyjson_mut_val* obj, const char* key, std::string_view path, double min, double max,
                 double& out) {
    r.count(json::get_double(obj, key, min, max, out), path);
}

void read_graphics(Reader& r, yyjson_mut_val* obj, GraphicsSettings& g) {
    r.read_int(obj, "shadows", "graphics.shadows", 0, 3, g.shadows);
    r.read_int(obj, "drawDistance", "graphics.drawDistance", 0, 3, g.draw_distance);
    r.read_int(obj, "vegetation", "graphics.vegetation", 0, 3, g.vegetation);
    r.read_int(obj, "antialiasing", "graphics.antialiasing", 0, 3, g.antialiasing);
    std::string preset;
    json::Field f = json::get_string(obj, "preset", 16, preset);
    if (f == json::Field::Ok) {
        f = quality_preset_from_string(preset) ? json::Field::Ok : json::Field::Invalid;
    }
    r.count(f, "graphics.preset");
    // The levels are what counts; the preset is derived so the two never
    // disagree.
    g.preset = g.matching_preset();
}

bool is_valid_font_id(std::string_view id) {
    if (id.empty() || id.size() > lim::kMaxFontIdBytes) {
        return false;
    }
    for (const char c : id) {
        if (!((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '-')) {
            return false;
        }
    }
    return true;
}

void read_bindings(Reader& r, yyjson_mut_val* obj, KeyBindings& bindings) {
    for (const ActionInfo& info : action_table()) {
        const std::string key(info.id);
        yyjson_mut_val* v = yyjson_mut_obj_get(obj, key.c_str());
        if (v == nullptr) {
            continue;
        }
        const std::string path = "input.bindings." + key;
        std::array<SDL_Scancode, kKeysPerAction> keys{};
        bool ok = yyjson_mut_is_arr(v) && yyjson_mut_arr_size(v) <= kKeysPerAction;
        for (std::size_t slot = 0; ok && slot < yyjson_mut_arr_size(v); ++slot) {
            yyjson_mut_val* name = yyjson_mut_arr_get(v, slot);
            ok = yyjson_mut_is_str(name) &&
                 scancode_from_name(std::string_view(yyjson_mut_get_str(name), yyjson_mut_get_len(name)), keys[slot]);
        }
        if (!ok) {
            r.count(json::Field::Invalid, path);
            continue;
        }
        for (std::size_t slot = 0; slot < kKeysPerAction; ++slot) {
            bindings.set_key(info.action, slot, keys[slot]);
        }
    }
    // A key may trigger only one action: later duplicates are unbound.
    for (const ActionInfo& info : action_table()) {
        for (std::size_t slot = 0; slot < kKeysPerAction; ++slot) {
            const SDL_Scancode k = bindings.key(info.action, slot);
            Action first_action{};
            std::size_t first_slot = 0;
            if (bindings.find(k, first_action, first_slot) &&
                (first_action != info.action || first_slot != slot)) {
                bindings.set_key(info.action, slot, SDL_SCANCODE_UNKNOWN);
                r.count(json::Field::Invalid, "input.bindings." + std::string(info.id));
            }
        }
    }
}

void read_input(Reader& r, yyjson_mut_val* obj, InputSettings& in) {
    yyjson_mut_val* bindings = nullptr;
    const json::Field fb = json::get_object(obj, "bindings", bindings);
    r.count(fb, "input.bindings");
    if (fb == json::Field::Ok) {
        read_bindings(r, bindings, in.bindings);
    }
    read_double(r, obj, "cameraPanSpeed", "input.cameraPanSpeed", lim::kMinCameraSpeed, lim::kMaxCameraSpeed,
                in.camera_pan_speed);
    read_double(r, obj, "cameraRotateSpeed", "input.cameraRotateSpeed", lim::kMinCameraSpeed, lim::kMaxCameraSpeed,
                in.camera_rotate_speed);
    read_double(r, obj, "cameraZoomSpeed", "input.cameraZoomSpeed", lim::kMinCameraSpeed, lim::kMaxCameraSpeed,
                in.camera_zoom_speed);
    r.read_bool(obj, "invertZoom", "input.invertZoom", in.invert_zoom);
    r.read_bool(obj, "edgeScroll", "input.edgeScroll", in.edge_scroll);
}

void read_ui(Reader& r, yyjson_mut_val* obj, UiSettings& ui) {
    std::string font;
    json::Field f = json::get_string(obj, "font", lim::kMaxFontIdBytes, font);
    if (f == json::Field::Ok && !is_valid_font_id(font)) {
        f = json::Field::Invalid;
    }
    if (f == json::Field::Ok) {
        ui.font = font;
    }
    r.count(f, "ui.font");
    r.read_bool(obj, "showTooltips", "ui.showTooltips", ui.show_tooltips);
    r.read_int(obj, "tooltipDelayMs", "ui.tooltipDelayMs", 0, lim::kMaxTooltipDelayMs, ui.tooltip_delay_ms);
    std::string windows;
    json::Field w = json::get_string(obj, "windows", 2048, windows);
    if (w == json::Field::Ok && !std::all_of(windows.begin(), windows.end(), [](char c) {
            return (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == ':' || c == ',' || c == ';' || c == '-' ||
                   c == '_';
        })) {
        w = json::Field::Invalid;
    }
    if (w == json::Field::Ok) {
        ui.windows = windows;
    }
    r.count(w, "ui.windows");
}

void read_gameplay(Reader& r, yyjson_mut_val* obj, GameplaySettings& g) {
    r.read_int(obj, "autosaveMinutes", "gameplay.autosaveMinutes", 0, lim::kMaxAutosaveMinutes, g.autosave_minutes);
    r.read_int(obj, "autosaveKeep", "gameplay.autosaveKeep", 1, lim::kMaxAutosaveKeep, g.autosave_keep);
    r.read_bool(obj, "tutorialSeen", "gameplay.tutorialSeen", g.tutorial_seen);
    std::string text;
    json::Field f = json::get_string(obj, "playerName", lim::kMaxPlayerNameBytes, text);
    if (f == json::Field::Ok) {
        g.player_name = text;
    }
    r.count(f, "gameplay.playerName");
    f = json::get_string(obj, "joinAddress", lim::kMaxAddressBytes, text);
    if (f == json::Field::Ok && !is_valid_address(text)) {
        f = json::Field::Invalid;
    }
    if (f == json::Field::Ok) {
        g.join_address = text;
    }
    r.count(f, "gameplay.joinAddress");
    r.read_int(obj, "joinPort", "gameplay.joinPort", lim::kMinPort, lim::kMaxPort, g.join_port);
}

bool write_bindings(yyjson_mut_doc* doc, yyjson_mut_val* obj, const KeyBindings& bindings) {
    for (const ActionInfo& info : action_table()) {
        yyjson_mut_val* arr = yyjson_mut_arr(doc);
        if (arr == nullptr) {
            return false;
        }
        for (std::size_t slot = 0; slot < kKeysPerAction; ++slot) {
            const std::string name = scancode_to_name(bindings.key(info.action, slot));
            if (!yyjson_mut_arr_add_strncpy(doc, arr, name.data(), name.size())) {
                return false;
            }
        }
        const std::string key(info.id);
        yyjson_mut_val* key_val = yyjson_mut_strncpy(doc, key.data(), key.size());
        if (key_val == nullptr || !yyjson_mut_obj_put(obj, key_val, arr)) {
            return false;
        }
    }
    return true;
}

bool write_settings(yyjson_mut_doc* doc, const Settings& s) {
    yyjson_mut_val* root = yyjson_mut_doc_get_root(doc);
    bool ok = json::set_int(doc, root, "schemaVersion", lim::kSchemaVersion);
    ok = ok && json::set_string(doc, root, "language", s.language);

    yyjson_mut_val* d = json::ensure_object(doc, root, "display");
    const DisplaySettings& ds = s.display;
    ok = ok && d != nullptr;
    ok = ok && json::set_string(doc, d, "mode", window_mode_to_string(ds.mode));
    ok = ok && json::set_string(doc, d, "monitor", ds.monitor);
    ok = ok && json::set_int(doc, d, "fullscreenWidth", ds.fullscreen_width);
    ok = ok && json::set_int(doc, d, "fullscreenHeight", ds.fullscreen_height);
    ok = ok && json::set_int(doc, d, "windowWidth", ds.window_width);
    ok = ok && json::set_int(doc, d, "windowHeight", ds.window_height);
    if (ds.window_x && ds.window_y) {
        ok = ok && json::set_int(doc, d, "windowX", *ds.window_x);
        ok = ok && json::set_int(doc, d, "windowY", *ds.window_y);
    } else if (ok) {
        json::remove_key(d, "windowX");
        json::remove_key(d, "windowY");
    }
    ok = ok && json::set_bool(doc, d, "windowMaximized", ds.window_maximized);
    ok = ok && json::set_bool(doc, d, "vsync", ds.vsync);
    ok = ok && json::set_int(doc, d, "fpsLimit", ds.fps_limit);
    ok = ok && json::set_double(doc, d, "uiScale", ds.ui_scale);

    yyjson_mut_val* a = json::ensure_object(doc, root, "audio");
    ok = ok && a != nullptr;
    ok = ok && json::set_int(doc, a, "master", s.audio.master);
    ok = ok && json::set_int(doc, a, "effects", s.audio.effects);
    ok = ok && json::set_int(doc, a, "ambient", s.audio.ambient);
    ok = ok && json::set_int(doc, a, "music", s.audio.music);
    ok = ok && json::set_int(doc, a, "ui", s.audio.ui);

    yyjson_mut_val* g = json::ensure_object(doc, root, "graphics");
    ok = ok && g != nullptr;
    ok = ok && json::set_string(doc, g, "preset", quality_preset_to_string(s.graphics.preset));
    ok = ok && json::set_int(doc, g, "shadows", s.graphics.shadows);
    ok = ok && json::set_int(doc, g, "drawDistance", s.graphics.draw_distance);
    ok = ok && json::set_int(doc, g, "vegetation", s.graphics.vegetation);
    ok = ok && json::set_int(doc, g, "antialiasing", s.graphics.antialiasing);

    yyjson_mut_val* in = json::ensure_object(doc, root, "input");
    ok = ok && in != nullptr;
    yyjson_mut_val* b = ok ? json::ensure_object(doc, in, "bindings") : nullptr;
    ok = ok && b != nullptr && write_bindings(doc, b, s.input.bindings);
    ok = ok && json::set_double(doc, in, "cameraPanSpeed", s.input.camera_pan_speed);
    ok = ok && json::set_double(doc, in, "cameraRotateSpeed", s.input.camera_rotate_speed);
    ok = ok && json::set_double(doc, in, "cameraZoomSpeed", s.input.camera_zoom_speed);
    ok = ok && json::set_bool(doc, in, "invertZoom", s.input.invert_zoom);
    ok = ok && json::set_bool(doc, in, "edgeScroll", s.input.edge_scroll);

    yyjson_mut_val* u = json::ensure_object(doc, root, "ui");
    ok = ok && u != nullptr;
    ok = ok && json::set_string(doc, u, "font", s.ui.font);
    ok = ok && json::set_bool(doc, u, "showTooltips", s.ui.show_tooltips);
    ok = ok && json::set_int(doc, u, "tooltipDelayMs", s.ui.tooltip_delay_ms);
    ok = ok && json::set_string(doc, u, "windows", s.ui.windows);

    yyjson_mut_val* gp = json::ensure_object(doc, root, "gameplay");
    ok = ok && gp != nullptr;
    ok = ok && json::set_int(doc, gp, "autosaveMinutes", s.gameplay.autosave_minutes);
    ok = ok && json::set_int(doc, gp, "autosaveKeep", s.gameplay.autosave_keep);
    ok = ok && json::set_bool(doc, gp, "tutorialSeen", s.gameplay.tutorial_seen);
    ok = ok && json::set_string(doc, gp, "playerName", s.gameplay.player_name);
    ok = ok && json::set_string(doc, gp, "joinAddress", s.gameplay.join_address);
    ok = ok && json::set_int(doc, gp, "joinPort", s.gameplay.join_port);
    return ok;
}

}  // namespace

SettingsStore::SettingsStore(std::filesystem::path file) : file_(std::move(file)) {}

SettingsLoadReport SettingsStore::load() {
    SettingsLoadReport report;
    settings_ = Settings{};
    raw_.reset();
    read_only_ = false;

    const fs::ReadResult read = fs::read_file(file_, lim::kMaxFileBytes);
    if (read.error == fs::IoError::NotFound) {
        report.created_default = true;
        log::info("settings: no settings file, using defaults");
        return report;
    }

    json::ParseResult parsed;
    if (read.error == fs::IoError::None) {
        parsed = json::parse_object(read.data);
    }
    if (read.error != fs::IoError::None || parsed.error != json::ParseError::None) {
        if (read.error != fs::IoError::None) {
            log::error("settings: cannot read settings file ({})", fs::io_error_name(read.error));
        } else {
            log::error("settings: settings file is not valid JSON ({})", parsed.message);
        }
        // An unreadable file (other than a transient open failure) is set
        // aside so the user keeps it and the game starts with defaults.
        if (read.error != fs::IoError::OpenFailed) {
            report.quarantine_path = fs::quarantine_file(file_);
            report.quarantined = !report.quarantine_path.empty();
            if (report.quarantined) {
                log::warn("settings: damaged file moved to '{}'", text::path_to_utf8(report.quarantine_path.filename()));
            } else {
                log::error("settings: could not quarantine the damaged file; it will not be overwritten");
                read_only_ = true;
                report.read_only = true;
            }
        } else {
            read_only_ = true;
            report.read_only = true;
        }
        return report;
    }

    raw_ = std::move(parsed.doc);
    yyjson_mut_val* root = yyjson_mut_doc_get_root(raw_.get());
    Reader r;

    std::int64_t version = 0;
    const json::Field fv = json::get_int(root, "schemaVersion", 1, INT32_MAX, version);
    if (fv != json::Field::Ok) {
        r.count(json::Field::Invalid, "schemaVersion");
        version = lim::kSchemaVersion;
    }
    if (version > lim::kSchemaVersion) {
        read_only_ = true;
        report.read_only = true;
        log::warn("settings: file written by a newer version (schema {}); opening read-only", version);
    }

    std::string language;
    json::Field fl = json::get_string(root, "language", 64, language);
    if (fl == json::Field::Ok && !text::is_valid_language_setting(language)) {
        fl = json::Field::Invalid;
    }
    if (fl == json::Field::Ok) {
        settings_.language = language;
    }
    r.count(fl, "language");

    if (yyjson_mut_val* d = r.read_section(root, "display")) {
        read_display(r, d, settings_.display);
    }
    if (yyjson_mut_val* a = r.read_section(root, "audio")) {
        read_audio(r, a, settings_.audio);
    }
    if (yyjson_mut_val* g = r.read_section(root, "graphics")) {
        read_graphics(r, g, settings_.graphics);
    }
    if (yyjson_mut_val* in = r.read_section(root, "input")) {
        read_input(r, in, settings_.input);
    }
    if (yyjson_mut_val* u = r.read_section(root, "ui")) {
        read_ui(r, u, settings_.ui);
    }
    if (yyjson_mut_val* gp = r.read_section(root, "gameplay")) {
        read_gameplay(r, gp, settings_.gameplay);
    }

    report.ignored_fields = r.ignored;
    if (r.ignored > 0) {
        log::warn("settings: {} invalid field(s) ignored", r.ignored);
    }
    return report;
}

bool SettingsStore::save() {
    if (read_only_) {
        log::info("settings: not saving, the settings file is read-only");
        return false;
    }
    json::MutDoc doc;
    if (raw_) {
        doc.reset(yyjson_mut_doc_mut_copy(raw_.get(), nullptr));
    } else {
        doc = json::new_object_doc();
    }
    if (!doc || !write_settings(doc.get(), settings_)) {
        log::error("settings: out of memory while serializing");
        return false;
    }
    const std::string text = json::write_pretty(doc.get());
    if (text.empty() || text.size() > lim::kMaxFileBytes) {
        log::error("settings: serialized settings are empty or too large");
        return false;
    }

    std::error_code ec;
    std::filesystem::create_directories(file_.parent_path(), ec);
    const fs::IoError err = fs::write_file_atomic(file_, text, [](std::string_view back) {
        return json::parse_object(back).error == json::ParseError::None;
    });
    if (err != fs::IoError::None) {
        log::error("settings: save failed ({}); previous file kept", fs::io_error_name(err));
        return false;
    }
    raw_ = std::move(doc);
    return true;
}

}  // namespace sc
