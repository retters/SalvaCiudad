// The game windows as a list (phase 62): where each one is, which are in
// front of which, the windows of the things selected on the map (one
// "passing" window that the next selection takes over, and the pinned ones
// that stay), the groups of docked windows, the windows joined as tabs of
// one (phase 64) and the magnets. No drawing
// here: GameHud draws them and tells this list what the player did.
#pragma once

#include <cstddef>
#include <cstdint>
#include <map>
#include <span>
#include <string>
#include <string_view>
#include <vector>

#include "sim/entity.h"
#include "ui/draw_list.h"

namespace sc {

class WindowList {
public:
    struct Place {
        float x = 0.0f;  // Design units.
        float y = 0.0f;
        float w = 0.0f;  // 0: the window's own width.
        bool placed = false;
        bool pinned = false;
        bool minimized = false;
        int group = 0;  // Docked windows share a group; 0 = alone.
    };
    static constexpr std::size_t kMaxLayoutBytes = 2048;
    static constexpr std::size_t kMaxObjects = 16;

    // The windows' places as text:
    // "id:x,y,w,pinned,group[,minimized[,stack,tab]];...", whole design units
    // (`tab`: twice its place among the tabs, plus one if it is the one showing). Damaged entries are skipped; those of windows
    // that are not kept (the object windows, and the "building" and
    // "villager" windows of before phase 62) are read and dropped.
    void load(std::string_view text);
    // "" when it would not fit or is not plain text.
    [[nodiscard]] std::string save() const;

    [[nodiscard]] Place& place(const std::string& id) { return places_[id]; }
    [[nodiscard]] const std::map<std::string, Place>& places() const { return places_; }

    // --- Depth -----------------------------------------------------------
    // The open windows, from the one at the back to the one in front.
    [[nodiscard]] const std::vector<std::string>& order() const { return order_; }
    // Brings a window to the front (and opens it in the list).
    void raise(const std::string& id);
    [[nodiscard]] bool open(const std::string& id) const;
    // The window in front among those whose rectangle holds the point; ""
    // if none does.
    [[nodiscard]] std::string top_at(const std::map<std::string, ui::Rect>& rects, float x, float y) const;
    // Takes a window out: it leaves its group (a group left with one window
    // is no more), and an object window is forgotten.
    void close(const std::string& id);

    // --- Windows of things on the map ---------------------------------------
    // Node: a natural feature, `entity.index` its place in the map's list.
    enum class Kind : std::uint8_t { Building, Villager, Node, Creature };
    struct Object {
        std::string id;  // "obj1" ... "obj16".
        Kind kind = Kind::Building;
        sim::EntityId entity;
    };
    [[nodiscard]] const std::vector<Object>& objects() const { return objects_; }
    [[nodiscard]] const Object* object(const std::string& id) const;
    [[nodiscard]] static bool is_object_id(std::string_view id);
    // The camera windows ("cam1", "cam2"): like the object windows, their
    // places are of this run only.
    [[nodiscard]] static bool is_camera_id(std::string_view id);
    // The player selected a thing: its own window comes to the front if it
    // has one; else the passing window shows it; else a new passing window
    // opens. Returns the window's id, or "" when there are kMaxObjects
    // windows already, all pinned.
    std::string select(Kind kind, sim::EntityId entity);
    // The object window that is not pinned, if there is one.
    [[nodiscard]] const Object* passing() const;
    // Closes the passing window (Esc, a click on the ground).
    void close_passing();
    // Pins or lets go a window. Letting go an object window makes it the
    // passing one, and the one that was is closed.
    void set_pinned(const std::string& id, bool pinned);
    // Another game: no object windows.
    void clear_objects();

    // --- Tabs (phase 64) -------------------------------------------------
    // Windows joined in a stack share one place: one of them shows and the
    // others are tabs over it. Only the open ones count: a stack with one
    // open window looks like a window alone.
    // The open windows of `id`'s stack, in order; empty unless there are
    // at least two.
    [[nodiscard]] std::vector<std::string> tabs(const std::string& id) const;
    // Whether `id` is behind another tab of its stack (it is not drawn).
    [[nodiscard]] bool hidden(const std::string& id) const;
    // `id` (with the stack it was in) joins `onto`'s stack, takes its place
    // and group, and shows. raise() shows a tab.
    void merge(const std::string& id, const std::string& onto);
    // `id` leaves its stack and its group; it keeps its place.
    void split(const std::string& id);
    // The other windows of `id`'s stack take its place and width.
    void sync_stack(const std::string& id);

    // --- Groups ----------------------------------------------------------
    // `id` was dropped touching `other`: they move together from now on.
    void dock(const std::string& id, const std::string& other);
    void leave_group(const std::string& id);

    // --- Magnets ---------------------------------------------------------
    struct Area {
        float width = 0.0f;   // The screen.
        float height = 0.0f;
        float top = 0.0f;     // Under the top bar.
        float bottom = 0.0f;  // The build bar's top; 0: there is none.
    };
    // Pulls `box` (being dragged) to the edges of the area and of the other
    // windows when it is within `snap` of them: side by side, stacked, or
    // with equal edges in line.
    static void magnets(ui::Rect& box, std::span<const ui::Rect> others, const Area& area, float snap);
    // Whether two windows touch along an edge (so they dock when dropped).
    [[nodiscard]] static bool touching(const ui::Rect& a, const ui::Rect& b);

private:
    std::map<std::string, Place> places_;
    std::vector<std::string> order_;
    std::vector<Object> objects_;
    int next_group_ = 1;
    struct Stack {
        std::vector<std::string> ids;
        std::string shown;
    };
    std::vector<Stack> stacks_;
    [[nodiscard]] const Stack* stack_of(const std::string& id) const;
    [[nodiscard]] Stack* stack_of(const std::string& id);
    // The window of a stack that shows: the chosen one, or the first open.
    [[nodiscard]] std::string shown_of(const Stack& stack) const;
    void drop_small_stacks();
};

}  // namespace sc
