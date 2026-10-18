// Phase 121: the top bar's model has the same texts and tooltips as the old
// HUD (the keys below are those top_bar() used until phase 120).
#include <doctest.h>

#include <algorithm>
#include <filesystem>
#include <memory>
#include <optional>
#include <string>

#include "core/speed.h"
#include "game/game_hud.h"
#include "game/game_session.h"
#include "game/hud_model.h"
#include "i18n/translator.h"
#include "sim/worldgen.h"
#include "test_util.h"

using namespace sc;
using i18n::tr;

namespace {

std::shared_ptr<const sim::Content> content() {
    return std::shared_ptr<const sim::Content>(std::shared_ptr<const sim::Content>{}, &sc::test::core_content());
}

// The game's languages, Spanish active, once.
void languages() {
    static const bool loaded = [] {
        const std::filesystem::path data = std::filesystem::path(SC_SOURCE_DIR) / "data";
        auto& t = i18n::translator();
        REQUIRE(t.load(data / "lang", test::read_text(data / "lang" / "en.json")) == 0);
        for (const char* code : {"es", "en"}) {
            REQUIRE(t.add_mod_texts(test::read_text(data / "mods" / "core" / "lang" / (std::string(code) + ".json")), code));
        }
        REQUIRE(t.set_language("es"));
        return true;
    }();
    (void)loaded;
}

}  // namespace

TEST_SUITE("hud") {
    TEST_CASE("the top bar says what the old one said") {
        languages();
        for (const char* key : {"hud.population", "hud.population.tooltip", "hud.happiness", "hud.happiness.tooltip",
                                "hud.gold", "hud.gold.tooltip", "hud.food", "hud.food.tooltip", "hud.amount", "hud.date",
                                "hud.weather", "hud.weather.tooltip", "hud.speed.value", "hud.speed.pause.tooltip",
                                "hud.speed.slower.tooltip", "hud.speed.faster.tooltip", "hud.sick", "hud.fires",
                                "hud.troubles.tooltip", "hud.raiders", "hud.raiders.tooltip", "hud.net.players",
                                "hud.minimap.tooltip", "hud.compass.tooltip", "hud.log.goTo", "hud.tip.shift",
                                "hud.dock.goods", "hud.dock.stats", "hud.dock.log", "hud.dock.layers"}) {
            CHECK_MESSAGE(i18n::translator().has(key), key);
        }
        sim::GameSetup setup;
        setup.seed = 5;
        sim::MapSettings s;
        s.size = sim::MapSize::Small;
        s.seed = 31;
        std::optional<sim::MapData> map = sim::generate_map(s, *content());
        REQUIRE(map.has_value());
        GameSession session(content(), std::move(*map), setup);
        for (int i = 0; i < 20; ++i) {
            session.step();
        }
        const sim::Game& g = session.game();
        const TopBarModel m = top_bar_model(g, session.town(), session.local_player(), speed::kNormal, speed::kNormal,
                                            speed::kMax, HudNetInfo{});
        REQUIRE(m.founded);
        CHECK(m.population == tr("hud.population", g.population(session.town())));
        CHECK(m.happiness == tr("hud.happiness", g.happiness(session.town())));
        CHECK(m.gold == tr("hud.gold", g.gold(session.town())));
        const sim::Calendar cal = g.calendar();
        CHECK(m.date == tr("hud.date", static_cast<int>(cal.year), static_cast<int>(cal.month), static_cast<int>(cal.day)));
        CHECK(m.speed == tr("hud.speed.value", speed_text(speed::kNormal)));
        CHECK_FALSE(m.paused);
        CHECK(m.can_slower);
        // Food first, as one total; then the logs and the stone always.
        REQUIRE(m.goods.size() >= 3);
        CHECK(m.goods[0].id == "food");
        CHECK(m.goods[0].sprite);
        bool logs = false;
        for (const HudItem& item : m.goods) {
            logs = logs || item.id == "core:log";
            CHECK_FALSE(item.image.empty());
            CHECK_FALSE(item.tip.empty());
        }
        CHECK(logs);
        CHECK(m.goods.size() <= kTopBarGoods);
        // Paused: the pause shows, the speed stays the one it goes back to.
        const TopBarModel p = top_bar_model(g, session.town(), session.local_player(), speed::kPause, speed::kNormal,
                                            speed::kMax, HudNetInfo{});
        CHECK(p.paused);
        CHECK(p.speed == m.speed);
    }

    TEST_CASE("goods without a pile model use an icon; the others their picture") {
        const sim::Content& c = sc::test::core_content();
        for (const sim::ResourceDef& def : c.resources) {
            HudItem item;
            good_image(def, !def.pile.empty(), item);
            if (def.id == "core:log" || def.id == "core:stone" || def.pile.empty()) {
                CHECK_MESSAGE(item.sprite, def.id);
                CHECK(item.image.starts_with("icon-"));
            } else {
                CHECK_FALSE(item.sprite);
                CHECK(item.image.starts_with("/thumbs/resource/"));
            }
        }
    }

    TEST_CASE("the build bar lists a category's buildings with picture and cost, and the tutorial's marks") {
        languages();
        sim::GameSetup setup;
        setup.seed = 5;
        sim::MapSettings ms;
        ms.size = sim::MapSize::Small;
        ms.seed = 31;
        std::optional<sim::MapData> map = sim::generate_map(ms, *content());
        REQUIRE(map.has_value());
        GameSession session(content(), std::move(*map), setup);
        const sim::Game& g = session.game();
        const sim::DefIndex house = g.content().find_building("core:house");
        REQUIRE(house != sim::kNoDef);
        const std::uint8_t cat = static_cast<std::uint8_t>(g.content().buildings[house].category % kBuildCategories);
        BuildBarModel m = build_bar_model(g, session.town(), cat, house, {});
        REQUIRE(m.cats.size() == kBuildCategories);
        CHECK(m.cats[cat].on);
        const auto it = std::find_if(m.items.begin(), m.items.end(), [](const BuildItem& b) { return b.id == "core:house"; });
        REQUIRE(it != m.items.end());
        CHECK(it->on);
        CHECK(it->image == "/thumbs/building/core/house");
        CHECK(it->name == tr(g.content().buildings[house].name_key));
        CHECK(it->tip.find(tr("hud.build.size", g.content().buildings[house].width, g.content().buildings[house].depth)) !=
              std::string::npos);
        CHECK(it->cost.size() == g.content().buildings[house].cost.size());
        CHECK(it->mark == "build:core:house");
        for (const BuildItem& b : m.items) {
            CHECK(b.id != "core:town_center");
        }
        // Pointed at from another category: that category is marked.
        const std::uint8_t other = static_cast<std::uint8_t>((cat + 1) % kBuildCategories);
        m = build_bar_model(g, session.town(), other, sim::kNoDef, "build:core:house");
        CHECK(m.cats[cat].mark == "build:core:house");
        CHECK(m.cats[other].mark.empty());
    }
}
