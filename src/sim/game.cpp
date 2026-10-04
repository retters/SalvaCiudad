#include "sim/game.h"

#include <algorithm>
#include <functional>
#include <bit>
#include <optional>

namespace sc::sim {

namespace {

constexpr std::uint32_t kSaveVersion = 1;
constexpr std::int32_t kNodeCell = 16;           // Meters per node lookup cell.
constexpr std::uint32_t kJobEvery = 20;          // Ticks between job assignments.
constexpr std::int32_t kWanderRadius = 18;
constexpr std::int32_t kStartGold = 100;         // In the town center, at 100 % starting goods (D-2803).
constexpr std::int32_t kPostReserve = 100;       // Gold a new trading post keeps (D-2804).
constexpr std::int32_t kGoldMovers = 2;          // Laborers moving gold at once, per town.

Fixed walk_speed(bool adult) {
    return Fixed::from_ratio(adult ? 20 : 16, 100);  // Meters per tick: 2 m/s for adults.
}

std::int32_t carry_capacity(const Content& c, DefIndex resource) {
    if (resource >= c.resources.size()) {
        return village::kCarry;
    }
    if (c.resources[resource].carry > 0) {
        return c.resources[resource].carry;  // Gold goes in bags (phase 28).
    }
    return std::max(1, village::kCarry / std::max(1, c.resources[resource].weight));
}

std::int32_t amount_of(const std::vector<Stock>& list, DefIndex r) {
    for (const Stock& s : list) {
        if (s.resource == r) {
            return s.amount;
        }
    }
    return 0;
}

void add_to(std::vector<Stock>& list, DefIndex r, std::int32_t n) {
    for (Stock& s : list) {
        if (s.resource == r) {
            s.amount += n;
            return;
        }
    }
    if (n != 0) {
        list.push_back({r, n});
    }
}

std::int32_t total(const std::vector<Stock>& list) {
    std::int32_t t = 0;
    for (const Stock& s : list) {
        t += s.amount;
    }
    return t;
}

// A building on the walking grid: most block it, gates only stop raiders
// and traps nothing.
void block_nav(NavGrid& nav, const BuildingDef& d, std::int32_t x, std::int32_t z, std::int32_t w, std::int32_t depth,
               bool on) {
    if (d.trap) {
        return;
    }
    if (d.gate) {
        nav.set_gate(x, z, x + w, z + depth, on);
        return;
    }
    nav.set_building(x, z, x + w, z + depth, on);
}

void compact(std::vector<Stock>& list) {
    std::erase_if(list, [](const Stock& s) { return s.amount <= 0; });
}

std::uint64_t distance2(FixedVec2 a, FixedVec2 b) {
    return (a - b).length_squared_raw();
}

// Whether `r` in `b` is there to be taken away: everything in a storage,
// and what a workplace made or gathered (not the inputs of its recipes).
bool gives_out(const Content& c, const Building& b, DefIndex r) {
    const BuildingDef& d = c.buildings[b.def];
    if (d.kind == BuildingKind::Storage || d.kind == BuildingKind::TownCenter || d.kind == BuildingKind::Market) {
        return true;
    }
    if (d.kind != BuildingKind::Workplace) {
        return false;
    }
    for (const DefIndex recipe : d.recipes) {
        for (const ResourceAmount& in : c.recipes[recipe].inputs) {
            if (in.resource == r) {
                return false;
            }
        }
    }
    // What a service uses stays there too (a tavern's beer).
    for (const ResourceAmount& use : d.service_uses) {
        if (use.resource == r) {
            return false;
        }
    }
    return true;
}

}  // namespace

const char* task_name(Task t) {
    static constexpr const char* kNames[] = {"idle",    "wander",       "going to eat", "going to gather",
                                             "gathering", "delivering", "fetching",     "carrying to a site",
                                             "going to build", "building", "going to work", "producing",
                                             "going to a field", "farming", "going hunting", "hunting",
                                             "going fishing", "fishing", "running to a fire", "fighting a fire",
                                             "going to fight", "fighting", "fleeing"};
    const auto i = static_cast<std::size_t>(t);
    return i < std::size(kNames) ? kNames[i] : "?";
}

// All the rules that change the game, with access to its state.
class VillageRules {
public:
    explicit VillageRules(Game& g) : g_(g), c_(*g.content_) {}

    // --- Lookups -----------------------------------------------------------

    [[nodiscard]] const BuildingDef& def(const Building& b) const { return c_.buildings[b.def]; }

    [[nodiscard]] bool complete(const Building& b) const { return b.state == BuildingState::Complete; }

    // Something laborers work on: a new building, or an upgrade.
    [[nodiscard]] bool is_site(const Building& b) const {
        return b.state == BuildingState::Construction ||
               (b.upgrading && b.level < def(b).levels.size());
    }
    [[nodiscard]] const std::vector<ResourceAmount>& site_cost(const Building& b) const {
        return b.state == BuildingState::Construction ? def(b).cost : def(b).levels[b.level].cost;
    }
    [[nodiscard]] std::int32_t site_work(const Building& b) const {
        return b.state == BuildingState::Construction ? def(b).build_work : def(b).levels[b.level].work;
    }

    [[nodiscard]] std::int32_t free_space(const Building& b) const {
        return complete(b) ? def(b).storage - total(b.stock) : 0;
    }

    [[nodiscard]] bool accepts(const Building& b, DefIndex resource) const {
        if (!complete(b) || resource >= c_.resources.size() || def(b).storage <= 0) {
            return false;
        }
        if (def(b).kind != BuildingKind::Storage && def(b).kind != BuildingKind::TownCenter) {
            return false;  // Workplaces keep their own goods only.
        }
        return ((def(b).stores >> static_cast<unsigned>(c_.resources[resource].category)) & 1u) != 0;
    }

    // Nearest complete storage of `owner` that can take `resource`.
    EntityId storage_for(std::uint8_t owner, FixedVec2 from, DefIndex resource) const {
        EntityId best;
        std::uint64_t best_d = UINT64_MAX;
        for (const EntityId id : g_.owned(owner)) {
            const Building& b = *g_.buildings_.get(id);
            if (!accepts(b, resource) || free_space(b) <= 0) {
                continue;
            }
            const std::uint64_t d = distance2(from, g_.door(b));
            if (d < best_d) {
                best_d = d;
                best = id;
            }
        }
        return best;
    }

    // Nearest storage of `owner` holding `resource` (any food if kNoDef);
    // markets restock from the others.
    EntityId storage_with(std::uint8_t owner, FixedVec2 from, DefIndex resource, bool skip_markets = false) const {
        EntityId best;
        std::uint64_t best_d = UINT64_MAX;
        for (const EntityId id : g_.owned(owner)) {
            const Building& b = *g_.buildings_.get(id);
            if (!complete(b) || def(b).storage <= 0 ||
                (skip_markets && def(b).kind == BuildingKind::Market)) {
                continue;
            }
            bool has = false;
            for (const Stock& s : b.stock) {
                if (s.amount <= 0 || !gives_out(c_, b, s.resource)) {
                    continue;
                }
                if (resource == kNoDef ? c_.resources[s.resource].category == ResourceCategory::Food
                                       : s.resource == resource) {
                    has = true;
                }
            }
            if (!has) {
                continue;
            }
            const std::uint64_t d = distance2(from, g_.door(b));
            if (d < best_d) {
                best_d = d;
                best = id;
            }
        }
        return best;
    }

    // --- Races (phase 19) ---------------------------------------------------------------

    [[nodiscard]] const RaceDef* race_of(const Villager& v) const {
        return v.race < c_.races.size() ? &c_.races[v.race] : nullptr;
    }

    // Whole work steps this tick: one at 100 %, with the rest carried over.
    std::int32_t steps(Villager& v, Skill skill) {
        const RaceDef* r = race_of(v);
        std::int32_t rate = r != nullptr ? r->work[static_cast<std::size_t>(skill)] : 100;
        // Working by feel in the dark of the night (phase 70).
        if (g_.in_the_dark(v)) {
            rate = rate * village::kDarkPercent / 100;
        }
        v.work_carry += rate;
        const std::int32_t n = v.work_carry / 100;
        v.work_carry -= n * 100;
        return n;
    }

    [[nodiscard]] Skill gather_skill(FeatureType t) const {
        switch (t) {
            case FeatureType::Tree: return Skill::Wood;
            case FeatureType::Stone:
            case FeatureType::IronOre: return Skill::Stone;
            default: return Skill::Forage;
        }
    }

    [[nodiscard]] Skill produce_skill(const Building& job, const RecipeDef& recipe) const {
        if (def(job).mature_years > 0) {
            return Skill::Orchard;
        }
        for (const ResourceAmount& in : recipe.inputs) {
            const std::string& id = c_.resources[in.resource].id;
            if (id == "core:iron_ore" || id == "core:iron" || id == "core:coal") {
                return Skill::Metal;
            }
            if (id == "core:stone" || id == "core:clay") {
                return Skill::Stone;
            }
        }
        if (recipe.inputs.empty()) {
            // Gathering in a workshop (clay pit, iron mine, herbs): stone for the pits.
            for (const ResourceAmount& out : recipe.outputs) {
                const std::string& id = c_.resources[out.resource].id;
                if (id == "core:clay" || id == "core:iron_ore" || id == "core:stone") {
                    return Skill::Stone;
                }
            }
            return Skill::Forage;
        }
        return Skill::Craft;
    }

    // The race of a newborn or a newcomer.
    [[nodiscard]] std::uint8_t newcomer_race(std::uint8_t town) {
        const std::size_t races = c_.races.size();
        if (races == 0) {
            return 0;
        }
        const std::uint8_t home = g_.rules_.races[town % g_.rules_.races.size()];
        const bool mixed = home == kMixedRace || home >= races;
        if (mixed || g_.rng_.below(100) < g_.rules_.other_races) {
            // Any race, or one of those allowed to come (phase 56).
            const auto pick = static_cast<std::uint8_t>(g_.rng_.below(static_cast<std::uint32_t>(races)));
            const std::uint16_t allowed = g_.rules_.immigrants;
            if (allowed == 0 || mixed) {
                return pick;
            }
            for (std::size_t k = 0; k < races; ++k) {
                const std::size_t r = (pick + k) % races;
                if (r < 16 && ((allowed >> r) & 1u) != 0) {
                    return static_cast<std::uint8_t>(r);
                }
            }
        }
        return home;
    }

    // --- Movement ------------------------------------------------------------

    bool walk_to(Villager& v, FixedVec2 to) {
        v.path_index = 0;
        if (!g_.nav_.find_path(v.position, to, v.path)) {
            v.path.clear();
            return false;
        }
        return true;
    }

    [[nodiscard]] static bool moving(const Villager& v) { return v.path_index < v.path.size(); }

    void move(Villager& v) {
        // Deep snow slows everybody down, to about half.
        Fixed budget = walk_speed(g_.adult(v)) * Fixed::from_ratio(200 - g_.snow_, 200);
        if (const RaceDef* r = race_of(v)) {
            budget = budget * Fixed::from_ratio(r->move, 100);
        }
        // And so does the dark of the night, out of the light (phase 70).
        if (g_.in_the_dark(v)) {
            budget = budget * Fixed::from_ratio(village::kDarkPercent, 100);
        }
        while (budget > Fixed{} && moving(v)) {
            const FixedVec2 target = v.path[v.path_index];
            const FixedVec2 d = target - v.position;
            const Fixed len = d.length();
            if (len <= budget) {
                v.position = target;
                budget -= len;
                ++v.path_index;
            } else {
                v.position = v.position + d * (budget / len);
                budget = Fixed{};
            }
        }
        if (!moving(v)) {
            v.path.clear();
            v.path_index = 0;
        }
    }

    // --- Tasks -------------------------------------------------------------

    void go(Villager& v, Task task, EntityId target) {
        v.task = task;
        v.target = target;
        const Building* b = g_.buildings_.get(target);
        if (b == nullptr || !walk_to(v, g_.approach(*b, v.position))) {
            fail(v);
        }
    }

    // Gives up the current task; tries again a little later.
    void fail(Villager& v) {
        release(v);
        v.task = Task::Idle;
        v.path.clear();
        v.path_index = 0;
        v.idle_ticks = 20 + static_cast<std::int32_t>(g_.rng_.below(30));
    }

    // Drops reservations: a node being worked, goods promised to a site.
    void release(Villager& v) {
        if (v.node != 0) {
            Node& n = g_.nodes_[v.node - 1];
            if (n.reserved == v_index_ + 1) {
                n.reserved = 0;
            }
            v.node = 0;
        }
        if (v.task == Task::GoFetch && v.carrying.amount == 0 && v.timer > 0) {
            // Goods promised to a site but not picked up.
            if (Building* s = g_.buildings_.get(v.site); s != nullptr && is_site(*s)) {
                add_to(s->incoming, v.carrying.resource, -v.timer);
                compact(s->incoming);
            }
            v.timer = 0;
        }
        if (v.task == Task::GoSite && v.carrying.amount > 0) {
            // Goods on their way that will not arrive; they go to storage.
            if (Building* s = g_.buildings_.get(v.target); s != nullptr && is_site(*s)) {
                add_to(s->incoming, v.carrying.resource, -v.carrying.amount);
                compact(s->incoming);
            }
        }
        if (v.carrying.amount <= 0) {
            v.carrying = {};
        }
        if (v.task == Task::GoFetch) {
            v.site = {};
        }
    }

    void wander(Villager& v, FixedVec2 around) {
        const std::int32_t dx = g_.rng_.range(-kWanderRadius, kWanderRadius);
        const std::int32_t dz = g_.rng_.range(-kWanderRadius, kWanderRadius);
        const FixedVec2 to{around.x + Fixed::from_int(dx), around.z + Fixed::from_int(dz)};
        v.task = Task::Wander;
        if (!walk_to(v, to)) {
            v.task = Task::Idle;
        } else {
            // A stroll, not a trek around a lake.
            Fixed length;
            FixedVec2 at = v.position;
            for (const FixedVec2& p : v.path) {
                length += (p - at).length();
                at = p;
            }
            if (length > Fixed::from_int(kWanderRadius * 3)) {
                v.path.clear();
                v.path_index = 0;
                v.task = Task::Idle;
            }
        }
        v.idle_ticks = 40 + static_cast<std::int32_t>(g_.rng_.below(80));
    }

    FixedVec2 home_point(const Villager& v) const {
        if (const Building* tc = g_.buildings_.get(g_.players_[v.owner].town_center)) {
            return g_.door(*tc);
        }
        return v.position;
    }

    // --- Phase 66: the explorer ------------------------------------------------------

    // Meter points a walk of `meters` in a straight line takes: five ticks
    // a meter, a point every four ticks, and paths a third longer.
    [[nodiscard]] static std::int32_t food_for_walk(std::int32_t meters) { return meters * 13 / 8; }

    [[nodiscard]] const Building* explorer_post(const Villager& v) const {
        const Building* job = g_.buildings_.get(v.job);
        return job != nullptr && complete(*job) && def(*job).work == WorkKind::Explore ? job : nullptr;
    }

    void stop(Villager& v) {
        v.path.clear();
        v.path_index = 0;
    }

    // The player's order: provisions first when it has few and the town has food.
    void order_scout(Villager& v, FixedVec2 to) {
        const Building* post = explorer_post(v);
        if (post == nullptr) {
            return;
        }
        release(v);
        stop(v);
        v.order_point = to;
        if (distance2(to, g_.door(*post)) <= meters2(village::kHomeMeters)) {
            return_home(v);  // Sent home.
            return;
        }
        if (v.provisions < village::kProvisions / 2) {
            const EntityId food = storage_with(v.owner, v.position, kNoDef);
            if (food.valid()) {
                v.order = Order::Provision;
                go(v, Task::GoProvision, food);
                if (v.task == Task::GoProvision) {
                    return;
                }
            }
        }
        start_scout(v);
    }

    // At the storage: food for the road, the most nutritious first.
    void take_provisions(Villager& v) {
        Building* b = g_.buildings_.get(v.target);
        while (b != nullptr && v.provisions < village::kProvisions) {
            Stock* best = nullptr;
            for (Stock& st : b->stock) {
                const ResourceDef& r = c_.resources[st.resource];
                if (st.amount > 0 && r.category == ResourceCategory::Food && r.nutrition > 0 && gives_out(c_, *b, st.resource) &&
                    (best == nullptr || r.nutrition > c_.resources[best->resource].nutrition)) {
                    best = &st;
                }
            }
            if (best == nullptr) {
                break;
            }
            --best->amount;
            v.provisions = std::min(village::kProvisions,
                                    v.provisions + c_.resources[best->resource].nutrition * village::kFoodPerNutrition);
        }
        if (b != nullptr) {
            compact(b->stock);
        }
        start_scout(v);
    }

    // On its way to the point. With fog and the point explored: the
    // shortest way over explored ground only. Else, or if there is none:
    // straight at it until something is in the way. Without fog: the way
    // anybody would take.
    void start_scout(Villager& v) {
        v.order = Order::Going;
        v.task = Task::Scout;
        v.target = {};
        stop(v);
        const FixedVec2 to = v.order_point;
        bool found = false;
        if (!g_.vision_.active()) {
            found = walk_to(v, to);
        } else {
            const std::uint8_t group = g_.town_group(v.owner);
            const std::function<bool(std::int32_t, std::int32_t)> known = [&](std::int32_t cx, std::int32_t cz) {
                return g_.vision_.explored_at(group, cx * NavGrid::kCell + 1, cz * NavGrid::kCell + 1);
            };
            if (g_.vision_.explored_at(group, to.x.floor_int(), to.z.floor_int())) {
                found = g_.nav_.find_path_within(v.position, to, v.path, known) && !v.path.empty();
            }
            if (!found) {
                stop(v);
                const FixedVec2 d = to - v.position;
                const Fixed length = d.length();
                const std::int32_t steps = length.floor_int();
                FixedVec2 last = v.position;
                std::int32_t done = 0;
                for (std::int32_t i = 1; i <= steps; ++i) {
                    const FixedVec2 p = v.position + d * (Fixed::from_int(i) / length);
                    if (!g_.nav_.walkable(g_.nav_.cell_of(p.x), g_.nav_.cell_of(p.z))) {
                        break;
                    }
                    last = p;
                    done = i;
                }
                if (done == steps && g_.nav_.walkable(g_.nav_.cell_of(to.x), g_.nav_.cell_of(to.z))) {
                    last = to;
                    ++done;
                }
                if (done > 0) {
                    v.path.push_back(last);
                    found = true;
                }
            }
        }
        if (!found) {
            stop(v);
            v.order = Order::Waiting;  // No way from here: it waits for another order.
            v.task = Task::ScoutWait;
        }
    }

    void return_home(Villager& v) {
        const Building* post = explorer_post(v);
        stop(v);
        if (post == nullptr || !walk_to(v, g_.door(*post))) {
            v.order = Order::None;
            fail(v);
            return;
        }
        v.order = Order::Returning;
        v.task = Task::Scout;
        v.target = {};
    }

    // Every so often, for an explorer under orders: it eats from what it
    // carries, and turns back with just enough left to get home, or cold.
    void scout_check(Villager& v) {
        const Building* post = explorer_post(v);
        if (post == nullptr) {
            v.order = Order::None;  // No longer an explorer.
            if (v.task == Task::Scout || v.task == Task::ScoutWait || v.task == Task::GoProvision) {
                fail(v);
            }
            return;
        }
        if (v.food < village::kEatBelow && v.provisions > 0) {
            const std::int32_t bite = std::min(v.provisions, village::kFoodMax - v.food);
            v.food += bite;
            v.provisions -= bite;
        }
        if (v.order != Order::Going && v.order != Order::Waiting) {
            return;
        }
        const std::int32_t meters = NavGrid::distance_estimate(v.position, g_.door(*post));
        const bool hungry = v.food + v.provisions < village::kHungryFood + food_for_walk(meters);
        const bool cold = v.warmth < village::kWarmthMax / 4;
        if ((hungry || cold) && meters > village::kHomeMeters) {
            g_.events_.push_back({Game::Event::Kind::ExplorerBack, v.owner, {}, v.position,
                                  static_cast<std::uint16_t>(hungry ? 0 : 1), 0});
            return_home(v);
        }
    }

    // Not enough food left to finish the walk it is on and then get to
    // where the food is: it goes to eat first, if that leaves it better off
    // (it turns back at the start of a long haul, not at the end). A walk
    // that even a villager who just ate cannot come back from is given up:
    // nobody starves for a site too far from any food.
    void eat_now(Villager& v) {
        if (v.task == Task::GoEat || v.task == Task::GoFight || v.task == Task::Fight || v.task == Task::GoFire ||
            v.task == Task::FightFire || v.task == Task::Flee || v.task == Task::Idle || v.task == Task::Wander) {
            return;  // (Idle and strolling villagers decide to eat by themselves.)
        }
        const EntityId food = storage_with(v.owner, v.position, kNoDef);
        const Building* b = g_.buildings_.get(food);
        if (b == nullptr) {
            return;
        }
        // What is left of the walk: five ticks a meter, a point every four.
        Fixed rest;
        FixedVec2 at = v.position;
        for (std::size_t i = v.path_index; i < v.path.size(); ++i) {
            rest += (v.path[i] - at).length();
            at = v.path[i];
        }
        const FixedVec2 table = g_.door(*b);
        const std::int32_t need =
            village::kHungryFood + rest.floor_int() * 5 / 4 + NavGrid::distance_estimate(at, table) * 5 / 4;
        if (v.food >= need) {
            return;
        }
        // A meal leaves the meter at 900 or more; coming back here costs the walk.
        const bool helps = v.food + 100 < village::kFoodMax - 100 - NavGrid::distance_estimate(v.position, table) * 5 / 4;
        if (!moving(v) || helps) {
            release(v);
            stop(v);
            go(v, Task::GoEat, food);
        } else {
            fail(v);  // Too far to go and come back.
        }
    }

    void decide(Villager& v) {
        const std::uint8_t owner = v.owner;
        // 0. An explorer under orders goes on with them (after fleeing, say).
        if (v.order != Order::None) {
            if (explorer_post(v) == nullptr) {
                v.order = Order::None;
            } else if (v.order == Order::Returning) {
                return_home(v);
                return;
            } else if (v.order == Order::Waiting) {
                v.task = Task::ScoutWait;
                return;
            } else {
                start_scout(v);
                return;
            }
        }
        // 1. Eat.
        if (v.food < village::kEatBelow) {
            const EntityId food = storage_with(owner, v.position, kNoDef);
            if (food.valid()) {
                go(v, Task::GoEat, food);
                return;
            }
        }
        // 1a. The bell: adults take up arms, children stay home.
        if (g_.players_[owner].alarm) {
            if (g_.adult(v) && v.disease == 0 && start_fight(v)) {
                return;
            }
            const Building* home = g_.buildings_.get(v.home);
            const Building* tc = g_.buildings_.get(g_.players_[owner].town_center);
            if (home != nullptr || tc != nullptr) {
                wander(v, g_.door(home != nullptr ? *home : *tc));
                return;
            }
        }
        // 1b. The sick rest at home.
        if (v.disease != 0) {
            if (const Building* home = g_.buildings_.get(v.home)) {
                wander(v, g_.door(*home));
                return;
            }
        }
        // 1c. A fire nearby: to the buckets.
        if (g_.fires_ > 0 && g_.adult(v) && start_firefighting(v)) {
            return;
        }
        // 2. Leftover goods.
        if (v.carrying.amount > 0) {
            if (const Building* job = g_.buildings_.get(v.job);
                job != nullptr && complete(*job) && free_space(*job) > 0 && gives_out(c_, *job, v.carrying.resource)) {
                go(v, Task::GoDeliver, v.job);
                return;
            }
            const EntityId s = storage_for(owner, v.position, v.carrying.resource);
            if (s.valid()) {
                go(v, Task::GoDeliver, s);
                return;
            }
            keep_gold(v);
            v.carrying = {};  // Nowhere to put it: dropped (gold goes to the town center).
        }
        if (!g_.adult(v)) {
            wander(v, home_point(v));
            return;
        }
        // 2b. Firewood for the home before it gets cold.
        if (start_home_firewood(v)) {
            return;
        }
        // 3. Job.
        if (Building* job = g_.buildings_.get(v.job); job != nullptr && complete(*job)) {
            const BuildingDef& d = def(*job);
            if (d.work == WorkKind::Gather && start_gathering(v, *job)) {
                return;
            }
            if (d.work == WorkKind::Produce && start_producing(v, *job)) {
                return;
            }
            if (d.work == WorkKind::Farm && start_farming(v, *job)) {
                return;
            }
            if (d.work == WorkKind::Hunt && start_hunting(v, *job)) {
                return;
            }
            if (d.work == WorkKind::Fish && start_fishing(v, *job)) {
                return;
            }
            if (d.kind == BuildingKind::Market && start_restocking(v, *job)) {
                return;
            }
            if (!d.service_uses.empty() && start_supplying(v, *job)) {
                return;
            }
            wander(v, g_.door(*job));
            return;
        }
        // 4. Laborer: construction, then hauling, then the town's gold.
        if (start_construction(v) || start_hauling(v) || start_moving_gold(v)) {
            return;
        }
        wander(v, home_point(v));
    }

    // Walking costs around a workplace, rebuilt when buildings change.
    const NavGrid::Area& work_area(EntityId id, const Building& b) {
        auto& [owner, area] = g_.work_areas_[id.index];
        if (owner != id || area.version != g_.nav_.version()) {
            owner = id;
            const Fixed cx = Fixed::from_int(b.x) + Fixed::from_ratio(b.width, 2);
            const Fixed cz = Fixed::from_int(b.z) + Fixed::from_ratio(b.depth, 2);
            area = g_.nav_.flood({cx, cz}, max_work_cost(def(b)));
        }
        return area;
    }

    // A work radius in meters as walking cost, with room for slopes and
    // small detours; far sides of rivers stay out.
    static std::uint16_t max_work_cost(const BuildingDef& d) {
        return static_cast<std::uint16_t>(std::clamp(d.work_radius * 5 * 3 / 2, 10, 60000));
    }

    bool start_gathering(Villager& v, const Building& job) {
        const BuildingDef& d = def(job);
        const NavGrid::Area& area = work_area(v.job, job);
        if (area.side == 0) {
            return false;
        }
        // Nodes can only be within the straight distance the cost allows.
        const std::int32_t reach = max_work_cost(d) / 5 + 2;
        const std::int32_t mx = job.x + job.width / 2;
        const std::int32_t mz = job.z + job.depth / 2;
        const std::int32_t side = g_.node_cells_side_;
        const std::int32_t cx0 = std::max(0, (mx - reach) / kNodeCell);
        const std::int32_t cz0 = std::max(0, (mz - reach) / kNodeCell);
        const std::int32_t cx1 = std::min(side - 1, (mx + reach) / kNodeCell);
        const std::int32_t cz1 = std::min(side - 1, (mz + reach) / kNodeCell);
        std::uint32_t best = 0;
        std::uint32_t best_cost = 0xFFFF;
        for (std::int32_t cz = cz0; cz <= cz1; ++cz) {
            for (std::int32_t cx = cx0; cx <= cx1; ++cx) {
                for (const std::uint32_t i : g_.node_cells_[static_cast<std::size_t>(cz * side + cx)]) {
                    const Node& n = g_.nodes_[i];
                    const MapFeature& f = g_.map_.features[i];
                    if (n.amount <= 0 || n.reserved != 0 || ((d.gathers >> static_cast<unsigned>(f.type)) & 1u) == 0) {
                        continue;
                    }
                    if (g_.frozen() && regrows(f)) {
                        continue;  // Frozen bushes and herbs.
                    }
                    // The cheapest cell next to the node (rocks may sit on steep ones).
                    const std::int32_t nx = g_.nav_.cell_of(f.x);
                    const std::int32_t nz = g_.nav_.cell_of(f.z);
                    std::uint32_t cost = 0xFFFF;
                    for (std::int32_t dz = -1; dz <= 1; ++dz) {
                        for (std::int32_t dx = -1; dx <= 1; ++dx) {
                            cost = std::min<std::uint32_t>(cost, area.at(nx + dx, nz + dz));
                        }
                    }
                    if (cost < best_cost) {
                        best_cost = cost;
                        best = i + 1;
                    }
                }
            }
        }
        if (best == 0) {
            return false;
        }
        const MapFeature& f = g_.map_.features[best - 1];
        v.task = Task::GoGather;
        v.node = best;
        g_.nodes_[best - 1].reserved = v_index_ + 1;
        // Stand a step away from the trunk or rock.
        const FixedVec2 p{f.x, f.z};
        const FixedVec2 to = p + (v.position - p).normalized() * Fixed::from_ratio(8, 10);
        if (!walk_to(v, to)) {
            fail(v);
        }
        return true;
    }

    [[nodiscard]] bool regrows(const MapFeature& f) const {
        const FeatureDef* fd = c_.feature(f.type);
        return fd != nullptr && fd->regrow_days > 0;
    }

    // Laborers carry what workplaces gathered or made to a storage.
    bool start_hauling(Villager& v) {
        EntityId best;
        DefIndex best_res = kNoDef;
        std::uint64_t best_d = UINT64_MAX;
        for (const EntityId id : g_.owned(v.owner)) {
            const Building& b = *g_.buildings_.get(id);
            if (!complete(b) || def(b).kind != BuildingKind::Workplace) {
                continue;
            }
            DefIndex res = kNoDef;
            std::int32_t most = 0;
            for (const Stock& st : b.stock) {
                if (st.amount > most && gives_out(c_, b, st.resource)) {
                    most = st.amount;
                    res = st.resource;
                }
            }
            // Worth a trip: a full load, or a workplace nearly full.
            if (res == kNoDef || (most < carry_capacity(c_, res) && total(b.stock) * 4 < def(b).storage * 3)) {
                continue;
            }
            const std::uint64_t d = distance2(v.position, g_.door(b));
            if (d < best_d) {
                best_d = d;
                best = id;
                best_res = res;
            }
        }
        if (!best.valid()) {
            return false;
        }
        const EntityId dest = storage_for(v.owner, g_.door(*g_.buildings_.get(best)), best_res);
        if (!dest.valid()) {
            return false;
        }
        v.site = dest;
        v.carrying = {best_res, 0};
        v.timer = 0;
        go(v, Task::GoFetch, best);
        return true;
    }

    // --- Gold (phase 28) ---------------------------------------------------------------

    // Gold a villager holds goes to the town center when it would be lost
    // (nowhere to put it, or the villager is gone): gold only changes hands
    // by trade, theft or fire.
    void keep_gold(const Villager& v) {
        if (v.carrying.resource != g_.gold_ || v.carrying.amount <= 0 || g_.gold_ == kNoDef) {
            return;
        }
        if (Building* tc = g_.buildings_.get(g_.players_[v.owner].town_center)) {
            add_to(tc->stock, g_.gold_, v.carrying.amount);
        }
    }

    // A storage that keeps gold other than the trading post and the town
    // center: a vault.
    [[nodiscard]] bool is_vault(const Building& b) const {
        return def(b).kind == BuildingKind::Storage && !def(b).trade && accepts(b, g_.gold_);
    }

