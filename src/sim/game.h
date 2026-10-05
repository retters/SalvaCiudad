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
#include <optional>
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
#include "sim/vision.h"

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
inline constexpr std::uint32_t kGameRulesVersion = 74;

namespace village {
// A house with people or a workplace with workers lights this far beyond
// its walls (its windows), if its def says nothing.
inline constexpr std::int32_t kOccupiedLight = 6;
// Phase 70: at night, out of the light, villagers walk and work at this
// percent (those of a race that sees at night, as always).
inline constexpr std::int32_t kDarkPercent = 75;
// The light of the simulation is kept in cells of this many meters.
inline constexpr std::int32_t kLightCell = 4;
// Phase 71: energy. A point a tick while up and about: eight minutes at
// x1. Resting at home gives it back in two; with no home, by a campfire or
// the town center, in four.
// Phase 72: the night's dangers. Wolves and bears notice villagers from
// half again as far and roam this much farther from their dens; towers,
// soldiers and the militia do this percent of their damage to what stands
// in the dark; with fog of war, everybody sees half as far.
inline constexpr std::int32_t kNightAggroPercent = 150;
inline constexpr std::int32_t kNightRoamMeters = 15;
// Phase 96: how long a beast that was chasing somebody waits at the edge of
// a light that keeps it out before it gives up, in ticks.
inline constexpr std::int32_t kWardWaitTicks = 100;
inline constexpr std::int32_t kDarkAimPercent = 75;
inline constexpr std::int32_t kEnergyMax = 4800;
inline constexpr std::int32_t kRestGain = 4;
inline constexpr std::int32_t kRestGainOutside = 2;
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
// Phase 113. A happening begins on a day the seed of the game decides, is
// seen where it is for a few days and leaves the town it is for in a good
// mood: kMoodPoints of happiness for all its houses during kMoodDays days,
// fewer in the last ones. The whales pass a day of every autumn, for the
// towns with a building within kWhaleMeters of the sea (their next merchant
// comes in half the time that was left); the lanterns go up one night a
// year in every town with kLanternFolk of a people that has the custom:
// the first night from the day the seed gives (that day, in a game without
// nights) on which the town has them.
inline constexpr std::int32_t kMoodPoints = 3;
inline constexpr std::uint32_t kMoodDays = 10;
inline constexpr std::int32_t kWhaleMeters = 150;
inline constexpr std::uint32_t kWhaleDays = 4;    // (A day of the calendar is ten seconds at x1.)
inline constexpr std::uint32_t kLanternDays = 4;
inline constexpr std::int32_t kLanternFolk = 2;
// Phase 112. A unicorn grazes in its glade until somebody fells a tree
// within the radius of the glade: then it is gone for good. While it is
// there, a place within kUnicornMeters of the middle of the glade has
// kUnicornBeauty more of surroundings, and the sick whose home is that near
// get well twice as fast. A town sees it the first time one of its people
// comes within kUnicornSight meters of the glade.
inline constexpr std::int32_t kUnicornMeters = 60;
inline constexpr std::int32_t kUnicornBeauty = 8;
inline constexpr std::int32_t kUnicornSight = 60;
// Phase 111. Mammoths: kMammoths come to each of their zones when winter
// begins and those left go when it ends. A lodge goes for them only with
// two hunters and a weapon of the kLodgeArms it keeps (laborers bring them
// while there are mammoths in its reach); the two set out together, each
// with kMammothFood of food and kMammothEnergy of energy at least (one who
// has less eats or rests first), one waits for the other at the herd up to
// kMammothWait ticks, and kMammothWork worker-ticks of both bring one down: kMammothMeat of meat, kMammothHides hides and
// kMammothIvory of ivory, and a weapon less. One hunt in kMammothWoundOneIn
// leaves a hunter wounded: kMammothWound of health less, never under
// kWoundLeast by the wound alone. A town hears of a herd that comes within
// kMammothNewsMeters of one of its buildings.
inline constexpr std::int32_t kMammoths = 3;
inline constexpr std::int32_t kLodgeArms = 2;
inline constexpr std::int32_t kMammothFood = 850;
inline constexpr std::int32_t kMammothEnergy = 1600;
inline constexpr std::int32_t kMammothWait = 900;
inline constexpr std::int32_t kMammothWork = 480;
inline constexpr std::int32_t kMammothMeat = 40;
inline constexpr std::int32_t kMammothHides = 4;
inline constexpr std::int32_t kMammothIvory = 2;
inline constexpr std::int32_t kMammothWoundOneIn = 4;
inline constexpr std::int32_t kMammothWound = 500;
inline constexpr std::int32_t kWoundLeast = 100;
inline constexpr std::int32_t kMammothNewsMeters = 250;
// Phase 110. A fisher's hut fishes at kFishAlone percent of the pace of
// before; each shoal with fish in it and each bank of reeds within its
// reach adds kFishPerSpot, up to kFishMost. Every fish caught with shoals in
// reach comes out of one of them; they fill again when the season changes.
inline constexpr std::int32_t kFishAlone = 50;
inline constexpr std::int32_t kFishPerSpot = 34;
inline constexpr std::int32_t kFishMost = 150;
inline constexpr std::int32_t kFishWork = 45;  // Worker-ticks a fish took, and takes at 100 percent.
// Phase 109. A zone of rabbits holds kRabbits of them, half with a lynx
// within kLynxMeters of it. With kManyRabbits or more, a field of a crop
// they eat that stands in the zone loses kRabbitLoss percent of its harvest,
// unless a fence runs along half its border, a guard is within its reach
// or a lynx is near. A hunter brings kRabbitMeat of meat from one.
inline constexpr std::int32_t kRabbits = 16;
inline constexpr std::int32_t kManyRabbits = 10;
inline constexpr std::int32_t kRabbitLoss = 20;
inline constexpr std::int32_t kRabbitMeat = 2;
inline constexpr std::int32_t kLynxMeters = 60;
// Phase 106. A guard dog (a building with a guard radius) looks every
// kDogTicks: with a wolf, a bear or a raider in its reach it barks (a notice,
// once until kBarkQuietTicks have gone by with nobody there), the villagers
// in its reach run for the town center, and it keeps the nearest wolf at bay,
// biting it for kDogBite each time.
inline constexpr std::int32_t kDogTicks = 10;
inline constexpr std::int32_t kBarkQuietTicks = 600;
inline constexpr std::int32_t kDogBite = 6;
// A house cat: kCatLooks looks (four coats and a kitten); it adds
// kCatBeauty to its house's environment, and kCatJoy to the happiness of the
// houses within kCatMeters where somebody of a people that likes cats lives.
inline constexpr std::int32_t kCatLooks = 5;
inline constexpr std::int32_t kCatBeauty = 2;
inline constexpr std::int32_t kCatJoy = 2;
inline constexpr std::int32_t kCatMeters = 15;
// Phase 105. A coop is safe from the fox with kCoopFence modules of any line
// (a fence, a hedge, a palisade) within kGardenMeters of its walls, or a
// guard in reach. Unsafe, it loses a hen kFoxPercent days in a hundred. It
// keeps kCoopFeed units of feed.
inline constexpr std::int32_t kCoopFence = 4;
inline constexpr std::int32_t kFoxPercent = 4;
inline constexpr std::int32_t kCoopFeed = 4;
// Phase 104. A garden's fence or hedge stands within this of the walls.
inline constexpr std::int32_t kGardenMeters = 3;
// Wild flowers make a house's place nicer: those within kFlowerMeters of its
// walls, a point for every kFlowerPoints of them (see Game::flowers), up to
// kMaxFlowerBeauty; from spring to autumn.
inline constexpr std::int32_t kFlowerMeters = 6;
inline constexpr std::int32_t kFlowerPoints = 1200;
inline constexpr std::int32_t kMaxFlowerBeauty = 5;
// A hive looks at one place in kHiveStep meters each way, and makes a unit
// for every kNectarPerUnit of flowers it finds in a day.
inline constexpr std::int32_t kHiveStep = 2;
inline constexpr std::int32_t kNectarPerUnit = 40000;
// Phase 103: a rain barrel is empty after this many days without rain.
inline constexpr std::int32_t kBarrelDryDays = 10;
inline constexpr std::int32_t kColdBelow = 10;        // Houses burn firewood below this (°C).
inline constexpr std::int32_t kMaxSnow = 100;
// Phase 66. With this little food to spare over what the walk to the
// food takes, a villager leaves what it is doing and goes to eat.
inline constexpr std::int32_t kHungryFood = 60;
// An explorer's provisions, in hunger meter points: two full meters.
inline constexpr std::int32_t kProvisions = 2000;
// An order to a point this near its own building sends an explorer home.
inline constexpr std::int32_t kHomeMeters = 12;
// Phase 102: a laborer picks up what lies loose (stones) for a site that
// wants it, within this many meters of the site.
inline constexpr std::int32_t kLooseMeters = 100;
}  // namespace village

