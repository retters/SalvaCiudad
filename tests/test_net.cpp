#include <doctest.h>

#include <memory>

#include <SDL3/SDL_timer.h>
#include <optional>
#include <ostream>

#include "core/speed.h"
#include "game/build_info.h"
#include "net/enet_link.h"
#include "net/lockstep.h"
#include "net/protocol.h"
#include "sim/worldgen.h"
#include "test_util.h"
#include "version.h"

using namespace sc;
using namespace sc::net;

namespace {

std::shared_ptr<const sim::Content> content() {
    return std::shared_ptr<const sim::Content>(std::shared_ptr<const sim::Content>{}, &sc::test::core_content());
}

LocalInfo info(const std::string& name) {
    LocalInfo i;
    i.game_version = "0.9.0";
    i.content_hash = content()->hash;
    i.mods = {{"core", "1.0.0", 7}};
    i.name = name;
    return i;
}

// Maps are generated once per settings and shared by the machines.
const sim::MapData& map_for(const sim::MapSettings& s) {
    static std::map<std::pair<std::uint64_t, int>, sim::MapData> cache;
    const auto key = std::make_pair(s.seed, static_cast<int>(s.players));
    auto it = cache.find(key);
    if (it == cache.end()) {
        std::optional<sim::MapData> m = sim::generate_map(s, *content());
        REQUIRE(m.has_value());
        it = cache.emplace(key, std::move(*m)).first;
    }
    return it->second;
}

struct Machine {
    MemoryNetwork::Endpoint* link = nullptr;
    std::unique_ptr<NetSession> session;
    std::unique_ptr<sim::Game> game;
    std::vector<NetEvent> events;
};

class Cluster {
public:
    MemoryNetwork net;
    std::vector<Machine> m;
    std::uint64_t now = 1000;

    Cluster() {
        Machine host;
        host.link = &net.add();
        host.session = std::make_unique<NetHost>(*host.link, info("Host"));
        m.push_back(std::move(host));
    }
    NetHost& host() { return static_cast<NetHost&>(*m[0].session); }
    NetClient& client(std::size_t i) { return static_cast<NetClient&>(*m[i].session); }

    std::size_t join(const std::string& name, LocalInfo li = {}) {
        Machine c;
        c.link = &net.add();
        if (li.name.empty()) {
            li = info(name);
        }
        c.session = std::make_unique<NetClient>(*c.link, m[0].link->self_id(), li);
        net.connect(m[0].link->self_id(), c.link->self_id());
        m.push_back(std::move(c));
        return m.size() - 1;
    }

    // Everything each machine has to do in one frame.
    void frame(int ticks) {
        now += 100;
        for (std::size_t i = 0; i < m.size(); ++i) {
            Machine& x = m[i];
            if (!x.session) {
                continue;
            }
            x.session->poll(now);
            if (std::optional<Start> s = x.session->take_start()) {
                x.game = std::make_unique<sim::Game>(content(), map_for(s->config.map),
                                                     sim::GameSetup{s->players, s->config.seed, s->config.shared_town,
                                                                    s->config.rules});
                x.session->game_built(x.game.get(), map_hash(x.game->map()));
            }
            if (std::optional<std::vector<std::uint8_t>> snap = x.session->take_snapshot()) {
                auto g = std::make_unique<sim::Game>(content(), sim::MapData{}, 0, 0);
                sim::BinaryReader r(*snap);
                REQUIRE(g->load(r, content()));
                x.game = std::move(g);
                x.session->snapshot_loaded(x.game.get());
            }
            (void)x.session->advance(ticks, now);
            for (NetEvent& e : x.session->take_events()) {
                x.events.push_back(std::move(e));
            }
        }
    }

    void frames(int n, int ticks = 1) {
        for (int i = 0; i < n; ++i) {
            frame(ticks);
        }
    }

