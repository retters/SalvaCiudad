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
#include "game/thing_rows.h"
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

    // Phase 124: the windows of buildings are RmlUi's, their rows built by
    // building_rows(). Every core building's window says only translated
    // texts, and its buttons reach the game.
    TEST_CASE("every core building's window is translated, and its buttons reach the game") {
        languages();
        sim::GameSetup setup;
        setup.seed = 7;
        setup.rules.raiders = sim::Threat::None;
        setup.rules.fires = sim::Threat::None;
        sim::MapSettings ms;
        ms.size = sim::MapSize::Small;
        ms.seed = 31;
        std::optional<sim::MapData> map = sim::generate_map(ms, *content());
        REQUIRE(map.has_value());
        GameSession session(content(), std::move(*map), setup);
        for (int i = 0; i < 20; ++i) {
            session.step();
        }
        sim::Game& g = session.game();
        const sim::Content& c = g.content();
        const auto apply = [&](sim::CommandType type, sim::DefIndex def = sim::kNoDef, std::int32_t value = 0) {
            sim::Command cmd;
            cmd.type = type;
            cmd.player = session.local_player();
            cmd.def = def;
            cmd.value = value;
            g.apply(cmd);
        };
        for (int i = 0; i < 8; ++i) {
            apply(sim::CommandType::DevLevel);  // Every building unlocked.
        }
        for (std::size_t r = 0; r < c.resources.size(); ++r) {
            apply(sim::CommandType::DevGrant, static_cast<sim::DefIndex>(r), 2000);
        }
        const sim::Building* tc = g.buildings().get(g.player(session.town()).town_center);
        REQUIRE(tc != nullptr);
        const std::int32_t cx = tc->x;
        const std::int32_t cz = tc->z;
        // Each building near the town center, wherever it fits.
        const auto put = [&](sim::DefIndex d) {
            for (std::int32_t r = 4; r <= 60; ++r) {
                for (std::int32_t dz = -r; dz <= r; ++dz) {
                    for (std::int32_t dx = -r; dx <= r; ++dx) {
                        if (std::max(std::abs(dx), std::abs(dz)) != r ||
                            g.can_place(session.local_player(), d, cx + dx, cz + dz, 0) != sim::PlaceError::None) {
                            continue;
                        }
                        sim::Command cmd;
                        cmd.type = sim::CommandType::PlaceBuilding;
                        cmd.player = session.local_player();
                        cmd.def = d;
                        cmd.position = {sim::Fixed::from_int(cx + dx), sim::Fixed::from_int(cz + dz)};
                        g.apply(cmd);
                        return true;
                    }
                }
            }
            return false;
        };
        // Nothing untranslated: a missing text shows its key.
        const auto looks_like_key = [](const std::string& t) {
            for (const char* prefix : {"hud.", "building.", "resource.", "task.", "unit.", "herd.", "crop.", "need."}) {
                if (t.find(prefix) != std::string::npos) {
                    return true;
                }
            }
            return t.find('{') != std::string::npos;
        };
        TradeDraft draft;
        const auto check_window = [&](sim::EntityId id) {
            const ThingRows rows = building_rows(session, id, draft);
            CHECK_FALSE(rows.gone);
            CHECK(rows.icon.starts_with("/thumbs/building/"));
            std::vector<std::string> texts;
            for (const WinRow& r : rows.rows) {
                texts.push_back(r.text);
                texts.push_back(r.tip);
                for (const RowButton& b : r.buttons) {
                    texts.push_back(b.label);
                    texts.push_back(b.tip);
                    CHECK(b.act >= 0);
                    CHECK(static_cast<std::size_t>(b.act) < rows.acts.size());
                }
                for (const RowPerson& p : r.people) {
                    texts.push_back(p.name);
                    texts.push_back(p.sub);
                }
                CHECK_FALSE(row_rml(r).empty());
            }
            for (const std::string& t : texts) {
                CHECK_MESSAGE(!looks_like_key(t), c.buildings[g.buildings().get(id)->def].id << ": " << t);
            }
        };
        const auto newest = [&](sim::DefIndex d) {
            sim::EntityId found;
            for (std::size_t i = 0; i < g.buildings().size(); ++i) {
                if (g.buildings().data()[i].def == d) {
                    found = g.buildings().entities()[i];
                }
            }
            return found;
        };
        // Every building, one at a time: placed, its window being built and
        // built, and taken away again (the town has no room for all at once).
        // Roads are no buildings once laid.
        std::string missed;
        std::size_t windows = 0;
        for (std::size_t d = 0; d < c.buildings.size(); ++d) {
            const sim::BuildingDef& def = c.buildings[d];
            if (def.kind == sim::BuildingKind::TownCenter || def.cart || def.road > 0 || def.road_eraser) {
                continue;
            }
            if (!put(static_cast<sim::DefIndex>(d))) {
                missed += " " + def.id;
                continue;
            }
            const sim::EntityId id = newest(static_cast<sim::DefIndex>(d));
            REQUIRE(id.valid());
            check_window(id);
            apply(sim::CommandType::DevBuild);
            for (int i = 0; i < 3; ++i) {
                session.step();
            }
            check_window(id);
            ++windows;
            sim::Command remove;
            remove.type = sim::CommandType::RemoveBuilding;
            remove.player = session.local_player();
            remove.entity = id;
            g.apply(remove);
            for (int i = 0; i < 3; ++i) {
                session.step();
            }
        }
        CHECK_MESSAGE(missed.empty(), "not placed:" << missed);
        check_window(g.player(session.town()).town_center);
        MESSAGE(windows << " building windows read");

        // The ones whose buttons are pressed below.
        for (const char* id : {"core:house", "core:trading_post"}) {
            REQUIRE(put(c.find_building(id)));
        }
        bool workshop = false;
        bool farmhouse = false;
        for (std::size_t d = 0; d < c.buildings.size(); ++d) {
            const sim::BuildingDef& def = c.buildings[d];
            bool& have = def.work == sim::WorkKind::Farm ? farmhouse : workshop;
            if (!have && ((def.work == sim::WorkKind::Produce && def.workers > 1) ||
                          (def.work == sim::WorkKind::Farm && def.fields > 0))) {
                have = put(static_cast<sim::DefIndex>(d));
            }
        }
        REQUIRE(workshop);
        REQUIRE(farmhouse);
        apply(sim::CommandType::DevBuild);
        for (int i = 0; i < 40; ++i) {
            session.step();
        }

        // The buttons: each found by its text (or its mark) and pressed.
        const auto press = [&](sim::EntityId id, const std::string& label, const std::string& mark = {}) {
            const ThingRows rows = building_rows(session, id, draft);
            for (const WinRow& r : rows.rows) {
                for (const RowButton& b : r.buttons) {
                    if ((!label.empty() && b.label == label) || (!mark.empty() && b.mark == mark)) {
                        RowEffects e;
                        if (b.enabled) {
                            rows.acts[static_cast<std::size_t>(b.act)](session, 0, e);
                            session.step();
                        }
                        return e;
                    }
                }
            }
            FAIL("no button " << label << mark);
            return RowEffects{};
        };
        const auto find = [&](auto pred) {
            for (std::size_t i = 0; i < g.buildings().size(); ++i) {
                const sim::Building& b = g.buildings().data()[i];
                if (b.owner == session.town() && b.state == sim::BuildingState::Complete && pred(c.buildings[b.def], b)) {
                    return g.buildings().entities()[i];
                }
            }
            return sim::EntityId{};
        };
        // A workshop: fewer workers, more again, then stopped and working.
        const sim::EntityId shop = find([](const sim::BuildingDef& d, const sim::Building&) {
            return d.work == sim::WorkKind::Produce && d.workers > 1;
        });
        REQUIRE(shop.valid());
        const std::int32_t wanted = g.buildings().get(shop)->wanted_workers;
        {
            const ThingRows rows = building_rows(session, shop, draft);
            const RowButton* fewer = nullptr;
            for (const WinRow& r : rows.rows) {
                if (r.kind == WinRow::Kind::Stepper && r.buttons.size() == 2 && r.buttons[1].mark == "workers") {
                    fewer = &r.buttons[0];
                }
            }
            REQUIRE(fewer != nullptr);
            REQUIRE(fewer->enabled);
            RowEffects e;
            rows.acts[static_cast<std::size_t>(fewer->act)](session, 0, e);
            session.step();
            CHECK(g.buildings().get(shop)->wanted_workers == wanted - 1);
        }
        (void)press(shop, {}, "workers");  // The tutorial's "+".
        CHECK(g.buildings().get(shop)->wanted_workers == wanted);
        (void)press(shop, tr("hud.building.working"));
        CHECK(g.buildings().get(shop)->stopped);
        (void)press(shop, tr("hud.building.stopped"));
        CHECK_FALSE(g.buildings().get(shop)->stopped);
        // A farm: "New field" waits for the field to be marked on the map.
        const sim::EntityId farm =
            find([](const sim::BuildingDef& d, const sim::Building&) { return d.work == sim::WorkKind::Farm && d.fields > 0; });
        REQUIRE(farm.valid());
        (void)press(farm, tr("hud.farm.newField"));
        CHECK(session.ui().field_farm == farm);
        // The town center's bell.
        const sim::EntityId center = g.player(session.town()).town_center;
        (void)press(center, tr("hud.bell.ring"));
        CHECK(g.player(session.town()).alarm);
        (void)press(center, tr("hud.bell.stop"));
        CHECK_FALSE(g.player(session.town()).alarm);
        // The town center cannot be demolished; a house can, and its window goes.
        for (const WinRow& r : building_rows(session, center, draft).rows) {
            for (const RowButton& b : r.buttons) {
                CHECK(b.label != tr("hud.building.demolish"));
            }
        }
        const sim::EntityId home =
            find([](const sim::BuildingDef& d, const sim::Building&) { return d.kind == sim::BuildingKind::House; });
        REQUIRE(home.valid());
        const RowEffects gone = press(home, tr("hud.building.demolish"));
        CHECK(gone.close);
        for (int i = 0; i < 5; ++i) {
            session.step();
        }
        CHECK(g.buildings().get(home) == nullptr);
        CHECK(building_rows(session, home, draft).gone);
        CHECK(building_rows(session, home, draft).rows.front().text == tr("hud.window.gone.building"));
        // A trading post's automatic trade: a slider moved, and the rule applied.
        const sim::EntityId post = find([](const sim::BuildingDef& d, const sim::Building&) { return d.trade; });
        REQUIRE(post.valid());
        {
            const ThingRows rows = building_rows(session, post, draft);
            const auto slider = std::find_if(rows.rows.begin(), rows.rows.end(),
                                             [](const WinRow& r) { return r.kind == WinRow::Kind::Slider; });
            REQUIRE(slider != rows.rows.end());
            RowEffects e;
            rows.acts[static_cast<std::size_t>(slider->act)](session, 500, e);  // Sell over 500.
            CHECK(draft.sell == 500);
        }
        (void)press(post, tr("hud.auto.apply"));
        REQUIRE_FALSE(g.player(session.town()).trade_rules.empty());
        CHECK(g.player(session.town()).trade_rules.front().sell_above == 500);
    }

    TEST_CASE("a window's rows as RML: escaped, and only enabled buttons act") {
        WinRow text;
        text.text = "a < b & \"c\"";
        CHECK(row_rml(text) == "<div class=\"line\">a &lt; b &amp; &quot;c&quot;</div>");
        WinRow buttons;
        buttons.kind = WinRow::Kind::Buttons;
        RowButton on;
        on.label = "Ok";
        on.act = 3;
        on.on = true;
        RowButton off;
        off.icon = "icon-x";
        off.act = 4;
        off.enabled = false;
        buttons.buttons = {on, off};
        const std::string rml = row_rml(buttons);
        CHECK(rml.find("class=\"btn on\" data-act=\"3\"") != std::string::npos);
        CHECK(rml.find("data-act=\"4\"") == std::string::npos);
        CHECK(rml.find("class=\"btn off square\"") != std::string::npos);
        // A slider's value is not part of its key: moving it does not rebuild it.
        WinRow slider;
        slider.kind = WinRow::Kind::Slider;
        slider.min = -10;
        slider.max = 2000;
        slider.step = 10;
        slider.value = 40;
        WinRow moved = slider;
        moved.value = 50;
        CHECK(row_key(slider) == row_key(moved));
        CHECK(row_rml(slider) != row_rml(moved));
    }
}
