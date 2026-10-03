#include <doctest.h>

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <format>
#include <memory>
#include <optional>

#include <stb_image.h>

#include "core/file_io.h"
#include "core/png.h"
#include "game/map_report.h"
#include "game/map_scene.h"
#include "sim/worldgen.h"
#include "test_util.h"

using namespace sc;

namespace {

sim::MapData small_map(std::uint64_t seed) {
    sim::MapSettings s;
    s.seed = seed;
    s.size = sim::MapSize::Small;
    s.players = 2;
    s.sea = sim::Sea::Always;
    std::optional<sim::MapData> m = sim::generate_map(s, sc::test::core_content());
    REQUIRE(m.has_value());
    return std::move(*m);
}

report::Report sample_report(const sim::MapData& map) {
    report::Report r;
    r.created_at = "2026-09-29T15:32:01";
    r.game_version = "0.20.0";
    r.build_id = "abc123";
    r.content_hash = 0x0123456789abcdefull;
    r.mods = {"core 1.0.0"};
    r.map = map.settings;
    r.generator_version = map.generator_version;
    r.map_checksum = map.checksum();
    r.view.mode = CameraMode::ThirdPerson;
    r.view.target = {100.5f, 21.25f, 200.75f};
    r.view.yaw = 1.25f;
    r.view.pitch = 0.5f;
    r.view.distance = 42.0f;
    r.view.width = 1280;
    r.view.height = 720;
    r.view.season = sim::Season::Winter;
    r.view.snow = 0.5f;
    r.cursor = report::Cell{100, 200};
    report::Stroke st;
    st.screen = {{10.0f, 20.0f}, {30.0f, 40.0f}};
    st.cells = {{100, 200}, {101, 200}, {101, 201}};
    r.strokes.push_back(st);
    return r;
}

// A scratch folder that goes away with the test.
struct TempDir {
    std::filesystem::path path;
    explicit TempDir(const char* name) {
        path = std::filesystem::temp_directory_path() / "salvaciudad_tests" / name;
        std::error_code ec;
        std::filesystem::remove_all(path, ec);
        std::filesystem::create_directories(path);
    }
    ~TempDir() {
        std::error_code ec;
        std::filesystem::remove_all(path, ec);
    }
};

}  // namespace