    // Villagers of `town` fetching or carrying gold (counted once per step).
    std::int32_t gold_movers(std::uint8_t town) {
        if (!movers_counted_) {
            movers_counted_ = true;
            movers_.fill(0);
            for (const Villager& o : g_.villagers_.data()) {
                if (o.carrying.resource == g_.gold_ && (o.task == Task::GoFetch || o.task == Task::GoDeliver)) {
                    ++movers_[o.owner];
                }
            }
        }
        return movers_[town];
    }

    // Gold on its way into `to`: carried there, and the loads of those
    // still fetching it.
    [[nodiscard]] std::int32_t gold_coming(std::uint8_t town, EntityId to, bool with_fetching) const {
        std::int32_t n = 0;
        for (const Villager& o : g_.villagers_.data()) {
            if (o.owner != town || o.carrying.resource != g_.gold_) {
                continue;
            }
            if (o.task == Task::GoDeliver && o.target == to) {
                n += o.carrying.amount;
            } else if (with_fetching && o.task == Task::GoFetch && o.site == to) {
                n += carry_capacity(c_, g_.gold_);
            }
        }
        return n;
    }

    // The nearest vault of `town` with room for gold, or with gold.
    [[nodiscard]] EntityId vault_near(std::uint8_t town, FixedVec2 from, bool with_gold) const {
        EntityId best;
        std::uint64_t best_d = UINT64_MAX;
        for (const EntityId id : g_.owned(town)) {
            const Building& b = *g_.buildings_.get(id);
            if (!complete(b) || !is_vault(b) ||
                (with_gold ? amount_of(b.stock, g_.gold_) <= 0 : free_space(b) <= 0)) {
                continue;
            }
            const std::uint64_t d = distance2(from, g_.door(b));
            if (d < best_d) {
                best_d = d;
                best = id;
            }
        }
        return best;
    }

    // The trading post keeps the gold its player set (its `limit`): laborers
    // take what is over to a vault (or the town center) and bring what is
    // missing from one (or from the town center). Gold in the town center
    // goes to a vault when there is one.
    bool start_moving_gold(Villager& v) {
        const DefIndex gold = g_.gold_;
        const std::uint8_t town = v.owner;
        if (gold == kNoDef || (no_gold_work_ >> town & 1u) != 0 || gold_movers(town) >= kGoldMovers) {
            return false;
        }
        Building* tc = g_.buildings_.get(g_.players_[town].town_center);
        const EntityId tc_id = g_.players_[town].town_center;
        EntityId from, to;
        if (Building* post = trading_post(town)) {
            const EntityId post_id = id_of(*post);
            const std::int32_t in_post = amount_of(post->stock, gold);
            if (in_post > post->limit) {
                from = post_id;
                to = vault_near(town, g_.door(*post), false);
                if (!to.valid() && tc != nullptr) {
                    to = tc_id;
                }
            } else if (in_post < post->limit && free_space(*post) > 0) {
                from = vault_near(town, g_.door(*post), true);
                if (!from.valid() && tc != nullptr && amount_of(tc->stock, gold) > 0) {
                    from = tc_id;
                }
                // Not if what is on its way fills it.
                if (from.valid() && in_post + gold_coming(town, post_id, true) < post->limit) {
                    to = post_id;
                } else {
                    from = {};
                }
            }
        }
        if ((!from.valid() || !to.valid()) && tc != nullptr && amount_of(tc->stock, gold) > 0) {
            from = tc_id;
            to = vault_near(town, g_.door(*tc), false);
        }
        if (!from.valid() || !to.valid() || from == to) {
            no_gold_work_ |= 1u << town;  // Nothing to move this step: the others need not look.
            return false;
        }
        v.site = to;
        v.carrying = {gold, 0};
        v.timer = 0;
        go(v, Task::GoFetch, from);
        ++movers_[town];
        return true;
    }

    // How much gold a mover may take from `from` for `to`: a trading post
    // keeps its reserve, and one is filled no further than it.
    [[nodiscard]] std::int32_t gold_to_move(const Building& from, EntityId to, std::uint8_t town) const {
        if (def(from).trade) {
            return std::max(0, amount_of(from.stock, g_.gold_) - from.limit);
        }
        if (const Building* post = g_.buildings_.get(to); post != nullptr && def(*post).trade) {
            return std::max(0, post->limit - amount_of(post->stock, g_.gold_) - gold_coming(town, to, false));
        }
        return INT32_MAX;
    }

    bool start_home_firewood(Villager& v) {
        if (g_.firewood_ == kNoDef) {
            return false;
        }
        const Building* home = g_.buildings_.get(v.home);
        const Season season = g_.calendar().season;
        const bool cold_ahead = g_.temperature_ < village::kColdBelow || season == Season::Autumn || season == Season::Winter;
        if (home == nullptr || !cold_ahead || amount_of(home->stock, g_.firewood_) + amount_of(home->incoming, g_.firewood_) >=
                                                    village::kHouseFirewood / 2) {
            return false;
        }
        const EntityId from = storage_with(v.owner, v.position, g_.firewood_);
        if (!from.valid()) {
            return false;
        }
        v.site = v.home;  // The goods go home.
        v.carrying = {g_.firewood_, 0};
        v.timer = 0;
        go(v, Task::GoFetch, from);
        return true;
    }

    // --- Wildlife, raiders and the militia (phase 15) -------------------------------------

    struct CreatureStats {
        std::int32_t speed;   // Hundredths of a meter per tick.
        std::int32_t health;
        std::int32_t damage;  // Per bite or blow, every 10 ticks.
        std::int32_t aggro;   // Meters: predators attack, prey flees, raiders fight.
    };
    static constexpr CreatureStats kStats[] = {
        {30, 150, 0, 14},   // Deer: flee.
        {25, 300, 30, 4},   // Boar: bite once when cornered.
        {32, 250, 40, 18},  // Wolf.
        {26, 700, 120, 12}, // Bear.
        {22, 400, 60, 6},   // Raider.
        {21, 500, 50, 16},  // Soldier (its unit decides).
    };
    [[nodiscard]] static const CreatureStats& stats(CreatureKind k) {
        return kStats[static_cast<std::size_t>(k) % std::size(kStats)];
    }
    [[nodiscard]] static CreatureKind kind_of(ZoneType t) {
        switch (t) {
            case ZoneType::Deer: return CreatureKind::Deer;
            case ZoneType::Boar: return CreatureKind::Boar;
            case ZoneType::Wolves: return CreatureKind::Wolf;
            case ZoneType::Bears: return CreatureKind::Bear;
            case ZoneType::Count: break;
        }
        return CreatureKind::Deer;
    }

    // A walkable point near `at` within `radius` meters (or `at`).
    [[nodiscard]] FixedVec2 open_point(FixedVec2 at, std::int32_t radius) {
        for (int attempt = 0; attempt < 8; ++attempt) {
            const FixedVec2 p{at.x + Fixed::from_int(g_.rng_.range(-radius, radius)),
                              at.z + Fixed::from_int(g_.rng_.range(-radius, radius))};
            const std::int32_t cx = p.x.floor_int() / NavGrid::kCellMeters;
            const std::int32_t cz = p.z.floor_int() / NavGrid::kCellMeters;
            if (g_.nav_.walkable(cx, cz)) {
                return p;
            }
        }
        return at;
    }

    void spawn_animal(std::size_t z) {
        const Zone& zone = g_.map_.zones[z];
        Creature a;
        a.kind = kind_of(zone.type);
        a.zone = static_cast<std::uint16_t>(z);
        a.home = {zone.x, zone.z};
        a.position = open_point(a.home, std::max(2, zone.radius.floor_int()));
        a.previous = a.position;
        a.goal = a.position;
        a.health = stats(a.kind).health;
        a.timer = static_cast<std::int32_t>(g_.rng_.below(10));
        g_.creatures_.add(g_.registry_.create(), a);
    }

    void remove_creature(EntityId id) {
        const Creature* a = g_.creatures_.get(id);
        if (a == nullptr) {
            return;
        }
        if (a->kind != CreatureKind::Raider && a->zone < g_.zone_animals_.size()) {
            g_.zone_animals_[a->zone] = std::max(0, g_.zone_animals_[a->zone] - 1);
        }
        g_.creatures_.remove(id);
        g_.registry_.destroy(id);
    }

    // Villagers by 32 m square, rebuilt each tick for the creatures.
    struct Grid {
        std::int32_t side = 0;
        std::vector<std::pair<std::uint32_t, std::uint32_t>> cells;  // (square, villager index), sorted.
    };
    Grid grid_;
    static constexpr std::int32_t kGridMeters = 32;

    void build_grid() {
        grid_.side = (g_.map_.size + kGridMeters - 1) / kGridMeters;
        grid_.cells.clear();
        const auto& vs = g_.villagers_;
        for (std::size_t k = 0; k < vs.size(); ++k) {
            const FixedVec2 p = vs.data()[k].position;
            const std::int32_t gx = std::clamp(p.x.floor_int() / kGridMeters, 0, grid_.side - 1);
            const std::int32_t gz = std::clamp(p.z.floor_int() / kGridMeters, 0, grid_.side - 1);
            grid_.cells.emplace_back(static_cast<std::uint32_t>(gz * grid_.side + gx), static_cast<std::uint32_t>(k));
        }
        std::sort(grid_.cells.begin(), grid_.cells.end());
    }

    // The nearest villager within `radius` meters (of a town, if given).
    [[nodiscard]] EntityId villager_near(FixedVec2 at, std::int32_t radius, std::int32_t town = -1) const {
        EntityId best;
        std::uint64_t best_d = meters2(radius);
        const std::int32_t reach = radius / kGridMeters + 1;
        const std::int32_t gx = at.x.floor_int() / kGridMeters;
        const std::int32_t gz = at.z.floor_int() / kGridMeters;
        const auto& vs = g_.villagers_;
        for (std::int32_t z = std::max(0, gz - reach); z <= std::min(grid_.side - 1, gz + reach); ++z) {
            for (std::int32_t x = std::max(0, gx - reach); x <= std::min(grid_.side - 1, gx + reach); ++x) {
                const auto key = static_cast<std::uint32_t>(z * grid_.side + x);
                auto it = std::lower_bound(grid_.cells.begin(), grid_.cells.end(), std::make_pair(key, 0u));
                for (; it != grid_.cells.end() && it->first == key; ++it) {
                    const Villager& v = vs.data()[it->second];
                    if (town >= 0 && v.owner != town) {
                        continue;
                    }
                    const std::uint64_t d = distance2(v.position, at);
                    if (d < best_d) {
                        best_d = d;
                        best = vs.entities()[it->second];
                    }
                }
            }
        }
        return best;
    }

    // Moves toward `to` by `step`; false if the ground ahead is blocked.
    bool step_toward(Creature& a, FixedVec2 to, Fixed step) {
        const FixedVec2 d = to - a.position;
        const Fixed len = d.length();
        if (len <= step) {
            a.position = to;
            return true;
        }
        const FixedVec2 next = a.position + d * (step / len);
        const std::int32_t cx = next.x.floor_int() / NavGrid::kCellMeters;
        const std::int32_t cz = next.z.floor_int() / NavGrid::kCellMeters;
        if (!g_.nav_.ground(cx, cz)) {
            return false;
        }
        a.position = next;
        return true;
    }

    [[nodiscard]] const UnitDef* unit_of(const Creature& a) const {
        return a.kind == CreatureKind::Soldier && a.unit < c_.units.size() ? &c_.units[a.unit] : nullptr;
    }
    [[nodiscard]] std::int32_t damage_of(const Creature& a) const {
        const UnitDef* u = unit_of(a);
        return u != nullptr ? u->damage : stats(a.kind).damage;
    }
    [[nodiscard]] std::int32_t max_health(const Creature& a) const {
        const UnitDef* u = unit_of(a);
        return u != nullptr ? u->health : stats(a.kind).health;
    }
    [[nodiscard]] std::int32_t every_of(const Creature& a) const {
        const UnitDef* u = unit_of(a);
        return u != nullptr ? u->attack_every : 10;
    }
    [[nodiscard]] std::int32_t range_of(const Creature& a) const {
        const UnitDef* u = unit_of(a);
        return u != nullptr ? u->range : 1;
    }
    [[nodiscard]] Fixed speed_of(const Creature& a) const {
        const UnitDef* u = unit_of(a);
        return Fixed::from_ratio(u != nullptr ? u->speed : stats(a.kind).speed, 100) * Fixed::from_ratio(200 - g_.snow_, 200);
    }

    // A villager is attacked: it runs to the town center unless it fights.
    void hurt(Villager& v, EntityId id, std::int32_t damage, CreatureKind by, EntityId attacker) {
        v.health -= damage;
        if (v.task == Task::Fight || v.task == Task::GoFight) {
            v.target = attacker;  // Fights back.
            v.task = Task::Fight;
            v.path.clear();
            v.path_index = 0;
            return;
        }
        if (v.task != Task::Flee) {
            release(v);
            v.task = Task::Flee;
            const Building* tc = g_.buildings_.get(g_.players_[v.owner].town_center);
            if (tc == nullptr || !walk_to(v, g_.door(*tc))) {
                v.task = Task::Idle;
            }
            g_.events_.push_back({Game::Event::Kind::Attacked, v.owner, id, v.position, static_cast<std::uint16_t>(by), 0});
        }
    }

    void animal_think(Creature& a) {
        const CreatureStats& st = stats(a.kind);
        const Zone& zone = g_.map_.zones[std::min<std::size_t>(a.zone, g_.map_.zones.size() - 1)];
        const std::int32_t territory = zone.radius.floor_int() + 20;
        const std::int32_t threat = threat_percent(g_.rules_.wildlife);
        if (a.kind == CreatureKind::Deer) {
            const EntityId near = villager_near(a.position, st.aggro);
            if (const Villager* v = g_.villagers_.get(near)) {
                // Away from the villager.
                const FixedVec2 away = a.position - v->position;
                const Fixed len = away.length();
                if (len > Fixed{}) {
                    a.goal = a.position + away * (Fixed::from_int(16) / len);
                    a.state = CreatureState::Flee;
                    return;
                }
            }
        } else if (a.state != CreatureState::Chase && threat > 0) {
            const std::int32_t reach = a.kind == CreatureKind::Boar ? st.aggro : st.aggro * std::min(threat, 200) / 100;
            const EntityId near = villager_near(a.position, reach);
            if (near.valid() && distance2(a.position, a.home) <= meters2(territory) &&
                (a.kind != CreatureKind::Boar || g_.rng_.below(2) == 0)) {
                a.state = CreatureState::Chase;
                a.target = near;
                a.target_kind = TargetKind::Villager;
                return;
            }
        }
        if (a.state == CreatureState::Chase && a.target_kind == TargetKind::Creature) {
            if (g_.creatures_.get(a.target) == nullptr || distance2(a.position, a.home) > meters2(territory + 20)) {
                a.state = CreatureState::Wander;
                a.target = {};
                a.goal = a.home;
            }
            return;
        }
        if (a.state == CreatureState::Chase) {
            const Villager* v = g_.villagers_.get(a.target);
            if (v == nullptr || distance2(a.position, a.home) > meters2(territory + 20) ||
                (v->task == Task::Flee && distance2(v->position, a.home) > meters2(territory))) {
                a.state = CreatureState::Wander;
                a.target = {};
                a.goal = a.home;
            }
            return;
        }
        // Wandering in the zone, now and then.
        if (a.position == a.goal || g_.rng_.below(8) == 0) {
            a.state = CreatureState::Wander;
            a.goal = open_point(a.home, std::max(2, zone.radius.floor_int()));
        }
    }

    // Raiders: every 10 ticks, look for someone to fight or give up.
    void raider_think(Creature& a) {
        if (a.state == CreatureState::Leave) {
            return;
        }
        if (a.health * 100 < max_health(a) * 35) {
            leave(a);
            return;
        }
        if (a.state == CreatureState::Chase) {
            const FixedVec2* at = nullptr;
            if (a.target_kind == TargetKind::Creature) {
                const Creature* o = g_.creatures_.get(a.target);
                at = o != nullptr ? &o->position : nullptr;
            } else {
                const Villager* v = g_.villagers_.get(a.target);
                at = v != nullptr ? &v->position : nullptr;
            }
            if (at == nullptr || distance2(*at, a.position) > meters2(14)) {
                resume_raid(a);
            }
            return;
        }
        if (a.state == CreatureState::Bash) {
            return;
        }
        // Soldiers of the town first, then anybody.
        const EntityId soldier = creature_near(a.position, stats(a.kind).aggro, [&](const Creature& o) {
            return o.kind == CreatureKind::Soldier && o.town == a.town && o.state != CreatureState::Travel;
        });
        if (soldier.valid()) {
            a.state = CreatureState::Chase;
            a.target = soldier;
            a.target_kind = TargetKind::Creature;
            return;
        }
        const EntityId near = villager_near(a.position, stats(a.kind).aggro, a.town);
        if (near.valid()) {
            a.state = CreatureState::Chase;
            a.target = near;
            a.target_kind = TargetKind::Villager;
        }
    }

    // Back on the way to the raid's target (or a new one).
    void resume_raid(Creature& a) {
        const Building* target = g_.buildings_.get(a.target);
        if (target == nullptr || target->owner != a.town) {
            a.target = raid_target(a.town, a.position);
            target = g_.buildings_.get(a.target);
        }
        if (target == nullptr || !g_.nav_.find_path_through(a.position, g_.door(*target), a.path)) {
            leave(a);
            return;
        }
        a.path_index = 0;
        a.state = CreatureState::Approach;
    }

    void leave(Creature& a) {
        a.state = CreatureState::Leave;
        a.path_index = 0;
        if (!g_.nav_.find_path_through(a.position, a.home, a.path)) {
            a.path.clear();
        }
    }

    // What raiders go for: the fullest store, or a house.
    [[nodiscard]] EntityId raid_target(std::uint8_t town, FixedVec2 from) {
        EntityId best;
        std::int64_t best_score = INT64_MIN;
        const bool burn = g_.rng_.below(3) == 0;
        const auto& list = g_.buildings_;
        for (std::size_t i = 0; i < list.size(); ++i) {
            const Building& b = list.data()[i];
            if (b.owner != town || !complete(b) || def(b).kind == BuildingKind::Defense) {
                continue;
            }
            std::int64_t score = burn ? (def(b).kind == BuildingKind::House ? 1000 : 0) : total(b.stock) * 10;
            score -= static_cast<std::int64_t>(distance2(from, center_of(b)) >> 36);  // Nearer is better.
            if (score > best_score) {
                best_score = score;
                best = list.entities()[i];
            }
        }
        return best;
    }

    // The building on a cell, if any (raiders breaking through).
    [[nodiscard]] EntityId building_at(std::int32_t x, std::int32_t z) const {
        const auto& list = g_.buildings_;
        for (std::size_t i = 0; i < list.size(); ++i) {
            const Building& b = list.data()[i];
            if (x >= b.x && x < b.x + b.width && z >= b.z && z < b.z + b.depth && !def(b).trap) {
                return list.entities()[i];
            }
        }
        return {};
    }

    void raider_move(Creature& a, EntityId self) {
        Fixed budget = speed_of(a);
        while (budget > Fixed{} && a.path_index < a.path.size()) {
            const FixedVec2 to = a.path[a.path_index];
            const FixedVec2 d = to - a.position;
            const Fixed len = d.length();
            const FixedVec2 next = len <= budget ? to : a.position + d * (budget / len);
            // Something built in the way: break it first.
            const std::int32_t cx = next.x.floor_int();
            const std::int32_t cz = next.z.floor_int();
            if (g_.nav_.obstacle(cx / NavGrid::kCellMeters, cz / NavGrid::kCellMeters)) {
                const EntityId wall = building_at(cx, cz);
                const Building* b = g_.buildings_.get(wall);
                if (b != nullptr && (a.state == CreatureState::Leave || wall != a.target)) {
                    a.state = a.state == CreatureState::Leave ? CreatureState::Leave : CreatureState::Bash;
                    a.goal = a.path[a.path_index];
                    bash(a, wall);
                    return;
                }
            }
            if (len <= budget) {
                a.position = to;
                budget -= len;
                ++a.path_index;
            } else {
                a.position = next;
                budget = Fixed{};
            }
        }
        if (a.path_index >= a.path.size()) {
            if (a.state == CreatureState::Leave) {
                gone_.push_back(self);  // Back beyond the edge, with its loot.
            } else if (a.state == CreatureState::Approach) {
                raid(a);
            }
        }
    }

    // Blows at a building in the way (every 10 ticks).
    void bash(Creature& a, EntityId id) {
        if (++a.timer % 10 != 0) {
            return;
        }
        Building* b = g_.buildings_.get(id);
        if (b == nullptr) {
            return;
        }
        b->damage += damage_of(a);
        if (def(*b).kind == BuildingKind::TownCenter && a.kind == CreatureKind::Raider) {
            b->damage = std::min(b->damage, def(*b).hp - 1);  // Raiders cannot bring a town center down.
        }
        if (b->damage >= def(*b).hp) {
            remove_building(id);
            if (a.state == CreatureState::Bash) {
                a.state = CreatureState::Approach;
            }
        }
    }

    // At the target: rob it, or set it on fire, then go.
    void raid(Creature& a) {
        Building* b = g_.buildings_.get(a.target);
        if (b == nullptr || b->owner != a.town) {
            resume_raid(a);
            return;
        }
        if (total(b->stock) > 0) {
            // The most of one good it can carry.
            Stock* most = nullptr;
            for (Stock& st : b->stock) {
                most = most == nullptr || st.amount > most->amount ? &st : most;
            }
            const std::int32_t take = std::min(most->amount, 30);
            a.loot = {most->resource, take};
            most->amount -= take;
            compact(b->stock);
        } else if (!def(*b).fireproof) {
            ignite(*b, a.target);
        } else {
            b->damage = std::min(def(*b).hp - 1, b->damage + damage_of(a) * 5);
        }
        leave(a);
    }

    void update_creatures() {
        if (g_.creatures_.size() == 0) {
            return;
        }
        build_grid();
        gone_.clear();
        auto& cs = g_.creatures_;
        for (std::size_t i = 0; i < cs.size(); ++i) {
            Creature& a = cs.data()[i];
            const EntityId self = cs.entities()[i];
            a.previous = a.position;
            const bool think = (g_.tick_ + self.index) % 10 == 0;
            if (a.kind == CreatureKind::Soldier) {
                soldier_tick(a, self, think);
                continue;
            }
            if (a.kind == CreatureKind::Raider) {
                if (think) {
                    raider_think(a);
                }
                if (a.state == CreatureState::Chase) {
                    fight(a, self);
                } else {
                    raider_move(a, self);
                }
                continue;
            }
            if (think) {
                animal_think(a);
            }
            if (a.state == CreatureState::Chase) {
                fight(a, self);
            } else if (!step_toward(a, a.goal, speed_of(a) * (a.state == CreatureState::Flee ? Fixed::one() : Fixed::from_ratio(1, 3)))) {
                a.goal = a.position;
            }
        }
        for (const EntityId id : gone_) {
            if (const Creature* a = g_.creatures_.get(id); a != nullptr) {
                remove_creature(id);
            }
        }
        // Dead creatures.
        std::vector<EntityId> dead;
        for (std::size_t i = 0; i < cs.size(); ++i) {
            if (cs.data()[i].health <= 0) {
                dead.push_back(cs.entities()[i]);
            }
        }
        for (const EntityId id : dead) {
            remove_creature(id);
        }
    }
    std::vector<EntityId> gone_;

    void fight(Creature& a, EntityId self) {
        if (a.target_kind == TargetKind::Creature) {
            fight_creature(a, self);
        } else {
            fight_villager(a, self);
        }
    }

    // The nearest creature within `radius` meters that `pick` accepts.
    template <typename Pick>
    [[nodiscard]] EntityId creature_near(FixedVec2 at, std::int32_t radius, Pick pick) const {
        EntityId best;
        std::uint64_t best_d = meters2(radius);
        const auto& cs = g_.creatures_;
        for (std::size_t i = 0; i < cs.size(); ++i) {
            const Creature& o = cs.data()[i];
            if (o.health <= 0 || !pick(o)) {
                continue;
            }
            const std::uint64_t d = distance2(o.position, at);
            if (d < best_d) {
                best_d = d;
                best = cs.entities()[i];
            }
        }
        return best;
    }

    // Creature against creature: soldiers, raiders, animals.
    void fight_creature(Creature& a, EntityId self) {
        Creature* o = g_.creatures_.get(a.target);
        if (o == nullptr || o->health <= 0 || o->state == CreatureState::Travel) {
            a.target = {};
            a.target_kind = TargetKind::Villager;
            if (a.kind == CreatureKind::Raider) {
                resume_raid(a);
            } else {
                a.state = CreatureState::Wander;
                a.goal = a.kind == CreatureKind::Soldier ? a.position : a.home;
            }
            return;
        }
        const std::int32_t reach = range_of(a);
        if (distance2(a.position, o->position) > meters2(reach) + (meters2(1) >> 1)) {
            (void)step_toward(a, o->position, speed_of(a));
            return;
        }
        if (++a.timer % every_of(a) != 0) {
            return;
        }
        o->health -= damage_of(a);
        // Whoever is hit fights back (deer run).
        if (o->kind != CreatureKind::Deer && o->state != CreatureState::Chase && o->state != CreatureState::Travel &&
            o->state != CreatureState::Leave) {
            o->state = CreatureState::Chase;
            o->target = self;
            o->target_kind = TargetKind::Creature;
        }
    }

    // --- Soldiers (phase 16) ----------------------------------------------------------

    [[nodiscard]] bool foe_of_soldier(const Creature& me, const Creature& o) const {
        if (o.state == CreatureState::Travel) {
            return false;
        }
        switch (o.kind) {
            case CreatureKind::Raider: return o.state != CreatureState::Leave;
            case CreatureKind::Wolf:
            case CreatureKind::Bear: return true;
            case CreatureKind::Soldier: return g_.enemies(me.town, o.town);
            default: return false;
        }
    }

    [[nodiscard]] FixedVec2 rally_of(std::uint8_t town) const {
        const PlayerState& ps = g_.players_[town];
        if (ps.rally.x != Fixed{} || ps.rally.z != Fixed{}) {
            return ps.rally;
        }
        const Building* tc = g_.buildings_.get(ps.town_center);
        return tc != nullptr ? g_.door(*tc) : FixedVec2{};
    }

    // Separate maps: whether a soldier is on another town's map.
    [[nodiscard]] bool in_region_of(const Creature& a, std::uint8_t town) const {
        return g_.map_.region_size() == 0 ||
               g_.map_.region_at(a.position.x.floor_int(), a.position.z.floor_int()) == static_cast<std::int32_t>(town);
    }

    // Off to another map over the world map; back on its edge later.
    void travel(Creature& a, std::uint8_t to) {
        a.state = CreatureState::Travel;
        a.timer = static_cast<std::int32_t>(g_.travel_ticks(a.town, to));
        a.goal = {Fixed::from_int(to), Fixed{}};  // Where to, while away.
        a.path.clear();
        a.path_index = 0;
    }

    void arrive_from_travel(Creature& a) {
        const std::uint8_t to = static_cast<std::uint8_t>(a.goal.x.floor_int());
        // Over the sea to another island (phase 22): ashore near the town.
        if (g_.map_.region_size() == 0) {
            const Building* tc = g_.buildings_.get(g_.players_[to].town_center);
            FixedVec2 at;
            if (tc != nullptr && coast_landing(g_.door(*tc), at, nullptr)) {
                a.position = at;
                a.previous = at;
                a.state = CreatureState::Wander;
                return;
            }
        }
        const Game::Region r = g_.region(to);
        // A walkable point on the edge nearest the town it came from.
        FixedVec2 at{Fixed::from_int(r.x + r.size / 2), Fixed::from_int(r.z + 8)};
        for (int attempt = 0; attempt < 12; ++attempt) {
            const std::int32_t along = static_cast<std::int32_t>(g_.rng_.below(static_cast<std::uint32_t>(r.size - 16))) + 8;
            const std::int32_t side = attempt % 4;
            const std::int32_t x = side == 0 ? 8 : side == 1 ? r.size - 9 : along;
            const std::int32_t z = side == 2 ? 8 : side == 3 ? r.size - 9 : along;
            const FixedVec2 p{Fixed::from_int(r.x + x), Fixed::from_int(r.z + z)};
            if (g_.nav_.walkable(p.x.floor_int() / NavGrid::kCellMeters, p.z.floor_int() / NavGrid::kCellMeters)) {
                at = p;
                break;
            }
        }
        a.position = at;
        a.previous = at;
        a.state = CreatureState::Wander;
    }

    void soldier_tick(Creature& a, EntityId self, bool think) {
        if (a.state == CreatureState::Travel) {
            if (--a.timer <= 0) {
                arrive_from_travel(a);
            }
            return;
        }
        const PlayerState& ps = g_.players_[a.town];
        if (think && a.state != CreatureState::Chase) {
            soldier_think(a);
        }
        if (a.state == CreatureState::Chase) {
            if (a.target_kind == TargetKind::Creature) {
                fight_creature(a, self);
            } else {
                a.state = CreatureState::Wander;
            }
            return;
        }
        // Following a path: to the rally point, or at the enemy (breaking
        // what is in the way).
        Fixed budget = speed_of(a);
        const bool siege = ps.order == ArmyOrderKind::Attack && a.target_kind == TargetKind::Building;
        while (budget > Fixed{} && a.path_index < a.path.size()) {
            const FixedVec2 to = a.path[a.path_index];
            const FixedVec2 d = to - a.position;
            const Fixed len = d.length();
            const FixedVec2 next = len <= budget ? to : a.position + d * (budget / len);
            if (siege) {
                const std::int32_t cx = next.x.floor_int();
                const std::int32_t cz = next.z.floor_int();
                if (g_.nav_.obstacle(cx / NavGrid::kCellMeters, cz / NavGrid::kCellMeters)) {
                    const EntityId wall = building_at(cx, cz);
                    if (wall.valid() && wall != a.target) {
                        strike(a, wall);
                        return;
                    }
                }
            }
            if (len <= budget) {
                a.position = to;
                budget -= len;
                ++a.path_index;
            } else {
                a.position = next;
                budget = Fixed{};
            }
        }
        if (a.path_index >= a.path.size() && siege) {
            strike(a, a.target);
        }
    }

