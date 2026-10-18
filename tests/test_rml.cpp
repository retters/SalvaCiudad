// Phases 117 to 119: RmlUi's adapters (texts, files, keys, fonts), documents,
// the effects, with the game's render interface recording without a GPU, and
// the styles.
#include <doctest.h>

#include <cmath>
#include <filesystem>
#include <memory>
#include <optional>
#include <string>

#include <SDL3/SDL_events.h>
#include <SDL3/SDL_keycode.h>
#include <SDL3/SDL_mouse.h>

#include <RmlUi/Core/Context.h>
#include <RmlUi/Core/DataModelHandle.h>
#include <RmlUi/Core/Element.h>
#include <RmlUi/Core/ElementDocument.h>
#include <RmlUi/Core/Dictionary.h>
#include <RmlUi/Core/RenderInterface.h>

#include "game/rml_panels.h"
#include "core/file_io.h"
#include "i18n/translator.h"
#include "render/rml_renderer.h"
#include "test_util.h"
#include "ui/font_library.h"
#include "ui/glyph_atlas.h"
#include "ui/rml/rml_input.h"
#include "ui/rml/rml_style.h"
#include "ui/rml/rml_system.h"
#include "ui/rml/rml_test_window.h"
#include "ui/rml/rml_ui.h"

using namespace sc;

namespace {

const std::filesystem::path kData = std::filesystem::path(SC_SOURCE_DIR) / "data";

// RmlUi is global: one interface for the whole test run, with the game's
// languages (Spanish active), fonts and data/ui.
struct Fixture {
    RmlRenderer render;  // No device: it records and counts.
    ui::GlyphAtlas atlas{1024};
    ui::FontLibrary fonts;
    rml::RmlUi ui;
    rml::TestWindow test_window;
    bool ok = false;

    Fixture() {
        auto& t = i18n::translator();
        const std::string en = test::read_text(kData / "lang" / "en.json");
        REQUIRE(t.load(kData / "lang", en) == 0);
        for (const char* code : {"es", "en"}) {
            REQUIRE(t.add_mod_texts(test::read_text(kData / "mods" / "core" / "lang" / (std::string(code) + ".json")),
                                    code));
        }
        REQUIRE(t.set_language("es"));
        REQUIRE(fonts.load(kData / "fonts"));
        ok = ui.init(render, atlas, fonts, {kData / "ui"}, "alegreya-sans") && test_window.bind(*ui.context());
    }
};

Fixture& fixture() {
    static Fixture f;
    REQUIRE(f.ok);
    return f;
}

Rml::Vector2f center(Rml::Element& e) {
    return e.GetAbsoluteOffset(Rml::BoxArea::Border) + e.GetBox().GetSize(Rml::BoxArea::Border) * 0.5f;
}

SDL_Event mouse_motion(float x, float y) {
    SDL_Event e{};
    e.type = SDL_EVENT_MOUSE_MOTION;
    e.motion.x = x;
    e.motion.y = y;
    return e;
}

SDL_Event mouse_button(bool down) {
    SDL_Event e{};
    e.type = down ? SDL_EVENT_MOUSE_BUTTON_DOWN : SDL_EVENT_MOUSE_BUTTON_UP;
    e.button.button = SDL_BUTTON_LEFT;
    return e;
}

void click(rml::RmlUi& ui, Rml::Element& e) {
    const Rml::Vector2f c = center(e);
    (void)ui.process_event(mouse_motion(c.x, c.y), 1.0f);
    (void)ui.process_event(mouse_button(true), 1.0f);
    (void)ui.process_event(mouse_button(false), 1.0f);
}

}  // namespace