TEST_SUITE("map_report") {
    TEST_CASE("PNG files read back as written") {
        // Wide enough to need several stored blocks.
        const std::uint32_t w = 300;
        const std::uint32_t h = 100;
        std::vector<std::uint8_t> rgb(static_cast<std::size_t>(w) * h * 3);
        for (std::size_t i = 0; i < rgb.size(); ++i) {
            rgb[i] = static_cast<std::uint8_t>(i * 7 + i / 13);
        }
        const std::string file = png::encode_rgb(rgb, w, h);
        REQUIRE_FALSE(file.empty());
        int x = 0, y = 0, comp = 0;
        stbi_uc* back = stbi_load_from_memory(reinterpret_cast<const stbi_uc*>(file.data()), static_cast<int>(file.size()),
                                              &x, &y, &comp, 3);
        REQUIRE(back != nullptr);
        CHECK(x == static_cast<int>(w));
        CHECK(y == static_cast<int>(h));
        CHECK(std::equal(rgb.begin(), rgb.end(), back));
        stbi_image_free(back);
        CHECK(png::encode_rgb(rgb, w, h + 1).empty());
        CHECK(png::encode_rgb({}, 0, 0).empty());
    }

    TEST_CASE("a report reads back what `--reporte` needs") {
        const sim::MapData map = small_map(77);
        const report::Report r = sample_report(map);
        TerrainNames names;
        const std::string text = report::to_json(r, map, sc::test::core_content(), names);
        REQUIRE_FALSE(text.empty());
        CHECK(text.find("\"landforms\"") != std::string::npos);
        report::Replay back;
        std::string error;
        REQUIRE(report::parse_replay(text, &sc::test::core_content(), back, error));
        CHECK(back.map == map.settings);
        CHECK(back.generator_version == map.generator_version);
        CHECK(back.content_hash == r.content_hash);
        CHECK(back.build_id == r.build_id);
        CHECK(back.view.mode == CameraMode::ThirdPerson);
        CHECK(back.view.target.x == doctest::Approx(100.5));
        CHECK(back.view.target.z == doctest::Approx(200.75));
        CHECK(back.view.yaw == doctest::Approx(1.25));
        CHECK(back.view.distance == doctest::Approx(42.0));
        CHECK(back.view.width == 1280);
        CHECK(back.view.season == sim::Season::Winter);
        CHECK(back.view.snow == doctest::Approx(0.5));
        // Without the mods loaded yet, the rest still reads.
        report::Replay early;
        CHECK(report::parse_replay(text, nullptr, early, error));
        CHECK(early.view.height == 720);
    }

    TEST_CASE("broken or tampered reports are refused") {
        const sim::MapData map = small_map(78);
        TerrainNames names;
        const std::string good = report::to_json(sample_report(map), map, sc::test::core_content(), names);
        const auto refused = [&](std::string text) {
            report::Replay out;
            std::string error;
            const bool ok = report::parse_replay(text, &sc::test::core_content(), out, error);
            CHECK_FALSE(error.empty());
            return !ok;
        };
        const auto changed = [&](std::string_view from, std::string_view to) {
            std::string t = good;
            const std::size_t at = t.find(from);
            REQUIRE(at != std::string::npos);
            t.replace(at, from.size(), to);
            return t;
        };
        CHECK(refused(""));
        CHECK(refused("[1, 2]"));
        CHECK(refused("{\"schemaVersion\": 1}"));
        CHECK(refused(good.substr(0, good.size() / 2)));
        CHECK(refused(changed("\"schemaVersion\": 1", "\"schemaVersion\": 2")));
        CHECK(refused(changed("\"size\": \"small\"", "\"size\": \"tiny\"")));
        CHECK(refused(changed("\"camera\": \"thirdPerson\"", "\"camera\": \"orbit\"")));
        CHECK(refused(changed("\"mapType\": \"land\"", "\"mapType\": \"evil:x\"")));
        CHECK(refused(changed("\"biomes\": []", "\"biomes\": [\"evil:swamp\"]")));
        CHECK(refused(changed("\"temperature\": 100", "\"temperature\": 900")));
        CHECK(refused(changed("\"width\": 1280", "\"width\": 99999")));
        CHECK(refused(changed("\"players\": 2", "\"players\": 40")));
        CHECK(refused(changed("\"seed\": \"78\"", "\"seed\": \"78; del *\"")));
        CHECK(refused(changed("\"seed\": \"78\"", "\"seed\": 78")));
        CHECK(refused(changed("\"contentHash\": \"0123456789abcdef\"", "\"contentHash\": \"xyz\"")));
        CHECK(refused(std::string(report::kMaxFileBytes + 1, ' ')));
    }

    TEST_CASE("the cells under a stroke follow the ground under each point") {
        // A camera looking straight down: pixel (x, y) is cell (x / 4, y / 4).
        const auto hit = [](float x, float y) -> std::optional<math::Vec3> {
            if (x < 0.0f || y < 0.0f || x >= 400.0f) {
                return std::nullopt;  // Off the map.
            }
            return math::Vec3{x / 4.0f, 20.0f, y / 4.0f};
        };
        report::Stroke line;
        line.screen = {{0.0f, 0.0f}, {40.0f, 0.0f}};
        const std::vector<report::Cell> cells = report::cells_under(line, hit);
        REQUIRE(cells.size() == 11);
        for (std::int32_t i = 0; i <= 10; ++i) {
            CHECK(cells[static_cast<std::size_t>(i)] == report::Cell{i, 0});
        }
        report::Stroke dot;
        dot.screen = {{81.0f, 9.0f}};
        CHECK(report::cells_under(dot, hit) == std::vector<report::Cell>{{20, 2}});
        report::Stroke off;
        off.screen = {{500.0f, 0.0f}, {600.0f, 0.0f}};
        CHECK(report::cells_under(off, hit).empty());
    }

    TEST_CASE("a stroke that comes back to its start surrounds an area") {
        const auto hit = [](float x, float y) -> std::optional<math::Vec3> { return math::Vec3{x / 4.0f, 20.0f, y / 4.0f}; };
        // A square outline, 40 pixels a side, ending near its start.
        report::Stroke square;
        for (int i = 0; i <= 40; i += 4) square.screen.push_back({static_cast<float>(i), 0.0f});
        for (int i = 0; i <= 40; i += 4) square.screen.push_back({40.0f, static_cast<float>(i)});
        for (int i = 40; i >= 0; i -= 4) square.screen.push_back({static_cast<float>(i), 40.0f});
        for (int i = 40; i >= 8; i -= 4) square.screen.push_back({0.0f, static_cast<float>(i)});
        CHECK(report::closes(square));
        const std::vector<report::Cell> cells = report::cells_under(square, hit);
        CHECK(std::binary_search(cells.begin(), cells.end(), report::Cell{5, 5}));
        CHECK(cells.size() >= 100);  // All of the 11 x 11 cells, near enough.
        // An open line does not.
        report::Stroke line;
        for (int i = 0; i <= 80; i += 4) line.screen.push_back({static_cast<float>(i), static_cast<float>(i % 8)});
        CHECK_FALSE(report::closes(line));
        const std::vector<report::Cell> along = report::cells_under(line, hit);
        CHECK_FALSE(std::binary_search(along.begin(), along.end(), report::Cell{10, 10}));
        // A wide area is sampled more sparsely, never past the limit.
        report::Stroke wide = square;
        for (auto& pt : wide.screen) {
            pt = {pt[0] * 100.0f, pt[1] * 100.0f};
        }
        CHECK(report::cells_under(wide, hit).size() <= report::kMaxAreaSamples + 4000);
    }

    TEST_CASE("the ground is found from far away") {
        const sim::MapData map = small_map(79);
        // From 5 km up and away, looking down at the middle of the map.
        const math::Vec3 middle{256.0f, 0.0f, 256.0f};
        const math::Vec3 origin{256.0f - 3000.0f, 4000.0f, 256.0f};
        const math::Vec3 dir = math::normalize(middle - origin);
        CHECK_FALSE(ground_hit(map, origin, dir).has_value());  // Past the usual 4 km.
        const std::optional<math::Vec3> hit = ground_hit(map, origin, dir, 8000.0f);
        REQUIRE(hit.has_value());
        // On the ground, a little before the middle (the ground is above 0).
        CHECK(std::abs(hit->y - map_surface_height(map, hit->x, hit->z)) < 0.05f);
        CHECK(hit->x < 256.0f);
        CHECK(hit->x > 150.0f);
        CHECK(std::abs(hit->z - 256.0f) < 1.0f);
    }

    TEST_CASE("strokes are painted over the screenshot") {
        const std::uint32_t w = 50, h = 30;
        std::vector<std::uint8_t> rgb(static_cast<std::size_t>(w) * h * 3, 0);
        report::Stroke st;
        st.screen = {{5.0f, 10.0f}, {45.0f, 10.0f}};
        report::draw_strokes(rgb, w, h, {st}, 4.0f, {200, 10, 20});
        const auto at = [&](std::uint32_t x, std::uint32_t y) { return rgb[(static_cast<std::size_t>(y) * w + x) * 3]; };
        CHECK(at(25, 10) == 200);
        CHECK(at(25, 9) == 200);
        CHECK(at(25, 20) == 0);
        CHECK(at(1, 10) == 0);
        // Strokes past the edges do not write outside the image.
        report::Stroke wild;
        wild.screen = {{-100.0f, -100.0f}, {1000.0f, 1000.0f}};
        report::draw_strokes(rgb, w, h, {wild}, 6.0f, {1, 2, 3});
        CHECK(rgb.size() == static_cast<std::size_t>(w) * h * 3);
    }

    TEST_CASE("report folders: names, and only the oldest of ours are deleted") {
        CHECK(report::is_report_name("2026-09-29_153201"));
        CHECK(report::is_report_name("2026-09-29_153201-2"));
        CHECK_FALSE(report::is_report_name("2026-09-29"));
        CHECK_FALSE(report::is_report_name("mis fotos"));
        CHECK_FALSE(report::is_report_name("2026-09-29_153201-"));
        CHECK_FALSE(report::is_report_name("2026-09-29_15320x"));
        CHECK(report::is_report_name(report::folder_name_now()));

        TempDir tmp("reports");
        for (int i = 0; i < 6; ++i) {
            const std::filesystem::path dir = report::create_folder(tmp.path, std::format("2026-09-2{}_120000", i));
            REQUIRE_FALSE(dir.empty());
            REQUIRE(fs::write_file_atomic(dir / "captura.png", "x") == fs::IoError::None);
        }
        // The same name again gets a suffix.
        CHECK(report::create_folder(tmp.path, "2026-09-25_120000").filename() == "2026-09-25_120000-2");
        // Something else in the oldest one: it is kept.
        REQUIRE(fs::write_file_atomic(tmp.path / "2026-09-20_120000" / "notas.txt", "mine") == fs::IoError::None);
        std::filesystem::create_directories(tmp.path / "otra carpeta");
        report::prune(tmp.path, 3);
        CHECK(std::filesystem::exists(tmp.path / "2026-09-20_120000" / "notas.txt"));
        CHECK_FALSE(std::filesystem::exists(tmp.path / "2026-09-21_120000"));
        CHECK_FALSE(std::filesystem::exists(tmp.path / "2026-09-22_120000"));
        CHECK_FALSE(std::filesystem::exists(tmp.path / "2026-09-23_120000"));
        CHECK(std::filesystem::exists(tmp.path / "2026-09-24_120000"));
        CHECK(std::filesystem::exists(tmp.path / "2026-09-25_120000-2"));
        CHECK(std::filesystem::exists(tmp.path / "otra carpeta"));
    }
}
