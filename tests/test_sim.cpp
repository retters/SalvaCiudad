#include <doctest.h>

#include <cmath>
#include <filesystem>
#include <ostream>
#include <regex>
#include <string>

#include "game/replay_file.h"
#include "sim/command.h"
#include "sim/entity.h"
#include "sim/fixed.h"
#include "sim/rng.h"
#include "sim/serialize.h"
#include "sim/simulation.h"
#include "sim/world.h"
#include "test_util.h"

using namespace sc;
using namespace sc::sim;

namespace {

Fixed f(int v) {
    return Fixed::from_int(v);
}

// The scripted game used by the determinism tests: groups of walkers
// arrive for several players, some are sent somewhere, some removed (one
// twice, which must be rejected the same way every time).
std::vector<ScheduledCommand> script() {
    std::vector<ScheduledCommand> s;
    const auto spawn = [&](std::uint64_t tick, std::uint8_t player, int x, int z, std::uint16_t count) {
        Command c;
        c.type = CommandType::SpawnWalkers;
        c.player = player;
        c.position = {f(x), f(z)};
        c.count = count;
        s.push_back({tick, 0, c});
    };
    const auto send = [&](std::uint64_t tick, std::uint32_t index, int x, int z) {
        Command c;
        c.type = CommandType::SendWalker;
        c.entity = {index, 0};
        c.position = {f(x), f(z)};
        s.push_back({tick, 0, c});
    };
    const auto remove = [&](std::uint64_t tick, std::uint32_t index) {
        Command c;
        c.type = CommandType::RemoveWalker;
        c.entity = {index, 0};
        s.push_back({tick, 0, c});
    };
    spawn(0, 0, 0, 0, 40);
    spawn(5, 1, 100, -50, 30);
    spawn(20, 2, -200, 150, 64);
    send(100, 0, 300, 300);
    remove(150, 1);
    remove(200, 1);  // Already gone: rejected.
    spawn(300, 11, 400, 400, 50);
    send(650, 5, -480, -480);
    spawn(800, 3, -300, -300, 64);
    remove(900, 7);
    spawn(1200, 4, 10, 20, 25);
    return s;
}

void schedule_from(Simulation& sim, std::uint64_t from_tick) {
    for (const ScheduledCommand& c : script()) {
        if (c.tick >= from_tick) {
            REQUIRE(sim.schedule(c.tick, c.command));
        }
    }
}

Simulation run(std::uint64_t seed, std::uint64_t ticks) {
    Simulation sim(seed);
    schedule_from(sim, 0);
    while (sim.tick() < ticks) {
        sim.step();
    }
    return sim;
}

constexpr std::uint64_t kScenarioTicks = 1500;

// The hash the scenario must give on every build and every machine. If the
// simulation rules change on purpose, update it and bump kRulesVersion.
constexpr std::uint64_t kGoldenHash = 0xed6fa5148c47bb17ull;

}  // namespace

