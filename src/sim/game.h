// The village game (phase 8): villagers who walk, work, eat, age, have
// children and die; buildings placed by the players and built in stages by
// laborers; natural resources harvested from the map; storage and food.
// Everything is integer-only and advances only through commands and ticks,
// so every machine computes the same game (section 7.3).
#pragma once

#include <array>
#include <map>
#include <cstdint>
#include <memory>
#include <span>
#include <string>
#include <vector>

#include "sim/climate.h"
#include "sim/command.h"
#include "sim/content.h"
#include "sim/entity.h"
#include "sim/fixed.h"
#include "sim/map.h"
#include "sim/nav.h"
#include "sim/rng.h"
#include "sim/serialize.h"

namespace sc::sim {

// Game time of a normal year: about 20 minutes at x1 (decision D-801).
// A game's own year may be shorter or longer (GameRules, phase 10); use
// Game::year_ticks() and friends for anything inside a game.
inline constexpr std::uint32_t kTicksPerSecond = 10;
inline constexpr std::uint32_t kTicksPerDay = 100;
inline constexpr std::uint32_t kDaysPerMonth = 10;
inline constexpr std::uint32_t kMonthsPerYear = 12;
inline constexpr std::uint32_t kTicksPerMonth = kTicksPerDay * kDaysPerMonth;
inline constexpr std::uint32_t kTicksPerYear = kTicksPerMonth * kMonthsPerYear;

// Rules of the village; also the number that invalidates saves and replays
// when it changes.
inline constexpr std::uint32_t kGameRulesVersion = 10;

namespace village {
inline constexpr std::int32_t kFoodMax = 1000;           // Hunger meter.
inline constexpr std::int32_t kEatBelow = 500;           // Goes to eat under this.
inline constexpr std::uint32_t kTicksPerFoodPoint = 4;   // Hunger: one meter point per 4 ticks.
inline constexpr std::int32_t kFoodPerNutrition = 100;   // Meter points per nutrition point.
inline constexpr std::int32_t kHealthMax = 1000;
inline constexpr std::int32_t kAdultAgeYears = 5;        // Gameplay ages (D-801).
inline constexpr std::int32_t kOldAgeYears = 45;
inline constexpr std::int32_t kCarry = 12;               // Units carried of weight 1.
inline constexpr std::int32_t kStartVillagers = 12;
inline constexpr std::int32_t kMaxVillagersPerPlayer = 1000;
inline constexpr std::int32_t kWarmthMax = 1000;      // Cold meter (phase 10).
inline constexpr std::int32_t kHouseFirewood = 20;    // Firewood a house keeps.
inline constexpr std::int32_t kColdBelow = 10;        // Houses burn firewood below this (°C).
inline constexpr std::int32_t kMaxSnow = 100;
}  // namespace village

// A natural resource of the map (one per map feature, same index).
struct Node {
    std::int32_t amount = 0;        // Units left; 0 = gone (trees, stones) or empty (bushes).
    std::uint32_t reserved = 0;     // Villager entity index + 1 working it, or 0.
    std::uint64_t regrow_tick = 0;  // Bushes refill at this tick; 0 = not waiting.
    bool operator==(const Node&) const = default;
};

enum class BuildingState : std::uint8_t { Construction, Complete };

struct Stock {
    DefIndex resource = kNoDef;
    std::int32_t amount = 0;
    bool operator==(const Stock&) const = default;
};

struct Building {
    DefIndex def = 0;
    std::uint8_t owner = 0;
    std::uint8_t rotation = 0;       // 0..3, quarter turns.
    std::int32_t x = 0;              // Corner cell of the rotated footprint.
    std::int32_t z = 0;
    std::int32_t width = 0;          // Rotated footprint.
    std::int32_t depth = 0;
    BuildingState state = BuildingState::Construction;
    std::vector<Stock> delivered;    // Construction: materials on site.
    std::vector<Stock> incoming;     // Construction: materials on their way.
    std::int32_t work_done = 0;      // Construction work, or recipe progress.
    std::vector<Stock> stock;        // Storage and workplace goods.
    std::vector<EntityId> workers;
    std::int32_t wanted_workers = 0;
    std::vector<EntityId> residents;
    bool heated = true;              // Houses: warm today (firewood, or no need).
    bool operator==(const Building&) const = default;
};

enum class Task : std::uint8_t {
    Idle,          // Deciding.
    Wander,        // Nothing to do: strolls near the town center.
    GoEat,         // Walking to food.
    GoGather,      // Walking to a resource node.
    Gather,        // Working a node.
    GoDeliver,     // Carrying goods to a storage.
    GoFetch,       // Walking to a storage to take goods.
    GoSite,        // Carrying materials to a construction site.
    GoBuild,       // Walking to a site to build.
    Build,         // Building.
    GoWorkplace,   // Walking to the workplace (with recipe inputs).
    Produce,       // Working a recipe.
    Count
};

enum class Sex : std::uint8_t { Male, Female };

struct Villager {
    std::uint8_t owner = 0;
    Sex sex = Sex::Male;
    std::uint8_t race = 0;
    std::uint32_t appearance = 0;     // Random bits for the look (palette, accessories).
    std::uint32_t family = 0;
    std::int64_t born_tick = 0;       // Can be negative: born before the game.
    FixedVec2 position;
    FixedVec2 previous;               // Position one tick ago (for smooth drawing).
    std::int32_t food = village::kFoodMax;
    std::int32_t health = village::kHealthMax;
    std::int32_t warmth = village::kWarmthMax;
    std::int32_t clothes = 0;         // Ticks left of the clothes worn; 0 = none.
    EntityId home;
    EntityId job;                     // Workplace.
    Task task = Task::Idle;
    EntityId target;                  // Building the task is about.
    EntityId site;                    // Construction site the fetched goods are for.
    std::uint32_t node = 0;           // Node index + 1 for gathering, 0 = none.
    std::int32_t timer = 0;           // Ticks of the current work step.
    Stock carrying;
    std::vector<FixedVec2> path;
    std::uint16_t path_index = 0;
    std::int32_t idle_ticks = 0;      // Waits before deciding again.
    bool operator==(const Villager&) const = default;
};

struct PlayerState {
    bool active = false;
    EntityId town_center;
    std::uint32_t next_family = 1;
    std::int32_t births = 0;
    std::int32_t deaths = 0;
    std::int32_t arrivals = 0;
    bool operator==(const PlayerState&) const = default;
};

// Why a building cannot go somewhere.
enum class PlaceError : std::uint8_t { None, UnknownBuilding, OutsideMap, Water, TooSteep, Blocked, Unique, NotYours };

// How a game is set up besides its map.
struct GameSetup {
    std::uint8_t players = 1;
    std::uint64_t seed = 0;
    bool shared_town = false;  // All the players run one town (section 7.7).
    GameRules rules;
};

class Game {
public:
    // Sets up a new game on `map`: a town center, villagers and starting
    // goods at each of the first `players` start positions. With
    // `shared_town`, all the players run one town (section 7.7).
    Game(std::shared_ptr<const Content> content, MapData map, std::uint8_t players, std::uint64_t seed,
         bool shared_town = false);
    Game(std::shared_ptr<const Content> content, MapData map, const GameSetup& setup);