    // Every 10 ticks: an enemy to fight, or the order to follow.
    void soldier_think(Creature& a) {
        const PlayerState& ps = g_.players_[a.town];
        if (ps.outcome == Outcome::Lost) {
            a.health = 0;
            return;
        }
        if (ps.order != ArmyOrderKind::Retreat) {
            const std::int32_t reach = std::max(range_of(a) + 6, 16);
            const EntityId foe = creature_near(a.position, reach, [&](const Creature& o) { return foe_of_soldier(a, o); });
            if (foe.valid()) {
                a.state = CreatureState::Chase;
                a.target = foe;
                a.target_kind = TargetKind::Creature;
                a.path.clear();
                a.path_index = 0;
                return;
            }
        }
        const bool moving = a.path_index < a.path.size();
        switch (ps.order) {
            case ArmyOrderKind::Attack: {
                const PlayerState& enemy = g_.players_[ps.enemy];
                const Building* tc = g_.buildings_.get(enemy.town_center);
                if (tc == nullptr || !g_.enemies(a.town, ps.enemy)) {
                    return;  // Nothing left to attack: wait there.
                }
                // Another map, or across the sea: over the world map.
                if (!in_region_of(a, ps.enemy) || !g_.nav_.same_land(a.position, g_.door(*tc))) {
                    travel(a, ps.enemy);
                    return;
                }
                if (!moving && (a.target != enemy.town_center || a.target_kind != TargetKind::Building ||
                                distance2(a.position, g_.door(*tc)) > meters2(12))) {
                    a.target = enemy.town_center;
                    a.target_kind = TargetKind::Building;
                    a.path_index = 0;
                    if (!g_.nav_.find_path_through(a.position, g_.door(*tc), a.path)) {
                        a.path.clear();
                    }
                }
                return;
            }
            case ArmyOrderKind::Defend:
            case ArmyOrderKind::Retreat:
            case ArmyOrderKind::Count: {
                const FixedVec2 at = rally_of(a.town);
                if (!in_region_of(a, a.town) || !g_.nav_.same_land(a.position, at)) {
                    travel(a, a.town);
                    return;
                }
                a.target_kind = TargetKind::Villager;
                a.target = {};
                if (!moving && distance2(a.position, at) > meters2(8)) {
                    // Around the rally point, not all on one spot.
                    const FixedVec2 spot{at.x + Fixed::from_int(g_.rng_.range(-5, 5)), at.z + Fixed::from_int(g_.rng_.range(-5, 5))};
                    a.path_index = 0;
                    if (!g_.nav_.find_path(a.position, spot, a.path)) {
                        a.path.clear();
                    }
                }
                return;
            }
        }
    }

    // Soldiers hitting a building (every attack): a town center brought
    // down loses its town the game.
    void strike(Creature& a, EntityId id) {
        if (++a.timer % every_of(a) != 0) {
            return;
        }
        Building* b = g_.buildings_.get(id);
        if (b == nullptr) {
            a.target = {};
            return;
        }
        if (b->owner != a.town && !g_.enemies(a.town, b->owner)) {
            return;  // Allies' walls are left alone.
        }
        b->damage += damage_of(a) * 2;
        if (b->damage >= def(*b).hp) {
            const std::uint8_t owner = b->owner;
            const bool tc = id == g_.players_[owner].town_center;
            remove_building(id);
            a.path.clear();
            a.path_index = 0;
            if (tc) {
                g_.players_[owner].town_center = {};
                check_outcomes();
            }
        }
    }

    // Barracks: the unit in front is trained, then takes a villager and
    // its equipment.
    void train() {
        auto& list = g_.buildings_;
        for (std::size_t i = 0; i < list.size(); ++i) {
            Building& b = list.data()[i];
            if (!def(b).trains || !complete(b) || b.training.empty()) {
                continue;
            }
            const DefIndex u = b.training.front();
            if (u >= c_.units.size()) {
                b.training.erase(b.training.begin());
                continue;
            }
            const UnitDef& unit = c_.units[u];
            if (b.train_progress < unit.train_work) {
                b.train_progress = std::min(unit.train_work, b.train_progress + 10);
                continue;
            }
            // Ready: someone to arm, and the arms.
            bool have = true;
            for (const ResourceAmount& c : unit.cost) {
                have = have && g_.tradeable(b.owner, c.resource) >= c.amount;
            }
            EntityId recruit;
            std::uint64_t best = UINT64_MAX;
            const FixedVec2 door = g_.door(b);
            for (std::size_t k = 0; k < g_.villagers_.size() && have; ++k) {
                const Villager& v = g_.villagers_.data()[k];
                // Laborers first: a villager with a job counts double the distance.
                const std::uint64_t d = distance2(v.position, door) * (v.job.valid() ? 2u : 1u);
                if (v.owner == b.owner && g_.adult(v) && v.disease == 0 && d < best) {
                    best = d;
                    recruit = g_.villagers_.entities()[k];
                }
            }
            if (!have || !recruit.valid()) {
                continue;
            }
            for (const ResourceAmount& c : unit.cost) {
                (void)take_from_town(b.owner, c.resource, c.amount);
            }
            kill(recruit, true);
            --g_.players_[b.owner].deaths;  // Not a death: a soldier now.
            Creature s;
            s.kind = CreatureKind::Soldier;
            s.state = CreatureState::Wander;
            s.town = b.owner;
            s.zone = 0xFFFF;
            s.unit = u;
            s.position = door;
            s.previous = door;
            s.home = door;
            s.goal = door;
            s.health = unit.health;
            s.timer = static_cast<std::int32_t>(g_.rng_.below(10));
            g_.creatures_.add(g_.registry_.create(), s);
            b.training.erase(b.training.begin());
            b.train_progress = 0;
            g_.events_.push_back({Game::Event::Kind::UnitTrained, b.owner, {}, door, u, 0});
        }
    }

    // Who is still in the game, and whether it is over (section 6.3).
    void check_outcomes() {
        if (g_.game_over_) {
            return;
        }
        std::vector<std::uint8_t> towns;
        for (std::uint8_t p = 0; p < g_.player_count_; ++p) {
            if (g_.town_of(p) == p && g_.players_[p].active) {
                towns.push_back(p);
            }
        }
        const GameRules& rules = g_.rules_;
        for (const std::uint8_t p : towns) {
            PlayerState& ps = g_.players_[p];
            if (ps.outcome != Outcome::Playing) {
                continue;
            }
            const bool no_center = g_.buildings_.get(ps.town_center) == nullptr;
            const bool no_people = g_.population(p) == 0 && g_.soldiers(p) == 0;
            const bool objective = rules.versus && rules.victory == Victory::Objective;
            if (no_center || (no_people && !objective)) {
                ps.outcome = Outcome::Lost;
                ps.alarm = false;
                g_.events_.push_back({Game::Event::Kind::TownLost, p, {}, {}, 0, 0});
            }
        }
        std::vector<std::uint8_t> alive;
        for (const std::uint8_t p : towns) {
            if (g_.players_[p].outcome == Outcome::Playing) {
                alive.push_back(p);
            }
        }
        std::int32_t winner = -1;
        bool over = alive.empty();
        if (rules.versus && !over) {
            switch (rules.victory) {
                case Victory::Elimination:
                case Victory::Objective:
                    if (towns.size() > 1 && alive.size() == 1) {
                        winner = alive.front();
                        over = true;
                    }
                    break;
                case Victory::Score:
                    if (g_.tick_ >= static_cast<std::uint64_t>(rules.score_years) * g_.year_ticks()) {
                        std::int32_t best = INT32_MIN;
                        for (const std::uint8_t p : alive) {
                            const std::int32_t sc = g_.score(p);
                            if (sc > best) {
                                best = sc;
                                winner = p;
                            }
                        }
                        over = true;
                    }
                    break;
                case Victory::None:
                case Victory::Count: break;
            }
        }
        if (!over) {
            return;
        }
        g_.game_over_ = true;
        for (const std::uint8_t p : alive) {
            g_.players_[p].outcome = static_cast<std::int32_t>(p) == winner ? Outcome::Won : Outcome::Lost;
        }
        g_.events_.push_back({Game::Event::Kind::GameOver, 0, {}, {}, static_cast<std::uint16_t>(winner + 1), 0});
    }

    // Chasing and biting (or hitting) a villager.
    void fight_villager(Creature& a, EntityId self) {
        Villager* v = g_.villagers_.get(a.target);
        if (v == nullptr) {
            if (a.kind == CreatureKind::Raider) {
                resume_raid(a);
            } else {
                a.state = CreatureState::Wander;
                a.goal = a.home;
            }
            return;
        }
        if (distance2(a.position, v->position) > meters2(1) + (meters2(1) >> 1)) {
            (void)step_toward(a, v->position, speed_of(a));
            return;
        }
        if (++a.timer % 10 != 0) {
            return;
        }
        hurt(*v, a.target, damage_of(a), a.kind, self);
        if (a.kind == CreatureKind::Boar && v->health > 0) {
            a.state = CreatureState::Wander;  // Enough: back to the herd.
            a.target = {};
            a.goal = a.home;
            return;
        }
        if (v->health <= 0) {
            kill(a.target);
            build_grid();  // The villagers moved in their store.
            a.target = {};
            if (a.kind == CreatureKind::Raider) {
                resume_raid(a);
            } else {
                a.state = CreatureState::Wander;
                a.goal = a.home;
            }
        }
    }

    // Towers shoot; traps bite.
    void defend() {
        auto& list = g_.buildings_;
        auto& cs = g_.creatures_;
        for (std::size_t i = 0; i < list.size(); ++i) {
            Building& b = list.data()[i];
            const BuildingDef& d = def(b);
            if (!complete(b) || d.attack_damage <= 0) {
                continue;
            }
            if (d.trap) {
                if (b.rearm > 0) {
                    --b.rearm;
                    continue;
                }
                for (std::size_t k = 0; k < cs.size(); ++k) {
                    Creature& a = cs.data()[k];
                    const std::int32_t ax = a.position.x.floor_int();
                    const std::int32_t az = a.position.z.floor_int();
                    const bool foe = a.kind == CreatureKind::Soldier ? g_.enemies(a.town, b.owner)
                                     : a.kind == CreatureKind::Raider  ? a.town == b.owner
                                                                       : Game::hostile(a.kind);
                    if (foe && a.state != CreatureState::Travel && ax >= b.x && ax < b.x + b.width && az >= b.z &&
                        az < b.z + b.depth) {
                        a.health -= d.attack_damage;
                        b.rearm = 300;
                        break;
                    }
                }
                continue;
            }
            if (d.attack_range <= 0 || (g_.tick_ + i) % static_cast<std::uint64_t>(d.attack_every) != 0) {
                continue;
            }
            Creature* aim = nullptr;
            std::uint64_t aim_d = meters2(d.attack_range);
            const FixedVec2 c = center_of(b);
            for (Creature& a : cs.data()) {
                const bool enemy = a.kind == CreatureKind::Raider    ? a.town == b.owner
                                   : a.kind == CreatureKind::Soldier ? g_.enemies(a.town, b.owner) &&
                                                                           a.state != CreatureState::Travel
                                                                     : Game::hostile(a.kind);
                if (enemy && distance2(a.position, c) < aim_d) {
                    aim_d = distance2(a.position, c);
                    aim = &a;
                }
            }
            if (aim != nullptr) {
                aim->health -= d.attack_damage;
            }
        }
    }

    // Once a day: raids are planned and come.
    void daily_raids() {
        const std::int32_t scale = threat_percent(g_.rules_.raiders);
        if (scale == 0) {
            return;
        }
        const auto interval = static_cast<std::uint64_t>(kTicksPerYear) * 100u / static_cast<std::uint64_t>(scale);
        for (std::uint8_t p = 0; p < g_.player_count_; ++p) {
            PlayerState& ps = g_.players_[p];
            if (g_.town_of(p) != p || !ps.active || !ps.town_center.valid()) {
                continue;
            }
            if (ps.next_raid == 0) {
                ps.next_raid = g_.tick_ + interval + kTicksPerYear;  // A year of grace (of the usual length).
            } else if (g_.tick_ >= ps.next_raid) {
                ps.next_raid = g_.tick_ + interval * 3 / 4 + g_.rng_.below(static_cast<std::uint32_t>(interval / 2 + 1));
                start_raid(p, scale);
            }
        }
    }

    // A shore on the same land as `goal`, from where it can be reached:
    // along a few directions from the goal to where the land meets the
    // water, at least 40 m away. `path` gets the way there (for raiders).
    bool coast_landing(FixedVec2 goal, FixedVec2& out, std::vector<FixedVec2>* path) {
        constexpr int kDirections = 16;
        const Angle first = g_.rng_.angle();
        for (int d = 0; d < kDirections; ++d) {
            const Angle a{static_cast<std::uint16_t>(first.units + d * (65536 / kDirections))};
            const Fixed dx = cos(a);
            const Fixed dz = sin(a);
            FixedVec2 last = goal;
            bool shore = false;
            for (std::int32_t r = 4; r <= 3000; r += 4) {
                const FixedVec2 p{goal.x + dx * Fixed::from_int(r), goal.z + dz * Fixed::from_int(r)};
                const std::int32_t cx = p.x.floor_int();
                const std::int32_t cz = p.z.floor_int();
                if (cx < 0 || cz < 0 || cx >= g_.map_.size || cz >= g_.map_.size) {
                    break;
                }
                if (!g_.nav_.ground(cx / NavGrid::kCellMeters, cz / NavGrid::kCellMeters)) {
                    shore = g_.map_.water_at(cx, cz) && r >= 40;
                    break;
                }
                last = p;
            }
            std::vector<FixedVec2> way;
            if (shore && g_.nav_.find_path_through(last, goal, path != nullptr ? *path : way)) {
                out = last;
                return true;
            }
        }
        return false;
    }

    void start_raid(std::uint8_t town, std::int32_t scale) {
        const EntityId target = raid_target(town, g_.door(*g_.buildings_.get(g_.players_[town].town_center)));
        const Building* tb = g_.buildings_.get(target);
        if (tb == nullptr) {
            return;
        }
        // How rich the town is.
        std::int64_t wealth = 0;
        const std::vector<std::int32_t> stored = g_.stored(town);
        for (std::size_t r = 0; r < stored.size(); ++r) {
            wealth += static_cast<std::int64_t>(stored[r]) * std::max(1, c_.resources[r].value);
        }
        const std::int64_t base = 2 + wealth / 400 + g_.population(town) / 15;
        const auto count = static_cast<std::int32_t>(std::clamp<std::int64_t>(base * scale / 100, 2, 40));
        // From the edge of the town's map.
        const Game::Region region = g_.region(town);
        std::vector<FixedVec2> path;
        FixedVec2 from;
        bool found = false;
        for (int attempt = 0; attempt < 8 && !found; ++attempt) {
            const std::int32_t along = static_cast<std::int32_t>(g_.rng_.below(static_cast<std::uint32_t>(region.size - 16))) + 8;
            const std::int32_t side = static_cast<std::int32_t>(g_.rng_.below(4));
            const std::int32_t x = side == 0 ? 6 : side == 1 ? region.size - 7 : along;
            const std::int32_t z = side == 2 ? 6 : side == 3 ? region.size - 7 : along;
            from = {Fixed::from_int(region.x + x), Fixed::from_int(region.z + z)};
            found = g_.nav_.ground(from.x.floor_int() / NavGrid::kCellMeters, from.z.floor_int() / NavGrid::kCellMeters) &&
                    g_.nav_.find_path_through(from, g_.door(*tb), path);
        }
        // Islands (phase 22): no way in from the edge; they land on the coast.
        if (!found) {
            found = coast_landing(g_.door(*tb), from, &path);
        }
        if (!found) {
            return;
        }
        for (std::int32_t n = 0; n < count; ++n) {
            Creature a;
            a.kind = CreatureKind::Raider;
            a.state = CreatureState::Approach;
            a.town = town;
            a.zone = 0xFFFF;
            a.home = from;
            a.position = {from.x + Fixed::from_ratio(static_cast<std::int32_t>(g_.rng_.below(5)) - 2, 1),
                          from.z + Fixed::from_ratio(static_cast<std::int32_t>(g_.rng_.below(5)) - 2, 1)};
            a.previous = a.position;
            a.path = path;
            a.health = stats(a.kind).health;
            a.target = target;
            a.timer = static_cast<std::int32_t>(g_.rng_.below(10));
            g_.creatures_.add(g_.registry_.create(), a);
        }
        ++g_.players_[town].raids;
        g_.events_.push_back({Game::Event::Kind::RaidStarted, town, target, from, static_cast<std::uint16_t>(count), 0});
    }

    // The militia: adults go for the nearest enemy near the town.
    bool start_fight(Villager& v) {
        const Building* tc = g_.buildings_.get(g_.players_[v.owner].town_center);
        if (tc == nullptr) {
            return false;
        }
        const FixedVec2 at = center_of(*tc);
        EntityId best;
        std::uint64_t best_d = meters2(160);
        const auto& cs = g_.creatures_;
        for (std::size_t i = 0; i < cs.size(); ++i) {
            const Creature& a = cs.data()[i];
            const bool enemy = a.kind == CreatureKind::Raider    ? a.town == v.owner && a.state != CreatureState::Leave
                               : a.kind == CreatureKind::Soldier ? g_.enemies(a.town, v.owner) &&
                                                                       a.state != CreatureState::Travel
                                                                 : Game::hostile(a.kind);
            if (!enemy || distance2(a.position, at) > meters2(160)) {
                continue;
            }
            const std::uint64_t d = distance2(a.position, v.position);
            if (d < best_d) {
                best_d = d;
                best = cs.entities()[i];
            }
        }
        if (!best.valid()) {
            return false;
        }
        v.task = Task::GoFight;
        v.target = best;
        if (!walk_to(v, g_.creatures_.get(best)->position)) {
            fail(v);
        }
        return true;
    }

    void fight(Villager& v) {
        Creature* a = g_.creatures_.get(v.target);
        if (a == nullptr || a->health <= 0) {
            v.task = Task::Idle;
            return;
        }
        if (distance2(a->position, v.position) > meters2(3)) {
            v.task = Task::GoFight;
            if (!walk_to(v, a->position)) {
                fail(v);
            }
            return;
        }
        if (++v.timer % 10 == 0) {
            a->health -= 35;
            // An animal that is hit turns on its attacker.
            if (a->kind != CreatureKind::Raider && a->kind != CreatureKind::Deer && a->state != CreatureState::Chase) {
                a->state = CreatureState::Chase;
                a->target = {};
                for (std::size_t k = 0; k < g_.villagers_.size(); ++k) {
                    if (&g_.villagers_.data()[k] == &v) {
                        a->target = g_.villagers_.entities()[k];
                    }
                }
            }
        }
    }

    // --- Trade (phase 14) ----------------------------------------------------------------

    // The town's trading post, if it has a finished one.
    [[nodiscard]] Building* trading_post(std::uint8_t town) {
        for (Building& b : g_.buildings_.data()) {
            if (b.owner == town && def(b).trade && complete(b)) {
                return &b;
            }
        }
        return nullptr;
    }

    // Takes goods (gold too) from a town: the trading post first, then its
    // other storages. False, and nothing taken, if it has not enough.
    bool take_from_town(std::uint8_t town, DefIndex r, std::int32_t n) {
        if (r >= c_.resources.size() || g_.tradeable(town, r) < n) {
            return false;
        }
        std::vector<Building*> order;
        if (Building* post = trading_post(town)) {
            order.push_back(post);
        }
        for (Building& b : g_.buildings_.data()) {
            if (b.owner == town && complete(b) && def(b).storage > 0 && !def(b).trade && gives_out(c_, b, r)) {
                order.push_back(&b);
            }
        }
        for (Building* b : order) {
            const std::int32_t take = std::min(n, amount_of(b->stock, r));
            if (take > 0) {
                add_to(b->stock, r, -take);
                compact(b->stock);
                n -= take;
            }
            if (n == 0) {
                break;
            }
        }
        return true;
    }

    // Gives goods to a town: into its trading post while there is room,
    // the rest to the town center (which may overflow).
    void give_to_town(std::uint8_t town, DefIndex r, std::int32_t n) {
        if (Building* post = trading_post(town)) {
            const std::int32_t put = std::min(n, free_space(*post));
            if (put > 0) {
                add_to(post->stock, r, put);
                n -= put;
            }
        }
        if (n > 0) {
            if (Building* tc = g_.buildings_.get(g_.players_[town].town_center)) {
                add_to(tc->stock, r, n);
            }
        }
    }

    // Once a day: merchants come and go, caravans arrive, offers expire.
    void daily_trade() {
        for (std::uint8_t p = 0; p < g_.player_count_; ++p) {
            if (g_.town_of(p) != p || !g_.players_[p].active) {
                continue;
            }
            PlayerState& ps = g_.players_[p];
            if (ps.merchant_leaves != 0 && g_.tick_ >= ps.merchant_leaves) {
                ps.merchant_leaves = 0;
                ps.merchant.clear();
                g_.events_.push_back({Game::Event::Kind::MerchantLeft, p, {}, {}, 0, 0});
                if (ps.tally != TradeTally{}) {
                    Game::Event e{Game::Event::Kind::AutoTrade, p, {}, {}, 0, 0};
                    e.tally = ps.tally;
                    g_.events_.push_back(e);
                }
                ps.tally = {};
            }
            if (ps.merchant_arrives == 0) {
                // The first one comes a month after there is a trading post.
                if (trading_post(p) != nullptr) {
                    ps.merchant_arrives = g_.tick_ + g_.month_ticks();
                }
            } else if (g_.tick_ >= ps.merchant_arrives) {
                ps.merchant_arrives = g_.tick_ + 2 * g_.month_ticks() + g_.rng_.below(static_cast<std::uint32_t>(g_.month_ticks()));
                if (Building* post = trading_post(p)) {
                    merchant_arrives(p, *post);
                } else {
                    ps.merchant_arrives = 0;
                }
            }
            if (g_.merchant_here(p)) {
                auto_trade(p);
            }
        }
        // Caravans that got there.
        for (std::size_t i = 0; i < g_.caravans_.size();) {
            const Caravan c = g_.caravans_[i];
            if (g_.tick_ < c.arrives) {
                ++i;
                continue;
            }
            g_.caravans_.erase(g_.caravans_.begin() + static_cast<std::ptrdiff_t>(i));
            give_to_town(c.to, c.resource, c.amount);
            g_.events_.push_back({Game::Event::Kind::CaravanArrived, c.to, {}, {}, c.resource, c.from});
        }
        // Offers nobody answered: the goods go back.
        for (std::size_t i = 0; i < g_.offers_.size();) {
            const TradeOffer o = g_.offers_[i];
            if (g_.tick_ < o.expires) {
                ++i;
                continue;
            }
            g_.offers_.erase(g_.offers_.begin() + static_cast<std::ptrdiff_t>(i));
            give_to_town(o.from, o.give, o.give_amount);
            g_.events_.push_back({Game::Event::Kind::OfferAnswered, o.from, {}, {}, 0, o.to});
        }
    }

    // Once a day while a merchant is here: the town's rules, sales first
    // (their gold goes into the post), then purchases with the post's gold
    // only; the vaults' gold stays out of it (phase 29).
    void auto_trade(std::uint8_t p) {
        PlayerState& ps = g_.players_[p];
        Building* post = trading_post(p);
        if (post == nullptr || ps.trade_rules.empty() || g_.gold_ == kNoDef) {
            return;
        }
        const auto good_of = [&](DefIndex r) -> MerchantGood* {
            for (MerchantGood& m : ps.merchant) {
                if (m.resource == r) {
                    return &m;
                }
            }
            return nullptr;
        };
        for (const TradeRule& rule : ps.trade_rules) {
            const MerchantGood* good = good_of(rule.resource);
            if (rule.sell_above == kNoRule || good == nullptr || good->sell <= 0) {
                continue;
            }
            // Only to a merchant who pays well enough (phase 60).
            // His price of the day, as a percent of the good's value: he pays
            // three quarters of it and charges five quarters (merchant_arrives).
            if (rule.sell_min != 0 && good->sell * 400 < c_.resources[rule.resource].value * 3 * rule.sell_min) {
                continue;
            }
            const std::int32_t n = std::min(kMaxTrade, g_.tradeable(p, rule.resource) - rule.sell_above);
            if (n > 0 && take_from_town(p, rule.resource, n)) {
                give_to_town(p, g_.gold_, n * good->sell);
                ps.tally.sold += n;
                ps.tally.sold_gold += n * good->sell;
            }
        }
        for (const TradeRule& rule : ps.trade_rules) {
            MerchantGood* good = good_of(rule.resource);
            if (rule.buy_below == kNoRule || good == nullptr || good->stock <= 0) {
                continue;
            }
            // Only from a merchant who is not too dear.
            if (rule.buy_max != 0 && good->buy * 400 - 399 > c_.resources[rule.resource].value * 5 * rule.buy_max) {
                continue;
            }
            const std::int32_t budget = amount_of(post->stock, g_.gold_);
            const std::int32_t n = std::min({rule.buy_below - g_.tradeable(p, rule.resource), good->stock, budget / good->buy});
            if (n <= 0) {
                continue;
            }
            add_to(post->stock, g_.gold_, -n * good->buy);
            compact(post->stock);
            good->stock -= n;
            give_to_town(p, rule.resource, n);
            ps.tally.bought += n;
            ps.tally.bought_gold += n * good->buy;
        }
    }

    void set_trade_rule(const Command& c) {
        PlayerState& ps = g_.players_[g_.town_of(c.player)];
        if (c.def >= c_.resources.size() || c_.resources[c.def].value <= 0) {
            ++g_.rejected_;
            return;
        }
        auto it = std::lower_bound(ps.trade_rules.begin(), ps.trade_rules.end(), c.def,
                                   [](const TradeRule& r, DefIndex d) { return r.resource < d; });
        const bool found = it != ps.trade_rules.end() && it->resource == c.def;
        if (c.value == kNoRule && c.value2 == kNoRule) {
            if (found) {
                ps.trade_rules.erase(it);
            }
            return;
        }
        if (!found) {
            it = ps.trade_rules.insert(it, TradeRule{c.def, kNoRule, kNoRule});
        }
        it->sell_above = c.value;
        it->buy_below = c.value2;
        it->sell_min = c.value == kNoRule ? std::uint8_t{0} : static_cast<std::uint8_t>(c.count);
        it->buy_max = c.value2 == kNoRule ? std::uint8_t{0} : static_cast<std::uint8_t>(c.def2);
    }

    // A merchant with a few goods at prices of the day.
    void merchant_arrives(std::uint8_t p, Building& post) {
        PlayerState& ps = g_.players_[p];
        ps.merchant.clear();
        ps.tally = {};
        ps.merchant_leaves = g_.tick_ + g_.month_ticks();
        std::vector<DefIndex> goods;
        for (std::size_t r = 0; r < c_.resources.size(); ++r) {
            if (c_.resources[r].value > 0) {
                goods.push_back(static_cast<DefIndex>(r));
            }
        }
        // Every tradeable good gets a price; a few of them are for sale.
        const std::uint32_t for_sale = 4 + g_.rng_.below(3);
        for (std::size_t i = 0; i < goods.size(); ++i) {
            const std::int32_t value = c_.resources[goods[i]].value;
            const std::int32_t factor = 75 + static_cast<std::int32_t>(g_.rng_.below(51));  // 75..125 %.
            MerchantGood m;
            m.resource = goods[i];
            m.sell = value * factor * 3 / 400;  // 75 % of the day's price; 0: he does not buy it.
            m.buy = std::max(m.sell + 1, (value * factor * 5 + 399) / 400);  // 125 %.
            ps.merchant.push_back(m);
        }
        for (std::uint32_t k = 0; k < for_sale && !ps.merchant.empty(); ++k) {
            MerchantGood& m = ps.merchant[g_.rng_.below(static_cast<std::uint32_t>(ps.merchant.size()))];
            m.stock += 20 + static_cast<std::int32_t>(g_.rng_.below(41));
        }
        g_.events_.push_back({Game::Event::Kind::MerchantArrived, p, id_of(post), center_of(post), 0, 0});
    }

    [[nodiscard]] EntityId id_of(const Building& b) const {
        const auto& list = g_.buildings_;
        for (std::size_t i = 0; i < list.size(); ++i) {
            if (&list.data()[i] == &b) {
                return list.entities()[i];
            }
        }
        return {};
    }

    void trade_with_merchant(const Command& c) {
        const std::uint8_t town = g_.town_of(c.player);
        Building* post = g_.buildings_.get(c.entity);
        PlayerState& ps = g_.players_[town];
        MerchantGood* good = nullptr;
        for (MerchantGood& m : ps.merchant) {
            good = m.resource == c.def ? &m : good;
        }
        if (post == nullptr || post->owner != town || !def(*post).trade || !complete(*post) || !g_.merchant_here(town) ||
            good == nullptr || g_.gold_ == kNoDef) {
            ++g_.rejected_;
            return;
        }
        if (c.value > 0) {
            // The gold goes first, which makes room in the post.
            const std::int32_t n = c.value;
            if (good->stock < n || !take_from_town(town, g_.gold_, n * good->buy)) {
                ++g_.rejected_;
                return;
            }
            good->stock -= n;
            give_to_town(town, c.def, n);
        } else {
            const std::int32_t n = -c.value;
            if (good->sell == 0 || !take_from_town(town, c.def, n)) {
                ++g_.rejected_;
                return;
            }
            give_to_town(town, g_.gold_, n * good->sell);
        }
    }

    void offer_trade(const Command& c) {
        const std::uint8_t from = g_.town_of(c.player);
        const auto to = static_cast<std::uint8_t>(c.count);  // Checked when read.
        const auto valid = [&](DefIndex r) {
            return r < c_.resources.size() && (c_.resources[r].value > 0 || r == g_.gold_);
        };
        if (to >= g_.player_count_ || !g_.players_[to].active || g_.town_of(to) != to || to == from || !valid(c.def) ||
            !valid(c.def2) || g_.offers_.size() >= 64 || !take_from_town(from, c.def, c.value)) {
            ++g_.rejected_;
            return;
        }
        TradeOffer o;
        o.id = g_.next_offer_++;
        o.from = from;
        o.to = to;
        o.give = c.def;
        o.give_amount = c.value;
        o.want = c.def2;
        o.want_amount = c.value2;
        o.expires = g_.tick_ + g_.month_ticks();
        g_.offers_.push_back(o);
        g_.events_.push_back({Game::Event::Kind::OfferReceived, to, {}, {}, 0, from});
    }

    void answer_offer(const Command& c) {
        const std::uint8_t town = g_.town_of(c.player);
        auto it = std::find_if(g_.offers_.begin(), g_.offers_.end(),
                               [&](const TradeOffer& o) { return o.id == static_cast<std::uint32_t>(c.value); });
        if (it == g_.offers_.end() || (it->to != town && it->from != town) || (c.count == 1 && it->to != town)) {
            ++g_.rejected_;
            return;
        }
        const TradeOffer o = *it;
        if (c.count == 1) {
            if (!take_from_town(o.to, o.want, o.want_amount)) {
                ++g_.rejected_;
                return;
            }
            const std::uint64_t travel = g_.travel_ticks(o.from, o.to);
            g_.caravans_.push_back({o.from, o.to, o.give, o.give_amount, g_.tick_, g_.tick_ + travel});
            g_.caravans_.push_back({o.to, o.from, o.want, o.want_amount, g_.tick_, g_.tick_ + travel});
        } else {
            give_to_town(o.from, o.give, o.give_amount);
        }
        g_.offers_.erase(std::find(g_.offers_.begin(), g_.offers_.end(), o));
        g_.events_.push_back({Game::Event::Kind::OfferAnswered, o.from, {}, {}, static_cast<std::uint16_t>(c.count), o.to});
    }

    // --- Health and fire (phase 13) ---------------------------------------------------

