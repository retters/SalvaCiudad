#include <doctest.h>

#include <algorithm>
#include <filesystem>
#include <map>
#include <memory>
#include <optional>
#include <utility>
#include <vector>

#include "game/save_file.h"
#include "sim/game.h"
#include "sim/worldgen.h"
#include "test_util.h"
#include "version.h"

using namespace sc;
using namespace sc::sim;

namespace {

std::shared_ptr<const Content> core() {
    return std::shared_ptr<const Content>(std::shared_ptr<const Content>{}, &test::core_content());
}

const MapData& map_for(std::uint64_t seed) {
    static std::map<std::uint64_t, MapData> cache;
    auto it = cache.find(seed);
    if (it == cache.end()) {
        MapSettings s;
        s.seed = seed;
        s.size = MapSize::Small;
        s.sea = Sea::None;
        std::optional<MapData> m = generate_map(s, test::core_content());
        REQUIRE(m.has_value());
        it = cache.emplace(seed, std::move(*m)).first;
    }
    return it->second;
}

// A map with wolves a few hundred meters from the town.
constexpr std::uint64_t kWolfMap = 92;
// A minute of day and then half an hour of night; or always day.
constexpr DayNightSettings kLongNight{1, 30};
constexpr DayNightSettings kAlwaysDay{};

GameSetup setup(DayNightSettings cycle, Threat wildlife = Threat::Medium, Threat raiders = Threat::None) {
    GameSetup s;
    s.seed = 15;
    s.rules.climate.seasons = 0b0010;  // Summer.
    s.rules.diseases = Threat::None;
    s.rules.fires = Threat::None;
    s.rules.raiders = raiders;
    s.rules.wildlife = wildlife;
    s.rules.day_night = cycle;
    return s;
}

void run(Game& g, std::uint32_t ticks) {
    for (std::uint32_t i = 0; i < ticks; ++i) {
        g.step();
    }
}

void grant(Game& g, const char* resource, std::int32_t amount) {
    Command c;
    c.type = CommandType::DevGrant;
    c.def = g.content().find_resource(resource);
    REQUIRE(c.def != kNoDef);
    c.value = amount;
    g.apply(c);
}

void provide(Game& g) {
    for (const char* food : {"core:bread", "core:meat", "core:vegetables", "core:fruit"}) {
        grant(g, food, 3000);
    }
}

void to_night(Game& g) {
    for (int t = 0; t < 2000 && !g.night(); ++t) {
        g.step();
    }
    REQUIRE(g.night());
}

DefIndex building(const Game& g, const char* id) {
    const DefIndex d = g.content().find_building(id);
    REQUIRE(d != kNoDef);
    return d;
}

// The developer's order: everything being built is done.
void finish_all(Game& g) {
    Command c;
    c.type = CommandType::DevBuild;
    g.apply(c);
}

// A building of `def` at (x, z), or as near as it fits (a few meters); built at once.
EntityId put(Game& g, const char* def, std::int32_t x, std::int32_t z) {
    const DefIndex d = building(g, def);
    for (std::int32_t r = 0; r <= 6; ++r) {
        for (std::int32_t dz = -r; dz <= r; ++dz) {
            for (std::int32_t dx = -r; dx <= r; ++dx) {
                if (std::max(std::abs(dx), std::abs(dz)) != r || g.can_place(0, d, x + dx, z + dz, 0) != PlaceError::None) {
                    continue;
                }
                Command c;
                c.type = CommandType::PlaceBuilding;
                c.def = d;
                c.position = {Fixed::from_int(x + dx), Fixed::from_int(z + dz)};
                g.apply(c);
                finish_all(g);
                for (std::size_t i = 0; i < g.buildings().size(); ++i) {
                    const Building& b = g.buildings().data()[i];
                    if (b.def == d && b.x == x + dx && b.z == z + dz) {
                        return g.buildings().entities()[i];
                    }
                }
            }
        }
    }
    return {};
}

bool beast(const Creature& a) {
    return a.kind == CreatureKind::Wolf || a.kind == CreatureKind::Bear;
}

// The wolves' den nearest to the town: its zone and its middle, in meters.
struct Den {
    std::size_t zone = 0;
    std::int32_t x = 0;
    std::int32_t z = 0;
};
Den nearest_den(const Game& g) {
    const Building* tc = g.buildings().get(g.player(0).town_center);
    REQUIRE(tc != nullptr);
    Den den;
    std::int64_t best = -1;
    for (const Creature& a : g.creatures().data()) {
        if (a.kind != CreatureKind::Wolf) {
            continue;
        }
        const Zone& zone = g.map().zones[a.zone];
        const std::int64_t dx = zone.x.floor_int() - tc->x;
        const std::int64_t dz = zone.z.floor_int() - tc->z;
        if (best < 0 || dx * dx + dz * dz < best) {
            best = dx * dx + dz * dz;
            den = {a.zone, zone.x.floor_int(), zone.z.floor_int()};
        }
    }
    REQUIRE(best >= 0);
    return den;
}

// How many times, in 6000 ticks, a wolf or a bear walks from the dark into
// the light of five `light`s set around the wolves' den.
int walks_into(const char* light, DayNightSettings cycle) {
    Game g(core(), map_for(kWolfMap), setup(cycle));
    provide(g);
    if (cycle.enabled()) {
        to_night(g);
    }
    const Den den = nearest_den(g);
    for (const auto& [dx, dz] : {std::pair{0, 0}, std::pair{10, 0}, std::pair{-10, 0}, std::pair{0, 10}, std::pair{0, -10}}) {
        REQUIRE(put(g, light, den.x + dx, den.z + dz).valid());
    }
    run(g, 1);
    CHECK(g.lit(den.x, den.z) == cycle.enabled());  // (The lit cells are only kept up at night.)
    CHECK(g.warded(den.x, den.z) == (cycle.enabled() && g.content().buildings[building(g, light)].wards));
    // By day, "the light" is where it would be: around the middle one.
    const std::int32_t reach = g.content().buildings[building(g, light)].light - 2;
    const auto in_light = [&](FixedVec2 p) {
        if (cycle.enabled()) {
            return g.lit(p.x.floor_int(), p.z.floor_int());
        }
        const std::int64_t dx = p.x.floor_int() - den.x, dz = p.z.floor_int() - den.z;
        return dx * dx + dz * dz <= static_cast<std::int64_t>(reach) * reach;
    };
    std::map<std::uint32_t, bool> was_in;
    int entered = 0;
    for (int t = 0; t < 6000; ++t) {
        g.step();
        for (std::size_t i = 0; i < g.creatures().size(); ++i) {
            const Creature& a = g.creatures().data()[i];
            if (!beast(a)) {
                continue;
            }
            const bool in = in_light(a.position);
            const std::uint32_t id = g.creatures().entities()[i].index;
            const auto it = was_in.find(id);
            if (it != was_in.end() && !it->second && in) {
                ++entered;
            }
            was_in[id] = in;
        }
    }
    return entered;
}

// A town with an explorer, in the night.
struct Scout {
    EntityId who;
    Den den;
};
Scout scout(Game& g) {
    provide(g);
    const Building* tc = g.buildings().get(g.player(0).town_center);
    REQUIRE(tc != nullptr);
    const EntityId hut = put(g, "core:explorer", tc->x + 14, tc->z);
    REQUIRE(hut.valid());
    for (int t = 0; t < 400 && g.buildings().get(hut)->workers.empty(); ++t) {
        run(g, 10);
    }
    REQUIRE(g.buildings().get(hut)->workers.size() == 1);
    Scout s;
    s.who = g.buildings().get(hut)->workers[0];
    to_night(g);
    s.den = nearest_den(g);
    return s;
}

void send(Game& g, EntityId who, FixedVec2 where) {
    Command c;
    c.type = CommandType::MoveVillager;
    c.entity = who;
    c.position = where;
    g.apply(c);
}

bool near(const Game& g, EntityId who, FixedVec2 where, std::int32_t meters) {
    const Villager* v = g.villagers().get(who);
    if (v == nullptr) {
        return false;
    }
    const FixedVec2 d = v->position - where;
    return abs(d.x) <= Fixed::from_int(meters) && abs(d.z) <= Fixed::from_int(meters);
}

// A dirt road from the explorer to `to`, with an iron lantern beside it every
// ten meters and a few around its end; all of it built and lit. (On open
// ground there are many ways just as short: the road is what makes the
// explorer take this one.)
void light_the_way(Game& g, EntityId who, FixedVec2 to) {
    NavGrid nav = g.nav();
    std::vector<FixedVec2> path;
    REQUIRE(nav.find_path(g.villagers().get(who)->position, to, path));
    const DefIndex road = building(g, "core:dirt_road");
    std::vector<std::pair<std::int32_t, std::int32_t>> cells;
    FixedVec2 at = g.villagers().get(who)->position;
    Fixed since = Fixed::from_int(10);
    for (const FixedVec2& next : path) {
        const FixedVec2 d = next - at;
        const Fixed len = d.length();
        for (Fixed done{}; done < len; done += Fixed::one()) {
            const FixedVec2 p = at + d * (done / len);
            const std::pair<std::int32_t, std::int32_t> cell{(p.x.floor_int() / 2) * 2, (p.z.floor_int() / 2) * 2};
            if (cells.empty() || cells.back() != cell) {
                cells.push_back(cell);
            }
            if (since >= Fixed::from_int(10)) {
                // Three meters to the side of the way.
                const FixedVec2 side{-d.z * (Fixed::from_int(3) / len), d.x * (Fixed::from_int(3) / len)};
                REQUIRE(put(g, "core:lantern_iron", (p + side).x.floor_int(), (p + side).z.floor_int()).valid());
                since = Fixed{};
            }
            since += Fixed::one();
        }
        at = next;
    }
    for (const auto& [dx, dz] : {std::pair{3, 3}, std::pair{-12, 0}, std::pair{12, 0}, std::pair{0, -12}, std::pair{0, 12}}) {
        REQUIRE(put(g, "core:lantern_iron", to.x.floor_int() + dx, to.z.floor_int() + dz).valid());
    }
    for (const auto& [x, z] : cells) {
        if (g.can_place(0, road, x, z, 0) == PlaceError::None) {
            Command c;
            c.type = CommandType::PlaceBuilding;
            c.def = road;
            c.position = {Fixed::from_int(x), Fixed::from_int(z)};
            g.apply(c);
        }
    }
    finish_all(g);
    REQUIRE(g.roads().size() * 10 >= cells.size() * 9);
    run(g, 1);
}

// The explorer goes to the wolves' den in the night. What became of it.
struct Journey {
    bool arrived = false;
    bool hurt = false;
    bool in_light_out_of_town = true;
    int ticks = 0;
};
Journey journey(bool lanterns) {
    Game g(core(), map_for(kWolfMap), setup(kLongNight));
    const Scout s = scout(g);
    const FixedVec2 den{Fixed::from_int(s.den.x), Fixed::from_int(s.den.z)};
    if (lanterns) {
        light_the_way(g, s.who, den);
    }
    const std::int32_t health = g.villagers().get(s.who)->health;
    const Building* tc = g.buildings().get(g.player(0).town_center);
    const std::int32_t tx = tc->x, tz = tc->z;
    send(g, s.who, den);
    Journey j;
    for (int t = 0; t < 12000 && !j.arrived; ++t) {
        g.step();
        REQUIRE(g.night());
        const Villager* v = g.villagers().get(s.who);
        if (v == nullptr) {
            j.hurt = true;
            break;
        }
        j.hurt = j.hurt || v->health < health;
        // (It may go by the town's stores for provisions first: the lit way begins at its hut.)
        const std::int64_t dx = v->position.x.floor_int() - tx, dz = v->position.z.floor_int() - tz;
        j.in_light_out_of_town = j.in_light_out_of_town && (dx * dx + dz * dz < 60 * 60 ||
                                                           g.warded(v->position.x.floor_int(), v->position.z.floor_int()));
        j.arrived = near(g, s.who, den, 3);
        ++j.ticks;
    }
    return j;
}

}  // namespace

