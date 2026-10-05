// Founding the town (phase 73): a game starts with no towns; each seat
// founds its own anywhere the ground allows; the settlers come with a wagon
// that keeps their goods, and build the town center themselves.
#include <doctest.h>

#include <memory>
#include <optional>

#include "sim/game.h"
#include "sim/worldgen.h"
#include "test_util.h"

using namespace sc::sim;

namespace {

std::shared_ptr<const Content> content() {
    return std::shared_ptr<const Content>(std::shared_ptr<const Content>{}, &sc::test::core_content());
}

MapData small_map(std::uint64_t seed, std::uint8_t players = 1) {
    MapSettings s;
    s.seed = seed;
    s.size = MapSize::Small;
    s.sea = Sea::None;
    s.players = players;
    std::optional<MapData> m = generate_map(s, *content());
    REQUIRE(m.has_value());
    return std::move(*m);
}

// A game as the game makes it: nobody has a town yet.
Game unfounded(std::uint64_t seed, std::uint8_t players = 1, FogMode fog = FogMode::None, bool shared = false) {
    GameSetup setup;
    setup.players = players;
    setup.seed = seed;
    setup.shared_town = shared;
    setup.rules.fog = fog;
    setup.start_towns = false;
    return Game(content(), small_map(seed, players), setup);
}

Command found_at(std::uint8_t player, std::int32_t x, std::int32_t z, std::uint8_t rotation = 0) {
    Command c;
    c.type = CommandType::FoundTown;
    c.player = player;
    c.position = {Fixed::from_int(x), Fixed::from_int(z)};
    c.value = rotation;
    return c;
}

// The corner that puts the town center's middle on a suggested site.
std::pair<std::int32_t, std::int32_t> corner_at(const Game& g, std::size_t site) {
    const BuildingDef& d = g.content().buildings[g.town_center_def()];
    const StartPosition& s = g.map().starts[site];
    return {s.x.floor_int() - d.width / 2, s.z.floor_int() - d.depth / 2};
}

bool found_on_site(Game& g, std::uint8_t player, std::size_t site) {
    const auto [x, z] = corner_at(g, site);
    const std::uint32_t before = g.rejected_commands();
    g.apply(found_at(player, x, z));
    return g.rejected_commands() == before;
}

const Building* cart_of(const Game& g, std::uint8_t player) {
    return g.buildings().get(g.player(player).cart);
}

const Building* center_of(const Game& g, std::uint8_t player) {
    return g.buildings().get(g.player(player).town_center);
}

std::int32_t amount(const Building& b, DefIndex r) {
    std::int32_t n = 0;
    for (const Stock& s : b.stock) {
        n += s.resource == r ? s.amount : 0;
    }
    return n;
}

DefIndex resource(const char* id) {
    const DefIndex r = content()->find_resource(id);
    REQUIRE(r != kNoDef);
    return r;
}

// A water cell away from the map's edge, if the map has one.
std::optional<std::pair<std::int32_t, std::int32_t>> water_cell(const Game& g) {
    for (std::int32_t z = 20; z < g.map().size - 20; z += 3) {
        for (std::int32_t x = 20; x < g.map().size - 20; x += 3) {
            if (g.map().water_at(x, z)) {
                return std::pair{x, z};
            }
        }
    }
    return std::nullopt;
}

}  // namespace

