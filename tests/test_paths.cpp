#include <doctest.h>

#include "platform/paths.h"
#include "test_util.h"

using namespace sc;

TEST_SUITE("paths") {
    TEST_CASE("without the portable marker the per-user folder is used") {
        test::TempDir install;
        test::TempDir user;
        DataPaths p = choose_data_paths(install.path(), user.path());
        CHECK_FALSE(p.portable);
        CHECK(p.user_dir == user.path());
        CHECK(p.game_data_dir() == install.path() / "data");
        REQUIRE(prepare_data_paths(p, user.path()));
        CHECK(std::filesystem::is_directory(user / "logs"));
        CHECK(std::filesystem::is_directory(user / "saves"));
        CHECK(std::filesystem::is_directory(user / "mods"));
        CHECK(p.settings_file() == user.path() / "settings.json");
    }

    TEST_CASE("portable.txt keeps everything next to the executable") {
        test::TempDir install;
        test::TempDir user;
        test::write_text(install / kPortableMarker, "");
        DataPaths p = choose_data_paths(install.path(), user.path());
        CHECK(p.portable);
        CHECK(p.user_dir == install.path() / "userdata");
        REQUIRE(prepare_data_paths(p, user.path()));
        CHECK(std::filesystem::is_directory(install / "userdata" / "logs"));
        CHECK(user.count_entries() == 0);
    }

    TEST_CASE("a folder named portable.txt does not turn on portable mode") {
        test::TempDir install;
        test::TempDir user;
        std::filesystem::create_directory(install / kPortableMarker);
        CHECK_FALSE(choose_data_paths(install.path(), user.path()).portable);
    }

    TEST_CASE("an unusable portable folder falls back to the per-user folder") {
        test::TempDir install;
        test::TempDir user;
        test::write_text(install / kPortableMarker, "");
        // A file where the userdata folder should go blocks its creation.
        test::write_text(install / "userdata", "not a folder");
        DataPaths p = choose_data_paths(install.path(), user.path());
        REQUIRE(prepare_data_paths(p, user.path()));
        CHECK_FALSE(p.portable);
        CHECK(p.user_dir == user.path());
    }
}