    // Applies a command at the current tick. Invalid ones are ignored and
    // counted, the same on every machine.
    void apply(const Command& command);
    void step();

    [[nodiscard]] std::uint64_t tick() const { return tick_; }
    [[nodiscard]] std::uint64_t hash() const;
    [[nodiscard]] std::uint32_t rejected_commands() const { return rejected_; }

    [[nodiscard]] const Content& content() const { return *content_; }
    [[nodiscard]] const std::shared_ptr<const Content>& content_ptr() const { return content_; }
    [[nodiscard]] const MapData& map() const { return map_; }
    [[nodiscard]] const std::vector<Node>& nodes() const { return nodes_; }
    [[nodiscard]] const EntityRegistry& registry() const { return registry_; }
    [[nodiscard]] const ComponentStore<Villager>& villagers() const { return villagers_; }
    [[nodiscard]] const ComponentStore<Building>& buildings() const { return buildings_; }
    [[nodiscard]] const PlayerState& player(std::uint8_t p) const { return players_[p]; }
    [[nodiscard]] const NavGrid& nav() const { return nav_; }
    [[nodiscard]] std::uint8_t player_count() const { return player_count_; }
    // Whether the developer tools' commands are accepted (single player,
    // or a multiplayer game that allows them). Part of the state.
    [[nodiscard]] bool dev_commands() const { return dev_commands_; }
    // The town a player runs: their own, or the common one.
    [[nodiscard]] std::uint8_t town_of(std::uint8_t player) const { return shared_town_ ? 0 : player; }
    [[nodiscard]] bool shared_town() const { return shared_town_; }

