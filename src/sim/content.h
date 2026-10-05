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
// Phase 103: kinds of annex a content may have (a bit each in a house).
inline constexpr std::size_t kMaxAnnexes = 16;

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
    // Phase 98: of a hundred units eaten, how many are bad (red mushrooms):
    // who eats one falls ill of the disease that comes from food, unless
    // the town has a healer or a doctor, who tell them apart.
    std::int32_t bad_percent = 0;
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

// Phase 93: the pieces a building that goes in lines (a wall, a fence) is
// drawn with, by how each module joins its neighbors. At rest a straight
// joins east and west, a corner east and north, a tee all but south, an
// end reaches west (north: -Z); the step's east half stands a meter higher.
enum class LinePiece : std::uint8_t { Pillar, End, Straight, Corner, Tee, Cross, Diagonal, Step, Site, Breach, Count };
inline constexpr std::size_t kLinePieces = static_cast<std::size_t>(LinePiece::Count);

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
    std::uint16_t gathers = 0;      // FeatureKind bits, for Gather.
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
    // Phase 100: it needs not all of `service_uses` but any one of them
    // (beer or wine): the first in the list that it has is the one used.
    bool service_any = false;
    // Phase 105: a coop. With no worker, its `coop_hens` hens lay a unit of
    // `coop_gives` (eggs) every `coop_days` days while they have feed: a unit
    // of any of `coop_feed` (grain) lasts them `coop_feed_days` days, and
    // laborers bring it from a storage. A fox takes a hen now and then
    // unless a fence or a guard keeps it out (see village::kCoopFence); each
    // hen less lays its share less, and the flock is whole again in spring.
    DefIndex coop_gives = kNoDef;
    std::int32_t coop_hens = 4;
    std::int32_t coop_days = 3;
    std::vector<DefIndex> coop_feed;
    std::int32_t coop_feed_days = 6;
    // Phase 105: a guard (the dog's kennel): no fox comes to the coops
    // within this many meters of it.
    std::int32_t guard_radius = 0;
    // Phase 104: gardens. A line with `garden_modules` makes a garden of
    // what has that many of its modules (or of its gates) within
    // village::kGardenMeters of its walls. `garden_house`: of a house, which
    // gains `garden_desirability` and, every quarter of the year without
    // frost, sends `garden_gives` to the nearest storage that takes it.
    // `garden_formal`: of a decoration that makes its place nicer, whose
    // desirability then counts double.
    std::int32_t garden_modules = 0;
    bool garden_house = false;
    std::int32_t garden_desirability = 0;
    std::vector<ResourceAmount> garden_gives;
    bool garden_formal = false;
    // Phase 104: a hive. With no worker, it makes `hive_gives` (honey) by
    // the wild flowers within `hive_radius` meters, none in winter, and
    // keeps it (its `storage`) until laborers carry it away.
    DefIndex hive_gives = kNoDef;
    std::int32_t hive_radius = 30;
    // Phase 103: an annex: a small piece that serves every house whose
    // walls are within `annex_radius` meters of its own. A house takes each
    // kind of annex once, however many stand by it. `annex_bit`: which of
    // the content's annexes it is (kMaxAnnexes at most), set by the loader.
    bool annex = false;
    std::int8_t annex_bit = -1;
    std::int32_t annex_radius = 3;
    std::int32_t annex_desirability = 0;  // Added to the environment of its houses.
    std::uint8_t annex_need = kNoNeed;    // Its houses are as happy as with this need met; they do not level up by it.
    std::int32_t annex_happiness = 0;     // Added to the happiness of its houses...
    bool annex_children = false;          // ...those with children only.
    bool annex_rain = false;              // A rain barrel: full, a fire that starts in its house goes out.
    std::int32_t annex_firewood = 0;      // Firewood its houses keep, instead of village::kHouseFirewood.
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
    // Phase 96: its light keeps wolves and bears out at night (a road
    // lantern, the beacon). Needs `light`.
    bool wards = false;
    // Phase 73: the settlers' wagon. Nobody builds or removes it: it comes
    // with a new town, keeps its goods, and goes when the center is built.
    bool cart = false;
    // Phase 93. `line`: the family of walls it belongs to ("": none).
    // Modules of a family (those of 2 x 2) are traced by dragging and join
    // each other; a gate of the family may be placed over them and takes
    // their place. `line_diagonal`: it may be
    // traced at 45 degrees. `line_pieces`: its models by LinePiece (the
    // view's; an empty one: its own model).
    std::string line;
    bool line_diagonal = false;
    std::array<std::string, kLinePieces> line_pieces;
    // Phase 94. `desirability_radius`: meters its desirability reaches (0:
    // the usual 30, fading with the distance); with a reach of its own it
    // counts whole inside it and once, however many of them are there (a
    // hedge of twenty modules is one hedge). `yields`: what `yield_per` of
    // them give once a year, in their `seasons`, to a gatherer that picks
    // fruit and has them in its reach (the berries of a hedge).
    std::int32_t desirability_radius = 0;
    std::vector<ResourceAmount> yields;
    std::int32_t yield_per = 1;
    // Phase 95: roads. `road`: it is a stretch of road, and people walk on
    // it this fast, percent (0: not a road). Traced like a wall; once built
    // it is no building any more but a mark on the ground. A faster road
    // may be traced over a slower one. `road_eraser`: tracing it lays
    // nothing, it takes the roads away. `road_desirability`: what a house
    // gains with its door on it.
    // Phase 100, presentation only: its model in winter (a vineyard's bare vines); empty: the same all year.
    std::string model_winter;
    std::int32_t road = 0;
    bool road_eraser = false;
    std::int32_t road_desirability = 0;
    // Phase 97: with rain it is mud: no faster than the open ground while
    // it rains and the day after.
    bool road_muddy = false;
};

