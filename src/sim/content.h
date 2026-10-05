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

// Most model files a definition (or a building level) can list as
// variants of its look (phase 31).
inline constexpr std::size_t kMaxModelVariants = 8;

// Index of a definition in its list; stable for a given set of mods.
using DefIndex = std::uint16_t;
inline constexpr DefIndex kNoDef = 0xFFFF;

enum class ResourceCategory : std::uint8_t { Food, Material, Fuel, Good, Gold, Count };

// Phase 67: how a resource looks when carried or piled up (presentation
// only: the simulation never reads it).
enum class LoadKind : std::uint8_t { Crate, Logs, Stone, Sack, Basket, Count };

struct ResourceDef {
    std::string id;           // "core:log"
    std::string name_key;     // Text key, from the mod's language files.
    ResourceCategory category = ResourceCategory::Material;
    std::int32_t nutrition = 0;  // Food points per unit (Food only).
    std::int32_t weight = 1;     // Units a villager carries per trip: 12 / weight.
    std::int32_t carry = 0;      // Units per trip in place of 12 / weight; 0 = from the weight (phase 28).
    std::int32_t value = 0;      // Base price in gold; 0 = merchants do not trade it (phase 14).
    LoadKind load = LoadKind::Crate;  // Phase 67; by default food goes in a basket and the rest in a crate.
    // Phase 89: its own pile beside storages, sites and workshops, in three
    // sizes: "<pile>_1.glb" to "<pile>_3.glb" inside the folder of `mod`.
    // Empty: the pile of its kind of load. Presentation only.
    std::string pile;
    std::string mod;
};

// The sizes a pile comes in, and the file of one: "<pile>_<level>.glb".
inline constexpr int kPileLevels = 3;
[[nodiscard]] std::string pile_file(std::string_view pile, int level);

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
    Hunt,     // Game in the map's animal zones.
    Fish,     // Fish from water nearby.
    Explore,  // Phase 66: its worker goes where the player sends it.
    Count
};

enum class BuildingKind : std::uint8_t { House, Storage, Workplace, TownCenter, Decoration, Defense, Military, Market, Count };

// What a home needs to be happy and to grow (phase 12). Service buildings
// provide some of them to the homes within their reach.
enum class Need : std::uint8_t {
    Food,           // A varied diet: three kinds a month.
    Water,          // A well nearby.
    Clothes,
    Shoes,
    Religion,       // A chapel nearby, with its priest.
    Entertainment,  // A tavern nearby, with beer.
    Heating,        // Firewood in the hearth.
    Beauty,         // A pleasant neighborhood.
    Market,         // A market nearby.
    Hygiene,        // A bathhouse nearby (phase 13).
    Healer,         // A healer's hut nearby: sickness is milder.
    Doctor,         // A physician nearby: milder still.
    Count
};
inline constexpr std::uint8_t kNoNeed = 0xFF;

// A level a building can be upgraded to: houses (by themselves, when their
// needs are met) and the town center (by the player).
struct LevelDef {
    std::int32_t residents = 0;     // Houses: room at this level.
    std::vector<ResourceAmount> cost;
    std::int32_t work = 200;
    std::uint16_t needs = 0;        // Need bits that must be met.
    std::int32_t tier = 0;          // Town center level needed.
    std::int32_t population = 0;    // Town center: villagers needed.
    std::vector<std::string> models;  // Its variants; empty: the building's (presentation only).
    std::string models_mod;           // Mod whose folder holds them.
};

// The farthest a building may light (its def's "light").
inline constexpr std::int32_t kMaxLight = 40;

