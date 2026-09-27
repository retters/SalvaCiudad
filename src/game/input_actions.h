// Rebindable keyboard actions. Each action has up to two keys (for example
// W and the up arrow). Keys are stored by SDL scancode name, so bindings
// follow the physical key position on any keyboard layout.
#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include <string>
#include <string_view>

#include <SDL3/SDL_scancode.h>

namespace sc {

enum class Action : std::uint8_t {
    CameraForward,
    CameraBack,
    CameraLeft,
    CameraRight,
    CameraRotateLeft,
    CameraRotateRight,
    CameraZoomIn,
    CameraZoomOut,
    CameraCycleMode,
    GamePause,
    GameSpeed1,
    GameSpeed2,
    GameSpeed3,
    GameQuickSave,
    GameQuickLoad,
    UiToggleFullscreen,
    UiScreenshot,
    UiDebugOverlay,
    Count,
};

inline constexpr std::size_t kActionCount = static_cast<std::size_t>(Action::Count);
inline constexpr std::size_t kKeysPerAction = 2;

enum class ActionGroup : std::uint8_t { Camera, Game, Interface };

struct ActionInfo {
    Action action;
    std::string_view id;  // Settings key and text key suffix: "camera.forward".
    ActionGroup group;
    std::array<SDL_Scancode, kKeysPerAction> default_keys;
};

[[nodiscard]] std::span<const ActionInfo> action_table();
[[nodiscard]] const ActionInfo& action_info(Action action);

// Current bindings. SDL_SCANCODE_UNKNOWN means "no key".
class KeyBindings {
public:
    KeyBindings();  // Defaults.

    [[nodiscard]] SDL_Scancode key(Action action, std::size_t slot) const;
    void set_key(Action action, std::size_t slot, SDL_Scancode key);

    // The action and slot already using `key`, if any.
    [[nodiscard]] bool find(SDL_Scancode key, Action& action, std::size_t& slot) const;

    // True if `key` triggers `action`.
    [[nodiscard]] bool matches(Action action, SDL_Scancode key) const;

    void reset_to_defaults();

    bool operator==(const KeyBindings&) const = default;

private:
    std::array<std::array<SDL_Scancode, kKeysPerAction>, kActionCount> keys_{};
};

// Scancode <-> stable name for the settings file ("W", "Up", "Space"...).
// An empty name is "no key". Returns false for unknown names.
[[nodiscard]] bool scancode_from_name(std::string_view name, SDL_Scancode& out);
[[nodiscard]] std::string scancode_to_name(SDL_Scancode key);

// Name to show the player: the key's label on the current layout.
[[nodiscard]] std::string key_display_name(SDL_Scancode key);

}  // namespace sc
