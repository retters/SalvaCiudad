// The content of the windows of things (phase 124): rows of plain data
// built from the game each frame, with the actions of their buttons, which
// hud_rml_windows.cpp shows in the RmlUi window hud/win/thing.rml. Kept
// apart from RmlUi so the tests can read the texts and press the buttons.
// The texts and the commands are those of the old windows (phases 4 to 116).
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
};

// A button's action; `value` is a slider's new value (else 0).
using RowFn = std::function<void(GameSession&, int value, RowEffects&)>;

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
        Text,     // A line.
        Dim,      // A quieter line.
        Accent,   // A line in the accent color.
        Section,  // A heading inside the window.
        Hero,     // The thing's picture (`image`) with a chip (`text`, `cls`: ok, warn).
        Meter,    // A bar filled to `fraction`.
        Buttons,  // A row of buttons sharing its width.
        Stepper,  // A label (`text`) and its buttons on the right.
        People,   // A list of people, `text` its heading.
        Slider,   // A slider (`value` in `min`..`max` by `step`), `act` on change.
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
    std::string icon;   // The title bar's picture.
    bool gone = false;  // The thing is no more: the rows say so.

    // Helpers to build them.
    int add_act(RowFn fn);
    WinRow& line(std::string text, WinRow::Kind kind = WinRow::Kind::Text);
    RowButton button(std::string label, std::string tip, RowFn fn, bool enabled = true, bool on = false);
    void buttons(std::vector<RowButton> list);
    void stepper(std::string text, RowButton minus, RowButton plus);
};

// The automatic trade rule being edited in a trading post's window, kept
// by the HUD between frames (phase 28).
struct TradeDraft {
    int pick = 0;
    int loaded = -1;
    int sell = -10;
    int buy = -10;
    int sell_min = 70;
    int buy_max = 70;
};

// The rows of a building's window; the button the tutorial points at
// carries its mark ("workers").
[[nodiscard]] ThingRows building_rows(const GameSession& s, sim::EntityId entity, TradeDraft& draft);
// The rows of the window of a thing that is no more.
[[nodiscard]] ThingRows gone_rows(WindowList::Kind kind);

// RML: text made safe to put in a document, and one row as the window shows it.
[[nodiscard]] std::string rml_escape(std::string_view text);
[[nodiscard]] std::string row_rml(const WinRow& row);
// What decides whether a shown row must be rebuilt: its RML, but a slider's
// value is set apart (rebuilding it while dragged would drop the drag).
[[nodiscard]] std::string row_key(const WinRow& row);

}  // namespace sc
