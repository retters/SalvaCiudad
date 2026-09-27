#include <doctest.h>

#include <map>
#include <memory>
#include <optional>
#include <ostream>
#include <tuple>

#include "sim/game.h"
#include "sim/worldgen.h"
#include "test_util.h"

using namespace sc::sim;

namespace {

std::shared_ptr<const Content> core() {
    return std::shared_ptr<const Content>(std::shared_ptr<const Content>{}, &sc::test::core_content());
}

const MapData& map_for(std::uint64_t seed, std::uint8_t players = 1, bool separate = false) {
    static std::map<std::tuple<std::uint64_t, std::uint8_t, bool>, MapData> cache;
    const auto key = std::make_tuple(seed, players, separate);
    auto it = cache.find(key);
    if (it == cache.end()) {
        MapSettings s;
        s.seed = seed;
        s.size = MapSize::Small;
        s.players = players;
        s.separate = separate;
        std::optional<MapData> m = generate_map(s, sc::test::core_content());
        REQUIRE(m.has_value());
        it = cache.emplace(key, std::move(*m)).first;
    }
    return it->second;
}

GameSetup setup(std::uint8_t players = 1) {
    GameSetup s;
    s.players = players;
    s.seed = 14;
    s.rules.climate.seasons = 0b0010;  // Summer.
    s.rules.diseases = Threat::None;
    s.rules.fires = Threat::None;
    return s;
}

void run(Game& g, std::uint32_t ticks) {
    for (std::uint32_t i = 0; i < ticks; ++i) {
        g.step();
    }
}

void grant(Game& g, const char* resource, std::int32_t amount, std::uint8_t player = 0) {
    Command c;
    c.type = CommandType::DevGrant;
    c.player = player;
    c.def = g.content().find_resource(resource);
    REQUIRE(c.def != kNoDef);
    c.value = amount;
    g.apply(c);
}

EntityId build(Game& g, const char* def, std::uint8_t player = 0) {
    grant(g, "core:log", 200, player);
    grant(g, "core:stone", 100, player);
    const DefIndex d = g.content().find_building(def);
    REQUIRE(d != kNoDef);
    const Building* tc = g.buildings().get(g.player(player).town_center);
    REQUIRE(tc != nullptr);
    for (int r = 12; r < 140; r += 2) {
        for (int a = 0; a < 8; ++a) {
            const int x = tc->x + (a % 3 - 1) * r;
            const int z = tc->z + (a / 3 - 1) * r;
            if (g.can_place(player, d, x, z, 0) != PlaceError::None) {
                continue;
            }
            Command c;
            c.type = CommandType::PlaceBuilding;
            c.player = player;
            c.def = d;
            c.position = {Fixed::from_int(x), Fixed::from_int(z)};
            g.apply(c);
            EntityId id;
            for (std::size_t i = 0; i < g.buildings().size(); ++i) {
                const Building& b = g.buildings().data()[i];
                if (b.def == d && b.x == x && b.z == z) {
                    id = g.buildings().entities()[i];
                }
            }
            REQUIRE(id.valid());
            for (int t = 0; t < 80 && g.buildings().get(id)->state != BuildingState::Complete; ++t) {
                run(g, 100);
            }
            REQUIRE(g.buildings().get(id)->state == BuildingState::Complete);
            return id;
        }
    }
    FAIL("no room for " << def);
    return {};
}

void wait_for_merchant(Game& g, std::uint8_t player = 0) {
    for (int t = 0; t < 40 && !g.merchant_here(player); ++t) {
        run(g, 100);
    }
    REQUIRE(g.merchant_here(player));
}

std::int32_t amount(const Game& g, const char* resource, std::uint8_t player = 0) {
    return g.tradeable(player, g.content().find_resource(resource));
}

// A town's gold: in its buildings and in its villagers' hands.
std::int32_t gold(const Game& g, std::uint8_t player) {
    std::int32_t n = g.gold(player);
    for (const Villager& v : g.villagers().data()) {
        n += v.owner == player && v.carrying.resource == g.gold() ? v.carrying.amount : 0;
    }
    return n;
}

Command offer(std::uint8_t from, std::uint8_t to, DefIndex give, std::int32_t n, DefIndex want, std::int32_t m) {
    Command c;
    c.type = CommandType::OfferTrade;
    c.player = from;
    c.count = to;
    c.def = give;
    c.value = n;
    c.def2 = want;
    c.value2 = m;
    return c;
}

Command answer(std::uint8_t player, std::uint32_t id, bool yes) {
    Command c;
    c.type = CommandType::AnswerOffer;
    c.player = player;
    c.value = static_cast<std::int32_t>(id);
    c.count = yes ? 1 : 0;
    return c;
}

}  // namespace