    void ready_all() {
        for (std::size_t i = 1; i < m.size(); ++i) {
            client(i).set_info(client(i).lobby().players.empty() ? "x" : "Player" + std::to_string(i),
                               static_cast<std::uint8_t>(i % kColors), true);
        }
        frames(3, 0);
    }

    // Lets the clients run every turn they have, with the host still.
    void settle() {
        for (int i = 0; i < 40; ++i) {
            now += 100;
            for (std::size_t k = 1; k < m.size(); ++k) {
                if (m[k].session) {
                    m[k].session->poll(now);
                    (void)m[k].session->advance(0, now);
                    (void)m[k].session->advance(8, now);
                }
            }
        }
    }
};

// A building of `def` placed near the player's town, if there is room.
std::optional<sim::Command> place_near(const sim::Game& g, std::uint8_t player, const char* def, int k) {
    const sim::DefIndex d = content()->find_building(def);
    const sim::Building* tc = g.buildings().get(g.player(g.town_of(player)).town_center);
    if (tc == nullptr) {
        return std::nullopt;
    }
    for (int r = 12 + k * 3; r < 90; r += 3) {
        for (int a = 0; a < 8; ++a) {
            const int x = tc->x + (a % 3 - 1) * r;
            const int z = tc->z + (a / 3 - 1) * r;
            if (g.can_place(g.town_of(player), d, x, z, 0) == sim::PlaceError::None) {
                sim::Command c;
                c.type = sim::CommandType::PlaceBuilding;
                c.def = d;
                c.position = {sim::Fixed::from_int(x), sim::Fixed::from_int(z)};
                return c;
            }
        }
    }
    return std::nullopt;
}

GameConfig config(std::uint64_t seed, bool shared) {
    GameConfig c;
    c.map.seed = seed;
    c.map.size = sim::MapSize::Small;
    c.shared_town = shared;
    c.seed = seed * 7 + 1;
    return c;
}

void expect_same_games(Cluster& c) {
    // Clients may be up to the delay ahead of the host: bring everybody
    // to the same tick first.
    std::uint64_t target = c.m[0].game->tick();
    for (std::size_t i = 1; i < c.m.size(); ++i) {
        if (c.m[i].session && c.m[i].game && c.m[i].session->state() != NetSession::State::Closed) {
            target = std::max(target, c.m[i].game->tick());
        }
    }
    c.m[0].session->poll(c.now);
    (void)c.m[0].session->advance(static_cast<int>(target - c.m[0].game->tick()), c.now);
    for (std::size_t i = 1; i < c.m.size(); ++i) {
        if (c.m[i].session && c.m[i].game && c.m[i].game->tick() < target) {
            c.m[i].session->poll(c.now);
            (void)c.m[i].session->advance(static_cast<int>(target - c.m[i].game->tick()), c.now);
        }
    }
    const std::uint64_t tick = c.m[0].game->tick();
    const std::uint64_t hash = c.m[0].game->hash();
    for (std::size_t i = 1; i < c.m.size(); ++i) {
        if (!c.m[i].session || c.m[i].session->state() == NetSession::State::Closed) {
            continue;
        }
        REQUIRE(c.m[i].game != nullptr);
        CHECK_MESSAGE(c.m[i].game->tick() == tick, "machine " << i);
        CHECK_MESSAGE(c.m[i].game->hash() == hash, "machine " << i);
    }
}

}  // namespace

