// Finding mods, choosing their load order and turning their definitions
// into the game's content (sections 5.4 and 7.13). Mods come from the
// game's `data/mods` (the base game `core` and bundled mods) and from the
// user's `mods` folder. Everything read is validated; a mod with errors is
// switched off and its errors are shown in the mods screen, and the game
// keeps working with the others.
#pragma once

#include <cstdint>
#include <filesystem>
#include <string>
#include <vector>

#include "mods/mod_manifest.h"
#include "sim/content.h"

namespace sc::mods {

namespace limits {
inline constexpr std::size_t kMaxMods = 128;
inline constexpr std::size_t kMaxFilesPerMod = 4096;
inline constexpr std::size_t kMaxFileBytes = 64u * 1024u * 1024u;
inline constexpr std::size_t kMaxDefFileBytes = 4u * 1024u * 1024u;
inline constexpr std::size_t kMaxDefsPerFile = 2000;
inline constexpr std::size_t kMaxScriptBytes = 1024u * 1024u;
}  // namespace limits

inline constexpr const char* kCoreModId = "core";

struct ModInfo {
    ModManifest manifest;
    std::filesystem::path dir;
    bool builtin = false;     // From the game's data folder.
    bool enabled = false;     // Chosen by the player (core always).
    bool loaded = false;      // Part of the current content.
    std::uint64_t hash = 0;   // Of all its files, for multiplayer checks.
    std::vector<std::string> errors;  // Why it could not load (English).
};

// A Lua script of a mod, loaded after its definitions.
struct ModScript {
    std::string mod;
    std::filesystem::path dir;
    std::string source;  // scripts/main.lua
};

// A model file a definition uses, found or not (for the model viewer,
// phase 30).
struct ModelRef {
    std::string def_type;  // "building", "mapFeature", "species" or "race".
    std::string def_id;
    std::string name_key;  // The definition's name, if it has one.
    std::string mod;       // Mod whose folder holds the file.
    std::string path;      // Inside that mod: "models/props/rock.glb".
    bool exists = false;
};

struct BuildResult {
    sim::Content content;
    // Every model the definitions use, found or not, including those of
    // mods left out for errors.
    std::vector<ModelRef> model_refs;
    std::vector<ModScript> scripts;
    std::vector<std::filesystem::path> language_files;  // lang/*.json of the loaded mods, in order.
    std::vector<std::string> load_order;                // Mod ids.
    std::vector<std::filesystem::path> dirs;            // Folder of each loaded mod, same order.

    // Folder of a loaded mod; empty if unknown.
    [[nodiscard]] std::filesystem::path dir(std::string_view mod) const;
};

// Safe path of a file inside a mod: relative, with no ".." and no drive or
// root. Empty if rejected.
[[nodiscard]] std::filesystem::path mod_file(const std::filesystem::path& mod_dir, std::string_view relative);

class ModLibrary {
public:
    // Finds every mod folder (with a mod.json) in both places. A user mod
    // with the id of a built-in one is rejected.
    void scan(const std::filesystem::path& builtin_dir, const std::filesystem::path& user_dir, const Version& game);

    // Marks the chosen mods (by id, in the player's order) as enabled.
    void select(const std::vector<std::string>& enabled);

    // Builds the content of `core` plus the enabled mods. Mods whose files
    // have errors, whose dependencies are missing or that form a cycle are
    // left out, with their errors recorded.
    [[nodiscard]] BuildResult build();

    [[nodiscard]] const std::vector<ModInfo>& mods() const { return mods_; }
    [[nodiscard]] std::vector<ModInfo>& mods() { return mods_; }
    [[nodiscard]] const ModInfo* find(std::string_view id) const;
    // Ids of the enabled mods, except core, in the player's order.
    [[nodiscard]] std::vector<std::string> enabled_ids() const;
    // Moves an enabled mod up or down in the player's order.
    void move(std::string_view id, int delta);

private:
    [[nodiscard]] std::vector<std::size_t> load_order();

    std::vector<ModInfo> mods_;
    std::vector<std::string> order_;  // Player's order of mod ids.
};

// Hash of a folder's files, sorted by relative path (FNV-1a, 64 bits).
[[nodiscard]] std::uint64_t hash_folder(const std::filesystem::path& dir, std::string& error);

}  // namespace sc::mods