struct BuildingDef {
    std::string id;
    std::string name_key;
    std::vector<std::string> models;  // Variants, paths inside the mod: "models/house.glb" (presentation only).
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
    bool picks_fruit = false;       // Phase 84, for Gather: its workers pick the fruit of the fruit trees too.
    std::int32_t residents = 0;     // Houses.
    std::int32_t storage = 0;       // Units it can store.
    std::uint8_t stores = 0;        // ResourceCategory bits it accepts.
    std::vector<DefIndex> recipes;  // Produce.
    std::int32_t tier = 0;          // Town center tier needed.
    std::int32_t desirability = 0;  // Effect on nearby homes (phase 12).
    bool unique = false;            // Only one per player (town center).
    // Phase 11: when and how much a workplace produces.
    std::uint8_t seasons = 0;       // Season bits it works in (0 = all).
    std::int32_t mature_years = 0;  // Years after it is built before it produces (orchards).
    std::int32_t yearly_limit = 0;  // Most units produced per year (0 = no limit).
    std::int32_t fields = 0;        // Farms: how many fields it can have.
    // Phase 12.
    std::vector<LevelDef> levels;   // Upgrades, in order.
    std::uint8_t service = kNoNeed; // Need it provides to homes nearby.
    std::int32_t service_radius = 0;
    std::vector<ResourceAmount> service_uses;  // Used up each day to provide it (a tavern's beer).
    std::uint8_t category = 0;      // BuildCategory, for the build bar.
    bool fireproof = false;         // Stone: does not catch fire (phase 13).
    bool trade = false;             // Merchants come to it (phase 14).
    // Phase 15: defenses.
    std::int32_t hp = 500;          // Damage raiders must do to break it.
    bool gate = false;              // Villagers walk through; raiders must break it.
    bool trap = false;              // Walkable; hurts the first enemy on it, then rearms.
    std::int32_t attack_range = 0;  // Towers shoot enemies this close (meters).
    std::int32_t attack_damage = 0; // Per shot (towers) or per trap.
    std::int32_t attack_every = 20; // Ticks between shots.
    std::int32_t sight = 12;        // Phase 32: meters it sees from its center (fog of war).
    bool landmark = false;          // Phase 34: its silhouette shows through the fog of war.
    bool trains = false;            // A barracks: turns villagers into soldiers (phase 16).
    std::int32_t worker_sight = 0;  // Phase 66: meters its workers see, if more than their own.
    std::int32_t warmth = 0;        // A campfire: villagers this many meters around it do not get cold while it burns.
    // Phase 69: a lamp, a brazier, the town center: it lights this many
    // meters around it at night (a campfire, while it burns). `cool_light`:
    // the pale blue of what glows by magic, not the color of fire.
    std::int32_t light = 0;
    bool cool_light = false;
    // Phase 73: the settlers' wagon. Nobody builds or removes it: it comes
    // with a new town, keeps its goods, and goes when the center is built.
    bool cart = false;
};

// A disease (phase 13): where it comes from, how it spreads, how bad it is.
enum class DiseaseSource : std::uint8_t { Cold, Water, Rats, Count };
struct DiseaseDef {
    std::string id;
    std::string name_key;
    DiseaseSource source = DiseaseSource::Cold;
    std::int32_t chance = 20;     // Per 10 000 villagers and day, when the source is there.
    std::int32_t contagion = 20;  // Per 1000 and day, for each sick person at home or at work.
    std::int32_t severity = 60;   // Health lost per day, of 1000 (the sick do not heal).
    std::int32_t days = 8;        // How long it lasts.
};

// A kind of soldier (phase 16): trained at a barracks from an adult
// villager and its equipment.
struct UnitDef {
    std::string id;
    std::string name_key;
    std::int32_t health = 500;
    std::int32_t damage = 50;        // Per blow or shot.
    std::int32_t attack_every = 10;  // Ticks between blows.
    std::int32_t range = 2;          // Meters; more than 4 shoots.
    std::int32_t speed = 21;         // Hundredths of a meter per tick.
    std::vector<ResourceAmount> cost;
    std::int32_t train_work = 300;   // Ticks at the barracks.
    std::int32_t power = 1;          // Military power (score).
    std::uint8_t tier = 0;
    std::int32_t sight = 16;         // Phase 32: meters it sees (fog of war).
};

// What a villager's work is, for the races' speeds (phase 19).
enum class Skill : std::uint8_t { Wood, Stone, Forage, Farm, Orchard, Hunt, Fish, Build, Craft, Metal, Count };
inline constexpr std::size_t kSkills = static_cast<std::size_t>(Skill::Count);

// A people (section 7.12): its characters and its traits, all in data.
struct RaceDef {
    std::string id;
    std::string name_key;
    // Its characters (phase 57), files of core (see race_body_file): a
    // villager takes one of its sex. A people with one model for everybody
    // lists it under either. The view's only: the simulation never reads them.
    std::vector<std::string> bodies_male;
    std::vector<std::string> bodies_female;
    // Skin and hair colors its villagers come in (0xRRGGBB); empty: those
    // of each model.
    std::vector<std::uint32_t> skins;
    std::vector<std::uint32_t> hairs;
    // Phase 63: the names its villagers go by, per sex (a people with one
    // list uses it for both). Each fits kMaxNameBytes.
    std::vector<std::string> names_male;
    std::vector<std::string> names_female;
    std::int32_t move = 100;     // Walking speed, percent.
    std::array<std::int32_t, kSkills> work{100, 100, 100, 100, 100, 100, 100, 100, 100, 100};
    std::int32_t cold = 0;       // Resistance to cold, percent (less warmth lost, less flu); may be negative.
    std::int32_t disease = 0;    // Resistance to every disease, percent.
    bool night_vision = false;   // Not slowed by the dark of the night (phase 70).
    std::int32_t sight = 12;     // Phase 32: meters a villager sees (fog of war).
};