TEST_SUITE("net") {
    TEST_CASE("every message survives the trip, and garbage is refused") {
        Lobby lobby;
        lobby.config = config(5, true);
        lobby.phase = LobbyPhase::Playing;
        lobby.players = {{0, "Ana", 3, true, true, true}, {4, "Ñandú", 11, false, false, true}};
        Turn turn;
        turn.tick = 99;
        turn.speed = 8;
        sim::Command cmd;
        cmd.type = sim::CommandType::SetWorkers;
        cmd.player = 3;
        cmd.entity = {5, 1};
        cmd.value = 2;
        turn.commands = {{3, cmd}};
        const std::vector<Message> all = {
            Hello{kProtocolVersion, "0.9.0", 42, {{"core", "1.0.0", 9}}, "Ana"},
            Welcome{7},
            Reject{RejectReason::Mods, "0.9.0", {{"core", "1.0.0", 9}}},
            lobby,
            SetInfo{"Bob", 2, true},
            Start{config(3, false), 4},
            Loaded{123},
            Commands{{cmd}},
            turn,
            Ack{50, true, PartHashes{{1, 2, 3, 4, 5, 6, 7}}},
            pack_snapshot(10, std::vector<std::uint8_t>(1000, 7)),
            SpeedPropose{12},
            SpeedVote{4, 2, 1},
            SpeedAnswer{4, true},
            SpeedSet{0, 2, SpeedReason::Pause},
            VoteEnded{4},
            Notice{NoticeKind::Rejoined, 3, 77},
        };
        CHECK(all.size() == std::variant_size_v<Message>);
        for (const Message& msg : all) {
            const std::vector<std::uint8_t> bytes = encode(msg);
            const std::optional<Message> back = decode(bytes);
            REQUIRE(back.has_value());
            CHECK(back->index() == msg.index());
            CHECK(encode(*back) == bytes);
            // Cut short anywhere, it is refused.
            for (std::size_t n = 0; n < bytes.size(); ++n) {
                CHECK_FALSE(decode(std::span(bytes.data(), n)).has_value());
            }
        }
        // Out of range values.
        CHECK_FALSE(decode(encode(Welcome{12})).has_value());
        CHECK_FALSE(decode(encode(SetInfo{"", 1, false})).has_value());
        CHECK_FALSE(decode(encode(SetInfo{"a\nb", 1, false})).has_value());
        CHECK_FALSE(decode(encode(SpeedPropose{3})).has_value());   // Not a step.
        CHECK_FALSE(decode(encode(SpeedPropose{24})).has_value());  // x6: only alone.
        CHECK(decode(encode(SpeedPropose{20})).has_value());        // x5.
        CHECK(decode(encode(SpeedPropose{1})).has_value());         // x0.25.
        std::vector<std::uint8_t> junk = {200, 1, 2, 3};
        CHECK_FALSE(decode(junk).has_value());
        std::vector<std::uint8_t> snapshot;
        CHECK(unpack_snapshot(pack_snapshot(1, std::vector<std::uint8_t>(5000, 3)), snapshot));
        CHECK(snapshot.size() == 5000);
    }

    TEST_CASE("twelve players in a common town stay in step") {
        Cluster c;
        for (int i = 1; i < 12; ++i) {
            c.join("P" + std::to_string(i));
        }
        c.frames(3, 0);
        c.host().set_config(config(21, true));
        c.ready_all();
        REQUIRE(c.host().lobby().players.size() == 12);
        REQUIRE(c.host().can_start());
        REQUIRE(c.host().start());
        c.frames(3, 0);
        CHECK(c.host().state() == NetSession::State::Playing);
        for (std::size_t i = 0; i < c.m.size(); ++i) {
            REQUIRE(c.m[i].game != nullptr);
            CHECK(c.m[i].session->local_slot() == i);
        }
        // Everybody gives orders now and then.
        for (int f = 0; f < 400; ++f) {
            if (f % 37 == 0) {
                const std::size_t who = static_cast<std::size_t>(f / 37) % c.m.size();
                if (auto cmd = place_near(*c.m[who].game, static_cast<std::uint8_t>(who), "core:house", f / 37)) {
                    c.m[who].session->issue(*cmd);
                }
            }
            c.frame(1);
        }
        c.settle();
        expect_same_games(c);
        CHECK(c.host().desyncs() == 0);
        CHECK(c.m[0].game->tick() > 350);
        // The orders were carried out, in the common town.
        CHECK(c.m[0].game->buildings().size() > 3);
    }

    TEST_CASE("separate towns, one per player") {
        Cluster c;
        for (int i = 1; i < 4; ++i) {
            c.join("P" + std::to_string(i));
        }
        c.frames(3, 0);
        c.host().set_config(config(22, false));
        c.ready_all();
        REQUIRE(c.host().start());
        c.frames(3, 0);
        REQUIRE(c.m[0].game != nullptr);
        CHECK(c.m[0].game->player_count() == 4);
        for (std::uint8_t p = 0; p < 4; ++p) {
            CHECK(c.m[0].game->population(p) == sim::village::kStartVillagers);
        }
        // A player cannot give orders to another player's town.
        if (auto cmd = place_near(*c.m[2].game, 2, "core:house", 0)) {
            c.m[2].session->issue(*cmd);
        }
        c.frames(200, 1);
        c.settle();
        expect_same_games(c);
    }

    TEST_CASE("a player who drops out comes back and follows") {
        Cluster c;
        c.join("Ana");
        c.join("Bob");
        c.frames(3, 0);
        c.host().set_config(config(23, false));
        c.ready_all();
        REQUIRE(c.host().start());
        c.frames(100, 1);
        // Bob's game closes by force.
        const std::string bob = c.m[2].session->lobby().players[2].name;
        const PeerId gone = c.m[2].link->self_id();
        c.net.cut(gone);
        c.m[0].link->disconnect(gone);
        c.m[2].session.reset();
        c.frames(50, 1);
        CHECK(c.m[0].game->tick() > 130);  // The others went on.
        // He starts the game again and joins with the same name.
        LocalInfo li = info(bob);
        const std::size_t again = c.join(bob, li);
        c.frames(5, 0);
        c.frames(60, 1);
        c.settle();
        CHECK(c.m[again].session->state() == NetSession::State::Playing);
        CHECK(c.m[again].session->local_slot() == 2);
        c.m[2].game.reset();  // The old machine is gone.
        expect_same_games(c);
    }

    TEST_CASE("at x5 the game keeps in step: the margins follow the speed") {
        Cluster c;
        c.join("Ana");
        c.frames(3, 0);
        c.host().set_config(config(25, true));
        c.ready_all();
        REQUIRE(c.host().start());
        c.frames(10, 1);
        c.host().request_speed(sc::speed::kMaxNetwork);
        c.frames(2, 0);
        REQUIRE(c.client(1).vote().has_value());
        c.client(1).answer_vote(true);
        c.frames(2, 0);
        REQUIRE(c.host().speed() == sc::speed::kMaxNetwork);
        // Five ticks a frame, as the clock asks for at x5.
        const std::uint64_t before = c.m[0].game->tick();
        c.frames(200, 5);
        CHECK(c.m[0].game->tick() >= before + 900);  // Hardly a frame waiting for anybody.
        CHECK(c.m[1].game->tick() + 60 >= c.m[0].game->tick());  // The client keeps up.
        CHECK(c.host().desyncs() == 0);  // Through four checks, 250 ticks apart.
        CHECK(c.host().speed() == sc::speed::kMaxNetwork);  // Nobody was slow.
        // The check comes as often in real time as at x1: every 250 ticks.
        CHECK(hash_interval(sc::speed::kMaxNetwork) == 5 * kHashInterval);
        CHECK(hash_interval(sc::speed::kNormal) == kHashInterval);
        CHECK(hash_interval(sc::speed::kMin) == kHashInterval);
    }

    TEST_CASE("a desynchronization is found and repaired") {
        Cluster c;
        c.join("Ana");
        c.frames(3, 0);
        c.host().set_config(config(24, true));
        c.ready_all();
        REQUIRE(c.host().start());
        c.frames(20, 1);
        // Ana's game goes its own way (as a bug would do).
        sim::Command cheat;
        cheat.type = sim::CommandType::DevGrant;
        cheat.def = content()->find_resource("core:log");
        cheat.value = 500;
        c.m[1].game->apply(cheat);
        c.frames(120, 1);
        CHECK(c.host().desyncs() >= 1);
        bool told = false;
        for (const NetEvent& e : c.m[0].events) {
            told = told || e.kind == NetEvent::Kind::Desync;
        }
        CHECK(told);
        c.settle();
        expect_same_games(c);
    }

    TEST_CASE("speed: pause at once, the rest by vote") {
        Cluster c;
        c.join("Ana");
        c.frames(3, 0);
        c.host().set_config(config(25, true));
        c.ready_all();
        REQUIRE(c.host().start());
        c.frames(10, 1);
        c.client(1).request_speed(0);
        c.frames(2, 1);
        CHECK(c.host().speed() == 0);
        const std::uint64_t paused_at = c.m[0].game->tick();
        c.frames(10, 1);
        CHECK(c.m[0].game->tick() == paused_at);
        // Resuming needs everybody.
        c.client(1).request_speed(8);
        c.frames(2, 0);
        REQUIRE(c.host().vote().has_value());
        c.host().answer_vote(true);
        c.frames(2, 0);
        CHECK(c.host().speed() == 8);
        CHECK(c.client(1).speed() == 8);
        // A refused vote changes nothing.
        c.host().request_speed(12);
        c.frames(2, 0);
        REQUIRE(c.client(1).vote().has_value());
        c.client(1).answer_vote(false);
        c.frames(2, 0);
        CHECK(c.host().speed() == 8);
        // Over x5 there is nothing to vote with others.
        c.host().request_speed(24);
        c.frames(2, 0);
        CHECK_FALSE(c.client(1).vote().has_value());
        // And one nobody answers ends by itself.
        c.client(1).request_speed(4);
        c.frames(3, 0);
        CHECK(c.host().vote().has_value());
        c.now += NetSession::kVoteTimeoutMs;
        c.frames(1, 0);
        CHECK_FALSE(c.host().vote().has_value());
        CHECK(c.host().speed() == 8);
    }

    TEST_CASE("other versions and other mods are refused with the reason") {
        Cluster c;
        LocalInfo old = info("Old");
        old.game_version = "0.1.0";
        const std::size_t a = c.join("Old", old);
        LocalInfo modded = info("Modded");
        modded.content_hash ^= 1;
        const std::size_t b = c.join("Modded", modded);
        c.frames(4, 0);
        const auto reason = [&](std::size_t i) {
            for (const NetEvent& e : c.m[i].events) {
                if (e.kind == NetEvent::Kind::Rejected) {
                    return e.reject.reason;
                }
            }
            return RejectReason::Count;
        };
        CHECK(reason(a) == RejectReason::Version);
        CHECK(reason(b) == RejectReason::Mods);
        CHECK(c.host().lobby().players.size() == 1);
    }

    TEST_CASE("another build with the same version number is refused") {
        // The game sends its version with the build (D-3321).
        const std::string_view full = full_version();
        CHECK(version_number(full) == SC_VERSION_STRING);
        CHECK(full.size() == std::string_view(SC_VERSION_STRING).size() + 1 + 12);
        CHECK(build_id().size() == 12);
        CHECK(build_id().find_first_not_of("0123456789abcdef") == std::string_view::npos);
        CHECK(full.ends_with(build_id()));
        CHECK(version_number("0.20.0") == "0.20.0");

        // The host of the cluster plays "0.9.0"; a client adds a build to it.
        Cluster c;
        LocalInfo other = info("Other");
        other.game_version += "+000000000000";
        const std::size_t a = c.join("Other", other);
        LocalInfo same = info("Same");
        const std::size_t b = c.join("Same", same);
        c.frames(4, 0);
        bool refused = false;
        for (const NetEvent& e : c.m[a].events) {
            refused = refused || (e.kind == NetEvent::Kind::Rejected && e.reject.reason == RejectReason::Version &&
                                  version_number(e.reject.host_version) == version_number(other.game_version));
        }
        CHECK(refused);
        CHECK(c.m[b].session->state() != NetSession::State::Closed);
    }

    TEST_CASE("local network discovery datagrams") {
        CHECK(is_discovery_probe(discovery_probe()));
        CHECK_FALSE(is_discovery_probe(std::vector<std::uint8_t>{1, 2, 3}));
        const std::vector<std::uint8_t> answer = discovery_answer(47801, "Ana", 3, true);
        LanGame g;
        REQUIRE(read_discovery_answer(answer, g));
        CHECK(g.port == 47801);
        CHECK(g.host_name == "Ana");
        CHECK(g.players == 3);
        CHECK(g.playing);
        for (std::size_t n = 0; n < answer.size(); ++n) {
            CHECK_FALSE(read_discovery_answer(std::span(answer.data(), n), g));
        }
        CHECK_FALSE(read_discovery_answer(discovery_answer(0, "Ana", 3, true), g));
        CHECK_FALSE(read_discovery_answer(discovery_answer(1, "", 3, true), g));
        CHECK_FALSE(read_discovery_answer(discovery_answer(1, "Ana", 13, true), g));
    }
}

