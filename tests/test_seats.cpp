// Seats and towns that change during a game (phase 75): the host adds
// seats to a game already going, a seat founds its own town or joins
// another seat's, and nothing assumes a town and a seat are the same thing.
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

MapData small_map(std::uint64_t seed, std::uint8_t sites) {
    MapSettings s;
    s.seed = seed;
    s.size = MapSize::Small;
    s.sea = Sea::None;
    s.players = sites;
    std::optional<MapData> m = generate_map(s, *content());
    REQUIRE(m.has_value());
    return std::move(*m);
}

Command found_on_site(const Game& g, std::uint8_t player, std::size_t site) {
    const BuildingDef& d = g.content().buildings[g.town_center_def()];
    const StartPosition& s = g.map().starts[site];
    Command c;
    c.type = CommandType::FoundTown;
    c.player = player;
    c.position = {Fixed::from_int(s.x.floor_int() - d.width / 2), Fixed::from_int(s.z.floor_int() - d.depth / 2)};
    return c;
}

Command add_seat(std::uint8_t by, const char* name, std::uint8_t color = 3) {
    Command c;
    c.type = CommandType::AddSeat;
    c.player = by;
    c.text = name;
    c.count = color;
    return c;
}

Command request_join(std::uint8_t seat, std::uint8_t town) {
    Command c;
    c.type = CommandType::RequestJoin;
    c.player = seat;
    c.count = town;
    return c;
}

Command cancel_join(std::uint8_t seat) {
    Command c;
    c.type = CommandType::CancelJoin;
    c.player = seat;
    return c;
}

Command refuse_join(std::uint8_t founder, std::uint8_t seat) {
    Command c;
    c.type = CommandType::RefuseJoin;
    c.player = founder;
    c.count = seat;
    return c;
}

Command join_town(std::uint8_t founder, std::uint8_t seat) {
    Command c;
    c.type = CommandType::JoinTown;
    c.player = founder;
    c.count = seat;
    return c;
}

// A game of one seat, as a single-player game is: three sites on the map,
// the first one founded.
Game one_seat(std::uint64_t seed, FogMode fog = FogMode::None) {
    GameSetup setup;
    setup.players = 1;
    setup.seed = seed;
    setup.rules.fog = fog;
    setup.rules.shared_vision = false;  // Each town sees for itself.
    setup.start_towns = false;
    setup.access = access::kAll;  // Whoever comes later may found or join.
    setup.seats = {{"Ana", 2}};
    Game g(content(), small_map(seed, 3), setup);
    g.apply(found_on_site(g, 0, 0));
    REQUIRE(g.founded(0));
    return g;
}

// A house placed by `player` near its town's center, if there is room.
std::optional<Command> house_near(const Game& g, std::uint8_t player) {
    const DefIndex house = content()->find_building("core:house");
    const Building* tc = g.buildings().get(g.player(g.town_of(player)).town_center);
    if (tc == nullptr) {
        return std::nullopt;
    }
    for (std::int32_t r = 12; r < 70; r += 2) {
        for (std::int32_t dx = -r; dx <= r; dx += 2) {
            if (g.can_place(player, house, tc->x + dx, tc->z + r, 0) == PlaceError::None) {
                Command c;
                c.type = CommandType::PlaceBuilding;
                c.player = player;
                c.def = house;
                c.position = {Fixed::from_int(tc->x + dx), Fixed::from_int(tc->z + r)};
                return c;
            }
        }
    }
    return std::nullopt;
}

bool reload(const Game& g, Game& back) {
    BinaryWriter w;
    g.save(w);
    BinaryReader r(w.bytes());
    return back.load(r, content());
}

}  // namespace

