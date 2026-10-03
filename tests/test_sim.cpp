#include <doctest.h>

#include <cmath>
#include <filesystem>
#include <ostream>
#include <regex>
#include <string>

#include "sim/command.h"
#include "sim/entity.h"
#include "sim/fixed.h"
#include "sim/noise.h"
#include "sim/rng.h"
#include "sim/serialize.h"
#include "test_util.h"

using namespace sc;
using namespace sc::sim;

namespace {

Fixed f(int v) {
    return Fixed::from_int(v);
}

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
        // The floor around every kind of square, and at random.
        const auto exact = [](std::uint64_t v) {
            const std::uint64_t r = isqrt(v);
            return r * r <= v && (r == 4294967295ull || (r + 1) * (r + 1) > v);
        };
        bool all = true;
        for (std::uint64_t r = 1; r < (1ull << 32); r = r * 3 / 2 + 1) {
            all = all && exact(r * r - 1) && exact(r * r) && (r == 4294967295ull || exact(r * r + 1));
        }
        std::uint64_t x = 12345;
        for (int i = 0; i < 100000; ++i) {
            x = mix64(x);
            all = all && exact(x) && exact(x >> (i % 64));
        }
        CHECK(all);
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
        c.type = CommandType::RemoveBuilding;
        c.player = 3;
        c.entity = {12, 4};
        c.position = {f(-100), Fixed::from_ratio(7, 3)};
        BinaryWriter w;
        c.write(w);
        CHECK(w.bytes().size() == 32);
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
        bad.type = CommandType::DevGrant;
        bad.value = 0;
        CHECK(rejects(bad));
        bad.value = kMaxDevGrant + 1;
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
