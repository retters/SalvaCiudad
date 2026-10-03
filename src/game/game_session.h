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

#include "game/fog_view.h"
#include "game/save_file.h"
#include "mods/mod_library.h"
#include "sim/game.h"

namespace sc {

namespace net {
class NetSession;
}

class GameSession {
public:
    // A new game. In multiplayer `players` seats share the map (one common
    // town when `shared_town`) and this machine plays `local_player`.
    GameSession(std::shared_ptr<const sim::Content> content, sim::MapData map, const sim::GameSetup& setup,
                std::uint8_t local_player = 0);
    // A game that already exists (loaded, or received from the host).
    GameSession(std::unique_ptr<sim::Game> game, std::uint8_t local_player);

    // Multiplayer: commands go to the network, which runs the turns.
    void attach(net::NetSession* net) { net_ = net; }
    [[nodiscard]] bool networked() const { return net_ != nullptr; }
    // The host's state replaces this machine's (a resynchronization).
    void replace_game(std::unique_ptr<sim::Game> game) {
        game_ = std::move(game);
        fog_.begin(*game_, game_->vision_group(local_player_));
    }

    [[nodiscard]] sim::Game& game() { return *game_; }
    [[nodiscard]] const sim::Game& game() const { return *game_; }
    [[nodiscard]] std::uint8_t local_player() const { return local_player_; }
    // The town the local player runs (their own, or the common one).
    [[nodiscard]] std::uint8_t town() const { return game_->town_of(local_player_); }

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
        // Phase 63: a natural feature (its node's index + 1; 0: none) or an
        // animal, soldier or raider. One thing is selected at a time.
        std::uint32_t selected_node = 0;
        sim::EntityId selected_creature;
        void clear_selection() {
            selected_building = {};
            selected_villager = {};
            selected_node = 0;
            selected_creature = {};
        }
        [[nodiscard]] bool any_selected() const {
            return selected_building.valid() || selected_villager.valid() || selected_node != 0 || selected_creature.valid();
        }
        // Phase 61: the villager the camera follows (third or first person).
        sim::EntityId followed_villager;
        // Marking out a field for this farm: dragged from one corner cell.
        sim::EntityId field_farm;
        bool field_dragging = false;
        bool line_dragging = false;  // Walls: pressed at one end, released at the other.
        bool rally_mode = false;     // The next click on the ground: where the army defends.
        std::int32_t drag_x = 0;
        std::int32_t drag_z = 0;
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

    // What the local player sees through the fog of war (phase 32); update
    // it once a frame.
    [[nodiscard]] FogView& fog() { return fog_; }
    [[nodiscard]] const FogView& fog() const { return fog_; }

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
    std::uint8_t local_player_ = 0;
    net::NetSession* net_ = nullptr;
    Interaction ui_;
    FogView fog_;
};

// Text key explaining a load result to the player.
[[nodiscard]] const char* load_result_key(GameSession::LoadResult r);

}  // namespace sc