// Phase 66: what an explorer under orders is doing.
enum class Order : std::uint8_t {
    None,
    Provision,  // Going for provisions before leaving.
    Going,      // On its way to the point.
    Waiting,    // There (or as far as it got).
    Returning,  // On its way home: sent, or out of provisions, or cold.
    Count
};

// Phase 93: tracing. Walls, fences and the like go in lines of modules of
// 2 x 2 m on a lattice of even cells. A trace goes from the module of one
// cell to the module of another: straight if they share a row or a column;
// at 45 degrees if `diagonal` and they are as far apart on both; else an L,
// along x first unless `z_first`. At most kMaxTrace modules (the rest of a
// longer one is left out). Returns each module's corner cell, in order.
inline constexpr std::int32_t kTraceModule = 2;
inline constexpr std::size_t kMaxTrace = 64;
[[nodiscard]] std::vector<std::pair<std::int32_t, std::int32_t>> trace_cells(std::int32_t x0, std::int32_t z0, std::int32_t x1,
                                                                            std::int32_t z1, bool z_first, bool diagonal);

// A natural resource of the map (one per map feature, same index).
struct Node {
    std::int32_t amount = 0;        // Units left; 0 = gone (trees, stones) or empty (bushes).
    std::uint32_t reserved = 0;     // Villager entity index + 1 working it, or 0.
    std::uint64_t regrow_tick = 0;  // Bushes refill at this tick; 0 = not waiting.
    // Phase 84, fruit trees: the fruit picked in the year `fruit_year`.
    std::uint32_t fruit_year = 0;
    std::int32_t fruit_picked = 0;
    // Phase 86, trees: the day (counted from the first of year 1, 120 a
    // year) it goes up a size; kNeverGrows if it is as large as its species
    // gets. A sprout (a tree with nothing to fell that waits in `regrow_tick`)
    // becomes its species' smallest size at that tick.
    std::uint32_t grow_day = 0;
    bool operator==(const Node&) const = default;
};

// Phase 86: trees grow. A tree goes up a size a year after reaching the
// one it has, and from large to huge in two; a sprout is a tree in a year.
inline constexpr std::uint32_t kNeverGrows = 0xFFFFFFFFu;
inline constexpr std::uint32_t kDaysPerYear = 120;
[[nodiscard]] constexpr std::uint32_t growth_years(TreeSize from) {
    return from == TreeSize::Large ? 2 : 1;
}
// The day of the year (0..119) a tree has its birthday, by where it stands:
// the forest does not grow all on one day.
[[nodiscard]] constexpr std::uint32_t tree_birthday(const MapFeature& f) {
    std::uint32_t k = static_cast<std::uint32_t>(f.x.raw()) * 0x9E3779B1u ^ static_cast<std::uint32_t>(f.z.raw()) * 0x85EBCA77u;
    k ^= k >> 15;
    k *= 0x2C1B3C6Du;
    k ^= k >> 12;
    return k % kDaysPerYear;
}

enum class BuildingState : std::uint8_t { Construction, Complete };

// Phase 81: whether a workplace that lives off the land has something to
// take within its reach. Waiting: only what grows back is left, empty or
// frozen today (or, for hunters and fishers, no game or no open water).
// Exhausted: nothing is left of what does not grow back.
// OnlyFruit (phase 85): a woodcutter told to spare the fruit trees has
// nothing else left; it is told like Exhausted, in its own words.
// Growing (phase 87): a woodcutter has only sprouts, or trees too young
// for one told to fell the grown ones; it waits, without a word.
enum class Supply : std::uint8_t { Fine, Waiting, Exhausted, OnlyFruit, Growing, Count };

// Phase 85: what the player lets a workplace do, as bits of
// Building::options; the SetOption command names one by its number.
namespace option {
inline constexpr std::uint8_t kFellFruit = 1u << 0;   // A woodcutter fells the fruit trees too.
inline constexpr std::uint8_t kReplant = 1u << 1;     // Phase 87: it plants a sprout where it felled a tree.
inline constexpr std::uint8_t kMatureOnly = 1u << 2;  // Phase 87: it fells only the grown trees.
inline constexpr std::uint8_t kCount = 3;
}  // namespace option
// The options a workplace of this kind has.
[[nodiscard]] constexpr std::uint8_t workplace_options(const BuildingDef& d) {
    return d.work == WorkKind::Gather && (d.gathers & 1u) != 0
               ? static_cast<std::uint8_t>(option::kFellFruit | option::kReplant | option::kMatureOnly)
               : std::uint8_t{0};
}

// A farm's field (phase 11): a rectangle of cells, a plan of three years
// (a crop or fallow each), and this year's progress.
enum class FieldState : std::uint8_t { Waiting, Growing, Ripe, Done, Count };
inline constexpr std::int32_t kMinFieldSide = 4;
inline constexpr std::int32_t kMaxFieldSide = 20;
// Phase 107: a fold's pasture may be larger.
inline constexpr std::int32_t kMaxPastureSide = 32;
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

