// The interface of a village game (section 6.4): the top bar with goods,
// population, date and speed; the build bar; the launcher on the left; the
// game windows, which move, snap, dock, collapse to tabs and are remembered
// (hud_windows.cpp); and the notifications.
#pragma once

#include <cstdint>
#include <map>
#include <set>
#include <string>
#include <vector>

#include "game/services.h"
#include "ui/context.h"

namespace sc {

// A speed as text: "0.25", "0.5", "1" ... "9" (the decimal mark by language).
[[nodiscard]] std::string speed_text(int quarters);

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

    // A notification: shown for a while above the build bar and kept in the
    // event log; with a place, a click takes the camera there.
    void notify(std::string text, bool has_pos, float x, float z, const sim::Calendar& when, std::uint64_t now_ns);
    // The tutorial: the element to point at ("build:<id>", "tab:<n>",
    // "workers", "speed", "dock:<id>"; empty for none).
    void set_highlight(std::string key) { highlight_ = std::move(key); }
    // Top of the build bar last frame (for panels that sit above it).
    [[nodiscard]] float build_bar_top() const { return build_bar_top_; }

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
    // Automatic trade rules of the trading post (phase 29), and its height.
    [[nodiscard]] float auto_trade_height(ui::Context& ctx, const sim::Game& game, std::uint8_t town, float row_h) const;
    void auto_trade_section(ui::Context& ctx, GameSession& s, const ui::Rect& box, float& y, float row_h);
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
    // The rule being edited in the trading post's window: which good, and
    // its "sell over" and "buy under" (kNoRule: off); `rule_loaded_` is the
    // good they were read for.
    int rule_pick_ = 0;
    int rule_loaded_ = -1;
    int rule_sell_ = -10;
    int rule_buy_ = -10;
    int offer_give_amount_ = 20;
    int offer_want_ = 1;
    int offer_want_amount_ = 20;
    // Multiplayer: who plays, whom the game waits for, speed votes.
    void network(ui::Context& ctx, GameSession& s, float& right);
    int shown_speed_ = 4;  // The last speed that was not the pause (quarters).
    std::uint32_t answered_vote_ = 0;
    std::uint8_t category_ = 0;  // Build bar group shown.
    void house_lines(const sim::Game& game, const sim::Building& b, std::vector<std::string>& lines) const;
    [[nodiscard]] bool pressed(const ui::Context& ctx, Action action) const;
    void block(GameSession& s, const ui::Rect& r);
    [[nodiscard]] std::string cost_text(const sim::BuildingDef& def) const;

    // Phase 17: the windows (hud_windows.cpp).
    struct WindowPlace {
        float x = 0.0f;  // Design units.
        float y = 0.0f;
        float w = 0.0f;  // 0: the window's own width.
        bool placed = false;
        bool pinned = false;
        int group = 0;   // Docked windows share a group; 0 = alone.
    };
    static constexpr std::size_t kMaxLayoutBytes = 2048;
    std::map<std::string, WindowPlace> places_;
    bool places_loaded_ = false;
    std::string focus_;
    std::string dragging_;
    bool resizing_ = false;
    float grab_x_ = 0.0f;
    float grab_y_ = 0.0f;
    int next_group_ = 1;
    std::map<std::string, ui::Rect> shown_;       // Drawn this frame.
    std::map<std::string, ui::Rect> shown_last_;  // Drawn last frame (for the magnets).
    std::map<std::string, std::uint64_t> seen_ns_;
    std::set<std::string> opened_;                // Opened by the player this frame: they take the focus.
    void load_places();
    void save_places();
    void windows_begin(ui::Context& ctx);
    void windows_end(ui::Context& ctx);
    // Draws a window's frame, title, pin and close; `box` comes in with the
    // default place and size and goes out where the player put it. False
    // when it is collapsed to a tab or was closed (`open` becomes false).
    bool window(ui::Context& ctx, GameSession& s, const std::string& id, const std::string& title, ui::Rect& box,
                bool& open);
    void open_window(const std::string& id);
    [[nodiscard]] float left_x(ui::Context& ctx) const;
    void dock(ui::Context& ctx, GameSession& s);
    void goods_window(ui::Context& ctx, GameSession& s);
    void stats_window(ui::Context& ctx, GameSession& s);
    void log_window(ui::Context& ctx, GameSession& s);
    void layers_window(ui::Context& ctx, GameSession& s);
    bool goods_open_ = false;
    bool stats_open_ = false;
    bool log_open_ = false;
    bool layers_open_ = false;
    sim::EntityId last_building_;
    sim::EntityId last_villager_;
    struct Note {
        std::string text;
        bool has_pos = false;
        float x = 0.0f;
        float z = 0.0f;
        std::uint64_t at_ns = 0;
        int count = 1;
        int year = 1;
        int month = 1;
        int day = 1;
    };
    std::vector<Note> notes_;
    void notifications(ui::Context& ctx, GameSession& s, float bottom);
    float build_bar_top_ = 0.0f;
    std::string highlight_;
    // A pulsing outline around a highlighted element.
    void mark(ui::Context& ctx, const ui::Rect& r) const;

    // Phase 24: the minimap, with the four cardinal points, and the compass
    // (hud_minimap.cpp).
    void minimap(ui::Context& ctx, GameSession& s, bool blocked);
    void compass(ui::Context& ctx, const ui::Rect& box, float yaw);
    const GameSession* minimap_session_ = nullptr;  // Whose map the image shows.
    sim::MapSettings minimap_settings_;
    // Phase 32: the map's image without fog, and the fog it was last drawn
    // with (the view's generation and revision, and when).
    std::vector<std::uint8_t> minimap_base_;
    std::uint32_t minimap_fog_generation_ = 0;
    std::uint32_t minimap_fog_revision_ = 0;
    int minimap_fog_mode_ = -1;
    std::uint64_t minimap_fog_ns_ = 0;
    bool minimap_dragging_ = false;
    float top_bar_bottom_ = 0.0f;
    float right_top_ = 0.0f;  // Below the minimap: where windows on the right start.

    Services& services_;
};

}  // namespace sc
