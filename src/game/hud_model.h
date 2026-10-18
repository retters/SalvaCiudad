// What the player's HUD shows, as plain data (phase 121): built from the
// game each frame and handed to the RmlUi documents of the HUD (data/ui/hud)
// as their data models. Kept apart from RmlUi so the tests can check the
// texts. The texts are the same as those of the old HUD (phases 4 to 116).
#pragma once

#include <cstdint>
#include <string>
#include <vector>

#include "sim/game.h"

namespace sc {

// One thing the bar counts: a good, the food, the people.
struct HudItem {
    std::string id;
    std::string text;
    std::string image;    // A sprite ("icon-log") or a picture path ("/thumbs/resource/core/fish").
    bool sprite = false;  // `image` is a sprite.
    std::string tip;      // Tooltip; lines separated by '\n'.
    bool operator==(const HudItem&) const = default;
};

struct HudNetInfo {
    bool networked = false;
    int connected = 0;
    std::string names;  // One per line, as the tooltip shows them.
};

struct TopBarModel {
    bool founded = false;  // Phase 74: before, no goods or people to count.
    std::vector<HudItem> goods;     // Food first, then every other good the town has.
    int hidden = 0;                 // Goods that did not fit: "+N".
    std::string hidden_tip;
    std::string population;
    std::string population_tip;
    std::string happiness;
    std::string gold;
    std::string happiness_tip;
    bool unhappy = false;
    bool troubles = false;          // Somebody sick or something burning.
    std::string sick;
    std::string fires;
    bool burning = false;
    std::string troubles_tip;
    bool raiders = false;
    std::string raiders_text;
    std::string alarm_text;
    std::string raiders_tip;
    std::string weather;            // Day or night, rain or snow, season and temperature.
    std::string date;
    std::string weather_tip;
    std::string weather_icon;       // A sprite: icon-sun, icon-moon, icon-rain or icon-snow.
    bool cold = false;
    std::string speed;              // "x2"
    bool paused = false;
    bool can_slower = false;
    bool can_faster = false;
    bool networked = false;
    std::string players;
    std::string players_tip;
    bool operator==(const TopBarModel&) const = default;
};

inline constexpr std::size_t kTopBarGoods = 12;  // More go into "+N".

// `speed`: the game's speed now; `shown_speed`: the last one that was not
// the pause; `max_speed`: the fastest allowed.
[[nodiscard]] TopBarModel top_bar_model(const sim::Game& game, std::uint8_t town, std::uint8_t local_player, int speed,
                                        int shown_speed, int max_speed, const HudNetInfo& net);

// The image of a good: its pile's picture if it has a model, else an icon.
void good_image(const sim::ResourceDef& def, bool has_model, HudItem& item);

struct DockEntry {
    std::string id;
    std::string label;
    std::string tip;
    std::string icon;  // Sprite.
    std::string mark;  // What the tutorial calls it: "dock:<id>".
    bool open = false;
    bool operator==(const DockEntry&) const = default;
};

// The build bar (phase 122): the categories, and the buildings of the one
// shown with their picture and cost.
struct BuildCat {
    int index = 0;
    std::string name;
    std::string icon;  // Sprite.
    std::string mark;  // The tutorial's key when it points here, else empty.
    bool on = false;
    bool operator==(const BuildCat&) const = default;
};

struct BuildItem {
    std::string id;     // "core:house"
    std::string name;
    std::string image;  // Its thumbnail.
    std::vector<HudItem> cost;
    std::string tip;    // Name, cost, size, workers... as the old bar's tooltip.
    std::string lock;   // "Level 2" when locked, else empty.
    std::string mark;   // "build:<id>"
    bool on = false;    // Being placed.
    bool operator==(const BuildItem&) const = default;
};

struct BuildBarModel {
    std::vector<BuildCat> cats;
    std::vector<BuildItem> items;
    bool operator==(const BuildBarModel&) const = default;
};

inline constexpr std::size_t kBuildCategories = 12;

// `highlight`: what the tutorial points at ("build:<id>" marks the building
// and, while another category is shown, its category).
[[nodiscard]] BuildBarModel build_bar_model(const sim::Game& game, std::uint8_t town, std::uint8_t category,
                                            sim::DefIndex placing, const std::string& highlight);

struct HudNote {
    std::string text;
    std::string tip;  // "Go there" when it has a place.
    bool has_pos = false;
    bool operator==(const HudNote&) const = default;
};

}  // namespace sc