TEST_SUITE("founding") {
    TEST_CASE("a new game has no towns and waits for its founders") {
        Game g = unfounded(11);
        CHECK(g.player_count() == 1);
        CHECK(g.buildings().size() == 0);
        CHECK(g.villagers().size() == 0);
        CHECK(g.population(0) == 0);
        CHECK(g.awaiting_founders());
        CHECK_FALSE(g.founded(0));
        CHECK(g.founder(0));
        for (int i = 0; i < 50; ++i) {
            g.step();
        }
        CHECK(g.tick() == 0);       // No time goes by...
        CHECK(g.waited() == 50);    // ...but the steps are counted,
        CHECK(g.turn() == 50);      // for multiplayer's turns.
        CHECK_FALSE(g.game_over());
        CHECK(g.take_events().empty());
    }

    TEST_CASE("a seat without a town can only found it") {
        Game g = unfounded(11);
        const DefIndex house = content()->find_building("core:house");
        REQUIRE(house != kNoDef);
        const auto [x, z] = corner_at(g, 0);
        Command c;
        c.type = CommandType::PlaceBuilding;
        c.def = house;
        c.position = {Fixed::from_int(x), Fixed::from_int(z)};
        g.apply(c);
        CHECK(g.rejected_commands() == 1);
        CHECK(g.buildings().size() == 0);
        c.type = CommandType::RingBell;
        c.value = 1;
        g.apply(c);
        CHECK(g.rejected_commands() == 2);
    }

    TEST_CASE("founding brings settlers, a wagon with the goods and the center as a site") {
        Game g = unfounded(11);
        REQUIRE(g.cart_def() != kNoDef);
        const auto [x, z] = corner_at(g, 0);
        REQUIRE(g.can_found(0, x, z, 0) == PlaceError::None);
        REQUIRE(found_on_site(g, 0, 0));
        CHECK(g.founded(0));
        CHECK_FALSE(g.awaiting_founders());
        CHECK(g.population(0) == village::kStartVillagers);
        CHECK(g.buildings().size() == 2);
        const Building* tc = center_of(g, 0);
        const Building* cart = cart_of(g, 0);
        REQUIRE(tc != nullptr);
        REQUIRE(cart != nullptr);
        CHECK(tc->state == BuildingState::Construction);
        CHECK(tc->x == x);
        CHECK(tc->z == z);
        CHECK(tc->stock.empty());
        CHECK(cart->state == BuildingState::Complete);
        CHECK(content()->buildings[cart->def].cart);
        // The goods of today's start, plus what the center costs.
        const BuildingDef& center = content()->buildings[tc->def];
        REQUIRE(!center.cost.empty());
        std::int32_t cost_logs = 0;
        for (const ResourceAmount& c : center.cost) {
            cost_logs += c.resource == resource("core:log") ? c.amount : 0;
        }
        CHECK(amount(*cart, resource("core:log")) == 60 + cost_logs);
        CHECK(amount(*cart, resource("core:berries")) == 188);
        CHECK(amount(*cart, resource("core:gold")) == 100);
        CHECK(g.gold(0) == 100);
        // Everybody stands on ground they can walk.
        for (const Villager& v : g.villagers().data()) {
            CHECK(g.nav().walkable(v.position.x.floor_int() / NavGrid::kCellMeters,
                                   v.position.z.floor_int() / NavGrid::kCellMeters));
        }
        bool founded_event = false, started_event = false;
        for (const Game::Event& e : g.take_events()) {
            founded_event = founded_event || (e.kind == Game::Event::Kind::TownFounded && e.owner == 0);
            started_event = started_event || e.kind == Game::Event::Kind::GameStarted;
        }
        CHECK(founded_event);
        CHECK(started_event);
        g.step();
        CHECK(g.tick() == 1);
    }

    TEST_CASE("the settlers build the center from the wagon, which then goes") {
        Game g = unfounded(11);
        REQUIRE(found_on_site(g, 0, 0));
        const DefIndex log = resource("core:log");
        const DefIndex stone = resource("core:stone");
        const DefIndex gold = resource("core:gold");
        const std::vector<std::int32_t> before = g.stored(0);
        const BuildingDef& center = content()->buildings[g.town_center_def()];
        std::int32_t cost_logs = 0, cost_stone = 0;
        for (const ResourceAmount& c : center.cost) {
            cost_logs += c.resource == log ? c.amount : 0;
            cost_stone += c.resource == stone ? c.amount : 0;
        }
        int ticks = 0;
        while (center_of(g, 0) != nullptr && center_of(g, 0)->state != BuildingState::Complete && ticks < 20000) {
            g.step();
            ++ticks;
        }
        MESSAGE("town center built in " << ticks << " ticks");
        const Building* tc = center_of(g, 0);
        REQUIRE(tc != nullptr);
        REQUIRE(tc->state == BuildingState::Complete);
        CHECK(cart_of(g, 0) == nullptr);
        CHECK_FALSE(g.player(0).cart.valid());
        CHECK(g.buildings().size() == 1);
        // Nothing was lost on the way: what the wagon had, less the cost.
        const std::vector<std::int32_t> after = g.stored(0);
        CHECK(after[log] == before[log] - cost_logs);
        CHECK(after[stone] == before[stone] - cost_stone);
        CHECK(after[gold] == before[gold]);
        CHECK(amount(*tc, gold) == before[gold]);
        CHECK(g.population(0) == village::kStartVillagers);
        CHECK(g.rejected_commands() == 0);
    }

    TEST_CASE("founding is refused on water, off the map, over a building and twice") {
        Game g = unfounded(15, 2);
        const std::int32_t size = g.map().size;
        CHECK(g.can_found(0, 0, 0, 0) == PlaceError::OutsideMap);
        CHECK(g.can_found(0, size - 6, size - 6, 0) == PlaceError::OutsideMap);
        if (const auto wet = water_cell(g)) {
            CHECK(g.can_found(0, wet->first - 2, wet->second - 2, 0) == PlaceError::Water);
            g.apply(found_at(0, wet->first - 2, wet->second - 2));
            CHECK(g.rejected_commands() == 1);
            CHECK(g.buildings().size() == 0);
        } else {
            MESSAGE("this map has no water to try");
        }
        const std::uint32_t rejected = g.rejected_commands();
        REQUIRE(found_on_site(g, 0, 0));
        const auto [x, z] = corner_at(g, 0);
        // The same seat again, there or anywhere.
        CHECK(g.can_found(0, x + 40, z, 0) == PlaceError::Unique);
        g.apply(found_at(0, x + 40, z));
        CHECK(g.rejected_commands() == rejected + 1);
        // Another seat over the first one's center, or its wagon.
        CHECK(g.can_found(1, x + 2, z + 2, 0) == PlaceError::Blocked);
        const Building* cart = cart_of(g, 0);
        REQUIRE(cart != nullptr);
        CHECK(g.can_found(1, cart->x - 1, cart->z - 1, 0) == PlaceError::Blocked);
        // A seat that is not in the game.
        CHECK(g.can_found(5, x + 60, z, 0) == PlaceError::NotYours);
        CHECK(g.buildings().size() == 2);
    }

    TEST_CASE("the game waits for every founder, and two towns may stand side by side") {
        Game g = unfounded(15, 2);
        REQUIRE(g.player_count() == 2);
        REQUIRE(found_on_site(g, 0, 0));
        CHECK(g.awaiting_founders());
        for (int i = 0; i < 20; ++i) {
            g.step();
        }
        CHECK(g.tick() == 0);
        // Right beside the first: no reserved ground, no minimum distance.
        const Building* first = center_of(g, 0);
        REQUIRE(first != nullptr);
        std::optional<std::pair<std::int32_t, std::int32_t>> near;
        for (std::int32_t d = first->width + 3; d < 40 && !near; ++d) {
            for (const auto& [dx, dz] : {std::pair{d, 0}, std::pair{-d, 0}, std::pair{0, d}, std::pair{0, -d}}) {
                if (g.can_found(1, first->x + dx, first->z + dz, 0) == PlaceError::None) {
                    near = std::pair{first->x + dx, first->z + dz};
                    break;
                }
            }
        }
        REQUIRE(near.has_value());
        g.apply(found_at(1, near->first, near->second));
        CHECK(g.rejected_commands() == 0);
        CHECK(g.founded(1));
        CHECK_FALSE(g.awaiting_founders());
        CHECK(g.population(1) == village::kStartVillagers);
        const Building* second = center_of(g, 1);
        REQUIRE(second != nullptr);
        first = center_of(g, 0);  // The store may have moved it.
        REQUIRE(first != nullptr);
        CHECK(std::abs(second->x - first->x) + std::abs(second->z - first->z) < 60);
        for (int i = 0; i < 600; ++i) {
            g.step();
        }
        CHECK(g.tick() == 600);
        CHECK(g.population(0) == village::kStartVillagers);
        CHECK(g.population(1) == village::kStartVillagers);
        CHECK_FALSE(g.game_over());
    }

    TEST_CASE("a house can be placed while the center is still a site") {
        Game g = unfounded(11);
        REQUIRE(found_on_site(g, 0, 0));
        const DefIndex house = content()->find_building("core:house");
        const Building* tc = center_of(g, 0);
        REQUIRE(tc != nullptr);
        REQUIRE(tc->state == BuildingState::Construction);
        CHECK(g.tier(0) == 1);
        bool placed = false;
        for (std::int32_t r = 12; r < 60 && !placed; r += 2) {
            for (std::int32_t dx = -r; dx <= r && !placed; dx += 2) {
                if (g.can_place(0, house, tc->x + dx, tc->z + r, 0) == PlaceError::None) {
                    Command c;
                    c.type = CommandType::PlaceBuilding;
                    c.def = house;
                    c.position = {Fixed::from_int(tc->x + dx), Fixed::from_int(tc->z + r)};
                    g.apply(c);
                    placed = true;
                }
            }
        }
        REQUIRE(placed);
        CHECK(g.rejected_commands() == 0);
        CHECK(g.buildings().size() == 3);
        // Both get built, the wagon feeding the two sites.
        int ticks = 0;
        const auto all_built = [&] {
            for (const Building& b : g.buildings().data()) {
                if (b.state != BuildingState::Complete) {
                    return false;
                }
            }
            return true;
        };
        while (!all_built() && ticks < 30000) {
            g.step();
            ++ticks;
        }
        CHECK(all_built());
        CHECK(g.buildings().size() == 2);  // Center and house; the wagon is gone.
    }

    TEST_CASE("the wagon is neither built nor removed by the player") {
        Game g = unfounded(11);
        REQUIRE(found_on_site(g, 0, 0));
        const Building* tc = center_of(g, 0);
        REQUIRE(tc != nullptr);
        CHECK(g.can_place(0, g.cart_def(), tc->x + 30, tc->z, 0) == PlaceError::UnknownBuilding);
        Command c;
        c.type = CommandType::RemoveBuilding;
        c.entity = g.player(0).cart;
        g.apply(c);
        CHECK(g.rejected_commands() == 1);
        CHECK(cart_of(g, 0) != nullptr);
        c.entity = g.player(0).town_center;
        g.apply(c);
        CHECK(g.rejected_commands() == 2);
        CHECK(center_of(g, 0) != nullptr);
    }

    TEST_CASE("in a common town only its first seat founds, and everybody shares it") {
        Game g = unfounded(11, 3, FogMode::None, true);
        CHECK(g.founder(0));
        CHECK_FALSE(g.founder(1));
        const auto [x, z] = corner_at(g, 0);
        CHECK(g.can_found(1, x, z, 0) == PlaceError::NotYours);
        g.apply(found_at(1, x, z));
        CHECK(g.rejected_commands() == 1);
        CHECK(g.awaiting_founders());
        REQUIRE(found_on_site(g, 0, 0));
        CHECK_FALSE(g.awaiting_founders());
        CHECK(g.founded(2));
        CHECK(g.player(2).town_center == g.player(0).town_center);
        CHECK(g.player(2).cart == g.player(0).cart);
        CHECK(g.population(0) == village::kStartVillagers);
    }

    TEST_CASE("with fog, a town is founded on ground nobody has seen and sees around it") {
        Game g = unfounded(11, 1, FogMode::Static);
        REQUIRE(g.fog());
        const auto [x, z] = corner_at(g, 0);
        CHECK_FALSE(g.vision().explored_at(g.vision_group(0), x, z));
        CHECK(g.can_found(0, x, z, 0) == PlaceError::None);
        REQUIRE(found_on_site(g, 0, 0));
        CHECK(g.vision().explored_at(g.vision_group(0), x, z));
        CHECK(g.vision().explored_at(g.vision_group(0), x + 30, z));
    }

    TEST_CASE("saving and loading before founding and with the center half built") {
        Game g = unfounded(15, 2);
        REQUIRE(found_on_site(g, 0, 0));
        for (int i = 0; i < 7; ++i) {
            g.step();  // Still waiting for the second seat.
        }
        {
            BinaryWriter w;
            g.save(w);
            Game back(content(), MapData{}, 0, 0);
            BinaryReader r(w.bytes());
            REQUIRE(back.load(r, content()));
            CHECK(back.hash() == g.hash());
            CHECK(back.awaiting_founders());
            CHECK(back.waited() == 7);
            CHECK(back.founded(0));
            CHECK_FALSE(back.founded(1));
            CHECK(back.player(0).cart == g.player(0).cart);
        }
        REQUIRE(found_on_site(g, 1, 1));
        for (int i = 0; i < 150; ++i) {
            g.step();
        }
        const Building* tc = center_of(g, 0);
        REQUIRE(tc != nullptr);
        REQUIRE(tc->state == BuildingState::Construction);
        BinaryWriter w;
        g.save(w);
        Game back(content(), MapData{}, 0, 0);
        BinaryReader r(w.bytes());
        REQUIRE(back.load(r, content()));
        CHECK(back.hash() == g.hash());
        CHECK(back.turn() == g.turn());
        for (int i = 0; i < 3000; ++i) {
            g.step();
            back.step();
        }
        CHECK(back.hash() == g.hash());
    }

    TEST_CASE("towns that stand from the start are as before: center built, goods inside, no wagon") {
        Game g(content(), small_map(11), 1, 11);
        CHECK_FALSE(g.awaiting_founders());
        CHECK(g.founded(0));
        const Building* tc = center_of(g, 0);
        REQUIRE(tc != nullptr);
        CHECK(tc->state == BuildingState::Complete);
        CHECK(cart_of(g, 0) == nullptr);
        CHECK(g.buildings().size() == 1);
        CHECK(amount(*tc, resource("core:log")) == 60);
        CHECK(g.can_found(0, tc->x + 40, tc->z, 0) == PlaceError::Unique);
    }
}
