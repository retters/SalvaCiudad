// Program entry point. SDL_main.h maps it to WinMain on Windows.
#include <SDL3/SDL_main.h>

#include <string_view>

#include "game/app.h"

int main(int argc, char* argv[]) {
    // --instance <1..8>: its own data folder and port, to try multiplayer
    // with several windows on one computer (section 7.4).
    int instance = 0;
    // --loopback: multiplayer only on this computer (127.0.0.1), without
    // listening on the network or searching it; no firewall prompt.
    bool loopback = false;
    for (int i = 1; i < argc; ++i) {
        loopback = loopback || std::string_view(argv[i]) == "--loopback";
    }
    for (int i = 1; i + 1 < argc; ++i) {
        if (std::string_view(argv[i]) == "--instance") {
            const std::string_view v = argv[i + 1];
            if (v.size() == 1 && v[0] >= '1' && v[0] <= '8') {
                instance = v[0] - '0';
            }
        }
    }
    sc::App app(instance, loopback);
    return app.run();
}