    [[nodiscard]] static FixedVec2 center_of(const Building& b) {
        return {Fixed::from_int(b.x) + Fixed::from_ratio(b.width, 2), Fixed::from_int(b.z) + Fixed::from_ratio(b.depth, 2)};
    }
    [[nodiscard]] static std::uint64_t meters2(std::int64_t m) { return static_cast<std::uint64_t>(m * m) << 32; }

    // A well within 50 m of `b` (to fight its fire).
    [[nodiscard]] bool well_near(const Building& b) const {
        for (const Building& o : g_.buildings_.data()) {
            if (o.owner == b.owner && complete(o) && def(o).service == static_cast<std::uint8_t>(Need::Water) &&
                distance2(center_of(o), center_of(b)) <= meters2(50)) {
                return true;
            }
        }
        return false;
    }

    bool start_firefighting(Villager& v) {
        EntityId best;
        std::uint64_t best_d = meters2(80);
        for (const EntityId id : g_.owned(v.owner)) {
            const Building& b = *g_.buildings_.get(id);
            if (b.fire <= 0) {
                continue;
            }
            const std::uint64_t d = distance2(v.position, center_of(b));
            if (d < best_d && well_near(b)) {
                best_d = d;
                best = id;
            }
        }
        if (!best.valid()) {
            return false;
        }
        go(v, Task::GoFire, best);
        return true;
    }

    void fight_fire(Villager& v) {
        Building* b = g_.buildings_.get(v.target);
        if (b == nullptr || b->fire <= 0) {
            v.task = Task::Idle;
            return;
        }
        if (++v.timer < 10) {
            return;
        }
        v.timer = 0;
        b->fire = std::max(0, b->fire - 2);  // A bucket.
        if (b->fire == 0) {
            --g_.fires_;
            g_.buildings_changed_ = true;
            v.task = Task::Idle;
        }
    }

    void ignite(Building& b, EntityId id) {
        if (b.fire > 0 || def(b).fireproof || b.state != BuildingState::Complete) {
            return;
        }
        b.fire = 10;
        ++g_.fires_;
        g_.buildings_changed_ = true;
        g_.events_.push_back({Game::Event::Kind::FireStarted, b.owner, id, center_of(b), 0});
    }

    // Every tick while something burns: fires grow, spread and destroy.
    void burn() {
        std::vector<EntityId> gone;
        auto& list = g_.buildings_;
        for (std::size_t i = 0; i < list.size(); ++i) {
            Building& b = list.data()[i];
            if (b.fire <= 0) {
                continue;
            }
            if (g_.tick_ % 10 == 0) {
                b.fire = std::min(100, b.fire + 1);
                b.burned = std::min(1000, b.burned + 1 + b.fire / 10);
            }
            if (g_.tick_ % 100 == 0) {
                g_.buildings_changed_ = true;  // The view shows it charring.
            }
            // Sparks reach buildings close by.
            if (g_.tick_ % 50 == 0) {
                for (std::size_t k = 0; k < list.size(); ++k) {
                    Building& o = list.data()[k];
                    if (k == i || o.fire > 0 || def(o).fireproof ||
                        distance2(center_of(o), center_of(b)) > meters2(10 + (b.width + o.width) / 2)) {
                        continue;
                    }
                    if (g_.rng_.below(1000) < static_cast<std::uint32_t>(b.fire)) {
                        ignite(o, list.entities()[k]);
                    }
                }
            }
            if (b.burned >= 1000) {
                gone.push_back(list.entities()[i]);
            }
        }
        for (const EntityId id : gone) {
            Building* b = g_.buildings_.get(id);
            if (b == nullptr) {
                continue;
            }
            --g_.fires_;
            b->fire = 0;
            if (id == g_.players_[b->owner].town_center) {
                b->burned = 900;  // The town center survives, scorched.
                continue;
            }
            ++g_.players_[b->owner].burned_down;
            g_.events_.push_back({Game::Event::Kind::BurnedDown, b->owner, id, center_of(*b), 0});
            remove_building(id, true);
        }
    }

    // Once a day: new fires, with more chances where fires are lit.
    void start_fires() {
        const std::int32_t scale = threat_percent(g_.rules_.fires);
        if (scale == 0 || g_.snow_ > 30) {
            return;
        }
        auto& list = g_.buildings_;
        for (std::size_t i = 0; i < list.size(); ++i) {
            Building& b = list.data()[i];
            if (b.fire > 0 || def(b).fireproof || !complete(b)) {
                continue;
            }
            std::int32_t chance = 4;  // Per 100 000 a day.
            if (def(b).kind == BuildingKind::House && g_.temperature_ < village::kColdBelow && !b.residents.empty()) {
                chance *= 3;  // A hearth burning.
            }
            for (const DefIndex r : def(b).recipes) {
                for (const ResourceAmount& in : c_.recipes[r].inputs) {
                    if (in.resource == g_.firewood_ || c_.resources[in.resource].category == ResourceCategory::Fuel) {
                        chance *= 4;  // An oven or a forge.
                    }
                }
            }
            if (g_.rng_.below(100000) < static_cast<std::uint32_t>(chance * scale / 100)) {
                ignite(b, list.entities()[i]);
            }
        }
    }

    // Once a day: sickness comes, spreads, gets better or kills.
    void update_health() {
        const std::int32_t scale = threat_percent(g_.rules_.diseases);
        const std::size_t kinds = std::min<std::size_t>(c_.diseases.size(), 32);
        // Where the sick are: homes and workplaces, by entity index.
        std::map<std::uint32_t, std::uint32_t> at_home;
        std::map<std::uint32_t, std::uint32_t> at_work;
        for (const Villager& v : g_.villagers_.data()) {
            if (v.disease != 0 && v.disease <= kinds) {
                const std::uint32_t bit = 1u << (v.disease - 1u);
                if (v.home.valid()) {
                    at_home[v.home.index] |= bit;
                }
                if (v.job.valid()) {
                    at_work[v.job.index] |= bit;
                }
            }
        }
        // Food stores big enough to draw rats.
        std::vector<FixedVec2> rat_stores;
        for (const Building& b : g_.buildings_.data()) {
            if (!complete(b) || def(b).storage <= 0) {
                continue;
            }
            std::int32_t food = 0;
            for (const Stock& st : b.stock) {
                food += c_.resources[st.resource].category == ResourceCategory::Food ? st.amount : 0;
            }
            if (food > 150) {
                rat_stores.push_back(center_of(b));
            }
        }
        std::vector<EntityId> dying;
        auto& vs = g_.villagers_;
        for (std::size_t k = 0; k < vs.size(); ++k) {
            Villager& v = vs.data()[k];
            const Building* home = g_.buildings_.get(v.home);
            const auto has = [&](Need n) {
                return home != nullptr && ((home->needs >> static_cast<unsigned>(n)) & 1u) != 0;
            };
            if (v.disease != 0) {
                const DiseaseDef& d = c_.diseases[std::min<std::size_t>(v.disease - 1u, kinds - 1)];
                std::int32_t severity = d.severity;
                std::int32_t recovery = 1;
                if (has(Need::Doctor)) {
                    severity /= 4;
                    recovery = 3;
                } else if (has(Need::Healer)) {
                    severity /= 2;
                    recovery = 2;
                }
                v.health -= severity;
                v.sick_days -= recovery;
                if (v.health <= 0) {
                    dying.push_back(vs.entities()[k]);
                    continue;
                }
                if (v.sick_days <= 0) {
                    v.disease = 0;
                    v.sick_days = 0;
                    v.immune_days = 60;
                }
                continue;
            }
            if (v.immune_days > 0) {
                --v.immune_days;
                continue;
            }
            if (scale == 0) {
                continue;
            }
            const FixedVec2 here = home != nullptr ? center_of(*home) : v.position;
            for (std::size_t d = 0; d < kinds; ++d) {
                const DiseaseDef& def_d = c_.diseases[d];
                std::int32_t chance = 0;  // Per 10 000.
                bool source = false;
                switch (def_d.source) {
                    case DiseaseSource::Cold:
                        source = g_.temperature_ < 5 && (v.clothes == 0 || home == nullptr || !home->heated);
                        break;
                    case DiseaseSource::Water: source = !has(Need::Water); break;
                    case DiseaseSource::Rats:
                        for (const FixedVec2& r : rat_stores) {
                            source = source || distance2(r, here) <= meters2(40);
                        }
                        source = source && !has(Need::Hygiene);
                        break;
                    case DiseaseSource::Count: break;
                }
                if (source) {
                    chance += def_d.chance;
                }
                const std::uint32_t bit = 1u << d;
                if (v.home.valid() && (at_home[v.home.index] & bit) != 0) {
                    chance += def_d.contagion * 10;
                }
                if (v.job.valid() && (at_work[v.job.index] & bit) != 0) {
                    chance += def_d.contagion * 5;
                }
                chance = chance * scale / 100;
                if (const RaceDef* r = race_of(v)) {
                    const std::int32_t resist = r->disease + (def_d.source == DiseaseSource::Cold ? r->cold : 0);
                    chance = chance * std::max(0, 100 - resist) / 100;
                }
                if (has(Need::Hygiene)) {
                    chance /= 2;
                }
                if (chance > 0 && g_.rng_.below(10000) < static_cast<std::uint32_t>(chance)) {
                    // The first case of a disease in the town is news.
                    bool first = true;
                    for (const Villager& o : vs.data()) {
                        first = first && !(o.owner == v.owner && o.disease == d + 1);
                    }
                    v.disease = static_cast<std::uint8_t>(d + 1);
                    v.sick_days = def_d.days;
                    if (first) {
                        g_.events_.push_back({Game::Event::Kind::Outbreak, v.owner, vs.entities()[k], v.position,
                                              static_cast<std::uint16_t>(d)});
                    }
                    break;
                }
            }
        }
        for (const EntityId id : dying) {
            kill(id);
        }
    }

    // --- Markets and services (phase 12) ------------------------------------------

    // Brings `res` from a storage to the worker's job.
    bool fetch_to_job(Villager& v, DefIndex res, bool skip_markets) {
        const EntityId from = storage_with(v.owner, v.position, res, skip_markets);
        if (!from.valid() || from == v.job) {
            return false;
        }
        v.site = v.job;
        v.carrying = {res, 0};
        v.timer = 0;
        go(v, Task::GoFetch, from);
        return true;
    }

    // A market keeps a little of every food and good the homes want.
    bool start_restocking(Villager& v, const Building& market) {
        if (free_space(market) <= 0) {
            return false;
        }
        for (std::size_t r = 0; r < c_.resources.size(); ++r) {
            const ResourceDef& rd = c_.resources[r];
            const auto res = static_cast<DefIndex>(r);
            const bool wanted = (rd.category == ResourceCategory::Food && rd.nutrition > 0) || res == g_.clothes_ ||
                                res == g_.shoes_;
            if (wanted && amount_of(market.stock, res) < 12 && fetch_to_job(v, res, true)) {
                return true;
            }
        }
        return false;
    }

    // A tavern keeps its beer (whatever its service uses).
    bool start_supplying(Villager& v, const Building& place) {
        for (const ResourceAmount& use : def(place).service_uses) {
            if (amount_of(place.stock, use.resource) < 10 && fetch_to_job(v, use.resource, false)) {
                return true;
            }
        }
        return false;
    }

    // --- Farming (phase 11) -----------------------------------------------------

    [[nodiscard]] bool can_sow(const Field& f) const {
        const Season season = g_.calendar().season;
        return f.state == FieldState::Waiting && f.plan[f.slot] != kNoDef && g_.temperature_ >= 6 &&
               season != Season::Winter;
    }

    [[nodiscard]] bool wants_compost(const Field& f) const {
        return can_sow(f) && f.work == 0 && f.fertility < 85 && f.fertilized < 10;
    }

    void go_field(Villager& v, EntityId farm, std::size_t index) {
        const Field& f = g_.buildings_.get(farm)->fields[index];
        v.task = Task::GoField;
        v.target = farm;
        v.spot = static_cast<std::uint16_t>(index + 1);
        const FixedVec2 to{Fixed::from_int(f.x) + Fixed::from_ratio(1 + 2 * g_.rng_.range(0, f.w - 1), 2),
                           Fixed::from_int(f.z) + Fixed::from_ratio(1 + 2 * g_.rng_.range(0, f.d - 1), 2)};
        if (!walk_to(v, to)) {
            fail(v);
        }
    }

    bool start_farming(Villager& v, Building& farm) {
        // Harvest first, then compost and sowing.
        for (std::size_t i = 0; i < farm.fields.size(); ++i) {
            if (farm.fields[i].state == FieldState::Ripe && farm.fields[i].pending > 0) {
                go_field(v, v.job, i);
                return true;
            }
        }
        for (std::size_t i = 0; i < farm.fields.size(); ++i) {
            const Field& f = farm.fields[i];
            if (!can_sow(f)) {
                continue;
            }
            if (wants_compost(f) && g_.fertilizer_ != kNoDef && amount_of(farm.stock, g_.fertilizer_) == 0) {
                // Compost from the storage to the farm, if there is any.
                const EntityId from = storage_with(v.owner, v.position, g_.fertilizer_);
                if (from.valid()) {
                    v.site = v.job;
                    v.carrying = {g_.fertilizer_, 0};
                    v.timer = 0;
                    go(v, Task::GoFetch, from);
                    return true;
                }
            }
            go_field(v, v.job, i);
            return true;
        }
        return false;
    }

    void farm_work(Villager& v) {
        Building* farm = g_.buildings_.get(v.target);
        if (farm == nullptr || v.spot == 0 || v.spot > farm->fields.size()) {
            v.task = Task::Idle;
            return;
        }
        Field& f = farm->fields[v.spot - 1u];
        if (f.state == FieldState::Ripe) {
            // One unit at a time into the basket.
            if ((v.timer += steps(v, Skill::Farm)) < 20) {
                return;
            }
            v.timer = 0;
            const DefIndex res = f.crop < c_.crops.size() ? c_.crops[f.crop].resource : kNoDef;
            if (res == kNoDef || f.pending <= 0) {
                v.task = Task::Idle;
                return;
            }
            v.carrying.resource = res;
            ++v.carrying.amount;
            --f.pending;
            if (f.pending <= 0) {
                f.state = FieldState::Done;
                f.fertility = std::clamp(f.fertility + c_.crops[f.crop].fertility, 0, 100);
                g_.buildings_changed_ = true;
            }
            if (f.pending <= 0 || v.carrying.amount >= carry_capacity(c_, res)) {
                v.task = Task::Idle;  // To the farm with it.
            }
            return;
        }
        if (!can_sow(f)) {
            v.task = Task::Idle;
            return;
        }
        if (wants_compost(f) && g_.fertilizer_ != kNoDef && amount_of(farm->stock, g_.fertilizer_) > 0) {
            if ((v.timer += steps(v, Skill::Farm)) < 40) {
                return;
            }
            v.timer = 0;
            add_to(farm->stock, g_.fertilizer_, -1);
            compact(farm->stock);
            f.fertility = std::min(100, f.fertility + 3);
            ++f.fertilized;
            return;
        }
        // Sowing: two worker-ticks a cell.
        if (++f.work >= f.w * f.d * 2) {
            f.state = FieldState::Growing;
            f.crop = f.plan[f.slot];
            f.growth = 0;
            f.work = 0;
            g_.buildings_changed_ = true;
            v.task = Task::Idle;
        }
    }

    // Once a day: a new year's plans, growth, frost and ripening.
    void grow_fields() {
        const Calendar cal = g_.calendar();
        const std::int32_t t = g_.temperature_;
        for (Building& b : g_.buildings_.data()) {
            for (Field& f : b.fields) {
                if (f.year != cal.year) {
                    if (f.year != 0) {
                        f.slot = static_cast<std::uint8_t>((f.slot + 1) % kPlanYears);
                    }
                    f.year = cal.year;
                    f.state = FieldState::Waiting;
                    f.crop = kNoDef;
                    f.work = f.growth = f.pending = f.fertilized = 0;
                    if (f.plan[f.slot] == kNoDef) {
                        f.state = FieldState::Done;  // A fallow year rests the soil.
                        f.fertility = std::min(100, f.fertility + 15);
                    }
                    g_.buildings_changed_ = true;
                }
                if (f.state != FieldState::Growing || f.crop >= c_.crops.size()) {
                    continue;
                }
                const CropDef& crop = c_.crops[f.crop];
                if (t <= 0 && !crop.hardy) {
                    f.state = FieldState::Done;  // Frost killed it.
                    f.growth = 0;
                    g_.buildings_changed_ = true;
                    continue;
                }
                if (t >= 5) {
                    f.growth += 1000 * (50 + f.fertility) / (150 * std::max(1, crop.grow_days));
                }
                if (f.growth >= 1000) {
                    f.growth = 1000;
                    f.state = FieldState::Ripe;
                    f.pending = g_.per_year(std::max(1, f.w * f.d * crop.yield * f.fertility / 1000));
                    g_.buildings_changed_ = true;
                }
            }
        }
    }

    // --- Hunting and fishing (phase 11) ---------------------------------------------

    static std::int32_t zone_capacity(ZoneType t, const GameRules& rules) {
        const bool predators = rules.wildlife != Threat::None;
        switch (t) {
            case ZoneType::Deer: return 16;
            case ZoneType::Boar: return 10;
            case ZoneType::Wolves: return predators ? 5 : 0;
            case ZoneType::Bears: return predators ? 2 : 0;
            case ZoneType::Count: break;
        }
        return 0;
    }

    bool start_hunting(Villager& v, const Building& lodge) {
        const FixedVec2 door = g_.door(lodge);
        const std::int32_t reach = def(lodge).work_radius;
        std::optional<std::size_t> best;
        std::uint64_t best_d = UINT64_MAX;
        for (std::size_t z = 0; z < g_.map_.zones.size(); ++z) {
            const Zone& zone = g_.map_.zones[z];
            if (g_.zone_animals_[z] <= 0 || (zone.type != ZoneType::Deer && zone.type != ZoneType::Boar)) {
                continue;  // Hunters go for deer and boar.
            }
            const FixedVec2 c{zone.x, zone.z};
            const std::uint64_t d = distance2(c, door);
            const std::int64_t r = static_cast<std::int64_t>(reach) + zone.radius.floor_int();
            if (d > static_cast<std::uint64_t>(r * r) * (1ull << 32) || d >= best_d || !g_.nav_.connected(door, c)) {
                continue;
            }
            best_d = d;
            best = z;
        }
        if (!best) {
            return false;
        }
        const Zone& zone = g_.map_.zones[*best];
        const std::int32_t spread = std::max(2, zone.radius.floor_int() / 2);
        const FixedVec2 to{zone.x + Fixed::from_int(g_.rng_.range(-spread, spread)),
                           zone.z + Fixed::from_int(g_.rng_.range(-spread, spread))};
        v.task = Task::GoHunt;
        v.spot = static_cast<std::uint16_t>(*best + 1);
        if (!walk_to(v, to)) {
            fail(v);
        }
        return true;
    }

    void hunt_work(Villager& v) {
        if ((v.timer += steps(v, Skill::Hunt)) < 120) {
            return;
        }
        v.timer = 0;
        v.task = Task::Idle;
        const std::size_t z = v.spot - 1u;
        if (v.spot == 0 || z >= g_.zone_animals_.size() || g_.zone_animals_[z] <= 0 || g_.meat_ == kNoDef) {
            return;
        }
        // The hunted animal: the nearest one of the zone.
        EntityId prey;
        std::uint64_t prey_d = UINT64_MAX;
        const auto& cs = g_.creatures_;
        for (std::size_t i = 0; i < cs.size(); ++i) {
            const Creature& a = cs.data()[i];
            if (a.kind != CreatureKind::Raider && a.zone == z && distance2(a.position, v.position) < prey_d) {
                prey_d = distance2(a.position, v.position);
                prey = cs.entities()[i];
            }
        }
        if (prey.valid()) {
            remove_creature(prey);
        } else {
            --g_.zone_animals_[z];
        }
        v.carrying = {g_.meat_, carry_capacity(c_, g_.meat_)};
        if (Building* lodge = g_.buildings_.get(v.job); lodge != nullptr && g_.hide_ != kNoDef) {
            add_to(lodge->stock, g_.hide_, 1);  // The hide stays at the lodge.
        }
    }

    bool start_fishing(Villager& v, const Building& hut) {
        if (g_.temperature_ <= -3 || g_.fish_ == kNoDef) {
            return false;  // Frozen over.
        }
        // The nearest water within reach.
        const std::int32_t reach = def(hut).work_radius;
        const std::int32_t cx = hut.x + hut.width / 2;
        const std::int32_t cz = hut.z + hut.depth / 2;
        std::optional<std::pair<std::int32_t, std::int32_t>> best;
        std::int64_t best_d = INT64_MAX;
        for (std::int32_t z = std::max(0, cz - reach); z < std::min(g_.map_.size, cz + reach); z += 2) {
            for (std::int32_t x = std::max(0, cx - reach); x < std::min(g_.map_.size, cx + reach); x += 2) {
                const std::int64_t d = static_cast<std::int64_t>(x - cx) * (x - cx) + static_cast<std::int64_t>(z - cz) * (z - cz);
                if (d < best_d && d <= static_cast<std::int64_t>(reach) * reach && g_.map_.water_at(x, z)) {
                    best_d = d;
                    best = std::pair{x, z};
                }
            }
        }
        if (!best) {
            return false;
        }
        v.task = Task::GoFish;
        if (!walk_to(v, {Fixed::from_int(best->first), Fixed::from_int(best->second)})) {
            fail(v);
        }
        return true;
    }

    void fish_work(Villager& v) {
        if (g_.temperature_ <= -3) {
            v.task = Task::Idle;
            return;
        }
        if ((v.timer += steps(v, Skill::Fish)) < 45) {
            return;
        }
        v.timer = 0;
        v.carrying.resource = g_.fish_;
        ++v.carrying.amount;
        if (v.carrying.amount >= 8) {
            v.task = Task::Idle;
        }
    }

    bool start_producing(Villager& v, Building& job) {
        const BuildingDef& d = def(job);
        if (d.recipes.empty()) {
            return false;
        }
        // Seasons, years to mature and a yearly limit (orchards).
        const Calendar cal = g_.calendar();
        if (d.seasons != 0 && ((d.seasons >> static_cast<unsigned>(cal.season)) & 1u) == 0) {
            return false;
        }
        if (d.mature_years > 0 &&
            static_cast<std::int64_t>(g_.tick_) - job.built_tick < static_cast<std::int64_t>(d.mature_years) * g_.year_ticks()) {
            return false;
        }
        if (d.yearly_limit > 0) {
            if (job.produced_year != cal.year) {
                job.produced_year = cal.year;
                job.produced = 0;
            }
            if (job.produced >= g_.per_year(d.yearly_limit)) {
                return false;
            }
        }
        // The first recipe whose product is short: with its inputs here,
        // work; otherwise fetch what is missing for the first one possible.
        const std::int32_t target = job.limit > 0 ? job.limit : 30 + 3 * g_.population(v.owner);
        const std::vector<std::int32_t> totals = g_.stored(v.owner);
        for (std::size_t k = 0; k < d.recipes.size(); ++k) {
            const RecipeDef& recipe = c_.recipes[d.recipes[k]];
            if (!recipe.outputs.empty() && totals[recipe.outputs.front().resource] >= target) {
                continue;  // Enough in store: the inputs are kept for other uses.
            }
            bool ready = true;
            for (const ResourceAmount& in : recipe.inputs) {
                ready = ready && amount_of(job.stock, in.resource) >= in.amount;
            }
            if (ready) {
                job.recipe = static_cast<std::uint8_t>(k);
                go(v, Task::GoWorkplace, v.job);
                return true;
            }
        }
        for (std::size_t k = 0; k < d.recipes.size(); ++k) {
            const RecipeDef& recipe = c_.recipes[d.recipes[k]];
            if (!recipe.outputs.empty() && totals[recipe.outputs.front().resource] >= target) {
                continue;
            }
            for (const ResourceAmount& in : recipe.inputs) {
                if (amount_of(job.stock, in.resource) < in.amount && fetch_to_job(v, in.resource, true)) {
                    return true;
                }
            }
        }
        return false;
    }

    bool start_construction(Villager& v) {
        // Sites by distance; materials first, then work.
        EntityId best_fetch_site;
        EntityId best_fetch_from;
        DefIndex best_res = kNoDef;
        std::uint64_t best_fetch_d = UINT64_MAX;
        EntityId best_build;
        std::uint64_t best_build_d = UINT64_MAX;
        for (const EntityId id : g_.owned(v.owner)) {
            const Building& b = *g_.buildings_.get(id);
            if (!is_site(b)) {
                continue;
            }
            const std::uint64_t d = distance2(v.position, g_.door(b));
            bool all_there = true;
            for (const ResourceAmount& cost : site_cost(b)) {
                const std::int32_t missing = cost.amount - amount_of(b.delivered, cost.resource);
                if (missing <= 0) {
                    continue;
                }
                all_there = false;
                if (missing - amount_of(b.incoming, cost.resource) <= 0 || d >= best_fetch_d) {
                    continue;
                }
                const EntityId from = storage_with(v.owner, v.position, cost.resource);
                if (from.valid()) {
                    best_fetch_d = d;
                    best_fetch_site = id;
                    best_fetch_from = from;
                    best_res = cost.resource;
                }
            }
            if (all_there && b.work_done < site_work(b) && d < best_build_d) {
                best_build_d = d;
                best_build = id;
            }
        }
        if (best_fetch_site.valid()) {
            Building& site = *g_.buildings_.get(best_fetch_site);
            const Building& from = *g_.buildings_.get(best_fetch_from);
            std::int32_t missing = 0;
            for (const ResourceAmount& cost : site_cost(site)) {
                if (cost.resource == best_res) {
                    missing = cost.amount - amount_of(site.delivered, best_res) - amount_of(site.incoming, best_res);
                }
            }
            const std::int32_t take = std::min({missing, carry_capacity(c_, best_res), amount_of(from.stock, best_res)});
            if (take > 0) {
                add_to(site.incoming, best_res, take);
                v.site = best_fetch_site;
                v.carrying = {best_res, 0};  // What is fetched, before it is in hand.
                v.timer = take;              // How much was promised to the site.
                go(v, Task::GoFetch, best_fetch_from);
                return true;
            }
        }
        if (best_build.valid()) {
            go(v, Task::GoBuild, best_build);
            return true;
        }
        return false;
    }

    // --- Arrivals and work ----------------------------------------------------

    void arrive(Villager& v) {
        switch (v.task) {
            case Task::Wander:
                v.task = Task::Idle;
                break;
            case Task::GoEat: eat(v); break;
            case Task::GoDeliver: deliver(v); break;
            case Task::GoGather:
                v.task = Task::Gather;
                v.timer = 0;
                break;
            case Task::GoFetch: fetch(v); break;
            case Task::GoSite: deliver_to_site(v); break;
            case Task::GoBuild:
                v.task = Task::Build;
                break;
            case Task::GoWorkplace: at_workplace(v); break;
            case Task::GoField:
                v.task = Task::Farm;
                v.timer = 0;
                break;
            case Task::GoHunt:
                v.task = Task::Hunt;
                v.timer = 0;
                break;
            case Task::GoFish:
                v.task = Task::Fish;
                v.timer = 0;
                v.carrying = {};
                break;
            case Task::GoFire:
                v.task = Task::FightFire;
                v.timer = 0;
                break;
            case Task::GoFight:
                v.task = Task::Fight;
                v.timer = 0;
                break;
            case Task::Flee:
                v.task = Task::Idle;
                break;
            case Task::GoProvision: take_provisions(v); break;
            case Task::Scout:
                if (v.order == Order::Returning) {
                    v.order = Order::None;  // Home: an ordinary day again.
                    v.task = Task::Idle;
                } else {
                    v.order = Order::Waiting;
                    v.task = Task::ScoutWait;
                }
                break;
            default: v.task = Task::Idle; break;
        }
    }

    void eat(Villager& v) {
        Building* b = g_.buildings_.get(v.target);
        v.task = Task::Idle;
        if (b == nullptr) {
            return;
        }
        // Several helpings: kinds not among the last helpings first (a varied diet
        // keeps villagers healthy), then the most nutritious.
        while (v.food < village::kFoodMax - 100) {
            Stock* best = nullptr;
            const auto score = [&](const Stock& s) {
                const bool fresh = std::find(v.meals.begin(), v.meals.end(), s.resource) == v.meals.end();
                return (fresh ? 1000 : 0) + c_.resources[s.resource].nutrition;
            };
            for (Stock& s : b->stock) {
                const ResourceDef& r = c_.resources[s.resource];
                if (s.amount > 0 && r.category == ResourceCategory::Food && r.nutrition > 0 && gives_out(c_, *b, s.resource) &&
                    (best == nullptr || score(s) > score(*best))) {
                    best = &s;
                }
            }
            if (best == nullptr) {
                break;
            }
            --best->amount;
            v.meals[v.meal_index++ % v.meals.size()] = best->resource;
            v.meal_index = static_cast<std::uint8_t>(v.meal_index % v.meals.size());
            // Variety: the kinds among the last helpings.
            std::uint8_t kinds = 0;
            for (std::size_t m = 0; m < v.meals.size(); ++m) {
                const DefIndex kind = v.meals[m];
                if (kind != kNoDef && std::find(v.meals.begin(), v.meals.begin() + static_cast<std::ptrdiff_t>(m), kind) ==
                                          v.meals.begin() + static_cast<std::ptrdiff_t>(m)) {
                    ++kinds;
                }
            }
            v.variety = kinds;
            v.food = std::min(village::kFoodMax, v.food + c_.resources[best->resource].nutrition * village::kFoodPerNutrition);
        }
        // New clothes and shoes when the old ones are worn out; they last a year.
        if (v.clothes <= 0 && g_.clothes_ != kNoDef && gives_out(c_, *b, g_.clothes_) &&
            amount_of(b->stock, g_.clothes_) > 0) {
            add_to(b->stock, g_.clothes_, -1);
            v.clothes = static_cast<std::int32_t>(kTicksPerYear);
        }
        if (v.shoes <= 0 && g_.shoes_ != kNoDef && gives_out(c_, *b, g_.shoes_) && amount_of(b->stock, g_.shoes_) > 0) {
            add_to(b->stock, g_.shoes_, -1);
            v.shoes = static_cast<std::int32_t>(kTicksPerYear);
        }
        compact(b->stock);
    }

    void deliver(Villager& v) {
        Building* b = g_.buildings_.get(v.target);
        v.task = Task::Idle;
        if (b == nullptr || v.carrying.amount <= 0) {
            return;
        }
        std::int32_t put = std::min(v.carrying.amount, free_space(*b));
        const bool own = v.target == v.job && def(*b).kind == BuildingKind::Workplace;
        // A house takes firewood for its hearth.
        const bool hearth = def(*b).kind == BuildingKind::House && v.carrying.resource == g_.firewood_ &&
                            g_.firewood_ != kNoDef;
        if (hearth) {
            put = std::min(v.carrying.amount, village::kHouseFirewood - amount_of(b->stock, g_.firewood_));
        }
        // The town center always takes gold, full or not (like goods from trade).
        if (v.carrying.resource == g_.gold_ && def(*b).kind == BuildingKind::TownCenter) {
            put = v.carrying.amount;
        }
        if (put > 0 && (own || hearth || accepts(*b, v.carrying.resource))) {
            add_to(b->stock, v.carrying.resource, put);
            v.carrying.amount -= put;
        }
        if (v.carrying.amount <= 0) {
            v.carrying = {};
        }
    }

