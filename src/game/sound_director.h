// Decides what sounds (phase 18): game events, the work nearest the camera
// (axes, hammers), fires, the ambient bed by season and the interface.
#pragma once

#include <array>
#include <cstdint>

#include "audio/mixer.h"
#include "game/settings.h"
#include "mods/mod_library.h"
#include "sim/game.h"

namespace sc {

class SoundDirector {
public:
    SoundDirector() : output_(mixer_) {}

    // Reads core's sounds/*.wav; missing or bad files stay silent (logged).
    void load(const mods::BuildResult& pack);
    // Opens the sound device; false if there is none (the game goes on).
    bool start();
    void set_volumes(const AudioSettings& settings);

    void ui_click();
    void event(sim::Game::Event::Kind kind);
    // Once a frame while a game is shown: `x`, `z` where the camera looks,
    // `height` how far it is.
    void update(const sim::Game& game, float x, float z, float height, bool paused, float dt);
    // Leaving a game: everything stops.
    void stop();
    // Closes the audio device; before SDL_Quit, which frees it.
    void shutdown();

    [[nodiscard]] audio::Mixer& mixer() { return mixer_; }

private:
    enum Sfx : std::size_t { Chop, Hammer, Bell, Fire, Click, Notify, Coins, Sword, Birds, Wind, Count };
    audio::Mixer mixer_;
    audio::Output output_;
    std::array<audio::SoundId, Sfx::Count> ids_{};
    float work_timer_ = 0.0f;
    std::uint32_t turn_ = 0;
    void play(Sfx s, audio::Category c, float gain = 1.0f);
};

}  // namespace sc
