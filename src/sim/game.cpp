#include "sim/game.h"

#include <algorithm>

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
    if (d.kind == BuildingKind::Storage || d.kind == BuildingKind::TownCenter) {
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
    return true;
}

}  // namespace

const char* task_name(Task t) {
    static constexpr const char* kNames[] = {"idle",    "wander",       "going to eat", "going to gather",
                                             "gathering", "delivering", "fetching",     "carrying to a site",
                                             "going to build", "building", "going to work", "producing"};
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

    // Nearest storage of `owner` holding `resource` (any food if kNoDef).
    EntityId storage_with(std::uint8_t owner, FixedVec2 from, DefIndex resource) const {
        EntityId best;
        std::uint64_t best_d = UINT64_MAX;
        const auto& list = g_.buildings_;
        for (std::size_t i = 0; i < list.size(); ++i) {
            const Building& b = list.data()[i];
            if (b.owner != owner || !complete(b) || def(b).storage <= 0) {
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
        Fixed budget = walk_speed(g_.adult(v));
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
            if (Building* s = g_.buildings_.get(v.site); s != nullptr && s->state == BuildingState::Construction) {
                add_to(s->incoming, v.carrying.resource, -v.timer);
                compact(s->incoming);
            }
            v.timer = 0;
        }
        if (v.task == Task::GoSite && v.carrying.amount > 0) {
            // Goods on their way that will not arrive; they go to storage.
            if (Building* s = g_.buildings_.get(v.target); s != nullptr && s->state == BuildingState::Construction) {
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
        // 3. Job.
        if (Building* job = g_.buildings_.get(v.job); job != nullptr && complete(*job)) {
            const BuildingDef& d = def(*job);
            if (d.work == WorkKind::Gather && start_gathering(v, *job)) {
                return;
            }
            if (d.work == WorkKind::Produce && start_producing(v, *job)) {
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

    bool start_producing(Villager& v, Building& job) {
        const BuildingDef& d = def(job);
        if (d.recipes.empty()) {
            return false;
        }
        const RecipeDef& recipe = c_.recipes[d.recipes.front()];
        // Inputs at the workplace: work there.
        bool ready = true;
        for (const ResourceAmount& in : recipe.inputs) {
            if (amount_of(job.stock, in.resource) < in.amount) {
                ready = false;
            }
        }
        if (ready) {
            go(v, Task::GoWorkplace, v.job);
            return true;
        }
        // Otherwise fetch the first missing input.
        for (const ResourceAmount& in : recipe.inputs) {
            if (amount_of(job.stock, in.resource) >= in.amount) {
                continue;
            }
            const EntityId from = storage_with(v.owner, v.position, in.resource);
            if (!from.valid()) {
                return false;
            }
            v.site = v.job;  // The goods go to the workplace.
            v.carrying = {in.resource, 0};
            v.timer = 0;
            go(v, Task::GoFetch, from);
            return true;
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
            if (b.owner != v.owner || b.state != BuildingState::Construction) {
                continue;
            }
            const std::uint64_t d = distance2(v.position, g_.door(b));
            bool all_there = true;
            for (const ResourceAmount& cost : def(b).cost) {
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
            if (all_there && b.work_done < def(b).build_work && d < best_build_d) {
                best_build_d = d;
                best_build = list.entities()[i];
            }
        }
        if (best_fetch_site.valid()) {
            Building& site = *g_.buildings_.get(best_fetch_site);
            const Building& from = *g_.buildings_.get(best_fetch_from);
            std::int32_t missing = 0;
            for (const ResourceAmount& cost : def(site).cost) {
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
            default: v.task = Task::Idle; break;
        }
    }

    void eat(Villager& v) {
        Building* b = g_.buildings_.get(v.target);
        v.task = Task::Idle;
        if (b == nullptr) {
            return;
        }
        // Several helpings, from the most nutritious food first.
        while (v.food < village::kFoodMax - 100) {
            Stock* best = nullptr;
            for (Stock& s : b->stock) {
                const ResourceDef& r = c_.resources[s.resource];
                if (s.amount > 0 && r.category == ResourceCategory::Food && r.nutrition > 0 && gives_out(c_, *b, s.resource) &&
                    (best == nullptr || r.nutrition > c_.resources[best->resource].nutrition)) {
                    best = &s;
                }
            }
            if (best == nullptr) {
                break;
            }
            --best->amount;
            v.food = std::min(village::kFoodMax, v.food + c_.resources[best->resource].nutrition * village::kFoodPerNutrition);
        }
        compact(b->stock);
    }

    void deliver(Villager& v) {
        Building* b = g_.buildings_.get(v.target);
        v.task = Task::Idle;
        if (b == nullptr || v.carrying.amount <= 0) {
            return;
        }
        const std::int32_t put = std::min(v.carrying.amount, free_space(*b));
        const bool own = v.target == v.job && def(*b).kind == BuildingKind::Workplace;
        if (put > 0 && (own || accepts(*b, v.carrying.resource))) {
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
        const bool for_site = site != nullptr && site->state == BuildingState::Construction;
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
        if (site == nullptr || site->state != BuildingState::Construction) {
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
                const std::uint64_t at = g_.tick_ + static_cast<std::uint64_t>(fd->regrow_days) * kTicksPerDay;
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
        if (site == nullptr || site->state != BuildingState::Construction) {
            v.task = Task::Idle;
            return;
        }
        ++site->work_done;
        if (site->work_done % 25 == 0) {
            g_.buildings_changed_ = true;  // The view shows the rising building.
        }
        if (site->work_done >= def(*site).build_work) {
            finish(*site);
            v.task = Task::Idle;
        }
    }

    void finish(Building& b) {
        b.state = BuildingState::Complete;
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
        const RecipeDef& recipe = c_.recipes[def(*job).recipes.front()];
        for (const ResourceAmount& in : recipe.inputs) {
            if (amount_of(job->stock, in.resource) < in.amount) {
                v.task = Task::Idle;
                return;
            }
        }
        if (++v.timer < recipe.work) {
            return;
        }
        for (const ResourceAmount& in : recipe.inputs) {
            add_to(job->stock, in.resource, -in.amount);
        }
        compact(job->stock);
        const ResourceAmount& out = recipe.outputs.front();
        v.carrying = {out.resource, out.amount};
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
        if (g_.population(owner) >= village::kMaxVillagersPerPlayer) {
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
        v.born_tick = static_cast<std::int64_t>(g_.tick_) - static_cast<std::int64_t>(age_years) * kTicksPerYear -
                      static_cast<std::int64_t>(g_.rng_.below(kTicksPerYear));
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
                }
                b.workers.pop_back();
            }
            while (static_cast<std::int32_t>(b.workers.size()) < b.wanted_workers) {
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
                if (b.owner != v.owner || !complete(b) || def(b).residents <= 0 ||
                    static_cast<std::int32_t>(b.residents.size()) >= def(b).residents) {
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
            if (!complete(b) || def(b).residents <= 0 || static_cast<std::int32_t>(b.residents.size()) >= def(b).residents) {
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
            if (mother == nullptr || !father || food_stored(b.owner) < 3 * g_.population(b.owner) ||
                g_.rng_.below(1000) >= 120) {
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
            if (!g_.players_[p].active) {
                continue;
            }
            std::int32_t room = 0;
            for (std::size_t i = 0; i < list.size(); ++i) {
                const Building& b = list.data()[i];
                if (b.owner == p && complete(b) && def(b).residents > 0) {
                    room += def(b).residents - static_cast<std::int32_t>(b.residents.size());
                }
            }
            const std::int32_t food = food_stored(p);
            const std::int32_t pop = g_.population(p);
            // Newcomers want a town that has food to spare.
            if (room < 2 || food < 40 + pop * 10) {
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
    }

    // --- The tick -------------------------------------------------------------

    void step() {
        ++g_.tick_;
        // Bushes that grow back.
        while (!g_.regrow_.empty() && g_.regrow_.front().first <= g_.tick_) {
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
        if (g_.tick_ % kTicksPerMonth == 0) {
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
            } else if (v.health < village::kHealthMax && g_.tick_ % 4 == 0) {
                ++v.health;
            }
            if (moving(v)) {
                move(v);
                if (!moving(v)) {
                    arrive(v);
                }
            } else if (v.task == Task::Gather || v.task == Task::Build || v.task == Task::Produce) {
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

    void remove_building(EntityId id) {
        Building* b = g_.buildings_.get(id);
        if (b == nullptr) {
            return;
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

    void apply(const Command& c) {
        if (c.player >= g_.player_count_ || !g_.players_[c.player].active) {
            ++g_.rejected_;
            return;
        }
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
        g_.player_count_ = std::min<std::uint8_t>(players, static_cast<std::uint8_t>(g_.map_.starts.size()));
        DefIndex tc_def = kNoDef;
        for (std::size_t i = 0; i < c_.buildings.size(); ++i) {
            if (c_.buildings[i].kind == BuildingKind::TownCenter && tc_def == kNoDef) {
                tc_def = static_cast<DefIndex>(i);
            }
        }
        for (std::uint8_t p = 0; p < g_.player_count_; ++p) {
            PlayerState& ps = g_.players_[p];
            ps.active = true;
            if (tc_def == kNoDef) {
                continue;
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
            } kStart[] = {{"core:log", 60}, {"core:stone", 20}, {"core:berries", 150}, {"core:roots", 40}};
            for (const auto& item : kStart) {
                const DefIndex r = c_.find_resource(item.id);
                if (r != kNoDef) {
                    add_to(tc->stock, r, item.amount);
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

Game::Game(std::shared_ptr<const Content> content, MapData map, std::uint8_t players, std::uint64_t seed)
    : content_(std::move(content)), map_(std::move(map)), seed_(seed), rng_(seed, 21) {
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
    return static_cast<std::int32_t>(std::max<std::int64_t>(0, age) / kTicksPerYear);
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

void write_state(const Game& g, BinaryWriter& w, std::uint64_t seed, std::uint32_t rejected,
                 const std::vector<std::pair<std::uint64_t, std::uint32_t>>& regrow) {
    w.u64(g.tick());
    w.u64(seed);
    w.u32(rejected);
    w.u8(g.dev_commands() ? 1 : 0);
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
    }
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
        write_stocks(w, b.delivered);
        write_stocks(w, b.incoming);
        w.i32(b.work_done);
        write_stocks(w, b.stock);
        write_ids(w, b.workers);
        w.i32(b.wanted_workers);
        write_ids(w, b.residents);
    }
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
}

}  // namespace

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
    if (!r.u64(g.tick_) || !r.u64(g.seed_) || !r.u32(rejected) || !r.u8(dev) || dev > 1 || !r.u8(pc) ||
        pc > kMaxPlayers) {
        r.fail();
        return false;
    }
    g.rejected_ = rejected;
    g.dev_commands_ = dev != 0;
    g.player_count_ = pc;
    for (std::uint8_t p = 0; p < pc; ++p) {
        PlayerState& ps = g.players_[p];
        std::uint8_t active = 0;
        if (!r.u8(active) || !r.u32(ps.town_center.index) || !r.u32(ps.town_center.generation) || !r.u32(ps.next_family) ||
            !r.i32(ps.births) || !r.i32(ps.deaths) || !r.i32(ps.arrivals)) {
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
    if (!r.count(100000, 30, n)) {
        return false;
    }
    for (std::uint32_t k = 0; k < n; ++k) {
        EntityId id;
        Building b;
        std::uint8_t state = 0;
        if (!r.u32(id.index) || !r.u32(id.generation) || !r.u16(b.def) || !r.u8(b.owner) || !r.u8(b.rotation) ||
            !r.i32(b.x) || !r.i32(b.z) || !r.u8(state) || b.def >= c.buildings.size() || b.owner >= pc || state > 1 ||
            b.rotation > 3 || !g.registry_.alive(id)) {
            r.fail();
            return false;
        }
        b.state = static_cast<BuildingState>(state);
        footprint(c.buildings[b.def], b.rotation, b.width, b.depth);
        if (b.x < 0 || b.z < 0 || b.x + b.width > g.map_.size || b.z + b.depth > g.map_.size ||
            !read_stocks(r, b.delivered, c.resources.size()) || !read_stocks(r, b.incoming, c.resources.size()) ||
            !r.i32(b.work_done) || !read_stocks(r, b.stock, c.resources.size()) || !read_ids(r, b.workers) ||
            !r.i32(b.wanted_workers) || !read_ids(r, b.residents)) {
            r.fail();
            return false;
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
            !r.i32(v.food) || !r.i32(v.health) || !r.u32(v.home.index) || !r.u32(v.home.generation) ||
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
