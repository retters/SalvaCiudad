// Game content defined as data by the mods (section 5.4): resources,
// buildings, recipes, natural features and flora. The game's mod loader
// reads and validates the JSON files and fills a Content; the simulation
// only reads it. Integers only, like the rest of the simulation.
#pragma once

#include <array>
#include <cstdint>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

#include "sim/flora.h"
#include "sim/map.h"

namespace sc::sim {

// Index of a definition in its list; stable for a given set of mods.
using DefIndex = std::uint16_t;
inline constexpr DefIndex kNoDef = 0xFFFF;

enum class ResourceCategory : std::uint8_t { Food, Material, Fuel, Good, Count };

struct ResourceDef {
    std::string id;           // "core:log"
    std::string name_key;     // Text key, from the mod's language files.
    ResourceCategory category = ResourceCategory::Material;
    std::int32_t nutrition = 0;  // Food points per unit (Food only).
    std::int32_t weight = 1;     // Units a villager carries per trip: 12 / weight.
};

struct ResourceAmount {
    DefIndex resource = kNoDef;
    std::int32_t amount = 0;
};

// What the workers of a building do; each kind is implemented in C++.
enum class WorkKind : std::uint8_t {
    None,
    Gather,   // Harvest natural features of one kind nearby.
    Produce,  // Turn inputs into outputs with the building's recipes.
    Build,    // Construct and demolish (the builder's hut).
    Haul,     // Carry goods between buildings.
    Farm,     // Fields (phase 11).
    Hunt,
    Fish,
    Count
};

enum class BuildingKind : std::uint8_t { House, Storage, Workplace, TownCenter, Decoration, Defense, Military, Count };

struct BuildingDef {
    std::string id;
    std::string name_key;
    std::string model;          // Path inside the mod, "models/house.glb".
    std::string mod;            // Id of the mod that defines it (for the model path).
    BuildingKind kind = BuildingKind::Workplace;
    std::int32_t width = 4;     // Footprint in cells, before rotation.
    std::int32_t depth = 4;
    std::vector<ResourceAmount> cost;
    std::int32_t build_work = 100;  // Worker-ticks to build.
    std::int32_t workers = 0;       // Most workers.
    WorkKind work = WorkKind::None;
    std::uint8_t gathers = 0;       // FeatureKind bits, for Gather.
    std::int32_t work_radius = 0;   // Meters, for Gather/Hunt/Fish.
    std::int32_t residents = 0;     // Houses.
    std::int32_t storage = 0;       // Units it can store.
    std::uint8_t stores = 0;        // ResourceCategory bits it accepts.
    std::vector<DefIndex> recipes;  // Produce.
    std::int32_t tier = 0;          // Town center tier needed.
    std::int32_t desirability = 0;  // Effect on nearby homes (phase 12).
    bool unique = false;            // Only one per player (town center).
};

struct RecipeDef {
    std::string id;
    std::vector<ResourceAmount> inputs;
    std::vector<ResourceAmount> outputs;
    std::int32_t work = 50;  // Worker-ticks per batch.
};

// Natural features of the map, as things to harvest.
using FeatureKind = FeatureType;  // The map's natural features.

struct FeatureDef {
    std::string id;
    FeatureKind kind = FeatureKind::Tree;
    DefIndex resource = kNoDef;
    std::int32_t amount = 10;      // Units per feature (trees: per size, see below).
    std::int32_t work = 20;        // Worker-ticks per unit.
    std::int32_t regrow_days = 0;  // Berries and herbs grow back; 0 = never.
    std::string model;             // Path inside the mod (trees use their species).
    std::string mod;
};

struct Content {
    std::vector<ResourceDef> resources;
    std::vector<BuildingDef> buildings;
    std::vector<RecipeDef> recipes;
    std::vector<FeatureDef> features;
    Flora flora;

    // Hash of the mods that affect the simulation (section 7.4), for
    // multiplayer checks and save files.
    std::uint64_t hash = 0;

    [[nodiscard]] DefIndex find_resource(std::string_view id) const;
    [[nodiscard]] DefIndex find_building(std::string_view id) const;
    [[nodiscard]] DefIndex find_recipe(std::string_view id) const;
    [[nodiscard]] const FeatureDef* feature(FeatureKind kind) const;
};

}  // namespace sc::sim
