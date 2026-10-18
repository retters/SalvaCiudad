// The content of the windows of things (phase 124) and of the other game
// windows and panels (phase 125): rows of plain data built from the game
// each frame, with the actions of their buttons, which hud_rml_windows.cpp
// shows in RmlUi (hud/win/thing.rml, hud/panel.rml). Kept apart from RmlUi
// so the tests can read the texts and press the buttons. The texts and the
// commands are those of the old windows (phases 4 to 116).
#pragma once

#include <cstdint>
#include <functional>
#include <string>
#include <string_view>
#include <vector>

#include "game/window_list.h"
#include "sim/game.h"

namespace sc {

class GameSession;

// What a pressed button asks of the HUD besides its command.
struct RowEffects {
    bool close = false;  // The window goes (the building was demolished).
    bool link = false;   // The thing below becomes the selection; the window stays.
    WindowList::Kind kind = WindowList::Kind::Villager;
    sim::EntityId entity;
    bool focus = false;  // The camera goes to (x, z).
    float x = 0.0f;
    float z = 0.0f;
};

// What came with the press: a slider's new value, a text field's text and
// whether Enter was pressed in it.
struct RowInput {
    int value = 0;
    std::string text;
    bool enter = false;
};

using RowFn = std::function<void(GameSession&, const RowInput&, RowEffects&)>;

struct RowButton {
    std::string label;
    std::string icon;  // A sprite shown before the label ("icon-x"); may be alone.
    std::string tip;
    std::string mark;  // The tutorial's key ("workers").
    bool on = false;
    bool enabled = true;
    bool danger = false;
    int act = -1;      // Index into ThingRows::acts.
};

struct RowPerson {
    std::string image;  // Its portrait ("/thumbs/person/...").
    std::string name;
    std::string sub;    // What it is doing.
    int act = -1;
};

struct WinRow {
    enum class Kind : std::uint8_t {
        Text,     // A line; `cls` may color it (bad, night).
        Dim,      // A quieter line.
        Accent,   // A line in the accent color.
        Section,  // A heading inside the window.
        Hero,     // The thing's picture (`image`) with a chip (`text`, `cls`: ok, warn).
        Meter,    // A bar filled to `fraction`, `cls` its color (bad, food, warm, health, energy).
        Buttons,  // A row of buttons sharing its width.
        Stepper,  // A label (`text`) and its buttons on the right.
        People,   // A list of people, `text` its heading.
        Slider,   // A slider (`value` in `min`..`max` by `step`), `act` on change.
        Input,    // A text field holding `text`, at most `max` bytes, `act` on each change.
        Title,    // A panel's title.
        Paragraph,  // Text that wraps, as long as it is.
        Raw,      // RML made by the code (escaped there): the trade window's world map.
    };
    Kind kind = Kind::Text;
    std::string text;
    std::string tip;
    std::string image;
    std::string cls;
    float fraction = 0.0f;
    std::vector<RowButton> buttons;
    std::vector<RowPerson> people;
    int value = 0;
    int min = 0;
    int max = 0;
    int step = 1;
    bool enabled = true;
    int act = -1;
};

struct ThingRows {
    std::vector<WinRow> rows;
    std::vector<RowFn> acts;
    std::string icon;   // The title bar's picture, or a sprite when `icon_sprite`.
    bool icon_sprite = false;
    bool gone = false;  // The thing is no more: the rows say so.

    // Helpers to build them.
    int add_act(RowFn fn);
    WinRow& line(std::string text, WinRow::Kind kind = WinRow::Kind::Text);
    RowButton button(std::string label, std::string tip, RowFn fn, bool enabled = true, bool on = false);
    void buttons(std::vector<RowButton> list);
    void stepper(std::string text, RowButton minus, RowButton plus);
    // A choice among `count` options shown as `text` with arrows; `pick`
    // is where the choice is kept (it must outlive the rows).
    void choice(std::string text, int* pick, int count);
    // A slider of `*field` with its text above.
    void slider(std::string text, std::string tip, int* field, int lo, int hi, int step, bool enabled = true);
};

// The automatic trade rule being edited in a trading post's window (phase 28).
struct TradeDraft {
    int pick = 0;
    int loaded = -1;
    int sell = -10;
    int buy = -10;
    int sell_min = 70;
    int buy_max = 70;
};

// A trade offer to another town being written (phase 14).
struct OfferDraft {
    int to = 0;
    int give = 0;
    int give_amount = 20;
    int want = 1;
    int want_amount = 20;
};

// What the windows keep between frames.
struct ThingState {
    TradeDraft trade;
    OfferDraft offer;
    int attack_pick = 0;
    std::string rename_id;  // The window whose villager is being renamed.
    std::string rename_text;
};

// A town's name as the HUD shows it.
using TownNames = std::function<std::string(std::uint8_t)>;

// The rows of a building's window; the button the tutorial points at
// carries its mark ("workers").
[[nodiscard]] ThingRows building_rows(const GameSession& s, sim::EntityId entity, ThingState& state);
// Phase 125: a villager's (`id`: its window, for the renaming), a natural
// feature's (`entity.index`), an animal's or a soldier's, and one of the
// developer tools' people (`entity.index`).
[[nodiscard]] ThingRows villager_rows(const GameSession& s, const std::string& id, sim::EntityId entity, ThingState& state);
[[nodiscard]] ThingRows node_rows(const GameSession& s, sim::EntityId entity);
[[nodiscard]] ThingRows creature_rows(const GameSession& s, sim::EntityId entity, const TownNames& names);
[[nodiscard]] ThingRows walker_rows(const GameSession& s, sim::EntityId entity);
[[nodiscard]] ThingRows thing_rows(const GameSession& s, const std::string& id, WindowList::Kind kind, sim::EntityId entity,
                                   ThingState& state, const TownNames& names);
// The rows of the window of a thing that is no more.
[[nodiscard]] ThingRows gone_rows(WindowList::Kind kind);
// Phase 125: the trade window (empty rows: no other town to trade with) and the army's.
[[nodiscard]] ThingRows trade_rows(const GameSession& s, ThingState& state, const TownNames& names);
[[nodiscard]] ThingRows army_rows(const GameSession& s, ThingState& state, const TownNames& names);

// Where a thing is, for the eye of its window; false if it is no more.
[[nodiscard]] bool thing_place(const GameSession& s, WindowList::Kind kind, sim::EntityId entity, float& x, float& z);
// Whether a natural feature is still there to look at: not felled or dug
// out (a picked bush that grows back is).
[[nodiscard]] bool node_there(const sim::Game& game, std::uint32_t index);
// Text keys of a feature, a creature and what a creature is doing.
[[nodiscard]] const char* feature_name_key(sim::FeatureType type);
[[nodiscard]] const char* creature_name_key(sim::CreatureKind kind);
[[nodiscard]] const char* creature_state_key(sim::CreatureState state);

// RML: text made safe to put in a document, and one row as the window shows it.
[[nodiscard]] std::string rml_escape(std::string_view text);
[[nodiscard]] std::string row_rml(const WinRow& row);
// What decides whether a shown row must be rebuilt: its RML, but a slider's
// value and a text field's text are set apart (rebuilding them while used
// would drop the drag or the typing).
[[nodiscard]] std::string row_key(const WinRow& row);

}  // namespace sc
