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
inline constexpr std::uint32_t kGameRulesVersion = 15;

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

// A farm's field (phase 11): a rectangle of cells, a plan of three years
// (a crop or fallow each), and this year's progress.
enum class FieldState : std::uint8_t { Waiting, Growing, Ripe, Done, Count };
inline constexpr std::int32_t kMinFieldSide = 4;
inline constexpr std::int32_t kMaxFieldSide = 20;
inline constexpr std::size_t kPlanYears = 3;

struct Field {
    std::int32_t x = 0;
    std::int32_t z = 0;
    std::int32_t w = 0;
    std::int32_t d = 0;
    std::array<DefIndex, kPlanYears> plan{kNoDef, kNoDef, kNoDef};  // Crop per year; kNoDef = fallow.
    std::uint8_t slot = 0;          // This year's place in the plan.
    FieldState state = FieldState::Waiting;
    DefIndex crop = kNoDef;         // What was sown this year.
    std::int32_t work = 0;          // Sowing progress.
    std::int32_t growth = 0;        // 0..1000.
    std::int32_t fertility = 60;    // 0..100.
    std::int32_t pending = 0;       // Harvest left to bring in.
    std::uint32_t year = 0;         // The calendar year this cycle belongs to.
    std::int32_t fertilized = 0;    // Compost spread this year.
    bool operator==(const Field&) const = default;
};

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
    std::vector<Field> fields;       // Farms.
    std::int64_t built_tick = 0;     // When it was finished (orchards mature).
    std::uint32_t produced_year = 0; // Workplaces with a yearly limit.
    std::int32_t produced = 0;
    // Phase 12.
    std::uint8_t level = 0;          // Upgrades done (houses, the town center).
    bool upgrading = false;          // Materials and work for the next level.
    std::int32_t limit = 0;          // Workplaces: stock of their product to reach (0 = automatic).
    std::uint8_t recipe = 0;         // The recipe being worked.
    std::uint16_t needs = 0;         // Houses: Need bits met today.
    std::int32_t happiness = 50;     // Houses: 0..100.
    std::int32_t desirability = 0;   // Houses: how pleasant the place is.
    // Phase 13.
    std::int32_t fire = 0;           // 0 = not burning; else 1..100.
    std::int32_t burned = 0;         // Damage from fire, 0..1000 (then it is gone).
    // Phase 15.
    std::int32_t damage = 0;         // From raiders; at its def's hp it breaks.
    std::int32_t rearm = 0;          // Traps: ticks until armed again.
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
    GoField,       // Walking to a field.
    Farm,          // Sowing, spreading compost or harvesting.
    GoHunt,        // Walking to where game lives.
    Hunt,
    GoFish,        // Walking to the water's edge.
    Fish,
    GoFire,        // Running to a burning building.
    FightFire,     // Throwing buckets from a well.
    GoFight,       // Militia: going for an enemy.
    Fight,
    Flee,          // Running from an animal or a raider to the town center.
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
    std::int32_t shoes = 0;           // Ticks left of the shoes worn.
    std::uint8_t disease = 0;         // DiseaseDef index + 1; 0 = healthy.
    std::int32_t sick_days = 0;
    std::int32_t immune_days = 0;     // After an illness.
    std::array<DefIndex, 4> meals{kNoDef, kNoDef, kNoDef, kNoDef};  // The last helpings eaten.
    std::uint8_t meal_index = 0;
    std::uint8_t variety = 0;         // Kinds of food among those helpings.
    std::uint16_t spot = 0;           // Field or animal zone being worked (index + 1).
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

// A good a merchant has: how many and at what prices (coins per unit).
struct MerchantGood {
    DefIndex resource = 0;
    std::int32_t stock = 0;  // Units to sell; buying from the town has no limit.
    std::int32_t buy = 0;    // What the town pays.
    std::int32_t sell = 0;   // What the town gets.
    bool operator==(const MerchantGood&) const = default;
};

struct PlayerState {
    bool active = false;
    EntityId town_center;
    std::uint32_t next_family = 1;
    std::int32_t births = 0;
    std::int32_t deaths = 0;
    std::int32_t arrivals = 0;
    std::int32_t departures = 0;      // Unhappy villagers who left.
    std::int32_t burned_down = 0;     // Buildings lost to fire.
    // Phase 14: the treasury and the merchant from the surroundings.
    std::int32_t coins = 0;
    std::uint64_t merchant_arrives = 0;  // Tick; 0 = not yet planned.
    std::uint64_t merchant_leaves = 0;   // Tick; past it, no merchant.
    std::vector<MerchantGood> merchant;  // What this merchant sells and buys.
    // Phase 15.
    bool alarm = false;                  // The bell: adults fight, children hide.
    std::uint64_t next_raid = 0;         // Tick; 0 = not yet planned.
    std::int32_t raids = 0;
    bool operator==(const PlayerState&) const = default;
};

// Animals and raiders (phase 15). Animals live in a zone of the map;
// raiders come from the edge to rob or burn a town, then go back.
enum class CreatureKind : std::uint8_t { Deer, Boar, Wolf, Bear, Raider, Count };
enum class CreatureState : std::uint8_t { Wander, Flee, Chase, Approach, Bash, Leave, Count };

