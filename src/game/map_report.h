// Map reports (phase 38): what the player marked on the map with Ctrl+F12,
// saved as two screenshots and a reporte.json in a temporary folder, and
// read back by `--reporte <folder>` to show the same view of the same map
// made by the current generator.
#pragma once

#include <array>
#include <cstdint>
#include <filesystem>
#include <functional>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

#include "game/camera.h"
#include "game/terrain_names.h"
#include "math/vec.h"
#include "sim/climate.h"
#include "sim/content.h"
#include "sim/map.h"

namespace sc::report {

inline constexpr int kSchemaVersion = 1;
inline constexpr std::size_t kMaxFileBytes = 4u * 1024u * 1024u;
inline constexpr std::size_t kKeep = 30;               // Reports kept; older ones are deleted.
inline constexpr std::size_t kMaxStrokes = 64;
inline constexpr std::size_t kMaxStrokePoints = 4096;  // Per stroke.
inline constexpr std::size_t kMaxCells = 200'000;      // Marked cells listed.
inline constexpr const char* kFileName = "reporte.json";

// Phase 129: a trip of the camera when the report is shown again, to
// measure how the game runs along it (written by hand). Each step goes
// from where the last one ended (or from the view) to its own place in
// `seconds`.
struct TourStep {
    float seconds = 1.0f;
    std::array<float, 2> offset{};  // x, z meters from the trip's start.
    float yaw = 0.0f;
    float pitch = 0.0f;
    float distance = 0.0f;
};
inline constexpr std::size_t kMaxTourSteps = 64;
struct Tour {
    int speed = 0;         // Game speed in quarters (4 is x1); 0 paused.
    bool at_town = false;  // It starts over the first town's center, not the view's target.
    std::vector<TourStep> steps;
};

// Where the camera was, and the window it drew into.
struct View {
    CameraMode mode = CameraMode::Aerial;
    math::Vec3 target;
    float yaw = 0.0f;
    float pitch = 0.0f;
    float distance = 0.0f;
    std::uint32_t width = 0;
    std::uint32_t height = 0;
    sim::Season season = sim::Season::Spring;
    float snow = 0.0f;  // 0..1, as drawn.
    // Villagers to put in the middle of the view when the report is shown
    // again (--reporte), to measure how a crowd draws. Written by hand.
    std::uint32_t people = 0;
    // Phase 129: written by hand; empty when there is none.
    Tour tour;
};
inline constexpr std::int64_t kMaxReportPeople = 5000;

using Cell = std::array<std::int32_t, 2>;

struct Stroke {
    std::vector<std::array<float, 2>> screen;  // Pixels from the window's top left.
    std::vector<Cell> cells;                   // Under it (and inside it, if closed), sorted, each once.
    bool closed = false;                       // It surrounds an area.
};

// Most points sampled inside a closed stroke: a wide area is sampled more
// sparsely.
inline constexpr std::size_t kMaxAreaSamples = 20'000;

// Whether a stroke ends near where it began, so it surrounds an area: its
// ends within a fifth of its size (at least 24 pixels).
[[nodiscard]] bool closes(const Stroke& stroke);

struct Report {
    std::string created_at;  // Local time, ISO 8601.
    std::string game_version;
    std::string build_id;
    std::uint64_t content_hash = 0;
    std::vector<std::string> mods;  // "id version".
    sim::MapSettings map;
    std::uint16_t generator_version = 0;
    std::uint64_t map_checksum = 0;
    View view;
    bool in_game = false;  // A game (with its town) rather than a bare map.
    sim::FogMode fog = sim::FogMode::None;
    std::optional<Cell> cursor;
    std::vector<Stroke> strokes;
};

// The cells under a stroke: `hit` gives the ground under a screen point
// (none off the map); the stroke is sampled every `step` pixels. A closed
// stroke also gives the cells inside it.
[[nodiscard]] std::vector<Cell> cells_under(const Stroke& stroke,
                                            const std::function<std::optional<math::Vec3>(float, float)>& hit,
                                            float step = 2.0f);

// The report as JSON, with what is under the cursor and a summary of the
// marked cells described by `names`.
[[nodiscard]] std::string to_json(const Report& r, const sim::MapData& map, const sim::Content& content,
                                  TerrainNames& names);

// What `--reporte` needs from a reporte.json, checked strictly (it is
// untrusted input).
struct Replay {
    std::string game_version;
    std::string build_id;
    std::uint64_t content_hash = 0;
    std::uint16_t generator_version = 0;
    sim::MapSettings map;
    View view;
};
// False with an English message when the file is not a valid report or
// names a map type or biome `content` does not have. Without `content`
// (before the mods are loaded) the map type and biome are left at 0.
[[nodiscard]] bool parse_replay(std::string_view text, const sim::Content* content, Replay& out, std::string& error);

// Paints the strokes over an RGB image, `thickness` pixels wide.
void draw_strokes(std::vector<std::uint8_t>& rgb, std::uint32_t width, std::uint32_t height,
                  const std::vector<Stroke>& strokes, float thickness, std::array<std::uint8_t, 3> color);

// %TEMP%\SalvasProsperia\reportes (or the system's temporary folder elsewhere).
[[nodiscard]] std::filesystem::path base_dir();
// A folder name for a report made now: "2026-09-29_153201".
[[nodiscard]] std::string folder_name_now();
// Whether a name is one of ours (only those are ever deleted).
[[nodiscard]] bool is_report_name(std::string_view name);
// Creates a new folder in `base` for a report, adding "-2", "-3"... if the
// name is taken. Empty on failure.
[[nodiscard]] std::filesystem::path create_folder(const std::filesystem::path& base, const std::string& name);
// Deletes the oldest report folders in `base` beyond `keep`, and only
// folders named like reports holding only the files a report writes.
void prune(const std::filesystem::path& base, std::size_t keep);

// Names in the JSON.
[[nodiscard]] std::string_view camera_mode_name(CameraMode mode);
[[nodiscard]] std::string_view water_name(WaterKind kind);
[[nodiscard]] std::string_view landform_name(sim::LandformKind kind);

}  // namespace sc::report