// Phase 104: the bits of Building::garden.
namespace garden {
inline constexpr std::uint8_t kHouse = 1;
inline constexpr std::uint8_t kFormal = 2;
}  // namespace garden

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
    std::uint16_t annexes = 0;       // Houses: the annexes that serve it (a bit per BuildingDef::annex_bit); phase 103.
    std::uint8_t garden = 0;         // Phase 104: garden::kHouse (a house with its fence), garden::kFormal (a decoration with its hedge).
    std::uint8_t cat = 0;            // Phase 106: a house's cat: 0 none, else its look (1 to village::kCatLooks).
    // Phase 107: a fold's herd: which of its def's herds, how many females, whether it has its male, and
    // the years whose spring (wool, young) and autumn (the surplus) are done.
    std::uint8_t herd = 0;
    std::uint8_t females = 0;
    std::uint8_t males = 0;
    std::uint32_t herd_spring = 0;
    std::uint32_t herd_autumn = 0;
    std::uint8_t flock = 0;          // Phase 105: a coop's hens. (Its `produced` is the days of feed left; its `work_done`, eggs on the way.)
    std::int32_t happiness = 50;     // Houses: 0..100.
    std::int32_t desirability = 0;   // Houses: how pleasant the place is.
    // Phase 13.
    std::int32_t fire = 0;           // 0 = not burning; else 1..100.
    std::int32_t burned = 0;         // Damage from fire, 0..1000 (then it is gone).
    // Phase 15.
    std::int32_t damage = 0;         // From raiders; at its def's hp it breaks.
    std::int32_t rearm = 0;          // Traps: ticks until armed again.
    // Phase 16: barracks.
    std::vector<DefIndex> training;  // Units waiting, first in training.
    std::int32_t train_progress = 0;
    // Phase 63: stopped by the player. Its workers go back to laboring and
    // `wanted_workers` is kept for when it works again.
    bool stopped = false;
    // Phase 81: set when one of its workers looks for something to take.
    Supply supply = Supply::Fine;
    std::uint8_t options = 0;        // Phase 85: sim::option bits.
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
    // Phase 66: an explorer under orders.
    GoProvision,   // Walking to a storage for provisions.
    Scout,         // Walking where it was sent, or back home.
    ScoutWait,     // Waiting where it was sent.
    // Phase 71: out of energy.
    GoRest,        // Walking home (or to a campfire or the town center) to rest.
    Rest,          // Staying there until the energy is back.
    Count
};

enum class Sex : std::uint8_t { Male, Female };

struct Villager {
    std::uint8_t owner = 0;
    Sex sex = Sex::Male;
    std::uint8_t race = 0;            // RaceDef index (phase 19).
    std::int32_t work_carry = 0;      // Work beyond whole steps, in hundredths (race speeds).
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
    std::string name;                 // Phase 63: given by the player; empty: the one it came with.
    // Phase 66: an explorer's order, where to, and the food it carries (meter points).
    Order order = Order::None;
    FixedVec2 order_point;
    std::int32_t provisions = 0;
    // Phase 71: 0..kEnergyMax; at 0 it goes to rest (if the rules say so).
    std::int32_t energy = village::kEnergyMax;
    // Ticks spent walking since it last ate or stood at a storage with
    // food: what the way back to the food may cost, however winding or
    // slow it was (see eat_now).
    std::int32_t walked = 0;
    bool operator==(const Villager&) const = default;
};

// A good a merchant has: how many and at what prices (gold per unit).
struct MerchantGood {
    DefIndex resource = 0;
    std::int32_t stock = 0;  // Units to sell; buying from the town has no limit.
    std::int32_t buy = 0;    // What the town pays.
    std::int32_t sell = 0;   // What the town gets.
    bool operator==(const MerchantGood&) const = default;
};

// Automatic trade at the trading post (phase 29): while a merchant is
// here, once a day, sell what the town has over `sell_above` and buy up to
// `buy_below`, with the gold in the post.
struct TradeRule {
    DefIndex resource = 0;
    std::int32_t sell_above = kNoRule;
    std::int32_t buy_below = kNoRule;
    // Phase 60: sell only if the merchant's price of the day is at least
    // this percent of the good's value, buy only if it is at most this one
    // (a merchant's prices go from 75 to 125 %); 0: at any price.
    std::uint8_t sell_min = 0;
    std::uint8_t buy_max = 0;
    bool operator==(const TradeRule&) const = default;
};

// What automatic trade did during a merchant's visit.
struct TradeTally {
    std::int32_t sold = 0;        // Units.
    std::int32_t sold_gold = 0;   // Gold received.
    std::int32_t bought = 0;
    std::int32_t bought_gold = 0; // Gold paid.
    bool operator==(const TradeTally&) const = default;
};

enum class ArmyOrderKind : std::uint8_t { Defend, Attack, Retreat, Count };
enum class Outcome : std::uint8_t { Playing, Won, Lost, Count };

// Phase 113: what happens now and then, by the calendar and the seed.
enum class HappeningKind : std::uint8_t { Whales, Lanterns, Count };
inline constexpr std::size_t kHappeningKinds = static_cast<std::size_t>(HappeningKind::Count);
// One under way: where it is seen and until which day (days from the first
// of year 1; that day it is over).
struct Happening {
    HappeningKind kind = HappeningKind::Whales;
    std::uint8_t town = 0;
    FixedVec2 at;
    std::uint32_t until_day = 0;
    bool operator==(const Happening&) const = default;
};
inline constexpr std::size_t kMaxHappenings = 64;

struct PlayerState {
    bool active = false;
    // Phase 75: who sits here (the player's name and color, for the
    // interface and to give the seat back to whoever returns with the name).
    std::string name;
    std::uint8_t color = 0;
    // Phase 76: the seat came after the game began (by AddSeat). What it
    // may do without a town depends on the game's access.
    bool late = false;
    // Phase 77: the town this seat, which has none, has asked to join
    // (kNoRequest: none). It waits until the town's founder answers, or
    // the seat withdraws it or founds a town of its own.
    std::uint8_t request = 0xFF;
    // Phase 73: the seat's town exists (it was founded). Until then the
    // seat owns nothing and may only found. `cart`: the wagon the settlers
    // came with, which keeps their goods until the town center is built.
    bool founded = false;
    EntityId cart;
    EntityId town_center;
    std::uint32_t next_family = 1;
    std::int32_t births = 0;
    std::int32_t deaths = 0;
    std::int32_t arrivals = 0;
    std::int32_t departures = 0;      // Unhappy villagers who left.
    std::int32_t burned_down = 0;     // Buildings lost to fire.
    // Phase 14: the merchant from the surroundings. The town's gold is a
    // resource kept in its buildings (phase 28).
    std::uint64_t merchant_arrives = 0;  // Tick; 0 = not yet planned.
    std::uint64_t merchant_leaves = 0;   // Tick; past it, no merchant.
    // Phase 112: the unicorns the town has seen: bit k, the k-th glade of the map (the first 64).
    std::uint64_t unicorns_seen = 0;
    // Phase 113: the mood each kind of happening left: until which day (0: none).
    std::array<std::uint32_t, kHappeningKinds> mood_until{};
    std::vector<MerchantGood> merchant;  // What this merchant sells and buys.
    // Phase 29: automatic trade, by resource index, and this visit's tally.
    std::vector<TradeRule> trade_rules;
    TradeTally tally;
    // Phase 15.
    bool alarm = false;                  // The bell: adults fight, children hide.
    std::uint64_t next_raid = 0;         // Tick; 0 = not yet planned.
    std::int32_t raids = 0;
    // Phase 16: the army's standing order and the outcome of the game.
    ArmyOrderKind order = ArmyOrderKind::Defend;
    FixedVec2 rally;                     // Defend: where (zero: the town center).
    std::uint8_t enemy = 0;              // Attack: whom.
    Outcome outcome = Outcome::Playing;
    bool operator==(const PlayerState&) const = default;
};