    // Time and weather (phase 10).
    [[nodiscard]] const GameRules& rules() const { return rules_; }
    [[nodiscard]] std::uint32_t year_ticks() const { return sim::year_ticks(rules_.climate.year); }
    [[nodiscard]] std::uint32_t month_ticks() const { return year_ticks() / 12; }
    [[nodiscard]] std::uint32_t day_ticks() const { return month_ticks() / 10; }
    [[nodiscard]] Calendar calendar() const { return sim::calendar(rules_.climate, tick_); }
    [[nodiscard]] std::int32_t temperature() const { return temperature_; }
    [[nodiscard]] std::int32_t snow() const { return snow_; }
    // Freezing: bushes and herbs neither grow back nor can be picked.
    [[nodiscard]] bool frozen() const { return temperature_ <= 0; }

    // Hashes of the parts of the state, to find where two games differ
    // after a desynchronization.
    struct PartHash {
        const char* name;
        std::uint64_t hash;
    };
    [[nodiscard]] std::vector<PartHash> hash_parts() const;
    void set_dev_commands(bool allowed) { dev_commands_ = allowed; }

    // Totals in the player's storage, per resource definition.
    [[nodiscard]] std::vector<std::int32_t> stored(std::uint8_t player) const;
    [[nodiscard]] std::int32_t population(std::uint8_t player, bool adults_only = false) const;
    [[nodiscard]] std::int32_t age_years(const Villager& v) const;
    [[nodiscard]] bool adult(const Villager& v) const;
    // Rotated footprint of a building definition.
    static void footprint(const BuildingDef& def, std::uint8_t rotation, std::int32_t& w, std::int32_t& d);
    // Whether `player` may place `def` with its corner at (x, z).
    [[nodiscard]] PlaceError can_place(std::uint8_t player, DefIndex def, std::int32_t x, std::int32_t z,
                                       std::uint8_t rotation) const;
    // Point in front of a building's door, where villagers go.
    [[nodiscard]] FixedVec2 door(const Building& b) const;
    // Where someone coming from `from` stands to use a building.
    [[nodiscard]] FixedVec2 approach(const Building& b, FixedVec2 from) const;

    // Map features felled or emptied since the last call (for the view).
    [[nodiscard]] std::vector<std::uint32_t> take_changed_nodes();
    // Buildings added, changed or removed since the last call.
    [[nodiscard]] bool take_buildings_changed();

    void save(BinaryWriter& w) const;
    // Replaces this game with a saved one using `content`. On failure the
    // game is left unchanged and false is returned.
    [[nodiscard]] bool load(BinaryReader& r, std::shared_ptr<const Content> content);

private:
    friend class VillageRules;

    std::shared_ptr<const Content> content_;
    MapData map_;
    NavGrid nav_;
    std::vector<Node> nodes_;
    std::vector<std::vector<std::uint32_t>> node_cells_;  // Node indices per 16 m cell.
    std::int32_t node_cells_side_ = 0;
    std::vector<std::uint8_t> occupied_;  // Map cells under buildings.

    std::uint64_t tick_ = 0;
    std::uint64_t seed_ = 0;
    Rng rng_;
    EntityRegistry registry_;
    ComponentStore<Villager> villagers_;
    ComponentStore<Building> buildings_;
    std::array<PlayerState, kMaxPlayers> players_{};
    std::uint8_t player_count_ = 0;
    std::uint32_t rejected_ = 0;
    bool dev_commands_ = true;
    bool shared_town_ = false;
    GameRules rules_;
    std::int32_t temperature_ = 12;  // Today's; follows from the tick.
    std::int32_t snow_ = 0;          // 0..kMaxSnow.
    DefIndex firewood_ = kNoDef;     // Resources the rules use, looked up once.
    DefIndex clothes_ = kNoDef;

    std::vector<std::pair<std::uint64_t, std::uint32_t>> regrow_;  // (tick, node), sorted.
    std::vector<std::uint32_t> changed_nodes_;
    // Walking costs around workplaces (derived, never saved), by entity index.
    std::map<std::uint32_t, std::pair<EntityId, NavGrid::Area>> work_areas_;
    bool buildings_changed_ = true;

    void build_indexes();
};

// Human-readable name of a task (English, for logs and the developer tools).
[[nodiscard]] const char* task_name(Task t);

}  // namespace sc::sim