    void fetch(Villager& v) {
        Building* from = g_.buildings_.get(v.target);
        Building* site = g_.buildings_.get(v.site);
        const DefIndex res = v.carrying.resource;
        const bool for_site = site != nullptr && is_site(*site);
        const std::int32_t promised = for_site ? v.timer : 0;
        v.timer = 0;
        v.carrying = {};
        if (from == nullptr || site == nullptr || res >= c_.resources.size()) {
            if (site != nullptr && for_site) {
                add_to(site->incoming, res, -promised);
                compact(site->incoming);
            }
            v.site = {};
            v.task = Task::Idle;
            return;
        }
        std::int32_t want = for_site ? promised : carry_capacity(c_, res);
        want = std::min(want, amount_of(from->stock, res));
        if (res == g_.gold_ && !for_site) {
            want = std::min(want, gold_to_move(*from, v.site, v.owner));
        }
        if (for_site && want < promised) {
            add_to(site->incoming, res, want - promised);
        }
        compact(site->incoming);
        if (want <= 0) {
            v.site = {};
            v.task = Task::Idle;
            return;
        }
        add_to(from->stock, res, -want);
        compact(from->stock);
        v.carrying = {res, want};
        const EntityId dest = v.site;
        v.site = {};
        go(v, for_site ? Task::GoSite : (dest == v.job ? Task::GoWorkplace : Task::GoDeliver), dest);
    }

    void deliver_to_site(Villager& v) {
        Building* site = g_.buildings_.get(v.target);
        v.task = Task::Idle;
        if (site == nullptr || !is_site(*site)) {
            return;  // Goods stay in hand; delivered to storage next.
        }
        add_to(site->incoming, v.carrying.resource, -v.carrying.amount);
        compact(site->incoming);
        add_to(site->delivered, v.carrying.resource, v.carrying.amount);
        v.carrying = {};
        g_.buildings_changed_ = true;
    }

    void at_workplace(Villager& v) {
        Building* job = g_.buildings_.get(v.target);
        if (job == nullptr) {
            v.task = Task::Idle;
            return;
        }
        if (v.carrying.amount > 0) {
            add_to(job->stock, v.carrying.resource, v.carrying.amount);
            v.carrying = {};
        }
        v.task = Task::Produce;
        v.timer = 0;
    }

    void work(Villager& v) {
        switch (v.task) {
            case Task::Gather: gather(v); break;
            case Task::Build: build(v); break;
            case Task::Produce: produce(v); break;
            case Task::Farm: farm_work(v); break;
            case Task::Hunt: hunt_work(v); break;
            case Task::Fish: fish_work(v); break;
            case Task::FightFire: fight_fire(v); break;
            case Task::Fight: fight(v); break;
            default: v.task = Task::Idle; break;
        }
    }

    void gather(Villager& v) {
        if (v.node == 0) {
            v.task = Task::Idle;
            return;
        }
        Node& n = g_.nodes_[v.node - 1];
        const MapFeature& f = g_.map_.features[v.node - 1];
        const FeatureDef* fd = c_.feature(f.type);
        if (fd == nullptr || n.amount <= 0) {
            release(v);
            v.task = Task::Idle;
            return;
        }
        if ((v.timer += steps(v, gather_skill(f.type))) < fd->work) {
            return;
        }
        v.timer = 0;
        --n.amount;
        v.carrying.resource = fd->resource;
        ++v.carrying.amount;
        if (n.amount <= 0) {
            g_.changed_nodes_.push_back(v.node - 1);
            if (fd->regrow_days > 0) {
                const std::uint64_t at = g_.tick_ + static_cast<std::uint64_t>(fd->regrow_days) * g_.day_ticks();
                n.regrow_tick = at;
                const std::pair<std::uint64_t, std::uint32_t> item{at, v.node - 1};
                g_.regrow_.insert(std::upper_bound(g_.regrow_.begin(), g_.regrow_.end(), item), item);
            }
        }
        if (n.amount <= 0 || v.carrying.amount >= carry_capacity(c_, fd->resource)) {
            release(v);
            v.task = Task::Idle;  // Decides to deliver next.
        }
    }

    void build(Villager& v) {
        Building* site = g_.buildings_.get(v.target);
        if (site == nullptr || !is_site(*site)) {
            v.task = Task::Idle;
            return;
        }
        const std::int32_t before = site->work_done;
        site->work_done += steps(v, Skill::Build);
        if (site->work_done / 25 != before / 25) {
            g_.buildings_changed_ = true;  // The view shows the rising building.
        }
        if (site->work_done >= site_work(*site)) {
            if (site->state == BuildingState::Construction) {
                finish(*site);
            } else {
                // An upgrade done.
                ++site->level;
                site->upgrading = false;
                site->delivered.clear();
                site->incoming.clear();
                site->work_done = 0;
                g_.buildings_changed_ = true;
            }
            v.task = Task::Idle;
        }
    }

    void finish(Building& b) {
        b.state = BuildingState::Complete;
        b.built_tick = static_cast<std::int64_t>(g_.tick_);
        b.delivered.clear();
        b.incoming.clear();
        b.work_done = 0;
        b.wanted_workers = def(b).workers;
        if (def(b).trade) {
            b.limit = kPostReserve;
        }
        g_.buildings_changed_ = true;
    }

    void produce(Villager& v) {
        Building* job = g_.buildings_.get(v.target);
        if (job == nullptr || def(*job).recipes.empty()) {
            v.task = Task::Idle;
            return;
        }
        const RecipeDef& recipe =
            c_.recipes[def(*job).recipes[std::min<std::size_t>(job->recipe, def(*job).recipes.size() - 1)]];
        for (const ResourceAmount& in : recipe.inputs) {
            if (amount_of(job->stock, in.resource) < in.amount) {
                v.task = Task::Idle;
                return;
            }
        }
        if ((v.timer += steps(v, produce_skill(*job, recipe))) < recipe.work) {
            return;
        }
        // Another worker may have reached the year's limit meanwhile.
        const std::int32_t limit = g_.per_year(def(*job).yearly_limit);
        if (limit > 0 && job->produced_year == g_.calendar().year && job->produced >= limit) {
            v.task = Task::Idle;
            return;
        }
        for (const ResourceAmount& in : recipe.inputs) {
            add_to(job->stock, in.resource, -in.amount);
        }
        compact(job->stock);
        const ResourceAmount& out = recipe.outputs.front();
        v.carrying = {out.resource, out.amount};
        job->produced += out.amount;
        v.task = Task::Idle;  // Delivers next.
    }

    // --- Population ----------------------------------------------------------

    [[nodiscard]] std::int32_t food_stored(std::uint8_t owner) const {
        std::int32_t food = 0;
        const std::vector<std::int32_t> totals = g_.stored(owner);
        for (std::size_t r = 0; r < totals.size(); ++r) {
            if (c_.resources[r].category == ResourceCategory::Food) {
                food += totals[r];
            }
        }
        return food;
    }

    EntityId spawn_villager(std::uint8_t owner, FixedVec2 at, Sex sex, std::int32_t age_years, std::uint32_t family,
                            std::uint8_t race = 0) {
        if (g_.population(owner) >= std::min(village::kMaxVillagersPerPlayer, g_.rules_.max_population)) {
            return {};
        }
        const EntityId id = g_.registry_.create();
        if (!id.valid()) {
            return id;
        }
        Villager v;
        v.owner = owner;
        v.sex = sex;
        v.race = race < c_.races.size() ? race : 0;
        v.appearance = g_.rng_.next_u32();
        v.family = family;
        v.born_tick = static_cast<std::int64_t>(g_.tick_) - static_cast<std::int64_t>(age_years) * g_.year_ticks() -
                      static_cast<std::int64_t>(g_.rng_.below(g_.year_ticks()));
        v.position = at;
        v.previous = at;
        v.food = 700 + static_cast<std::int32_t>(g_.rng_.below(300));
        v.idle_ticks = static_cast<std::int32_t>(g_.rng_.below(40));
        g_.villagers_.add(id, v);
        g_.villagers_changed();
        return id;
    }

    // A villager is gone: `silent` for those who left or became soldiers
    // (not deaths).
    void kill(EntityId id, bool silent = false) {
        Villager* v = g_.villagers_.get(id);
        if (v == nullptr) {
            return;
        }
        if (!silent) {
            g_.events_.push_back({Game::Event::Kind::Died, v->owner, {}, v->position, 0, 0});
        }
        v_index_ = id.index;
        release(*v);
        keep_gold(*v);
        if (Building* job = g_.buildings_.get(v->job)) {
            std::erase(job->workers, id);
        }
        if (Building* home = g_.buildings_.get(v->home)) {
            std::erase(home->residents, id);
        }
        ++g_.players_[v->owner].deaths;
        g_.villagers_.remove(id);
        g_.villagers_changed();
        g_.registry_.destroy(id);
    }

    void assign_jobs() {
        auto& list = g_.buildings_;
        // Per town: adults without a job, and how many must stay laborers
        // (to build and carry) when something is being built.
        std::array<std::int32_t, kMaxPlayers> free{};
        std::array<std::int32_t, kMaxPlayers> reserve{};
        std::array<bool, kMaxPlayers> building{};
        for (const Building& b : list.data()) {
            building[b.owner] = building[b.owner] || b.state == BuildingState::Construction;
        }
        std::array<std::int32_t, kMaxPlayers> adults{};
        for (const Villager& v : g_.villagers_.data()) {
            if (g_.adult(v)) {
                ++adults[v.owner];
                free[v.owner] += g_.buildings_.get(v.job) == nullptr ? 1 : 0;
            }
        }
        for (std::size_t p = 0; p < kMaxPlayers; ++p) {
            reserve[p] = building[p] ? std::max(2, adults[p] / 5) : 1;
        }
        for (std::size_t i = 0; i < list.size(); ++i) {
            Building& b = list.data()[i];
            std::erase_if(b.workers, [&](EntityId w) { return g_.villagers_.get(w) == nullptr; });
            if (!complete(b)) {
                continue;
            }
            // Too many (all of them, when it is stopped): the newest go
            // back to laboring.
            const std::int32_t wanted = b.stopped ? 0 : b.wanted_workers;
            while (static_cast<std::int32_t>(b.workers.size()) > wanted) {
                if (Villager* w = g_.villagers_.get(b.workers.back())) {
                    w->job = {};
                    ++free[b.owner];
                }
                b.workers.pop_back();
            }
            while (static_cast<std::int32_t>(b.workers.size()) < wanted && free[b.owner] > reserve[b.owner]) {
                // The nearest free adult of the owner.
                EntityId best;
                std::uint64_t best_d = UINT64_MAX;
                const auto& vs = g_.villagers_;
                for (std::size_t k = 0; k < vs.size(); ++k) {
                    const Villager& v = vs.data()[k];
                    if (v.owner != b.owner || v.job.valid() || !g_.adult(v)) {
                        continue;
                    }
                    const std::uint64_t d = distance2(v.position, g_.door(b));
                    if (d < best_d) {
                        best_d = d;
                        best = vs.entities()[k];
                    }
                }
                if (!best.valid()) {
                    break;
                }
                Villager& v = *g_.villagers_.get(best);
                v.job = list.entities()[i];
                b.workers.push_back(best);
                --free[b.owner];
            }
        }
    }

    void assign_homes() {
        auto& vs = g_.villagers_;
        auto& list = g_.buildings_;
        // Houses with room, by town (found once; before, every homeless
        // villager looked through every building).
        std::array<std::vector<std::size_t>, kMaxPlayers> open;
        bool any_homeless = false;
        for (const Villager& v : vs.data()) {
            any_homeless = any_homeless || g_.buildings_.get(v.home) == nullptr;
        }
        if (!any_homeless) {
            return;
        }
        for (std::size_t i = 0; i < list.size(); ++i) {
            const Building& b = list.data()[i];
            if (b.owner < kMaxPlayers && complete(b) && g_.capacity(b) > 0 &&
                static_cast<std::int32_t>(b.residents.size()) < g_.capacity(b)) {
                open[b.owner].push_back(i);
            }
        }
        for (std::size_t k = 0; k < vs.size(); ++k) {
            Villager& v = vs.data()[k];
            if (g_.buildings_.get(v.home) != nullptr) {
                continue;
            }
            v.home = {};
            if (v.owner >= kMaxPlayers) {
                continue;
            }
            // A house with room; one with family is better.
            std::size_t best = SIZE_MAX;
            int best_score = -1;
            for (const std::size_t i : open[v.owner]) {
                const Building& b = list.data()[i];
                if (static_cast<std::int32_t>(b.residents.size()) >= g_.capacity(b)) {
                    continue;
                }
                int score = 1;
                for (const EntityId r : b.residents) {
                    const Villager* o = vs.get(r);
                    if (o != nullptr && o->family == v.family) {
                        score = 3;
                    }
                }
                if (b.residents.empty()) {
                    score = 2;
                }
                if (score > best_score) {
                    best_score = score;
                    best = i;
                }
            }
            if (best != SIZE_MAX) {
                v.home = list.entities()[best];
                list.data()[best].residents.push_back(vs.entities()[k]);
            }
        }
    }

    // Old age goes by the calendar's months: the years of a life stretch
    // with the year.
    void old_age() {
        std::vector<EntityId> dying;
        const auto& vs = g_.villagers_;
        for (std::size_t k = 0; k < vs.size(); ++k) {
            const Villager& v = vs.data()[k];
            const std::int32_t age = g_.age_years(v);
            if (age >= village::kOldAgeYears &&
                g_.rng_.below(1000) < static_cast<std::uint32_t>(std::min(500, (age - village::kOldAgeYears + 1) * 8))) {
                dying.push_back(vs.entities()[k]);
            }
        }
        for (const EntityId id : dying) {
            kill(id);
        }
    }

    // The village's month, always a hundred seconds at x1. `calendar_month`:
    // it is also the calendar's.
    void monthly(bool calendar_month) {
        check_outcomes();
        // Diets: last month's variety; the game comes back to its zones.
        for (std::size_t z = 0; z < g_.zone_animals_.size(); ++z) {
            const std::int32_t cap = g_.zone_open(z) ? zone_capacity(g_.map_.zones[z].type, g_.rules_) : 0;
            const std::int32_t before = g_.zone_animals_[z];
            g_.zone_animals_[z] = std::min(cap, before + std::max(1, cap / 6));
            for (std::int32_t n = before; n < g_.zone_animals_[z]; ++n) {
                spawn_animal(z);
            }
        }
        if (calendar_month) {
            old_age();
        }
        // Births: a home with a man and a woman, room and fed parents.
        auto& list = g_.buildings_;
        for (std::size_t i = 0; i < list.size(); ++i) {
            Building& b = list.data()[i];
            if (!complete(b) || g_.capacity(b) <= 0 || static_cast<std::int32_t>(b.residents.size()) >= g_.capacity(b)) {
                continue;
            }
            const Villager* mother = nullptr;
            const Villager* dad = nullptr;
            for (const EntityId r : b.residents) {
                const Villager* v = g_.villagers_.get(r);
                if (v == nullptr || !g_.adult(*v) || g_.age_years(*v) > 40 || v->food < 500) {
                    continue;
                }
                if (v->sex == Sex::Female) {
                    mother = v;
                } else {
                    dad = v;
                }
            }
            const bool father = dad != nullptr;
            // Happier homes have more children (12 % a month at 60).
            if (mother == nullptr || !father || food_stored(b.owner) < 3 * g_.population(b.owner) || b.happiness < 25 ||
                g_.rng_.below(1000) >= static_cast<std::uint32_t>(2 * b.happiness)) {
                continue;
            }
            const std::uint32_t family = mother->family;
            const std::uint8_t owner = b.owner;
            const FixedVec2 at = g_.door(b);
            const Sex sex = g_.rng_.below(2) == 0 ? Sex::Male : Sex::Female;
            // The child takes the race of one of the parents.
            const std::uint8_t race = mother->race == dad->race || g_.rng_.below(2) == 0 ? mother->race : dad->race;
            const EntityId baby = spawn_villager(owner, at, sex, 0, family, race);
            if (baby.valid()) {
                Villager* bv = g_.villagers_.get(baby);
                bv->born_tick = static_cast<std::int64_t>(g_.tick_);
                bv->home = list.entities()[i];
                g_.buildings_.get(list.entities()[i])->residents.push_back(baby);
                ++g_.players_[owner].births;
                g_.events_.push_back({Game::Event::Kind::Born, owner, baby, at, 0, 0});
            }
        }
        // Newcomers, when there is room and food to spare.
        for (std::uint8_t p = 0; p < g_.player_count_; ++p) {
            if (!g_.players_[p].active || g_.town_of(p) != p) {
                continue;
            }
            std::int32_t room = 0;
            for (std::size_t i = 0; i < list.size(); ++i) {
                const Building& b = list.data()[i];
                if (b.owner == p && complete(b) && g_.capacity(b) > 0) {
                    room += g_.capacity(b) - static_cast<std::int32_t>(b.residents.size());
                }
            }
            const std::int32_t food = food_stored(p);
            const std::int32_t pop = g_.population(p);
            // Newcomers want a town that has food to spare and happy people.
            if (room < 2 || food < 40 + pop * 10 || g_.happiness(p) < 35) {
                continue;
            }
            const Building* tc = g_.buildings_.get(g_.players_[p].town_center);
            if (tc == nullptr) {
                continue;
            }
            const std::int32_t count = std::min(room, 2 + static_cast<std::int32_t>(g_.rng_.below(3)));
            const std::uint32_t family = g_.players_[p].next_family++;
            const std::uint8_t race = newcomer_race(p);
            for (std::int32_t n = 0; n < count; ++n) {
                const Sex sex = n == 0 ? Sex::Male : (n == 1 ? Sex::Female : (g_.rng_.below(2) == 0 ? Sex::Male : Sex::Female));
                const std::int32_t age = n < 2 ? 18 + static_cast<std::int32_t>(g_.rng_.below(15))
                                               : static_cast<std::int32_t>(g_.rng_.below(4));
                if (spawn_villager(p, g_.door(*tc), sex, age, family, race).valid()) {
                    ++g_.players_[p].arrivals;
                }
            }
        }
        // Very unhappy homes may pack up and leave.
        std::vector<EntityId> leaving;
        for (const Building& b : list.data()) {
            if (def(b).kind == BuildingKind::House && !b.residents.empty() && b.happiness < 15 &&
                g_.rng_.below(100) < 25) {
                leaving.insert(leaving.end(), b.residents.begin(), b.residents.end());
            }
        }
        for (const EntityId id : leaving) {
            if (const Villager* v = g_.villagers_.get(id)) {
                ++g_.players_[v->owner].departures;
                --g_.players_[v->owner].deaths;  // kill() counts a death; this was a departure.
            }
            kill(id, true);
        }
    }

    // --- The tick -------------------------------------------------------------

    // Once a day: the weather, the snow and the houses' fires.
    // Once a day: which services work, and each home's needs, beauty,
    // happiness and upgrade.
    void update_homes() {
        struct Service {
            std::uint8_t need;
            std::uint8_t owner;
            FixedVec2 at;
            std::uint64_t reach2;
        };
        std::vector<Service> services;
        const auto center = [](const Building& b) {
            return FixedVec2{Fixed::from_int(b.x) + Fixed::from_ratio(b.width, 2), Fixed::from_int(b.z) + Fixed::from_ratio(b.depth, 2)};
        };
        const auto meters2 = [](std::int64_t m) { return static_cast<std::uint64_t>(m * m) << 32; };
        for (Building& b : g_.buildings_.data()) {
            const BuildingDef& d = def(b);
            if (d.service == kNoNeed || !complete(b)) {
                continue;
            }
            bool active = d.workers == 0 || !b.workers.empty();
            for (const ResourceAmount& use : d.service_uses) {
                active = active && amount_of(b.stock, use.resource) >= use.amount;
            }
            if (!active) {
                continue;
            }
            for (const ResourceAmount& use : d.service_uses) {
                add_to(b.stock, use.resource, -use.amount);
            }
            compact(b.stock);
            services.push_back({d.service, b.owner, center(b), meters2(d.service_radius)});
        }
        for (Building& b : g_.buildings_.data()) {
            const BuildingDef& d = def(b);
            if (d.kind != BuildingKind::House || !complete(b)) {
                continue;
            }
            const FixedVec2 here = center(b);
            std::uint16_t bits = 0;
            const auto set = [&](Need n) { bits = static_cast<std::uint16_t>(bits | (1u << static_cast<unsigned>(n))); };
            // What the residents have.
            std::int32_t fed = 0, clothed = 0, shod = 0, n = 0;
            for (const EntityId r : b.residents) {
                if (const Villager* v = g_.villagers_.get(r)) {
                    ++n;
                    fed += v->variety >= 3 ? 1 : 0;
                    clothed += v->clothes > 0 ? 1 : 0;
                    shod += v->shoes > 0 ? 1 : 0;
                }
            }
            if (n > 0 && fed * 2 >= n) {
                set(Need::Food);
            }
            if (n > 0 && clothed * 2 >= n) {
                set(Need::Clothes);
            }
            if (n > 0 && shod * 2 >= n) {
                set(Need::Shoes);
            }
            if (b.heated) {
                set(Need::Heating);
            }
            for (const Service& sv : services) {
                if (sv.owner == b.owner && distance2(here, sv.at) <= sv.reach2) {
                    bits = static_cast<std::uint16_t>(bits | (1u << sv.need));
                }
            }
            // Beauty: pleasant and unpleasant buildings nearby, and trees.
            const std::int32_t beauty = g_.desirability_at(here, &b);
            b.desirability = beauty;
            if (beauty >= 10) {
                set(Need::Beauty);
            }
            b.needs = bits;
            // Happiness: a base, each need met, and the neighborhood.
            const auto met = static_cast<std::int32_t>(std::popcount(static_cast<unsigned>(bits)));
            b.happiness = std::clamp(28 + 8 * met + std::clamp(beauty / 2, -10, 10), 0, 100);
            // An upgrade when the next level's needs are met.
            if (!b.upgrading && b.level < d.levels.size()) {
                const LevelDef& next = d.levels[b.level];
                if ((bits & next.needs) == next.needs && g_.tier(b.owner) >= std::max(1, next.tier)) {
                    b.upgrading = true;
                }
            }
        }
    }

    // The calendar's day (phase 59): the weather turns and the crops grow.
    void calendar_daily() {
        g_.temperature_ = sim::temperature(g_.rules_.climate, g_.seed_, g_.tick_);
        grow_fields();
        g_.buildings_changed_ = true;
    }

    // The village's day, always ten seconds at x1. `calendar_day`: it is
    // also the calendar's (always, with a year of the usual length).
    void daily(bool calendar_day) {
        g_.temperature_ = sim::temperature(g_.rules_.climate, g_.seed_, g_.tick_);
        if (calendar_day) {
            grow_fields();
        }
        update_homes();
        update_health();
        start_fires();
        daily_trade();
        daily_raids();
        const std::int32_t t = g_.temperature_;
        if (t < 0) {
            g_.snow_ = std::min(village::kMaxSnow, g_.snow_ + 1 + std::min(-t, 10) / 2);
        } else if (t > 2) {
            g_.snow_ = std::max(0, g_.snow_ - (t - 1));
        }
        auto& list = g_.buildings_;
        for (std::size_t i = 0; i < list.size(); ++i) {
            Building& b = list.data()[i];
            if (def(b).warmth > 0 && complete(b)) {
                // A campfire burns a unit of firewood from the town's stores
                // each cold day; without it, it is out.
                b.heated = true;
                if (t < village::kColdBelow) {
                    const FixedVec2 at{Fixed::from_int(b.x), Fixed::from_int(b.z)};
                    Building* store = g_.firewood_ == kNoDef ? nullptr : g_.buildings_.get(storage_with(b.owner, at, g_.firewood_));
                    b.heated = store != nullptr;
                    if (store != nullptr) {
                        add_to(store->stock, g_.firewood_, -1);
                        compact(store->stock);
                    }
                }
                continue;
            }
            if (def(b).kind != BuildingKind::House || !complete(b)) {
                continue;
            }
            // One log's worth of firewood (3) lasts three freezing days, or
            // six cool ones.
            const std::uint64_t day = g_.tick_ / g_.day_ticks();
            const std::int32_t need = t < 0 ? 1 : (t < village::kColdBelow && day % 2 == 0 ? 1 : 0);
            if (need == 0 || b.residents.empty()) {
                b.heated = true;
                continue;
            }
            const std::int32_t have = g_.firewood_ == kNoDef ? 0 : amount_of(b.stock, g_.firewood_);
            b.heated = have >= need;
            if (have > 0) {
                add_to(b.stock, g_.firewood_, -std::min(have, need));
                compact(b.stock);
            }
        }
        g_.buildings_changed_ = true;
    }

    // Cold: a villager out of a warm home loses warmth when it is cold
    // (half as fast with clothes); at zero, health. Returns false if dead.
    bool weather(Villager& v) {
        if (v.clothes > 0) {
            --v.clothes;
        }
        if (v.shoes > 0) {
            --v.shoes;
        }
        if (g_.tick_ % 4 != 0) {
            return true;
        }
        const Building* home = g_.buildings_.get(v.home);
        bool warm_home = home != nullptr && home->heated;
        if (g_.temperature_ < 5 && !warm_home) {
            // A campfire burning nearby is as good as a warm home.
            for (const EntityId id : g_.owned(v.owner)) {
                const Building& fire = *g_.buildings_.get(id);
                const std::int32_t reach = def(fire).warmth;
                if (reach > 0 && fire.heated && complete(fire) &&
                    distance2(v.position, {Fixed::from_int(fire.x) + Fixed::from_ratio(fire.width, 2),
                                           Fixed::from_int(fire.z) + Fixed::from_ratio(fire.depth, 2)}) <= meters2(reach)) {
                    warm_home = true;
                    break;
                }
            }
        }
        if (g_.temperature_ < 5 && !warm_home) {
            std::int32_t loss = (v.clothes > 0 ? 1 : 2) + (g_.temperature_ < -8 ? 1 : 0);
            if (const RaceDef* r = race_of(v); r != nullptr && r->cold != 0) {
                // Hardy peoples lose less; a negative resistance loses more.
                loss = std::max(0, (loss * (100 - r->cold) + 50) / 100);
            }
            v.warmth = std::max(0, v.warmth - loss);
        } else {
            v.warmth = std::min(village::kWarmthMax, v.warmth + 3);
        }
        if (v.warmth == 0) {
            v.health -= 1;
        }
        return v.health > 0;
    }

    void step() {
        ++g_.tick_;
        const bool calendar_day = g_.tick_ % g_.calendar_day_ticks() == 0;
        if (g_.tick_ % g_.day_ticks() == 0) {
            daily(calendar_day);
        } else if (calendar_day) {
            calendar_daily();
        }
        if (g_.fires_ > 0) {
            burn();
        }
        // Bushes that grow back (not while it freezes).
        while (!g_.frozen() && !g_.regrow_.empty() && g_.regrow_.front().first <= g_.tick_) {
            const std::uint32_t i = g_.regrow_.front().second;
            g_.regrow_.erase(g_.regrow_.begin());
            Node& n = g_.nodes_[i];
            const FeatureDef* fd = c_.feature(g_.map_.features[i].type);
            if (fd != nullptr && n.regrow_tick != 0) {
                n.amount = std::max(1, (fd->amount * g_.map_.features[i].scale.raw()) >> 16);
                n.regrow_tick = 0;
                g_.changed_nodes_.push_back(i);
            }
        }
        if (g_.tick_ % kJobEvery == 0) {
            assign_jobs();
            assign_homes();
        }
        const bool calendar_month = g_.tick_ % g_.calendar_month_ticks() == 0;
        if (g_.tick_ % g_.month_ticks() == 0) {
            monthly(calendar_month);
        } else if (calendar_month) {
            old_age();
        }
        std::vector<EntityId> dying;
        auto& vs = g_.villagers_;
        for (std::size_t k = 0; k < vs.size(); ++k) {
            Villager& v = vs.data()[k];
            v_index_ = vs.entities()[k].index;
            v.previous = v.position;
            // The militia follows its enemy.
            if (v.task == Task::GoFight && (g_.tick_ + k) % 20 == 0) {
                const Creature* a = g_.creatures_.get(v.target);
                if (a != nullptr && distance2(a->position, v.position) <= meters2(3)) {
                    v.task = Task::Fight;
                    v.path.clear();
                    v.path_index = 0;
                } else if (!start_fight(v)) {
                    v.task = Task::Idle;
                    v.path.clear();
                    v.path_index = 0;
                }
            }
            // A full meter lasts four months; children eat half as much.
            if (g_.tick_ % (g_.adult(v) ? village::kTicksPerFoodPoint : 2 * village::kTicksPerFoodPoint) == 0) {
                --v.food;
            }
            if (v.food <= 0) {
                v.food = 0;
                v.health -= g_.tick_ % 2 == 0 ? 1 : 0;  // About three minutes to starve.
                if (v.health <= 0) {
                    dying.push_back(vs.entities()[k]);
                    continue;
                }
            } else if (v.health < village::kHealthMax && v.warmth > 0 && v.disease == 0 && g_.tick_ % (v.variety >= 3 ? 2 : 4) == 0) {
                ++v.health;  // Faster with a varied diet.
            }
            if (!weather(v)) {
                dying.push_back(vs.entities()[k]);
                continue;
            }
            // Phase 66: the explorer's food and way back; the hungry leave their task.
            if ((g_.tick_ + k) % 16 == 0) {
                if (v.order != Order::None) {
                    scout_check(v);
                } else {
                    eat_now(v);
                }
            }
            if (moving(v)) {
                move(v);
                if (!moving(v)) {
                    arrive(v);
                }
            } else if (v.task == Task::ScoutWait && v.order == Order::Waiting) {
                // Waits for another order.
            } else if (v.task == Task::Gather || v.task == Task::Build || v.task == Task::Produce || v.task == Task::Farm ||
                       v.task == Task::Hunt || v.task == Task::Fish || v.task == Task::FightFire || v.task == Task::Fight) {
                work(v);
            } else if (v.idle_ticks > 0) {
                --v.idle_ticks;
            } else {
                decide(v);
            }
        }
        for (const EntityId id : dying) {
            kill(id);
        }
        update_creatures();
        defend();
        if (g_.tick_ % 10 == 0) {
            train();
        }
    }

    // --- Setup and commands ---------------------------------------------------------