// Animals and raiders (phase 15). Animals live in a zone of the map;
// raiders come from the edge to rob or burn a town, then go back.
enum class CreatureKind : std::uint8_t { Deer, Boar, Wolf, Bear, Raider, Soldier, Count };
enum class CreatureState : std::uint8_t { Wander, Flee, Chase, Approach, Bash, Leave, Travel, Count };
// What a creature's `target` is.
enum class TargetKind : std::uint8_t { Villager, Creature, Building, Count };

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
    // Phase 16.
    TargetKind target_kind = TargetKind::Villager;
    DefIndex unit = 0;            // Soldiers: their UnitDef.
    // Phase 96: ticks a beast has waited at the edge of a light it will not enter.
    std::uint16_t held = 0;
    // Phase 106: ticks a wolf is kept at bay by a guard dog: it neither moves nor bites.
    std::uint16_t bay = 0;
    bool operator==(const Creature&) const = default;
};

// Trade between players (phase 14): the offer holds the sender's goods
// until it is answered.
struct TradeOffer {
    std::uint32_t id = 0;
    std::uint8_t from = 0;
    std::uint8_t to = 0;
    DefIndex give = 0;  // A resource (gold too).
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
    DefIndex resource = 0;
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
    Unexplored,  // Under the fog of war (phase 32).
    Unreachable, // Phase 65: no villager of the town can walk there.
    DoorBelow,   // Phase 65: the ground rises too high behind the door; turned, it may fit.
};
// Phase 65: the ground under a building may differ this much in height, and
// rise this much over its floor (the walls are buried that far, no more).
inline constexpr std::int32_t kMaxSlopeCm = 400;
inline constexpr std::int32_t kMaxWallSlopeCm = 180;  // What follows the ground (walls...).
inline constexpr std::int32_t kMaxRoadSlopeCm = 100;  // A stretch of road (phase 95).
inline constexpr std::int32_t kMaxDryDays = 30;       // As far back as days_without_rain() looks (phase 97).
inline constexpr std::int32_t kMaxBuriedCm = 200;

inline constexpr std::uint8_t kNoRequest = 0xFF;

// A seat's player, as the lobby knows it.
struct SeatInfo {
    std::string name;
    std::uint8_t color = 0;
};

// How a game is set up besides its map.
struct GameSetup {
    std::uint8_t players = 1;
    std::uint64_t seed = 0;
    bool shared_town = false;  // All the players run one town (section 7.7).
    GameRules rules;
    // Phase 73. True: every town stands from the first tick at the map's
    // suggested sites, its center built and stocked (the tests of earlier
    // phases and the reference town). False, as the game does it: nobody
    // has a town until they found it, and time waits for all of them.
    bool start_towns = true;
    // Phase 75: the names and colors of the seats, in order (may be shorter
    // than `players`: the rest have no name).
    std::vector<SeatInfo> seats;
    // Phase 76: what newcomers may do (sim::access bits); 0: closed.
    std::uint8_t access = 0;
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
    // Phase 73. A new game waits, without a tick going by, until every
    // seat with a town of its own has founded it. Steps taken meanwhile
    // only run commands; `turn()` counts them too (what multiplayer numbers
    // its turns by).
    [[nodiscard]] bool awaiting_founders() const { return !started_; }
    [[nodiscard]] std::uint64_t turn() const { return tick_ + waited_; }
    [[nodiscard]] std::uint64_t waited() const { return waited_; }
    // Whether `player` still has to found the town it runs, and whether it
    // is the one who founds it (in a common town, its first seat).
    [[nodiscard]] bool founded(std::uint8_t player) const {
        return player < kMaxPlayers && players_[town_of(player)].founded;
    }
    [[nodiscard]] bool founder(std::uint8_t player) const { return player < player_count_ && town_of(player) == player; }
    // The definitions a town starts from: its center, and the settlers'
    // wagon (kNoDef: the mods have none, and the center is built at once).
    [[nodiscard]] DefIndex town_center_def() const { return town_center_def_; }
    [[nodiscard]] DefIndex cart_def() const { return cart_def_; }
    // Phase 74. The map's start positions are only suggestions; one with a
    // town center this close is not offered any more.
    static constexpr std::int32_t kSiteTakenMeters = 60;
    [[nodiscard]] bool site_taken(std::size_t site) const;
    // Whether `player` may found its town with the center's corner at
    // (x, z): the usual rules of the ground, anywhere on the map, explored
    // or not, plus room for the wagon nearby.
    [[nodiscard]] PlaceError can_found(std::uint8_t player, std::int32_t x, std::int32_t z, std::uint8_t rotation) const;
    [[nodiscard]] std::uint64_t hash() const;
    [[nodiscard]] std::uint32_t rejected_commands() const { return rejected_; }
    // Tasks left to go and eat (phase 66), for the tests: it must stay rare.
    [[nodiscard]] std::uint32_t interrupted_tasks() const { return interrupted_; }