TEST_SUITE("rml") {
    TEST_CASE("@key texts are translated and the rest stays as written") {
        const rml::KeyLookup lookup = [](std::string_view key) -> std::optional<std::string> {
            if (key == "hud.window.pin") {
                return std::string("Fijar");
            }
            if (key == "a.b") {
                return std::string("AB");
            }
            return std::nullopt;
        };
        std::string out;
        CHECK(rml::translate_keys("@hud.window.pin", lookup, out) == 1);
        CHECK(out == "Fijar");
        CHECK(rml::translate_keys("[@a.b] y @a.b.", lookup, out) == 2);
        CHECK(out == "[AB] y AB.");
        CHECK(rml::translate_keys("correo@ejemplo y @sinpunto", lookup, out) == 0);
        CHECK(out == "correo@ejemplo y @sinpunto");
        CHECK(rml::translate_keys("@no.existe", lookup, out) == 0);
        CHECK(out == "@no.existe");
        CHECK(rml::translate_keys("@", lookup, out) == 0);
        CHECK(out == "@");
    }

    TEST_CASE("documents are read only from inside their roots") {
        test::TempDir dir;
        std::filesystem::create_directories(dir / "ui" / "a");
        test::write_text(dir / "ui" / "a" / "b.rml", "<rml/>");
        test::write_text(dir / "secreto.txt", "no");
        const std::vector<std::filesystem::path> roots = {dir / "ui"};
        CHECK(rml::resolve_ui_path(roots, "a/b.rml").has_value());
        CHECK(rml::resolve_ui_path(roots, "a\\b.rml").has_value());
        for (const char* bad : {"../secreto.txt", "a/../../secreto.txt", "/a/b.rml", "\\a\\b.rml", "C:/a/b.rml",
                                "a//b.rml", "a/./b.rml", "", "a/missing.rml", "a"}) {
            CHECK_MESSAGE(!rml::resolve_ui_path(roots, bad).has_value(), bad);
        }
    }

    TEST_CASE("SDL keys, modifiers and buttons map to RmlUi's") {
        CHECK(rml::key_from_sdl(SDLK_A) == Rml::Input::KI_A);
        CHECK(rml::key_from_sdl(SDLK_Z) == Rml::Input::KI_Z);
        CHECK(rml::key_from_sdl(SDLK_7) == Rml::Input::KI_7);
        CHECK(rml::key_from_sdl(SDLK_F12) == Rml::Input::KI_F12);
        CHECK(rml::key_from_sdl(SDLK_KP_0) == Rml::Input::KI_NUMPAD0);
        CHECK(rml::key_from_sdl(SDLK_KP_9) == Rml::Input::KI_NUMPAD9);
        CHECK(rml::key_from_sdl(SDLK_BACKSPACE) == Rml::Input::KI_BACK);
        CHECK(rml::key_from_sdl(SDLK_PAGEDOWN) == Rml::Input::KI_NEXT);
        CHECK(rml::modifiers_from_sdl(SDL_KMOD_LCTRL | SDL_KMOD_RSHIFT) ==
              (Rml::Input::KM_CTRL | Rml::Input::KM_SHIFT));
        CHECK(rml::button_from_sdl(SDL_BUTTON_LEFT) == 0);
        CHECK(rml::button_from_sdl(SDL_BUTTON_RIGHT) == 1);
        CHECK(rml::button_from_sdl(SDL_BUTTON_MIDDLE) == 2);
        CHECK(rml::button_from_sdl(SDL_BUTTON_X1) == -1);
    }

    TEST_CASE("the font engine measures with the game's fonts") {
        Fixture& f = fixture();
        Rml::FontEngineInterface* engine = Rml::GetFontEngineInterface();
        REQUIRE(engine != nullptr);
        const Rml::FontFaceHandle regular = engine->GetFontFaceHandle("ui", Rml::Style::FontStyle::Normal,
                                                                      Rml::Style::FontWeight::Normal, 16);
        const Rml::FontFaceHandle bold =
            engine->GetFontFaceHandle("ui", Rml::Style::FontStyle::Normal, Rml::Style::FontWeight::Bold, 16);
        const Rml::FontFaceHandle unknown = engine->GetFontFaceHandle("Comic", Rml::Style::FontStyle::Normal,
                                                                      Rml::Style::FontWeight::Normal, 16);
        REQUIRE(regular != 0);
        REQUIRE(bold != 0);
        CHECK(bold != regular);
        CHECK(unknown == regular);  // Unknown families fall back to the interface's.
        const Rml::FontMetrics& m = engine->GetFontMetrics(regular);
        CHECK(m.size == 16);
        CHECK(m.ascent > 8.0f);
        CHECK(m.descent > 0.0f);
        CHECK(m.line_spacing >= m.ascent + m.descent);
        const Rml::String lang;
        const Rml::TextShapingContext shaping{lang};
        CHECK(engine->GetStringWidth(regular, "WWWW", shaping) > engine->GetStringWidth(regular, "iiii", shaping));
        CHECK(engine->GetStringWidth(regular, "", shaping) == 0);
        CHECK(engine->GetFontFaceHandle("logo", Rml::Style::FontStyle::Normal, Rml::Style::FontWeight::Normal, 30) != 0);
        CHECK(f.ui.ready());
    }

    TEST_CASE("a data model reacts to a click, and the pointer over a document is the interface's") {
        Fixture& f = fixture();
        Rml::Context& ctx = *f.ui.context();
        int count = 0;
        Rml::DataModelConstructor c = ctx.CreateDataModel("contador");
        REQUIRE(static_cast<bool>(c));
        REQUIRE(c.Bind("count", &count));
        c.BindEventCallback("add", [&count](Rml::DataModelHandle model, Rml::Event&, const Rml::VariantList&) {
            ++count;
            model.DirtyVariable("count");
        });
        Rml::ElementDocument* doc = ctx.LoadDocumentFromMemory(R"(<rml><head><style>
            body { display: block; position: absolute; left: 100px; top: 100px; width: 200px; font-family: ui; font-size: 16px; }
            div { display: block; height: 40px; }
            </style></head>
            <body data-model="contador"><div id="b" data-event-click="add">{{count}}</div><div id="t">@hud.window.pin</div></body></rml>)");
        REQUIRE(doc != nullptr);
        doc->Show();
        f.ui.update(1280, 720, 1.0f);
        Rml::Element* b = doc->GetElementById("b");
        REQUIRE(b != nullptr);
        REQUIRE(doc->GetElementById("t") != nullptr);
        CHECK(doc->GetElementById("t")->GetInnerRML() == "Fijar");
        click(f.ui, *b);
        f.ui.update(1280, 720, 1.0f);
        CHECK(count == 1);
        // Over the document the pointer belongs to the interface; elsewhere, to the game.
        CHECK(f.ui.process_event(mouse_motion(150.0f, 110.0f), 1.0f));
        CHECK(f.ui.wants_mouse());
        CHECK_FALSE(f.ui.process_event(mouse_motion(900.0f, 600.0f), 1.0f));
        CHECK_FALSE(f.ui.wants_mouse());
        f.render.begin_frame(1280, 720);
        f.ui.render();
        CHECK(f.render.draw_count() > 0);
        doc->Close();
        f.ui.update(1280, 720, 1.0f);
        ctx.RemoveDataModel("contador");
    }

    TEST_CASE("the test window loads clean, works and follows the language and the scale") {
        Fixture& f = fixture();
        const int errors = f.ui.system().errors();
        REQUIRE(f.ui.show_document(rml::TestWindow::kDocument, true));
        f.ui.update(1280, 720, 1.0f);
        CHECK(f.ui.system().errors() == errors);
        CHECK(f.ui.document_shown(rml::TestWindow::kDocument));
        Rml::ElementDocument* doc = f.ui.document(rml::TestWindow::kDocument);
        REQUIRE(doc != nullptr);
        std::string text = doc->GetInnerRML();
        CHECK(text.find("Cantero") != std::string::npos);
        CHECK(text.find("@") == std::string::npos);  // Every @key was found.

        // The + and - buttons go through the data model.
        Rml::ElementList steps;
        doc->GetElementsByClassName(steps, "step");
        REQUIRE(steps.size() == 2);
        click(f.ui, *steps[0]);
        f.ui.update(1280, 720, 1.0f);
        CHECK(f.test_window.state().workers == 1);
        click(f.ui, *steps[1]);
        f.ui.update(1280, 720, 1.0f);
        CHECK(f.test_window.state().workers == 2);

        // The scale: twice the density, twice the width.
        const float width = doc->GetBox().GetSize(Rml::BoxArea::Border).x;
        f.ui.update(1280, 720, 2.0f);
        // From 1.5 up the icons come from the 2x sheet: the document reloaded.
        doc = f.ui.document(rml::TestWindow::kDocument);
        REQUIRE(doc != nullptr);
        CHECK(doc->GetBox().GetSize(Rml::BoxArea::Border).x == doctest::Approx(width * 2.0f).epsilon(0.02));

        // Another language reloads the document with its texts.
        REQUIRE(i18n::translator().set_language("en"));
        f.test_window.update();
        f.ui.update(1280, 720, 1.0f);
        doc = f.ui.document(rml::TestWindow::kDocument);
        REQUIRE(doc != nullptr);
        text = doc->GetInnerRML();
        CHECK(text.find("Stonecutter") != std::string::npos);
        CHECK(f.ui.document_shown(rml::TestWindow::kDocument));
        REQUIRE(i18n::translator().set_language("es"));
        f.ui.update(1280, 720, 1.0f);
        CHECK(f.ui.system().errors() == errors);
        REQUIRE(f.ui.show_document(rml::TestWindow::kDocument, false));
    }

    TEST_CASE("the blur plans follow RmlUi's and the engine's blurs") {
        CHECK(rml_fx::blur_plan(0.0f).levels == 0);
        CHECK(rml_fx::blur_plan(1.0f).levels == 0);
        CHECK(rml_fx::blur_plan(1.0f).sigma == doctest::Approx(1.0f));
        const rml_fx::BlurPlan big = rml_fx::blur_plan(18.0f);
        CHECK(big.levels == 3);  // 18 * 2 / 3 = 12: three halvings.
        CHECK(big.sigma == doctest::Approx(18.0f / 8.0f));
        CHECK(rml_fx::blur_plan(1e9f).sigma <= rml_fx::kMaxSinglePassSigma);
        CHECK(rml_fx::blur_plan(std::nanf("")).levels == 0);
        const auto w = rml_fx::blur_weights(2.0f);
        CHECK(w[0] + 2.0f * (w[1] + w[2] + w[3]) == doctest::Approx(1.0f));
        CHECK(w[0] > w[1]);
        CHECK(w[2] > w[3]);
        CHECK(rml_fx::blur_weights(0.0f)[0] == doctest::Approx(1.0f));
        // The backdrop: more rounds for more blur, taps never too far apart.
        CHECK(rml_fx::backdrop_plan(0.0f).passes == 0);
        const rml_fx::BackdropPlan soft = rml_fx::backdrop_plan(5.0f);
        CHECK(soft.levels == 1);  // Half resolution.
        CHECK(soft.passes == 1);
        const rml_fx::BackdropPlan glass = rml_fx::backdrop_plan(18.0f);
        CHECK(glass.levels > 1);  // Frosted's blur of 18 pixels goes smaller.
        CHECK(glass.passes <= 2);
        CHECK(glass.step <= 1.5f);
        const rml_fx::BackdropPlan most = rml_fx::backdrop_plan(1e9f);
        CHECK(most.levels == rml_fx::kMaxBackdropLevels);
        CHECK(most.passes <= 4);
        // Half-size targets.
        CHECK(rml_fx::half(1920) == 960);
        CHECK(rml_fx::half(1081) == 541);
        CHECK(rml_fx::half(1) == 1);
    }

    TEST_CASE("filters and gradients with bad numbers are refused") {
        RmlRenderer r;
        const float nan = std::nanf("");
        const Rml::Dictionary good{{"sigma", Rml::Variant(4.0f)}};
        const Rml::Dictionary bad{{"sigma", Rml::Variant(nan)}};
        const Rml::CompiledFilterHandle blur = r.CompileFilter("blur", good);
        CHECK(blur != 0);
        CHECK(r.CompileFilter("blur", bad) == 0);
        CHECK(r.CompileFilter("opacity", {{"value", Rml::Variant(nan)}}) == 0);
        CHECK(r.CompileFilter("drop-shadow", {{"offset", Rml::Variant(Rml::Vector2f(nan, 0.0f))}}) == 0);
        CHECK(r.CompileFilter("saturate", {{"value", Rml::Variant(1.6f)}}) != 0);
        CHECK(r.CompileFilter("melt", good) == 0);
        r.ReleaseFilter(blur);
        CHECK(r.CompileShader("radial-gradient", {{"radius", Rml::Variant(Rml::Vector2f(0.0f, 1.0f))}}) == 0);
        CHECK(r.CompileShader("linear-gradient", {}) == 0);  // No color stops.
        CHECK(r.CompileShader("creation", {}) == 0);
    }

    TEST_CASE("six glass windows blur the scene once; the simple glass not at all") {
        Fixture& f = fixture();
        const int errors = f.ui.system().errors();
        const std::string doc = rml::TestWindow::kDocument;
        REQUIRE(f.ui.show_document(doc, true));
        for (int i = 1; i <= 5; ++i) {
            REQUIRE(f.ui.show_document(doc + "#" + std::to_string(i), true));
        }
        f.ui.update(1280, 720, 1.0f);
        CHECK(f.ui.system().errors() == errors);
        // The copies stand apart.
        Rml::ElementDocument* first = f.ui.document(doc);
        Rml::ElementDocument* third = f.ui.document(doc + "#2");
        REQUIRE(first != nullptr);
        REQUIRE(third != nullptr);
        CHECK(third->GetAbsoluteOffset(Rml::BoxArea::Border).x ==
              doctest::Approx(first->GetAbsoluteOffset(Rml::BoxArea::Border).x + 64.0f));

        f.render.set_glass(GlassMode::Full);
        f.render.begin_frame(1280, 720);
        f.ui.render();
        RmlRenderer::Stats s = f.render.stats();
        CHECK(s.backdrops == 6);
        CHECK(s.backdrop_blurs == 1);
        CHECK(s.layers >= 2);
        CHECK(s.composites >= 6);
        CHECK(s.clip_writes > 0);  // The rounded corners clip the glass.
        CHECK(f.render.wants_backdrop());
        // The box shadows are drawn once into textures, then reused.
        f.render.begin_frame(1280, 720);
        f.ui.render();
        CHECK(f.render.stats().saved_layers == 0);

        f.render.set_glass(GlassMode::Simple);
        f.ui.set_simple_glass(true);
        f.ui.update(1280, 720, 1.0f);
        CHECK(first->IsClassSet("glass-simple"));
        f.render.begin_frame(1280, 720);
        f.ui.render();
        s = f.render.stats();
        CHECK(s.backdrops == 0);  // The style drops backdrop-filter with the simple glass (phase 119).
        CHECK(s.backdrop_blurs == 0);
        CHECK_FALSE(f.render.wants_backdrop());

        f.render.set_glass(GlassMode::Full);
        f.ui.set_simple_glass(false);
        // Closed now: RmlUi's own static pools (the gradients') are gone
        // before the fixture shuts RmlUi down at exit.
        f.ui.close_documents();
        CHECK_FALSE(f.ui.document_shown(doc));
        CHECK(f.ui.system().errors() == errors);
    }

    TEST_CASE("each token type takes CSS values and gives RCSS") {
        using rml::TokenType;
        const rml::FontCheck fonts = [](std::string_view id) { return id == "alegreya-sans"; };
        const auto conv = [&](TokenType t, std::string_view v) { return rml::convert_token(t, v, fonts, nullptr); };
        CHECK(conv(TokenType::Color, "#fff") == "rgba(255, 255, 255, 255)");
        CHECK(conv(TokenType::Color, "#5b5bd6") == "rgba(91, 91, 214, 255)");
        CHECK(conv(TokenType::Color, "#00000080") == "rgba(0, 0, 0, 128)");
        CHECK(conv(TokenType::Color, "rgba(255, 255, 255, .5)") == "rgba(255, 255, 255, 128)");
        CHECK(conv(TokenType::Color, "transparent") == "rgba(0, 0, 0, 0)");
        CHECK_FALSE(conv(TokenType::Color, "rgba(300, 0, 0, 1)"));
        CHECK_FALSE(conv(TokenType::Color, "rgba(0, 0, 0, 2)"));
        CHECK_FALSE(conv(TokenType::Color, "#12345"));
        CHECK_FALSE(conv(TokenType::Color, "red; } body { color: blue"));
        CHECK(conv(TokenType::Length, "16px") == "16dp");
        CHECK(conv(TokenType::Length, "0") == "0dp");
        CHECK(conv(TokenType::Length, "50%") == "50%");
        CHECK_FALSE(conv(TokenType::Length, "1em"));
        CHECK_FALSE(conv(TokenType::Length, "12"));
        CHECK(conv(TokenType::Number, "650") == "650");
        CHECK_FALSE(conv(TokenType::Number, "bold"));
        CHECK(conv(TokenType::Shadow, "inset 0 1px 0 rgba(255, 255, 255, .9), 0 10px 32px rgba(20, 30, 70, .2)") ==
              "rgba(255, 255, 255, 230) 0dp 1dp 0dp inset, rgba(20, 30, 70, 51) 0dp 10dp 32dp");
        CHECK(conv(TokenType::Shadow, "none") == "none");
        CHECK_FALSE(conv(TokenType::Shadow, "0 10px"));  // No color.
        CHECK(conv(TokenType::Filter, "blur(18px) saturate(160%)") == "blur(18dp) saturate(160%)");
        CHECK_FALSE(conv(TokenType::Filter, "blur(18px) url(x)"));
        CHECK(conv(TokenType::Paint, "linear-gradient(160deg, rgba(255, 255, 255, .62), transparent 65%)") ==
              "linear-gradient(160deg, rgba(255, 255, 255, 158), rgba(0, 0, 0, 0) 65%)");
        CHECK(conv(TokenType::Paint, "#5b5bd6") == "linear-gradient(rgba(91, 91, 214, 255), rgba(91, 91, 214, 255))");
        CHECK_FALSE(conv(TokenType::Paint, "image(grain.png repeat)"));  // No images allowed here.
        CHECK_FALSE(conv(TokenType::Paint, "conic-gradient(red, blue)"));
        CHECK(conv(TokenType::Font, "alegreya-sans") == "alegreya-sans");
        CHECK(conv(TokenType::Font, "ui") == "ui");
        CHECK_FALSE(conv(TokenType::Font, "comic-sans"));
        CHECK(conv(TokenType::IconMode, "solid") == "solid");
        CHECK_FALSE(conv(TokenType::IconMode, "neon"));
        // Every default is valid.
        for (const rml::TokenSpec& t : rml::token_specs()) {
            CHECK_MESSAGE(rml::convert_token(t.type, t.value, nullptr, nullptr).has_value(), t.name);
        }
    }

    TEST_CASE("tokens are substituted and unknown ones reported") {
        const rml::TokenMap tokens{{"text", "rgba(1, 2, 3, 255)"}, {"panel-radius", "16dp"}};
        std::vector<std::string> unknown;
        const std::string out =
            rml::substitute_tokens("a { color: var(--text); border-radius: var(--panel-radius) var(--nope); }",
                                   tokens, &unknown);
        CHECK(out == "a { color: rgba(1, 2, 3, 255); border-radius: 16dp var(--nope); }");
        REQUIRE(unknown.size() == 1);
        CHECK(unknown[0] == "nope");
    }

    TEST_CASE("the game's styles load; damaged ones are refused with a reason; a mod adds one") {
        const rml::FontCheck fonts = [](std::string_view) { return false; };
        std::string error;
        const auto frosted = rml::load_style(kData / "ui", "frosted", fonts, error);
        REQUIRE_MESSAGE(frosted.has_value(), error);
        CHECK(frosted->glass);
        CHECK(frosted->name("es") == "Frosted");
        CHECK(frosted->icon_mode == "duotone");
        CHECK(frosted->tokens.at("panel").find("image(/styles/frosted/grain.png repeat)") != std::string::npos);
        const auto vidrio = rml::load_style(kData / "ui", "vidrio", fonts, error);
        REQUIRE_MESSAGE(vidrio.has_value(), error);
        CHECK(vidrio->name("es-MX") == "Vidrio oscuro");
        CHECK(vidrio->name("en") == "Dark glass");
        CHECK(vidrio->tokens.at("text") == "rgba(241, 240, 255, 255)");
        CHECK(vidrio->sheet.find("border-color") != std::string::npos);
        CHECK(vidrio->preview.size() == 6);

        // A mod's ui folder with one good style and several bad ones.
        test::TempDir dir;
        const std::filesystem::path ui = dir / "ui";
        const auto style = [&ui](const std::string& id, const std::string& json) {
            std::filesystem::create_directories(ui / "styles" / id);
            test::write_text(ui / "styles" / id / "style.json", json);
        };
        style("pizarra", R"({"schemaVersion": 1, "name": {"es": "Pizarra"}, "glass": false,
                             "tokens": {"accent": "#ff8800", "panel": "image(tiza.png), #223344"},
                             "sheets": ["extra.rcss"]})");
        test::write_text(ui / "styles" / "pizarra" / "extra.rcss",
                         ".window { border-color: var(--accent); decorator: image(tiza.png); }\n");
        std::filesystem::copy_file(kData / "ui" / "styles" / "frosted" / "grain.png",
                                   ui / "styles" / "pizarra" / "tiza.png");
        style("rota", "{ not json");
        style("token", R"({"schemaVersion": 1, "name": {"es": "X"}, "tokens": {"sparkle": "#fff"}})");
        style("tipo", R"({"schemaVersion": 1, "name": {"es": "X"}, "tokens": {"panel-radius": "#fff"}})");
        style("fuera", R"({"schemaVersion": 1, "name": {"es": "X"}, "sheets": ["../pizarra/extra.rcss"]})");
        style("falta", R"({"schemaVersion": 1, "name": {"es": "X"}, "sheets": ["nada.rcss"]})");
        style("imagen", R"j({"schemaVersion": 1, "name": {"es": "X"}, "tokens": {"panel": "image(../../x.png)"}})j");
        style("campo", R"({"schemaVersion": 1, "name": {"es": "X"}, "script": "x"})");
        style("frosted", R"({"schemaVersion": 1, "name": {"es": "Otro"}})");  // Id taken by the game's.

        rml::StyleLibrary library;
        library.scan({kData / "ui", ui}, fonts);
        CHECK(library.find("frosted") != nullptr);
        CHECK(library.find("frosted")->name("es") == "Frosted");
        CHECK(library.find("vidrio") != nullptr);
        const rml::Style* pizarra = library.find("pizarra");
        REQUIRE(pizarra != nullptr);
        CHECK_FALSE(pizarra->glass);
        CHECK(pizarra->tokens.at("panel-blur") == "none");
        CHECK(pizarra->sheet.find("border-color: rgba(255, 136, 0, 255)") != std::string::npos);
        CHECK(pizarra->sheet.find("image(/styles/pizarra/tiza.png)") != std::string::npos);
        CHECK(library.styles().size() == 3);
        std::string errors;
        for (const std::string& e : library.errors()) {
            errors += e + "\n";
        }
        for (const char* id : {"rota:", "token: unknown token 'sparkle'", "tipo: token 'panel-radius'", "fuera:",
                               "falta:", "imagen:", "campo: style.json: unknown field 'script'",
                               "frosted: another style"}) {
            CHECK_MESSAGE(errors.find(id) != std::string::npos, id << "\n" << errors);
        }

        // The example mod's style (docs/CREAR_MODS.md).
        rml::StyleLibrary with_example;
        with_example.scan({kData / "ui", std::filesystem::path(SC_SOURCE_DIR) / "tools" / "example_mod" / "ui"}, fonts);
        CHECK(with_example.errors().empty());
        REQUIRE(with_example.find("pizarra") != nullptr);
        CHECK(with_example.find("pizarra")->name("es") == "Pizarra (ejemplo)");
    }

    TEST_CASE("the style changes with the test window open") {
        Fixture& f = fixture();
        const int errors = f.ui.system().errors();
        const std::string doc = rml::TestWindow::kDocument;
        REQUIRE(f.ui.show_document(doc, true));
        f.ui.update(1280, 720, 1.0f);
        CHECK(f.ui.style_id() == "frosted");
        Rml::ElementDocument* d = f.ui.document(doc);
        REQUIRE(d != nullptr);
        CHECK(d->GetProperty<Rml::Colourb>("color") == Rml::Colourb(27, 31, 36, 255));
        // The icons are the style's sprites.
        Rml::ElementList images;
        d->GetElementsByTagName(images, "img");
        int sprites = 0;
        for (Rml::Element* img : images) {
            sprites += img->HasAttribute("sprite") ? 1 : 0;
        }
        CHECK(sprites >= 7);

        CHECK(f.ui.set_style("vidrio") == "vidrio");
        f.ui.update(1280, 720, 1.0f);
        d = f.ui.document(doc);
        REQUIRE(d != nullptr);
        CHECK(f.ui.document_shown(doc));
        CHECK(d->GetProperty<Rml::Colourb>("color") == Rml::Colourb(241, 240, 255, 255));
        // Twice the scale: the icons' sheet at 2x, without errors.
        f.ui.update(1280, 720, 2.0f);
        CHECK(f.ui.document_shown(doc));
        // An unknown style falls back to Frosted.
        CHECK(f.ui.set_style("nope") == "frosted");
        f.ui.update(1280, 720, 1.0f);
        d = f.ui.document(doc);
        REQUIRE(d != nullptr);
        CHECK(d->GetProperty<Rml::Colourb>("color") == Rml::Colourb(27, 31, 36, 255));
        CHECK(f.ui.system().errors() == errors);
        f.ui.close_documents();
    }

    // Phase 127: the keyboard moves through the buttons of a panel.
    TEST_CASE("Tab, Enter and Esc move through a panel's buttons; the arrows stay the game's after a click") {
        Fixture& f = fixture();
        const std::string doc_key = "hud/panel.rml#nav";
        REQUIRE(f.ui.show_document(doc_key, true));
        Rml::ElementDocument* doc = f.ui.document(doc_key);
        REQUIRE(doc != nullptr);
        ThingRows rows;
        std::vector<int> pressed;
        for (int i = 0; i < 3; ++i) {
            rows.buttons({rows.button("B" + std::to_string(i), {},
                                      [&pressed, i](GameSession*, const RowInput&, RowEffects&) { pressed.push_back(i); }, i != 2)});
        }
        std::vector<std::string> keys;
        rows_into(doc->GetElementById("rows"), rows, keys);
        // The clicks of the panel, as RmlPanels hears them.
        struct Clicks final : Rml::EventListener {
            ThingRows* rows = nullptr;
            void ProcessEvent(Rml::Event& ev) override {
                for (Rml::Element* e = ev.GetTargetElement(); e != nullptr; e = e->GetParentNode()) {
                    if (e->HasAttribute("data-act")) {
                        RowEffects fx;
                        rows->acts[static_cast<std::size_t>(e->GetAttribute<int>("data-act", -1))](nullptr, RowInput{}, fx);
                        return;
                    }
                }
            }
        } clicks;
        clicks.rows = &rows;
        doc->AddEventListener("click", &clicks);
        f.ui.update(1280, 720, 1.0f);
        const auto key = [&](SDL_Keycode k) {
            SDL_Event e{};
            e.type = SDL_EVENT_KEY_DOWN;
            e.key.key = k;
            const bool taken = f.ui.process_event(e, 1.0f);
            f.ui.update(1280, 720, 1.0f);
            return taken;
        };
        const auto focused = [&]() -> std::string {
            Rml::Element* e = f.ui.context()->GetFocusElement();
            return e != nullptr && e->HasAttribute("data-act") ? e->GetInnerRML() : std::string();
        };
        f.ui.set_navigation(rml::RmlUi::Navigation::Off);
        CHECK_FALSE(key(SDLK_TAB));
        f.ui.set_navigation(rml::RmlUi::Navigation::Windows);
        CHECK_FALSE(key(SDLK_LEFT));  // Nothing has the focus: the camera's.
        CHECK(key(SDLK_TAB));
        CHECK(focused().find("B0") != std::string::npos);
        CHECK(f.ui.context()->GetFocusElement()->IsPseudoClassSet("focus-visible"));
        // The arrows go to the button below and back.
        CHECK(key(SDLK_DOWN));
        CHECK(focused().find("B1") != std::string::npos);
        CHECK(key(SDLK_UP));
        CHECK(focused().find("B0") != std::string::npos);
        CHECK(key(SDLK_TAB));
        CHECK(focused().find("B1") != std::string::npos);
        CHECK(key(SDLK_RETURN));
        REQUIRE(pressed.size() == 1);
        CHECK(pressed[0] == 1);
        CHECK(key(SDLK_TAB));  // The third is off: not reached, the first again.
        CHECK(focused().find("B2") == std::string::npos);
        CHECK(key(SDLK_ESCAPE));  // Out of the buttons...
        CHECK_FALSE(key(SDLK_LEFT));  // ...and the arrows are the game's again.
        doc->RemoveEventListener("click", &clicks);
        f.ui.set_navigation(rml::RmlUi::Navigation::Off);
        REQUIRE(f.ui.show_document(doc_key, false));
    }

    TEST_CASE("a tooltip shows the tip of what lies under the pointer, and the tutorial marks") {
        Fixture& f = fixture();
        Rml::Context& ctx = *f.ui.context();
        Rml::ElementDocument* doc = ctx.LoadDocumentFromMemory(R"(<rml><head><link type="text/rcss" href="/base.rcss"/>
            <style>body { width: 400dp; height: 300dp; } .b { width: 100dp; height: 40dp; }</style></head>
            <body><div class="b" id="a" tip="@hud.speed.pause.tooltip" tip-detail="more">x</div>
            <div class="b" id="c" mark="speed">y</div></body></rml>)");
        REQUIRE(doc != nullptr);
        doc->Show();
        f.ui.set_tooltips(true, 0);
        f.ui.set_mark("speed");
        f.ui.update(1280, 720, 1.0f);
        Rml::Element* a = doc->GetElementById("a");
        const Rml::Vector2f c = center(*a);
        (void)f.ui.process_event(mouse_motion(c.x, c.y), 1.0f);
        f.ui.update(1280, 720, 1.0f);
        CHECK(f.ui.tooltip_shown().find(i18n::translator().text("hud.speed.pause.tooltip")) != std::string::npos);
        CHECK(doc->GetElementById("c")->IsClassSet("marked"));
        CHECK_FALSE(a->IsClassSet("marked"));
        // Away from it, the tooltip goes.
        (void)f.ui.process_event(mouse_motion(900.0f, 700.0f), 1.0f);
        f.ui.update(1280, 720, 1.0f);
        CHECK(f.ui.tooltip_shown().empty());
        f.ui.set_mark({});
        doc->Close();
        f.ui.close_documents();
        f.ui.update(1280, 720, 1.0f);
    }
}