    EntityId add_building(std::uint8_t owner, DefIndex def_index, std::int32_t x, std::int32_t z, std::uint8_t rotation,
                          bool complete_now) {
        const BuildingDef& d = c_.buildings[def_index];
        Building b;
        b.def = def_index;
        b.owner = owner;
        b.rotation = rotation;
        b.x = x;
        b.z = z;
        Game::footprint(d, rotation, b.width, b.depth);
        b.state = complete_now || d.build_work <= 0 ? BuildingState::Complete : BuildingState::Construction;
        b.built_tick = static_cast<std::int64_t>(g_.tick_);
        b.wanted_workers = b.state == BuildingState::Complete ? d.workers : 0;
        const EntityId id = g_.registry_.create();
        if (!id.valid()) {
            return id;
        }
        // Clear the ground: whatever stands on the footprint goes.
        for (std::int32_t cz = z / kNodeCell - 1; cz <= (z + b.depth) / kNodeCell + 1; ++cz) {
            for (std::int32_t cx = x / kNodeCell - 1; cx <= (x + b.width) / kNodeCell + 1; ++cx) {
                if (cx < 0 || cz < 0 || cx >= g_.node_cells_side_ || cz >= g_.node_cells_side_) {
                    continue;
                }
                for (const std::uint32_t i : g_.node_cells_[static_cast<std::size_t>(cz * g_.node_cells_side_ + cx)]) {
                    const MapFeature& f = g_.map_.features[i];
                    const std::int32_t fx = f.x.floor_int();
                    const std::int32_t fz = f.z.floor_int();
                    if (fx >= x - 1 && fx <= x + b.width && fz >= z - 1 && fz <= z + b.depth && g_.nodes_[i].amount > 0) {
                        g_.nodes_[i].amount = 0;
                        g_.nodes_[i].regrow_tick = 0;
                        g_.changed_nodes_.push_back(i);
                    }
                }
            }
        }
        for (std::int32_t cz = z; cz < z + b.depth; ++cz) {
            for (std::int32_t cx = x; cx < x + b.width; ++cx) {
                g_.occupied_[static_cast<std::size_t>(cz) * static_cast<std::size_t>(g_.map_.size) + static_cast<std::size_t>(cx)] = 1;
            }
        }
        block_nav(g_.nav_, d, x, z, b.width, b.depth, true);
        g_.buildings_.add(id, b);
        g_.building_set_changed();
        g_.buildings_changed_ = true;
        return id;
    }

    void mark_field(const Field& f, std::uint8_t value) {
        for (std::int32_t cz = f.z; cz < f.z + f.d; ++cz) {
            for (std::int32_t cx = f.x; cx < f.x + f.w; ++cx) {
                g_.occupied_[static_cast<std::size_t>(cz) * static_cast<std::size_t>(g_.map_.size) + static_cast<std::size_t>(cx)] =
                    value;
            }
        }
    }

    void add_field(Building& farm, std::int32_t x, std::int32_t z, std::int32_t w, std::int32_t d) {
        Field f;
        f.x = x;
        f.z = z;
        f.w = w;
        f.d = d;
        // The soil's own fertility, averaged.
        std::int64_t sum = 0;
        for (std::int32_t cz = z; cz < z + d; ++cz) {
            for (std::int32_t cx = x; cx < x + w; ++cx) {
                sum += g_.map_.fertility[static_cast<std::size_t>(cz) * static_cast<std::size_t>(g_.map_.size) +
                                         static_cast<std::size_t>(cx)];
            }
        }
        f.fertility = static_cast<std::int32_t>(sum * 100 / (255 * static_cast<std::int64_t>(w) * d));
        // A first plan: the content's crops in turn.
        for (std::size_t y = 0; y < kPlanYears && !c_.crops.empty(); ++y) {
            f.plan[y] = static_cast<DefIndex>(y % c_.crops.size());
        }
        f.year = g_.calendar().year;
        // Whatever grows there is cleared.
        for (std::int32_t cz = z / kNodeCell - 1; cz <= (z + d) / kNodeCell + 1; ++cz) {
            for (std::int32_t cx = x / kNodeCell - 1; cx <= (x + w) / kNodeCell + 1; ++cx) {
                if (cx < 0 || cz < 0 || cx >= g_.node_cells_side_ || cz >= g_.node_cells_side_) {
                    continue;
                }
                for (const std::uint32_t i : g_.node_cells_[static_cast<std::size_t>(cz * g_.node_cells_side_ + cx)]) {
                    const MapFeature& mf = g_.map_.features[i];
                    const std::int32_t fx = mf.x.floor_int();
                    const std::int32_t fz = mf.z.floor_int();
                    if (fx >= x && fx < x + w && fz >= z && fz < z + d && g_.nodes_[i].amount > 0) {
                        g_.nodes_[i].amount = 0;
                        g_.nodes_[i].regrow_tick = 0;
                        g_.changed_nodes_.push_back(i);
                    }
                }
            }
        }
        mark_field(f, 2);
        farm.fields.push_back(f);
        g_.buildings_changed_ = true;
    }

    // A building is gone. Its gold goes to the town center unless it burned
    // (phase 28); the rest of what it stored is lost.
    void remove_building(EntityId id, bool burned = false) {
        Building* b = g_.buildings_.get(id);
        if (b == nullptr) {
            return;
        }
        if (b->fire > 0) {
            --g_.fires_;
            b->fire = 0;
        }
        for (const Field& f : b->fields) {
            mark_field(f, 0);
        }
        for (const EntityId w : b->workers) {
            if (Villager* v = g_.villagers_.get(w)) {
                v->job = {};
            }
        }
        for (const EntityId r : b->residents) {
            if (Villager* v = g_.villagers_.get(r)) {
                v->home = {};
            }
        }
        // Delivered materials go back to the town center.
        if (Building* tc = g_.buildings_.get(g_.players_[b->owner].town_center); tc != nullptr && tc != b) {
            for (const Stock& s : b->delivered) {
                add_to(tc->stock, s.resource, s.amount);
            }
            if (!burned && g_.gold_ != kNoDef) {
                add_to(tc->stock, g_.gold_, amount_of(b->stock, g_.gold_));
                compact(tc->stock);
            }
        }
        for (std::int32_t cz = b->z; cz < b->z + b->depth; ++cz) {
            for (std::int32_t cx = b->x; cx < b->x + b->width; ++cx) {
                g_.occupied_[static_cast<std::size_t>(cz) * static_cast<std::size_t>(g_.map_.size) + static_cast<std::size_t>(cx)] = 0;
            }
        }
        block_nav(g_.nav_, def(*b), b->x, b->z, b->width, b->depth, false);
        g_.buildings_.remove(id);
        g_.building_set_changed();
        g_.registry_.destroy(id);
        g_.buildings_changed_ = true;
    }

    void apply(const Command& command) {
        if (command.player >= g_.player_count_ || !g_.players_[command.player].active) {
            ++g_.rejected_;
            return;
        }
        // In a common town every player gives orders to player 0's town.
        Command c = command;
        c.player = g_.town_of(command.player);
        switch (c.type) {
            case CommandType::PlaceBuilding: {
                const std::int32_t x = c.position.x.floor_int();
                const std::int32_t z = c.position.z.floor_int();
                const auto rot = static_cast<std::uint8_t>(c.value & 3);
                if (g_.can_place(c.player, c.def, x, z, rot) != PlaceError::None ||
                    !add_building(c.player, c.def, x, z, rot, false).valid()) {
                    ++g_.rejected_;
                }
                break;
            }
            case CommandType::RemoveBuilding: {
                const Building* b = g_.buildings_.get(c.entity);
                if (b == nullptr || b->owner != c.player || c.entity == g_.players_[c.player].town_center) {
                    ++g_.rejected_;
                    break;
                }
                remove_building(c.entity);
                break;
            }
            case CommandType::SetWorkers: {
                Building* b = g_.buildings_.get(c.entity);
                if (b == nullptr || b->owner != c.player) {
                    ++g_.rejected_;
                    break;
                }
                b->wanted_workers = std::clamp(c.value, 0, def(*b).workers);
                g_.buildings_changed_ = true;
                break;
            }
            case CommandType::PlaceField: {
                const std::int32_t w = c.value & 0xFF;
                const std::int32_t d = (c.value >> 8) & 0xFF;
                const std::int32_t x = c.position.x.floor_int();
                const std::int32_t z = c.position.z.floor_int();
                if (g_.can_place_field(c.player, c.entity, x, z, w, d) != PlaceError::None) {
                    ++g_.rejected_;
                    break;
                }
                add_field(*g_.buildings_.get(c.entity), x, z, w, d);
                break;
            }
            case CommandType::SetCrop: {
                Building* farm = g_.buildings_.get(c.entity);
                const std::size_t index = static_cast<std::size_t>(c.value & 0xFF);
                const std::size_t year = static_cast<std::size_t>(c.value >> 8);
                if (farm == nullptr || farm->owner != c.player || index >= farm->fields.size() || year >= kPlanYears ||
                    (c.def != kNoDef && c.def >= c_.crops.size())) {
                    ++g_.rejected_;
                    break;
                }
                farm->fields[index].plan[year] = c.def;
                g_.buildings_changed_ = true;
                break;
            }
            case CommandType::RemoveField: {
                Building* farm = g_.buildings_.get(c.entity);
                const auto index = static_cast<std::size_t>(c.value);
                if (farm == nullptr || farm->owner != c.player || index >= farm->fields.size()) {
                    ++g_.rejected_;
                    break;
                }
                mark_field(farm->fields[index], 0);
                farm->fields.erase(farm->fields.begin() + static_cast<std::ptrdiff_t>(index));
                g_.buildings_changed_ = true;
                break;
            }
            case CommandType::UpgradeBuilding: {
                Building* b = g_.buildings_.get(c.entity);
                if (b == nullptr || b->owner != c.player || !complete(*b) || b->upgrading ||
                    def(*b).kind != BuildingKind::TownCenter || b->level >= def(*b).levels.size() ||
                    g_.population(c.player) < def(*b).levels[b->level].population) {
                    ++g_.rejected_;
                    break;
                }
                b->upgrading = true;
                g_.buildings_changed_ = true;
                break;
            }
            case CommandType::SetLimit: {
                Building* b = g_.buildings_.get(c.entity);
                if (b == nullptr || b->owner != c.player) {
                    ++g_.rejected_;
                    break;
                }
                b->limit = c.value;
                break;
            }
            case CommandType::RenameVillager: {
                Villager* v = g_.villagers_.get(c.entity);
                if (v == nullptr || v->owner != g_.town_of(c.player) || !valid_villager_name(c.text)) {
                    ++g_.rejected_;
                    break;
                }
                v->name = c.text;
                break;
            }
            case CommandType::MoveVillager: {
                Villager* v = g_.villagers_.get(c.entity);
                const Building* job = v != nullptr ? g_.buildings_.get(v->job) : nullptr;
                if (v == nullptr || v->owner != g_.town_of(c.player) || job == nullptr || !complete(*job) ||
                    def(*job).work != WorkKind::Explore) {
                    ++g_.rejected_;
                    break;
                }
                v_index_ = c.entity.index;
                const Fixed edge = Fixed::from_int(g_.map_.size - 1);
                order_scout(*v, {std::min(c.position.x, edge), std::min(c.position.z, edge)});
                break;
            }
            case CommandType::SetProduction: {
                Building* b = g_.buildings_.get(c.entity);
                if (b == nullptr || b->owner != g_.town_of(c.player) || def(*b).workers <= 0) {
                    ++g_.rejected_;
                    break;
                }
                b->stopped = c.value == 0;
                g_.buildings_changed_ = true;
                break;
            }
            case CommandType::Trade: trade_with_merchant(c); break;
            case CommandType::TrainUnit: {
                Building* b = g_.buildings_.get(c.entity);
                const std::uint8_t town = g_.town_of(c.player);
                if (b == nullptr || b->owner != town || !def(*b).trains || !complete(*b) ||
                    (c.value == 1 && (c.def >= c_.units.size() || c_.units[c.def].tier > g_.tier(town) ||
                                      b->training.size() >= 10)) ||
                    (c.value == 0 && b->training.empty())) {
                    ++g_.rejected_;
                    break;
                }
                if (c.value == 1) {
                    b->training.push_back(c.def);
                } else {
                    b->training.pop_back();
                    if (b->training.empty()) {
                        b->train_progress = 0;
                    }
                }
                break;
            }
            case CommandType::ArmyOrder: {
                const std::uint8_t town = g_.town_of(c.player);
                PlayerState& ps = g_.players_[town];
                const auto order = static_cast<ArmyOrderKind>(c.value);
                const auto enemy = static_cast<std::uint8_t>(c.count);  // Below kMaxPlayers: checked when read.
                if (order == ArmyOrderKind::Attack &&
                    (!g_.enemies(town, enemy) || g_.buildings_.get(g_.players_[enemy].town_center) == nullptr)) {
                    ++g_.rejected_;
                    break;
                }
                ps.order = order;
                if (order == ArmyOrderKind::Defend) {
                    ps.rally = c.position;
                } else if (order == ArmyOrderKind::Attack) {
                    ps.enemy = enemy;
                }
                // The soldiers heed it at once.
                for (Creature& a : g_.creatures_.data()) {
                    if (a.kind == CreatureKind::Soldier && a.town == town && a.state != CreatureState::Travel) {
                        a.state = CreatureState::Wander;
                        a.target = {};
                        a.path.clear();
                        a.path_index = 0;
                    }
                }
                break;
            }
            case CommandType::DevSpawn: {
                const std::uint8_t town = g_.town_of(c.player);
                const Building* tc = g_.buildings_.get(g_.players_[town].town_center);
                if (!g_.dev_commands_ || tc == nullptr) {
                    ++g_.rejected_;
                    break;
                }
                const FixedVec2 at = g_.door(*tc);
                for (std::int32_t n = 0; n < c.value; ++n) {
                    const std::uint32_t family = n % 2 == 0 ? g_.players_[town].next_family++ : g_.players_[town].next_family - 1;
                    const FixedVec2 spot{at.x + Fixed::from_int(static_cast<std::int32_t>(g_.rng_.below(9)) - 4),
                                         at.z - Fixed::from_int(2 + static_cast<std::int32_t>(g_.rng_.below(4)))};
                    (void)spawn_villager(town, spot, n % 2 == 0 ? Sex::Male : Sex::Female,
                                         18 + static_cast<std::int32_t>(g_.rng_.below(20)), family, newcomer_race(town));
                }
                break;
            }
            case CommandType::DevLevel: {
                Building* tc = g_.buildings_.get(g_.players_[g_.town_of(c.player)].town_center);
                if (!g_.dev_commands_ || tc == nullptr || tc->level >= def(*tc).levels.size()) {
                    ++g_.rejected_;
                    break;
                }
                ++tc->level;
                tc->upgrading = false;
                g_.buildings_changed_ = true;
                break;
            }
            case CommandType::DevRaid:
                if (!g_.dev_commands_ || !g_.players_[g_.town_of(c.player)].town_center.valid()) {
                    ++g_.rejected_;
                    break;
                }
                start_raid(g_.town_of(c.player), std::max(100, threat_percent(g_.rules_.raiders)));
                break;
            case CommandType::RingBell: {
                const std::uint8_t town = g_.town_of(c.player);
                PlayerState& ps = g_.players_[town];
                ps.alarm = c.value == 1;
                // Everybody drops what they do and heeds it.
                for (Villager& v : g_.villagers_.data()) {
                    if (v.owner == town && (v.task == Task::Wander || v.task == Task::Gather || v.task == Task::GoGather ||
                                            v.task == Task::Produce || v.task == Task::GoWorkplace || v.task == Task::Farm ||
                                            v.task == Task::GoField || v.task == Task::Fight || v.task == Task::GoFight)) {
                        release(v);
                        v.task = Task::Idle;
                        v.path.clear();
                        v.path_index = 0;
                        v.idle_ticks = 0;
                    }
                }
                break;
            }
            case CommandType::OfferTrade: offer_trade(c); break;
            case CommandType::SetTradeRule: set_trade_rule(c); break;
            case CommandType::AnswerOffer: answer_offer(c); break;
            case CommandType::DevFeature: {
                const auto type = static_cast<FeatureType>(c.def);
                const std::int32_t x = c.position.x.floor_int();
                const std::int32_t z = c.position.z.floor_int();
                const bool tree = type == FeatureType::Tree;
                if (!g_.dev_commands_ || c.def >= static_cast<std::uint16_t>(FeatureType::Count) || x >= g_.map_.size ||
                    z >= g_.map_.size || g_.map_.features.size() >= kMaxMapFeatures ||
                    (tree && (c.def2 >= c_.flora.species.size() || c.count >= kTreeSizes))) {
                    ++g_.rejected_;
                    break;
                }
                MapFeature f;
                f.type = type;
                f.species = tree ? static_cast<std::uint8_t>(c.def2) : std::uint8_t{0};
                f.size = tree ? static_cast<std::uint8_t>(c.count) : std::uint8_t{0};
                f.rotation = static_cast<std::uint16_t>(c.value2);
                f.x = c.position.x;
                f.z = c.position.z;
                f.scale = Fixed::from_raw(c.value);
                // A resource like any other: with its node, and where gatherers look.
                Node node;
                if (tree) {
                    node.amount = c_.flora.species[f.species].logs[f.size];
                } else if (const FeatureDef* fd = c_.feature(type)) {
                    node.amount = std::max(1, (fd->amount * f.scale.raw()) >> 16);
                }
                const auto index = static_cast<std::uint32_t>(g_.map_.features.size());
                g_.map_.features.push_back(f);
                g_.nodes_.push_back(node);
                const std::int32_t cx = std::clamp(x / kNodeCell, 0, g_.node_cells_side_ - 1);
                const std::int32_t cz = std::clamp(z / kNodeCell, 0, g_.node_cells_side_ - 1);
                g_.node_cells_[static_cast<std::size_t>(cz * g_.node_cells_side_ + cx)].push_back(index);
                g_.features_added_ = true;
                break;
            }
            case CommandType::DevIgnite: {
                Building* b = g_.buildings_.get(c.entity);
                if (!g_.dev_commands_ || b == nullptr || b->owner != c.player) {
                    ++g_.rejected_;
                    break;
                }
                ignite(*b, c.entity);
                break;
            }
            case CommandType::DevGrant: {
                Building* tc = g_.buildings_.get(g_.players_[c.player].town_center);
                if (!g_.dev_commands_ || tc == nullptr || c.def >= c_.resources.size() || c.value < 1 ||
                    c.value > kMaxDevGrant) {
                    ++g_.rejected_;
                    break;
                }
                add_to(tc->stock, c.def, c.value);
                break;
            }
            default:
                ++g_.rejected_;
                break;
        }
    }

    void setup(std::uint8_t players) {
        const auto towns = static_cast<std::uint8_t>(g_.map_.starts.size());
        // A common town has room for every seat, so anyone can join later.
        g_.player_count_ = g_.shared_town_ ? kMaxPlayers : std::min<std::uint8_t>(players, towns);
        for (std::size_t z = 0; z < g_.zone_animals_.size(); ++z) {
            if (!g_.zone_open(z)) {
                g_.zone_animals_[z] = 0;
            }
            for (std::int32_t n = 0; n < g_.zone_animals_[z]; ++n) {
                spawn_animal(z);
            }
        }
        DefIndex tc_def = kNoDef;
        for (std::size_t i = 0; i < c_.buildings.size(); ++i) {
            if (c_.buildings[i].kind == BuildingKind::TownCenter && tc_def == kNoDef) {
                tc_def = static_cast<DefIndex>(i);
            }
        }
        for (std::uint8_t p = 0; p < g_.player_count_; ++p) {
            PlayerState& ps = g_.players_[p];
            ps.active = true;
            if (tc_def == kNoDef || p >= towns || g_.town_of(p) != p) {
                continue;  // The common town is player 0's.
            }
            const StartPosition& s = g_.map_.starts[p];
            std::int32_t w = 0, d = 0;
            Game::footprint(c_.buildings[tc_def], 0, w, d);
            const std::int32_t x = s.x.floor_int() - w / 2;
            const std::int32_t z = s.z.floor_int() - d / 2;
            ps.town_center = add_building(p, tc_def, x, z, 0, true);
            Building* tc = g_.buildings_.get(ps.town_center);
            if (tc == nullptr) {
                continue;
            }
            // Starting goods.
            const struct {
                const char* id;
                std::int32_t amount;
            } kStart[] = {{"core:log", 60},   {"core:stone", 20},    {"core:berries", 150},
                          {"core:roots", 40}, {"core:firewood", 40}, {"core:clothes", 12}};
            const std::int32_t percent = g_.rules_.start == StartGoods::Scarce   ? 50
                                         : g_.rules_.start == StartGoods::Plenty ? 200
                                                                                 : 100;
            for (const auto& item : kStart) {
                const DefIndex r = c_.find_resource(item.id);
                if (r != kNoDef) {
                    add_to(tc->stock, r, item.amount * percent / 100);
                }
            }
            if (g_.gold_ != kNoDef) {
                add_to(tc->stock, g_.gold_, kStartGold * percent / 100);
            }
            // Five couples and two children.
            const FixedVec2 at = g_.door(*tc);
            const std::uint8_t start_race = g_.rules_.races[p % g_.rules_.races.size()];
            const auto races = static_cast<std::uint8_t>(std::max<std::size_t>(1, c_.races.size()));
            for (std::int32_t n = 0; n < 5; ++n) {
                const std::uint32_t family = ps.next_family++;
                const std::uint8_t race = start_race == kMixedRace || start_race >= races
                                              ? static_cast<std::uint8_t>(n % races)
                                              : start_race;
                const FixedVec2 spot{at.x + Fixed::from_int(n * 2 - 4), at.z - Fixed::from_int(2)};  // Outside, past the door.
                (void)spawn_villager(p, spot, Sex::Male, 20 + static_cast<std::int32_t>(g_.rng_.below(12)), family, race);
                (void)spawn_villager(p, spot, Sex::Female, 19 + static_cast<std::int32_t>(g_.rng_.below(12)), family, race);
                if (n < 2) {
                    (void)spawn_villager(p, spot, g_.rng_.below(2) == 0 ? Sex::Male : Sex::Female,
                                         1 + static_cast<std::int32_t>(g_.rng_.below(3)), family, race);
                }
            }
        }
    }

