// Fog of war (phases 32 to 34): what each side explored, where it may
// build, how it is saved and what the view shows.
#include <doctest.h>

#include <memory>
#include <optional>
#include <string>

#include "game/fog_view.h"
#include "game/map_scene.h"
#include "game/village_view.h"
#include "game/minimap.h"
#include "sim/game.h"
#include "sim/vision.h"
#include "sim/worldgen.h"
#include "test_util.h"

using namespace sc;
using namespace sc::sim;

namespace {

std::shared_ptr<const Content> content() {
    return std::shared_ptr<const Content>(std::shared_ptr<const Content>{}, &test::core_content());
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

GameSetup setup(std::uint8_t players, FogMode fog, bool versus = false, bool shared_vision = true) {
    GameSetup s;
    s.players = players;
    s.seed = 7;
    s.rules.fog = fog;
    s.rules.versus = versus;
    s.rules.shared_vision = shared_vision;
    return s;
}

const Building& town_center(const Game& g, std::uint8_t player = 0) {
    const Building* b = g.buildings().get(g.player(player).town_center);
    REQUIRE(b != nullptr);
    return *b;
}

DefIndex building(std::string_view id) {
    const DefIndex d = content()->find_building(std::string("core:") + std::string(id));
    REQUIRE(d != kNoDef);
    return d;
}

void run(Game& g, std::uint32_t ticks) {
    for (std::uint32_t i = 0; i < ticks; ++i) {
        g.step();
    }
}

// Sends people out: a woodcutter's camp at the edge of what the town
// center sees, so its workers walk to trees beyond it.
void send_out(Game& g) {
    const Building& tc = town_center(g);
    const DefIndex camp = building("woodcutter");
    const std::int32_t mx = tc.x + tc.width / 2;
    const std::int32_t mz = tc.z + tc.depth / 2;
    for (std::int32_t r = 44; r >= 20; r -= 2) {
        for (std::int32_t a = 0; a < 16; ++a) {
            static constexpr std::int32_t kDirs[16][2] = {{10, 0}, {9, 4}, {7, 7}, {4, 9}, {0, 10}, {-4, 9}, {-7, 7}, {-9, 4},
                                                          {-10, 0}, {-9, -4}, {-7, -7}, {-4, -9}, {0, -10}, {4, -9}, {7, -7}, {9, -4}};
            const std::int32_t x = mx + kDirs[a][0] * r / 10 - 2;
            const std::int32_t z = mz + kDirs[a][1] * r / 10 - 2;
            if (g.can_place(0, camp, x, z, 0) == PlaceError::None) {
                Command c;
                c.type = CommandType::PlaceBuilding;
                c.def = camp;
                c.position = {Fixed::from_int(x), Fixed::from_int(z)};
                g.apply(c);
                return;
            }
        }
    }
    FAIL("no room for a woodcutter");
}

// Cells of a disc, counted one by one.
std::int32_t disc_cells(std::int32_t side, std::int32_t x, std::int32_t z, std::int32_t r) {
    std::int32_t n = 0;
    for_each_disc_row(side, x, z, r, [&](std::int32_t, std::int32_t cx0, std::int32_t cx1) { n += cx1 - cx0 + 1; });
    return n;
}

}  // namespace

TEST_SUITE("fog") {
    TEST_CASE("a disc of sight covers the cells whose centers are within reach") {
        constexpr std::int32_t kSide = 64;
        for (const std::int32_t r : {0, 3, 12, 45}) {
            for_each_disc_row(kSide, 130, 97, r, [&](std::int32_t cz, std::int32_t cx0, std::int32_t cx1) {
                for (std::int32_t cx = cx0; cx <= cx1; ++cx) {
                    const std::int32_t dx = cx * kFogCell + 2 - 130;
                    const std::int32_t dz = cz * kFogCell + 2 - 97;
                    CHECK(dx * dx + dz * dz <= r * r);
                }
                // The next cell out on each side is beyond reach.
                for (const std::int32_t cx : {cx0 - 1, cx1 + 1}) {
                    if (cx >= 0 && cx < kSide) {
                        const std::int32_t dx = cx * kFogCell + 2 - 130;
                        const std::int32_t dz = cz * kFogCell + 2 - 97;
                        CHECK(dx * dx + dz * dz > r * r);
                    }
                }
            });
        }
        // Roughly the area of the circle, in 16 m2 cells.
        const std::int32_t n = disc_cells(1024, 2000, 2000, 40);
        CHECK(n > 280);
        CHECK(n < 350);
        // Clipped at the edges, never outside the grid.
        for_each_disc_row(16, 0, 0, 30, [&](std::int32_t cz, std::int32_t cx0, std::int32_t cx1) {
            CHECK(cz >= 0);
            CHECK(cx0 >= 0);
            CHECK(cx1 < 16);
        });
        CHECK(disc_cells(16, -500, -500, 30) == 0);
    }

    TEST_CASE("the explored cells, their count and checksum survive a round trip") {
        Vision v;
        v.reset(512, 0b101);
        CHECK(v.active());
        CHECK(v.side() == 128);
        CHECK(v.used(0));
        CHECK_FALSE(v.used(1));
        v.reveal(0, 100, 100, 20);
        v.reveal(2, 400, 30, 12);
        const std::uint32_t count = v.count(0);
        CHECK(count > 50);
        v.reveal(0, 100, 100, 20);  // Nothing new.
        CHECK(v.count(0) == count);
        CHECK(v.explored_at(0, 100, 100));
        CHECK_FALSE(v.explored_at(0, 300, 300));
        CHECK_FALSE(v.explored_at(1, 100, 100));
        CHECK(v.explored_rect(0, 96, 96, 8, 8));
        CHECK_FALSE(v.explored_rect(0, 96, 96, 80, 8));

        BuildingGhost ghost;
        ghost.id = {7, 2};
        ghost.def = 3;
        ghost.owner = 1;
        ghost.x = 200;
        ghost.z = 40;
        ghost.progress = 400;
        v.remember(2, ghost);

        BinaryWriter summary_bytes;
        v.write_summary(summary_bytes);
        VisionSummary summary;
        {
            BinaryReader sr(summary_bytes.bytes());
            REQUIRE(Vision::read_summary(sr, 10, 2, 512, summary));
            CHECK(sr.at_end());
        }
        BinaryWriter w;
        v.write(w);
        Vision back;
        BinaryReader r(w.bytes());
        REQUIRE(Vision::read(r, 512, true, summary, back));
        CHECK(r.at_end());
        CHECK(back == v);
        CHECK(back.ghosts(2).size() == 1);

        // A checksum that does not match the cells is refused.
        VisionSummary bad = summary;
        bad.sums[0] ^= 1;
        BinaryReader r2(w.bytes());
        Vision untouched;
        CHECK_FALSE(Vision::read(r2, 512, true, bad, untouched));
        CHECK_FALSE(untouched.active());
        // Nor cells for another map size, nor cells where there is no fog.
        BinaryReader r3(w.bytes());
        CHECK_FALSE(Vision::read(r3, 1024, true, summary, untouched));
        BinaryReader r4(w.bytes());
        CHECK_FALSE(Vision::read(r4, 512, false, summary, untouched));
        // Ghosts of an unknown building or owner are refused.
        BinaryReader sr2(summary_bytes.bytes());
        CHECK_FALSE(Vision::read_summary(sr2, 3, 2, 512, summary));
        BinaryReader sr3(summary_bytes.bytes());
        CHECK_FALSE(Vision::read_summary(sr3, 10, 1, 512, summary));
    }

    TEST_CASE("a ghost stays as last seen until its place is seen again") {
        Vision v;
        v.reset(512, 0b1);
        BuildingGhost seen;
        seen.id = {5, 1};
        seen.def = 2;
        seen.owner = 1;
        seen.x = 300;
        seen.z = 300;
        seen.level = 1;
        // Someone stands by it: it is in sight and remembered.
        v.begin_sight();
        v.reveal(0, 302, 302, 12, true);
        REQUIRE(v.sees(0, 300, 300, 4, 4));
        v.remember(0, seen);
        const std::uint32_t revision = v.ghost_revision();
        v.remember(0, seen);  // The same: nothing changes.
        CHECK(v.ghost_revision() == revision);
        // They walk away: out of sight, still remembered as it was.
        v.begin_sight();
        v.reveal(0, 100, 100, 12, true);
        CHECK_FALSE(v.sees(0, 300, 300, 4, 4));
        CHECK(v.explored_at(0, 302, 302));
        REQUIRE(v.ghosts(0).size() == 1);
        CHECK(v.ghosts(0)[0] == seen);
        // A newer look replaces the old one; forgetting takes it away.
        BuildingGhost burning = seen;
        burning.burning = true;
        v.remember(0, burning);
        CHECK(v.ghosts(0)[0].burning);
        CHECK(v.ghost_revision() != revision);
        v.forget(0, {5, 9});  // Another generation: not this one.
        CHECK(v.ghosts(0).size() == 1);
        v.forget(0, seen.id);
        CHECK(v.ghosts(0).empty());
        // Kept sorted by entity index.
        for (const std::uint32_t index : {9u, 3u, 6u}) {
            BuildingGhost g = seen;
            g.id = {index, 0};
            v.remember(0, g);
        }
        REQUIRE(v.ghosts(0).size() == 3);
        CHECK(v.ghosts(0)[0].id.index == 3);
        CHECK(v.ghosts(0)[2].id.index == 9);
    }

    TEST_CASE("with dynamic fog each town remembers the other's buildings it saw") {
        // Two towns in versus; each sees its own buildings, never keeps a
        // ghost of its own, and the ghosts are the same on every machine and
        // after a save.
        const MapData map = small_map(12, 2);
        Game a(content(), map, setup(2, FogMode::Dynamic, true));
        Game b(content(), map, setup(2, FogMode::Dynamic, true));
        run(a, 2000);
        run(b, 2000);
        CHECK(a.vision() == b.vision());
        for (std::uint8_t p = 0; p < 2; ++p) {
            for (const BuildingGhost& h : a.vision().ghosts(a.vision_group(p))) {
                CHECK(a.town_group(h.owner) != a.vision_group(p));
            }
        }
        BinaryWriter w;
        a.save(w);
        Game back(content(), MapData{}, 0, 0);
        BinaryReader r(w.bytes());
        REQUIRE(back.load(r, content()));
        CHECK(back.vision() == a.vision());
        CHECK(back.hash() == a.hash());
        run(a, 500);
        run(back, 500);
        CHECK(back.hash() == a.hash());
    }

    TEST_CASE("with dynamic fog what moves shows only in sight") {
        Game g(content(), small_map(3), setup(1, FogMode::Dynamic));
        FogView view;
        view.begin(g, g.vision_group(0));
        send_out(g);
        run(g, 3000);
        view.update(g);
        std::size_t hidden = 0;
        std::size_t shown = 0;
        for (const Creature& a : g.creatures().data()) {
            const float x = static_cast<float>(a.position.x.raw()) / 65536.0f;
            const float z = static_cast<float>(a.position.z.raw()) / 65536.0f;
            CHECK(view.shows(x, z) == view.in_sight(x, z));
            (view.shows(x, z) ? shown : hidden) += 1;
            if (view.explored(x, z) && !view.in_sight(x, z)) {
                CHECK_FALSE(view.shows(x, z));  // Explored but out of sight.
            }
        }
        CHECK(hidden > 0);  // The animals far away.
        // With static fog, explored is enough.
        Game s(content(), small_map(3), setup(1, FogMode::Static));
        FogView still;
        still.begin(s, s.vision_group(0));
        const Building& tc = town_center(s);
        const float cx = static_cast<float>(tc.x) + 30.0f;
        CHECK(still.shows(cx, static_cast<float>(tc.z)));
        CHECK(still.shows(cx, static_cast<float>(tc.z)) == still.explored(cx, static_cast<float>(tc.z)));
    }

    TEST_CASE("without fog nothing is kept and everything may be built as before") {
        Game g(content(), small_map(3), setup(1, FogMode::None));
        CHECK_FALSE(g.fog());
        CHECK_FALSE(g.vision().active());
        run(g, 30);
        CHECK_FALSE(g.vision().active());
    }

    TEST_CASE("the town's surroundings start explored and building beyond is refused") {
        Game g(content(), small_map(3), setup(1, FogMode::Static));
        REQUIRE(g.vision().active());
        const Building& tc = town_center(g);
        const std::uint8_t group = g.vision_group(0);
        CHECK(g.vision().explored_at(group, tc.x + tc.width / 2, tc.z + tc.depth / 2));
        CHECK(g.vision().explored_at(group, tc.x + tc.width / 2 + 40, tc.z + tc.depth / 2));
        CHECK_FALSE(g.vision().explored_at(group, tc.x + tc.width / 2 + 150, tc.z + tc.depth / 2));

        // A house near the town center goes; one far away does not.
        const DefIndex house = building("house");
        bool near_ok = false;
        for (std::int32_t dx = 10; dx < 30 && !near_ok; dx += 2) {
            near_ok = g.can_place(0, house, tc.x + dx, tc.z, 0) == PlaceError::None;
        }
        CHECK(near_ok);
        std::optional<std::pair<std::int32_t, std::int32_t>> far;
        for (std::int32_t dx = 120; dx < 200 && !far; dx += 4) {
            for (const std::int32_t sign : {1, -1}) {
                const std::int32_t x = tc.x + sign * dx;
                if (x > 10 && x < g.map().size - 20) {
                    const PlaceError e = g.can_place(0, house, x, tc.z, 0);
                    if (e == PlaceError::Unexplored) {
                        far = std::pair{x, tc.z};
                        break;
                    }
                }
            }
        }
        REQUIRE(far.has_value());
        // The same game without fog would take it: only the fog is in the way.
        Game open(content(), small_map(3), setup(1, FogMode::None));
        CHECK(open.can_place(0, house, far->first, far->second, 0) != PlaceError::Unexplored);
        // As a command too.
        Command c;
        c.type = CommandType::PlaceBuilding;
        c.def = house;
        c.position = {Fixed::from_int(far->first), Fixed::from_int(far->second)};
        const std::size_t before = g.buildings().size();
        const std::uint32_t rejected = g.rejected_commands();
        g.apply(c);
        CHECK(g.buildings().size() == before);
        CHECK(g.rejected_commands() == rejected + 1);
    }

    TEST_CASE("revealed fog: the whole map explored from the start, the rest as dynamic") {
        Game g(content(), small_map(3), setup(1, FogMode::Revealed));
        REQUIRE(g.vision().active());
        CHECK(g.vision().all_explored());
        const Building& tc = town_center(g);
        const std::uint8_t group = g.vision_group(0);
        // Explored everywhere on the map, and nowhere off it.
        CHECK(g.vision().explored_at(group, tc.x + tc.width / 2 + 150, tc.z + tc.depth / 2));
        CHECK(g.vision().explored_at(group, 0, 0));
        CHECK(g.vision().explored_at(group, g.map().size - 1, g.map().size - 1));
        CHECK_FALSE(g.vision().explored_at(group, g.map().size + 8, 4));
        CHECK(g.vision().explored_rect(group, 8, 8, 5, 5));
        CHECK_FALSE(g.vision().explored_rect(group, g.map().size - 2, 8, 5, 5));
        // So the fog refuses no place to build: far away is as near.
        const DefIndex house = building("house");
        for (std::int32_t x = 12; x < g.map().size - 20; x += 16) {
            CHECK(g.can_place(0, house, x, tc.z, 0) != PlaceError::Unexplored);
        }
        // The same places a game without fog takes.
        Game open(content(), small_map(3), setup(1, FogMode::None));
        for (std::int32_t x = 12; x < g.map().size - 20; x += 16) {
            CHECK(g.can_place(0, house, x, tc.z, 0) == open.can_place(0, house, x, tc.z, 0));
        }
        // The view: all of it explored, dim where nobody is looking, clear
        // around the town; nothing hidden.
        FogView view;
        view.begin(g, group);
        CHECK(view.game_mode() == FogMode::Revealed);
        CHECK(view.mode() == FogMode::Dynamic);
        std::size_t dim = 0, clear = 0;
        for (const std::uint8_t t : view.texels()) {
            CHECK(t != FogView::kHidden);
            dim += t == FogView::kExplored ? 1 : 0;
            clear += t == FogView::kInSight ? 1 : 0;
        }
        CHECK(clear > 100);
        CHECK(dim > clear);
        CHECK(view.explored(4.0f, 4.0f));
        CHECK_FALSE(view.in_sight(4.0f, 4.0f));
        // Saving and loading keep it, with nothing more in the file than
        // the dynamic fog has.
        run(g, 300);
        BinaryWriter w;
        g.save(w);
        Game back(content(), MapData{}, 0, 0);
        BinaryReader r(w.bytes());
        REQUIRE(back.load(r, content()));
        CHECK(back.rules().fog == FogMode::Revealed);
        CHECK(back.vision().all_explored());
        CHECK(back.hash() == g.hash());
        Game dynamic(content(), small_map(3), setup(1, FogMode::Dynamic));
        run(dynamic, 300);
        BinaryWriter wd;
        dynamic.save(wd);
        CHECK(w.bytes().size() == wd.bytes().size());
        run(g, 200);
        run(back, 200);
        CHECK(back.hash() == g.hash());
    }

    TEST_CASE("the villagers explore as they walk") {
        Game g(content(), small_map(5), setup(1, FogMode::Static));
        const std::uint32_t start = g.vision().count(g.vision_group(0));
        CHECK(start > 0);
        send_out(g);
        run(g, 6000);
        CHECK(g.vision().count(g.vision_group(0)) > start);
    }

    TEST_CASE("the fog does not change the rest of the game") {
        const MapData map = small_map(9, 2);
        Game none(content(), map, setup(2, FogMode::None));
        Game fog(content(), map, setup(2, FogMode::Dynamic));
        run(none, 2000);
        run(fog, 2000);
        const auto a = none.hash_parts();
        const auto b = fog.hash_parts();
        REQUIRE(a.size() == b.size());
        for (std::size_t i = 0; i < a.size(); ++i) {
            const std::string name = a[i].name;
            if (name != "header" && name != "vision") {
                INFO(name);
                CHECK(a[i].hash == b[i].hash);
            }
        }
    }

    TEST_CASE("two games with the same setup explore the same cells") {
        const MapData map = small_map(12, 2);
        Game a(content(), map, setup(2, FogMode::Static, true));
        Game b(content(), map, setup(2, FogMode::Static, true));
        run(a, 1500);
        run(b, 1500);
        CHECK(a.hash() == b.hash());
        CHECK(a.vision() == b.vision());
    }

    TEST_CASE("allies share what they explore unless each town keeps its own") {
        const MapData map = small_map(12, 2);
        Game coop(content(), map, setup(2, FogMode::Static));
        CHECK(coop.vision_group(0) == coop.vision_group(1));
        CHECK(coop.vision().groups() == 0b1);
        Game apart(content(), map, setup(2, FogMode::Static, false, false));
        CHECK(apart.vision_group(0) != apart.vision_group(1));
        Game versus(content(), map, setup(2, FogMode::Static, true, true));
        CHECK(versus.vision_group(0) != versus.vision_group(1));
        CHECK(versus.vision().groups() == 0b11);
        // Each town sees its own start, not the other's.
        const Building& tc1 = town_center(versus, 1);
        CHECK_FALSE(versus.vision().explored_at(versus.vision_group(0), tc1.x + tc1.width / 2, tc1.z + tc1.depth / 2));
        CHECK(versus.vision().explored_at(versus.vision_group(1), tc1.x + tc1.width / 2, tc1.z + tc1.depth / 2));
        CHECK(coop.vision().explored_at(coop.vision_group(0), tc1.x + tc1.width / 2, tc1.z + tc1.depth / 2));
    }

    TEST_CASE("saving and loading keep what was explored") {
        Game g(content(), small_map(3), setup(1, FogMode::Dynamic));
        run(g, 600);
        BinaryWriter w;
        g.save(w);
        Game back(content(), MapData{}, 0, 0);
        BinaryReader r(w.bytes());
        REQUIRE(back.load(r, content()));
        CHECK(r.at_end());
        CHECK(back.vision() == g.vision());
        CHECK(back.hash() == g.hash());
        CHECK(back.rules().fog == FogMode::Dynamic);
        CHECK_FALSE(back.vision().all_explored());
        // And they go on the same way.
        run(g, 300);
        run(back, 300);
        CHECK(back.hash() == g.hash());
    }

    TEST_CASE("the rules keep the fog and shared vision") {
        GameRules rules;
        rules.fog = FogMode::Dynamic;
        rules.shared_vision = false;
        BinaryWriter w;
        rules.write(w);
        GameRules back;
        BinaryReader r(w.bytes());
        REQUIRE(GameRules::read(r, back));
        CHECK(back == rules);
        // An unknown fog mode is refused.
        std::vector<std::uint8_t> bad = w.bytes();
        bad[bad.size() - 2] = 7;
        BinaryReader r2(bad);
        CHECK_FALSE(GameRules::read(r2, back));
    }

    TEST_CASE("the view sees around its people and keeps the texels up to date") {
        Game g(content(), small_map(3), setup(1, FogMode::Dynamic));
        FogView view;
        view.begin(g, g.vision_group(0));
        REQUIRE(view.side() == g.vision().side());
        CHECK(view.take_dirty().empty());  // The caller sends the whole texture first.
        const Building& tc = town_center(g);
        const float cx = static_cast<float>(tc.x) + static_cast<float>(tc.width) * 0.5f;
        const float cz = static_cast<float>(tc.z) + static_cast<float>(tc.depth) * 0.5f;
        CHECK(view.in_sight(cx, cz));
        CHECK(view.shows(cx, cz));
        CHECK_FALSE(view.explored(cx + 200.0f, cz));
        CHECK_FALSE(view.shows(cx + 200.0f, cz));
        const auto texel = [&](float x, float z) {
            const auto tx = static_cast<std::size_t>(x / static_cast<float>(kFogCell));
            const auto tz = static_cast<std::size_t>(z / static_cast<float>(kFogCell));
            return view.texels()[tz * static_cast<std::size_t>(view.side()) + tx];
        };
        CHECK(texel(cx, cz) == FogView::kInSight);
        CHECK(texel(cx + 200.0f, cz) == FogView::kHidden);
        // As villagers walk, what changed goes to the GPU in tiles.
        send_out(g);
        bool changed = false;
        for (int i = 0; i < 6000 && !changed; ++i) {
            g.step();
            view.update(g);
            changed = !view.take_dirty().empty();
        }
        CHECK(changed);
        // Revealing everything shows everything, only in this view.
        const std::uint64_t hash = g.hash();
        view.set_revealed(true);
        CHECK(view.mode() == FogMode::None);
        CHECK(view.shows(cx + 200.0f, cz));
        CHECK(g.hash() == hash);
    }

    TEST_CASE("with dynamic fog the explored ground out of sight is dim") {
        Game g(content(), small_map(3), setup(1, FogMode::Dynamic));
        // Walk until something explored falls out of sight.
        FogView view;
        view.begin(g, g.vision_group(0));
        send_out(g);
        bool dim = false;
        for (int i = 0; i < 8000 && !dim; ++i) {
            g.step();
            view.update(g);
            if (i % 50 == 0) {
                for (const std::uint8_t t : view.texels()) {
                    if (t == FogView::kExplored) {
                        dim = true;
                        break;
                    }
                }
            }
        }
        CHECK(dim);
        // Static fog keeps it all in view.
        Game s(content(), small_map(3), setup(1, FogMode::Static));
        FogView still;
        still.begin(s, s.vision_group(0));
        send_out(s);
        run(s, 4000);
        still.update(s);
        for (const std::uint8_t t : still.texels()) {
            CHECK(t != FogView::kExplored);
        }
    }

    TEST_CASE("the minimap darkens what was never seen") {
        Game g(content(), small_map(3), setup(1, FogMode::Static));
        FogView view;
        view.begin(g, g.vision_group(0));
        std::vector<std::uint8_t> image = minimap::render(g.map());
        const std::vector<std::uint8_t> clear = image;
        minimap::apply_fog(image, g.map().size, view);
        std::size_t dark = 0;
        std::size_t kept = 0;
        for (std::size_t i = 0; i < image.size(); i += 4) {
            dark += image[i] == 14 && image[i + 1] == 15 && image[i + 2] == 20 ? 1 : 0;
            kept += image[i] == clear[i] ? 1 : 0;
        }
        CHECK(dark > image.size() / 4 / 2);  // Most of the map.
        CHECK(kept > 0);                     // Not the town.
    }

    TEST_CASE("the ceiling hides a wide plateau but not a lone peak nor a tall tree") {
        // Flat ground at 10 m, a plateau 30 m higher and 160 m wide, and a
        // peak as high but 12 m wide far from it.
        MapData map;
        map.size = 1024;
        const std::int32_t v = map.vertices_per_side();
        map.heights.assign(static_cast<std::size_t>(v) * static_cast<std::size_t>(v), 1000);
        for (std::int32_t z = 0; z < v; ++z) {
            for (std::int32_t x = 0; x < v; ++x) {
                const bool plateau = std::abs(x - 256) <= 80 && std::abs(z - 256) <= 80;
                const bool peak = std::abs(x - 700) <= 6 && std::abs(z - 150) <= 6;
                if (plateau || peak) {
                    map.heights[static_cast<std::size_t>(z) * static_cast<std::size_t>(v) + static_cast<std::size_t>(x)] = 4000;
                }
            }
        }
        const std::int32_t side = map.size / FogView::kCeilingCell;
        const std::vector<std::uint16_t> ceiling = fog_ceiling(map, side);
        REQUIRE(ceiling.size() == static_cast<std::size_t>(side) * static_cast<std::size_t>(side));
        const auto at = [&](std::int32_t x, std::int32_t z) {
            return ceiling[static_cast<std::size_t>(z / FogView::kCeilingCell) * static_cast<std::size_t>(side) +
                           static_cast<std::size_t>(x / FogView::kCeilingCell)];
        };
        CHECK(at(256, 256) > 4000);  // The middle of the plateau stays under the fog.
        CHECK(at(700, 150) < 4000);  // The peak sticks out.
        // Far from both, 14 m over the ground: a big tree (18 m) shows, a small one (4,5 m) does not.
        CHECK(at(900, 900) == 1000 + FogView::kCeilingAbove);
        CHECK(1000 + 1800 > at(900, 900));
        CHECK(1000 + 450 < at(900, 900));
        CHECK(fog_ceiling(map, 0).empty());
    }

    TEST_CASE("landmarks carry their mark to the renderer") {
        auto copy = std::make_shared<Content>(test::core_content());
        REQUIRE_FALSE(copy->flora.species.empty());
        const MapData map = small_map(3);
        const MapFeature* tree = nullptr;
        for (const MapFeature& f : map.features) {
            if (f.type == FeatureType::Tree) {
                tree = &f;
                break;
            }
        }
        REQUIRE(tree != nullptr);
        CHECK_FALSE(feature_instance(map, *tree, copy.get(), Season::Summer, false).landmark);
        copy->flora.species[tree->species].landmark = true;
        CHECK(feature_instance(map, *tree, copy.get(), Season::Summer, false).landmark);
    }

    TEST_CASE("only tall buildings and landmarks of others show in the unexplored, and nothing that moves") {
        auto copy = std::make_shared<Content>(test::core_content());
        const MapData map = small_map(12, 2);
        Game g(copy, map, setup(2, FogMode::Static, true));
        FogView fog;
        fog.begin(g, g.vision_group(0));
        VillageView view;
        view.set_fog(&fog);
        const Building& mine = town_center(g, 0);
        const Building& rival = town_center(g, 1);
        REQUIRE(fog.rect_unexplored(rival.x, rival.z, rival.width, rival.depth));
        CHECK_FALSE(view.building_shown(g, rival));
        CHECK_FALSE(view.building_silhouette(g, mine));  // Ours shows anyway.
        // Without its model, the rival's town center is 5 m high: under the ceiling.
        CHECK_FALSE(view.building_silhouette(g, rival));
        copy->buildings[rival.def].landmark = true;
        CHECK(view.building_silhouette(g, rival));
        // Whatever moves there stays hidden, however tall.
        const float rx = static_cast<float>(rival.x) + 2.0f;
        const float rz = static_cast<float>(rival.z) + 2.0f;
        CHECK_FALSE(view.mover_shown(g, true, 1, rx, rz));
        CHECK_FALSE(view.mover_shown(g, false, 0, rx, rz));
        // The ceiling does not touch the game.
        const std::uint64_t hash = g.hash();
        CHECK(fog.ceiling_side() == fog.side() * kFogCell / FogView::kCeilingCell);
        CHECK(fog.ceiling_at(rx, rz) > 10.0f);
        CHECK(g.hash() == hash);
    }
}