TEST_SUITE("sim_fixed") {
    TEST_CASE("basic arithmetic and rounding") {
        CHECK((f(3) + f(4)).raw() == f(7).raw());
        CHECK((f(3) * f(4)) == f(12));
        CHECK((f(7) / f(2)) == Fixed::from_ratio(7, 2));
        CHECK(Fixed::from_ratio(1, 3).raw() == 21845);   // Toward zero.
        CHECK(Fixed::from_ratio(-1, 3).raw() == -21845);
        CHECK((Fixed::from_raw(-1) * Fixed::from_raw(1)).raw() == -1);  // Floor of a tiny negative.
        CHECK(Fixed::from_ratio(-7, 2).floor_int() == -4);
        CHECK(f(5).floor_int() == 5);
    }

    TEST_CASE("saturation instead of overflow") {
        CHECK(f(30000) * f(30000) == Fixed::max());
        CHECK(f(-30000) * f(30000) == Fixed::min());
        CHECK(Fixed::max() + Fixed::one() == Fixed::max());
        CHECK(-Fixed::min() == Fixed::max());
        CHECK(f(1) / Fixed{} == Fixed::max());
        CHECK(f(-1) / Fixed{} == Fixed::min());
        CHECK(Fixed::from_int(100000) == Fixed::max());
        CHECK(Fixed::from_ratio(INT64_MAX, 1) == Fixed::max());
        CHECK(Fixed::from_ratio(1, 0) == Fixed{});
    }

    TEST_CASE("square roots are exact floors") {
        CHECK(sqrt(f(4)) == f(2));
        CHECK(sqrt(f(2)).raw() == 92681);  // floor(sqrt(2) * 65536)
        CHECK(sqrt(f(-4)) == Fixed{});
        CHECK(isqrt(0) == 0);
        CHECK(isqrt(99) == 9);
        CHECK(isqrt(UINT64_MAX) == 4294967295ull);
        CHECK((FixedVec2{f(3), f(4)}.length()) == f(5));
        CHECK((FixedVec2{f(20000), f(20000)}.length()).floor_int() == 28284);
        CHECK((FixedVec2{f(30000), f(30000)}.length()) == Fixed::max());  // Saturates.
    }

    TEST_CASE("trigonometry matches the reference closely") {
        CHECK(sin(Angle{}) == Fixed{});
        CHECK(sin(Angle{16384}) == Fixed::one());
        CHECK(cos(Angle{}) == Fixed::one());
        CHECK(sin(Angle{32768}) == Fixed{});
        CHECK(sin(Angle{49152}) == -Fixed::one());
        for (std::uint32_t u = 0; u < 65536; u += 97) {
            const double ref = std::sin(static_cast<double>(u) / 65536.0 * 2.0 * 3.141592653589793);
            CHECK(std::abs(static_cast<double>(sin(Angle{static_cast<std::uint16_t>(u)}).raw()) / 65536.0 - ref) < 2e-5);
        }
    }

    TEST_CASE("atan2 finds directions within a few units") {
        const auto units = [](Angle a) { return static_cast<int>(a.units); };
        CHECK(std::abs(units(atan2(Fixed{}, f(1)))) <= 2);
        CHECK(std::abs(units(atan2(f(1), Fixed{})) - 16384) <= 2);
        CHECK(std::abs(units(atan2(Fixed{}, f(-1))) - 32768) <= 2);
        CHECK(std::abs(units(atan2(f(-1), Fixed{})) - 49152) <= 2);
        CHECK(atan2(Fixed{}, Fixed{}) == Angle{});
        for (std::uint32_t u = 0; u < 65536; u += 331) {
            const Angle a{static_cast<std::uint16_t>(u)};
            const Angle back = atan2(sin(a) * f(100), cos(a) * f(100));
            const int diff = static_cast<std::int16_t>(static_cast<std::uint16_t>(back.units - a.units));
            CHECK_MESSAGE(std::abs(diff) <= 4, "angle " << u);
        }
    }
}

TEST_SUITE("sim_rng") {
    TEST_CASE("PCG32 matches the reference sequence") {
        // pcg32-demo with seed 42, stream 54.
        Rng rng(42, 54);
        CHECK(rng.next_u32() == 0xa15c02b7u);
        CHECK(rng.next_u32() == 0x7b47f409u);
        CHECK(rng.next_u32() == 0xba1d3330u);
        CHECK(rng.next_u32() == 0x83d2f293u);
        CHECK(rng.next_u32() == 0xbfa4784bu);
        CHECK(rng.next_u32() == 0xcbed606eu);
    }

    TEST_CASE("bounded draws stay in range and cover it") {
        Rng rng(7, 1);
        int seen[6] = {};
        for (int i = 0; i < 6000; ++i) {
            const std::uint32_t v = rng.below(6);
            REQUIRE(v < 6);
            ++seen[v];
        }
        for (const int s : seen) {
            CHECK(s > 800);
        }
        for (int i = 0; i < 1000; ++i) {
            const std::int32_t v = rng.range(-3, 3);
            CHECK(v >= -3);
            CHECK(v <= 3);
        }
        CHECK(rng.below(0) == 0);
        CHECK(rng.range(5, 5) == 5);
        CHECK(rng.unit() < Fixed::one());
    }

    TEST_CASE("streams are independent and state can be restored") {
        Rng a(1, 1);
        Rng b(1, 2);
        CHECK(a.next_u32() != b.next_u32());
        Rng c(9, 3);
        (void)c.next_u32();
        Rng d;
        REQUIRE(Rng::restore(c.state(), c.increment(), d));
        CHECK(c.next_u32() == d.next_u32());
        CHECK_FALSE(Rng::restore(1, 2, d));  // Even increment.
    }
}

