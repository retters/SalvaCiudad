// The development test window of phase 117 (Ctrl+F3 > Interface): the
// stonecutter's window of the interface mockups, with test data, to measure
// RmlUi and see it next to the old interface. Its data model, "prueba",
// holds the numbers and the texts that carry numbers; the buttons change
// them through event callbacks, as the real windows will do with commands.
#pragma once

#include <cstdint>
#include <string>

#include <RmlUi/Core/DataModelHandle.h>

namespace Rml {
class Context;
}

namespace sc::rml {

struct TestWindowState {
    int workers = 2;
    int max_workers = 2;
    bool producing = true;
    bool pinned = false;
    bool minimized = false;
    bool closed = false;  // Its X was pressed; the owner hides the document.
    // Texts with numbers, made by tr() (D-11711).
    std::string workers_title;
    std::string workers_value;
    std::string workers_tip;
};

class TestWindow {
public:
    static constexpr const char* kDocument = "dev/prueba.rml";

    // Creates the data model; before the document is loaded.
    bool bind(Rml::Context& context);
    // Refreshes the texts when the numbers or the language changed.
    void update();
    [[nodiscard]] const TestWindowState& state() const { return state_; }
    // True once after the X was pressed.
    bool take_closed() {
        const bool closed = state_.closed;
        state_.closed = false;
        return closed;
    }

private:
    void refresh_texts();

    TestWindowState state_;
    Rml::DataModelHandle model_;
    std::uint64_t language_generation_ = ~0ull;
};

}  // namespace sc::rml
