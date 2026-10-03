// The map behind the main menu (phase 50): a small map from a list of
// seeds chosen by hand. The list that ships is data/menu_backgrounds.json;
// the developer tools add seeds to a file of the same name in the user's
// folder, which is read after it.
#pragma once

#include <cstdint>
#include <filesystem>
#include <string>
#include <string_view>
#include <vector>

#include "sim/map.h"

namespace sc::menu_backgrounds {

inline constexpr std::string_view kFileName = "menu_backgrounds.json";
inline constexpr std::size_t kMaxSeeds = 256;
inline constexpr std::size_t kMaxFileBytes = 64u * 1024u;
// Used when no list can be read.
inline constexpr std::uint64_t kFallbackSeed = 2026;

// Parses {"schemaVersion": 1, "seeds": ["123", ...]} strictly: seeds are
// decimal strings (they do not fit a JSON number). Returns false, with
// `error` in English for the log, if anything is off.
[[nodiscard]] bool parse(std::string_view text, std::vector<std::uint64_t>& seeds, std::string& error);
[[nodiscard]] std::string to_json(const std::vector<std::uint64_t>& seeds);

// The seeds of a file; empty (with a line in the log) if it is missing or
// not valid.
[[nodiscard]] std::vector<std::uint64_t> load(const std::filesystem::path& file);
// Adds `seed` to the file (atomically). False if it could not be written;
// true also when the seed was already there.
[[nodiscard]] bool add(const std::filesystem::path& file, std::uint64_t seed);

// The seed number `pick` (any number: it wraps) of the two lists together.
[[nodiscard]] std::uint64_t choose(const std::vector<std::uint64_t>& shipped, const std::vector<std::uint64_t>& user,
                                   std::uint64_t pick);

// The map behind the menu: small, with the defaults of a new game.
[[nodiscard]] sim::MapSettings settings_for(std::uint64_t seed);

}  // namespace sc::menu_backgrounds
