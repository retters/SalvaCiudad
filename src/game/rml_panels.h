// Panels of rows in RmlUi (phases 125 and 126): what is not a game window
// but asks or tells something: the game's panels (the town's question,
// founding, the tutorial...) and, out of a game, the menus and screens.
// Each is a document of its own (hud/panel.rml#<id>) filled with rows of
// thing_rows.h, given again every frame it stays.
#pragma once

#include <map>
#include <string>
#include <vector>

#include <RmlUi/Core/EventListener.h>

#include "game/thing_rows.h"

namespace Rml {
class Element;
class ElementDocument;
}  // namespace Rml

namespace sc {

class Services;
namespace rml {
class RmlUi;
}

// Puts `view`'s rows into `box`: all of them when their number changed,
// else only those whose key changed (`shown` keeps the keys last put).
void rows_into(Rml::Element* box, const ThingRows& view, std::vector<std::string>& shown);

class RmlPanels final : public Rml::EventListener {
public:
    // Under the top bar (one below the other), above the build bar, in the
    // middle, or a menu screen: in the middle over a veil that keeps the
    // mouse from what is behind.
    enum class Place : std::uint8_t { Top, Bottom, Center, Screen };

    explicit RmlPanels(Services& services) : services_(services) {}
    RmlPanels(const RmlPanels&) = delete;
    RmlPanels& operator=(const RmlPanels&) = delete;

    // A panel shown with the next call to show(); `width` in design units;
    // `y` in pixels puts its top there instead of where its place says.
    void give(const std::string& id, ThingRows rows, Place place, float width = 480.0f, float y = -1.0f);
    // Shows the panels given since the last call and closes the others.
    // `top`: where the top panels start; `bottom`: the build bar's top (0:
    // none); `scale`: pixels per design unit.
    void show(rml::RmlUi* rml, float width, float height, float scale, float top, float bottom);
    // Closes them all.
    void hide(rml::RmlUi* rml);
    [[nodiscard]] bool showing(const std::string& id) const { return panels_.contains(id); }
    [[nodiscard]] bool any_screen() const;
    // The rows last given for `id` (tests and the window manager); null if none.
    [[nodiscard]] const ThingRows* rows(const std::string& id) const;

    void ProcessEvent(Rml::Event& event) override;

private:
    struct Panel {
        ThingRows view;
        Place place = Place::Top;
        float width = 480.0f;
        float y = -1.0f;
        std::string doc;
        Rml::ElementDocument* attached = nullptr;
        std::vector<std::string> row_keys;
        bool given = false;
    };
    Services& services_;
    std::map<std::string, Panel> panels_;
    bool veil_ = false;
};

}  // namespace sc