TEST_SUITE("sim_core") {
    TEST_CASE("entity ids are reused with a new generation") {
        EntityRegistry reg;
        const EntityId a = reg.create();
        const EntityId b = reg.create();
        CHECK(reg.alive(a));
        CHECK(reg.destroy(a));
        CHECK_FALSE(reg.alive(a));
        CHECK_FALSE(reg.destroy(a));
        const EntityId c = reg.create();
        CHECK(c.index == a.index);
        CHECK(c.generation == a.generation + 1);
        CHECK_FALSE(reg.alive(a));  // The stale id does not see the new entity.
        CHECK(reg.alive(b));
        CHECK(reg.alive_count() == 2);
    }

    TEST_CASE("component removal keeps a predictable order") {
        EntityRegistry reg;
        ComponentStore<int> store;
        EntityId ids[4];
        for (int i = 0; i < 4; ++i) {
            ids[i] = reg.create();
            store.add(ids[i], i * 10);
        }
        CHECK(store.remove(ids[1]));
        REQUIRE(store.size() == 3);
        CHECK(store.data()[0] == 0);
        CHECK(store.data()[1] == 30);  // The last one moved into the gap.
        CHECK(store.data()[2] == 20);
        CHECK(store.get(ids[1]) == nullptr);
        CHECK(*store.get(ids[3]) == 30);
    }

    TEST_CASE("commands round-trip and bad ones are rejected") {
        Command c;
        c.type = CommandType::SendWalker;
        c.player = 3;
        c.entity = {12, 4};
        c.position = {f(-100), Fixed::from_ratio(7, 3)};
        BinaryWriter w;
        c.write(w);
        CHECK(w.bytes().size() == 26);
        BinaryReader r(w.bytes());
        Command back;
        REQUIRE(Command::read(r, back));
        CHECK(back == c);

        const auto rejects = [](Command bad) {
            BinaryWriter bw;
            bad.write(bw);
            BinaryReader br(bw.bytes());
            Command out;
            return !Command::read(br, out);
        };
        Command bad = c;
        bad.player = 12;
        CHECK(rejects(bad));
        bad = c;
        bad.position.x = f(20000);
        CHECK(rejects(bad));
        bad = c;
        bad.type = CommandType::SpawnWalkers;
        bad.count = 0;
        CHECK(rejects(bad));
        bad.count = 65;
        CHECK(rejects(bad));
        bad = c;
        bad.entity = {};
        CHECK(rejects(bad));
        BinaryWriter weird;
        weird.u8(99);
        BinaryReader wr(weird.bytes());
        Command out;
        CHECK_FALSE(Command::read(wr, out));
    }

    TEST_CASE("the same game gives the same hashes every time") {
        const Simulation a = run(2026, kScenarioTicks);
        const Simulation b = run(2026, kScenarioTicks);
        CHECK(a.checkpoints().size() == kScenarioTicks / Simulation::kCheckpointInterval);
        CHECK(a.checkpoints() == b.checkpoints());
        CHECK(a.world().walkers().size() > 100);
        CHECK(a.world().rejected_commands() >= 1);  // At least the double removal.
        CHECK(a.world().rejected_commands() == b.world().rejected_commands());
        const Simulation other = run(2027, kScenarioTicks);
        CHECK(other.last_hash() != a.last_hash());
    }

    TEST_CASE("twelve simulations in one process stay identical") {
        std::vector<Simulation> sims;
        for (int i = 0; i < 12; ++i) {
            sims.emplace_back(99);
            schedule_from(sims.back(), 0);
        }
        for (std::uint64_t t = 0; t < 600; ++t) {
            for (Simulation& s : sims) {
                s.step();
            }
            if (t % 50 == 0) {
                for (const Simulation& s : sims) {
                    REQUIRE(s.world().hash() == sims.front().world().hash());
                }
            }
        }
        for (const Simulation& s : sims) {
            CHECK(s.checkpoints() == sims.front().checkpoints());
        }
    }

    TEST_CASE("saving, loading and continuing changes nothing") {
        const Simulation straight = run(2026, kScenarioTicks);

        Simulation first = run(2026, 700);
        const std::vector<std::uint8_t> snapshot = first.world().snapshot();
        Simulation resumed(0);  // Seed is irrelevant: the snapshot has the state.
        REQUIRE(resumed.restore(snapshot));
        CHECK(resumed.tick() == 700);
        schedule_from(resumed, 700);
        while (resumed.tick() < kScenarioTicks) {
            resumed.step();
        }
        CHECK(resumed.last_hash() == straight.last_hash());
        CHECK(resumed.world().hash() == straight.world().hash());
    }

    TEST_CASE("the scenario hash is the same on every build") {
        const Simulation sim = run(2026, kScenarioTicks);
        MESSAGE("scenario hash: " << sim.last_hash());
        CHECK(sim.last_hash() == kGoldenHash);
    }

    TEST_CASE("damaged snapshots are rejected and leave the world alone") {
        const Simulation sim = run(5, 300);
        std::vector<std::uint8_t> snap = sim.world().snapshot();
        World world(1);
        world.step();
        const std::uint64_t before = world.hash();

        std::vector<std::uint8_t> truncated(snap.begin(), snap.end() - 3);
        CHECK_FALSE(world.restore(truncated));
        std::vector<std::uint8_t> extra = snap;
        extra.push_back(0);
        CHECK_FALSE(world.restore(extra));
        std::vector<std::uint8_t> garbage(500, 0xEE);
        CHECK_FALSE(world.restore(garbage));
        std::vector<std::uint8_t> wrong_rules = snap;
        wrong_rules[4] ^= 0xFF;  // The rules version.
        CHECK_FALSE(world.restore(wrong_rules));
        CHECK(world.hash() == before);
        CHECK(world.restore(snap));
        CHECK(world.hash() == sim.world().hash());
    }
}

