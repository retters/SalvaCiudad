#include "sim/game.h"

#include <algorithm>
#include <bit>
#include <optional>

namespace sc::sim {

namespace {

constexpr std::uint32_t kSaveVersion = 1;
constexpr std::int32_t kNodeCell = 16;           // Meters per node lookup cell.
constexpr std::int32_t kMaxSlopeCm = 180;        // Height range allowed under a building.
constexpr std::uint32_t kJobEvery = 20;          // Ticks between job assignments.
constexpr std::int32_t kWanderRadius = 18;

Fixed walk_speed(bool adult) {
    return Fixed::from_ratio(adult ? 20 : 16, 100);  // Meters per tick: 2 m/s for adults.
}

std::int32_t carry_capacity(const Content& c, DefIndex resource) {
    if (resource >= c.resources.size()) {
        return village::kCarry;
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
                                             "going fishing", "fishing", "running to a fire", "fighting a fire"};
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
        const auto& list = g_.buildings_;
        for (std::size_t i = 0; i < list.size(); ++i) {
            const Building& b = list.data()[i];
            if (b.owner != owner || !accepts(b, resource) || free_space(b) <= 0) {
                continue;
            }
            const std::uint64_t d = distance2(from, g_.door(b));
            if (d < best_d) {
                best_d = d;
                best = list.entities()[i];
            }
        }
        return best;
    }

