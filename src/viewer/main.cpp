// Entry point of the model viewer (phase 30), a developer tool apart from the
// game. SDL_main.h maps it to WinMain on Windows.
#include <SDL3/SDL_main.h>

#include <filesystem>
#include <string_view>

#include "core/text.h"
#include "viewer/viewer_app.h"

// --estudio <folder>: the folder of models in study to show (phase 45): a
// path, or the name of a folder of art/studies ("tripo", "people"). Without
// it, a viewer built from a source tree offers art/studies/animals beside
// the mods.
int main(int argc, char* argv[]) {
    std::filesystem::path studies;
    for (int i = 1; i + 1 < argc; ++i) {
        if (std::string_view(argv[i]) == "--estudio") {
            studies = sc::text::path_from_utf8(argv[i + 1]);
        }
    }
    sc::viewer::ViewerApp app(std::move(studies));
    return app.run();
}