TEST_SUITE("lanterns") {
    TEST_CASE("the base game's road lanterns and its beacon") {
        const Content& c = test::core_content();
        const auto def = [&](const char* id) -> const BuildingDef& {
            const DefIndex d = c.find_building(id);
            REQUIRE(d != kNoDef);
            return c.buildings[d];
        };
        const auto costs = [&](const BuildingDef& d, const char* resource) {
            for (const ResourceAmount& a : d.cost) {
                if (a.resource == c.find_resource(resource)) {
                    return a.amount;
                }
            }
            return 0;
        };
        const BuildingDef& wood = def("core:lantern_wood");
        const BuildingDef& iron = def("core:lantern_iron");
        const BuildingDef& stone = def("core:lantern_stone");
        const BuildingDef& beacon = def("core:beacon");
        for (const BuildingDef* d : {&wood, &iron, &stone}) {
            CAPTURE(d->id);
            CHECK(d->width == 1);
            CHECK(d->depth == 1);
            CHECK(d->wards);
            CHECK(d->cost.size() == 1);
        }
        // A log, 8 m; an iron, 16 m; four stones, 12 m, and it neither burns nor breaks as easily.
        CHECK(costs(wood, "core:log") == 1);
        CHECK(wood.light == 8);
        CHECK(costs(iron, "core:iron") == 1);
        CHECK(iron.light == 16);
        CHECK(costs(stone, "core:stone") == 4);
        CHECK(stone.light == 12);
        CHECK(stone.fireproof);
        CHECK_FALSE(wood.fireproof);
        CHECK_FALSE(iron.fireproof);
        CHECK(stone.hp == 3 * wood.hp);
        CHECK(iron.hp == wood.hp);
        // The beacon: a tower of 3 x 3 that lights 30 m.
        CHECK(beacon.width == 3);
        CHECK(beacon.depth == 3);
        CHECK(beacon.light == 30);
        CHECK(beacon.wards);
        CHECK(beacon.cost.size() == 2);
        CHECK(costs(beacon, "core:log") == 20);
        CHECK(costs(beacon, "core:stone") == 10);
        // The lights there were keep nobody out.
        CHECK_FALSE(def("core:torch").wards);
        CHECK_FALSE(def("core:campfire").wards);
        CHECK_FALSE(def("core:town_center").wards);
    }

    TEST_CASE("no wolf or bear walks into a road lantern's light at night; into a torch's, or by day, they do") {
        const int lantern = walks_into("core:lantern_stone", kLongNight);
        const int torch = walks_into("core:torch", kLongNight);
        const int by_day = walks_into("core:lantern_stone", kAlwaysDay);
        MESSAGE("times a beast walked into the light: lantern at night " << lantern << ", torch at night " << torch
                                                                         << ", lantern by day " << by_day);
        CHECK(lantern == 0);
        CHECK(torch > 0);
        CHECK(by_day > 0);
    }

    TEST_CASE("in the night, who crosses the wolves' land by a lit way gets there unhurt; in the dark, they are set upon") {
        const Journey lit = journey(true);
        const Journey dark = journey(false);
        MESSAGE("by the lit road: " << lit.ticks << " ticks; in the dark: " << dark.ticks << " ticks, arrived " << dark.arrived);
        CHECK(lit.arrived);
        CHECK(lit.in_light_out_of_town);
        CHECK_FALSE(lit.hurt);
        CHECK(dark.hurt);
    }

    TEST_CASE("a wolf that chases somebody stops at the edge of the light, and after a while it goes") {
        Game g(core(), map_for(kWolfMap), setup(kLongNight));
        const Scout s = scout(g);
        const FixedVec2 den{Fixed::from_int(s.den.x), Fixed::from_int(s.den.z)};
        light_the_way(g, s.who, den);
        send(g, s.who, den);
        for (int t = 0; t < 12000 && !near(g, s.who, den, 3); ++t) {
            g.step();
        }
        REQUIRE(near(g, s.who, den, 3));
        // Out of the light, toward the nearest wolf, until one comes for the explorer.
        const auto warded = [&](FixedVec2 p) { return g.warded(p.x.floor_int(), p.z.floor_int()); };
        EntityId wolf;
        for (int attempt = 0; attempt < 6 && !wolf.valid(); ++attempt) {
            const Villager* v = g.villagers().get(s.who);
            REQUIRE(v != nullptr);
            FixedVec2 nearest{};
            std::uint64_t best = ~std::uint64_t{0};
            for (const Creature& a : g.creatures().data()) {
                const FixedVec2 d = a.position - v->position;
                const auto d2 = static_cast<std::uint64_t>(d.x.floor_int() * static_cast<std::int64_t>(d.x.floor_int()) +
                                                           d.z.floor_int() * static_cast<std::int64_t>(d.z.floor_int()));
                if (a.kind == CreatureKind::Wolf && !warded(a.position) && d2 < best) {
                    best = d2;
                    nearest = a.position;
                }
            }
            REQUIRE(best != ~std::uint64_t{0});
            // The first dark point on the way to it, and six meters more.
            const FixedVec2 d = nearest - v->position;
            const Fixed len = d.length();
            REQUIRE(len > Fixed{});
            Fixed out{};
            while (out < len && warded(v->position + d * (out / len))) {
                out += Fixed::one();
            }
            send(g, s.who, v->position + d * (std::min(len, out + Fixed::from_int(6)) / len));
            for (int t = 0; t < 600 && !wolf.valid(); ++t) {
                g.step();
                REQUIRE(g.villagers().get(s.who) != nullptr);
                for (std::size_t i = 0; i < g.creatures().size(); ++i) {
                    const Creature& a = g.creatures().data()[i];
                    if (a.kind == CreatureKind::Wolf && a.state == CreatureState::Chase && a.target == s.who) {
                        wolf = g.creatures().entities()[i];
                    }
                }
            }
        }
        REQUIRE(wolf.valid());
        // Back into the light. The wolf comes after, as far as its edge.
        send(g, s.who, den);
        bool waited = false;
        bool entered = false;
        bool gave_up = false;
        std::uint16_t longest = 0;
        for (int t = 0; t < 1500 && !gave_up; ++t) {
            g.step();
            const Creature* a = g.creatures().get(wolf);
            REQUIRE(a != nullptr);
            entered = entered || warded(a->position);
            waited = waited || a->held > 0;
            longest = std::max(longest, a->held);
            gave_up = waited && a->state != CreatureState::Chase;
        }
        CHECK(waited);
        CHECK_FALSE(entered);
        CHECK(gave_up);
        CHECK(longest == village::kWardWaitTicks - 1);
        CHECK(g.villagers().get(s.who) != nullptr);
        CHECK(g.creatures().get(wolf)->held == 0);
    }

    TEST_CASE("raiders walk into the beacon's light all the same") {
        Game g(core(), map_for(93), setup(kLongNight, Threat::None, Threat::Medium));
        provide(g);
        to_night(g);
        const Building* tc = g.buildings().get(g.player(0).town_center);
        REQUIRE(tc != nullptr);
        const std::int32_t tx = tc->x, tz = tc->z;  // (Building more moves the buildings in memory.)
        REQUIRE(put(g, "core:beacon", tx + 12, tz).valid());
        run(g, 1);
        REQUIRE(g.warded(tx, tz));
        Command raid;
        raid.type = CommandType::DevRaid;
        g.apply(raid);
        bool raiders = false;
        bool in_the_light = false;
        for (int t = 0; t < 8000 && !in_the_light; ++t) {
            g.step();
            for (const Creature& a : g.creatures().data()) {
                if (a.kind == CreatureKind::Raider) {
                    raiders = true;
                    in_the_light = in_the_light || g.warded(a.position.x.floor_int(), a.position.z.floor_int());
                }
            }
        }
        CHECK(raiders);
        CHECK(in_the_light);
    }

    TEST_CASE("the developer's order finishes what is being built, roads too, and needs the developer tools") {
        Game g(core(), map_for(92), setup(kAlwaysDay, Threat::None));
        const Building* tc = g.buildings().get(g.player(0).town_center);
        REQUIRE(tc != nullptr);
        const std::int32_t tx = tc->x, tz = tc->z;
        const auto site = [&](const char* def) {
            const DefIndex d = building(g, def);
            for (std::int32_t r = 14; r < 80; r += 2) {
                for (const auto& [dx, dz] : {std::pair{r, 0}, std::pair{0, r}, std::pair{-r, 0}, std::pair{0, -r}}) {
                    const std::int32_t x = ((tx + dx) / 2) * 2, z = ((tz + dz) / 2) * 2;
                    if (g.can_place(0, d, x, z, 0) == PlaceError::None) {
                        Command c;
                        c.type = CommandType::PlaceBuilding;
                        c.def = d;
                        c.position = {Fixed::from_int(x), Fixed::from_int(z)};
                        g.apply(c);
                        return;
                    }
                }
            }
            FAIL("no room for " << def);
        };
        site("core:house");
        site("core:lantern_iron");
        site("core:dirt_road");
        const auto sites = [&] {
            int n = 0;
            for (const Building& b : g.buildings().data()) {
                n += b.state == BuildingState::Construction ? 1 : 0;
            }
            return n;
        };
        REQUIRE(sites() == 3);
        // Without the developer tools it is refused.
        g.set_dev_commands(false);
        const std::uint32_t rejected = g.rejected_commands();
        finish_all(g);
        CHECK(g.rejected_commands() == rejected + 1);
        CHECK(sites() == 3);
        g.set_dev_commands(true);
        const std::size_t buildings = g.buildings().size();
        // As bytes, like in a network game.
        Command order;
        order.type = CommandType::DevBuild;
        BinaryWriter wire;
        order.write(wire);
        BinaryReader in(wire.bytes());
        Command received;
        REQUIRE(Command::read(in, received));
        g.apply(received);
        CHECK(sites() == 0);
        CHECK(g.buildings().size() == buildings - 1);  // The stretch of road is ground now.
        CHECK(g.roads().size() == 1);
        // No iron was needed, and nothing is owed.
        for (const Building& b : g.buildings().data()) {
            CHECK(b.delivered.empty());
            CHECK(b.incoming.empty());
        }
        run(g, 200);
        CHECK(sites() == 0);
    }

    TEST_CASE("saving and loading keeps the lanterns, their light and a wolf's wait") {
        Game g(core(), map_for(kWolfMap), setup(kLongNight));
        provide(g);
        to_night(g);
        const Den den = nearest_den(g);
        REQUIRE(put(g, "core:lantern_stone", den.x, den.z).valid());
        run(g, 600);
        BinaryWriter w;
        g.save(w);
        Game loaded(core(), map_for(kWolfMap), setup(kLongNight));
        BinaryReader r(w.bytes());
        REQUIRE(loaded.load(r, core()));
        CHECK(loaded.hash() == g.hash());
        loaded.update_light();
        CHECK(loaded.night());
        CHECK(loaded.warded(den.x, den.z));
        CHECK(loaded.warded(den.x, den.z) == g.warded(den.x, den.z));
        run(g, 600);
        run(loaded, 600);
        CHECK(loaded.hash() == g.hash());
    }

    // Not a test: a saved game in the night, with the three lanterns along a
    // road and the beacon, to look at them lit. Run it by name:
    //   salvasprosperia_tests -ts=lanterns -tc="manual*" --no-skip
    // It writes <temp>/SalvasProsperia/manual_lanterns.scsave: copy it to the saves folder and load it.
    TEST_CASE("manual: a saved game in the night with lanterns and the beacon" * doctest::skip()) {
        std::error_code ec;
        const std::filesystem::path folder = std::filesystem::temp_directory_path(ec) / "SalvasProsperia";
        std::filesystem::create_directories(folder, ec);
        const std::filesystem::path file = folder / "manual_lanterns.scsave";
        GameSetup rules = setup(kLongNight, Threat::None);
        rules.rules.fog = FogMode::None;
        Game g(core(), map_for(92), rules);
        provide(g);
        const Building* tc = g.buildings().get(g.player(0).town_center);
        REQUIRE(tc != nullptr);
        const std::int32_t tx = tc->x, tz = tc->z;  // (Building more moves the buildings in memory.)
        const std::int32_t x0 = ((tx + 16) / 2) * 2, z0 = ((tz - 10) / 2) * 2;
        // A road going east, a lantern of each kind beside it, and the beacon at its end.
        for (std::int32_t x = x0; x <= x0 + 60; x += 2) {
            if (g.can_place(0, building(g, "core:dirt_road"), x, z0, 0) == PlaceError::None) {
                Command c;
                c.type = CommandType::PlaceBuilding;
                c.def = building(g, "core:dirt_road");
                c.position = {Fixed::from_int(x), Fixed::from_int(z0)};
                g.apply(c);
            }
        }
        finish_all(g);
        CHECK(put(g, "core:lantern_wood", x0 + 6, z0 + 3).valid());
        CHECK(put(g, "core:lantern_iron", x0 + 22, z0 + 3).valid());
        CHECK(put(g, "core:lantern_stone", x0 + 40, z0 + 3).valid());
        CHECK(put(g, "core:beacon", x0 + 64, z0 - 1).valid());
        CHECK(put(g, "core:torch", x0 + 6, z0 + 14).valid());
        to_night(g);
        run(g, 20);
        save::SaveData data;
        data.header.name = "lanterns";
        data.header.game_version = SC_VERSION_STRING;
        data.header.saved_at = "2026-10-04T00:00:00";
        data.header.rules_version = kGameRulesVersion;
        data.header.content_hash = g.content().hash;
        data.header.seed = g.map().settings.seed;
        data.header.tick = g.tick();
        data.header.population = static_cast<std::uint32_t>(g.population(0));
        BinaryWriter w;
        g.save(w);
        data.put("GAME", std::move(w.bytes()));
        REQUIRE(save::write_file(file, data));
        MESSAGE("road from cell (" << x0 << ", " << z0 << "); town center at (" << tx << ", " << tz << ")");
    }
}
