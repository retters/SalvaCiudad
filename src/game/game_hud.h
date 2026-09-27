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
    void placement_hint(ui::Context& ctx, GameSession& s);
    [[nodiscard]] bool pressed(const ui::Context& ctx, Action action) const;
    void block(GameSession& s, const ui::Rect& r);
    [[nodiscard]] std::string cost_text(const sim::BuildingDef& def) const;

    Services& services_;
};

}  // namespace sc
