// The Mods screen: which mods are on, in what order, and why a mod could
// not load. Changes take effect with "Apply", which rebuilds the content.
#pragma once

#include <string>
#include <vector>

#include "game/services.h"
#include "ui/context.h"

namespace sc {

class ModsScreen {
public:
    explicit ModsScreen(Services& services) : services_(services) {}

    // Takes the current choice of mods, to edit it.
    void open();
    // Returns false when the player leaves the screen.
    bool frame(ui::Context& ctx, bool input_blocked);

private:
    Services& services_;
    std::vector<std::string> enabled_;  // Being edited, in order.
    bool dirty_ = false;
};

}  // namespace sc
