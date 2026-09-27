// A game being played on this machine: the simulation, the commands the
// player gave since the last tick, and saving and loading. Commands are
// applied at the start of the next tick, the same moment they will run on
// every machine in multiplayer (phase 9).
#pragma once

#include <array>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "game/save_file.h"
#include "mods/mod_library.h"
#include "sim/game.h"

namespace sc {

class GameSession {
public:
    GameSession(std::shared_ptr<const sim::Content> content, sim::MapData map, std::uint64_t seed);

    [[nodiscard]] sim::Game& game() { return *game_; }
    [[nodiscard]] const sim::Game& game() const { return *game_; }
    [[nodiscard]] std::uint8_t local_player() const { return 0; }

    // What the player is doing with the interface (not part of the game).
    struct Interaction {
        sim::DefIndex placing = sim::kNoDef;  // Building being placed.
        std::uint8_t rotation = 0;
        bool hover_valid = false;             // The cursor is over the map.
        std::int32_t hover_x = 0;             // Corner cell under the cursor.
        std::int32_t hover_z = 0;
        sim::PlaceError hover_error = sim::PlaceError::None;
        sim::EntityId selected_building;
        sim::EntityId selected_villager;
        // Screen rectangles of the interface this frame (x, y, w, h):
        // clicks there are not for the world.
        std::vector<std::array<float, 4>> hud_rects;
        [[nodiscard]] bool over_hud(float x, float y) const {
            for (const auto& r : hud_rects) {
                if (x >= r[0] && y >= r[1] && x < r[0] + r[2] && y < r[1] + r[3]) {
                    return true;
                }
            }
            return false;
        }
    };
    [[nodiscard]] Interaction& ui() { return ui_; }
    [[nodiscard]] const Interaction& ui() const { return ui_; }

    // Queues a command from the local player; it runs on the next tick.
    void issue(sim::Command command);
    // Applies the queued commands and advances one tick.
    void step();

    // The whole game as a save.
    [[nodiscard]] save::SaveData make_save(const std::string& name, const mods::ModLibrary& mods) const;

    enum class LoadResult : std::uint8_t { Ok, Unreadable, OtherVersion, OtherMods, Damaged };
    // Builds a session from a save made with the same rules and mods.
    [[nodiscard]] static LoadResult load(const save::SaveData& data, std::shared_ptr<const sim::Content> content,
                                         std::unique_ptr<GameSession>& out);

private:
    GameSession() = default;
    std::unique_ptr<sim::Game> game_;
    std::vector<sim::Command> pending_;
    Interaction ui_;
};

// Text key explaining a load result to the player.
[[nodiscard]] const char* load_result_key(GameSession::LoadResult r);

}  // namespace sc
