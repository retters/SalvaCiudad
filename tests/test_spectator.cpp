// Watching a game (phase 79), on the side of the machine that watches:
// what it sees (everything without fog, or what one town sees) and that it
// gives no orders. The network side is in the suite `net`.
#include <doctest.h>

#include <memory>
#include <optional>

#include "game/game_session.h"
#include "sim/game.h"
#include "sim/worldgen.h"
#include "test_util.h"

using namespace sc;
using namespace sc::sim;

namespace {

std::shared_ptr<const Content> content() {
    return std::shared_ptr<const Content>(std::shared_ptr<const Content>{}, &sc::test::core_content());
}

// Two towns, each seeing for itself under a static fog, after a few seconds.
std::unique_ptr<Game> two_towns(std::uint64_t seed) {
    MapSettings s;
    s.seed = seed;
    s.size = MapSize::Small;
    s.sea = Sea::None;
    s.players = 2;
    std::optional<MapData> m = generate_map(s, *content());
    REQUIRE(m.has_value());
    GameSetup setup;
    setup.players = 2;
    setup.seed = seed;
    setup.rules.fog = FogMode::Static;
    setup.rules.shared_vision = false;
    setup.seats = {{"Ana", 1}, {"Beto", 2}};
    auto g = std::make_unique<Game>(content(), std::move(*m), setup);
    for (int i = 0; i < 30; ++i) {
        g->step();
    }
    return g;
}

struct Point {
    float x = 0.0f;
    float z = 0.0f;
};

Point center_of(const Game& g, std::uint8_t town) {
    const Building* tc = g.buildings().get(g.player(town).town_center);
    REQUIRE(tc != nullptr);
    return {static_cast<float>(tc->x) + 4.0f, static_cast<float>(tc->z) + 4.0f};
}

}  // namespace

TEST_SUITE("spectator") {
    TEST_CASE("a spectator sees everything, or what one town sees") {
        GameSession s(two_towns(71), 0);
        const Point a = center_of(s.game(), 0);
        const Point b = center_of(s.game(), 1);
        // Playing town 0: its own surroundings, not the other town's.
        s.fog().update(s.game());
        CHECK_FALSE(s.spectating());
        CHECK(s.seat() == 0);
        REQUIRE(s.fog().mode() == FogMode::Static);
        CHECK(s.fog().explored(a.x, a.z));
        CHECK_FALSE(s.fog().explored(b.x, b.z));
        // Watching without a seat: the whole map, no fog at all.
        s.watch(0, true, GameSession::kNoSeat);
        s.fog().update(s.game());
        CHECK(s.spectating());
        CHECK(s.view_all());
        CHECK(s.seat() == GameSession::kNoSeat);
        CHECK(s.fog().mode() == FogMode::None);
        CHECK(s.fog().shows(a.x, a.z));
        CHECK(s.fog().shows(b.x, b.z));
        // "As town 1": only what that town explored.
        s.watch(1, false, GameSession::kNoSeat);
        s.fog().update(s.game());
        CHECK_FALSE(s.view_all());
        CHECK(s.local_player() == 1);
        CHECK(s.town() == 1);
        REQUIRE(s.fog().mode() == FogMode::Static);
        CHECK(s.fog().group() == s.game().vision_group(1));
        CHECK(s.fog().explored(b.x, b.z));
        CHECK_FALSE(s.fog().explored(a.x, a.z));
        // And as town 0.
        s.watch(0, false, GameSession::kNoSeat);
        s.fog().update(s.game());
        CHECK(s.fog().explored(a.x, a.z));
        CHECK_FALSE(s.fog().explored(b.x, b.z));
        // Back to everything.
        s.watch(0, true, GameSession::kNoSeat);
        CHECK(s.fog().mode() == FogMode::None);
    }

    TEST_CASE("whoever watches gives no orders; back in its seat, it does") {
        GameSession s(two_towns(72), 1);
        const DefIndex house = content()->find_building("core:house");
        const Building* tc = s.game().buildings().get(s.game().player(1).town_center);
        REQUIRE(tc != nullptr);
        std::optional<Command> place;
        for (std::int32_t r = 12; r < 70 && !place; r += 2) {
            for (std::int32_t dx = -r; dx <= r && !place; dx += 2) {
                if (s.game().can_place(1, house, tc->x + dx, tc->z + r, 0) == PlaceError::None) {
                    Command c;
                    c.type = CommandType::PlaceBuilding;
                    c.def = house;
                    c.position = {Fixed::from_int(tc->x + dx), Fixed::from_int(tc->z + r)};
                    place = c;
                }
            }
        }
        REQUIRE(place.has_value());
        const std::size_t buildings = s.game().buildings().size();
        // A player who goes to watch keeps the seat, and looks at everything.
        s.watch(1, true, 1);
        CHECK(s.spectating());
        CHECK(s.seat() == 1);
        s.issue(*place);
        s.step();
        CHECK(s.game().buildings().size() == buildings);
        CHECK(s.game().rejected_commands() == 0);
        // Looking as the other town does not make it theirs.
        s.watch(0, false, 1);
        CHECK(s.local_player() == 0);
        CHECK(s.seat() == 1);
        s.issue(*place);
        s.step();
        CHECK(s.game().buildings().size() == buildings);
        // Back: the seat it had, its own town's eyes, and its orders run.
        s.play(1);
        CHECK_FALSE(s.spectating());
        CHECK(s.local_player() == 1);
        CHECK(s.fog().mode() == FogMode::Static);
        CHECK(s.fog().group() == s.game().vision_group(1));
        s.issue(*place);
        s.step();
        CHECK(s.game().buildings().size() == buildings + 1);
        CHECK(s.game().buildings().data().back().owner == 1);
    }

    TEST_CASE("an order given just before going to watch does not run later") {
        GameSession s(two_towns(73), 0);
        Command bell;
        bell.type = CommandType::RingBell;
        bell.value = 1;
        s.issue(bell);
        s.watch(0, true, 0);
        s.step();
        CHECK_FALSE(s.game().player(0).alarm);
    }
}
