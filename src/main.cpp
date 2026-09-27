// Program entry point. SDL_main.h maps it to WinMain on Windows.
#include <SDL3/SDL_main.h>

#include "game/app.h"

int main(int /*argc*/, char* /*argv*/[]) {
    sc::App app;
    return app.run();
}