    [[nodiscard]] const Content& content() const { return *content_; }
    [[nodiscard]] const std::shared_ptr<const Content>& content_ptr() const { return content_; }
    [[nodiscard]] const MapData& map() const { return map_; }
    [[nodiscard]] const std::vector<Node>& nodes() const { return nodes_; }
    [[nodiscard]] const EntityRegistry& registry() const { return registry_; }
    [[nodiscard]] const ComponentStore<Villager>& villagers() const { return villagers_; }
    [[nodiscard]] const ComponentStore<Building>& buildings() const { return buildings_; }
    [[nodiscard]] const PlayerState& player(std::uint8_t p) const { return players_[p]; }
    [[nodiscard]] const NavGrid& nav() const { return nav_; }
    // Phase 95: roads, a layer of the ground. The cells of the walking grid
    // (2 m) that have one, by index (z * road_side() + x), and its kind: 1
    // and up, in the order of the content's road buildings.
    [[nodiscard]] const std::map<std::uint32_t, std::uint8_t>& roads() const { return roads_; }
    [[nodiscard]] std::int32_t road_side() const { return nav_.side(); }
    // The kind of road at a point, in meters (0: none), and the building it was laid as.
    [[nodiscard]] std::uint8_t road_at(std::int32_t x, std::int32_t z) const {
        return x < 0 || z < 0 ? std::uint8_t{0} : nav_.road(x / kRoadModule, z / kRoadModule);
    }
    [[nodiscard]] DefIndex road_def(std::uint8_t kind) const {
        return kind == 0 || kind > road_defs_.size() ? kNoDef : road_defs_[kind - 1];
    }
    [[nodiscard]] std::uint8_t road_kind(DefIndex def) const;
    // Changes whenever a road is laid or taken away (for the views).
    [[nodiscard]] std::uint32_t roads_version() const { return roads_version_; }
    // Phase 97: rain. The day of the calendar it is, counted from the start
    // of the game; whether rain or snow falls on a day (`wet`), and which.
    [[nodiscard]] std::uint64_t seed() const { return seed_; }
    [[nodiscard]] std::uint64_t calendar_day() const { return tick_ / calendar_day_ticks(); }
    [[nodiscard]] bool wet(std::uint64_t day) const;
    [[nodiscard]] bool rained(std::uint64_t day) const;  // It fell as rain: it was not freezing.
    [[nodiscard]] bool raining() const { return rained(calendar_day()); }
    [[nodiscard]] bool snowing() const { return wet(calendar_day()) && !raining(); }
    // Days since it last rained: 0 while it rains, at most kMaxDryDays.
    [[nodiscard]] std::int32_t days_without_rain() const;
    // Dirt roads are mud: it rains, or it did yesterday.
    [[nodiscard]] bool muddy() const { return muddy_; }
    // Phase 98: whether a feature of the map gives by seasons (a hive, a
    // nest, a stump, a ring of mushrooms): fruit_on() says what it has.
    [[nodiscard]] bool seasonal(const MapFeature& f) const;
    // Phase 99: the berry bushes of the biome a feature stands in (a
    // BushKind), and whether it is one that never bears fruit: a bramble.
    [[nodiscard]] BushKind bush_kind(const MapFeature& f) const;
    [[nodiscard]] bool barren(const MapFeature& f) const {
        return f.type == FeatureType::BerryBush && bush_kind(f) == BushKind::Thorn;
    }
    // The day the rings of mushrooms last filled, plus one; 0 if they have
    // not this autumn (or it is not autumn).
    [[nodiscard]] std::uint32_t ring_cycle() const { return ring_cycle_; }
    // Whether a town has somebody who tells the bad mushrooms from the good: a healer or a doctor.
    [[nodiscard]] bool has_healer(std::uint8_t town) const;
    [[nodiscard]] std::uint8_t player_count() const { return player_count_; }
    // Whether the developer tools' commands are accepted (single player,
    // or a multiplayer game that allows them). Part of the state.
    [[nodiscard]] bool dev_commands() const { return dev_commands_; }
    // The town a player runs (phase 75): each seat belongs to a town, its
    // own or another seat's. A town is known by the seat that founds it;
    // a seat that has not joined anybody's is its own town, founded or not.
    [[nodiscard]] std::uint8_t town_of(std::uint8_t player) const {
        return player < kMaxPlayers ? seat_town_[player] : player;
    }
    // Whether some town has more than one seat.
    [[nodiscard]] bool shared_town() const;
    // The seat whose machine hosts the game: the only one that adds seats.
    [[nodiscard]] std::uint8_t host() const { return host_seat_; }
    void set_host(std::uint8_t seat) { host_seat_ = seat < kMaxPlayers ? seat : 0; }
    // Whether `town` is a town that exists: a seat's own, already founded.
    [[nodiscard]] bool town_exists(std::uint8_t town) const {
        return town < player_count_ && players_[town].active && town_of(town) == town && players_[town].founded;
    }
    // Phase 76: whether new players get a seat, and what they may do with
    // it (sim::access bits). Changed by the host's SetAccess order.
    [[nodiscard]] std::uint8_t access() const { return access_; }
    [[nodiscard]] bool open() const { return (access_ & access::kOpen) != 0; }
    // Whether a seat without a town may found one: those who began the
    // game always; those who came later, if the game lets them.
    [[nodiscard]] bool may_found(std::uint8_t player) const {
        return player < player_count_ && (!players_[player].late || (access_ & access::kFound) != 0);
    }
    // Phase 77. Whether `player`, without a town, may ask to join `town`.
    [[nodiscard]] bool may_request(std::uint8_t player, std::uint8_t town) const;
    // How many seats run a town.
    [[nodiscard]] std::int32_t seats_of(std::uint8_t town) const;

