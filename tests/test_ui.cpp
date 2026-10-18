#include <doctest.h>

#include <filesystem>
#include <fstream>
#include <regex>
#include <sstream>

#include "core/file_io.h"
#include "test_util.h"
#include "ui/context.h"
#include "ui/draw_list.h"
#include "ui/font.h"
#include "ui/font_library.h"
#include "ui/glyph_atlas.h"
#include "ui/text.h"

using namespace sc;
using namespace sc::ui;

namespace {

const std::filesystem::path kFontsDir = std::filesystem::path(SC_SOURCE_DIR) / "data" / "fonts";

std::unique_ptr<Font> load_ui_font() {
    const auto r = fs::read_file(kFontsDir / "ui" / "AlegreyaSans-Regular.ttf", Font::kMaxFileBytes);
    REQUIRE(r.error == fs::IoError::None);
    auto f = std::make_unique<Font>();
    REQUIRE(f->load(std::vector<std::uint8_t>(r.data.begin(), r.data.end())));
    return f;
}

}  // namespace

TEST_SUITE("ui") {
    TEST_CASE("draw list clips and culls") {
        DrawList list;
        list.reset(800, 600, 0.001f, 0.001f);
        list.rect({10, 10, 100, 50}, Color::rgb(0xFF0000));
        CHECK(list.vertices().size() == 4);
        list.push_clip({0, 0, 50, 50});
        CHECK(list.clip() == Rect{0, 0, 50, 50});
        list.rect({100, 100, 10, 10}, Color::rgb(0x00FF00));  // Outside the clip: dropped.
        CHECK(list.vertices().size() == 4);
        list.rect({10, 10, 10, 10}, Color::rgb(0x00FF00));
        list.push_clip({40, 40, 100, 100});
        CHECK(list.clip() == Rect{40, 40, 10, 10});
        list.pop_clip();
        list.pop_clip();
        list.pop_clip();  // Never pops the screen clip.
        CHECK(list.clip() == Rect{0, 0, 800, 600});
        std::uint32_t total = 0;
        for (const DrawCommand& c : list.commands()) {
            total += c.index_count;
        }
        CHECK(total == list.indices().size());
        CHECK(list.indices().size() == 12);
    }

    TEST_CASE("pictures get their own draw commands; lines are two triangles") {
        DrawList list;
        list.reset(800, 600, 0.001f, 0.001f);
        list.rect({10, 10, 100, 50}, Color::rgb(0xFF0000));
        list.picture({200, 200, 64, 64}, 1, 0.0f, 0.0f, 1.0f, 1.0f, Color::rgb(0xFFFFFF));
        list.rect({10, 100, 10, 10}, Color::rgb(0x00FF00));
        list.picture({0, 0, 10, 10}, 0, 0.0f, 0.0f, 1.0f, 1.0f, Color::rgb(0xFFFFFF));  // No image: nothing.
        REQUIRE(list.commands().size() == 3);
        CHECK(list.commands()[0].image == 0);
        CHECK(list.commands()[1].image == 1);
        CHECK(list.commands()[1].index_count == 6);
        CHECK(list.commands()[2].image == 0);
        CHECK(list.vertices()[4].u == 0.0f);
        CHECK(list.vertices()[6].v == 1.0f);
        const std::size_t before = list.indices().size();
        list.line(0, 0, 100, 0, 4.0f, Color::rgb(0xFFFFFF));
        CHECK(list.indices().size() == before + 6);
        CHECK(list.vertices().back().y == doctest::Approx(-2.0f));
        list.line(5, 5, 5, 5, 4.0f, Color::rgb(0xFFFFFF));  // No length: nothing.
        CHECK(list.indices().size() == before + 6);
    }

    TEST_CASE("glyph atlas packs, fills up and clears") {
        GlyphAtlas atlas(64);
        const auto first_dirty = atlas.take_dirty();
        CHECK(first_dirty.w == 64);
        CHECK(atlas.pixels()[0] == 0xFF);  // White block.
        AtlasRegion r;
        REQUIRE(atlas.allocate(10, 10, r));
        CHECK(r.x >= GlyphAtlas::kWhiteSize);
        const std::vector<std::uint8_t> px(100, 7);
        atlas.write(r, px.data(), 10);
        const auto dirty = atlas.take_dirty();
        CHECK(dirty.w == 10);
        CHECK(dirty.h == 10);
        int placed = 1;
        while (atlas.allocate(10, 10, r)) {
            ++placed;
        }
        CHECK(placed > 10);
        CHECK_FALSE(atlas.allocate(100, 5, r));
        const auto gen = atlas.generation();
        atlas.clear();
        CHECK(atlas.generation() == gen + 1);
        CHECK(atlas.allocate(10, 10, r));
    }

    TEST_CASE("fonts load and reject garbage") {
        auto font = load_ui_font();
        CHECK(font->glyph_index('A') != 0);
        CHECK(font->glyph_index(0x00F1) != 0);  // ñ
        CHECK(font->ascent(20) > 0.0f);
        CHECK(font->line_height(20) >= 20.0f);
        Font bad;
        CHECK_FALSE(bad.load({}));
        CHECK_FALSE(bad.load(std::vector<std::uint8_t>(64, 0xAB)));
    }

    TEST_CASE("text measures, wraps and ellipsizes") {
        auto font = load_ui_font();
        GlyphAtlas atlas(512);
        TextRenderer text(atlas);
        text.set_font(FontRole::Regular, font.get());
        const TextStyle st{FontRole::Regular, 20};

        const float w_short = text.measure(st, "Salir");
        const float w_long = text.measure(st, "Crear partida multijugador");
        CHECK(w_short > 0.0f);
        CHECK(w_long > w_short);
        CHECK(text.measure(st, "") == 0.0f);

        const auto lines = text.wrap(st, "Uno dos tres cuatro cinco seis siete ocho", w_long * 0.6f);
        CHECK(lines.size() >= 2);
        for (const auto& line : lines) {
            CHECK(text.measure(st, line) <= w_long * 0.6f);
            CHECK_FALSE(line.ends_with(" "));
        }
        CHECK(text.wrap(st, "a\nb", 1000.0f).size() == 2);
        // A single word wider than the line is split, never lost.
        const auto split = text.wrap(st, "Supercalifragilístico", w_short);
        std::string joined;
        for (const auto& l : split) {
            joined += l;
        }
        CHECK(split.size() >= 2);
        CHECK(joined == "Supercalifragilístico");

        const std::string cut = text.ellipsize(st, "Crear partida multijugador", w_short * 1.5f);
        CHECK(cut.ends_with("\xE2\x80\xA6"));
        CHECK(text.measure(st, cut) <= w_short * 1.5f);
        CHECK(text.ellipsize(st, "Salir", 1000.0f) == "Salir");

        DrawList list;
        list.reset(800, 600, atlas.white_u(), atlas.white_v());
        const float drawn = text.draw(list, st, 0, 0, "Año", Color::rgb(0xFFFFFF));
        CHECK(drawn > 0.0f);
        CHECK(list.vertices().size() == 12);  // Three glyphs.
    }

    TEST_CASE("glows are smooth Gaussian blurs of the text") {
        // A single dot spreads into a symmetric bell that keeps its total and has no steps.
        AlphaMask dot;
        dot.resize(81, 81);
        dot.at(40, 40) = 1.0f;
        gaussian_blur(dot, 6.0f);
        float total = 0.0f;
        for (const float a : dot.a) {
            total += a;
        }
        CHECK(total == doctest::Approx(1.0f).epsilon(0.001));
        CHECK(dot.at(30, 40) == doctest::Approx(dot.at(50, 40)));
        CHECK(dot.at(40, 30) == doctest::Approx(dot.at(40, 50)));
        // The spread matches the sigma: about 0.6 of the peak one sigma away (exactly e^-0.5).
        CHECK(dot.at(46, 40) / dot.at(40, 40) == doctest::Approx(0.6065f).epsilon(0.08));
        // Falls off steadily outwards, and its slope never jumps (no visible rings).
        for (int x = 41; x < 70; ++x) {
            CHECK(dot.at(x, 40) <= dot.at(x - 1, 40));
            const float curve = dot.at(x - 1, 40) - 2.0f * dot.at(x, 40) + dot.at(x + 1, 40);
            CHECK(std::abs(curve) < dot.at(40, 40) * 0.05f);
        }

        // The text mask lines up with the drawn glyphs.
        auto font = load_ui_font();
        GlyphAtlas atlas(512);
        TextRenderer text(atlas);
        text.set_font(FontRole::Regular, font.get());
        const TextStyle st{FontRole::Regular, 32};
        AlphaMask mask;
        mask.resize(200, 60);
        CHECK(text.rasterize(st, 10.0f, 5.0f, "Salva", mask) == text.measure(st, "Salva"));
        AlphaMask s_mask;
        s_mask.resize(200, 60);
        text.rasterize(st, 10.0f, 5.0f, "S", s_mask);
        DrawList list;
        list.reset(800, 600, atlas.white_u(), atlas.white_v());
        text.draw(list, st, 10.0f, 5.0f, "S", Color::rgb(0xFFFFFF));
        REQUIRE(list.vertices().size() == 4);
        const Vertex& top_left = list.vertices()[0];
        const Vertex& bottom_right = list.vertices()[2];
        int x0 = 1000, y0 = 1000, x1 = -1, y1 = -1;
        for (int y = 0; y < s_mask.h; ++y) {
            for (int x = 0; x < s_mask.w; ++x) {
                if (s_mask.at(x, y) > 0.0f) {
                    x0 = std::min(x0, x);
                    y0 = std::min(y0, y);
                    x1 = std::max(x1, x + 1);
                    y1 = std::max(y1, y + 1);
                }
            }
        }
        CHECK(static_cast<float>(x0) >= top_left.x);
        CHECK(static_cast<float>(y0) >= top_left.y);
        CHECK(static_cast<float>(x1) <= bottom_right.x);
        CHECK(static_cast<float>(y1) <= bottom_right.y);
        CHECK(static_cast<float>(x1 - x0) >= (bottom_right.x - top_left.x) - 2.0f);
        CHECK(static_cast<float>(y1 - y0) >= (bottom_right.y - top_left.y) - 2.0f);

        // Composed glows come out as straight RGBA: the color is kept even where it is faint.
        AlphaMask bell = dot;
        const float peak = dot.at(40, 40);
        for (float& a : bell.a) {
            a /= peak;
        }
        GlowCanvas canvas(81, 81);
        canvas.over(bell, Color::rgb(0xFF8000), 1.0f);
        canvas.faded_line(10, 70, 60, 1, Color::rgb(0x8FB0C8));
        const std::vector<std::uint8_t> rgba = canvas.to_rgba8();
        REQUIRE(rgba.size() == 81u * 81u * 4u);
        const std::size_t near = (40u * 81u + 52u) * 4u;
        CHECK(rgba[near] == 255);
        CHECK(rgba[near + 1] == 128);
        CHECK(rgba[near + 3] > 0);
        const std::size_t mid = (70u * 81u + 40u) * 4u;
        const std::size_t end = (70u * 81u + 10u) * 4u;
        CHECK(rgba[mid + 3] >= 254);
        CHECK(rgba[end + 3] < 10);
        CHECK(rgba[0 + 3] == 0);
    }

    TEST_CASE("the shipped font manifest loads") {
        FontLibrary lib;
        REQUIRE(lib.load(kFontsDir));
        REQUIRE_FALSE(lib.ui_families().empty());
        CHECK(lib.ui_families().front().id == "alegreya-sans");
        CHECK(lib.ui_families().front().bold != nullptr);
        CHECK(lib.logo() != nullptr);
        CHECK(lib.ui_family("unknown")->id == "alegreya-sans");
    }

    TEST_CASE("font manifests with unsafe paths are rejected") {
        test::TempDir dir;
        test::write_text(dir / "fonts.json", R"({"schemaVersion": 1, "fonts": [
            {"id": "a", "name": "A", "role": "ui", "regular": "../outside.ttf"},
            {"id": "b", "name": "B", "role": "ui", "regular": "C:/Windows/Fonts/arial.ttf"},
            {"id": "c", "name": "C", "role": "ui", "regular": "/etc/font.ttf"},
            {"id": "Bad Id", "name": "D", "role": "ui", "regular": "x.ttf"},
            {"id": "e", "name": "E", "role": "ui", "regular": "missing.ttf"}]})");
        FontLibrary lib;
        CHECK_FALSE(lib.load(dir.path()));
        CHECK(lib.ui_families().empty());
    }


    // Phase 127: the old immediate-mode widgets are gone, and ImGui is only
    // for the tools (the developer tools, the debug overlay, the viewer).
    TEST_CASE("no screen uses the old widgets, and ImGui stays in the tools") {
        const std::filesystem::path src = std::filesystem::path(SC_SOURCE_DIR) / "src";
        const std::regex widget(R"((\bctx|\bui_|\bcontext)\s*(\.|->)\s*(button|checkbox|slider|selector|text_field|begin_scroll|end_scroll|panel|label|paragraph|tooltip_area|push_id|typing)\s*\()");
        const std::regex imgui(R"(\bImGui::)");
        const auto tool = [&](const std::filesystem::path& p) {
            const std::string rel = std::filesystem::relative(p, src).generic_string();
            return rel.starts_with("viewer/") || rel == "game/dev_tools.cpp" || rel.starts_with("render/debug_overlay");
        };
        std::size_t files = 0;
        for (const auto& entry : std::filesystem::recursive_directory_iterator(src)) {
            const std::string ext = entry.path().extension().string();
            if (!entry.is_regular_file() || (ext != ".cpp" && ext != ".h")) {
                continue;
            }
            ++files;
            std::ifstream in(entry.path(), std::ios::binary);
            std::stringstream text;
            text << in.rdbuf();
            const std::string code = text.str();
            CHECK_MESSAGE(!std::regex_search(code, widget), entry.path().generic_string());
            if (!tool(entry.path())) {
                CHECK_MESSAGE(!std::regex_search(code, imgui), entry.path().generic_string());
            }
        }
        CHECK(files > 100);
    }
}