TEST_SUITE("sim_replay") {
    TEST_CASE("a recorded game replays exactly, through a file") {
        const Simulation sim = run(31, 900);
        const Replay replay = sim.recording();
        CHECK(replay.commands.size() == 9);  // Script commands before tick 900.
        const ReplayCheck check = verify_replay(replay);
        CHECK_MESSAGE(check.ok, check.error);

        test::TempDir dir;
        REQUIRE(save_replay_file(dir / "game.screplay", replay));
        Replay loaded;
        std::string error;
        REQUIRE_MESSAGE(load_replay_file(dir / "game.screplay", loaded, error), error);
        CHECK(loaded == replay);
        CHECK(verify_replay(loaded).ok);
    }

    TEST_CASE("a changed command is caught at the next checkpoint") {
        Replay replay = run(31, 900).recording();
        replay.commands[3].command.position.x = f(-300);  // The walker sent at tick 100 goes elsewhere.
        const ReplayCheck check = verify_replay(replay);
        CHECK_FALSE(check.ok);
        CHECK(check.mismatch_tick == 110);
    }

    TEST_CASE("damaged or foreign replay files are rejected") {
        const Replay replay = run(31, 300).recording();
        std::vector<std::uint8_t> bytes = encode_replay(replay);
        Replay out;
        std::string error;
        CHECK(decode_replay(bytes, out, error));

        std::vector<std::uint8_t> flipped = bytes;
        flipped[30] ^= 1;
        CHECK_FALSE(decode_replay(flipped, out, error));
        CHECK(error.find("checksum") != std::string::npos);

        std::vector<std::uint8_t> truncated(bytes.begin(), bytes.begin() + 20);
        CHECK_FALSE(decode_replay(truncated, out, error));

        Replay other_rules = replay;
        other_rules.rules_version = kRulesVersion + 1;
        CHECK_FALSE(verify_replay(other_rules).ok);

        test::TempDir dir;
        test::write_text(dir / "notes.txt", "hello, this is not a replay at all");
        CHECK_FALSE(load_replay_file(dir / "notes.txt", out, error));
        CHECK_FALSE(load_replay_file(dir / "missing.screplay", out, error));
    }
}

TEST_SUITE("sim_rules") {
    TEST_CASE("the simulation code avoids what breaks determinism") {
        // docs/DETERMINISMO.md: no floating point, no unordered containers,
        // no clocks, files or standard random numbers inside src/sim.
        const std::regex forbidden(
            R"(\b(float|double|long double|unordered_map|unordered_set|rand|srand|random_device|mt19937|chrono|time_t|fopen|ifstream|ofstream|getenv)\b|<random>|<chrono>|<thread>)");
        const std::regex line_comment(R"(//.*)");
        int files = 0;
        for (const auto& entry : std::filesystem::directory_iterator(std::filesystem::path(SC_SOURCE_DIR) / "src" / "sim")) {
            const auto ext = entry.path().extension();
            if (ext != ".h" && ext != ".cpp" && ext != ".inc") {
                continue;
            }
            ++files;
            const std::string code = std::regex_replace(test::read_text(entry.path()), line_comment, "");
            std::smatch m;
            CHECK_MESSAGE(!std::regex_search(code, m, forbidden),
                          entry.path().filename().string() << " uses '" << (m.empty() ? "" : m.str()) << "'");
        }
        CHECK(files >= 10);
    }
}
