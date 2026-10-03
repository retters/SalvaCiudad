// The explorer (phase 66): a villager the player sends to a point. It takes
// provisions, walks straight into what nobody has seen, keeps to explored
// ground when the point is explored, sees far, and comes back by itself
// before it starves.
#include <doctest.h>

#include <algorithm>
#include <cmath>
#include <memory>
#include <optional>

#include "sim/game.h"
#include "sim/vision.h"
#include "sim/worldgen.h"
#include "test_util.h"

using namespace sc::sim;

namespace {

std::shared_ptr<const Content> content() {
    return std::shared_ptr<const Content>(std::shared_ptr<const Content>{}, &sc::test::core_content());
}

double meters(Fixed f) {
    return static_cast<double>(f.raw()) / 65536.0;
}

// A small map with a level strip 200 m long from beside the town, and a
// pond across the middle of the strip that can be walked around.
struct Strip {
    MapData map;
    std::int32_t dir = 1;    // The strip runs east (1) or west (-1) of the town.
    std::int32_t x0 = 0;     // Where it starts, beside the town.
    std::int32_t z = 0;      // Its middle line.
    std::int32_t pond = 0;   // The pond's near edge, meters along the strip.
};

Strip strip(std::uint64_t seed, std::int32_t length = 200, MapSize size = MapSize::Small, bool with_pond = true) {
    MapSettings s;
    s.seed = seed;
    s.size = size;
    s.sea = Sea::None;
    s.players = 1;
    std::optional<MapData> m = generate_map(s, *content());
    REQUIRE(m.has_value());
    Strip f;
    f.map = std::move(*m);
    REQUIRE(!f.map.starts.empty());
    const std::int32_t sx = f.map.starts[0].x.floor_int();
    f.z = f.map.starts[0].z.floor_int();
    f.dir = sx + length + 40 < f.map.size ? 1 : -1;
    REQUIRE((f.dir == 1 || sx - length - 40 > 0));
    f.x0 = sx + f.dir * 16;
    f.pond = 110;
    const std::int32_t side = f.map.size + 1;
    const std::uint16_t base = f.map.height_cm(sx, f.z);
    const auto along = [&](std::int32_t x) { return (x - f.x0) * f.dir; };
    for (std::int32_t z = f.z - 40; z <= f.z + 40; ++z) {
        for (std::int32_t x = 0; x <= f.map.size; ++x) {
            if (along(x) < -30 || along(x) > length || z < 0 || z > f.map.size) {
                continue;
            }
            f.map.heights[static_cast<std::size_t>(z) * static_cast<std::size_t>(side) + static_cast<std::size_t>(x)] = base;
            if (x < f.map.size && z < f.map.size) {
                const bool wet = with_pond && along(x) >= f.pond && along(x) < f.pond + 12 && std::abs(z - f.z) <= 15;
                f.map.water[static_cast<std::size_t>(z) * static_cast<std::size_t>(f.map.size) + static_cast<std::size_t>(x)] =
                    wet ? static_cast<std::uint16_t>(base + 40) : std::uint16_t{0};
            }
        }
    }
    // Nothing to gather on the strip (and nothing in the way).
    std::erase_if(f.map.features, [&](const MapFeature& feature) {
        return along(feature.x.floor_int()) >= -32 && along(feature.x.floor_int()) <= length + 2 &&
               std::abs(feature.z.floor_int() - f.z) <= 42;
    });
    return f;
}

GameSetup setup(FogMode fog) {
    GameSetup s;
    s.players = 1;
    s.seed = 7;
    s.rules.fog = fog;
    s.rules.climate.seasons = 0b0010;  // Summer all year: nobody gets cold.
    s.rules.fires = Threat::None;
    s.rules.raiders = Threat::None;
    s.rules.wildlife = Threat::None;
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
    c.def = content()->find_resource(resource);
    c.value = amount;
    g.apply(c);
}

// The explorer's hut, built beside the town, with its worker.
struct Post {
    EntityId hut;
    EntityId worker;
};

Post explorer_post(Game& g) {
    const DefIndex def = content()->find_building("core:explorer");
    REQUIRE(def != kNoDef);
    const Building* tc = g.buildings().get(g.player(0).town_center);
    REQUIRE(tc != nullptr);
    Post post;
    for (std::int32_t r = 12; r < 40 && !post.hut.valid(); r += 2) {
        for (std::int32_t a = 0; a < 8 && !post.hut.valid(); ++a) {
            const std::int32_t x = tc->x + (a % 3 - 1) * r;
            const std::int32_t z = tc->z + (a / 3 - 1) * r;
            if ((a % 3 == 1 && a / 3 == 1) || g.can_place(0, def, x, z, 0) != PlaceError::None) {
                continue;
            }
            Command c;
            c.type = CommandType::PlaceBuilding;
            c.def = def;
            c.position = {Fixed::from_int(x), Fixed::from_int(z)};
            g.apply(c);
            for (std::size_t i = 0; i < g.buildings().size(); ++i) {
                if (g.buildings().data()[i].def == def) {
                    post.hut = g.buildings().entities()[i];
                }
            }
        }
    }
    REQUIRE(post.hut.valid());
    for (int t = 0; t < 80 && g.buildings().get(post.hut)->workers.empty(); ++t) {
        run(g, 100);
    }
    REQUIRE(g.buildings().get(post.hut)->state == BuildingState::Complete);
    REQUIRE(g.buildings().get(post.hut)->workers.size() == 1);
    post.worker = g.buildings().get(post.hut)->workers[0];
    return post;
}

Command order(EntityId who, double x, double z) {
    Command c;
    c.type = CommandType::MoveVillager;
    c.entity = who;
    c.position = {Fixed::from_ratio(static_cast<std::int32_t>(x * 16.0), 16), Fixed::from_ratio(static_cast<std::int32_t>(z * 16.0), 16)};
    return c;
}

}  // namespace

