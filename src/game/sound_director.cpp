#include "game/sound_director.h"

#include <algorithm>
#include <cmath>

#include "core/file_io.h"
#include "core/log.h"

namespace sc {

namespace {

float to_float(sim::Fixed f) {
    return static_cast<float>(f.raw()) / 65536.0f;
}

// Louder near the camera: full within 15 m, silent past `reach`.
float near_gain(float dx, float dz, float height, float reach) {
    const float d = std::sqrt(dx * dx + dz * dz + height * height * 0.5f);
    return std::clamp(1.0f - (d - 15.0f) / (reach - 15.0f), 0.0f, 1.0f);
}

}  // namespace

void SoundDirector::load(const mods::BuildResult& pack) {
    static constexpr const char* kFiles[] = {"chop", "hammer", "bell", "fire", "click", "notify",
                                             "coins", "sword", "birds", "wind", "rain"};
    ids_.fill(audio::kNoSound);
    if (mixer_.sound_count() > 0) {
        return;  // Loaded once; the sounds do not depend on the enabled mods.
    }
    for (std::size_t i = 0; i < std::size(kFiles); ++i) {
        const std::filesystem::path file =
            mods::mod_file(pack.dir("core"), std::string("sounds/") + kFiles[i] + ".wav");
        if (file.empty()) {
            continue;
        }
        const fs::ReadResult read = fs::read_file(file, audio::kMaxSoundBytes);
        if (read.error != fs::IoError::None) {
            log::warn("sound: cannot read {}", kFiles[i]);
            continue;
        }
        std::string error;
        std::optional<audio::Sound> sound = audio::parse_wav(
            std::span(reinterpret_cast<const std::uint8_t*>(read.data.data()), read.data.size()), error);
        if (!sound) {
            log::warn("sound: {}: {}", kFiles[i], error);
            continue;
        }
        ids_[i] = mixer_.add(std::move(*sound));
    }
}

bool SoundDirector::start() {
    const bool ok = output_.open();
    if (!ok) {
        log::warn("sound: no audio device; the game stays silent");
    }
    return ok;
}

void SoundDirector::set_volumes(const AudioSettings& s) {
    audio::Volumes v;
    v.master = s.master;
    v.category = {s.effects, s.ambient, s.ui};
    mixer_.set_volumes(v);
}

void SoundDirector::play(Sfx s, audio::Category c, float gain) {
    if (ids_[s] != audio::kNoSound) {
        mixer_.play(ids_[s], c, gain);
    }
}

void SoundDirector::ui_click() {
    play(Click, audio::Category::Ui, 0.5f);
}

void SoundDirector::event(sim::Game::Event::Kind kind) {
    using K = sim::Game::Event::Kind;
    switch (kind) {
        case K::RaidStarted:
        case K::FireStarted: play(Bell, audio::Category::Effects, 0.8f); break;
        case K::MerchantArrived:
        case K::AutoTrade:
        case K::CaravanArrived:
        case K::OfferAnswered: play(Coins, audio::Category::Effects, 0.7f); break;
        case K::UnitTrained: play(Sword, audio::Category::Effects, 0.6f); break;
        case K::Born: break;  // Too frequent: only the notification.
        default: play(Notify, audio::Category::Ui, 0.5f); break;
    }
}

void SoundDirector::update(const sim::Game& game, const FogView* fog, float x, float z, float height, bool paused,
                           float dt) {
    // Others' fires and work only where the player can see them (phase 32).
    const auto heard = [&](std::uint8_t town, float px, float pz) {
        return fog == nullptr || fog->mode() == sim::FogMode::None || game.town_group(town) == fog->group() ||
               fog->shows(px, pz);
    };
    // The ambient bed: birds in the warm seasons, wind in the cold. Higher
    // up, the birds fade and the wind stays.
    const bool cold = game.temperature() < 2 || game.calendar().season == sim::Season::Winter;
    const float up = std::clamp((height - 30.0f) / 150.0f, 0.0f, 1.0f);
    // Phase 97: under the rain the birds are quiet, and it is heard from any height.
    const bool rain = game.rules().rain != 0 && game.raining();
    if (ids_[Birds] != audio::kNoSound && ids_[Wind] != audio::kNoSound) {
        mixer_.set_loop(0, cold ? ids_[Wind] : ids_[Birds], audio::Category::Ambient,
                        paused ? 0.0f : (cold ? 0.5f : 0.45f * (1.0f - up) * (rain ? 0.25f : 1.0f)));
    }
    if (ids_[Rain] != audio::kNoSound) {
        mixer_.set_loop(2, ids_[Rain], audio::Category::Ambient, paused || !rain ? 0.0f : 0.55f - 0.2f * up);
    }
    // The nearest fire crackles.
    float fire = 0.0f;
    for (const sim::Building& b : game.buildings().data()) {
        if (b.fire > 0) {
            const float bx = static_cast<float>(b.x) + static_cast<float>(b.width) * 0.5f;
            const float bz = static_cast<float>(b.z) + static_cast<float>(b.depth) * 0.5f;
            if (!heard(b.owner, bx, bz)) {
                continue;
            }
            fire = std::max(fire, near_gain(bx - x, bz - z, height, 120.0f));
        }
    }
    if (ids_[Fire] != audio::kNoSound) {
        mixer_.set_loop(1, ids_[Fire], audio::Category::Effects, paused ? 0.0f : fire * 0.8f);
    }
    if (paused) {
        return;
    }
    // Work near the camera: now and then an axe or a hammer.
    work_timer_ -= dt;
    if (work_timer_ > 0.0f) {
        return;
    }
    work_timer_ = 0.35f;
    const auto& vs = game.villagers();
    const std::size_t n = vs.size();
    for (std::size_t k = 0; k < std::min<std::size_t>(n, 64); ++k) {
        const sim::Villager& v = vs.data()[(turn_ + k) % n];
        const bool building = v.task == sim::Task::Build;
        const bool chopping = v.task == sim::Task::Gather && v.node > 0 && v.node <= game.map().features.size() &&
                              game.map().features[v.node - 1].type == sim::FeatureType::Tree;
        if (!building && !chopping) {
            continue;
        }
        if (!heard(v.owner, to_float(v.position.x), to_float(v.position.z))) {
            continue;
        }
        const float gain = near_gain(to_float(v.position.x) - x, to_float(v.position.z) - z, height, 80.0f);
        if (gain <= 0.05f) {
            continue;
        }
        play(building ? Hammer : Chop, audio::Category::Effects, gain * 0.6f);
        turn_ += static_cast<std::uint32_t>(k + 1);
        return;
    }
    turn_ += 64;
}

void SoundDirector::stop() {
    mixer_.stop_all();
}

void SoundDirector::shutdown() {
    output_.close();
}

}  // namespace sc