    std::uint32_t v_index_ = 0;   // Entity index of the villager being updated.
    bool movers_counted_ = false;
    std::uint32_t no_gold_work_ = 0;  // Bit per town.
    std::array<std::int32_t, kMaxPlayers> movers_{};

private:
    Game& g_;
    const Content& c_;
};

// --- Game ---------------------------------------------------------------------

Game::Game(std::shared_ptr<const Content> content, MapData map, std::uint8_t players, std::uint64_t seed,
           bool shared_town)
    : Game(std::move(content), std::move(map), GameSetup{players, seed, shared_town, GameRules{}}) {}

Game::Game(std::shared_ptr<const Content> content, MapData map, const GameSetup& setup)
    : content_(std::move(content)),
      map_(std::move(map)),
      seed_(setup.seed),
      rng_(setup.seed, 21),
      shared_town_(setup.shared_town),
      rules_(setup.rules) {
    const std::uint8_t players = setup.players;
    firewood_ = content_->find_resource("core:firewood");
    clothes_ = content_->find_resource("core:clothes");
    fertilizer_ = content_->find_resource("core:fertilizer");
    meat_ = content_->find_resource("core:meat");
    hide_ = content_->find_resource("core:hide");
    fish_ = content_->find_resource("core:fish");
    shoes_ = content_->find_resource("core:shoes");
    gold_ = content_->find_resource("core:gold");
    zone_animals_.resize(map_.zones.size());
    for (std::size_t z = 0; z < map_.zones.size(); ++z) {
        zone_animals_[z] = VillageRules::zone_capacity(map_.zones[z].type, rules_);
    }
    temperature_ = sim::temperature(rules_.climate, seed_, 0);
    build_indexes();
    nodes_.assign(map_.features.size(), Node{});
    for (std::size_t i = 0; i < map_.features.size(); ++i) {
        const MapFeature& f = map_.features[i];
        if (f.type == FeatureType::Tree) {
            if (f.species < content_->flora.species.size() && f.size < kTreeSizes) {
                nodes_[i].amount = content_->flora.species[f.species].logs[f.size];
            }
        } else if (const FeatureDef* fd = content_->feature(f.type)) {
            nodes_[i].amount = std::max(1, (fd->amount * f.scale.raw()) >> 16);
        }
    }
    VillageRules(*this).setup(players);
    // Players of a common town share its town center.
    for (std::uint8_t p = 1; p < player_count_ && shared_town_; ++p) {
        players_[p].town_center = players_[0].town_center;
    }
    // What each town sees from the start (phase 32).
    if (fog()) {
        vision_.reset(map_.size, vision_groups());
        vision_.set_all_explored(rules_.fog == FogMode::Revealed);
        update_vision();
    }
    buildings_changed_ = true;
}

void Game::build_indexes() {
    nav_.build(map_);
    occupied_.assign(static_cast<std::size_t>(map_.size) * static_cast<std::size_t>(map_.size), 0);
    node_cells_side_ = (map_.size + kNodeCell - 1) / kNodeCell;
    node_cells_.assign(static_cast<std::size_t>(node_cells_side_) * static_cast<std::size_t>(node_cells_side_), {});
    for (std::size_t i = 0; i < map_.features.size(); ++i) {
        const MapFeature& f = map_.features[i];
        const std::int32_t cx = std::clamp(f.x.floor_int() / kNodeCell, 0, node_cells_side_ - 1);
        const std::int32_t cz = std::clamp(f.z.floor_int() / kNodeCell, 0, node_cells_side_ - 1);
        node_cells_[static_cast<std::size_t>(cz * node_cells_side_ + cx)].push_back(static_cast<std::uint32_t>(i));
    }
}

void Game::apply(const Command& command) {
    goods_changed();
    VillageRules(*this).apply(command);
    goods_changed();
}

void Game::step() {
    goods_changed();
    if (night()) {
        update_light();
    }
    VillageRules(*this).step();
    goods_changed();
    // The fog lifts once a second, where anybody's people are (phase 32).
    if (vision_.active() && tick_ % kTicksPerSecond == 0) {
        update_vision();
    }
}

std::uint8_t Game::town_group(std::uint8_t town) const {
    // Allies (every town in a cooperative game) share what they see.
    if (rules_.shared_vision && !rules_.versus) {
        return 0;
    }
    return static_cast<std::uint8_t>(town % kVisionGroups);
}

std::uint16_t Game::vision_groups() const {
    std::uint16_t groups = 0;
    for (std::uint8_t p = 0; p < player_count_; ++p) {
        groups = static_cast<std::uint16_t>(groups | (1u << vision_group(p)));
    }
    return groups;
}

std::int32_t Game::sight(const Building& b) const {
    // From the middle, so the whole footprint is inside.
    return content_->buildings[b.def].sight + std::max(b.width, b.depth) / 2;
}

std::int32_t Game::light(const Building& b) const {
    if (b.state != BuildingState::Complete) {
        return 0;
    }
    const BuildingDef& d = content_->buildings[b.def];
    if (d.light > 0) {
        // A campfire gives light while it burns.
        return d.warmth > 0 && !b.heated ? 0 : d.light;
    }
    if (b.residents.empty() && (b.workers.empty() || b.stopped)) {
        return 0;
    }
    return village::kOccupiedLight + std::max(b.width, b.depth) / 2;
}

void Game::update_light() {
    // What the lights are now, in a number: the cells are drawn again only
    // when it changes. A pure function of the buildings, so a loaded game
    // and a running one agree.
    std::uint64_t signature = 0xCBF29CE484222325ull;
    const auto mix = [&signature](std::uint64_t v) {
        signature = (signature ^ v) * 0x100000001B3ull;
    };
    for (const Building& b : buildings_.data()) {
        if (const std::int32_t radius = light(b); radius > 0) {
            mix(static_cast<std::uint64_t>(b.x + b.width / 2));
            mix(static_cast<std::uint64_t>(b.z + b.depth / 2));
            mix(static_cast<std::uint64_t>(radius));
        }
    }
    signature |= 1;  // Never 0, which means "not drawn yet".
    if (signature == light_signature_) {
        return;
    }
    light_signature_ = signature;
    light_side_ = (map_.size + village::kLightCell - 1) / village::kLightCell;
    light_cells_.assign(static_cast<std::size_t>(light_side_) * static_cast<std::size_t>(light_side_), 0);
    for (const Building& b : buildings_.data()) {
        const std::int32_t radius = light(b);
        if (radius <= 0) {
            continue;
        }
        const std::int32_t cx = b.x + b.width / 2;
        const std::int32_t cz = b.z + b.depth / 2;
        const std::int32_t x0 = std::max(0, (cx - radius) / village::kLightCell);
        const std::int32_t x1 = std::min(light_side_ - 1, (cx + radius) / village::kLightCell);
        const std::int32_t z0 = std::max(0, (cz - radius) / village::kLightCell);
        const std::int32_t z1 = std::min(light_side_ - 1, (cz + radius) / village::kLightCell);
        for (std::int32_t z = z0; z <= z1; ++z) {
            for (std::int32_t x = x0; x <= x1; ++x) {
                // By the middle of the cell.
                const std::int64_t dx = x * village::kLightCell + village::kLightCell / 2 - cx;
                const std::int64_t dz = z * village::kLightCell + village::kLightCell / 2 - cz;
                if (dx * dx + dz * dz <= static_cast<std::int64_t>(radius) * radius) {
                    light_cells_[static_cast<std::size_t>(z) * static_cast<std::size_t>(light_side_) +
                                 static_cast<std::size_t>(x)] = 1;
                }
            }
        }
    }
}

bool Game::lit(std::int32_t x, std::int32_t z) const {
    if (light_side_ == 0 || x < 0 || z < 0) {
        return false;
    }
    const std::int32_t cx = x / village::kLightCell;
    const std::int32_t cz = z / village::kLightCell;
    return cx < light_side_ && cz < light_side_ &&
           light_cells_[static_cast<std::size_t>(cz) * static_cast<std::size_t>(light_side_) +
                        static_cast<std::size_t>(cx)] != 0;
}

bool Game::in_the_dark(const Villager& v) const {
    if (!night()) {
        return false;
    }
    if (v.race < content_->races.size() && content_->races[v.race].night_vision) {
        return false;
    }
    return !lit(v.position.x.floor_int(), v.position.z.floor_int());
}

std::int32_t Game::sight(const Villager& v) const {
    std::int32_t own = v.race < content_->races.size() ? content_->races[v.race].sight : 12;
    // An explorer sees as far as its building says (phase 66).
    if (const Building* job = buildings_.get(v.job)) {
        own = std::max(own, content_->buildings[job->def].worker_sight);
    }
    return own;
}

std::int32_t Game::sight(const Creature& a) const {
    if (a.kind != CreatureKind::Soldier || a.state == CreatureState::Travel) {
        return 0;  // Animals and raiders give nobody sight; soldiers away on the world map neither.
    }
    return a.unit < content_->units.size() ? content_->units[a.unit].sight : 16;
}

void Game::update_vision() {
    if (!vision_.active()) {
        return;
    }
    // Dynamic fog also notes what is in sight now, for the ghosts.
    const bool dynamic = fog_is_dynamic(rules_.fog);
    if (dynamic) {
        vision_.begin_sight();
    }
    for (const Building& b : buildings_.data()) {
        vision_.reveal(town_group(b.owner), b.x + b.width / 2, b.z + b.depth / 2, sight(b), dynamic);
    }
    for (const Villager& v : villagers_.data()) {
        vision_.reveal(town_group(v.owner), v.position.x.floor_int(), v.position.z.floor_int(), sight(v), dynamic);
    }
    for (const Creature& a : creatures_.data()) {
        if (const std::int32_t r = sight(a); r > 0) {
            vision_.reveal(town_group(a.town), a.position.x.floor_int(), a.position.z.floor_int(), r, dynamic);
        }
    }
    if (dynamic) {
        update_ghosts();
    }
}

void Game::update_ghosts() {
    // Each group remembers the buildings of others it sees now, and forgets
    // those whose place it sees empty (phase 33).
    for (std::uint8_t g = 0; g < kVisionGroups; ++g) {
        if (!vision_.used(g)) {
            continue;
        }
        for (std::size_t k = 0; k < buildings_.size(); ++k) {
            const Building& b = buildings_.data()[k];
            if (town_group(b.owner) == g || !vision_.sees(g, b.x, b.z, b.width, b.depth)) {
                continue;
            }
            const BuildingDef& d = content_->buildings[b.def];
            BuildingGhost h;
            h.id = buildings_.entities()[k];
            h.def = b.def;
            h.owner = b.owner;
            h.rotation = b.rotation;
            h.level = b.level;
            h.burning = b.fire > 0;
            h.x = b.x;
            h.z = b.z;
            h.progress = b.state == BuildingState::Complete || d.build_work <= 0
                             ? std::int16_t{1000}
                             : static_cast<std::int16_t>(std::clamp(b.work_done * 1000 / d.build_work, 0, 1000));
            h.burned = static_cast<std::int16_t>(std::clamp(b.burned, 0, 1000));
            vision_.remember(g, h);
        }
        const std::vector<BuildingGhost> ghosts = vision_.ghosts(g);
        for (const BuildingGhost& h : ghosts) {
            if (buildings_.get(h.id) != nullptr || h.def >= content_->buildings.size()) {
                continue;
            }
            std::int32_t w = 0, d = 0;
            footprint(content_->buildings[h.def], h.rotation, w, d);
            if (vision_.sees(g, h.x, h.z, w, d)) {
                vision_.forget(g, h.id);
            }
        }
    }
}

void Game::footprint(const BuildingDef& def, std::uint8_t rotation, std::int32_t& w, std::int32_t& d) {
    const bool turned = (rotation & 1u) != 0;
    w = turned ? def.depth : def.width;
    d = turned ? def.width : def.depth;
}

FixedVec2 Game::door(const Building& b) const {
    // The door faces -Z in the model; rotations turn it a quarter each.
    const Fixed cx = Fixed::from_int(b.x) + Fixed::from_ratio(b.width, 2);
    const Fixed cz = Fixed::from_int(b.z) + Fixed::from_ratio(b.depth, 2);
    switch (b.rotation & 3u) {
        case 0: return {cx, Fixed::from_int(b.z) - Fixed::one()};
        case 1: return {Fixed::from_int(b.x + b.width) + Fixed::one(), cz};
        case 2: return {cx, Fixed::from_int(b.z + b.depth) + Fixed::one()};
        default: return {Fixed::from_int(b.x) - Fixed::one(), cz};
    }
}

FixedVec2 Game::approach(const Building& b, FixedVec2 from) const {
    // The closest point of a ring one meter around the footprint: every
    // side works as a way in, so a cliff behind the door is no detour.
    const Fixed x0 = Fixed::from_int(b.x - 1);
    const Fixed z0 = Fixed::from_int(b.z - 1);
    const Fixed x1 = Fixed::from_int(b.x + b.width + 1);
    const Fixed z1 = Fixed::from_int(b.z + b.depth + 1);
    const bool inside = from.x > x0 && from.x < x1 && from.z > z0 && from.z < z1;
    if (inside) {
        return door(b);
    }
    return {std::clamp(from.x, x0, x1), std::clamp(from.z, z0, z1)};
}

PlaceError Game::can_place(std::uint8_t player, DefIndex def_index, std::int32_t x, std::int32_t z,
                           std::uint8_t rotation) const {
    if (def_index >= content_->buildings.size()) {
        return PlaceError::UnknownBuilding;
    }
    const BuildingDef& d = content_->buildings[def_index];
    if (d.tier > tier(player)) {
        return PlaceError::Locked;
    }
    if (d.kind == BuildingKind::TownCenter || d.unique) {
        for (std::size_t i = 0; i < buildings_.size(); ++i) {
            const Building& b = buildings_.data()[i];
            if (b.owner == player && b.def == def_index) {
                return PlaceError::Unique;
            }
        }
    }
    std::int32_t w = 0, dp = 0;
    footprint(d, rotation, w, dp);
    constexpr std::int32_t kMargin = 4;
    if (x < kMargin || z < kMargin || x + w > map_.size - kMargin || z + dp > map_.size - kMargin) {
        return PlaceError::OutsideMap;
    }
    if (map_.region_size() > 0) {
        const Region r = region(town_of(player));
        if (x < r.x + kMargin || z < r.z + kMargin || x + w > r.x + r.size - kMargin || z + dp > r.z + r.size - kMargin) {
            return PlaceError::OutsideMap;
        }
    }
    if (vision_.active() && !vision_.explored_rect(vision_group(player), x, z, w, dp)) {
        return PlaceError::Unexplored;  // Decision D-3203.
    }
    std::int32_t lo = 65535, hi = 0;
    for (std::int32_t cz = z; cz < z + dp; ++cz) {
        for (std::int32_t cx = x; cx < x + w; ++cx) {
            if (occupied_[static_cast<std::size_t>(cz) * static_cast<std::size_t>(map_.size) + static_cast<std::size_t>(cx)] != 0) {
                return PlaceError::Blocked;
            }
            if (map_.water_at(cx, cz)) {
                return PlaceError::Water;
            }
        }
    }
    for (std::int32_t vz = z; vz <= z + dp; vz += 1) {
        for (std::int32_t vx = x; vx <= x + w; vx += 1) {
            const std::int32_t h = map_.height_cm(vx, vz);
            lo = std::min(lo, h);
            hi = std::max(hi, h);
        }
    }
    const bool on_ground = follows_ground(d);
    if (hi - lo > (on_ground ? kMaxWallSlopeCm : kMaxSlopeCm)) {
        return PlaceError::TooSteep;
    }
    // Its floor is level with the ground at the door. Downhill the
    // foundations show; uphill the ground may bury the walls only so far.
    if (!on_ground && hi - floor_cm(x, z, w, dp, rotation) > kMaxBuriedCm) {
        return PlaceError::DoorBelow;
    }
    // Not where nobody of the town could ever come to build it.
    if (d.kind != BuildingKind::TownCenter && !site_reachable(town_of(player), x, z, w, dp)) {
        return PlaceError::Unreachable;
    }
    return PlaceError::None;
}

std::int32_t Game::floor_cm(std::int32_t x, std::int32_t z, std::int32_t w, std::int32_t d, std::uint8_t rotation) const {
    // The door faces -Z in the model; rotations turn it a quarter each.
    switch (rotation & 3u) {
        case 0: return map_.height_cm(x + w / 2, z);
        case 1: return map_.height_cm(x + w, z + d / 2);
        case 2: return map_.height_cm(x + w / 2, z + d);
        default: return map_.height_cm(x, z + d / 2);
    }
}

bool Game::site_reachable(std::uint8_t town, std::int32_t x, std::int32_t z, std::int32_t w, std::int32_t d) const {
    if (town >= kMaxPlayers) {
        return false;
    }
    const Building* center = buildings_.get(players_[town].town_center);
    if (center == nullptr) {
        return true;
    }
    const FixedVec2 home = door(*center);
    const Fixed cx = Fixed::from_int(x) + Fixed::from_ratio(w, 2);
    const Fixed cz = Fixed::from_int(z) + Fixed::from_ratio(d, 2);
    // One meter out from the middle of each side: any of them is a way in.
    const FixedVec2 sides[4] = {{cx, Fixed::from_int(z - 1)},
                                {Fixed::from_int(x + w + 1), cz},
                                {cx, Fixed::from_int(z + d + 1)},
                                {Fixed::from_int(x - 1), cz}};
    for (const FixedVec2& side : sides) {
        if (nav_.connected(side, home)) {
            return true;
        }
    }
    return false;
}

PlaceError Game::can_place_field(std::uint8_t player, EntityId farm_id, std::int32_t x, std::int32_t z, std::int32_t w,
                                 std::int32_t d) const {
    const Building* farm = buildings_.get(farm_id);
    if (farm == nullptr || farm->owner != town_of(player)) {
        return PlaceError::NotYours;
    }
    const BuildingDef& fd = content_->buildings[farm->def];
    if (fd.work != WorkKind::Farm) {
        return PlaceError::UnknownBuilding;
    }
    if (static_cast<std::int32_t>(farm->fields.size()) >= fd.fields) {
        return PlaceError::TooMany;
    }
    if (w < kMinFieldSide || d < kMinFieldSide || w > kMaxFieldSide || d > kMaxFieldSide) {
        return PlaceError::BadSize;
    }
    constexpr std::int32_t kMargin = 4;
    if (x < kMargin || z < kMargin || x + w > map_.size - kMargin || z + d > map_.size - kMargin) {
        return PlaceError::OutsideMap;
    }
    // Its center within the farm's reach.
    const std::int64_t dx = (x + w / 2) - (farm->x + farm->width / 2);
    const std::int64_t dz = (z + d / 2) - (farm->z + farm->depth / 2);
    if (dx * dx + dz * dz > static_cast<std::int64_t>(fd.work_radius) * fd.work_radius) {
        return PlaceError::TooFar;
    }
    if (vision_.active() && !vision_.explored_rect(vision_group(player), x, z, w, d)) {
        return PlaceError::Unexplored;
    }
    std::int32_t lo = 65535, hi = 0;
    for (std::int32_t cz = z; cz < z + d; ++cz) {
        for (std::int32_t cx = x; cx < x + w; ++cx) {
            if (occupied_[static_cast<std::size_t>(cz) * static_cast<std::size_t>(map_.size) + static_cast<std::size_t>(cx)] != 0) {
                return PlaceError::Blocked;
            }
            if (map_.water_at(cx, cz)) {
                return PlaceError::Water;
            }
            const std::int32_t h = map_.height_cm(cx, cz);
            lo = std::min(lo, h);
            hi = std::max(hi, h);
        }
    }
    if (hi - lo > 300) {
        return PlaceError::TooSteep;
    }
    // Its farmers must be able to walk to it.
    const FixedVec2 middle{Fixed::from_int(x) + Fixed::from_ratio(w, 2), Fixed::from_int(z) + Fixed::from_ratio(d, 2)};
    if (!nav_.connected(middle, door(*farm))) {
        return PlaceError::Unreachable;
    }
    return PlaceError::None;
}

std::int32_t Game::desirability_at(FixedVec2 here, const Building* self) const {
    std::int32_t beauty = 0;
    for (const Building& o : buildings_.data()) {
        const std::int32_t des = content_->buildings[o.def].desirability;
        if (des == 0 || &o == self) {
            continue;
        }
        const FixedVec2 c{Fixed::from_int(o.x) + Fixed::from_ratio(o.width, 2), Fixed::from_int(o.z) + Fixed::from_ratio(o.depth, 2)};
        const std::uint64_t d2 = distance2(here, c);
        if (d2 < (static_cast<std::uint64_t>(30 * 30) << 32)) {
            const auto dist = static_cast<std::int32_t>(isqrt(d2 >> 32));
            beauty += des * (30 - dist) / 30;
        }
    }
    std::int32_t trees = 0;
    const std::int32_t side = node_cells_side_;
    const std::int32_t cx = here.x.floor_int() / kNodeCell;
    const std::int32_t cz = here.z.floor_int() / kNodeCell;
    for (std::int32_t z = std::max(0, cz - 1); z <= std::min(side - 1, cz + 1); ++z) {
        for (std::int32_t x = std::max(0, cx - 1); x <= std::min(side - 1, cx + 1); ++x) {
            for (const std::uint32_t i : node_cells_[static_cast<std::size_t>(z * side + x)]) {
                const MapFeature& f = map_.features[i];
                if (f.type == FeatureType::Tree && nodes_[i].amount > 0 &&
                    distance2(here, {f.x, f.z}) < (static_cast<std::uint64_t>(16 * 16) << 32)) {
                    ++trees;
                }
            }
        }
    }
    return beauty + std::min(trees, 8);
}

bool Game::zone_open(std::size_t z) const {
    const Zone& zone = map_.zones[z];
    if (zone.type != ZoneType::Wolves && zone.type != ZoneType::Bears) {
        return true;
    }
    // No dens right by a starting town.
    for (const StartPosition& s : map_.starts) {
        const std::int64_t dx = (s.x - zone.x).floor_int();
        const std::int64_t dz = (s.z - zone.z).floor_int();
        if (dx * dx + dz * dz < 150 * 150) {
            return false;
        }
    }
    return true;
}

const std::vector<EntityId>& Game::owned(std::uint8_t town) const {
    if (owned_dirty_) {
        for (auto& list : owned_) {
            list.clear();
        }
        for (std::size_t i = 0; i < buildings_.size(); ++i) {
            const std::uint8_t o = buildings_.data()[i].owner;
            if (o < kMaxPlayers) {
                owned_[o].push_back(buildings_.entities()[i]);
            }
        }
        owned_dirty_ = false;
    }
    static const std::vector<EntityId> kNone;
    return town < kMaxPlayers ? owned_[town] : kNone;
}

std::int32_t Game::soldiers(std::uint8_t player) const {
    std::int32_t n = 0;
    const std::uint8_t town = town_of(player);
    for (const Creature& a : creatures_.data()) {
        n += a.kind == CreatureKind::Soldier && a.town == town ? 1 : 0;
    }
    return n;
}

std::int32_t Game::military_power(std::uint8_t player) const {
    std::int32_t n = 0;
    const std::uint8_t town = town_of(player);
    for (const Creature& a : creatures_.data()) {
        if (a.kind == CreatureKind::Soldier && a.town == town && a.unit < content_->units.size()) {
            n += content_->units[a.unit].power;
        }
    }
    return n;
}

std::int32_t Game::score(std::uint8_t player) const {
    const std::uint8_t town = town_of(player);
    std::int64_t s = static_cast<std::int64_t>(population(town)) * 10 + static_cast<std::int64_t>(tier(town)) * 100 +
                     gold(town) / 10 + static_cast<std::int64_t>(military_power(town)) * 10;
    for (const Building& b : buildings_.data()) {
        s += b.owner == town && b.state == BuildingState::Complete ? 5 : 0;
    }
    return static_cast<std::int32_t>(std::min<std::int64_t>(s, INT32_MAX));
}

bool Game::enemies(std::uint8_t a, std::uint8_t b) const {
    return rules_.versus && rules_.pvp && a < player_count_ && b < player_count_ && town_of(a) != town_of(b);
}

std::int32_t Game::raiders_near(std::uint8_t player) const {
    std::int32_t n = 0;
    const std::uint8_t town = town_of(player);
    for (const Creature& a : creatures_.data()) {
        n += a.kind == CreatureKind::Raider && a.town == town && a.state != CreatureState::Leave ? 1 : 0;
    }
    return n;
}

std::int32_t Game::sick(std::uint8_t player) const {
    std::int32_t n = 0;
    const std::uint8_t town = town_of(player);
    for (const Villager& v : villagers_.data()) {
        n += v.owner == town && v.disease != 0 ? 1 : 0;
    }
    return n;
}

bool Game::merchant_here(std::uint8_t player) const {
    const PlayerState& ps = players_[town_of(player)];
    return ps.merchant_leaves != 0 && tick_ < ps.merchant_leaves;
}

std::uint64_t Game::travel_ticks(std::uint8_t from, std::uint8_t to) const {
    if (map_.region_size() > 0) {
        // The world map: squares apart, a day to load and five per square.
        const std::int32_t k = map_.size / map_.region_size();
        const std::int32_t dx = std::abs(from % k - to % k);
        const std::int32_t dz = std::abs(from / k - to / k);
        return static_cast<std::uint64_t>(day_ticks()) * static_cast<std::uint64_t>(1 + 5 * std::max(dx, dz));
    }
    // The same map: the road between the town centers at walking pace.
    const Building* a = buildings_.get(players_[from].town_center);
    const Building* b = buildings_.get(players_[to].town_center);
    if (a == nullptr || b == nullptr) {
        return day_ticks();
    }
    const std::int64_t dx = a->x - b->x;
    const std::int64_t dz = a->z - b->z;
    const std::uint64_t meters = isqrt(static_cast<std::uint64_t>(dx * dx + dz * dz));
    return day_ticks() + meters * kTicksPerSecond / 2;  // Carts at 2 m/s, like people.
}

std::int32_t Game::tradeable(std::uint8_t player, DefIndex resource) const {
    std::int32_t n = 0;
    const std::uint8_t town = town_of(player);
    for (const Building& b : buildings_.data()) {
        const BuildingDef& d = content_->buildings[b.def];
        if (b.owner == town && b.state == BuildingState::Complete && d.storage > 0 && (d.trade || gives_out(*content_, b, resource))) {
            n += amount_of(b.stock, resource);
        }
    }
    return n;
}

std::int32_t Game::gold(std::uint8_t player) const {
    return gold_ == kNoDef ? 0 : tradeable(player, gold_);
}

Game::GoldPlaces Game::gold_places(std::uint8_t player) const {
    GoldPlaces out;
    const std::uint8_t town = town_of(player);
    if (gold_ == kNoDef) {
        return out;
    }
    for (const Building& b : buildings_.data()) {
        const BuildingDef& d = content_->buildings[b.def];
        if (b.owner != town || b.state != BuildingState::Complete || d.storage <= 0) {
            continue;
        }
        const std::int32_t n = amount_of(b.stock, gold_);
        const bool keeps_gold = ((d.stores >> static_cast<unsigned>(ResourceCategory::Gold)) & 1u) != 0;
        if (d.trade) {
            out.post += n;
        } else if (d.kind == BuildingKind::Storage && keeps_gold) {
            out.vaults += n;
        } else {
            out.others += n;
        }
    }
    return out;
}

Game::Region Game::region(std::uint8_t player) const {
    const std::int32_t size = map_.region_size();
    if (size == 0) {
        return {0, 0, map_.size};
    }
    const std::int32_t k = map_.size / size;
    const std::int32_t p = town_of(player);
    return {(p % k) * size, (p / k) * size, size};
}

std::vector<Game::Event> Game::take_events() {
    std::vector<Event> out;
    out.swap(events_);
    return out;
}

std::int32_t Game::tier(std::uint8_t player) const {
    const Building* tc = buildings_.get(players_[town_of(player)].town_center);
    return tc == nullptr ? 1 : tc->level + 1;
}

std::int32_t Game::capacity(const Building& b) const {
    const BuildingDef& d = content_->buildings[b.def];
    if (b.level > 0 && b.level <= d.levels.size() && d.levels[b.level - 1u].residents > 0) {
        return d.levels[b.level - 1u].residents;
    }
    return d.residents;
}

std::int32_t Game::happiness(std::uint8_t player) const {
    const std::uint8_t town = town_of(player);
    std::int64_t sum = 0;
    std::int64_t people = 0;
    for (const Building& b : buildings_.data()) {
        if (b.owner == town && content_->buildings[b.def].kind == BuildingKind::House && !b.residents.empty()) {
            sum += static_cast<std::int64_t>(b.happiness) * static_cast<std::int64_t>(b.residents.size());
            people += static_cast<std::int64_t>(b.residents.size());
        }
    }
    const std::int64_t homeless = population(town) - people;
    sum += 25 * std::max<std::int64_t>(0, homeless);  // No home, less joy.
    people += std::max<std::int64_t>(0, homeless);
    return people == 0 ? 50 : static_cast<std::int32_t>(sum / people);
}

std::vector<std::int32_t> Game::stored(std::uint8_t player) const {
    // Within a tick the totals are counted once per player (decisions see
    // them as the tick began; the same on every machine).
    if (player < kMaxPlayers && (stored_valid_ >> player & 1u) != 0) {
        return stored_cache_[player];
    }
    std::vector<std::int32_t> out(content_->resources.size(), 0);
    for (std::size_t i = 0; i < buildings_.size(); ++i) {
        const Building& b = buildings_.data()[i];
        const BuildingDef& d = content_->buildings[b.def];
        if (b.owner != player || b.state != BuildingState::Complete || d.storage <= 0) {
            continue;
        }
        for (const Stock& s : b.stock) {
            if (s.resource < out.size() && gives_out(*content_, b, s.resource)) {
                out[s.resource] += s.amount;
            }
        }
    }
    if (player < kMaxPlayers) {
        stored_cache_[player] = out;
        stored_valid_ |= 1u << player;
    }
    return out;
}

std::int32_t Game::population(std::uint8_t player, bool adults_only) const {
    if (!adults_only && player < kMaxPlayers) {
        if (pop_dirty_) {
            pop_cache_.fill(0);
            for (const Villager& v : villagers_.data()) {
                if (v.owner < kMaxPlayers) {
                    ++pop_cache_[v.owner];
                }
            }
            pop_dirty_ = false;
        }
        return pop_cache_[player];
    }
    std::int32_t n = 0;
    for (const Villager& v : villagers_.data()) {
        if (v.owner == player && (!adults_only || adult(v))) {
            ++n;
        }
    }
    return n;
}

std::string Game::villager_name(const Villager& v) const {
    if (!v.name.empty()) {
        return v.name;
    }
    if (v.race >= content_->races.size()) {
        return {};
    }
    const RaceDef& race = content_->races[v.race];
    const bool female = v.sex == Sex::Female;
    const std::vector<std::string>& own = female ? race.names_female : race.names_male;
    const std::vector<std::string>& names = own.empty() ? (female ? race.names_male : race.names_female) : own;
    if (names.empty()) {
        return {};
    }
    // Its random bits, stirred so the name does not go with the looks.
    std::uint32_t h = v.appearance ^ 0x9E3779B9u;
    h ^= h >> 16;
    h *= 0x7FEB352Du;
    h ^= h >> 15;
    h *= 0x846CA68Bu;
    h ^= h >> 16;
    return names[h % names.size()];
}

std::int32_t Game::hunt_meat() const {
    return meat_ != kNoDef ? carry_capacity(*content_, meat_) : 0;
}

std::int32_t Game::hunt_hides() const {
    return hide_ != kNoDef ? 1 : 0;
}

std::int32_t Game::age_years(const Villager& v) const {
    const std::int64_t age = static_cast<std::int64_t>(tick_) - v.born_tick;
    return static_cast<std::int32_t>(std::max<std::int64_t>(0, age) / year_ticks());
}

bool Game::adult(const Villager& v) const {
    return age_years(v) >= village::kAdultAgeYears;
}

std::vector<std::uint32_t> Game::take_changed_nodes() {
    std::vector<std::uint32_t> out;
    out.swap(changed_nodes_);
    return out;
}

bool Game::take_buildings_changed() {
    const bool changed = buildings_changed_;
    buildings_changed_ = false;
    return changed;
}

// --- Saving --------------------------------------------------------------------

namespace {

void write_stocks(BinaryWriter& w, const std::vector<Stock>& list) {
    w.u32(static_cast<std::uint32_t>(list.size()));
    for (const Stock& s : list) {
        w.u16(s.resource);
        w.i32(s.amount);
    }
}

bool read_stocks(BinaryReader& r, std::vector<Stock>& out, std::size_t resources) {
    std::uint32_t n = 0;
    if (!r.count(256, 6, n)) {
        return false;
    }
    out.resize(n);
    for (Stock& s : out) {
        if (!r.u16(s.resource) || !r.i32(s.amount) || s.resource >= resources || s.amount < 0) {
            r.fail();
            return false;
        }
    }
    return true;
}

void write_ids(BinaryWriter& w, const std::vector<EntityId>& list) {
    w.u32(static_cast<std::uint32_t>(list.size()));
    for (const EntityId id : list) {
        w.u32(id.index);
        w.u32(id.generation);
    }
}

bool read_ids(BinaryReader& r, std::vector<EntityId>& out) {
    std::uint32_t n = 0;
    if (!r.count(1000, 8, n)) {
        return false;
    }
    out.resize(n);
    for (EntityId& id : out) {
        if (!r.u32(id.index) || !r.u32(id.generation)) {
            return false;
        }
    }
    return true;
}

void write_map(BinaryWriter& w, const MapData& m) {
    m.settings.write(w);
    w.u16(m.generator_version);
    w.i32(m.size);
    const auto u16s = [&](const std::vector<std::uint16_t>& v) {
        w.u32(static_cast<std::uint32_t>(v.size()));
        w.raw(std::span<const std::uint8_t>(reinterpret_cast<const std::uint8_t*>(v.data()), v.size() * 2));
    };
    const auto u8s = [&](const std::vector<std::uint8_t>& v) {
        w.u32(static_cast<std::uint32_t>(v.size()));
        w.raw(v);
    };
    u16s(m.heights);
    u16s(m.water);
    u8s(m.terrain);
    u8s(m.fertility);
    u8s(m.biome);
    w.u32(static_cast<std::uint32_t>(m.features.size()));
    for (const MapFeature& f : m.features) {
        w.u8(static_cast<std::uint8_t>(f.type));
        w.u8(f.species);
        w.u8(f.size);
        w.u16(f.rotation);
        w.fixed(f.x);
        w.fixed(f.z);
        w.fixed(f.scale);
    }
    w.u32(static_cast<std::uint32_t>(m.zones.size()));
    for (const Zone& z : m.zones) {
        w.u8(static_cast<std::uint8_t>(z.type));
        w.fixed(z.x);
        w.fixed(z.z);
        w.fixed(z.radius);
    }
    w.u32(static_cast<std::uint32_t>(m.starts.size()));
    for (const StartPosition& s : m.starts) {
        w.fixed(s.x);
        w.fixed(s.z);
    }
    w.u32(static_cast<std::uint32_t>(m.landforms.size()));
    for (const Landform& l : m.landforms) {
        w.u8(static_cast<std::uint8_t>(l.kind));
        w.i32(l.width);
        w.u32(static_cast<std::uint32_t>(l.points.size()));
        for (const auto& pt : l.points) {
            w.i32(pt[0]);
            w.i32(pt[1]);
        }
    }
    w.u32(static_cast<std::uint32_t>(m.sea_levels.size()));
    for (const std::uint16_t level : m.sea_levels) {
        w.u16(level);
    }
    u16s(m.region_owner);
    u16s(m.structure_owner);
    u16s(m.climate);
}

bool read_map(BinaryReader& r, MapData& m, const Content& c) {
    if (!MapSettings::read(r, m.settings) || !r.u16(m.generator_version) || !r.i32(m.size)) {
        return false;
    }
    if (m.size != world_cells(m.settings)) {
        r.fail();
        return false;
    }
    const std::size_t v = static_cast<std::size_t>(m.size + 1) * static_cast<std::size_t>(m.size + 1);
    const std::size_t cells = static_cast<std::size_t>(m.size) * static_cast<std::size_t>(m.size);
    const auto u16s = [&](std::vector<std::uint16_t>& out, std::size_t expected) {
        std::uint32_t n = 0;
        std::span<const std::uint8_t> bytes;
        if (!r.u32(n) || n != expected || !r.bytes(static_cast<std::size_t>(n) * 2, bytes)) {
            r.fail();
            return false;
        }
        out.resize(n);
        for (std::size_t i = 0; i < n; ++i) {
            out[i] = static_cast<std::uint16_t>(bytes[i * 2] | (bytes[i * 2 + 1] << 8));
        }
        return true;
    };
    const auto u8s = [&](std::vector<std::uint8_t>& out, std::size_t expected) {
        std::uint32_t n = 0;
        std::span<const std::uint8_t> bytes;
        if (!r.u32(n) || n != expected || !r.bytes(n, bytes)) {
            r.fail();
            return false;
        }
        out.assign(bytes.begin(), bytes.end());
        return true;
    };
    if (!u16s(m.heights, v) || !u16s(m.water, cells) || !u8s(m.terrain, cells) || !u8s(m.fertility, cells) ||
        !u8s(m.biome, cells)) {
        return false;
    }
    std::uint32_t n = 0;
    if (!r.count(kMaxMapFeatures, 16, n)) {
        return false;
    }
    m.features.resize(n);
    for (MapFeature& f : m.features) {
        std::uint8_t type = 0;
        if (!r.u8(type) || !r.u8(f.species) || !r.u8(f.size) || !r.u16(f.rotation) || !r.fixed(f.x) || !r.fixed(f.z) ||
            !r.fixed(f.scale) || type >= static_cast<std::uint8_t>(FeatureType::Count) || f.size >= kTreeSizes ||
            (type == 0 && f.species >= c.flora.species.size())) {
            r.fail();
            return false;
        }
        f.type = static_cast<FeatureType>(type);
    }
    if (!r.count(100000, 13, n)) {
        return false;
    }
    m.zones.resize(n);
    for (Zone& z : m.zones) {
        std::uint8_t type = 0;
        if (!r.u8(type) || !r.fixed(z.x) || !r.fixed(z.z) || !r.fixed(z.radius) || type >= static_cast<std::uint8_t>(ZoneType::Count)) {
            r.fail();
            return false;
        }
        z.type = static_cast<ZoneType>(type);
    }
    if (!r.count(kMaxPlayers, 8, n)) {
        return false;
    }
    m.starts.resize(n);
    for (StartPosition& s : m.starts) {
        if (!r.fixed(s.x) || !r.fixed(s.z)) {
            return false;
        }
    }
    // Landforms: points within a map's side of the map (a gulf's line may
    // start a little outside it).
    if (!r.count(kMaxLandforms, 9, n)) {
        return false;
    }
    m.landforms.resize(n);
    for (Landform& l : m.landforms) {
        std::uint8_t kind = 0;
        std::uint32_t points = 0;
        if (!r.u8(kind) || kind >= static_cast<std::uint8_t>(LandformKind::Count) || !r.i32(l.width) || l.width < 0 ||
            l.width > 2 * m.size || !r.count(kMaxLandformPoints, 8, points) || points == 0) {
            r.fail();
            return false;
        }
        l.kind = static_cast<LandformKind>(kind);
        l.points.resize(points);
        for (auto& pt : l.points) {
            if (!r.i32(pt[0]) || !r.i32(pt[1]) || pt[0] < -m.size || pt[1] < -m.size || pt[0] > 2 * m.size ||
                pt[1] > 2 * m.size) {
                r.fail();
                return false;
            }
        }
    }
    // None (a map made by hand) or one per region.
    const std::int32_t grid = world_grid(m.settings);
    if (!r.count(static_cast<std::uint32_t>(grid * grid), 2, n) || (n != 0 && n != static_cast<std::uint32_t>(grid * grid))) {
        r.fail();
        return false;
    }
    m.sea_levels.resize(n);
    for (std::uint16_t& level : m.sea_levels) {
        if (!r.u16(level)) {
            return false;
        }
    }
    // The hierarchical generator's owners: none, or one per square, each
    // naming a landform the map has.
    const std::size_t squares = static_cast<std::size_t>(m.owner_side()) * static_cast<std::size_t>(m.owner_side());
    for (std::vector<std::uint16_t>* owners : {&m.region_owner, &m.structure_owner}) {
        std::uint32_t count = 0;
        std::span<const std::uint8_t> bytes;
        if (!r.u32(count) || (count != 0 && count != squares) || !r.bytes(static_cast<std::size_t>(count) * 2, bytes)) {
            r.fail();
            return false;
        }
        owners->resize(count);
        for (std::size_t i = 0; i < count; ++i) {
            (*owners)[i] = static_cast<std::uint16_t>(bytes[i * 2] | (bytes[i * 2 + 1] << 8));
            if ((*owners)[i] > m.landforms.size()) {
                r.fail();
                return false;
            }
        }
    }
    // The climate of each square (phase 54): none, or temperature and
    // humidity from 0 to 100.
    std::uint32_t count = 0;
    std::span<const std::uint8_t> bytes;
    if (!r.u32(count) || (count != 0 && count != squares) || !r.bytes(static_cast<std::size_t>(count) * 2, bytes)) {
        r.fail();
        return false;
    }
    m.climate.resize(count);
    for (std::size_t i = 0; i < count; ++i) {
        if (bytes[i * 2] > 100 || bytes[i * 2 + 1] > 100) {
            r.fail();
            return false;
        }
        m.climate[i] = static_cast<std::uint16_t>(bytes[i * 2] | (bytes[i * 2 + 1] << 8));
    }
    return true;
}

// Where each part of the state starts in the written bytes.
struct Marks {
    std::size_t players = 0, registry = 0, nodes = 0, buildings = 0, villagers = 0, vision = 0;
};

void write_state(const Game& g, BinaryWriter& w, std::uint64_t seed, std::uint32_t rejected,
                 const std::vector<std::pair<std::uint64_t, std::uint32_t>>& regrow, Marks* marks = nullptr) {
    Marks m;
    w.u64(g.tick());
    w.u64(seed);
    w.u32(rejected);
    w.u8(g.dev_commands() ? 1 : 0);
    w.u8(g.shared_town() ? 1 : 0);
    g.rules().write(w);
    w.i32(g.snow());
    m.players = w.bytes().size();
    w.u8(g.player_count());
    for (std::uint8_t p = 0; p < g.player_count(); ++p) {
        const PlayerState& ps = g.player(p);
        w.u8(ps.active ? 1 : 0);
        w.u32(ps.town_center.index);
        w.u32(ps.town_center.generation);
        w.u32(ps.next_family);
        w.i32(ps.births);
        w.i32(ps.deaths);
        w.i32(ps.arrivals);
        w.i32(ps.departures);
        w.i32(ps.burned_down);
        w.u64(ps.merchant_arrives);
        w.u64(ps.merchant_leaves);
        w.u8(ps.alarm ? 1 : 0);
        w.u64(ps.next_raid);
        w.i32(ps.raids);
        w.u8(static_cast<std::uint8_t>(ps.order));
        w.vec2(ps.rally);
        w.u8(ps.enemy);
        w.u8(static_cast<std::uint8_t>(ps.outcome));
        w.u32(static_cast<std::uint32_t>(ps.merchant.size()));
        for (const MerchantGood& good : ps.merchant) {
            w.u16(good.resource);
            w.i32(good.stock);
            w.i32(good.buy);
            w.i32(good.sell);
        }
        w.u32(static_cast<std::uint32_t>(ps.trade_rules.size()));
        for (const TradeRule& rule : ps.trade_rules) {
            w.u16(rule.resource);
            w.i32(rule.sell_above);
            w.i32(rule.buy_below);
            w.u8(rule.sell_min);
            w.u8(rule.buy_max);
        }
        w.i32(ps.tally.sold);
        w.i32(ps.tally.sold_gold);
        w.i32(ps.tally.bought);
        w.i32(ps.tally.bought_gold);
    }
    w.u8(g.game_over() ? 1 : 0);
    w.u32(g.next_offer());
    w.u32(static_cast<std::uint32_t>(g.offers().size()));
    for (const TradeOffer& o : g.offers()) {
        w.u32(o.id);
        w.u8(o.from);
        w.u8(o.to);
        w.u16(o.give);
        w.i32(o.give_amount);
        w.u16(o.want);
        w.i32(o.want_amount);
        w.u64(o.expires);
    }
    w.u32(static_cast<std::uint32_t>(g.caravans().size()));
    for (const Caravan& c : g.caravans()) {
        w.u8(c.from);
        w.u8(c.to);
        w.u16(c.resource);
        w.i32(c.amount);
        w.u64(c.departs);
        w.u64(c.arrives);
    }
    m.registry = w.bytes().size();
    const EntityRegistry& reg = g.registry();
    w.u32(reg.slot_count());
    for (std::uint32_t i = 0; i < reg.slot_count(); ++i) {
        w.u32(reg.generations()[i]);
        w.u8(reg.alive_flags()[i]);
    }
    w.u32(static_cast<std::uint32_t>(reg.free_slots().size()));
    for (const std::uint32_t f : reg.free_slots()) {
        w.u32(f);
    }
    // Nodes: amounts, reservations and regrowth.
    m.nodes = w.bytes().size();
    w.u32(static_cast<std::uint32_t>(g.nodes().size()));
    for (const Node& n : g.nodes()) {
        w.i32(n.amount);
        w.u32(n.reserved);
        w.u64(n.regrow_tick);
    }
    w.u32(static_cast<std::uint32_t>(regrow.size()));
    for (const auto& [t, i] : regrow) {
        w.u64(t);
        w.u32(i);
    }
    w.u32(static_cast<std::uint32_t>(g.zone_animals().size()));
    for (const std::int32_t a : g.zone_animals()) {
        w.i32(a);
    }
    m.buildings = w.bytes().size();
    const auto& bs = g.buildings();
    w.u32(static_cast<std::uint32_t>(bs.size()));
    for (std::size_t i = 0; i < bs.size(); ++i) {
        const EntityId id = bs.entities()[i];
        const Building& b = bs.data()[i];
        w.u32(id.index);
        w.u32(id.generation);
        w.u16(b.def);
        w.u8(b.owner);
        w.u8(b.rotation);
        w.i32(b.x);
        w.i32(b.z);
        w.u8(static_cast<std::uint8_t>(b.state));
        w.u8(b.heated ? 1 : 0);
        write_stocks(w, b.delivered);
        write_stocks(w, b.incoming);
        w.i32(b.work_done);
        write_stocks(w, b.stock);
        write_ids(w, b.workers);
        w.i32(b.wanted_workers);
        write_ids(w, b.residents);
        w.i64(b.built_tick);
        w.u32(b.produced_year);
        w.i32(b.produced);
        w.u8(b.level);
        w.u8(b.upgrading ? 1 : 0);
        w.i32(b.limit);
        w.u8(b.recipe);
        w.u16(b.needs);
        w.i32(b.happiness);
        w.i32(b.desirability);
        w.i32(b.fire);
        w.i32(b.burned);
        w.i32(b.damage);
        w.i32(b.rearm);
        w.u32(static_cast<std::uint32_t>(b.training.size()));
        for (const DefIndex u : b.training) {
            w.u16(u);
        }
        w.i32(b.train_progress);
        w.u8(b.stopped ? 1 : 0);
        w.u32(static_cast<std::uint32_t>(b.fields.size()));
        for (const Field& f : b.fields) {
            w.i32(f.x);
            w.i32(f.z);
            w.i32(f.w);
            w.i32(f.d);
            for (const DefIndex p : f.plan) {
                w.u16(p);
            }
            w.u8(f.slot);
            w.u8(static_cast<std::uint8_t>(f.state));
            w.u16(f.crop);
            w.i32(f.work);
            w.i32(f.growth);
            w.i32(f.fertility);
            w.i32(f.pending);
            w.u32(f.year);
            w.i32(f.fertilized);
        }
    }
    m.villagers = w.bytes().size();
    const auto& vs = g.villagers();
    w.u32(static_cast<std::uint32_t>(vs.size()));
    for (std::size_t i = 0; i < vs.size(); ++i) {
        const EntityId id = vs.entities()[i];
        const Villager& v = vs.data()[i];
        w.u32(id.index);
        w.u32(id.generation);
        w.u8(v.owner);
        w.u8(static_cast<std::uint8_t>(v.sex));
        w.u8(v.race);
        w.u32(v.appearance);
        w.u32(v.family);
        w.i64(v.born_tick);
        w.vec2(v.position);
        w.vec2(v.previous);
        w.i32(v.food);
        w.i32(v.health);
        w.i32(v.warmth);
        w.i32(v.clothes);
        for (const DefIndex meal : v.meals) {
            w.u16(meal);
        }
        w.u8(v.meal_index);
        w.u8(v.variety);
        w.u16(v.spot);
        w.i32(v.shoes);
        w.u8(v.disease);
        w.i32(v.sick_days);
        w.i32(v.immune_days);
        w.u32(v.home.index);
        w.u32(v.home.generation);
        w.u32(v.job.index);
        w.u32(v.job.generation);
        w.u8(static_cast<std::uint8_t>(v.task));
        w.u32(v.target.index);
        w.u32(v.target.generation);
        w.u32(v.site.index);
        w.u32(v.site.generation);
        w.u32(v.node);
        w.i32(v.timer);
        w.u16(v.carrying.resource);
        w.i32(v.carrying.amount);
        w.string(v.name);
        w.u8(static_cast<std::uint8_t>(v.order));
        w.vec2(v.order_point);
        w.i32(v.provisions);
        w.u32(static_cast<std::uint32_t>(v.path.size()));
        for (const FixedVec2& p : v.path) {
            w.vec2(p);
        }
        w.u16(v.path_index);
        w.i32(v.idle_ticks);
        w.i32(v.work_carry);
    }
    // Animals and raiders.
    const auto& cs = g.creatures();
    w.u32(static_cast<std::uint32_t>(cs.size()));
    for (std::size_t i = 0; i < cs.size(); ++i) {
        const Creature& a = cs.data()[i];
        w.u32(cs.entities()[i].index);
        w.u32(cs.entities()[i].generation);
        w.u8(static_cast<std::uint8_t>(a.kind));
        w.u8(static_cast<std::uint8_t>(a.state));
        w.u8(a.town);
        w.u16(a.zone);
        w.vec2(a.position);
        w.vec2(a.previous);
        w.vec2(a.home);
        w.vec2(a.goal);
        w.u32(static_cast<std::uint32_t>(a.path.size()));
        for (const FixedVec2& p : a.path) {
            w.vec2(p);
        }
        w.u16(a.path_index);
        w.i32(a.health);
        w.i32(a.timer);
        w.u32(a.target.index);
        w.u32(a.target.generation);
        w.u16(a.loot.resource);
        w.i32(a.loot.amount);
        w.u8(static_cast<std::uint8_t>(a.target_kind));
        w.u16(a.unit);
    }
    // What each side explored: a count and a checksum (the cells themselves
    // follow the random numbers in a save).
    m.vision = w.bytes().size();
    g.vision().write_summary(w);
    if (marks != nullptr) {
        *marks = m;
    }
}

}  // namespace

std::vector<Game::PartHash> Game::hash_parts() const {
    BinaryWriter w;
    Marks m;
    write_state(*this, w, seed_, rejected_, regrow_, &m);
    const std::size_t end = w.bytes().size();
    w.u64(rng_.state());
    w.u64(rng_.increment());
    const auto part = [&](const char* name, std::size_t from, std::size_t to) {
        return PartHash{name, fnv1a64(std::span(w.bytes()).subspan(from, to - from))};
    };
    return {part("header", 0, m.players),         part("players", m.players, m.registry),
            part("entities", m.registry, m.nodes), part("nodes", m.nodes, m.buildings),
            part("buildings", m.buildings, m.villagers), part("villagers", m.villagers, m.vision),
            part("vision", m.vision, end),          part("random", end, w.bytes().size())};
}

std::uint64_t Game::hash() const {
    BinaryWriter w;
    write_state(*this, w, seed_, rejected_, regrow_);
    w.u64(rng_.state());
    w.u64(rng_.increment());
    return fnv1a64(w.bytes());
}

void Game::save(BinaryWriter& w) const {
    w.u32(kSaveVersion);
    w.u32(kGameRulesVersion);
    w.u64(content_->hash);
    write_map(w, map_);
    write_state(*this, w, seed_, rejected_, regrow_);
    w.u64(rng_.state());
    w.u64(rng_.increment());
    vision_.write(w);
}

bool Game::load(BinaryReader& r, std::shared_ptr<const Content> content) {
    std::uint32_t version = 0;
    std::uint32_t rules = 0;
    std::uint64_t content_hash = 0;
    if (!r.u32(version) || version != kSaveVersion || !r.u32(rules) || rules != kGameRulesVersion ||
        !r.u64(content_hash) || content_hash != content->hash) {
        r.fail();
        return false;
    }
    const Content& c = *content;
    MapData map;
    if (!read_map(r, map, c)) {
        return false;
    }
    // Build into a fresh game so a failure leaves this one untouched.
    Game g(content, MapData{}, 0, 0);
    g.map_ = std::move(map);
    g.build_indexes();
    std::uint32_t rejected = 0;
    std::uint8_t pc = 0;
    std::uint8_t dev = 0;
    std::uint8_t shared = 0;
    if (!r.u64(g.tick_) || !r.u64(g.seed_) || !r.u32(rejected) || !r.u8(dev) || dev > 1 || !r.u8(shared) ||
        shared > 1 || !GameRules::read(r, g.rules_) || !r.i32(g.snow_) || g.snow_ < 0 || g.snow_ > village::kMaxSnow ||
        !r.u8(pc) || pc > kMaxPlayers) {
        r.fail();
        return false;
    }
    g.rejected_ = rejected;
    g.dev_commands_ = dev != 0;
    g.shared_town_ = shared != 0;
    // Today's temperature follows from the tick (as on the day it began).
    // As of the last day that turned the weather: the village's or the calendar's.
    g.temperature_ = sim::temperature(g.rules_.climate, g.seed_,
                                      std::max(g.tick_ - g.tick_ % g.day_ticks(), g.tick_ - g.tick_ % g.calendar_day_ticks()));
    g.player_count_ = pc;
    for (std::uint8_t p = 0; p < pc; ++p) {
        PlayerState& ps = g.players_[p];
        std::uint8_t active = 0;
        if (!r.u8(active) || !r.u32(ps.town_center.index) || !r.u32(ps.town_center.generation) || !r.u32(ps.next_family) ||
            !r.i32(ps.births) || !r.i32(ps.deaths) || !r.i32(ps.arrivals) || !r.i32(ps.departures) ||
            !r.i32(ps.burned_down) || !r.u64(ps.merchant_arrives) ||
            !r.u64(ps.merchant_leaves)) {
            return false;
        }
        std::uint8_t alarm = 0, order = 0, outcome = 0;
        if (!r.u8(alarm) || alarm > 1 || !r.u64(ps.next_raid) || !r.i32(ps.raids) || !r.u8(order) ||
            order >= static_cast<std::uint8_t>(ArmyOrderKind::Count) || !r.vec2(ps.rally) || !r.u8(ps.enemy) ||
            ps.enemy >= kMaxPlayers || !r.u8(outcome) || outcome >= static_cast<std::uint8_t>(Outcome::Count)) {
            r.fail();
            return false;
        }
        ps.order = static_cast<ArmyOrderKind>(order);
        ps.outcome = static_cast<Outcome>(outcome);
        ps.alarm = alarm != 0;
        ps.active = active != 0;
        std::uint32_t goods = 0;
        if (!r.count(1024, 14, goods)) {
            return false;
        }
        ps.merchant.resize(goods);
        for (MerchantGood& m : ps.merchant) {
            if (!r.u16(m.resource) || m.resource >= c.resources.size() || !r.i32(m.stock) || m.stock < 0 || !r.i32(m.buy) ||
                m.buy < 1 || !r.i32(m.sell) || m.sell < 0) {
                r.fail();
                return false;
            }
        }
        std::uint32_t trade_rules = 0;
        if (!r.count(static_cast<std::uint32_t>(c.resources.size()), 10, trade_rules)) {
            return false;
        }
        ps.trade_rules.resize(trade_rules);
        for (std::size_t k = 0; k < ps.trade_rules.size(); ++k) {
            TradeRule& rule = ps.trade_rules[k];
            if (!r.u16(rule.resource) || rule.resource >= c.resources.size() ||
                (k > 0 && rule.resource <= ps.trade_rules[k - 1].resource) || !r.i32(rule.sell_above) ||
                rule.sell_above < kNoRule || rule.sell_above > kMaxRule || !r.i32(rule.buy_below) ||
                rule.buy_below < kNoRule || rule.buy_below > kMaxRule || !r.u8(rule.sell_min) || !r.u8(rule.buy_max) ||
                !valid_price_limit(rule.sell_min) || !valid_price_limit(rule.buy_max)) {
                r.fail();
                return false;
            }
        }
        TradeTally& t = ps.tally;
        if (!r.i32(t.sold) || t.sold < 0 || !r.i32(t.sold_gold) || t.sold_gold < 0 || !r.i32(t.bought) || t.bought < 0 ||
            !r.i32(t.bought_gold) || t.bought_gold < 0) {
            r.fail();
            return false;
        }
    }
    const auto trade_def = [&](DefIndex d) { return d < c.resources.size(); };
    std::uint8_t over = 0;
    std::uint32_t offers = 0;
    if (!r.u8(over) || over > 1 || !r.u32(g.next_offer_) || !r.count(64, 28, offers)) {
        r.fail();
        return false;
    }
    g.game_over_ = over != 0;
    g.offers_.resize(offers);
    for (TradeOffer& o : g.offers_) {
        if (!r.u32(o.id) || o.id >= g.next_offer_ || !r.u8(o.from) || o.from >= pc || !r.u8(o.to) || o.to >= pc ||
            !r.u16(o.give) || !trade_def(o.give) || !r.i32(o.give_amount) || o.give_amount < 1 || !r.u16(o.want) ||
            !trade_def(o.want) || !r.i32(o.want_amount) || o.want_amount < 1 || !r.u64(o.expires)) {
            r.fail();
            return false;
        }
    }
    std::uint32_t caravans = 0;
    if (!r.count(4096, 28, caravans)) {
        return false;
    }
    g.caravans_.resize(caravans);
    for (Caravan& cv : g.caravans_) {
        if (!r.u8(cv.from) || cv.from >= pc || !r.u8(cv.to) || cv.to >= pc || !r.u16(cv.resource) || !trade_def(cv.resource) ||
            !r.i32(cv.amount) || cv.amount < 1 || !r.u64(cv.departs) || !r.u64(cv.arrives)) {
            r.fail();
            return false;
        }
    }
    std::uint32_t slots = 0;
    if (!r.count(EntityRegistry::kMaxEntities, 5, slots)) {
        return false;
    }
    std::vector<std::uint32_t> gens(slots);
    std::vector<std::uint8_t> alive(slots);
    for (std::uint32_t i = 0; i < slots; ++i) {
        if (!r.u32(gens[i]) || !r.u8(alive[i])) {
            return false;
        }
    }
    std::uint32_t nfree = 0;
    if (!r.count(slots, 4, nfree)) {
        return false;
    }
    std::vector<std::uint32_t> free(nfree);
    for (std::uint32_t& f : free) {
        if (!r.u32(f)) {
            return false;
        }
    }
    if (!g.registry_.restore(std::move(gens), std::move(alive), std::move(free))) {
        r.fail();
        return false;
    }
    std::uint32_t n = 0;
    if (!r.count(kMaxMapFeatures, 16, n) || n != g.map_.features.size()) {
        r.fail();
        return false;
    }
    g.nodes_.resize(n);
    for (Node& node : g.nodes_) {
        if (!r.i32(node.amount) || !r.u32(node.reserved) || !r.u64(node.regrow_tick)) {
            return false;
        }
    }
    if (!r.count(kMaxMapFeatures, 12, n)) {
        return false;
    }
    g.regrow_.resize(n);
    for (auto& [t, i] : g.regrow_) {
        if (!r.u64(t) || !r.u32(i) || i >= g.nodes_.size()) {
            r.fail();
            return false;
        }
    }
    if (!r.count(100000, 4, n) || n != g.map_.zones.size()) {
        r.fail();
        return false;
    }
    g.zone_animals_.resize(n);
    for (std::int32_t& a : g.zone_animals_) {
        if (!r.i32(a) || a < 0 || a > 1000) {
            r.fail();
            return false;
        }
    }
    if (!r.count(100000, 30, n)) {
        return false;
    }
    for (std::uint32_t k = 0; k < n; ++k) {
        EntityId id;
        Building b;
        std::uint8_t state = 0;
        std::uint8_t heated = 0;
        if (!r.u32(id.index) || !r.u32(id.generation) || !r.u16(b.def) || !r.u8(b.owner) || !r.u8(b.rotation) ||
            !r.i32(b.x) || !r.i32(b.z) || !r.u8(state) || !r.u8(heated) || heated > 1 || b.def >= c.buildings.size() || b.owner >= pc || state > 1 ||
            b.rotation > 3 || !g.registry_.alive(id)) {
            r.fail();
            return false;
        }
        b.state = static_cast<BuildingState>(state);
        b.heated = heated != 0;
        footprint(c.buildings[b.def], b.rotation, b.width, b.depth);
        if (b.x < 0 || b.z < 0 || b.x + b.width > g.map_.size || b.z + b.depth > g.map_.size ||
            !read_stocks(r, b.delivered, c.resources.size()) || !read_stocks(r, b.incoming, c.resources.size()) ||
            !r.i32(b.work_done) || !read_stocks(r, b.stock, c.resources.size()) || !read_ids(r, b.workers) ||
            !r.i32(b.wanted_workers) || !read_ids(r, b.residents) || !r.i64(b.built_tick) || !r.u32(b.produced_year) ||
            !r.i32(b.produced)) {
            r.fail();
            return false;
        }
        std::uint8_t upgrading = 0;
        if (!r.u8(b.level) || b.level > c.buildings[b.def].levels.size() || !r.u8(upgrading) || upgrading > 1 ||
            !r.i32(b.limit) || b.limit < 0 || b.limit > 10000 || !r.u8(b.recipe) || !r.u16(b.needs) ||
            !r.i32(b.happiness) || b.happiness < 0 || b.happiness > 100 || !r.i32(b.desirability) || !r.i32(b.fire) ||
            b.fire < 0 || b.fire > 100 || !r.i32(b.burned) || b.burned < 0 || b.burned > 1000 || !r.i32(b.damage) ||
            b.damage < 0 || !r.i32(b.rearm) || b.rearm < 0) {
            r.fail();
            return false;
        }
        std::uint32_t queued = 0;
        if (!r.count(10, 2, queued)) {
            return false;
        }
        b.training.resize(queued);
        for (DefIndex& u : b.training) {
            if (!r.u16(u) || u >= c.units.size()) {
                r.fail();
                return false;
            }
        }
        std::uint8_t stopped = 0;
        if (!r.i32(b.train_progress) || b.train_progress < 0 || !r.u8(stopped) || stopped > 1) {
            r.fail();
            return false;
        }
        b.stopped = stopped != 0;
        b.upgrading = upgrading != 0;
        g.fires_ += b.fire > 0 ? 1 : 0;
        std::uint32_t nf = 0;
        if (!r.count(16, 40, nf)) {
            return false;
        }
        b.fields.resize(nf);
        for (Field& f : b.fields) {
            std::uint8_t field_state = 0;
            bool ok = r.i32(f.x) && r.i32(f.z) && r.i32(f.w) && r.i32(f.d);
            for (DefIndex& p : f.plan) {
                ok = ok && r.u16(p) && (p == kNoDef || p < c.crops.size());
            }
            ok = ok && r.u8(f.slot) && f.slot < kPlanYears && r.u8(field_state) &&
                 field_state < static_cast<std::uint8_t>(FieldState::Count) &&
                 r.u16(f.crop) && (f.crop == kNoDef || f.crop < c.crops.size()) && r.i32(f.work) && r.i32(f.growth) &&
                 r.i32(f.fertility) && f.fertility >= 0 && f.fertility <= 100 && r.i32(f.pending) && r.u32(f.year) &&
                 r.i32(f.fertilized);
            ok = ok && f.w >= kMinFieldSide && f.d >= kMinFieldSide && f.w <= kMaxFieldSide && f.d <= kMaxFieldSide &&
                 f.x >= 0 && f.z >= 0 && f.x + f.w <= g.map_.size && f.z + f.d <= g.map_.size;
            if (!ok) {
                r.fail();
                return false;
            }
            f.state = static_cast<FieldState>(field_state);
            for (std::int32_t cz = f.z; cz < f.z + f.d; ++cz) {
                for (std::int32_t cx = f.x; cx < f.x + f.w; ++cx) {
                    g.occupied_[static_cast<std::size_t>(cz) * static_cast<std::size_t>(g.map_.size) +
                                static_cast<std::size_t>(cx)] = 2;
                }
            }
        }
        for (std::int32_t cz = b.z; cz < b.z + b.depth; ++cz) {
            for (std::int32_t cx = b.x; cx < b.x + b.width; ++cx) {
                g.occupied_[static_cast<std::size_t>(cz) * static_cast<std::size_t>(g.map_.size) + static_cast<std::size_t>(cx)] = 1;
            }
        }
        block_nav(g.nav_, c.buildings[b.def], b.x, b.z, b.width, b.depth, true);
        g.buildings_.add(id, b);
    }
    g.building_set_changed();
    if (!r.count(village::kMaxVillagersPerPlayer * kMaxPlayers, 60, n)) {
        return false;
    }
    for (std::uint32_t k = 0; k < n; ++k) {
        EntityId id;
        Villager v;
        std::uint8_t sex = 0, task = 0;
        if (!r.u32(id.index) || !r.u32(id.generation) || !r.u8(v.owner) || !r.u8(sex) || !r.u8(v.race) ||
            !r.u32(v.appearance) || !r.u32(v.family) || !r.i64(v.born_tick) || !r.vec2(v.position) || !r.vec2(v.previous) ||
            !r.i32(v.food) || !r.i32(v.health) || !r.i32(v.warmth) || !r.i32(v.clothes) || !r.u16(v.meals[0]) || !r.u16(v.meals[1]) ||
            !r.u16(v.meals[2]) || !r.u16(v.meals[3]) || !r.u8(v.meal_index) || v.meal_index >= 4 ||
            !r.u8(v.variety) || !r.u16(v.spot) || !r.i32(v.shoes) || !r.u8(v.disease) || v.disease > c.diseases.size() ||
            !r.i32(v.sick_days) || !r.i32(v.immune_days) || !r.u32(v.home.index) || !r.u32(v.home.generation) ||
            !r.u32(v.job.index) || !r.u32(v.job.generation) || !r.u8(task) || !r.u32(v.target.index) ||
            !r.u32(v.target.generation) || !r.u32(v.site.index) || !r.u32(v.site.generation) || !r.u32(v.node) ||
            !r.i32(v.timer) || !r.u16(v.carrying.resource) || !r.i32(v.carrying.amount) || v.owner >= pc || sex > 1 ||
            task >= static_cast<std::uint8_t>(Task::Count) || v.node > g.nodes_.size() || !g.registry_.alive(id) ||
            (v.carrying.resource != kNoDef && v.carrying.resource >= c.resources.size()) || v.carrying.amount < 0) {
            r.fail();
            return false;
        }
        v.sex = static_cast<Sex>(sex);
        v.task = static_cast<Task>(task);
        std::uint8_t order = 0;
        if (!r.string(kMaxNameBytes, v.name) || !valid_villager_name(v.name) || !r.u8(order) ||
            order >= static_cast<std::uint8_t>(Order::Count) || !r.vec2(v.order_point) || !r.i32(v.provisions) ||
            v.provisions < 0 || v.provisions > village::kProvisions) {
            r.fail();
            return false;
        }
        v.order = static_cast<Order>(order);
        std::uint32_t steps = 0;
        if (!r.count(100000, 8, steps)) {
            return false;
        }
        v.path.resize(steps);
        for (FixedVec2& p : v.path) {
            if (!r.vec2(p)) {
                return false;
            }
        }
        if (!r.u16(v.path_index) || !r.i32(v.idle_ticks) || v.path_index > v.path.size() || !r.i32(v.work_carry) ||
            v.work_carry < 0 || v.work_carry >= 100 || (!c.races.empty() && v.race >= c.races.size())) {
            r.fail();
            return false;
        }
        g.villagers_.add(id, v);
    }
    g.villagers_changed();
    g.goods_changed();
    std::uint32_t creatures = 0;
    if (!r.count(1000000, 60, creatures)) {
        return false;
    }
    for (std::uint32_t k = 0; k < creatures; ++k) {
        EntityId id;
        Creature a;
        std::uint8_t kind = 0, state = 0;
        std::uint32_t steps = 0;
        if (!r.u32(id.index) || !r.u32(id.generation) || !g.registry_.alive(id) || !r.u8(kind) ||
            kind >= static_cast<std::uint8_t>(CreatureKind::Count) || !r.u8(state) ||
            state >= static_cast<std::uint8_t>(CreatureState::Count) || !r.u8(a.town) || a.town >= pc || !r.u16(a.zone) ||
            (kind < static_cast<std::uint8_t>(CreatureKind::Raider) && a.zone >= g.map_.zones.size()) ||
            !r.vec2(a.position) || !r.vec2(a.previous) || !r.vec2(a.home) || !r.vec2(a.goal) || !r.count(100000, 8, steps)) {
            r.fail();
            return false;
        }
        a.kind = static_cast<CreatureKind>(kind);
        a.state = static_cast<CreatureState>(state);
        a.path.resize(steps);
        for (FixedVec2& p : a.path) {
            if (!r.vec2(p)) {
                return false;
            }
        }
        if (!r.u16(a.path_index) || a.path_index > a.path.size() || !r.i32(a.health) || !r.i32(a.timer) ||
            !r.u32(a.target.index) || !r.u32(a.target.generation) || !r.u16(a.loot.resource) || !r.i32(a.loot.amount) ||
            a.loot.amount < 0 || (a.loot.amount > 0 && a.loot.resource >= c.resources.size())) {
            r.fail();
            return false;
        }
        std::uint8_t target_kind = 0;
        if (!r.u8(target_kind) || target_kind >= static_cast<std::uint8_t>(TargetKind::Count) || !r.u16(a.unit) ||
            (a.kind == CreatureKind::Soldier && a.unit >= c.units.size())) {
            r.fail();
            return false;
        }
        a.target_kind = static_cast<TargetKind>(target_kind);
        g.creatures_.add(id, a);
    }
    // The fog's summary, checked against the cells after the random numbers.
    VisionSummary summary;
    if (!Vision::read_summary(r, c.buildings.size(), pc, g.map_.size, summary)) {
        return false;
    }
    std::uint64_t state = 0, inc = 0;
    if (!r.u64(state) || !r.u64(inc) || !Rng::restore(state, inc, g.rng_)) {
        r.fail();
        return false;
    }
    if (!Vision::read(r, g.map_.size, g.fog(), summary, g.vision_) ||
        (g.fog() && g.vision_.groups() != g.vision_groups())) {
        r.fail();
        return false;
    }
    g.vision_.set_all_explored(g.rules_.fog == FogMode::Revealed);
    g.buildings_changed_ = true;
    *this = std::move(g);
    return true;
}

}  // namespace sc::sim