// A stretch of road: a cell of the walking grid.
inline constexpr std::int32_t kRoadModule = 2;
// The kinds of road a game may have (their number fits in a few bits of a cell).
inline constexpr std::size_t kMaxRoadKinds = 15;

// A disease (phase 13): where it comes from, how it spreads, how bad it is.
// (Food, phase 98: nobody catches it from the air; it comes from eating what was bad.)
enum class DiseaseSource : std::uint8_t { Cold, Water, Rats, Food, Count };
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
    return (d.kind == BuildingKind::Defense && d.attack_range <= 0) || d.road > 0;
}

// Phase 91: wild flowers. How thick they grow in a cell, from 0 (none) to
// 100, by its ground, its biome and where it is: they come in patches of a
// few meters on meadows and, thinner, on grass. No state: the same for a
// map on every machine and at any time. The view draws them from spring to
// autumn; the rules that count them (phase 104) say when.
struct Content;
[[nodiscard]] std::int32_t wildflowers(const MapData& map, const Content& content, std::int32_t cx, std::int32_t cz);

// The build categories "plaza", "garden" and "nature" (their places in the
// loader's list of names).
inline constexpr std::uint8_t kPlazaCategory = 7;
inline constexpr std::uint8_t kGardenCategory = 8;
inline constexpr std::uint8_t kNatureCategory = 9;

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
    // Phase 98: what gives once a year, in its seasons (Season bits; 0: not
    // one of these): a hive its honey, a nest its eggs, a stump its
    // mushrooms. It is picked a unit at a time and the feature stays, like
    // the fruit of a tree; out of season it has nothing. `after_rain`: it
    // fills not once a year but every day after a day of rain (a ring of
    // mushrooms); where it never rains, every ten days of its season.
    std::uint8_t seasons = 0;
    bool after_rain = false;
    // Phase 99, presentation only: how what gives by seasons looks without
    // its fruit (`model_green`) and in spring (`model_flower`); empty: as
    // ever. A berry bush's `models` are not variants by the place but by
    // its biome's BushKind, in order: berries, blueberries, brambles.
    std::string model_green;
    std::string model_flower;
    // Phase 102: lying about for anybody to take: when a site wants its
    // resource and no storage has any, a laborer picks it up and carries it
    // straight to the site (loose stones).
    bool loose = false;
    // Phase 102, presentation only: its `models` are not variants by the
    // place but by its biome's RockKind, in order: gray, mossy, sandstone.
    // (A stone deposit's are its three sizes, and after them it may list
    // its small size in mossy and in sandstone.)
    bool rock_of_biome = false;
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
