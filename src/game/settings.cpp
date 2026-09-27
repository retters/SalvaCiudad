#include "game/settings.h"

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
