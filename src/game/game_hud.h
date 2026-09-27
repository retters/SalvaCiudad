// The interface of a village game (section 6.4, phase 8 part): the top bar
// with goods, population, date and speed; the build bar; and the windows
// of the selected building or villager (docking and snapping come in
// phase 17).
#pragma once

#include <cstdint>
#include <string>

#include "game/services.h"
#include "ui/context.h"

namespace sc {

// Text key of a need (sim::Need).
[[nodiscard]] const char* need_text_key(std::uint8_t need);
// Text keys of the villagers' tasks, by sim::Task.
[[nodiscard]] const char* task_text_key(sim::Task task);
// "Year 2, month 3, day 4" parts from a tick.
struct GameDate {
    std::int32_t year = 1;
    std::int32_t month = 1;
    std::int32_t day = 1;
};
[[nodiscard]] GameDate game_date(std::uint64_t tick);

class GameHud {
public:
    explicit GameHud(Services& services) : services_(services) {}

    // Draws the interface. `blocked`: a menu is open over it (no input).
    // Returns true when Esc should open the game menu (nothing else
    // wanted it: no building being placed, nothing selected).
    bool frame(ui::Context& ctx, bool blocked);

private:
    void top_bar(ui::Context& ctx, GameSession& s);
    void build_bar(ui::Context& ctx, GameSession& s);
    void building_window(ui::Context& ctx, GameSession& s);
    void villager_window(ui::Context& ctx, GameSession& s);
    void farm_fields(ui::Context& ctx, GameSession& s, const sim::Building& b, const ui::Rect& box, float& y,
                     float row_h);
    void placement_hint(ui::Context& ctx, GameSession& s);
    // Phase 14: the merchant at a trading post, and trade with other towns.
    [[nodiscard]] std::vector<sim::DefIndex> merchant_rows(const sim::Game& game, std::uint8_t town) const;
    void merchant_section(ui::Context& ctx, GameSession& s, const ui::Rect& box, float& y, float row_h);
    void trade_window(ui::Context& ctx, GameSession& s);
    // Phase 16: the barracks and the army.
    void barracks_section(ui::Context& ctx, GameSession& s, const sim::Building& b, const ui::Rect& box, float& y,
                          float row_h);
    void army_window(ui::Context& ctx, GameSession& s);
    bool army_open_ = false;
    int attack_pick_ = 0;
    [[nodiscard]] std::string town_name(std::uint8_t player) const;
    [[nodiscard]] std::string goods_name(const sim::Game& game, sim::DefIndex r) const;
    bool trade_open_ = false;
    int offer_to_ = 0;
    int offer_give_ = 0;
    int offer_give_amount_ = 20;
    int offer_want_ = 1;
    int offer_want_amount_ = 20;
    // Multiplayer: who plays, whom the game waits for, speed votes.
    void network(ui::Context& ctx, GameSession& s, float& right);
    std::uint32_t answered_vote_ = 0;
    std::uint8_t category_ = 0;  // Build bar group shown.
    void house_lines(const sim::Game& game, const sim::Building& b, std::vector<std::string>& lines) const;
    [[nodiscard]] bool pressed(const ui::Context& ctx, Action action) const;
    void block(GameSession& s, const ui::Rect& r);
    [[nodiscard]] std::string cost_text(const sim::BuildingDef& def) const;

    Services& services_;
};

}  // namespace sc
