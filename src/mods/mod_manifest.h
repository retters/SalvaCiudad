// A mod's `mod.json` (section 5.4), read without trusting it.
#pragma once

#include <cstdint>
#include <string>
#include <string_view>
#include <vector>

namespace sc::mods {

namespace limits {
inline constexpr std::size_t kMaxManifestBytes = 64 * 1024;
inline constexpr std::size_t kMaxIdBytes = 32;
inline constexpr std::size_t kMaxListItems = 32;
inline constexpr std::size_t kMaxTextBytes = 256;
}  // namespace limits

struct Version {
    int major = 0;
    int minor = 0;
    int patch = 0;
    auto operator<=>(const Version&) const = default;
};

// "1.2.3". False if malformed.
[[nodiscard]] bool parse_version(std::string_view text, Version& out);
[[nodiscard]] std::string version_text(const Version& v);

// Game version ranges: ">=1.2.0", "<2.0.0", or both separated by a space.
struct VersionRange {
    Version min{};
    bool has_max = false;
    Version max{};  // Exclusive.
    [[nodiscard]] bool contains(const Version& v) const;
};
[[nodiscard]] bool parse_range(std::string_view text, VersionRange& out);

// Mod ids: 1..32 characters of [a-z0-9_].
[[nodiscard]] bool is_valid_mod_id(std::string_view id);

struct ModManifest {
    std::string id;
    std::string name_key;
    std::string description_key;
    Version version;
    VersionRange game_version;
    std::vector<std::string> authors;
    bool affects_simulation = true;
    std::vector<std::string> dependencies;
    std::vector<std::string> load_after;
};

// Parses and validates. On failure, `errors` explains why (English, for the
// log and the mods screen).
[[nodiscard]] bool parse_manifest(std::string_view json_text, ModManifest& out, std::vector<std::string>& errors);

}  // namespace sc::mods