TEST_SUITE("trade") {
    TEST_CASE("trade commands round-trip") {
        const Command c = offer(1, 2, 3, 40, 5, 25);
        BinaryWriter w;
        c.write(w);
        BinaryReader r(w.bytes());
        Command back;
        REQUIRE(Command::read(r, back));
        CHECK(back == c);
        // To oneself, or the same good both ways: refused when read.
        for (const Command& bad : {offer(1, 1, 3, 40, 4, 25), offer(1, 2, 3, 40, 3, 25), offer(1, 2, 3, 0, 4, 25)}) {
            BinaryWriter wb;
            bad.write(wb);
            BinaryReader rb(wb.bytes());
            CHECK_FALSE(Command::read(rb, back));
        }
    }

    TEST_CASE("a merchant comes to the trading post and trades") {
        Game g(core(), map_for(81), setup());
        CHECK(gold(g, 0) == 100);
        CHECK_FALSE(g.merchant_here(0));
        const EntityId post = build(g, "core:trading_post");
        bool arrived = false;
        for (int t = 0; t < 40 && !g.merchant_here(0); ++t) {
            run(g, 100);
            for (const Game::Event& e : g.take_events()) {
                arrived = arrived || e.kind == Game::Event::Kind::MerchantArrived;
            }
        }
        REQUIRE(g.merchant_here(0));
        CHECK(arrived);
        const std::vector<MerchantGood>& goods = g.player(0).merchant;
        REQUIRE(!goods.empty());
        for (const MerchantGood& m : goods) {
            CHECK(m.buy > m.sell);
            CHECK(g.content().resources[m.resource].value > 0);
        }
        // Sell logs.
        const DefIndex log = g.content().find_resource("core:log");
        const std::int32_t logs = amount(g, "core:log");
        REQUIRE(logs >= 10);
        std::int32_t sell = 0;
        for (const MerchantGood& m : goods) {
            sell = m.resource == log ? m.sell : sell;
        }
        Command c;
        c.type = CommandType::Trade;
        c.entity = post;
        c.def = log;
        c.value = -10;
        g.apply(c);
        CHECK(amount(g, "core:log") == logs - 10);
        CHECK(gold(g, 0) == 100 + 10 * sell);
        // Buy something he has.
        const MerchantGood* stocked = nullptr;
        for (const MerchantGood& m : goods) {
            stocked = m.stock > 0 && stocked == nullptr ? &m : stocked;
        }
        REQUIRE(stocked != nullptr);
        const DefIndex r = stocked->resource;
        const std::int32_t price = stocked->buy;
        const std::int32_t coins = gold(g, 0);
        const std::int32_t before = g.tradeable(0, r);
        const std::int32_t n = std::min(stocked->stock, g.gold(0) / price);
        REQUIRE(n > 0);
        c.def = r;
        c.value = n;
        g.apply(c);
        CHECK(gold(g, 0) == coins - n * price);
        CHECK(g.tradeable(0, r) == before + n);
        // More than he has, or more than the town can pay: refused.
        const auto rejected = g.rejected_commands();
        c.value = kMaxTrade;
        g.apply(c);
        CHECK(g.rejected_commands() == rejected + 1);
    }

    TEST_CASE("no merchant, no trade") {
        Game g(core(), map_for(82), setup());
        const EntityId post = build(g, "core:trading_post");
        Command c;
        c.type = CommandType::Trade;
        c.entity = post;
        c.def = g.content().find_resource("core:log");
        c.value = -10;
        const auto rejected = g.rejected_commands();
        g.apply(c);
        CHECK(g.rejected_commands() == rejected + 1);
        CHECK(gold(g, 0) == 100);
    }

    TEST_CASE("two towns trade by caravan") {
        Game g(core(), map_for(83, 2), setup(2));
        REQUIRE(g.player_count() == 2);
        const DefIndex log = g.content().find_resource("core:log");
        const DefIndex stone = g.content().find_resource("core:stone");
        const std::int32_t logs0 = amount(g, "core:log", 0);
        g.apply(offer(0, 1, log, 30, g.gold(), 20));
        REQUIRE(g.offers().size() == 1);
        CHECK(amount(g, "core:log", 0) == logs0 - 30);  // Set aside.
        const std::uint32_t id = g.offers()[0].id;
        // Only the receiver accepts.
        auto rejected = g.rejected_commands();
        g.apply(answer(0, id, true));
        CHECK(g.rejected_commands() == rejected + 1);
        const std::int32_t logs1 = amount(g, "core:log", 1);
        g.apply(answer(1, id, true));
        CHECK(g.offers().empty());
        CHECK(g.caravans().size() == 2);
        CHECK(gold(g, 1) == 80);
        const std::uint64_t travel = g.travel_ticks(0, 1);
        CHECK(travel >= g.day_ticks());
        run(g, static_cast<std::uint32_t>(travel + g.day_ticks()));
        CHECK(g.caravans().empty());
        CHECK(gold(g, 0) == 120);
        CHECK(amount(g, "core:log", 1) >= logs1 + 30 - 5);  // Villagers may use a few meanwhile.

        // Declined: the goods go back.
        const std::int32_t stone0 = amount(g, "core:stone", 0);
        g.apply(offer(0, 1, stone, 10, log, 10));
        REQUIRE(g.offers().size() == 1);
        g.apply(answer(1, g.offers()[0].id, false));
        CHECK(g.offers().empty());
        CHECK(amount(g, "core:stone", 0) == stone0);
        // Unanswered: back after a month.
        g.apply(offer(0, 1, g.gold(), 50, log, 10));
        CHECK(gold(g, 0) == 70);
        run(g, g.month_ticks() + g.day_ticks());
        CHECK(g.offers().empty());
        CHECK(gold(g, 0) == 120);
        // More than the town has: refused.
        rejected = g.rejected_commands();
        g.apply(offer(0, 1, g.gold(), 5000, log, 10));
        CHECK(g.rejected_commands() == rejected + 1);
    }

    TEST_CASE("a common town does not trade with itself") {
        GameSetup s = setup(2);
        s.shared_town = true;
        Game g(core(), map_for(84), s);
        const auto rejected = g.rejected_commands();
        g.apply(offer(0, 1, g.gold(), 10, g.content().find_resource("core:log"), 10));
        CHECK(g.rejected_commands() == rejected + 1);
        CHECK(g.offers().empty());
    }

    TEST_CASE("separate maps are regions nobody crosses") {
        const MapData& m = map_for(85, 3, true);
        CHECK(world_grid(m.settings) == 2);
        CHECK(m.size == 1024);
        CHECK(m.region_size() == 512);
        REQUIRE(m.starts.size() == 3);
        for (std::size_t p = 0; p < 3; ++p) {
            CHECK(m.region_at(m.starts[p].x.floor_int(), m.starts[p].z.floor_int()) == static_cast<std::int32_t>(p));
        }
        // The same seed gives the same world; each map is its own.
        MapSettings s = m.settings;
        std::optional<MapData> again = generate_map(s, sc::test::core_content());
        REQUIRE(again.has_value());
        CHECK(again->checksum() == m.checksum());
        s.separate = false;
        s.players = 1;
        s.seed = m.settings.seed + 1;
        std::optional<MapData> second = generate_map(s, sc::test::core_content());
        REQUIRE(second.has_value());
        CHECK(second->height_cm(100, 100) == m.height_cm(512 + 100, 100));

        Game g(core(), m, setup(3));
        REQUIRE(g.player_count() == 3);
        for (std::uint8_t p = 0; p < 3; ++p) {
            const Building* tc = g.buildings().get(g.player(p).town_center);
            REQUIRE(tc != nullptr);
            CHECK(m.region_at(tc->x, tc->z) == p);
            const Game::Region r = g.region(p);
            CHECK(r.size == 512);
        }
        // Player 0 cannot build in player 1's map.
        const Building* tc1 = g.buildings().get(g.player(1).town_center);
        CHECK(g.can_place(0, g.content().find_building("core:house"), tc1->x + 20, tc1->z, 0) == PlaceError::OutsideMap);
        // No path from one map to another.
        const Building* tc0 = g.buildings().get(g.player(0).town_center);
        CHECK_FALSE(g.nav().connected(g.door(*tc0), g.door(*tc1)));
        // Caravans: a day to load and five per square.
        CHECK(g.travel_ticks(0, 1) == 6u * g.day_ticks());
        CHECK(g.travel_ticks(0, 2) == 6u * g.day_ticks());
        run(g, 2000);  // Villagers stay home.
        for (const Villager& v : g.villagers().data()) {
            CHECK(m.region_at(v.position.x.floor_int(), v.position.z.floor_int()) == v.owner);
        }
    }

    TEST_CASE("trade survives a save") {
        Game g(core(), map_for(83, 2), setup(2));
        (void)build(g, "core:trading_post");
        wait_for_merchant(g);
        const DefIndex log = g.content().find_resource("core:log");
        g.apply(offer(0, 1, log, 20, g.gold(), 10));
        g.apply(offer(1, 0, g.gold(), 30, log, 10));
        g.apply(answer(0, g.offers()[1].id, true));
        REQUIRE(g.offers().size() == 1);
        REQUIRE(g.caravans().size() == 2);
        BinaryWriter w;
        g.save(w);
        Game back(core(), map_for(81), setup());
        BinaryReader r(w.bytes());
        REQUIRE(back.load(r, core()));
        CHECK(back.hash() == g.hash());
        CHECK(back.offers() == g.offers());
        CHECK(back.caravans() == g.caravans());
        CHECK(back.player(0).merchant == g.player(0).merchant);
        run(g, 1500);
        run(back, 1500);
        CHECK(back.hash() == g.hash());
    }
}

