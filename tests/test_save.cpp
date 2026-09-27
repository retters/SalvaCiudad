#include <doctest.h>

#include <memory>
#include <optional>

#include "game/game_hud.h"
#include "game/game_session.h"
#include "game/save_file.h"
#include "sim/worldgen.h"
#include "test_util.h"

using namespace sc;

namespace {

std::shared_ptr<const sim::Content> content() {
    return std::shared_ptr<const sim::Content>(std::shared_ptr<const sim::Content>{}, &sc::test::core_content());
}

sim::MapData small_map(std::uint64_t seed) {
    sim::MapSettings s;
    s.seed = seed;
    s.size = sim::MapSize::Small;
    std::optional<sim::MapData> m = sim::generate_map(s, *content());
    REQUIRE(m.has_value());
    return std::move(*m);
}

save::SaveData sample() {
    save::SaveData d;
    d.header.name = "Año 3, 40 habitantes";
    d.header.game_version = "0.8.0";
    d.header.saved_at = "2026-09-27T10:11:12";
    d.header.players = 1;
    d.header.rules_version = 8;
    d.header.content_hash = 0xFEDCBA9876543210ull;
    d.header.seed = 42;
    d.header.tick = 123456;
    d.header.population = 40;
    d.header.mods = {{"core", "1.0.0", "00000000000000ff"}};
    d.put("GAME", {1, 2, 3, 4, 5});
    d.put("XTRA", {9, 9});
    return d;
}

}  // namespace

TEST_SUITE("save") {
    TEST_CASE("crc32 matches the standard check value") {
        const char* text = "123456789";
        CHECK(save::crc32({reinterpret_cast<const std::uint8_t*>(text), 9}) == 0xCBF43926u);
    }

    TEST_CASE("a save round-trips, unknown chunks included") {
        const save::SaveData d = sample();
        const std::vector<std::uint8_t> bytes = save::encode(d);
        save::SaveData back;
        REQUIRE(save::decode(bytes, back) == save::LoadError::None);
        CHECK(back.header == d.header);
        CHECK(back.chunks == d.chunks);
        // The header alone, for the load list.
        save::SaveData head;
        REQUIRE(save::decode(bytes, head, true) == save::LoadError::None);
        CHECK(head.header == d.header);
        CHECK(head.chunks.empty());
    }

    TEST_CASE("broken files are rejected") {
        const std::vector<std::uint8_t> good = save::encode(sample());
        save::SaveData out;
        CHECK(save::decode({}, out) == save::LoadError::NotASave);
        std::vector<std::uint8_t> bad = good;
        bad[0] = 'X';
        CHECK(save::decode(bad, out) == save::LoadError::NotASave);
        // A flipped byte in a chunk fails its CRC.
        bad = good;
        bad[bad.size() - 3] ^= 0x40;
        CHECK(save::decode(bad, out) == save::LoadError::Corrupt);
        // Cut short anywhere.
        for (std::size_t n = 0; n < good.size(); n += 7) {
            CHECK(save::decode(std::span(good.data(), n), out) != save::LoadError::None);
        }
        // Trailing bytes.
        bad = good;
        bad.push_back(0);
        CHECK(save::decode(bad, out) == save::LoadError::Corrupt);
        // A newer schema is told apart from damage.
        bad = good;
        bad[8] = 99;
        CHECK(save::decode(bad, out) == save::LoadError::NewerSchema);
    }

    TEST_CASE("files are written atomically and listed newest first") {
        sc::test::TempDir dir;
        save::SaveData a = sample();
        a.header.saved_at = "2026-01-01T00:00:00";
        save::SaveData b = sample();
        b.header.saved_at = "2026-05-01T00:00:00";
        b.header.name = "b";
        REQUIRE(save::write_file(dir / "a.scsave", a));
        REQUIRE(save::write_file(dir / "b.scsave", b));
        sc::test::write_text(dir / "junk.scsave", "not a save");
        sc::test::write_text(dir / "other.txt", "ignored");
        const std::vector<save::Entry> list = save::list(dir.path());
        REQUIRE(list.size() == 3);
        CHECK(list[0].header.name == "b");
        CHECK(list[0].readable);
        CHECK(list[1].header.name == "Año 3, 40 habitantes");
        CHECK_FALSE(list[2].readable);
        CHECK(list[2].header.name == "junk");
    }

    TEST_CASE("file names from typed names are safe") {
        CHECK(save::file_stem("Mi pueblo 2") == "Mi pueblo 2");
        CHECK(save::file_stem("../../evil") == "______evil");
        CHECK(save::file_stem("a:b*c?") == "a_b_c_");
        CHECK(save::file_stem("") == "save");
        CHECK(save::file_stem("  .") == "  _");
    }

    TEST_CASE("a game session saves and loads to the same hash") {
        GameSession session(content(), small_map(31), 5);
        sim::Command c;
        c.type = sim::CommandType::DevGrant;
        c.def = content()->find_resource("core:log");
        c.value = 50;
        session.issue(c);
        for (int i = 0; i < 700; ++i) {
            session.step();
        }
        mods::ModLibrary none;
        const save::SaveData data = session.make_save("test", none);
        CHECK(data.header.tick == 700);
        CHECK(data.header.population == 12);
        // Through the file format and back.
        save::SaveData back;
        REQUIRE(save::decode(save::encode(data), back) == save::LoadError::None);
        std::unique_ptr<GameSession> loaded;
        REQUIRE(GameSession::load(back, content(), loaded) == GameSession::LoadResult::Ok);
        CHECK(loaded->game().hash() == session.game().hash());
        CHECK(loaded->game().stored(0)[c.def] == session.game().stored(0)[c.def]);

        // Other mods or another version are refused with a reason.
        auto other = std::make_shared<sim::Content>(sc::test::core_content());
        other->hash ^= 1;
        CHECK(GameSession::load(back, other, loaded) == GameSession::LoadResult::OtherMods);
        save::SaveData old = back;
        old.header.rules_version = 1;
        CHECK(GameSession::load(old, content(), loaded) == GameSession::LoadResult::OtherVersion);
        save::SaveData empty = back;
        empty.chunks.clear();
        CHECK(GameSession::load(empty, content(), loaded) == GameSession::LoadResult::Damaged);
    }

    TEST_CASE("dates and task texts") {
        CHECK(game_date(0).year == 1);
        CHECK(game_date(0).month == 1);
        CHECK(game_date(0).day == 1);
        const GameDate d = game_date(sim::kTicksPerYear + 2 * sim::kTicksPerMonth + 3 * sim::kTicksPerDay + 99);
        CHECK(d.year == 2);
        CHECK(d.month == 3);
        CHECK(d.day == 4);
        // Every task has a text in the base language.
        const std::string en = sc::test::read_text(std::filesystem::path(SC_SOURCE_DIR) / "data/lang/en.json");
        for (int t = 0; t < static_cast<int>(sim::Task::Count); ++t) {
            const std::string key = std::string("\"") + task_text_key(static_cast<sim::Task>(t)) + "\"";
            CHECK_MESSAGE(en.find(key) != std::string::npos, key);
        }
    }
}
