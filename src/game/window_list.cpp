#include "game/window_list.h"

#include <algorithm>
#include <charconv>
#include <cmath>

namespace sc {

namespace {

bool valid_layout_char(char c) {
    return (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == ':' || c == ',' || c == ';' || c == '-' || c == '_';
}

// Windows whose place is not remembered between runs.
bool kept(std::string_view id) {
    return !WindowList::is_object_id(id) && id != "building" && id != "villager";
}

}  // namespace

void WindowList::load(std::string_view text) {
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
        int values[6] = {0, 0, 0, 0, 0, 0};
        std::size_t p = colon + 1;
        int n = 0;
        for (; n < 6 && p <= entry.size(); ++n) {
            const std::size_t comma = std::min(entry.find(',', p), entry.size());
            const auto r = std::from_chars(entry.data() + p, entry.data() + comma, values[n]);
            if (r.ec != std::errc{} || r.ptr != entry.data() + comma) {
                break;
            }
            p = comma + 1;
        }
        // Five values before phase 62; six with "minimized".
        if ((n != 5 && n != 6) || p <= entry.size() || values[0] < 0 || values[1] < 0 || values[0] > 20000 ||
            values[1] > 20000 || values[2] < 0 || values[2] > 2000 || values[3] < 0 || values[3] > 1 || values[4] < 0 ||
            values[4] > 1000 || values[5] < 0 || values[5] > 1) {
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
        text += id + ":" + std::to_string(static_cast<int>(std::lround(w.x))) + "," +
                std::to_string(static_cast<int>(std::lround(w.y))) + "," +
                std::to_string(static_cast<int>(std::lround(w.w))) + "," + (w.pinned ? "1" : "0") + "," +
                std::to_string(group) + "," + (w.minimized ? "1" : "0") + ";";
    }
    if (text.size() > kMaxLayoutBytes || !std::all_of(text.begin(), text.end(), valid_layout_char)) {
        return {};
    }
    return text;
}

void WindowList::raise(const std::string& id) {
    std::erase(order_, id);
    order_.push_back(id);
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
    leave_group(id);
    if (is_object_id(id)) {
        std::erase_if(objects_, [&](const Object& o) { return o.id == id; });
        places_.erase(id);
    }
}

bool WindowList::is_object_id(std::string_view id) {
    return id.size() > 3 && id.substr(0, 3) == "obj";
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
