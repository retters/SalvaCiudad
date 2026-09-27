#include <doctest.h>

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

    TEST_CASE("widgets react to the mouse") {
        auto font = load_ui_font();
        GlyphAtlas atlas(512);
        TextRenderer text(atlas);
        text.set_font(FontRole::Regular, font.get());
        Context ctx(text);
        const Rect r{10, 10, 100, 30};

        Input in;
        in.mouse_x = 20;
        in.mouse_y = 20;
        in.mouse_down = true;
        in.mouse_pressed = true;
        ctx.begin_frame(in, 800, 600, 1.0f, 0, 0, 0);
        CHECK_FALSE(ctx.button(ctx.id("b"), r, "OK"));
        ctx.end_frame();

        in.mouse_down = false;
        in.mouse_pressed = false;
        in.mouse_released = true;
        ctx.begin_frame(in, 800, 600, 1.0f, 1, 0, 0);
        CHECK(ctx.button(ctx.id("b"), r, "OK"));
        ctx.end_frame();

        // Blocked input (a dialog is open) ignores the click.
        in.mouse_down = true;
        in.mouse_pressed = true;
        in.mouse_released = false;
        ctx.begin_frame(in, 800, 600, 1.0f, 2, 0, 0);
        ctx.set_input_blocked(true);
        CHECK_FALSE(ctx.button(ctx.id("b"), r, "OK"));
        ctx.end_frame();

        // Releasing outside the button cancels the click.
        in = Input{};
        in.mouse_x = 20;
        in.mouse_y = 20;
        in.mouse_down = true;
        in.mouse_pressed = true;
        ctx.begin_frame(in, 800, 600, 1.0f, 3, 0, 0);
        (void)ctx.button(ctx.id("b"), r, "OK");
        ctx.end_frame();
        in.mouse_x = 300;
        in.mouse_down = false;
        in.mouse_pressed = false;
        in.mouse_released = true;
        ctx.begin_frame(in, 800, 600, 1.0f, 4, 0, 0);
        CHECK_FALSE(ctx.button(ctx.id("b"), r, "OK"));
        ctx.end_frame();
    }

    TEST_CASE("sliders follow the mouse in steps") {
        auto font = load_ui_font();
        GlyphAtlas atlas(512);
        TextRenderer text(atlas);
        text.set_font(FontRole::Regular, font.get());
        Context ctx(text);
        Input in;
        in.mouse_x = 60;  // 50 % of a 100 px slider starting at 10.
        in.mouse_y = 20;
        in.mouse_down = true;
        in.mouse_pressed = true;
        ctx.begin_frame(in, 800, 600, 1.0f, 0, 0, 0);
        int v = 0;
        CHECK(ctx.slider(ctx.id("s"), {10, 10, 100, 30}, v, 0, 100, 5, [](int x) { return std::to_string(x); }));
        CHECK(v == 50);
        ctx.end_frame();
    }
}

TEST_SUITE("ui") {
    TEST_CASE("tooltips appear after the delay and only while hovering") {
        auto font = load_ui_font();
        GlyphAtlas atlas(512);
        TextRenderer text(atlas);
        text.set_font(FontRole::Regular, font.get());
        Context ctx(text);
        ctx.set_tooltips(true, 500);
        const Rect r{10, 10, 100, 30};
        Input in;
        in.mouse_x = 20;
        in.mouse_y = 20;

        const auto frame = [&](std::uint64_t ms) {
            ctx.begin_frame(in, 800, 600, 1.0f, ms * 1'000'000ull, 0, 0);
            (void)ctx.button(ctx.id("b"), r, "OK", "Help text");
            const std::size_t before = ctx.draw().vertices().size();
            ctx.end_frame();
            return ctx.draw().vertices().size() > before;
        };
        CHECK_FALSE(frame(0));
        CHECK_FALSE(frame(400));
        CHECK(frame(600));
        in.mouse_x = 500;  // Leaves the button.
        CHECK_FALSE(frame(700));
        ctx.set_tooltips(false, 0);
        in.mouse_x = 20;
        CHECK_FALSE(frame(800));
        CHECK_FALSE(frame(5000));
    }
}
