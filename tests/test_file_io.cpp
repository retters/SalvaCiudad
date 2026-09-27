#include <doctest.h>

#include "core/file_io.h"
#include "core/text.h"
#include "test_util.h"

using namespace sc;

TEST_SUITE("file_io") {
    TEST_CASE("reading a missing file reports NotFound") {
        test::TempDir dir;
        const auto r = fs::read_file(dir / "missing.json", 1024);
        CHECK(r.error == fs::IoError::NotFound);
        CHECK(r.data.empty());
    }

    TEST_CASE("reading a folder is not a file") {
        test::TempDir dir;
        CHECK(fs::read_file(dir.path(), 1024).error == fs::IoError::OpenFailed);
    }

    TEST_CASE("the size limit is enforced before reading") {
        test::TempDir dir;
        test::write_text(dir / "big.txt", std::string(2000, 'x'));
        CHECK(fs::read_file(dir / "big.txt", 1999).error == fs::IoError::TooLarge);
        const auto ok = fs::read_file(dir / "big.txt", 2000);
        CHECK(ok.error == fs::IoError::None);
        CHECK(ok.data.size() == 2000);
    }

    TEST_CASE("an empty file reads as empty") {
        test::TempDir dir;
        test::write_text(dir / "empty.txt", "");
        const auto r = fs::read_file(dir / "empty.txt", 10);
        CHECK(r.error == fs::IoError::None);
        CHECK(r.data.empty());
    }

    TEST_CASE("atomic write creates and replaces, leaving no temporary files") {
        test::TempDir dir;
        const auto file = dir / "data.json";
        CHECK(fs::write_file_atomic(file, "first") == fs::IoError::None);
        CHECK(test::read_text(file) == "first");
        CHECK(fs::write_file_atomic(file, "second, longer") == fs::IoError::None);
        CHECK(test::read_text(file) == "second, longer");
        CHECK(dir.count_entries() == 1);
    }

    TEST_CASE("a failed verification keeps the original file") {
        test::TempDir dir;
        const auto file = dir / "data.json";
        test::write_text(file, "good");
        const auto err = fs::write_file_atomic(file, "bad", [](std::string_view) { return false; });
        CHECK(err == fs::IoError::VerifyFailed);
        CHECK(test::read_text(file) == "good");
        CHECK(dir.count_entries() == 1);
    }

    TEST_CASE("writing into a missing folder fails without side effects") {
        test::TempDir dir;
        const auto file = dir / "no-such-folder" / "data.json";
        CHECK(fs::write_file_atomic(file, "x") == fs::IoError::OpenFailed);
        CHECK(dir.count_entries() == 0);
    }

    TEST_CASE("non-ASCII file names work") {
        test::TempDir dir;
        const auto file = dir.path() / text::path_from_utf8("configuración ñ 城市.json");
        CHECK(fs::write_file_atomic(file, "ñ") == fs::IoError::None);
        CHECK(test::read_text(file) == "ñ");
    }

    TEST_CASE("quarantine renames and never deletes") {
        test::TempDir dir;
        const auto file = dir / "settings.json";
        test::write_text(file, "{broken");
        const auto first = fs::quarantine_file(file);
        REQUIRE_FALSE(first.empty());
        CHECK_FALSE(std::filesystem::exists(file));
        CHECK(test::read_text(first) == "{broken");
        CHECK(text::path_to_utf8(first.filename()).starts_with("settings.json.bad-"));

        // A second damaged file in the same second gets a different name.
        test::write_text(file, "{broken again");
        const auto second = fs::quarantine_file(file);
        REQUIRE_FALSE(second.empty());
        CHECK(second != first);
        CHECK(test::read_text(first) == "{broken");
        CHECK(test::read_text(second) == "{broken again");
    }

    TEST_CASE("quarantining a missing file fails") {
        test::TempDir dir;
        CHECK(fs::quarantine_file(dir / "missing.json").empty());
    }
}
