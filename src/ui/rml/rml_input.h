// SDL keys, modifiers and buttons in RmlUi's terms (phase 117).
#pragma once

#include <SDL3/SDL_keycode.h>

#include <RmlUi/Core/Input.h>

namespace sc::rml {

[[nodiscard]] Rml::Input::KeyIdentifier key_from_sdl(SDL_Keycode key);
[[nodiscard]] int modifiers_from_sdl(SDL_Keymod mods);
// RmlUi numbers the buttons left 0, right 1, middle 2; -1 for the others.
[[nodiscard]] int button_from_sdl(int sdl_button);

}  // namespace sc::rml
