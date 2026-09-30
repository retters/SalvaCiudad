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

// Levels are 0..3. Vegetation takes effect with the map (phase 6).
struct GraphicsSettings {
    QualityPreset preset = QualityPreset::High;
    int shadows = 2;        // Off, low, medium, high.
    int draw_distance = 2;  // Short, medium, far, very far.
    int vegetation = 2;     // Low, medium, high, very high.
    int antialiasing = 2;   // Off, MSAA 2x, MSAA 4x, MSAA 8x.

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
    // Where the player left the game windows (GameHud's own compact format).
    std::string windows;

    bool operator==(const UiSettings&) const = default;
};

struct GameplaySettings {
    int autosave_minutes = 10;  // 0 = off; otherwise 1..120.
    int autosave_keep = 3;      // 1..20.
    bool tutorial_seen = false;
    // Multiplayer (phase 9). An empty name shows a default one.
    std::string player_name;
    std::string join_address = "127.0.0.1";
    int join_port = 47800;

    bool operator==(const GameplaySettings&) const = default;
};

// The last "New game" form (phase 23), shown again the next time. Choices
// are kept by name: map types, biomes and races by their mod id, since
// their order depends on the mods. One that no longer exists falls back
// to its default. The seed is not kept: each new game gets a fresh one.
struct NewGameSettings {
    std::string size = "medium";    // new_game_names::kSizes
    std::string map_type;           // Empty: the first one.
    std::string biome;              // Empty: the first one.
    int islands = 2;                // Per town, with islands.
    std::string sea = "sometimes";  // new_game_names::kSeas
    std::string water = "normal";   // new_game_names::kAmounts
    std::string forests = "normal";
    std::string resources = "normal";
    std::string relief = "low";     // new_game_names::kReliefs
    std::string landforms = "normal";  // new_game_names::kAmounts
    std::string generator = "classic";  // new_game_names::kGenerators (phase 39)
    int players = 1;
    int seasons = 0b1111;           // Bit per season: spring, summer, autumn, winter.
    std::string year = "normal";    // new_game_names::kYears
    std::string winter = "normal";  // new_game_names::kWinters
    std::string start = "normal";   // new_game_names::kStarts
    std::string diseases = "medium";  // new_game_names::kThreats
    std::string fires = "medium";
    std::string raiders = "medium";
    std::string wildlife = "medium";
    std::string race;               // A race's id, "mixed", or empty for the first.
    int other_races = 20;           // Percent of newcomers.
    int max_population = 1000;
    std::string fog = "static";     // new_game_names::kFogs (phase 32, decision D-3202).
    bool shared_vision = true;

    bool operator==(const NewGameSettings&) const = default;
};

// Names of the choices in NewGameSettings, in the order of the game's own
// values.
namespace new_game_names {
inline constexpr std::string_view kSizes[] = {"small", "medium", "large", "huge", "giant", "colossal"};
inline constexpr std::string_view kAmounts[] = {"low", "normal", "high"};
inline constexpr std::string_view kReliefs[] = {"low", "gentle", "mountainous"};
inline constexpr std::string_view kSeas[] = {"none", "sometimes", "always"};
inline constexpr std::string_view kYears[] = {"short", "normal", "long"};
inline constexpr std::string_view kWinters[] = {"mild", "normal", "harsh"};
inline constexpr std::string_view kStarts[] = {"scarce", "normal", "plenty"};
inline constexpr std::string_view kThreats[] = {"none", "low", "medium", "high", "brutal"};
inline constexpr std::string_view kFogs[] = {"none", "static", "dynamic"};
inline constexpr std::string_view kGenerators[] = {"classic", "hierarchical"};
inline constexpr std::string_view kMixedRace = "mixed";
}  // namespace new_game_names

struct Settings {
    std::string language = "auto";  // "auto" or a BCP 47 tag.
    DisplaySettings display;
    GraphicsSettings graphics;
    AudioSettings audio;
    InputSettings input;
    UiSettings ui;
    GameplaySettings gameplay;
    NewGameSettings new_game;

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
inline constexpr std::size_t kMaxPlayerNameBytes = 32;
inline constexpr std::size_t kMaxAddressBytes = 64;
inline constexpr int kMinPort = 1024;
inline constexpr int kMaxPort = 65535;
// New game (phase 23); the game checks that these match its own limits.
inline constexpr std::size_t kMaxDefIdBytes = 64;
inline constexpr int kMaxIslandsPerTown = 8;
inline constexpr int kMaxPlayers = 12;
inline constexpr int kMinPopulation = 50;
inline constexpr int kMaxPopulation = 1000;
}  // namespace settings_limits

// A host name or IPv4 address to join: letters, digits, dots and dashes.
[[nodiscard]] bool is_valid_address(std::string_view address);
// A mod definition's id as the new game keeps it: lowercase letters,
// digits, ':', '_', '-' and '.', at most kMaxDefIdBytes.
[[nodiscard]] bool is_valid_def_id(std::string_view id);

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
