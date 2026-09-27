// The player's choice of mods and their order, in `mods.json` in the user
// data folder. Separate from settings.json: changing mods changes the game's
// content, not the app's configuration.
#pragma once

#include <filesystem>
#include <string>
#include <vector>

namespace sc::mods {

struct ModSelection {
    std::vector<std::string> enabled;  // Mod ids in load order (core is implicit).
};

// Reads the file; a missing file gives an empty selection. A damaged file
// is quarantined and an empty selection is returned.
[[nodiscard]] ModSelection load_selection(const std::filesystem::path& file);
// Atomic write. Returns false on failure (logged).
bool save_selection(const std::filesystem::path& file, const ModSelection& selection);

}  // namespace sc::mods
