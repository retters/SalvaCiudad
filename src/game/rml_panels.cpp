#include "game/rml_panels.h"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdlib>
#include <format>

#include <RmlUi/Core/Element.h>
#include <RmlUi/Core/ElementDocument.h>
#include <RmlUi/Core/Event.h>

#include "game/services.h"
#include "ui/rml/rml_ui.h"

namespace sc {

namespace {

constexpr const char* kVeil = "hud/veil.rml";

// The panels under the top bar, from the top down; the others after them.
constexpr std::array<const char*, 7> kTopOrder = {"spectator", "waiting", "found", "arrival", "question", "join", "vote"};

std::size_t top_rank(const std::string& id) {
    const auto it = std::find(kTopOrder.begin(), kTopOrder.end(), id);
    return static_cast<std::size_t>(it - kTopOrder.begin());
}

// A slider's value, as its element has it (a range input keeps it in its
// "value" attribute).
int control_value(Rml::Element* e) {
    return e != nullptr ? static_cast<int>(std::lround(std::strtod(e->GetAttribute<Rml::String>("value", "0").c_str(), nullptr)))
                        : 0;
}

}  // namespace

void rows_into(Rml::Element* box, const ThingRows& view, std::vector<std::string>& shown) {
    if (box == nullptr) {
        return;
    }
    std::vector<std::string> keys;
    keys.reserve(view.rows.size());
    for (const WinRow& r : view.rows) {
        keys.push_back(row_key(r));
    }
    if (keys.size() != shown.size() || box->GetNumChildren() != static_cast<int>(keys.size())) {
        // Other rows: all again.
        std::string all;
        for (const WinRow& r : view.rows) {
            all += "<div class=\"r\">" + row_rml(r) + "</div>";
        }
        box->SetInnerRML(all);
    } else {
        // The same rows: only those that changed, so a button under the
        // pointer stays the same element while the rest moves on.
        for (std::size_t i = 0; i < keys.size(); ++i) {
            Rml::Element* row = box->GetChild(static_cast<int>(i));
            if (keys[i] != shown[i]) {
                row->SetInnerRML(row_rml(view.rows[i]));
            } else if (Rml::Element* input = row->GetFirstChild(); input != nullptr && view.rows[i].kind == WinRow::Kind::Slider &&
                                                                   control_value(input) != view.rows[i].value) {
                input->SetAttribute("value", std::to_string(view.rows[i].value));
            }
        }
    }
    shown = std::move(keys);
}

void RmlPanels::give(const std::string& id, ThingRows rows, Place place, float width, float y) {
    Panel& p = panels_[id];
    p.y = y;
    p.view = std::move(rows);
    p.place = place;
    p.width = width;
    p.given = true;
}

bool RmlPanels::any_screen() const {
    return std::any_of(panels_.begin(), panels_.end(), [](const auto& kv) { return kv.second.place == Place::Screen; });
}

const ThingRows* RmlPanels::rows(const std::string& id) const {
    const auto it = panels_.find(id);
    return it != panels_.end() ? &it->second.view : nullptr;
}

void RmlPanels::show(rml::RmlUi* rml, float width, float height, float scale, float top, float bottom) {
    if (rml == nullptr) {
        // No RmlUi (the tests): what was given is kept to be read, once.
        for (auto it = panels_.begin(); it != panels_.end();) {
            it = it->second.given ? (it->second.given = false, std::next(it)) : panels_.erase(it);
        }
        return;
    }
    // Those not given since the last call go.
    for (auto it = panels_.begin(); it != panels_.end();) {
        if (!it->second.given) {
            if (!it->second.doc.empty()) {
                (void)rml->show_document(it->second.doc, false);
            }
            it = panels_.erase(it);
        } else {
            ++it;
        }
    }
    // A menu screen: the veil behind it.
    const bool veil = any_screen();
    if (veil != veil_ || (veil && !rml->document_shown(kVeil))) {
        (void)rml->show_document(kVeil, veil);
        veil_ = veil;
    }
    if (veil) {
        if (Rml::ElementDocument* doc = rml->document(kVeil)) {
            doc->PullToFront();
        }
    }
    std::vector<std::string> ids;
    for (const auto& [id, p] : panels_) {
        ids.push_back(id);
    }
    std::stable_sort(ids.begin(), ids.end(), [](const std::string& a, const std::string& b) { return top_rank(a) < top_rank(b); });
    float y_top = std::round(top);
    for (const std::string& id : ids) {
        Panel& p = panels_[id];
        p.given = false;
        p.doc = "hud/panel.rml#" + id;
        if (!rml->document_shown(p.doc)) {
            (void)rml->show_document(p.doc, true);
        }
        Rml::ElementDocument* doc = rml->document(p.doc);
        if (doc == nullptr) {
            continue;
        }
        if (doc != p.attached) {
            p.attached = doc;
            p.row_keys.clear();
            for (const char* type : {"click", "change"}) {
                doc->AddEventListener(type, this);
            }
        }
        doc->SetClass("screen", p.place == Place::Screen);
        rows_into(doc->GetElementById("rows"), p.view, p.row_keys);
        const float w = std::round(std::min(p.width * scale, width - 28.0f * scale));
        doc->SetProperty("width", std::format("{:.0f}px", w));
        // A screen taller than the window scrolls.
        if (p.place == Place::Screen) {
            doc->SetProperty("max-height", std::format("{:.0f}px", std::round(height - 32.0f * scale)));
        }
        const float h = doc->GetBox().GetSize(Rml::BoxArea::Border).y;
        float y = y_top;
        switch (p.place) {
            case Place::Top: y_top += h + 8.0f * scale; break;
            case Place::Bottom: {
                // Above the build bar, in the middle: the windows keep the top.
                const float b = bottom > 0.0f ? bottom : height - 110.0f * scale;
                y = b - h - 12.0f * scale;
                break;
            }
            case Place::Center:
            case Place::Screen: y = (height - h) * 0.5f; break;
        }
        if (p.y >= 0.0f) {
            y = p.y;
        }
        doc->SetProperty("left", std::format("{:.0f}px", std::round((width - w) * 0.5f)));
        doc->SetProperty("top", std::format("{:.0f}px", std::round(std::max(0.0f, y))));
        doc->PullToFront();
    }
}

void RmlPanels::hide(rml::RmlUi* rml) {
    if (rml != nullptr) {
        for (const auto& [id, p] : panels_) {
            if (!p.doc.empty()) {
                (void)rml->show_document(p.doc, false);
            }
        }
        if (veil_) {
            (void)rml->show_document(kVeil, false);
        }
    }
    veil_ = false;
    panels_.clear();
}

void RmlPanels::ProcessEvent(Rml::Event& ev) {
    std::string id;
    for (const auto& [pid, p] : panels_) {
        if (p.attached == ev.GetCurrentElement()) {
            id = pid;
        }
    }
    const auto found = panels_.find(id);
    if (found == panels_.end()) {
        return;
    }
    RowInput input;
    int act = -1;
    if (ev.GetType() == "change") {
        Rml::Element* e = ev.GetTargetElement();
        if (e == nullptr || !e->HasAttribute("data-act")) {
            return;
        }
        act = e->GetAttribute<int>("data-act", -1);
        input.text = ev.GetParameter<Rml::String>("value", "");
        input.enter = ev.GetParameter<bool>("linebreak", false);
        input.value = control_value(e);
    } else if (ev.GetType() == "click") {
        for (Rml::Element* e = ev.GetTargetElement(); e != nullptr && e != ev.GetCurrentElement(); e = e->GetParentNode()) {
            if (e->HasAttribute("data-act")) {
                if (e->GetTagName() != "input") {
                    act = e->GetAttribute<int>("data-act", -1);
                }
                break;
            }
        }
    }
    if (act < 0 || static_cast<std::size_t>(act) >= found->second.view.acts.size()) {
        return;
    }
    const RowFn fn = found->second.view.acts[static_cast<std::size_t>(act)];  // A copy: it may change the panels.
    RowEffects effects;
    fn(services_.session(), input, effects);
    if (effects.focus) {
        services_.focus_camera(effects.x, effects.z);
    }
}

}  // namespace sc
