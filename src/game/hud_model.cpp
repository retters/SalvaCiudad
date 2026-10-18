#include "game/hud_model.h"

#include <algorithm>
#include <string_view>

#include "core/speed.h"
#include "game/game_hud.h"
#include "i18n/translator.h"

namespace sc {

using i18n::tr;

namespace {

// Goods without a pile model and their icon (data/ui/icons/icons.json).
struct GoodIcon {
    std::string_view id;
    std::string_view icon;
};
constexpr GoodIcon kGoodIcons[] = {
    {"core:log", "icon-log"}, {"core:stone", "icon-stone"}, {"core:gold", "icon-coins"}, {"core:ivory", "icon-box"},
};

std::string picture_path(std::string_view id) {
    std::string path = "/thumbs/resource/" + std::string(id);
    std::replace(path.begin(), path.end(), ':', '/');
    return path;
}

}  // namespace

void good_image(const sim::ResourceDef& def, bool has_model, HudItem& item) {
    for (const GoodIcon& g : kGoodIcons) {
        if (def.id == g.id) {
            item.image = std::string(g.icon);
            item.sprite = true;
            return;
        }
    }
    if (has_model) {
        item.image = picture_path(def.id);
        item.sprite = false;
    } else {
        item.image = "icon-box";
        item.sprite = true;
    }
}

BuildBarModel build_bar_model(const sim::Game& game, std::uint8_t town, std::uint8_t category,
                              sim::DefIndex placing, const std::string& highlight) {
    static constexpr const char* kCategoryKeys[kBuildCategories] = {
        "hud.build.cat.housing", "hud.build.cat.food",       "hud.build.cat.resources", "hud.build.cat.industry",
        "hud.build.cat.services", "hud.build.cat.decoration", "hud.build.cat.defense",   "hud.build.cat.plaza",
        "hud.build.cat.garden",  "hud.build.cat.nature",     "hud.build.cat.monuments", "hud.build.cat.ruins"};
    static constexpr const char* kCategoryIcons[kBuildCategories] = {
        "icon-home",   "icon-wheat", "icon-pickaxe", "icon-factory",  "icon-well",     "icon-flower",
        "icon-shield", "icon-fountain", "icon-stall", "icon-tree", "icon-landmark", "icon-ruins"};
    const sim::Content& content = game.content();
    BuildBarModel m;
    // The tutorial may point at a building: its category too, while another is shown.
    sim::DefIndex pointed = sim::kNoDef;
    if (highlight.starts_with("build:")) {
        pointed = content.find_building(std::string_view(highlight).substr(6));
    }
    const std::size_t shown = category % kBuildCategories;
    for (std::size_t c = 0; c < kBuildCategories; ++c) {
        BuildCat cat;
        cat.index = static_cast<int>(c);
        cat.name = tr(kCategoryKeys[c]);
        cat.icon = kCategoryIcons[c];
        cat.on = c == shown;
        if (pointed != sim::kNoDef && content.buildings[pointed].category % kBuildCategories == c && c != shown) {
            cat.mark = highlight;
        }
        m.cats.push_back(std::move(cat));
    }
    const std::int32_t tier = game.tier(town);
    for (std::size_t i = 0; i < content.buildings.size(); ++i) {
        const sim::BuildingDef& d = content.buildings[i];
        if (d.kind == sim::BuildingKind::TownCenter || d.cart || d.category % kBuildCategories != shown) {
            continue;
        }
        BuildItem item;
        item.id = d.id;
        item.name = tr(d.name_key);
        item.image = "/thumbs/building/" + d.id;
        std::replace(item.image.begin(), item.image.end(), ':', '/');
        std::string cost;
        for (const sim::ResourceAmount& c : d.cost) {
            if (c.resource >= content.resources.size()) {
                continue;
            }
            const sim::ResourceDef& r = content.resources[c.resource];
            HudItem part;
            part.id = r.id;
            part.text = std::to_string(c.amount);
            part.tip = tr("hud.amount", tr(r.name_key), c.amount);
            good_image(r, !r.pile.empty(), part);
            item.cost.push_back(std::move(part));
            cost += (cost.empty() ? "" : ", ") + tr("hud.amount", tr(r.name_key), c.amount);
        }
        std::string tip = item.name + "\n" + tr("hud.build.cost", cost.empty() ? tr("hud.cost.free") : cost) + "\n" +
                          tr("hud.build.size", d.width, d.depth);
        if (d.workers > 0) {
            tip += "\n" + tr("hud.build.workers", d.workers);
        }
        if (d.residents > 0) {
            tip += "\n" + tr("hud.build.residents", d.residents);
        }
        if (d.storage > 0) {
            tip += "\n" + tr("hud.build.storage", d.storage);
        }
        if (d.tier > tier) {
            tip += "\n" + tr("hud.build.locked", d.tier);
            item.lock = tr("hud.build.level", d.tier);
        }
        if (d.service != sim::kNoNeed) {
            tip += "\n" + tr("hud.build.service", tr(need_text_key(d.service)), d.service_radius);
        }
        item.tip = std::move(tip);
        item.mark = "build:" + d.id;
        item.on = placing == static_cast<sim::DefIndex>(i);
        m.items.push_back(std::move(item));
    }
    return m;
}

TopBarModel top_bar_model(const sim::Game& game, std::uint8_t town, std::uint8_t local_player, int speed,
                          int shown_speed, int max_speed, const HudNetInfo& net) {
    const sim::Content& content = game.content();
    TopBarModel m;
    // Speed: pause, and "- xN +" (phase 58).
    m.paused = speed == speed::kPause;
    m.speed = tr("hud.speed.value", speed_text(shown_speed));
    m.can_slower = shown_speed > speed::kMin;
    m.can_faster = shown_speed < max_speed;
    // Multiplayer: who plays.
    m.networked = net.networked;
    if (net.networked) {
        m.players = tr("hud.net.players", net.connected);
        m.players_tip = net.names;
    }
    // Season and weather, then the date.
    static constexpr const char* kSeasonKeys[] = {"hud.season.spring", "hud.season.summer", "hud.season.autumn",
                                                  "hud.season.winter"};
    const sim::Calendar cal = game.calendar();
    std::string weather =
        tr("hud.weather", tr(kSeasonKeys[static_cast<std::size_t>(cal.season) % 4]), game.temperature());
    const bool cycle = game.rules().day_night.enabled();
    const sim::DayTime day_time = game.day_time();
    if (cycle) {
        weather = tr("hud.dayTime", tr(day_time.night ? "hud.night" : "hud.day"), weather);
    }
    const bool rainy_game = game.rules().rain != 0;
    const bool raining = rainy_game && game.raining();
    const bool snowing = rainy_game && game.snowing();
    if (raining || snowing) {
        weather = tr("hud.dayTime", tr(raining ? "hud.weather.rain" : "hud.weather.snowfall"), weather);
    }
    m.weather = weather;
    m.cold = game.temperature() < 0;
    m.date = tr("hud.date", static_cast<int>(cal.year), static_cast<int>(cal.month), static_cast<int>(cal.day));
    m.weather_icon = raining ? "icon-rain" : snowing ? "icon-snow" : (cycle && day_time.night) ? "icon-moon" : "icon-sun";
    std::string weather_tip = tr(game.frozen() ? "hud.weather.frozen" : "hud.weather.tooltip", game.snow());
    if (rainy_game) {
        weather_tip += "\n" + (raining       ? tr("hud.weather.rain.tooltip")
                               : snowing      ? tr("hud.weather.snowfall.tooltip")
                               : game.muddy() ? tr("hud.weather.mud.tooltip")
                                              : tr("hud.weather.dry.tooltip", game.days_without_rain()));
    }
    if (cycle) {
        // Ten ticks a second at normal speed.
        const int seconds = static_cast<int>((day_time.ticks_left + 9) / 10);
        const std::string s2 = (seconds % 60 < 10 ? "0" : "") + std::to_string(seconds % 60);
        weather_tip = tr(day_time.night ? "hud.night.tooltip" : "hud.day.tooltip", seconds / 60, s2) + "\n" + weather_tip;
    }
    m.weather_tip = weather_tip;

    m.founded = game.founded(local_player);
    if (!m.founded) {
        return m;
    }
    // Happiness over the town's gold, and where the gold is.
    const std::int32_t joy = game.happiness(town);
    const sim::Game::GoldPlaces places = game.gold_places(town);
    m.happiness = tr("hud.happiness", joy);
    m.unhappy = joy < 35;
    m.gold = tr("hud.gold", game.gold(town));
    m.happiness_tip = tr("hud.happiness.tooltip") + "\n" + tr("hud.gold.tooltip", places.post, places.vaults, places.others);
    // Troubles: the sick over the fires, only when there are some.
    const std::int32_t sick = game.sick(town);
    std::int32_t fires = 0;
    for (const sim::Building& b : game.buildings().data()) {
        fires += b.fire > 0 && b.owner == town ? 1 : 0;
    }
    const std::int32_t raiders = game.raiders_near(town);
    m.raiders = raiders > 0;
    if (m.raiders) {
        m.raiders_text = tr("hud.raiders", raiders);
        m.alarm_text = tr(game.player(town).alarm ? "hud.alarm.on" : "hud.alarm.off");
        m.raiders_tip = tr("hud.raiders.tooltip");
    }
    m.troubles = sick > 0 || fires > 0;
    if (m.troubles) {
        m.sick = tr("hud.sick", sick);
        m.fires = tr("hud.fires", fires);
        m.burning = fires > 0;
        m.troubles_tip = tr("hud.troubles.tooltip");
    }
    const sim::PlayerState& ps = game.player(town);
    m.population = tr("hud.population", game.population(town));
    m.population_tip = tr("hud.population.tooltip", game.population(town, true), ps.births, ps.arrivals, ps.deaths);

    // Goods: food as one total (the kinds in the tooltip), then everything
    // else the town has, and always the logs and the stone.
    const std::vector<std::int32_t> stored = game.stored(town);
    std::int32_t food = 0;
    std::string food_detail;
    for (std::size_t r = 0; r < stored.size(); ++r) {
        if (content.resources[r].category == sim::ResourceCategory::Food) {
            food += stored[r];
            if (stored[r] > 0) {
                food_detail +=
                    (food_detail.empty() ? "" : "\n") + tr("hud.amount", tr(content.resources[r].name_key), stored[r]);
            }
        }
    }
    HudItem f;
    f.id = "food";
    f.text = std::to_string(food);
    f.image = "icon-bread";
    f.sprite = true;
    f.tip = tr("hud.food", food) + "\n" + (food_detail.empty() ? tr("hud.food.tooltip") : food_detail);
    m.goods.push_back(std::move(f));
    for (std::size_t r = 0; r < stored.size(); ++r) {
        const sim::ResourceDef& def = content.resources[r];
        if (def.category == sim::ResourceCategory::Food || def.category == sim::ResourceCategory::Gold ||
            (stored[r] == 0 && def.id != "core:log" && def.id != "core:stone")) {
            continue;
        }
        const std::string full = tr("hud.amount", tr(def.name_key), stored[r]);
        if (m.goods.size() >= kTopBarGoods) {
            ++m.hidden;
            m.hidden_tip += (m.hidden_tip.empty() ? "" : "\n") + full;
            continue;
        }
        HudItem item;
        item.id = def.id;
        item.text = std::to_string(stored[r]);
        item.tip = full;
        good_image(def, !def.pile.empty(), item);
        m.goods.push_back(std::move(item));
    }
    return m;
}

}  // namespace sc
