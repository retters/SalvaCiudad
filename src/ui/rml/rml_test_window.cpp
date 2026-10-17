#include "ui/rml/rml_test_window.h"

#include <algorithm>

#include <RmlUi/Core/Context.h>
#include <RmlUi/Core/DataModelHandle.h>

#include "i18n/translator.h"

namespace sc::rml {

using i18n::tr;

bool TestWindow::bind(Rml::Context& context) {
    Rml::DataModelConstructor c = context.CreateDataModel("prueba");
    if (!c) {
        return false;
    }
    c.Bind("workers", &state_.workers);
    c.Bind("max_workers", &state_.max_workers);
    c.Bind("producing", &state_.producing);
    c.Bind("pinned", &state_.pinned);
    c.Bind("minimized", &state_.minimized);
    c.Bind("workers_title", &state_.workers_title);
    c.Bind("workers_value", &state_.workers_value);
    c.Bind("workers_tip", &state_.workers_tip);
    const auto on = [&c](const char* name, auto&& change) {
        c.BindEventCallback(name, [change](Rml::DataModelHandle model, Rml::Event&, const Rml::VariantList&) {
            change();
            model.DirtyAllVariables();
        });
    };
    on("fewer", [this] {
        state_.workers = std::max(0, state_.workers - 1);
        language_generation_ = ~0ull;
    });
    on("more", [this] {
        state_.workers = std::min(state_.max_workers, state_.workers + 1);
        language_generation_ = ~0ull;
    });
    on("production", [this] { state_.producing = !state_.producing; });
    on("pin", [this] { state_.pinned = !state_.pinned; });
    on("minimize", [this] { state_.minimized = !state_.minimized; });
    on("close", [this] { state_.closed = true; });
    model_ = c.GetModelHandle();
    refresh_texts();
    return true;
}

void TestWindow::refresh_texts() {
    state_.workers_title = tr("hud.building.workerList", state_.workers);
    state_.workers_value = std::to_string(state_.workers) + " / " + std::to_string(state_.max_workers);
    state_.workers_tip = tr("hud.building.workers", state_.workers, state_.max_workers, state_.max_workers);
    language_generation_ = i18n::translator().generation();
    if (model_) {
        model_.DirtyAllVariables();
    }
}

void TestWindow::update() {
    if (language_generation_ != i18n::translator().generation()) {
        refresh_texts();
    }
}

}  // namespace sc::rml