TEST_SUITE("explorer") {
    TEST_CASE("sent into what nobody has seen, it takes provisions, walks straight and stops at the water") {
        const Strip f = strip(31);
        Game g(content(), f.map, setup(FogMode::Static));
        const Post post = explorer_post(g);
        const std::uint8_t group = g.vision_group(0);
        const double far_x = f.x0 + f.dir * 170.0;  // Beyond the pond, on the strip's middle line.
        REQUIRE_FALSE(g.vision().explored_at(group, static_cast<std::int32_t>(far_x), f.z));

        g.apply(order(post.worker, far_x, f.z));
        CHECK(g.rejected_commands() == 0);
        const Villager* v = g.villagers().get(post.worker);
        REQUIRE(v != nullptr);
        CHECK(v->order == Order::Provision);
        CHECK(v->task == Task::GoProvision);
        for (int t = 0; t < 3000 && g.villagers().get(post.worker)->order == Order::Provision; ++t) {
            g.step();
        }
        v = g.villagers().get(post.worker);
        REQUIRE(v->order == Order::Going);
        CHECK(v->provisions == village::kProvisions);

        // From there, a straight line at the point.
        const double ax = meters(v->position.x);
        const double az = meters(v->position.z);
        const double length = std::hypot(far_x - ax, f.z - az);
        double worst = 0.0;
        for (int t = 0; t < 6000 && g.villagers().get(post.worker)->order == Order::Going; ++t) {
            g.step();
            v = g.villagers().get(post.worker);
            const double px = meters(v->position.x);
            const double pz = meters(v->position.z);
            worst = std::max(worst, std::abs((px - ax) * (f.z - az) - (pz - az) * (far_x - ax)) / length);
        }
        v = g.villagers().get(post.worker);
        REQUIRE(v != nullptr);
        CHECK(v->order == Order::Waiting);
        CHECK(v->task == Task::ScoutWait);
        CHECK(worst < 0.6);
        // It stopped at the pond: it did not go around it.
        const double reached = (meters(v->position.x) - f.x0) * f.dir;
        CHECK(reached < f.pond + 0.5);
        CHECK(reached > f.pond - 6.0);
        // It sees 30 m: more than twice what a villager does.
        const auto wx = static_cast<std::int32_t>(meters(v->position.x));
        const auto wz = static_cast<std::int32_t>(meters(v->position.z));
        CHECK(g.vision().explored_at(group, wx, wz + 26));
        CHECK(g.vision().explored_at(group, wx, wz - 26));
        CHECK_FALSE(g.vision().explored_at(group, wx, wz + 46));

        // It waits there, whatever happens in town.
        const FixedVec2 at = v->position;
        run(g, 600);
        v = g.villagers().get(post.worker);
        CHECK(v->position == at);
        CHECK(v->order == Order::Waiting);

        // To an explored point: only over explored ground.
        const double back_x = f.x0 + f.dir * 40.0;
        REQUIRE(g.vision().explored_at(group, static_cast<std::int32_t>(back_x), f.z + 10));
        g.apply(order(post.worker, back_x, f.z + 10));
        v = g.villagers().get(post.worker);
        CHECK(v->order == Order::Going);  // It has provisions enough: straight to the road.
        bool known = true;
        for (int t = 0; t < 6000 && g.villagers().get(post.worker)->order == Order::Going; ++t) {
            g.step();
            v = g.villagers().get(post.worker);
            known = known && g.vision().explored_at(group, v->position.x.floor_int(), v->position.z.floor_int());
        }
        v = g.villagers().get(post.worker);
        CHECK(known);
        CHECK(v->order == Order::Waiting);
        CHECK(std::hypot(meters(v->position.x) - back_x, meters(v->position.z) - (f.z + 10)) < 3.0);
        CHECK(g.player(0).deaths == 0);
    }

    TEST_CASE("it comes back by itself with just enough food for the way") {
        const Strip f = strip(31);
        Game g(content(), f.map, setup(FogMode::Static));
        const Post post = explorer_post(g);
        (void)g.take_events();
        g.apply(order(post.worker, f.x0 + f.dir * 100.0, f.z));
        bool waited = false;
        bool turned_back = false;
        std::int32_t lowest = village::kFoodMax;
        for (int t = 0; t < 30000; ++t) {
            if (t % 1000 == 0) {
                grant(g, "core:roots", 30);  // The town does not go hungry meanwhile.
            }
            g.step();
            const Villager* v = g.villagers().get(post.worker);
            REQUIRE(v != nullptr);
            waited = waited || v->order == Order::Waiting;
            lowest = std::min(lowest, v->food);
            for (const Game::Event& e : g.take_events()) {
                turned_back = turned_back || (e.kind == Game::Event::Kind::ExplorerBack && e.value == 0);
            }
            if (turned_back && v->order == Order::None) {
                break;
            }
        }
        const Villager* v = g.villagers().get(post.worker);
        CHECK(waited);
        CHECK(turned_back);
        CHECK(v->order == Order::None);
        CHECK(v->provisions == 0);
        CHECK(lowest > 0);  // Never out of food.
        CHECK(v->health == village::kHealthMax);
        const Building* hut = g.buildings().get(post.hut);
        REQUIRE(hut != nullptr);
        CHECK(std::hypot(meters(v->position.x) - meters(g.door(*hut).x), meters(v->position.z) - meters(g.door(*hut).z)) < 60.0);
        CHECK(g.player(0).deaths == 0);
        // Sent home by hand, it is an ordinary villager again when it gets there.
        g.apply(order(post.worker, f.x0 + f.dir * 60.0, f.z));
        run(g, 400);
        g.apply(order(post.worker, meters(g.door(*hut).x), meters(g.door(*hut).z)));
        CHECK(g.villagers().get(post.worker)->order == Order::Returning);
        for (int t = 0; t < 3000 && g.villagers().get(post.worker)->order != Order::None; ++t) {
            g.step();
        }
        CHECK(g.villagers().get(post.worker)->order == Order::None);
    }

    TEST_CASE("the hungry eat before a long haul, and nobody's meter runs out") {
        // A site 320 m from the town: the walk there and back takes most of
        // a full meter. Before phase 66 a villager only thought of eating
        // between tasks, and ran out on the way.
        const Strip f = strip(33, 340, MapSize::Medium, false);
        Game g(content(), f.map, setup(FogMode::None));
        const DefIndex camp = content()->find_building("core:woodcutter");
        EntityId site;
        for (std::int32_t dz = -20; dz <= 20 && !site.valid(); dz += 4) {
            const std::int32_t x = f.x0 + f.dir * 320;
            if (g.can_place(0, camp, x, f.z + dz, 0) == PlaceError::None) {
                Command c;
                c.type = CommandType::PlaceBuilding;
                c.def = camp;
                c.position = {Fixed::from_int(x), Fixed::from_int(f.z + dz)};
                g.apply(c);
                site = g.buildings().entities().back();
            }
        }
        REQUIRE(site.valid());
        std::int32_t lowest = village::kFoodMax;
        for (int t = 0; t < 14000; t += 20) {
            if (t % 1000 == 0) {
                grant(g, "core:roots", 30);
            }
            run(g, 20);
            for (const Villager& v : g.villagers().data()) {
                lowest = std::min(lowest, v.food);
            }
        }
        const Building* b = g.buildings().get(site);
        REQUIRE(b != nullptr);
        MESSAGE("a site 320 m away: lowest meter " << lowest << ", built " << (b->state == BuildingState::Complete));
        CHECK(b->state == BuildingState::Complete);
        CHECK(lowest > 0);
        CHECK(g.player(0).deaths == 0);
    }

    TEST_CASE("without fog it takes the way anybody would, around the water") {
        const Strip f = strip(31);
        Game g(content(), f.map, setup(FogMode::None));
        const Post post = explorer_post(g);
        const double far_x = f.x0 + f.dir * 150.0;
        g.apply(order(post.worker, far_x, f.z));
        for (int t = 0; t < 9000 && g.villagers().get(post.worker)->order != Order::Waiting; ++t) {
            g.step();
        }
        const Villager* v = g.villagers().get(post.worker);
        REQUIRE(v != nullptr);
        CHECK(v->order == Order::Waiting);
        CHECK(std::hypot(meters(v->position.x) - far_x, meters(v->position.z) - f.z) < 3.0);  // Past the pond.
    }

    TEST_CASE("only the owner's explorer takes orders, and they are the same on every machine") {
        const Strip f = strip(31);
        Game a(content(), f.map, setup(FogMode::Static));
        Game b(content(), f.map, setup(FogMode::Static));
        const Post post = explorer_post(a);
        const Post same = explorer_post(b);
        REQUIRE(post.worker == same.worker);
        REQUIRE(a.hash() == b.hash());

        // Somebody who is not an explorer: refused.
        EntityId other;
        for (std::size_t i = 0; i < a.villagers().size(); ++i) {
            if (a.villagers().entities()[i] != post.worker && a.adult(a.villagers().data()[i])) {
                other = a.villagers().entities()[i];
            }
        }
        REQUIRE(other.valid());
        a.apply(order(other, f.x0 + f.dir * 100.0, f.z));
        CHECK(a.rejected_commands() == 1);
        CHECK(a.villagers().get(other)->order == Order::None);

        // As bytes, like in a network game.
        const Command sent = order(post.worker, f.x0 + f.dir * 170.0, f.z);
        BinaryWriter wire;
        sent.write(wire);
        BinaryReader in(wire.bytes());
        Command received;
        REQUIRE(Command::read(in, received));
        CHECK(received == sent);
        a.apply(sent);
        b.apply(received);
        b.apply(order(other, f.x0 + f.dir * 100.0, f.z));  // (Its refusal counts the same there.)
        for (int t = 0; t < 12; ++t) {
            run(a, 100);
            run(b, 100);
            REQUIRE(a.hash() == b.hash());
        }
        // Saved on its way and loaded: it goes on.
        BinaryWriter w;
        a.save(w);
        Game back(content(), f.map, setup(FogMode::Static));
        BinaryReader r(w.bytes());
        REQUIRE(back.load(r, content()));
        CHECK(back.hash() == a.hash());
        CHECK(back.villagers().get(post.worker)->order == a.villagers().get(post.worker)->order);
        CHECK(back.villagers().get(post.worker)->provisions == a.villagers().get(post.worker)->provisions);
        run(a, 1500);
        run(back, 1500);
        CHECK(back.hash() == a.hash());

        // A point off the map's corner is refused before it reaches the game.
        Command bad = sent;
        bad.position.x = Fixed::from_int(-5);
        BinaryWriter bw;
        bad.write(bw);
        BinaryReader br(bw.bytes());
        Command out;
        CHECK_FALSE(Command::read(br, out));

        // The hut stopped: its worker is a laborer again and forgets the order.
        Command stop;
        stop.type = CommandType::SetProduction;
        stop.entity = post.hut;
        stop.value = 0;
        a.apply(stop);
        run(a, 200);
        CHECK(a.villagers().get(post.worker)->order == Order::None);
        CHECK_FALSE(a.villagers().get(post.worker)->job.valid());
    }
}