    // Time and weather (phase 10).
    [[nodiscard]] const GameRules& rules() const { return rules_; }
    // The calendar's year, month and day: they stretch with the year's
    // length. Seasons, crops and ages go by them.
    [[nodiscard]] std::uint32_t year_ticks() const { return sim::year_ticks(rules_.climate); }
    [[nodiscard]] std::uint32_t calendar_month_ticks() const { return year_ticks() / 12; }
    [[nodiscard]] std::uint32_t calendar_day_ticks() const { return calendar_month_ticks() / 10; }
    // Phase 59: everything else keeps its pace in real time whatever the
    // year's length, so the village's month and day are always those of
    // the usual year (100 s and 10 s at x1).
    [[nodiscard]] std::uint32_t month_ticks() const { return kTicksPerMonth; }
    // What something measured per year of the usual length (a harvest, a
    // yearly limit) is in this game's year; at least 1 for anything over 0.
    [[nodiscard]] std::int32_t per_year(std::int32_t amount) const {
        const std::int64_t scaled = static_cast<std::int64_t>(amount) * year_ticks() / kTicksPerYear;
        return amount > 0 ? static_cast<std::int32_t>(std::max<std::int64_t>(1, scaled)) : 0;
    }
    [[nodiscard]] std::uint32_t day_ticks() const { return kTicksPerDay; }
    [[nodiscard]] Calendar calendar() const { return sim::calendar(rules_.climate, tick_); }
    // Phase 84: the fruit hanging from tree `node` today. A fruit tree
    // bears its year's fruit at the start of summer; what nobody picked is
    // lost when autumn ends.
    [[nodiscard]] std::int32_t fruit_on(std::uint32_t node) const { return fruit_on(node, calendar()); }
    [[nodiscard]] std::int32_t fruit_on(std::uint32_t node, const Calendar& when) const;
    // Phase 88: the trees still standing on the ground of a construction
    // site; it is not built while there is one.
    [[nodiscard]] std::int32_t trees_on_site(const Building& site) const;
    // The first tree standing on a rectangle of ground (index + 1, 0 if
    // none), one nobody is felling if there is one; `count`, how many stand.
    [[nodiscard]] std::uint32_t tree_on(std::int32_t x, std::int32_t z, std::int32_t w, std::int32_t d, std::int32_t margin,
                                        std::int32_t* count = nullptr) const;
    // Phase 86: today as days since the first of year 1 (120 a year).
    [[nodiscard]] std::uint32_t day_number() const {
        const Calendar c = calendar();
        return (c.year - 1) * kDaysPerYear + (c.month - 1) * 10 + (c.day - 1);
    }
    // The size a tree of this species grows into from `size`, if any.
    [[nodiscard]] std::optional<TreeSize> next_size(const MapFeature& tree) const;
    // Phase 87: a grown tree is large or huge, or as large as its species gets.
    [[nodiscard]] bool mature(const MapFeature& tree) const {
        return tree.size >= static_cast<std::uint8_t>(TreeSize::Large) || !next_size(tree);
    }
    // Whether a tree is a sprout: planted, not yet a tree to fell.
    [[nodiscard]] bool sprout(std::uint32_t node) const {
        return node < nodes_.size() && map_.features[node].type == FeatureType::Tree && nodes_[node].amount <= 0 &&
               nodes_[node].regrow_tick != 0;
    }
    [[nodiscard]] DayTime day_time() const { return sim::day_time(rules_.day_night, tick_); }
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
    // Phase 63. What a villager is called: the name the player gave it, or
    // the one it came with (from its people's list, by the random bits it
    // was born with: the same on every machine and after loading); "" for
    // a people without names.
    [[nodiscard]] std::string villager_name(const Villager& v) const;
    // What a hunter brings from one animal: meat, and hides left at the lodge.
    [[nodiscard]] std::int32_t hunt_meat() const;
    [[nodiscard]] std::int32_t hunt_hides() const;
    [[nodiscard]] bool adult(const Villager& v) const;
    // Rotated footprint of a building definition.
    static void footprint(const BuildingDef& def, std::uint8_t rotation, std::int32_t& w, std::int32_t& d);
    // Whether `player` may place `def` with its corner at (x, z).
    [[nodiscard]] PlaceError can_place(std::uint8_t player, DefIndex def, std::int32_t x, std::int32_t z,
                                       std::uint8_t rotation) const;
    // Phase 93: the buildings a gate of a line family would take the place
    // of there: the plain modules of its town and family that lie wholly
    // under it (a gate set into a wall). Empty for anything else.
    [[nodiscard]] std::vector<EntityId> replaced_by(std::uint8_t town, const BuildingDef& d, std::int32_t x, std::int32_t z,
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
            UnitTrained,     // `value`: the unit.
            TownLost,        // `owner` is out of the game.
            GameOver,        // `value`: the winner + 1, or 0.
            Born,            // Phase 17: for the notifications.
            Died,
            AutoTrade,       // Phase 29: the merchant left; `tally` is what automatic trade did.
            ExplorerBack,    // Phase 66: an explorer turns back; `value`: 0 low on food, 1 cold.
            TownFounded,     // Phase 73: `owner` founded its town at `at`.
            SeatAdded,       // Phase 75: seat `owner` came into the game, without a town.
            TownJoined,      // Phase 75: seat `owner` joined town `other`.
            AccessChanged,   // Phase 76: `value`: the new access bits.
            JoinRequested,   // Phase 77: seat `owner` asks to join town `other`.
            JoinRefused,     // Phase 77: town `other`'s founder refused seat `owner`.
            JoinCancelled,   // Phase 77: seat `owner` withdrew its request to town `other`.
            GameStarted,     // Phase 73: every town is founded; time runs.
            Exhausted,       // Phase 81: workplace `entity` has nothing left to take within its reach
                             // (`value` 1: nothing but the fruit trees it spares, phase 85).
            Fox,             // Phase 105: a fox took a hen from coop `entity`; `value`: the hens left.
            Barked,          // Phase 106: the dog of kennel `entity` barks; `value`: the CreatureKind it saw.
            Lynx,            // Phase 109: a lynx took a hen from coop `entity` (`value`: those left), or (`other` 1) a
                             // young one from fold `entity`.
            Rabbits,         // Phase 109: rabbits ate part of the harvest of a field of farm `entity`.
            Mammoths,        // Phase 111: winter: a herd of `value` mammoths came to its zone, at `at`.
            Wounded,         // Phase 111: villager `entity` came back wounded from a mammoth hunt.
            UnicornSeen,     // Phase 112: the town saw, for the first time, the unicorn of the glade at `at`.
            UnicornLeft,     // Phase 112: a tree was felled by the glade at `at` (`other`: the town that felled
                             // it): its unicorn is gone for good.
            Whales,          // Phase 113: the whales pass off the coast of the town, at `at`.
            Lanterns,        // Phase 113: the town lets its lanterns go, at `at` (the door of its center).
        };
        Kind kind = Kind::FireStarted;
        std::uint8_t owner = 0;
        EntityId entity;
        FixedVec2 at;
        std::uint16_t value = 0;  // Disease index, for outbreaks.
        std::uint8_t other = 0;   // The other player, for trade.
        TradeTally tally;
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
    // Gold (phase 28): the resource, kNoDef if the mods have none; a town's
    // gold in its buildings, and the part of it in its trading post and vaults.
    [[nodiscard]] DefIndex gold() const { return gold_; }
    [[nodiscard]] std::int32_t gold(std::uint8_t player) const;
    struct GoldPlaces {
        std::int32_t post = 0;
        std::int32_t vaults = 0;
        std::int32_t others = 0;
    };
    [[nodiscard]] GoldPlaces gold_places(std::uint8_t player) const;
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
    // How pleasant a place is for homes: buildings around (gardens add,
    // workshops take away) and trees (phase 12; the map layer, phase 17).
    [[nodiscard]] std::int32_t desirability_at(FixedVec2 here, const Building* self = nullptr) const;
    // Phase 110. What a fisher's hut has within its reach.
    struct FishSpots {
        std::int32_t shoals = 0;   // With fish in them.
        std::int32_t spent = 0;    // Fished out until the season changes.
        std::int32_t reeds = 0;
        std::int32_t ducks = 0;
        std::uint32_t fullest = 0; // The shoal with most fish left: its index + 1, or 0.
    };
    [[nodiscard]] FishSpots fish_spots(std::int32_t x, std::int32_t z, std::int32_t radius) const;
    [[nodiscard]] FishSpots fish_spots(const Building& hut) const;
    // The pace it fishes at, in percent of the pace of before.
    [[nodiscard]] static std::int32_t fish_percent(const FishSpots& spots);
    // Phase 113. What is happening now; the mood of a town (points of happiness for its houses); the day
    // of the year (0..119) a happening falls on in `year` (from 0) for `town`: the whales pass the same day
    // for everybody; and whether a cell is of the sea.
    [[nodiscard]] const std::vector<Happening>& happenings() const { return happenings_; }
    [[nodiscard]] std::int32_t town_mood(std::uint8_t town) const;
    [[nodiscard]] std::uint32_t happening_day(HappeningKind kind, std::uint32_t year, std::uint8_t town) const;
    [[nodiscard]] bool sea_at(std::int32_t x, std::int32_t z) const;
    // Phase 112. Whether a unicorn grazes in a glade whose middle is within `radius` meters of (x, z).
    [[nodiscard]] bool unicorn_near(std::int32_t x, std::int32_t z, std::int32_t radius) const;
    // Whether felling trees from a building of `def` at (x, z) (its corner) could frighten one away: it
    // fells trees, and the ground around a glade with its unicorn is within its reach.
    [[nodiscard]] bool fells_by_unicorn(DefIndex def, std::int32_t x, std::int32_t z) const;
    // Phase 111. The big game within the reach of a lodge: how many zones of mammoths, and how many
    // mammoths are in them now (none but in winter).
    struct BigGame {
        std::int32_t zones = 0;
        std::int32_t animals = 0;
    };
    [[nodiscard]] BigGame big_game(const Building& lodge) const;
    // Whether the middle of a zone of mammoths, where the herd stands, is within the reach of a lodge.
    [[nodiscard]] bool reaches_herd(const Building& lodge, const Zone& zone) const;
    // Phase 109. How many animals zone `z` holds at most (rabbits: half with a lynx near; mammoths: in winter).
    [[nodiscard]] std::int32_t zone_room(std::size_t z) const;
    // Whether a lynx lives within village::kLynxMeters of the edge of the circle at (x, z) of `radius` meters.
    [[nodiscard]] bool lynx_near(std::int32_t x, std::int32_t z, std::int32_t radius = 0) const;
    // Whether a guard (a kennel) has the rectangle within its reach.
    [[nodiscard]] bool guarded(std::int32_t x, std::int32_t z, std::int32_t w, std::int32_t d) const;
    // Whether the rabbits eat of a field (x, z, w, d) of `town` sown with `crop`: it is in a zone with many
    // of them and nothing keeps them out.
    [[nodiscard]] bool rabbits_eat(std::uint8_t town, DefIndex crop, std::int32_t x, std::int32_t z, std::int32_t w,
                                   std::int32_t d) const;
    // Phase 107. A fold's herd (null: not a fold), and how many animals its pasture has room for.
    [[nodiscard]] const HerdDef* herd_of(const Building& fold) const;
    [[nodiscard]] std::int32_t herd_room(const Building& fold) const;
    // Phase 105. Whether no fox comes to `coop`: it has its fence, or a guard in reach.
    [[nodiscard]] bool coop_safe(const Building& coop) const;
    // Phase 104. How thick the wild flowers are over the cells from (x0, z0)
    // to (x1, z1), one in `step` each way: the sum of sim::wildflowers
    // where nothing covers them (a building, a road, a field, water). With
    // `radius`, only those within that many meters of the middle.
    [[nodiscard]] std::int32_t flowers(std::int32_t x0, std::int32_t z0, std::int32_t x1, std::int32_t z1, std::int32_t step = 1,
                                       std::int32_t radius = 0) const;
    // What the flowers around `house` add to its environment today.
    [[nodiscard]] std::int32_t flower_beauty(const Building& house) const;
    // What a hive finds in a day (0 in winter).
    [[nodiscard]] std::int32_t nectar(const Building& hive) const;
    // Phase 103. The annexes that serve `house` now (bits of annex_bit):
    // those of its town, built, with their walls within their reach of the
    // house's. What a house has is in Building::annexes, set once a day.
    [[nodiscard]] std::uint16_t annexes_of(const Building& house) const;
    // The firewood a house keeps: more with a woodshed.
    [[nodiscard]] std::int32_t firewood_room(const Building& house) const;
    // Whether the rain barrels are full: it rained within village::kBarrelDryDays.
    [[nodiscard]] bool barrels_full() const;
    // Whether a fire that starts in `b` goes out by itself (a house with a full barrel).
    [[nodiscard]] bool has_full_barrel(const Building& b) const;