TEST_SUITE("seats") {
    TEST_CASE("a second seat comes into a game of one, founds its town, and both towns live on") {
        Game g = one_seat(21);
        CHECK(g.player_count() == 1);
        CHECK(g.player(0).name == "Ana");
        CHECK(g.player(0).color == 2);
        for (int i = 0; i < 300; ++i) {
            g.step();
        }
        g.apply(add_seat(0, "Beto", 5));
        REQUIRE(g.rejected_commands() == 0);
        CHECK(g.player_count() == 2);
        CHECK(g.player(1).active);
        CHECK(g.player(1).name == "Beto");
        CHECK(g.player(1).color == 5);
        CHECK(g.town_of(1) == 1);
        CHECK(g.founder(1));
        CHECK_FALSE(g.founded(1));
        CHECK_FALSE(g.town_exists(1));
        CHECK(g.population(1) == 0);
        CHECK_FALSE(g.awaiting_founders());  // A game already going does not stop for a newcomer.
        const std::uint64_t tick = g.tick();
        g.step();
        CHECK(g.tick() == tick + 1);
        bool added = false;
        for (const Game::Event& e : g.take_events()) {
            added = added || (e.kind == Game::Event::Kind::SeatAdded && e.owner == 1);
        }
        CHECK(added);
        // It founds on another site, with time running.
        g.apply(found_on_site(g, 1, 1));
        REQUIRE(g.rejected_commands() == 0);
        CHECK(g.town_exists(1));
        CHECK(g.population(1) == village::kStartVillagers);
        for (int i = 0; i < 6000; ++i) {  // Ten minutes at x1.
            g.step();
        }
        CHECK(g.population(0) >= village::kStartVillagers - 2);
        CHECK(g.population(1) >= village::kStartVillagers - 2);
        const Building* a = g.buildings().get(g.player(0).town_center);
        const Building* b = g.buildings().get(g.player(1).town_center);
        REQUIRE(a != nullptr);
        REQUIRE(b != nullptr);
        CHECK(a->state == BuildingState::Complete);
        CHECK(b->state == BuildingState::Complete);
        CHECK(a->owner == 0);
        CHECK(b->owner == 1);
        CHECK_FALSE(g.game_over());
        CHECK_FALSE(g.shared_town());
    }

    TEST_CASE("a third seat joins the first town: its orders run there and nowhere else") {
        Game g = one_seat(21);
        g.apply(add_seat(0, "Beto"));
        g.apply(found_on_site(g, 1, 1));
        g.apply(add_seat(0, "Caro"));
        REQUIRE(g.rejected_commands() == 0);
        REQUIRE(g.player_count() == 3);
        // Without a town, seat 2 can do nothing but found.
        if (auto house = house_near(g, 0)) {
            house->player = 2;
            g.apply(*house);
            CHECK(g.rejected_commands() == 1);
        }
        const std::uint32_t before = g.rejected_commands();
        g.apply(request_join(2, 0));
        g.apply(join_town(0, 2));
        REQUIRE(g.rejected_commands() == before);
        CHECK(g.town_of(2) == 0);
        CHECK(g.founded(2));
        CHECK_FALSE(g.founder(2));
        CHECK(g.shared_town());
        CHECK(g.seats_of(0) == 2);
        CHECK(g.seats_of(1) == 1);
        CHECK(g.player(2).town_center == g.player(0).town_center);
        bool joined = false;
        for (const Game::Event& e : g.take_events()) {
            joined = joined || (e.kind == Game::Event::Kind::TownJoined && e.owner == 2 && e.other == 0);
        }
        CHECK(joined);
        // Its house goes up in town 0...
        const std::size_t buildings = g.buildings().size();
        std::optional<Command> house = house_near(g, 2);
        REQUIRE(house.has_value());
        g.apply(*house);
        CHECK(g.rejected_commands() == before);
        REQUIRE(g.buildings().size() == buildings + 1);
        CHECK(g.buildings().data().back().owner == 0);
        // ...and it cannot touch town 1's buildings, nor found a town any more.
        Command remove;
        remove.type = CommandType::RemoveBuilding;
        remove.player = 2;
        std::optional<Command> other = house_near(g, 1);
        REQUIRE(other.has_value());
        g.apply(*other);
        remove.entity = g.buildings().entities().back();
        REQUIRE(g.buildings().data().back().owner == 1);
        g.apply(remove);
        CHECK(g.rejected_commands() == before + 1);
        CHECK(g.buildings().get(remove.entity) != nullptr);
        g.apply(found_on_site(g, 2, 2));
        CHECK(g.rejected_commands() == before + 2);
        // Seat 0 still runs its town as before.
        remove.player = 0;
        remove.entity = g.buildings().entities()[buildings];
        g.apply(remove);
        CHECK(g.rejected_commands() == before + 2);
    }

    TEST_CASE("only the host adds seats, and there are twelve at most") {
        Game g = one_seat(21);
        g.apply(add_seat(0, "Beto"));
        g.apply(add_seat(1, "Intruso"));  // Not the host.
        CHECK(g.rejected_commands() == 1);
        CHECK(g.player_count() == 2);
        g.apply(add_seat(7, "Nadie"));    // Not even in the game.
        CHECK(g.rejected_commands() == 2);
        for (int i = 2; i < kMaxPlayers; ++i) {
            g.apply(add_seat(0, ""));
        }
        CHECK(g.rejected_commands() == 2);
        CHECK(g.player_count() == kMaxPlayers);
        g.apply(add_seat(0, "Trece"));
        CHECK(g.rejected_commands() == 3);
        CHECK(g.player_count() == kMaxPlayers);
        // Another seat hosts (a saved game loaded by somebody else): it adds, the first does not.
        Game h = one_seat(22);
        h.apply(add_seat(0, "Beto"));
        h.set_host(1);
        CHECK(h.host() == 1);
        h.apply(add_seat(0, "No"));
        CHECK(h.rejected_commands() == 1);
        h.apply(add_seat(1, "Si"));
        CHECK(h.rejected_commands() == 1);
        CHECK(h.player_count() == 3);
    }

    TEST_CASE("joining a town: only its founder lets in, and only seats without a town") {
        Game g = one_seat(21);
        g.apply(add_seat(0, "Beto"));
        g.apply(add_seat(0, "Caro"));
        g.apply(add_seat(0, "Dani"));
        g.apply(found_on_site(g, 1, 1));
        REQUIRE(g.rejected_commands() == 0);
        g.apply(join_town(0, 1));  // Beto has a town of his own.
        CHECK(g.rejected_commands() == 1);
        g.apply(join_town(0, 0));  // Nobody joins themselves (refused when read; here by the rules).
        CHECK(g.rejected_commands() == 2);
        g.apply(join_town(0, 9));  // No such seat.
        CHECK(g.rejected_commands() == 3);
        g.apply(join_town(0, 2));  // Caro has not asked.
        CHECK(g.rejected_commands() == 4);
        CHECK(g.town_of(2) == 2);
        g.apply(request_join(2, 0));
        g.apply(join_town(0, 2));
        CHECK(g.rejected_commands() == 4);
        CHECK(g.town_of(2) == 0);
        g.apply(request_join(3, 1));
        g.apply(join_town(2, 3));  // Caro is in a town but did not found it.
        CHECK(g.rejected_commands() == 5);
        g.apply(join_town(0, 3));  // Dani asked Beto, not Ana.
        CHECK(g.rejected_commands() == 6);
        g.apply(join_town(1, 2));  // Caro already has a town.
        CHECK(g.rejected_commands() == 7);
        CHECK(g.town_of(2) == 0);
        g.apply(join_town(1, 3));
        CHECK(g.rejected_commands() == 7);
        CHECK(g.town_of(3) == 1);
        CHECK(g.seats_of(0) == 2);
        CHECK(g.seats_of(1) == 2);
    }

    TEST_CASE("names are checked: no control characters, no more than 32 bytes") {
        CHECK(valid_seat_name(""));
        CHECK(valid_seat_name("Ñandú"));
        CHECK(valid_seat_name(std::string(32, 'a')));
        CHECK_FALSE(valid_seat_name(std::string(33, 'a')));
        CHECK_FALSE(valid_seat_name("a\nb"));
        CHECK_FALSE(valid_seat_name(" a"));
        CHECK_FALSE(valid_seat_name("\xC3"));
        Game g = one_seat(21);
        g.apply(add_seat(0, "a\tb"));
        CHECK(g.rejected_commands() == 1);
        Command c = add_seat(0, "Beto", 99);  // No such color.
        g.apply(c);
        CHECK(g.rejected_commands() == 2);
        // A command with a name survives the trip; a bad one is refused.
        BinaryWriter w;
        add_seat(0, "Beto", 4).write(w);
        BinaryReader r(w.bytes());
        Command back;
        REQUIRE(Command::read(r, back));
        CHECK(back.text == "Beto");
        CHECK(back.count == 4);
        BinaryWriter w2;
        add_seat(0, "x", 99).write(w2);
        BinaryReader r2(w2.bytes());
        CHECK_FALSE(Command::read(r2, back));
        BinaryWriter w3;
        join_town(0, 0).write(w3);
        BinaryReader r3(w3.bytes());
        CHECK_FALSE(Command::read(r3, back));
    }

    TEST_CASE("seats, towns, names and the host are saved and loaded") {
        Game g = one_seat(23);
        g.apply(add_seat(0, "Beto", 7));
        g.apply(add_seat(0, "Caro", 1));
        g.apply(add_seat(0, "Dani", 9));  // Stays without a town.
        g.apply(found_on_site(g, 1, 1));
        g.apply(request_join(2, 1));
        g.apply(join_town(1, 2));
        g.set_host(1);
        REQUIRE(g.rejected_commands() == 0);
        for (int i = 0; i < 200; ++i) {
            g.step();
        }
        Game back(content(), MapData{}, 0, 0);
        REQUIRE(reload(g, back));
        CHECK(back.hash() == g.hash());
        CHECK(back.player_count() == 4);
        CHECK(back.host() == 1);
        CHECK(back.town_of(2) == 1);
        CHECK(back.town_of(3) == 3);
        CHECK_FALSE(back.founded(3));
        CHECK(back.player(1).name == "Beto");
        CHECK(back.player(2).color == 1);
        // The same orders give the same game afterwards.
        for (Game* x : {&g, &back}) {
            x->apply(found_on_site(*x, 3, 2));
            x->apply(add_seat(1, "Eva"));
            for (int i = 0; i < 1500; ++i) {
                x->step();
            }
        }
        CHECK(back.hash() == g.hash());
        CHECK(back.town_exists(3));
        CHECK(back.player_count() == 5);
    }

    TEST_CASE("with fog, a new seat sees nothing; in a town, what the town has seen") {
        Game g = one_seat(24, FogMode::Static);
        REQUIRE(g.fog());
        for (int i = 0; i < 50; ++i) {
            g.step();
        }
        const Building* tc = g.buildings().get(g.player(0).town_center);
        REQUIRE(tc != nullptr);
        const std::int32_t x = tc->x, z = tc->z;
        REQUIRE(g.vision().explored_at(g.vision_group(0), x, z));
        g.apply(add_seat(0, "Beto"));
        g.apply(add_seat(0, "Caro"));
        REQUIRE(g.rejected_commands() == 0);
        CHECK(g.vision_group(1) != g.vision_group(0));
        CHECK(g.vision().used(g.vision_group(1)));
        CHECK_FALSE(g.vision().explored_at(g.vision_group(1), x, z));
        g.apply(request_join(2, 0));
        g.apply(join_town(0, 2));
        CHECK(g.vision_group(2) == g.vision_group(0));
        CHECK(g.vision().explored_at(g.vision_group(2), x, z));
        // Its own town: it sees around it, and still nothing of the first.
        g.apply(found_on_site(g, 1, 1));
        REQUIRE(g.rejected_commands() == 0);
        const Building* other = g.buildings().get(g.player(1).town_center);
        REQUIRE(other != nullptr);
        CHECK(g.vision().explored_at(g.vision_group(1), other->x, other->z));
        CHECK_FALSE(g.vision().explored_at(g.vision_group(1), x, z));
        // And it all loads back (the groups are checked when loading).
        for (int i = 0; i < 30; ++i) {
            g.step();
        }
        Game back(content(), MapData{}, 0, 0);
        REQUIRE(reload(g, back));
        CHECK(back.hash() == g.hash());
    }

    TEST_CASE("access: the host says who comes in, and latecomers found only if the game lets them") {
        GameSetup setup;
        setup.players = 1;
        setup.seed = 26;
        setup.start_towns = false;
        Game g(content(), small_map(26, 3), setup);
        CHECK(g.access() == 0);
        CHECK_FALSE(g.open());
        CHECK(g.may_found(0));  // The seats the game began with always may.
        g.apply(found_on_site(g, 0, 0));
        g.apply(add_seat(0, "Beto"));
        REQUIRE(g.rejected_commands() == 0);
        CHECK(g.player(1).late);
        CHECK_FALSE(g.may_found(1));
        CHECK(g.can_found(1, 40, 40, 0) == PlaceError::NotYours);
        g.apply(found_on_site(g, 1, 1));
        CHECK(g.rejected_commands() == 1);
        Command access;
        access.type = CommandType::SetAccess;
        access.player = 1;  // Not the host.
        access.value = access::kAll;
        g.apply(access);
        CHECK(g.rejected_commands() == 2);
        CHECK(g.access() == 0);
        access.player = 0;
        g.apply(access);
        CHECK(g.rejected_commands() == 2);
        CHECK(g.access() == access::kAll);
        CHECK(g.open());
        bool told = false;
        for (const Game::Event& e : g.take_events()) {
            told = told || (e.kind == Game::Event::Kind::AccessChanged && e.value == access::kAll);
        }
        CHECK(told);
        g.apply(found_on_site(g, 1, 1));
        CHECK(g.rejected_commands() == 2);
        CHECK(g.town_exists(1));
        // Saved and loaded with the game.
        Game back(content(), MapData{}, 0, 0);
        REQUIRE(reload(g, back));
        CHECK(back.access() == access::kAll);
        CHECK(back.player(1).late);
        CHECK(back.hash() == g.hash());
        // Out of range, a command is refused when read.
        access.value = 99;
        BinaryWriter w;
        access.write(w);
        BinaryReader r(w.bytes());
        Command read_back;
        CHECK_FALSE(Command::read(r, read_back));
    }

    TEST_CASE("asking to join: the founder accepts or refuses, the seat may withdraw, one request at a time") {
        Game g = one_seat(27);
        g.apply(add_seat(0, "Beto"));
        g.apply(found_on_site(g, 1, 1));
        g.apply(add_seat(0, "Caro"));
        REQUIRE(g.rejected_commands() == 0);
        (void)g.take_events();
        CHECK(g.may_request(2, 0));
        CHECK(g.may_request(2, 1));
        CHECK_FALSE(g.may_request(2, 2));  // Not its own.
        CHECK_FALSE(g.may_request(1, 0));  // Beto has a town.
        CHECK(g.player(2).request == kNoRequest);
        g.apply(request_join(2, 0));
        REQUIRE(g.rejected_commands() == 0);
        CHECK(g.player(2).request == 0);
        CHECK(g.town_of(2) == 2);  // Asking is not joining.
        g.apply(request_join(2, 1));  // One at a time.
        CHECK(g.rejected_commands() == 1);
        CHECK(g.player(2).request == 0);
        g.apply(refuse_join(1, 2));  // Not Beto's to answer.
        CHECK(g.rejected_commands() == 2);
        g.apply(refuse_join(0, 2));
        CHECK(g.rejected_commands() == 2);
        CHECK(g.player(2).request == kNoRequest);
        g.apply(refuse_join(0, 2));  // Nothing left to refuse.
        CHECK(g.rejected_commands() == 3);
        // Refused, it asks the other town, thinks again and withdraws.
        g.apply(request_join(2, 1));
        CHECK(g.player(2).request == 1);
        g.apply(cancel_join(2));
        CHECK(g.player(2).request == kNoRequest);
        g.apply(cancel_join(2));  // Nothing to withdraw.
        CHECK(g.rejected_commands() == 4);
        g.apply(join_town(1, 2));  // Withdrawn: Beto cannot take it in any more.
        CHECK(g.rejected_commands() == 5);
        // It asks again, and founding its own town drops the request.
        g.apply(request_join(2, 0));
        g.apply(found_on_site(g, 2, 2));
        CHECK(g.rejected_commands() == 5);
        CHECK(g.town_exists(2));
        CHECK(g.player(2).request == kNoRequest);
        g.apply(join_town(0, 2));
        CHECK(g.rejected_commands() == 6);
        int asked = 0, refused = 0, cancelled = 0;
        for (const Game::Event& e : g.take_events()) {
            asked += e.kind == Game::Event::Kind::JoinRequested ? 1 : 0;
            refused += e.kind == Game::Event::Kind::JoinRefused && e.owner == 2 && e.other == 0 ? 1 : 0;
            cancelled += e.kind == Game::Event::Kind::JoinCancelled && e.owner == 2 && e.other == 1 ? 1 : 0;
        }
        CHECK(asked == 3);
        CHECK(refused == 1);
        CHECK(cancelled == 1);
    }

    TEST_CASE("asking to join needs the game to allow it, and a town that exists") {
        GameSetup setup;
        setup.players = 1;
        setup.seed = 28;
        setup.start_towns = false;
        setup.access = access::kOpen | access::kFound;  // To found, not to join.
        Game g(content(), small_map(28, 3), setup);
        g.apply(found_on_site(g, 0, 0));
        g.apply(add_seat(0, "Beto"));
        g.apply(add_seat(0, "Caro"));
        REQUIRE(g.rejected_commands() == 0);
        CHECK_FALSE(g.may_request(1, 0));
        g.apply(request_join(1, 0));
        CHECK(g.rejected_commands() == 1);
        Command access;
        access.type = CommandType::SetAccess;
        access.value = access::kOpen | access::kJoin;
        g.apply(access);
        g.apply(request_join(1, 2));  // Caro has founded nothing.
        CHECK(g.rejected_commands() == 2);
        g.apply(request_join(1, 7));  // No such seat.
        CHECK(g.rejected_commands() == 3);
        g.apply(request_join(1, 0));
        CHECK(g.rejected_commands() == 3);
        CHECK(g.player(1).request == 0);
        // A request waits as long as it takes, and is saved with the game.
        for (int i = 0; i < 3000; ++i) {
            g.step();
        }
        CHECK(g.player(1).request == 0);
        Game back(content(), MapData{}, 0, 0);
        REQUIRE(reload(g, back));
        CHECK(back.player(1).request == 0);
        CHECK(back.hash() == g.hash());
        back.apply(join_town(0, 1));
        CHECK(back.rejected_commands() == g.rejected_commands());
        CHECK(back.town_of(1) == 0);
        CHECK(back.founded(1));
    }

    TEST_CASE("the lobby's two kinds of game are seats and towns too") {
        GameSetup setup;
        setup.players = 3;
        setup.seed = 25;
        setup.shared_town = true;
        setup.start_towns = false;
        Game common(content(), small_map(25, 1), setup);
        CHECK(common.player_count() == 3);  // Only those who play: more come by AddSeat.
        CHECK(common.town_of(1) == 0);
        CHECK(common.town_of(2) == 0);
        CHECK(common.shared_town());
        CHECK(common.seats_of(0) == 3);
        setup.shared_town = false;
        setup.access = access::kAll;
        Game apart(content(), small_map(25, 3), setup);
        CHECK(apart.player_count() == 3);
        CHECK(apart.town_of(2) == 2);
        CHECK_FALSE(apart.shared_town());
        CHECK(apart.awaiting_founders());
        // A seat that joins another's town no longer keeps the game waiting.
        apart.apply(found_on_site(apart, 0, 0));
        apart.apply(found_on_site(apart, 1, 1));
        CHECK(apart.awaiting_founders());
        apart.apply(request_join(2, 1));
        apart.apply(join_town(1, 2));
        CHECK(apart.rejected_commands() == 0);
        CHECK_FALSE(apart.awaiting_founders());
    }
}
