// Multiplayer screens (section 6.2): joining a game (games found on the
// local network, or an address and port) and the lobby, where the players
// choose name and color, get ready, and the host picks the world mode and
// starts. Phase 126: RmlUi menu panels of rows (thing_rows.h).
#pragma once

#include <cstdint>
#include <string>

#include "game/services.h"
#include "game/thing_rows.h"
#include "ui/context.h"

namespace sc {

class UiHost;

// Colors of the players' seats, sRGB.
[[nodiscard]] ui::Color player_color(std::uint8_t index);

class JoinScreen {
public:
    explicit JoinScreen(Services& services) : services_(services) {}
    void open();
    enum class Result : std::uint8_t { None, Back, Joining };
    Result frame(ui::Context& ctx, UiHost& host, bool modal);
    [[nodiscard]] ThingRows rows();

private:
    Services& services_;
    std::string name_;
    std::string address_;
    std::string port_;
    Result result_ = Result::None;
    bool connect(const std::string& address, std::uint16_t port);
};

class LobbyScreen {
public:
    explicit LobbyScreen(Services& services) : services_(services) {}
    void open();
    enum class Result : std::uint8_t { None, Leave };
    Result frame(ui::Context& ctx, UiHost& host, bool modal);
    [[nodiscard]] ThingRows rows();

private:
    Services& services_;
    std::string name_;
    std::uint8_t color_ = 0;
    bool color_chosen_ = false;
    bool ready_ = false;
    bool watch_ = false;  // Phase 79: to watch the game instead of playing it.
    bool leave_ = false;
    void send_info();
};

}  // namespace sc