// Phase 65. Walls, palisades, gates and traps follow the ground piece by
// piece: they keep the old slope limit and stand on the ground. Every other
// building has a level floor at the height of the ground by its door, over
// stone foundations.
[[nodiscard]] inline bool follows_ground(const BuildingDef& d) {
    return d.kind == BuildingKind::Defense && d.attack_range <= 0;
}

// Phase 91: wild flowers. How thick they grow in a cell, from 0 (none) to
// 100, by its ground, its biome and where it is: they come in patches of a
// few meters on meadows and, thinner, on grass. No state: the same for a
// map on every machine and at any time. The view draws them from spring to
// autumn; the rules that count them (phase 104) say when.
struct Content;
[[nodiscard]] std::int32_t wildflowers(const MapData& map, const Content& content, std::int32_t cx, std::int32_t cz);

// The build category "plaza" (its place in the loader's list of names).
inline constexpr std::uint8_t kPlazaCategory = 7;

// Path of a character's model inside the core mod:
// "models/characters/<body>.glb".
[[nodiscard]] std::string race_body_file(std::string_view body);
inline constexpr std::size_t kMaxRaceBodies = 8;   // Per sex.
inline constexpr std::size_t kMaxRaceColors = 12;  // Skins, and hairs.
inline constexpr std::size_t kMaxRaceNames = 64;   // Per sex.

// A tutorial (section 6.5): a map and steps, each with a text, a goal that
// ends it and the part of the interface to point at.
enum class TutorialGoal : std::uint8_t { None, Camera, Place, Build, Workers, Speed, Stock, Population, Lua, Count };
struct TutorialStep {
    std::string text_key;
    TutorialGoal goal = TutorialGoal::None;
    std::string target;     // A building or resource id, or a Lua function.
    std::int32_t amount = 1;
    std::string highlight;  // "build:<id>", "workers", "speed", "dock:<id>".
};
struct TutorialDef {
    std::string id;
    std::string name_key;
    std::string mod;        // Whose main.lua has its Lua goals.
    std::int32_t seed = 1;
    std::uint8_t size = 0;  // MapSize.
    std::vector<TutorialStep> steps;
};

// Groups of the build bar.
enum class BuildCategory : std::uint8_t { Housing, Food, Resources, Industry, Services, Decoration, Defense, Count };

// A crop for the fields (phase 11).
struct CropDef {
    std::string id;
    std::string name_key;
    DefIndex resource = kNoDef;
    std::int32_t yield = 10;       // Units per 10 cells at full fertility.
    std::int32_t grow_days = 40;   // Days of growing weather (5 °C or more) to ripen.
    std::int32_t fertility = -10;  // Change to the field's fertility after a harvest.
    bool hardy = false;            // Survives frost.
    // Phase 90: how it looks in a field, as plots of 2 x 2 m, one per two
    // cells: its three stages (sprouts, green, ripe), files inside the
    // folder of `mod`. None: the plain plants of before. `sways`: it bends
    // with the wind. Presentation only.
    std::vector<std::string> models;
    std::string mod;
    bool sways = false;
};
inline constexpr std::size_t kCropStages = 3;

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
    std::vector<std::string> models;  // Variants, paths inside the mod (trees use their species).
    std::string mod;
    bool landmark = false;         // Phase 34: its silhouette shows through the fog of war.
};

struct Content {
    std::vector<ResourceDef> resources;
    std::vector<BuildingDef> buildings;
    std::vector<RecipeDef> recipes;
    std::vector<FeatureDef> features;
    std::vector<CropDef> crops;
    std::vector<DiseaseDef> diseases;
    std::vector<UnitDef> units;
    std::vector<TutorialDef> tutorials;
    std::vector<RaceDef> races;
    Flora flora;

    // Hash of the mods that affect the simulation (section 7.4), for
    // multiplayer checks and save files.
    std::uint64_t hash = 0;

    [[nodiscard]] DefIndex find_resource(std::string_view id) const;
    [[nodiscard]] DefIndex find_building(std::string_view id) const;
    [[nodiscard]] DefIndex find_recipe(std::string_view id) const;
    [[nodiscard]] DefIndex find_crop(std::string_view id) const;
    [[nodiscard]] const FeatureDef* feature(FeatureKind kind) const;
};

}  // namespace sc::sim