    // Nearest storage of `owner` holding `resource` (any food if kNoDef);
    // markets restock from the others.
    EntityId storage_with(std::uint8_t owner, FixedVec2 from, DefIndex resource, bool skip_markets = false) const {
        EntityId best;
        std::uint64_t best_d = UINT64_MAX;
        const auto& list = g_.buildings_;
        for (std::size_t i = 0; i < list.size(); ++i) {
            const Building& b = list.data()[i];
            if (b.owner != owner || !complete(b) || def(b).storage <= 0 ||
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
                best = list.entities()[i];
            }
        }
        return best;
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

    void decide(Villager& v) {
        const std::uint8_t owner = v.owner;
        // 1. Eat.
        if (v.food < village::kEatBelow) {
            const EntityId food = storage_with(owner, v.position, kNoDef);
            if (food.valid()) {
                go(v, Task::GoEat, food);
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
            v.carrying = {};  // Nowhere to put it: dropped.
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
        // 4. Laborer: construction, then hauling.
        if (start_construction(v) || start_hauling(v)) {
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
        const auto& list = g_.buildings_;
        for (std::size_t i = 0; i < list.size(); ++i) {
            const Building& b = list.data()[i];
            if (b.owner != v.owner || !complete(b) || def(b).kind != BuildingKind::Workplace) {
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
                best = list.entities()[i];
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
        const auto& list = g_.buildings_;
        for (std::size_t i = 0; i < list.size(); ++i) {
            const Building& b = list.data()[i];
            if (b.fire <= 0 || b.owner != v.owner) {
                continue;
            }
            const std::uint64_t d = distance2(v.position, center_of(b));
            if (d < best_d && well_near(b)) {
                best_d = d;
                best = list.entities()[i];
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
                    if (g_.rng_.below(1000) < static_cast<std::uint32_t>(b.fire / 2)) {
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
            remove_building(id);
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
            if (++v.timer < 20) {
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
            if (++v.timer < 40) {
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
                    f.pending = std::max(1, f.w * f.d * crop.yield * f.fertility / 1000);
                    g_.buildings_changed_ = true;
                }
            }
        }
    }

    // --- Hunting and fishing (phase 11) ---------------------------------------------

    static std::int32_t zone_capacity(ZoneType t) {
        switch (t) {
            case ZoneType::Deer: return 16;
            case ZoneType::Boar: return 10;
            default: return 0;  // Wolves and bears come with the wildlife (phase 15).
        }
    }

    bool start_hunting(Villager& v, const Building& lodge) {
        const FixedVec2 door = g_.door(lodge);
        const std::int32_t reach = def(lodge).work_radius;
        std::optional<std::size_t> best;
        std::uint64_t best_d = UINT64_MAX;
        for (std::size_t z = 0; z < g_.map_.zones.size(); ++z) {
            const Zone& zone = g_.map_.zones[z];
            if (g_.zone_animals_[z] <= 0 || zone_capacity(zone.type) == 0) {
                continue;
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
        if (++v.timer < 120) {
            return;
        }
        v.timer = 0;
        v.task = Task::Idle;
        const std::size_t z = v.spot - 1u;
        if (v.spot == 0 || z >= g_.zone_animals_.size() || g_.zone_animals_[z] <= 0 || g_.meat_ == kNoDef) {
            return;
        }
        --g_.zone_animals_[z];
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
        if (++v.timer < 45) {
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
            if (job.produced >= d.yearly_limit) {
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
        const auto& list = g_.buildings_;
        for (std::size_t i = 0; i < list.size(); ++i) {
            const Building& b = list.data()[i];
            if (b.owner != v.owner || !is_site(b)) {
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
                    best_fetch_site = list.entities()[i];
                    best_fetch_from = from;
                    best_res = cost.resource;
                }
            }
            if (all_there && b.work_done < site_work(b) && d < best_build_d) {
                best_build_d = d;
                best_build = list.entities()[i];
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
            v.clothes = static_cast<std::int32_t>(g_.year_ticks());
        }
        if (v.shoes <= 0 && g_.shoes_ != kNoDef && gives_out(c_, *b, g_.shoes_) && amount_of(b->stock, g_.shoes_) > 0) {
            add_to(b->stock, g_.shoes_, -1);
            v.shoes = static_cast<std::int32_t>(g_.year_ticks());
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
        if (++v.timer < fd->work) {
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
        ++site->work_done;
        if (site->work_done % 25 == 0) {
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
        if (++v.timer < recipe.work) {
            return;
        }
        // Another worker may have reached the year's limit meanwhile.
        const std::int32_t limit = def(*job).yearly_limit;
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

    EntityId spawn_villager(std::uint8_t owner, FixedVec2 at, Sex sex, std::int32_t age_years, std::uint32_t family) {
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
        v.appearance = g_.rng_.next_u32();
        v.family = family;
        v.born_tick = static_cast<std::int64_t>(g_.tick_) - static_cast<std::int64_t>(age_years) * g_.year_ticks() -
                      static_cast<std::int64_t>(g_.rng_.below(g_.year_ticks()));
        v.position = at;
        v.previous = at;
        v.food = 700 + static_cast<std::int32_t>(g_.rng_.below(300));
        v.idle_ticks = static_cast<std::int32_t>(g_.rng_.below(40));
        g_.villagers_.add(id, v);
        return id;
    }

    void kill(EntityId id) {
        Villager* v = g_.villagers_.get(id);
        if (v == nullptr) {
            return;
        }
        v_index_ = id.index;
        release(*v);
        if (Building* job = g_.buildings_.get(v->job)) {
            std::erase(job->workers, id);
        }
        if (Building* home = g_.buildings_.get(v->home)) {
            std::erase(home->residents, id);
        }
        ++g_.players_[v->owner].deaths;
        g_.villagers_.remove(id);
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
            // Too many: the newest go back to laboring.
            while (static_cast<std::int32_t>(b.workers.size()) > b.wanted_workers) {
                if (Villager* w = g_.villagers_.get(b.workers.back())) {
                    w->job = {};
                    ++free[b.owner];
                }
                b.workers.pop_back();
            }
            while (static_cast<std::int32_t>(b.workers.size()) < b.wanted_workers && free[b.owner] > reserve[b.owner]) {
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
        for (std::size_t k = 0; k < vs.size(); ++k) {
            Villager& v = vs.data()[k];
            if (g_.buildings_.get(v.home) != nullptr) {
                continue;
            }
            v.home = {};
            // A house with room; one with family is better.
            EntityId best;
            int best_score = -1;
            auto& list = g_.buildings_;
            for (std::size_t i = 0; i < list.size(); ++i) {
                Building& b = list.data()[i];
                if (b.owner != v.owner || !complete(b) || g_.capacity(b) <= 0 ||
                    static_cast<std::int32_t>(b.residents.size()) >= g_.capacity(b)) {
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
                    best = list.entities()[i];
                }
            }
            if (best.valid()) {
                v.home = best;
                g_.buildings_.get(best)->residents.push_back(vs.entities()[k]);
            }
        }
    }

    void monthly() {
        // Diets: last month's variety; the game comes back to its zones.
        for (std::size_t z = 0; z < g_.zone_animals_.size(); ++z) {
            const std::int32_t cap = zone_capacity(g_.map_.zones[z].type);
            g_.zone_animals_[z] = std::min(cap, g_.zone_animals_[z] + std::max(1, cap / 6));
        }
        // Old age.
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
        // Births: a home with a man and a woman, room and fed parents.
        auto& list = g_.buildings_;
        for (std::size_t i = 0; i < list.size(); ++i) {
            Building& b = list.data()[i];
            if (!complete(b) || g_.capacity(b) <= 0 || static_cast<std::int32_t>(b.residents.size()) >= g_.capacity(b)) {
                continue;
            }
            const Villager* mother = nullptr;
            bool father = false;
            for (const EntityId r : b.residents) {
                const Villager* v = g_.villagers_.get(r);
                if (v == nullptr || !g_.adult(*v) || g_.age_years(*v) > 40 || v->food < 500) {
                    continue;
                }
                if (v->sex == Sex::Female) {
                    mother = v;
                } else {
                    father = true;
                }
            }
            // Happier homes have more children (12 % a month at 60).
            if (mother == nullptr || !father || food_stored(b.owner) < 3 * g_.population(b.owner) || b.happiness < 25 ||
                g_.rng_.below(1000) >= static_cast<std::uint32_t>(2 * b.happiness)) {
                continue;
            }
            const std::uint32_t family = mother->family;
            const std::uint8_t owner = b.owner;
            const FixedVec2 at = g_.door(b);
            const Sex sex = g_.rng_.below(2) == 0 ? Sex::Male : Sex::Female;
            const EntityId baby = spawn_villager(owner, at, sex, 0, family);
            if (baby.valid()) {
                Villager* bv = g_.villagers_.get(baby);
                bv->born_tick = static_cast<std::int64_t>(g_.tick_);
                bv->home = list.entities()[i];
                g_.buildings_.get(list.entities()[i])->residents.push_back(baby);
                ++g_.players_[owner].births;
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
            for (std::int32_t n = 0; n < count; ++n) {
                const Sex sex = n == 0 ? Sex::Male : (n == 1 ? Sex::Female : (g_.rng_.below(2) == 0 ? Sex::Male : Sex::Female));
                const std::int32_t age = n < 2 ? 18 + static_cast<std::int32_t>(g_.rng_.below(15))
                                               : static_cast<std::int32_t>(g_.rng_.below(4));
                if (spawn_villager(p, g_.door(*tc), sex, age, family).valid()) {
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
            kill(id);
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
        const auto& all = g_.buildings_.data();
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
            std::int32_t beauty = 0;
            for (const Building& o : all) {
                const std::int32_t des = def(o).desirability;
                if (des == 0 || &o == &b) {
                    continue;
                }
                const std::uint64_t d2 = distance2(here, center(o));
                if (d2 < meters2(30)) {
                    const auto dist = static_cast<std::int32_t>(isqrt(d2 >> 32));
                    beauty += des * (30 - dist) / 30;
                }
            }
            std::int32_t trees = 0;
            const std::int32_t side = g_.node_cells_side_;
            const std::int32_t cx = here.x.floor_int() / kNodeCell;
            const std::int32_t cz = here.z.floor_int() / kNodeCell;
            for (std::int32_t z = std::max(0, cz - 1); z <= std::min(side - 1, cz + 1); ++z) {
                for (std::int32_t x = std::max(0, cx - 1); x <= std::min(side - 1, cx + 1); ++x) {
                    for (const std::uint32_t i : g_.node_cells_[static_cast<std::size_t>(z * side + x)]) {
                        const MapFeature& f = g_.map_.features[i];
                        if (f.type == FeatureType::Tree && g_.nodes_[i].amount > 0 &&
                            distance2(here, {f.x, f.z}) < meters2(16)) {
                            ++trees;
                        }
                    }
                }
            }
            beauty += std::min(trees, 8);
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

    void daily() {
        g_.temperature_ = sim::temperature(g_.rules_.climate, g_.seed_, g_.tick_);
        grow_fields();
        update_homes();
        update_health();
        start_fires();
        const std::int32_t t = g_.temperature_;
        if (t < 0) {
            g_.snow_ = std::min(village::kMaxSnow, g_.snow_ + 1 + std::min(-t, 10) / 2);
        } else if (t > 2) {
            g_.snow_ = std::max(0, g_.snow_ - (t - 1));
        }
        auto& list = g_.buildings_;
        for (std::size_t i = 0; i < list.size(); ++i) {
            Building& b = list.data()[i];
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
        const bool warm_home = home != nullptr && home->heated;
        if (g_.temperature_ < 5 && !warm_home) {
            v.warmth = std::max(0, v.warmth - (v.clothes > 0 ? 1 : 2) - (g_.temperature_ < -8 ? 1 : 0));
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
        if (g_.tick_ % g_.day_ticks() == 0) {
            daily();
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
        if (g_.tick_ % g_.month_ticks() == 0) {
            monthly();
        }
        std::vector<EntityId> dying;
        auto& vs = g_.villagers_;
        for (std::size_t k = 0; k < vs.size(); ++k) {
            Villager& v = vs.data()[k];
            v_index_ = vs.entities()[k].index;
            v.previous = v.position;
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
            if (moving(v)) {
                move(v);
                if (!moving(v)) {
                    arrive(v);
                }
            } else if (v.task == Task::Gather || v.task == Task::Build || v.task == Task::Produce || v.task == Task::Farm ||
                       v.task == Task::Hunt || v.task == Task::Fish || v.task == Task::FightFire) {
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
        g_.nav_.set_building(x, z, x + b.width, z + b.depth, true);
        g_.buildings_.add(id, b);
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

    void remove_building(EntityId id) {
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
        }
        for (std::int32_t cz = b->z; cz < b->z + b->depth; ++cz) {
            for (std::int32_t cx = b->x; cx < b->x + b->width; ++cx) {
                g_.occupied_[static_cast<std::size_t>(cz) * static_cast<std::size_t>(g_.map_.size) + static_cast<std::size_t>(cx)] = 0;
            }
        }
        g_.nav_.set_building(b->x, b->z, b->x + b->width, b->z + b->depth, false);
        g_.buildings_.remove(id);
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
            // Five couples and two children.
            const FixedVec2 at = g_.door(*tc);
            for (std::int32_t n = 0; n < 5; ++n) {
                const std::uint32_t family = ps.next_family++;
                const FixedVec2 spot{at.x + Fixed::from_int(n * 2 - 4), at.z - Fixed::from_int(2)};  // Outside, past the door.
                (void)spawn_villager(p, spot, Sex::Male, 20 + static_cast<std::int32_t>(g_.rng_.below(12)), family);
                (void)spawn_villager(p, spot, Sex::Female, 19 + static_cast<std::int32_t>(g_.rng_.below(12)), family);
                if (n < 2) {
                    (void)spawn_villager(p, spot, g_.rng_.below(2) == 0 ? Sex::Male : Sex::Female,
                                         1 + static_cast<std::int32_t>(g_.rng_.below(3)), family);
                }
            }
        }
    }

    std::uint32_t v_index_ = 0;   // Entity index of the villager being updated.

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
    zone_animals_.resize(map_.zones.size());
    for (std::size_t z = 0; z < map_.zones.size(); ++z) {
        zone_animals_[z] = VillageRules::zone_capacity(map_.zones[z].type);
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
    VillageRules(*this).apply(command);
}

void Game::step() {
    VillageRules(*this).step();
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
    if (hi - lo > kMaxSlopeCm) {
        return PlaceError::TooSteep;
    }
    return PlaceError::None;
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
    return PlaceError::None;
}

std::int32_t Game::sick(std::uint8_t player) const {
    std::int32_t n = 0;
    const std::uint8_t town = town_of(player);
    for (const Villager& v : villagers_.data()) {
        n += v.owner == town && v.disease != 0 ? 1 : 0;
    }
    return n;
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
    return out;
}

std::int32_t Game::population(std::uint8_t player, bool adults_only) const {
    std::int32_t n = 0;
    for (const Villager& v : villagers_.data()) {
        if (v.owner == player && (!adults_only || adult(v))) {
            ++n;
        }
    }
    return n;
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
}

bool read_map(BinaryReader& r, MapData& m, const Content& c) {
    if (!MapSettings::read(r, m.settings) || !r.u16(m.generator_version) || !r.i32(m.size)) {
        return false;
    }
    if (m.size != map_cells(m.settings.size)) {
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
    if (!r.count(4'000'000, 16, n)) {
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
    return true;
}

// Where each part of the state starts in the written bytes.
struct Marks {
    std::size_t players = 0, registry = 0, nodes = 0, buildings = 0, villagers = 0;
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
        w.u32(static_cast<std::uint32_t>(v.path.size()));
        for (const FixedVec2& p : v.path) {
            w.vec2(p);
        }
        w.u16(v.path_index);
        w.i32(v.idle_ticks);
    }
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
            part("buildings", m.buildings, m.villagers), part("villagers", m.villagers, end),
            part("random", end, w.bytes().size())};
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
    g.temperature_ = sim::temperature(g.rules_.climate, g.seed_, g.tick_ - g.tick_ % g.day_ticks());
    g.player_count_ = pc;
    for (std::uint8_t p = 0; p < pc; ++p) {
        PlayerState& ps = g.players_[p];
        std::uint8_t active = 0;
        if (!r.u8(active) || !r.u32(ps.town_center.index) || !r.u32(ps.town_center.generation) || !r.u32(ps.next_family) ||
            !r.i32(ps.births) || !r.i32(ps.deaths) || !r.i32(ps.arrivals) || !r.i32(ps.departures) ||
            !r.i32(ps.burned_down)) {
            return false;
        }
        ps.active = active != 0;
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
    if (!r.count(4'000'000, 16, n) || n != g.map_.features.size()) {
        r.fail();
        return false;
    }
    g.nodes_.resize(n);
    for (Node& node : g.nodes_) {
        if (!r.i32(node.amount) || !r.u32(node.reserved) || !r.u64(node.regrow_tick)) {
            return false;
        }
    }
    if (!r.count(4'000'000, 12, n)) {
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
            b.fire < 0 || b.fire > 100 || !r.i32(b.burned) || b.burned < 0 || b.burned > 1000) {
            r.fail();
            return false;
        }
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
        g.nav_.set_building(b.x, b.z, b.x + b.width, b.z + b.depth, true);
        g.buildings_.add(id, b);
    }
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
        if (!r.u16(v.path_index) || !r.i32(v.idle_ticks) || v.path_index > v.path.size()) {
            r.fail();
            return false;
        }
        g.villagers_.add(id, v);
    }
    std::uint64_t state = 0, inc = 0;
    if (!r.u64(state) || !r.u64(inc) || !Rng::restore(state, inc, g.rng_)) {
        r.fail();
        return false;
    }
    g.buildings_changed_ = true;
    *this = std::move(g);
    return true;
}

}  // namespace sc::sim