struct Creature {
    CreatureKind kind = CreatureKind::Deer;
    CreatureState state = CreatureState::Wander;
    std::uint8_t town = 0;        // Raiders: the town raided.
    std::uint16_t zone = 0;       // Animals: their zone.
    FixedVec2 position;
    FixedVec2 previous;           // Last tick's position (for the view).
    FixedVec2 home;               // Zone center, or where raiders came from.
    FixedVec2 goal;
    std::vector<FixedVec2> path;  // Raiders.
    std::uint16_t path_index = 0;
    std::int32_t health = 100;
    std::int32_t timer = 0;
    EntityId target;              // A villager (chase) or a building (raid, bash).
    Stock loot;
    bool operator==(const Creature&) const = default;
};

// Trade between players (phase 14): the offer holds the sender's goods
// until it is answered.
struct TradeOffer {
    std::uint32_t id = 0;
    std::uint8_t from = 0;
    std::uint8_t to = 0;
    DefIndex give = 0;  // A resource or kCoins.
    std::int32_t give_amount = 0;
    DefIndex want = 0;
    std::int32_t want_amount = 0;
    std::uint64_t expires = 0;
    bool operator==(const TradeOffer&) const = default;
};

// Goods on the road (or on the world map) to another town.
struct Caravan {
    std::uint8_t from = 0;
    std::uint8_t to = 0;
    DefIndex resource = 0;  // Or kCoins.
    std::int32_t amount = 0;
    std::uint64_t departs = 0;
    std::uint64_t arrives = 0;
    bool operator==(const Caravan&) const = default;
};

// Why a building cannot go somewhere.
enum class PlaceError : std::uint8_t {
    None,
    UnknownBuilding,
    OutsideMap,
    Water,
    TooSteep,
    Blocked,
    Unique,
    NotYours,
    TooFar,      // A field beyond its farm's reach.
    TooMany,     // A farm with all its fields.
    BadSize,
    Locked,      // Needs a bigger town center.
};

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
    // Whether `player` may add a field of `w` x `d` at (x, z) to `farm`.
    [[nodiscard]] PlaceError can_place_field(std::uint8_t player, EntityId farm, std::int32_t x, std::int32_t z,
                                             std::int32_t w, std::int32_t d) const;
    // The level of a player's town center, from 1.
    [[nodiscard]] std::int32_t tier(std::uint8_t player) const;
    // How happy a player's villagers are, 0..100 (homes weighted by residents).
    [[nodiscard]] std::int32_t happiness(std::uint8_t player) const;
    // Room in a house at its level.
    [[nodiscard]] std::int32_t capacity(const Building& b) const;
    // Villagers of a player's town who are sick; buildings on fire.
    [[nodiscard]] std::int32_t sick(std::uint8_t player) const;
    [[nodiscard]] std::int32_t fires() const { return fires_; }

    // What happened that the player should hear about (for the view).
    struct Event {
        enum class Kind : std::uint8_t {
            FireStarted,
            BurnedDown,
            Outbreak,
            MerchantArrived,
            MerchantLeft,
            OfferReceived,
            OfferAnswered,  // `value`: 1 accepted, 0 declined.
            CaravanArrived,
            RaidStarted,     // `value`: raiders.
            Attacked,        // A villager hurt by an animal (`value`: its kind) or a raider.
        };
        Kind kind = Kind::FireStarted;
        std::uint8_t owner = 0;
        EntityId entity;
        FixedVec2 at;
        std::uint16_t value = 0;  // Disease index, for outbreaks.
        std::uint8_t other = 0;   // The other player, for trade.
    };
    [[nodiscard]] std::vector<Event> take_events();

    // Trade (phase 14).
    [[nodiscard]] bool merchant_here(std::uint8_t player) const;
    [[nodiscard]] const std::vector<TradeOffer>& offers() const { return offers_; }
    [[nodiscard]] const std::vector<Caravan>& caravans() const { return caravans_; }
    [[nodiscard]] std::uint32_t next_offer() const { return next_offer_; }
    // Ticks a caravan takes between two towns.
    [[nodiscard]] std::uint64_t travel_ticks(std::uint8_t from, std::uint8_t to) const;
    // Goods of a town in its storages that trade can take.
    [[nodiscard]] std::int32_t tradeable(std::uint8_t player, DefIndex resource) const;
    // Separate maps: the region of a player's town, in cells (x, z, side).
    struct Region {
        std::int32_t x = 0;
        std::int32_t z = 0;
        std::int32_t size = 0;
    };
    [[nodiscard]] Region region(std::uint8_t player) const;

    // Animals and raiders (phase 15).
    [[nodiscard]] const ComponentStore<Creature>& creatures() const { return creatures_; }
    [[nodiscard]] static bool hostile(CreatureKind kind) {
        return kind == CreatureKind::Wolf || kind == CreatureKind::Bear || kind == CreatureKind::Raider;
    }
    [[nodiscard]] std::int32_t raiders_near(std::uint8_t player) const;
    // Whether animals of a zone live there (no predators by a starting town).
    [[nodiscard]] bool zone_open(std::size_t zone) const;

    // Animals left in each of the map's zones (hunting).
    [[nodiscard]] const std::vector<std::int32_t>& zone_animals() const { return zone_animals_; }
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
    DefIndex fertilizer_ = kNoDef;
    DefIndex meat_ = kNoDef;
    DefIndex hide_ = kNoDef;
    DefIndex fish_ = kNoDef;
    DefIndex shoes_ = kNoDef;
    std::vector<std::int32_t> zone_animals_;
    std::int32_t fires_ = 0;          // Buildings burning (follows from them).
    std::vector<TradeOffer> offers_;
    ComponentStore<Creature> creatures_;
    std::vector<Caravan> caravans_;
    std::uint32_t next_offer_ = 1;
    std::vector<Event> events_;

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
