// Application settings (settings.json, section 5.2 of the specification).
// Read field by field without trusting the file; written atomically, keeping
// fields that this version does not know.
#pragma once

#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <optional>
#include <string>
#include <string_view>

#include "core/json.h"
#include "game/input_actions.h"

namespace sc {

enum class WindowMode : std::uint8_t { Fullscreen, Windowed, Borderless };

[[nodiscard]] const char* window_mode_to_string(WindowMode mode);
[[nodiscard]] std::optional<WindowMode> window_mode_from_string(std::string_view s);

struct DisplaySettings {
    WindowMode mode = WindowMode::Borderless;
    std::string monitor;          // Display name; empty = primary display.
    int fullscreen_width = 0;     // Exclusive fullscreen mode; 0 = desktop mode.
    int fullscreen_height = 0;
    int window_width = 1600;      // Windowed mode client size.
    int window_height = 900;
    std::optional<int> window_x;  // Windowed position; empty = centered.
    std::optional<int> window_y;
    bool window_maximized = false;
    bool vsync = true;
    int fps_limit = 0;            // 0 = unlimited; otherwise 30..500.
    double ui_scale = 0.0;        // 0 = automatic from DPI; otherwise 0.75..2.0.

    bool operator==(const DisplaySettings&) const = default;
};

struct AudioSettings {
    int master = 80;  // 0..100 each.
    int effects = 100;
    int ambient = 100;
    int music = 70;
    int ui = 100;

    bool operator==(const AudioSettings&) const = default;
};

enum class QualityPreset : std::uint8_t { Low, Medium, High, Ultra, Custom };

[[nodiscard]] const char* quality_preset_to_string(QualityPreset preset);
[[nodiscard]] std::optional<QualityPreset> quality_preset_from_string(std::string_view s);

// Levels are 0..3. Stored now; applied by the 3D renderer from phase 3.
struct GraphicsSettings {
    QualityPreset preset = QualityPreset::High;
    int shadows = 2;        // Off, low, medium, high.
    int draw_distance = 2;  // Short, medium, far, very far.
    int vegetation = 2;     // Low, medium, high, very high.
    int antialiasing = 1;   // Off, FXAA, MSAA 2x, MSAA 4x.

    // Sets the levels of a preset (does nothing for Custom).
    void apply_preset(QualityPreset p);
    // Custom unless the levels match a preset exactly.
    [[nodiscard]] QualityPreset matching_preset() const;

    bool operator==(const GraphicsSettings&) const = default;
};

struct InputSettings {
    KeyBindings bindings;
    double camera_pan_speed = 1.0;  // Multipliers, 0.25..4.0.
    double camera_rotate_speed = 1.0;
    double camera_zoom_speed = 1.0;
    bool invert_zoom = false;
    bool edge_scroll = true;

    bool operator==(const InputSettings&) const = default;
};

struct UiSettings {
    std::string font = "alegreya-sans";  // Id from data/fonts/fonts.json.
    bool show_tooltips = true;
    int tooltip_delay_ms = 500;  // 0..3000.

    bool operator==(const UiSettings&) const = default;
};

struct GameplaySettings {
    int autosave_minutes = 10;  // 0 = off; otherwise 1..120.
    int autosave_keep = 3;      // 1..20.
    bool tutorial_seen = false;

    bool operator==(const GameplaySettings&) const = default;
};

struct Settings {
    std::string language = "auto";  // "auto" or a BCP 47 tag.
    DisplaySettings display;
    GraphicsSettings graphics;
    AudioSettings audio;
    InputSettings input;
    UiSettings ui;
    GameplaySettings gameplay;

    bool operator==(const Settings&) const = default;
};

// Limits and ranges, shared with the tests.
namespace settings_limits {
inline constexpr int kSchemaVersion = 1;
inline constexpr std::size_t kMaxFileBytes = 256u * 1024u;
inline constexpr std::size_t kMaxMonitorNameBytes = 128;
inline constexpr int kMinWindowSize = 640;
inline constexpr int kMaxWindowSize = 16384;
inline constexpr int kMaxWindowCoordinate = 65536;
inline constexpr int kMinFpsLimit = 30;
inline constexpr int kMaxFpsLimit = 500;
inline constexpr double kMinUiScale = 0.75;
inline constexpr double kMaxUiScale = 2.0;
inline constexpr double kMinCameraSpeed = 0.25;
inline constexpr double kMaxCameraSpeed = 4.0;
inline constexpr int kMaxTooltipDelayMs = 3000;
inline constexpr int kMaxAutosaveMinutes = 120;
inline constexpr int kMaxAutosaveKeep = 20;
inline constexpr std::size_t kMaxFontIdBytes = 64;
}  // namespace settings_limits

struct SettingsLoadReport {
    bool created_default = false;  // No file existed.
    bool quarantined = false;      // The file was unreadable and was renamed.
    std::filesystem::path quarantine_path;
    bool read_only = false;        // Written by a newer version; never overwritten.
    int ignored_fields = 0;        // Invalid fields that fell back to defaults.
};

class SettingsStore {
public:
    explicit SettingsStore(std::filesystem::path file);

    SettingsLoadReport load();

    // Writes the current settings atomically. Returns false if the store is
    // read-only or the write failed (the previous file is kept).
    bool save();

    [[nodiscard]] Settings& settings() { return settings_; }
    [[nodiscard]] const Settings& settings() const { return settings_; }
    [[nodiscard]] bool read_only() const { return read_only_; }
    [[nodiscard]] const std::filesystem::path& file() const { return file_; }

private:
    std::filesystem::path file_;
    Settings settings_;
    json::MutDoc raw_;  // Last document read, to keep unknown fields.
    bool read_only_ = false;
};

}  // namespace sc