TEST_SUITE("net_enet") {
    TEST_CASE("a host and a client over ENet on this machine") {
        EnetLibrary library;
        REQUIRE(library.ok());
        const std::uint16_t port = 47850;
        EnetLink host_link;
        REQUIRE(host_link.listen(port, 4, true));
        EnetLink client_link;
        REQUIRE(client_link.connect("127.0.0.1", port));
        NetHost host(host_link, info("Host"));
        NetClient client(client_link, client_link.server(), info("Ana"));
        host.set_config(config(26, true));
        std::uint64_t now = 0;
        const auto pump = [&](int frames) {
            for (int i = 0; i < frames; ++i) {
                now += 10;
                host.poll(now);
                client.poll(now);
                SDL_Delay(2);
            }
        };
        for (int i = 0; i < 300 && client.state() != NetSession::State::Lobby; ++i) {
            pump(1);
        }
        REQUIRE(client.state() == NetSession::State::Lobby);
        client.set_info("Ana", 4, true);
        for (int i = 0; i < 300 && !host.can_start(); ++i) {
            pump(1);
        }
        REQUIRE(host.lobby().players.size() == 2);
        CHECK(host.lobby().players[1].name == "Ana");
        REQUIRE(host.start());
        std::unique_ptr<sim::Game> host_game;
        std::unique_ptr<sim::Game> client_game;
        for (int i = 0; i < 300 && !(host_game && client_game); ++i) {
            pump(1);
            if (auto s = host.take_start()) {
                host_game = std::make_unique<sim::Game>(content(), map_for(s->config.map), s->players, s->config.seed,
                                                        s->config.shared_town);
                host.game_built(host_game.get(), map_hash(host_game->map()));
            }
            if (auto s = client.take_start()) {
                client_game = std::make_unique<sim::Game>(content(), map_for(s->config.map), s->players, s->config.seed,
                                                          s->config.shared_town);
                client.game_built(client_game.get(), map_hash(client_game->map()));
            }
        }
        REQUIRE(host_game);
        REQUIRE(client_game);
        for (int i = 0; i < 400 && client_game->tick() < 120; ++i) {
            pump(1);
            (void)host.advance(1, now);
            (void)client.advance(1, now);
        }
        CHECK(client_game->tick() >= 120);
        // Same tick, same game.
        while (host_game->tick() < client_game->tick()) {
            (void)host.advance(1, now);
        }
        while (client_game->tick() < host_game->tick()) {
            pump(1);
            (void)client.advance(1, now);
        }
        CHECK(client_game->hash() == host_game->hash());
        CHECK(host.desyncs() == 0);
        client_link.close();
        pump(20);
    }
}