    // Fog of war (phase 32): what each vision group has explored. A
    // group is a town, or all the allies when they share what they see.
    [[nodiscard]] bool fog() const { return rules_.fog != FogMode::None; }
    [[nodiscard]] const Vision& vision() const { return vision_; }
    [[nodiscard]] std::uint8_t town_group(std::uint8_t town) const;
    [[nodiscard]] std::uint8_t vision_group(std::uint8_t player) const { return town_group(town_of(player)); }
    // Meters a building, a villager or a soldier sees (0: it gives no sight).
    [[nodiscard]] std::int32_t sight(const Building& b) const;
    // Phase 69: how many meters around its middle a building lights at
    // night; 0 if it gives no light now.
    [[nodiscard]] std::int32_t light(const Building& b) const;
    // Phase 70. Whether it is night now (never, with no cycle); whether a
    // point is within the light of a building; and whether a villager is
    // slowed by the dark: at night, out of the light, without night vision.
    [[nodiscard]] bool night() const { return day_time().night; }
    [[nodiscard]] bool lit(std::int32_t x, std::int32_t z) const;
    // Phase 96: lit, at night, by a light that keeps wolves and bears out.
    [[nodiscard]] bool warded(std::int32_t x, std::int32_t z) const;
    [[nodiscard]] bool in_the_dark(const Villager& v) const;
    [[nodiscard]] std::int32_t sight(const Villager& v) const;
    [[nodiscard]] std::int32_t sight(const Creature& a) const;
    // Explores around every town's people and buildings; step() does it
    // once a second (public for the benchmarks). Nothing without fog.
    void update_vision();
    // Phase 70: the lit cells, from the buildings that give light now. Only
    // drawn again when those change (and after loading: it is not saved).
    void update_light();

    // Armies and the end of the game (phase 16).
    [[nodiscard]] std::int32_t soldiers(std::uint8_t player) const;
    [[nodiscard]] std::int32_t military_power(std::uint8_t player) const;
    [[nodiscard]] std::int32_t score(std::uint8_t player) const;
    [[nodiscard]] bool game_over() const { return game_over_; }
    // Whether two towns fight each other (versus with combat on).
    [[nodiscard]] bool enemies(std::uint8_t a, std::uint8_t b) const;

    // Animals left in each of the map's zones (hunting).
    [[nodiscard]] const std::vector<std::int32_t>& zone_animals() const { return zone_animals_; }
    // Point in front of a building's door, where villagers go.
    [[nodiscard]] FixedVec2 door(const Building& b) const;
    // Phase 65. The height of a building's floor, in centimeters: that of
    // the ground at the middle of its door's side (w, d: the rotated
    // footprint).
    [[nodiscard]] std::int32_t floor_cm(std::int32_t x, std::int32_t z, std::int32_t w, std::int32_t d,
                                        std::uint8_t rotation) const;
    // Whether a villager of `town` can walk to a place of that size: one
    // of its four sides is joined by land to the town center's door. True
    // for a town without a center yet.
    [[nodiscard]] bool site_reachable(std::uint8_t town, std::int32_t x, std::int32_t z, std::int32_t w,
                                      std::int32_t d) const;
    // Where someone coming from `from` stands to use a building.
    [[nodiscard]] FixedVec2 approach(const Building& b, FixedVec2 from) const;

