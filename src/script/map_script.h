// Mod rules for generated maps: each mod's main.lua may define
// `on_map_generated(map)`, which can read the map and add features with a
// deterministic random generator (docs/CREAR_MODS.md). Runs on the map
// generation thread; one Lua state per mod, created for each map.
#pragma once

#include <string>
#include <vector>

#include "mods/mod_library.h"
#include "sim/worldgen.h"

namespace sc::script {

class MapScripts final : public sim::MapHooks {
public:
    MapScripts(const std::vector<mods::ModScript>& scripts, const sim::Content& content);

    bool map_generated(sim::MapData& map) override;

    // Script errors (English), "mod: message". A failing script does not
    // stop the map: its rule is skipped.
    [[nodiscard]] const std::vector<std::string>& errors() const { return errors_; }

private:
    const std::vector<mods::ModScript>& scripts_;
    const sim::Content& content_;
    std::vector<std::string> errors_;
};

}  // namespace sc::script