namespace {

Command set_reserve(EntityId post, std::int32_t n) {
    Command c;
    c.type = CommandType::SetLimit;
    c.entity = post;
    c.value = n;
    return c;
}

// Runs until `done` holds (checked each day), checking on the way that the
// town's gold stays `total`.
template <typename F>
bool run_until(Game& g, std::int32_t total, F done, int days = 120) {
    for (int d = 0; d < days; ++d) {
        if (done()) {
            return true;
        }
        run(g, 100);
        if (gold(g, 0) != total) {
            FAIL_CHECK("the town's gold changed to " << gold(g, 0) << " from " << total);
            return false;
        }
    }
    return done();
}

}  // namespace

TEST_SUITE("gold") {
    TEST_CASE("gold is a resource that starts in the town center") {
        const DefIndex gold_def = sc::test::core_content().find_resource("core:gold");
        REQUIRE(gold_def != kNoDef);
        CHECK(sc::test::core_content().resources[gold_def].value == 0);  // Merchants do not trade it.
        CHECK(sc::test::core_content().resources[gold_def].category == ResourceCategory::Gold);
        for (const auto& [start, expected] : {std::pair{StartGoods::Scarce, 50}, std::pair{StartGoods::Normal, 100},
                                              std::pair{StartGoods::Plenty, 200}}) {
            GameSetup s = setup();
            s.rules.start = start;
            Game g(core(), map_for(81), s);
            REQUIRE(g.gold() == gold_def);
            CHECK(g.gold(0) == expected);
            const Game::GoldPlaces places = g.gold_places(0);
            CHECK(places.others == expected);  // The town center.
            CHECK(places.post == 0);
            CHECK(places.vaults == 0);
        }
        // Common storehouses do not take it.
        const BuildingDef& store = sc::test::core_content().buildings[sc::test::core_content().find_building("core:storehouse")];
        CHECK(((store.stores >> static_cast<unsigned>(ResourceCategory::Gold)) & 1u) == 0);
    }

    TEST_CASE("laborers keep the trading post's gold, and the rest goes to the vault") {
        Game g(core(), map_for(81), setup());
        const EntityId post = build(g, "core:trading_post");
        CHECK(g.buildings().get(post)->limit == 100);  // A new post keeps 100.
        // The town's 100 go from the town center to the post.
        CHECK(run_until(g, 100, [&] { return g.gold_places(0).post == 100; }));
        // Less: what is over goes back to the town center (there is no vault).
        g.apply(set_reserve(post, 40));
        CHECK(run_until(g, 100, [&] { return g.gold_places(0).post == 40 && g.gold_places(0).others == 60; }));
        // A vault: the town center's gold goes there.
        const EntityId vault = build(g, "core:vault");
        CHECK(gold(g, 0) == 100);
        CHECK(run_until(g, 100, [&] { return g.gold_places(0).vaults == 60; }));
        CHECK(g.gold_places(0).others == 0);
        // More than the town has: the post takes it all from the vault.
        g.apply(set_reserve(post, 300));
        CHECK(run_until(g, 100, [&] { return g.gold_places(0).post == 100; }));
        CHECK(g.gold_places(0).vaults == 0);
        // None: all of it to the vault, and it stays there.
        g.apply(set_reserve(post, 0));
        CHECK(run_until(g, 100, [&] { return g.gold_places(0).vaults == 100; }));
        CHECK(run_until(g, 100, [] { return false; }, 30) == false);  // A month: still 100 (checked daily).
        CHECK(g.gold_places(0).vaults == 100);
        // Demolished, the vault's gold goes to the town center.
        Command rm;
        rm.type = CommandType::RemoveBuilding;
        rm.entity = vault;
        g.apply(rm);
        CHECK(g.buildings().get(vault) == nullptr);
        CHECK(g.gold_places(0).others == 100);
        CHECK(gold(g, 0) == 100);
    }

    TEST_CASE("a vault does not burn; a trading post burns with its gold") {
        Game g(core(), map_for(82), setup());
        const EntityId vault = build(g, "core:vault");
        const EntityId post = build(g, "core:trading_post");
        g.apply(set_reserve(post, 60));
        CHECK(run_until(g, 100, [&] { return g.gold_places(0).post == 60 && g.gold_places(0).vaults == 40; }));
        Command fire;
        fire.type = CommandType::DevIgnite;
        fire.entity = vault;
        g.apply(fire);
        CHECK(g.buildings().get(vault)->fire == 0);
        fire.entity = post;
        g.apply(fire);
        REQUIRE(g.buildings().get(post)->fire > 0);
        for (int t = 0; t < 200 && g.buildings().get(post) != nullptr; ++t) {
            run(g, 100);
        }
        REQUIRE(g.buildings().get(post) == nullptr);
        // Gold on its way to the post while it burned goes to the town center.
        CHECK(gold(g, 0) <= 40);
        CHECK(gold(g, 0) >= 40 - 50);
        CHECK(g.gold_places(0).vaults <= 40);
    }

    TEST_CASE("buying takes the town's gold, the post's first") {
        Game g(core(), map_for(81), setup());
        const EntityId post = build(g, "core:trading_post");
        g.apply(set_reserve(post, 0));
        const EntityId vault = build(g, "core:vault");
        (void)vault;
        CHECK(run_until(g, 100, [&] { return g.gold_places(0).vaults == 100; }));
        wait_for_merchant(g);
        const MerchantGood* stocked = nullptr;
        for (const MerchantGood& m : g.player(0).merchant) {
            stocked = m.stock > 0 && m.buy <= 100 && stocked == nullptr ? &m : stocked;
        }
        REQUIRE(stocked != nullptr);
        const std::int32_t price = stocked->buy;
        const DefIndex r = stocked->resource;
        const std::int32_t have = gold(g, 0);
        const std::int32_t n = std::min(stocked->stock, g.gold(0) / price);
        REQUIRE(n > 0);
        Command c;
        c.type = CommandType::Trade;
        c.entity = post;
        c.def = r;
        c.value = n;
        g.apply(c);
        CHECK(gold(g, 0) == have - n * price);  // From the vault: the post had none.
        // All of the town's gold is not enough for one more.
        const auto rejected = g.rejected_commands();
        c.value = g.gold(0) / price + 1;
        g.apply(c);
        CHECK(g.rejected_commands() == rejected + 1);
        // Selling puts the gold in the post.
        std::int32_t sell = 0;
        const DefIndex log = g.content().find_resource("core:log");
        for (const MerchantGood& m : g.player(0).merchant) {
            sell = m.resource == log ? m.sell : sell;
        }
        REQUIRE(sell > 0);
        const std::int32_t in_post = g.gold_places(0).post;
        c.def = log;
        c.value = -10;
        g.apply(c);
        CHECK(g.gold_places(0).post == in_post + 10 * sell);
    }

    TEST_CASE("gold in buildings survives a save") {
        Game g(core(), map_for(81), setup());
        const EntityId post = build(g, "core:trading_post");
        (void)build(g, "core:vault");
        g.apply(set_reserve(post, 30));
        run(g, 700);  // Some of it on the way.
        BinaryWriter w;
        g.save(w);
        Game back(core(), map_for(82), setup());
        BinaryReader r(w.bytes());
        REQUIRE(back.load(r, core()));
        CHECK(back.hash() == g.hash());
        CHECK(back.gold_places(0).post == g.gold_places(0).post);
        CHECK(back.gold_places(0).vaults == g.gold_places(0).vaults);
        run(g, 2000);
        run(back, 2000);
        CHECK(back.hash() == g.hash());
        CHECK(gold(back, 0) == 100);
    }
}
