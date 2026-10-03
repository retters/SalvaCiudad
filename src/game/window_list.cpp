#include "game/window_list.h"

#include <algorithm>
#include <charconv>
#include <cmath>
#include <utility>

namespace sc {

namespace {

bool valid_layout_char(char c) {
    return (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == ':' || c == ',' || c == ';' || c == '-' || c == '_';
}

// Windows whose place is not remembered between runs.
bool kept(std::string_view id) {
    return !WindowList::is_object_id(id) && !WindowList::is_camera_id(id) && id != "building" && id != "villager";
}

}  // namespace

void WindowList::load(std::string_view text) {
    std::vector<std::vector<std::pair<int, std::string>>> read;  // By stack: tab value and window.
    std::size_t at = 0;
    while (at < text.size()) {
        const std::size_t end = std::min(text.find(';', at), text.size());
        const std::string_view entry = text.substr(at, end - at);
        at = end + 1;
        const std::size_t colon = entry.find(':');
        if (colon == std::string_view::npos || colon == 0 || colon > 16) {
            continue;
        }
        const std::string_view id = entry.substr(0, colon);
        if (!std::all_of(id.begin(), id.end(), valid_layout_char)) {
            continue;
        }
        int values[8] = {0, 0, 0, 0, 0, 0, 0, 0};
        std::size_t p = colon + 1;
        int n = 0;
        for (; n < 8 && p <= entry.size(); ++n) {
            const std::size_t comma = std::min(entry.find(',', p), entry.size());
            const auto r = std::from_chars(entry.data() + p, entry.data() + comma, values[n]);
            if (r.ec != std::errc{} || r.ptr != entry.data() + comma) {
                break;
            }
            p = comma + 1;
        }
        // Five values before phase 62; six with "minimized"; eight with the tabs.
        if ((n != 5 && n != 6 && n != 8) || p <= entry.size() || values[0] < 0 || values[1] < 0 || values[0] > 20000 ||
            values[1] > 20000 || values[2] < 0 || values[2] > 2000 || values[3] < 0 || values[3] > 1 || values[4] < 0 ||
            values[4] > 1000 || values[5] < 0 || values[5] > 1 || values[6] < 0 || values[6] > 64 || values[7] < 0 ||
            values[7] > 255) {
            continue;  // A damaged entry: that window goes back to its place.
        }
        if (!kept(id)) {
            continue;
        }
        Place& w = places_[std::string(id)];
        w.x = static_cast<float>(values[0]);
        w.y = static_cast<float>(values[1]);
        w.w = static_cast<float>(values[2]);
        w.placed = true;
        w.pinned = values[3] == 1;
        w.group = values[4];
        w.minimized = values[5] == 1;
        if (values[6] > 0) {
            // Its stack, by number, and its tab: twice its place among
            // the tabs, plus one for the tab that shows.
            const auto number = static_cast<std::size_t>(values[6]);
            if (read.size() < number) {
                read.resize(number);
            }
            read[number - 1].push_back({values[7], std::string(id)});
        }
    }
    for (std::vector<std::pair<int, std::string>>& tabs : read) {
        if (tabs.size() < 2) {
            continue;
        }
        std::stable_sort(tabs.begin(), tabs.end(), [](const auto& a, const auto& b) { return a.first / 2 < b.first / 2; });
        Stack stack;
        for (const auto& [tab, name] : tabs) {
            stack.ids.push_back(name);
            if ((tab & 1) != 0) {
                stack.shown = name;
            }
        }
        if (stack.shown.empty()) {
            stack.shown = stack.ids.front();
        }
        stacks_.push_back(std::move(stack));
    }
    // A group needs two windows; new groups take numbers after the read ones.
    std::map<int, int> members;
    for (const auto& [id, w] : places_) {
        ++members[w.group];
    }
    next_group_ = 1;
    for (auto& [id, w] : places_) {
        if (w.group != 0 && members[w.group] < 2) {
            w.group = 0;
        }
        next_group_ = std::max(next_group_, w.group + 1);
    }
}

std::string WindowList::save() const {
    std::string text;
    for (const auto& [id, w] : places_) {
        if (!kept(id) || (!w.placed && !w.pinned)) {
            continue;
        }
        // Groups with object windows are of this run only.
        int group = w.group;
        if (group != 0) {
            int members = 0;
            for (const auto& [other, o] : places_) {
                members += kept(other) && o.group == group ? 1 : 0;
            }
            group = members >= 2 ? group : 0;
        }
        // Its stack, numbered among those with two windows that are kept.
        int stack_number = 0;
        int tab = 0;
        int number = 0;
        for (const Stack& stack : stacks_) {
            const auto members = std::count_if(stack.ids.begin(), stack.ids.end(), [](const std::string& m) { return kept(m); });
            if (members < 2) {
                continue;
            }
            ++number;
            if (const auto at = std::find(stack.ids.begin(), stack.ids.end(), id); at != stack.ids.end()) {
                stack_number = number;
                tab = static_cast<int>(at - stack.ids.begin()) * 2 + (stack.shown == id ? 1 : 0);
            }
        }
        text += id + ":" + std::to_string(static_cast<int>(std::lround(w.x))) + "," +
                std::to_string(static_cast<int>(std::lround(w.y))) + "," +
                std::to_string(static_cast<int>(std::lround(w.w))) + "," + (w.pinned ? "1" : "0") + "," +
                std::to_string(group) + "," + (w.minimized ? "1" : "0") + "," + std::to_string(stack_number) + "," +
                std::to_string(tab) + ";";
    }
    if (text.size() > kMaxLayoutBytes || !std::all_of(text.begin(), text.end(), valid_layout_char)) {
        return {};
    }
    return text;
}

void WindowList::raise(const std::string& id) {
    std::erase(order_, id);
    order_.push_back(id);
    if (Stack* stack = stack_of(id)) {
        stack->shown = id;  // Its tab comes forward too.
    }
}

bool WindowList::open(const std::string& id) const {
    return std::find(order_.begin(), order_.end(), id) != order_.end();
}

std::string WindowList::top_at(const std::map<std::string, ui::Rect>& rects, float x, float y) const {
    for (std::size_t k = order_.size(); k-- > 0;) {
        const auto it = rects.find(order_[k]);
        if (it != rects.end() && it->second.contains(x, y)) {
            return order_[k];
        }
    }
    return {};
}

void WindowList::close(const std::string& id) {
    std::erase(order_, id);
    if (!kept(id)) {
        split(id);  // A window of this run only: it will not come back to its tab.
    } else if (stack_of(id) == nullptr) {
        leave_group(id);
    }
    if (is_object_id(id)) {
        std::erase_if(objects_, [&](const Object& o) { return o.id == id; });
        places_.erase(id);
    } else if (is_camera_id(id)) {
        places_.erase(id);
    }
}

const WindowList::Stack* WindowList::stack_of(const std::string& id) const {
    for (const Stack& stack : stacks_) {
        if (std::find(stack.ids.begin(), stack.ids.end(), id) != stack.ids.end()) {
            return &stack;
        }
    }
    return nullptr;
}

WindowList::Stack* WindowList::stack_of(const std::string& id) {
    return const_cast<Stack*>(std::as_const(*this).stack_of(id));
}

std::string WindowList::shown_of(const Stack& stack) const {
    if (open(stack.shown)) {
        return stack.shown;
    }
    for (const std::string& id : stack.ids) {
        if (open(id)) {
            return id;
        }
    }
    return {};
}

std::vector<std::string> WindowList::tabs(const std::string& id) const {
    std::vector<std::string> out;
    if (const Stack* stack = stack_of(id)) {
        for (const std::string& member : stack->ids) {
            if (open(member)) {
                out.push_back(member);
            }
        }
    }
    if (out.size() < 2) {
        out.clear();
    }
    return out;
}

bool WindowList::hidden(const std::string& id) const {
    const Stack* stack = stack_of(id);
    return stack != nullptr && shown_of(*stack) != id;
}

void WindowList::drop_small_stacks() {
    std::erase_if(stacks_, [](const Stack& stack) { return stack.ids.size() < 2; });
}

void WindowList::merge(const std::string& id, const std::string& onto) {
    if (id == onto) {
        return;
    }
    const Stack* mine = stack_of(id);
    if (mine != nullptr && mine == stack_of(onto)) {
        return;  // Tabs of the same window already.
    }
    // What moves: the window, or the whole stack it shows for.
    std::vector<std::string> moving = mine != nullptr ? mine->ids : std::vector<std::string>{id};
    if (mine != nullptr) {
        std::erase_if(stacks_, [&](const Stack& stack) { return &stack == mine; });
    }
    if (stack_of(onto) == nullptr) {
        stacks_.push_back({{onto}, onto});
    }
    Stack* target = stack_of(onto);
    const Place where = places_[onto];
    for (const std::string& member : moving) {
        leave_group(member);
        Place& p = places_[member];
        p.x = where.x;
        p.y = where.y;
        p.w = where.w;
        p.placed = where.placed;
        p.group = where.group;
        target->ids.push_back(member);
    }
    target->shown = id;
    raise(id);
}

void WindowList::split(const std::string& id) {
    Stack* stack = stack_of(id);
    if (stack == nullptr) {
        leave_group(id);
        return;
    }
    const auto at = std::find(stack->ids.begin(), stack->ids.end(), id);
    const bool was_shown = stack->shown == id;
    const auto next = stack->ids.erase(at);
    if (was_shown && !stack->ids.empty()) {
        // The tab beside it shows now.
        stack->shown = next != stack->ids.begin() ? *(next - 1) : stack->ids.front();
    }
    // Out of the group too; the others of the stack stay in it.
    const auto it = places_.find(id);
    if (it != places_.end()) {
        it->second.group = 0;
    }
    drop_small_stacks();
}

void WindowList::sync_stack(const std::string& id) {
    const Stack* stack = stack_of(id);
    if (stack == nullptr) {
        return;
    }
    const Place where = places_[id];
    for (const std::string& member : stack->ids) {
        if (member != id) {
            Place& p = places_[member];
            p.x = where.x;
            p.y = where.y;
            p.w = where.w;
            p.placed = where.placed;
            p.group = where.group;
        }
    }
}

bool WindowList::is_object_id(std::string_view id) {
    return id.size() > 3 && id.substr(0, 3) == "obj";
}

bool WindowList::is_camera_id(std::string_view id) {
    return id.size() > 3 && id.substr(0, 3) == "cam";
}

const WindowList::Object* WindowList::object(const std::string& id) const {
    for (const Object& o : objects_) {
        if (o.id == id) {
            return &o;
        }
    }
    return nullptr;
}

const WindowList::Object* WindowList::passing() const {
    for (const Object& o : objects_) {
        const auto it = places_.find(o.id);
        if (it == places_.end() || !it->second.pinned) {
            return &o;
        }
    }
    return nullptr;
}

std::string WindowList::select(Kind kind, sim::EntityId entity) {
    for (const Object& o : objects_) {
        if (o.kind == kind && o.entity == entity) {
            raise(o.id);
            return o.id;
        }
    }
    for (Object& o : objects_) {
        if (!places_[o.id].pinned) {
            o.kind = kind;
            o.entity = entity;
            places_[o.id].minimized = false;
            raise(o.id);
            return o.id;
        }
    }
    if (objects_.size() >= kMaxObjects) {
        return {};
    }
    // The lowest number not in use.
    for (std::size_t n = 1; n <= kMaxObjects; ++n) {
        const std::string id = "obj" + std::to_string(n);
        if (object(id) == nullptr) {
            places_[id] = Place{};
            objects_.push_back({id, kind, entity});
            raise(id);
            return id;
        }
    }
    return {};
}

void WindowList::close_passing() {
    if (const Object* o = passing()) {
        const std::string id = o->id;
        close(id);
    }
}

void WindowList::set_pinned(const std::string& id, bool pinned) {
    if (!pinned && is_object_id(id)) {
        // Only one passing window: the one that was goes.
        if (const Object* o = passing(); o != nullptr && o->id != id) {
            const std::string other = o->id;
            close(other);
        }
    }
    places_[id].pinned = pinned;
}

void WindowList::clear_objects() {
    while (!objects_.empty()) {
        const std::string id = objects_.back().id;
        close(id);
    }
}

void WindowList::dock(const std::string& id, const std::string& other) {
    if (id == other) {
        return;
    }
    Place& o = places_[other];
    if (o.group == 0) {
        o.group = next_group_++;
    }
    const int old = places_[id].group;
    places_[id].group = o.group;
    // What it leaves behind may no longer be a group.
    if (old != 0 && old != o.group) {
        int members = 0;
        for (const auto& [name, w] : places_) {
            members += w.group == old ? 1 : 0;
        }
        if (members < 2) {
            for (auto& [name, w] : places_) {
                w.group = w.group == old ? 0 : w.group;
            }
        }
    }
}

void WindowList::leave_group(const std::string& id) {
    const auto it = places_.find(id);
    if (it == places_.end() || it->second.group == 0) {
        return;
    }
    const int group = it->second.group;
    it->second.group = 0;
    int members = 0;
    for (const auto& [name, w] : places_) {
        members += w.group == group ? 1 : 0;
    }
    if (members < 2) {
        for (auto& [name, w] : places_) {
            w.group = w.group == group ? 0 : w.group;
        }
    }
}

void WindowList::magnets(ui::Rect& box, std::span<const ui::Rect> others, const Area& area, float snap) {
    float x = box.x;
    float y = box.y;
    const auto pull = [&](float& v, float target) {
        if (std::abs(v - target) < snap) {
            v = target;
        }
    };
    // The other windows first, then the screen: the screen wins.
    for (const ui::Rect& r : others) {
        const bool rows = y < r.bottom() + snap && y + box.h > r.y - snap;
        const bool cols = x < r.right() + snap && x + box.w > r.x - snap;
        if (rows) {
            pull(x, r.right());          // Side by side.
            pull(x, r.x - box.w);
            pull(x, r.x);                // Equal edges in line.
            pull(x, r.right() - box.w);
        }
        if (cols) {
            pull(y, r.bottom());         // Stacked.
            pull(y, r.y - box.h);
            pull(y, r.y);
            pull(y, r.bottom() - box.h);
        }
    }
    pull(x, 0.0f);
    pull(x, area.width - box.w);
    pull(y, area.height - box.h);
    if (area.bottom > 0.0f) {
        pull(y, area.bottom - box.h);
    }
    pull(y, area.top);
    box.x = x;
    box.y = y;
}

bool WindowList::touching(const ui::Rect& a, const ui::Rect& b) {
    const bool side = (std::abs(a.x - b.right()) < 1.0f || std::abs(a.right() - b.x) < 1.0f) && a.y < b.bottom() &&
                      a.bottom() > b.y;
    const bool stack = (std::abs(a.y - b.bottom()) < 1.0f || std::abs(a.bottom() - b.y) < 1.0f) && a.x < b.right() &&
                       a.right() > b.x;
    return side || stack;
}

}  // namespace sc
