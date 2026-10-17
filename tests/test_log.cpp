#include <doctest.h>

#include <algorithm>

#include "core/log.h"
#include "test_util.h"

using namespace sc;

TEST_SUITE("log") {
    TEST_CASE("writes one line per entry and filters by level") {
        test::TempDir dir;
        log::Options options;
        options.min_level = log::Level::Info;
        REQUIRE(log::open(dir.path(), options));
        log::debug("hidden {}", 1);
        log::info("visible {}", 2);
        log::warn("multi\nline");
        log::close();

        const std::string text = test::read_text(dir / "salvasprosperia.log");
        CHECK(text.find("hidden") == std::string::npos);
        CHECK(text.find("INFO  visible 2") != std::string::npos);
        CHECK(text.find("WARN  multi line") != std::string::npos);
        CHECK(std::count(text.begin(), text.end(), '\n') == 2);
    }

    TEST_CASE("opening rotates the previous log and keeps a limited number") {
        test::TempDir dir;
        log::Options options;
        options.kept_files = 3;
        for (int run = 0; run < 5; ++run) {
            REQUIRE(log::open(dir.path(), options));
            log::info("run {}", run);
            log::close();
        }
        CHECK(test::read_text(dir / "salvasprosperia.log").find("run 4") != std::string::npos);
        CHECK(test::read_text(dir / "salvasprosperia.1.log").find("run 3") != std::string::npos);
        CHECK(test::read_text(dir / "salvasprosperia.2.log").find("run 2") != std::string::npos);
        CHECK_FALSE(std::filesystem::exists(dir / "salvasprosperia.3.log"));
    }

    TEST_CASE("the log rotates when it reaches its size limit") {
        test::TempDir dir;
        log::Options options;
        options.max_file_bytes = 200;
        options.kept_files = 2;
        REQUIRE(log::open(dir.path(), options));
        for (int i = 0; i < 20; ++i) {
            log::info("entry number {}", i);
        }
        log::close();
        const auto size = std::filesystem::file_size(dir / "salvasprosperia.log");
        CHECK(size <= 200);
        CHECK(std::filesystem::exists(dir / "salvasprosperia.1.log"));
        CHECK(test::read_text(dir / "salvasprosperia.log").find("entry number 19") != std::string::npos);
    }
}
