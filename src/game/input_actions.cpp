#include "game/input_actions.h"

#include <SDL3/SDL_keyboard.h>

#include "i18n/translator.h"

namespace sc {

namespace {

constexpr SDL_Scancode kNone = SDL_SCANCODE_UNKNOWN;

constexpr ActionInfo kActions[] = {
    {Action::CameraForward, "camera.forward", ActionGroup::Camera, {SDL_SCANCODE_W, SDL_SCANCODE_UP}},
    {Action::CameraBack, "camera.back", ActionGroup::Camera, {SDL_SCANCODE_S, SDL_SCANCODE_DOWN}},
    {Action::CameraLeft, "camera.left", ActionGroup::Camera, {SDL_SCANCODE_A, SDL_SCANCODE_LEFT}},
    {Action::CameraRight, "camera.right", ActionGroup::Camera, {SDL_SCANCODE_D, SDL_SCANCODE_RIGHT}},
    {Action::CameraRotateLeft, "camera.rotateLeft", ActionGroup::Camera, {SDL_SCANCODE_Q, kNone}},
    {Action::CameraRotateRight, "camera.rotateRight", ActionGroup::Camera, {SDL_SCANCODE_E, kNone}},
    {Action::CameraZoomIn, "camera.zoomIn", ActionGroup::Camera, {SDL_SCANCODE_EQUALS, SDL_SCANCODE_KP_PLUS}},
    {Action::CameraZoomOut, "camera.zoomOut", ActionGroup::Camera, {SDL_SCANCODE_MINUS, SDL_SCANCODE_KP_MINUS}},
    {Action::CameraCycleMode, "camera.cycleMode", ActionGroup::Camera, {SDL_SCANCODE_F4, kNone}},
    {Action::GamePause, "game.pause", ActionGroup::Game, {SDL_SCANCODE_SPACE, SDL_SCANCODE_PAUSE}},
    {Action::GameSpeed1, "game.speed1", ActionGroup::Game, {SDL_SCANCODE_1, kNone}},
    {Action::GameSpeed2, "game.speed2", ActionGroup::Game, {SDL_SCANCODE_2, kNone}},
    {Action::GameSpeed3, "game.speed3", ActionGroup::Game, {SDL_SCANCODE_3, kNone}},
    {Action::GameSpeedDown, "game.speedDown", ActionGroup::Game, {SDL_SCANCODE_COMMA, kNone}},
    {Action::GameSpeedUp, "game.speedUp", ActionGroup::Game, {SDL_SCANCODE_PERIOD, kNone}},
    {Action::GameQuickSave, "game.quickSave", ActionGroup::Game, {SDL_SCANCODE_F5, kNone}},
    {Action::GameQuickLoad, "game.quickLoad", ActionGroup::Game, {SDL_SCANCODE_F9, kNone}},
    {Action::GameRotateBuilding, "game.rotateBuilding", ActionGroup::Game, {SDL_SCANCODE_R, kNone}},
    {Action::GameNextSite, "game.nextSite", ActionGroup::Game, {SDL_SCANCODE_TAB, kNone}},
    {Action::UiToggleFullscreen, "ui.toggleFullscreen", ActionGroup::Interface, {SDL_SCANCODE_F11, kNone}},
    {Action::UiScreenshot, "ui.screenshot", ActionGroup::Interface, {SDL_SCANCODE_F12, kNone}},
    {Action::UiDebugOverlay, "ui.debugOverlay", ActionGroup::Interface, {SDL_SCANCODE_F3, kNone}},
};
static_assert(std::size(kActions) == kActionCount, "every action needs an entry");

}  // namespace

std::span<const ActionInfo> action_table() {
    return kActions;
}

const ActionInfo& action_info(Action action) {
    return kActions[static_cast<std::size_t>(action)];
}

KeyBindings::KeyBindings() {
    reset_to_defaults();
}

void KeyBindings::reset_to_defaults() {
    for (const ActionInfo& info : kActions) {
        keys_[static_cast<std::size_t>(info.action)] = info.default_keys;
    }
}

SDL_Scancode KeyBindings::key(Action action, std::size_t slot) const {
    return slot < kKeysPerAction ? keys_[static_cast<std::size_t>(action)][slot] : kNone;
}

void KeyBindings::set_key(Action action, std::size_t slot, SDL_Scancode key) {
    if (slot < kKeysPerAction && action < Action::Count) {
        keys_[static_cast<std::size_t>(action)][slot] = key;
    }
}

bool KeyBindings::find(SDL_Scancode key, Action& action, std::size_t& slot) const {
    if (key == kNone) {
        return false;
    }
    for (std::size_t a = 0; a < kActionCount; ++a) {
        for (std::size_t s = 0; s < kKeysPerAction; ++s) {
            if (keys_[a][s] == key) {
                action = static_cast<Action>(a);
                slot = s;
                return true;
            }
        }
    }
    return false;
}

bool KeyBindings::matches(Action action, SDL_Scancode key) const {
    if (key == kNone || action >= Action::Count) {
        return false;
    }
    for (const SDL_Scancode k : keys_[static_cast<std::size_t>(action)]) {
        if (k == key) {
            return true;
        }
    }
    return false;
}

bool scancode_from_name(std::string_view name, SDL_Scancode& out) {
    if (name.empty()) {
        out = kNone;
        return true;
    }
    if (name.size() > 32) {
        return false;
    }
    const std::string copy(name);
    const SDL_Scancode sc = SDL_GetScancodeFromName(copy.c_str());
    if (sc == kNone) {
        return false;
    }
    out = sc;
    return true;
}

std::string scancode_to_name(SDL_Scancode key) {
    if (key == kNone) {
        return {};
    }
    const char* name = SDL_GetScancodeName(key);
    return name != nullptr ? name : "";
}

namespace {

// Keys whose SDL name is an English word get a translated name; letters,
// digits and symbols are shown as the layout labels them.
struct NamedKey {
    SDL_Scancode key;
    std::string_view text_id;
};
constexpr NamedKey kNamedKeys[] = {
    {SDL_SCANCODE_UP, "up"},
    {SDL_SCANCODE_DOWN, "down"},
    {SDL_SCANCODE_LEFT, "left"},
    {SDL_SCANCODE_RIGHT, "right"},
    {SDL_SCANCODE_SPACE, "space"},
    {SDL_SCANCODE_RETURN, "enter"},
    {SDL_SCANCODE_KP_ENTER, "keypadEnter"},
    {SDL_SCANCODE_ESCAPE, "escape"},
    {SDL_SCANCODE_BACKSPACE, "backspace"},
    {SDL_SCANCODE_TAB, "tab"},
    {SDL_SCANCODE_DELETE, "delete"},
    {SDL_SCANCODE_INSERT, "insert"},
    {SDL_SCANCODE_HOME, "home"},
    {SDL_SCANCODE_END, "end"},
    {SDL_SCANCODE_PAGEUP, "pageUp"},
    {SDL_SCANCODE_PAGEDOWN, "pageDown"},
    {SDL_SCANCODE_PAUSE, "pause"},
    {SDL_SCANCODE_CAPSLOCK, "capsLock"},
    {SDL_SCANCODE_LSHIFT, "leftShift"},
    {SDL_SCANCODE_RSHIFT, "rightShift"},
    {SDL_SCANCODE_LCTRL, "leftCtrl"},
    {SDL_SCANCODE_RCTRL, "rightCtrl"},
    {SDL_SCANCODE_LALT, "leftAlt"},
    {SDL_SCANCODE_RALT, "rightAlt"},
    {SDL_SCANCODE_KP_PLUS, "keypadPlus"},
    {SDL_SCANCODE_KP_MINUS, "keypadMinus"},
    {SDL_SCANCODE_KP_MULTIPLY, "keypadMultiply"},
    {SDL_SCANCODE_KP_DIVIDE, "keypadDivide"},
};

}  // namespace

std::string key_display_name(SDL_Scancode key) {
    if (key == kNone) {
        return {};
    }
    for (const NamedKey& named : kNamedKeys) {
        if (named.key == key) {
            return i18n::tr("key." + std::string(named.text_id));
        }
    }
    const SDL_Keycode code = SDL_GetKeyFromScancode(key, SDL_KMOD_NONE, false);
    const char* name = SDL_GetKeyName(code);
    if (name != nullptr && name[0] != '\0') {
        return name;
    }
    return scancode_to_name(key);
}

}  // namespace sc
