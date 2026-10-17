#include "ui/rml/rml_input.h"

#include <SDL3/SDL_mouse.h>

namespace sc::rml {

using namespace Rml::Input;

KeyIdentifier key_from_sdl(SDL_Keycode key) {
    if (key >= SDLK_A && key <= SDLK_Z) {
        return static_cast<KeyIdentifier>(KI_A + (key - SDLK_A));
    }
    if (key >= SDLK_0 && key <= SDLK_9) {
        return static_cast<KeyIdentifier>(KI_0 + (key - SDLK_0));
    }
    if (key >= SDLK_F1 && key <= SDLK_F12) {
        return static_cast<KeyIdentifier>(KI_F1 + (key - SDLK_F1));
    }
    if (key >= SDLK_KP_1 && key <= SDLK_KP_9) {
        return static_cast<KeyIdentifier>(KI_NUMPAD1 + (key - SDLK_KP_1));
    }
    switch (key) {
        case SDLK_SPACE: return KI_SPACE;
        case SDLK_RETURN: return KI_RETURN;
        case SDLK_ESCAPE: return KI_ESCAPE;
        case SDLK_BACKSPACE: return KI_BACK;
        case SDLK_TAB: return KI_TAB;
        case SDLK_DELETE: return KI_DELETE;
        case SDLK_INSERT: return KI_INSERT;
        case SDLK_HOME: return KI_HOME;
        case SDLK_END: return KI_END;
        case SDLK_PAGEUP: return KI_PRIOR;
        case SDLK_PAGEDOWN: return KI_NEXT;
        case SDLK_LEFT: return KI_LEFT;
        case SDLK_RIGHT: return KI_RIGHT;
        case SDLK_UP: return KI_UP;
        case SDLK_DOWN: return KI_DOWN;
        case SDLK_KP_0: return KI_NUMPAD0;
        case SDLK_KP_ENTER: return KI_NUMPADENTER;
        case SDLK_KP_PLUS: return KI_ADD;
        case SDLK_KP_MINUS: return KI_SUBTRACT;
        case SDLK_KP_MULTIPLY: return KI_MULTIPLY;
        case SDLK_KP_DIVIDE: return KI_DIVIDE;
        case SDLK_KP_PERIOD: return KI_DECIMAL;
        case SDLK_LSHIFT: return KI_LSHIFT;
        case SDLK_RSHIFT: return KI_RSHIFT;
        case SDLK_LCTRL: return KI_LCONTROL;
        case SDLK_RCTRL: return KI_RCONTROL;
        case SDLK_LALT: return KI_LMENU;
        case SDLK_RALT: return KI_RMENU;
        default: return KI_UNKNOWN;
    }
}

int modifiers_from_sdl(SDL_Keymod mods) {
    int out = 0;
    if ((mods & SDL_KMOD_CTRL) != 0) {
        out |= KM_CTRL;
    }
    if ((mods & SDL_KMOD_SHIFT) != 0) {
        out |= KM_SHIFT;
    }
    if ((mods & SDL_KMOD_ALT) != 0) {
        out |= KM_ALT;
    }
    if ((mods & SDL_KMOD_GUI) != 0) {
        out |= KM_META;
    }
    if ((mods & SDL_KMOD_CAPS) != 0) {
        out |= KM_CAPSLOCK;
    }
    if ((mods & SDL_KMOD_NUM) != 0) {
        out |= KM_NUMLOCK;
    }
    return out;
}

int button_from_sdl(int sdl_button) {
    switch (sdl_button) {
        case SDL_BUTTON_LEFT: return 0;
        case SDL_BUTTON_RIGHT: return 1;
        case SDL_BUTTON_MIDDLE: return 2;
        default: return -1;
    }
}

}  // namespace sc::rml
