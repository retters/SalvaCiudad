// Entry point of the model viewer (phase 30), a developer tool apart from the
// game. SDL_main.h maps it to WinMain on Windows.
#include <SDL3/SDL_main.h>

#include "viewer/viewer_app.h"

int main(int /*argc*/, char* /*argv*/[]) {
    sc::viewer::ViewerApp app;
    return app.run();
}