    // Map features felled or emptied since the last call (for the view).
    [[nodiscard]] std::vector<std::uint32_t> take_changed_nodes();
    // Buildings added, changed or removed since the last call.
    [[nodiscard]] bool take_buildings_changed();
    // Natural features were added to the map (developer tools) since the last call.
    [[nodiscard]] bool take_features_added() {
        const bool added = features_added_;
        features_added_ = false;
        return added;
    }

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
    // Roads (phase 95): see roads(). The walking grid keeps its own copy, by cell.
    std::map<std::uint32_t, std::uint8_t> roads_;
    std::vector<DefIndex> road_defs_;
    std::uint32_t roads_version_ = 0;
    // Phase 97. Derived from the day, not saved: whether the dirt roads are
    // mud. update_weather() sets it when a day of the calendar begins (and
    // after loading), and tells the walking grid how fast each road is now.
    bool muddy_ = false;
    std::uint32_t ring_cycle_ = 0;  // Phase 98, derived too: see ring_cycle().
    std::vector<std::uint32_t> ring_nodes_;  // The features that fill after the rain, for the view.
    void update_weather();
    // What a seasonal feature's count of what was picked is kept for: the
    // year, or the filling of the rings.
    [[nodiscard]] std::uint32_t pick_cycle(const FeatureDef& fd, const Calendar& when) const {
        return fd.after_rain ? ring_cycle_ : when.year;
    }
    DefIndex food_disease_ = kNoDef;  // The disease that comes from bad food, if the content has one.
    void set_road(std::int32_t cx, std::int32_t cz, std::uint8_t kind);
    // Takes away the roads under a rectangle of the map, in meters.
    void clear_roads(std::int32_t x, std::int32_t z, std::int32_t w, std::int32_t d);
    // Whether there is a road, or a stretch `town` is building, at a module's cell.
    [[nodiscard]] bool road_to_erase(std::uint8_t town, std::int32_t x, std::int32_t z) const;

    std::uint64_t tick_ = 0;
    std::uint64_t seed_ = 0;
    Rng rng_;
    EntityRegistry registry_;
    ComponentStore<Villager> villagers_;
    ComponentStore<Building> buildings_;
    std::array<PlayerState, kMaxPlayers> players_{};
    std::uint8_t player_count_ = 0;
    std::uint32_t rejected_ = 0;
    std::uint32_t interrupted_ = 0;  // Not saved: a count for the tests.
    bool dev_commands_ = true;
    std::array<std::uint8_t, kMaxPlayers> seat_town_{0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11};
    std::uint8_t host_seat_ = 0;
    std::uint8_t access_ = 0;
    bool started_ = true;          // Phase 73: false while it waits for the founders.
    std::uint64_t waited_ = 0;     // Steps taken while waiting.
    DefIndex town_center_def_ = kNoDef;
    DefIndex cart_def_ = kNoDef;
    // The ground rules of can_place: inside the map (and the town's
    // region), free, dry and not too steep.
    [[nodiscard]] PlaceError ground_error(std::uint8_t town, const BuildingDef& d, std::int32_t x, std::int32_t z,
                                          std::uint8_t rotation) const;
    // Where the wagon of a town founded at (x, z) goes: the nearest free
    // 2 x 2 by the center's door. False if there is none.
    [[nodiscard]] bool cart_spot(std::uint8_t town, std::int32_t x, std::int32_t z, std::uint8_t rotation,
                                 std::int32_t& cart_x, std::int32_t& cart_z) const;
    // Every seat that founds has: time starts.
    void check_started();
    GameRules rules_;
    std::int32_t temperature_ = 12;  // Today's; follows from the tick.
    std::int32_t snow_ = 0;          // 0..kMaxSnow.
    // Derived, not saved: one byte per cell of kLightCell meters (bit 0:
    // lit; bit 1: by a light that keeps the beasts out), and what it was
    // drawn from (0: never).
    std::vector<std::uint8_t> light_cells_;
    std::int32_t light_side_ = 0;
    std::uint64_t light_signature_ = 0;
    DefIndex firewood_ = kNoDef;     // Resources the rules use, looked up once.
    DefIndex clothes_ = kNoDef;
    DefIndex fertilizer_ = kNoDef;
    DefIndex meat_ = kNoDef;
    DefIndex hide_ = kNoDef;
    DefIndex ivory_ = kNoDef;
    DefIndex fish_ = kNoDef;
    DefIndex fruit_ = kNoDef;
    DefIndex shoes_ = kNoDef;
    DefIndex gold_ = kNoDef;
    std::vector<std::int32_t> zone_animals_;
    std::int32_t fires_ = 0;          // Buildings burning (follows from them).
    std::vector<Happening> happenings_;  // Phase 113.
    std::vector<TradeOffer> offers_;
    ComponentStore<Creature> creatures_;
    // Phase 20: counts that were recomputed over and over. Derived state,
    // never saved: the population by player (until a villager comes or
    // goes) and the stored goods by player (until the next tick or command).
    mutable std::array<std::int32_t, kMaxPlayers> pop_cache_{};
    mutable bool pop_dirty_ = true;
    mutable std::array<std::vector<std::int32_t>, kMaxPlayers> stored_cache_;
    mutable std::uint32_t stored_valid_ = 0;  // Bit per player.
    void villagers_changed() { pop_dirty_ = true; }
    // Each town's buildings, in the store's order (rebuilt when buildings
    // come or go): the searches of one villager look only at its town's.
    mutable std::array<std::vector<EntityId>, kMaxPlayers> owned_;
    mutable bool owned_dirty_ = true;
    [[nodiscard]] const std::vector<EntityId>& owned(std::uint8_t town) const;
    void building_set_changed() { owned_dirty_ = true; }
    void goods_changed() { stored_valid_ = 0; }
    bool game_over_ = false;
    std::vector<Caravan> caravans_;
    std::uint32_t next_offer_ = 1;
    std::vector<Event> events_;

    Vision vision_;
    // The vision groups the players make up (fixed for a game).
    [[nodiscard]] std::uint16_t vision_groups() const;
    void update_ghosts();

    std::vector<std::pair<std::uint64_t, std::uint32_t>> regrow_;  // (tick, node), sorted.
    std::vector<std::uint32_t> changed_nodes_;
    // Walking costs around workplaces (derived, never saved), by entity index.
    std::map<std::uint32_t, std::pair<EntityId, NavGrid::Area>> work_areas_;
    bool buildings_changed_ = true;
    bool features_added_ = false;

    void build_indexes();
    // Phase 83: the ground a stone deposit stands on is taken (or free again).
    void block_deposit(const MapFeature& f, bool blocked);
    void block_deposits();
};

// Human-readable name of a task (English, for logs and the developer tools).
[[nodiscard]] const char* task_name(Task t);

}  // namespace sc::sim
