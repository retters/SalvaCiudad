// Where the game reads its data and writes the user's files (section 5.1 of
// the specification).
#pragma once

#include <filesystem>
#include <optional>

namespace sc {

struct DataPaths {
    std::filesystem::path install_dir;  // Executable folder; holds data/.
    std::filesystem::path user_dir;     // settings.json, saves/, mods/, logs/.
    bool portable = false;

    [[nodiscard]] std::filesystem::path game_data_dir() const { return install_dir / "data"; }
    [[nodiscard]] std::filesystem::path settings_file() const { return user_dir / "settings.json"; }
    [[nodiscard]] std::filesystem::path logs_dir() const { return user_dir / "logs"; }
    [[nodiscard]] std::filesystem::path saves_dir() const { return user_dir / "saves"; }
    [[nodiscard]] std::filesystem::path user_mods_dir() const { return user_dir / "mods"; }
};

// Name of the marker file that turns on portable mode.
inline constexpr const char* kPortableMarker = "portable.txt";

// Decides the paths from an executable folder and the per-user folder the
// platform offers. Portable mode (a portable.txt next to the executable)
// keeps everything in <install_dir>/userdata. Testable without SDL.
[[nodiscard]] DataPaths choose_data_paths(const std::filesystem::path& install_dir,
                                          const std::filesystem::path& platform_user_dir);

// Creates the user folders. If a portable folder cannot be created, falls
// back to `platform_user_dir` and turns portable off. Returns false only if
// no user folder could be created at all.
bool prepare_data_paths(DataPaths& paths, const std::filesystem::path& platform_user_dir);

// Asks SDL for the executable folder and the per-user folder, then chooses
// and prepares the paths. Empty on failure.
[[nodiscard]] std::optional<DataPaths> resolve_data_paths();

}  // namespace sc
