// A game being played on this machine: the simulation, the commands the
// player gave since the last tick, and saving and loading. Commands are
// applied at the start of the next tick, the same moment they will run on
// every machine in multiplayer (phase 9).
#pragma once

#include <array>
#include <cstdint>
#include <functional>
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

// Phase 64: the pictures of the camera windows, as images of the interface.
inline constexpr std::uint32_t kCameraImageId = 10;  // And the next one.
inline constexpr int kCameraWindows = 2;

class GameSession {
public:
    // A new game. In multiplayer `players` seats share the map (one common
    // town when `shared_town`) and this machine plays `local_player`.
    GameSession(std::shared_ptr<const sim::Content> content, sim::MapData map, const sim::GameSetup& setup,
                std::uint8_t local_player = 0);
    // A game that already exists (loaded, or received from the host).
    GameSession(std::unique_ptr<sim::Game> game, std::uint8_t local_player);

    // Multiplayer: commands go to the network, which runs the turns.
    void attach(net::NetSession* net);
    [[nodiscard]] bool networked() const { return net_ != nullptr; }
    // The host's state replaces this machine's (a resynchronization).
    void replace_game(std::unique_ptr<sim::Game> game) {
        game_ = std::move(game);
        fog_.begin(*game_, game_->vision_group(local_player_));
    }

    [[nodiscard]] sim::Game& game() { return *game_; }
    [[nodiscard]] const sim::Game& game() const { return *game_; }
    [[nodiscard]] std::uint8_t local_player() const { return local_player_; }
    // A loaded game is played from another seat (phase 78).
    void set_local_player(std::uint8_t player);
    // Phase 79: watching. No order leaves this machine. `seat()` is the
    // seat this player owns (kNoSeat: a spectator, with none) and
    // `local_player()` the seat whose town is being looked at; with
    // `view_all()` the whole map shows, without fog.
    static constexpr std::uint8_t kNoSeat = 0xFF;
    [[nodiscard]] bool spectating() const { return spectating_; }
    [[nodiscard]] bool view_all() const { return view_all_; }
    [[nodiscard]] std::uint8_t seat() const { return seat_; }
    // Watches as seat `as` sees (or everything). `own_seat`: the seat this
    // player keeps meanwhile, kNoSeat for a spectator.
    void watch(std::uint8_t as, bool all, std::uint8_t own_seat);
    // Plays seat `seat` (its own again, or the one a spectator was given).
    void play(std::uint8_t seat);
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
        // One of the people placed with the developer tools (its number + 1;
        // 0: none), the one the camera follows, and what the view tells the
        // interface about each: its model, where it is, whether it is there.
        std::uint32_t selected_walker = 0;
        std::uint32_t followed_walker = 0;
        struct WalkerInfo {
            bool there = false;
            std::string model;
            float x = 0.0f;
            float z = 0.0f;
        };
        std::function<WalkerInfo(std::uint32_t)> walker_info;
        void clear_selection() {
            selected_building = {};
            selected_villager = {};
            selected_node = 0;
            selected_creature = {};
            selected_walker = 0;
        }
        [[nodiscard]] bool any_selected() const {
            return selected_building.valid() || selected_villager.valid() || selected_node != 0 ||
                   selected_creature.valid() || selected_walker != 0;
        }
        // Phase 61: the villager the camera follows (third or first person).
        sim::EntityId followed_villager;
        // Phase 64: the camera windows. Each looks at a thing from an orbit
        // of its own, without moving the main camera. `kind` as
        // WindowList::Kind. The view closes one whose thing is gone.
        struct CameraWindow {
            bool open = false;
            std::uint8_t kind = 0;
            sim::EntityId entity;
            float yaw = 0.6f;       // Radians around the thing.
            float pitch = 0.5f;     // Radians over the horizon.
            float distance = 12.0f;
        };
        std::array<CameraWindow, kCameraWindows> camera_windows;
        // Phase 74: founding the town. The site clicked, while the player is
        // asked to confirm (`found_asked`) and after the order left
        // (`found_sent`: the game's turn then, plus one; 0: not sent).
        // `found_mode` (phase 77): a seat that came later chose to found its
        // town (those who began the game always are choosing).
        bool found_mode = false;
        // Phase 79: a spectator's window with what it may do to play.
        bool arrival_open = true;
        bool found_asked = false;
        std::int32_t found_x = 0;
        std::int32_t found_z = 0;
        std::uint8_t found_rotation = 0;
        std::uint64_t found_sent = 0;
        // Marking out a field for this farm: dragged from one corner cell.
        sim::EntityId field_farm;
        bool field_dragging = false;
        bool line_dragging = false;  // Walls: pressed at one end, released at the other.
        bool rally_mode = false;     // The next click on the ground: where the army defends.
        std::int32_t drag_x = 0;
        std::int32_t drag_z = 0;
        // Phase 66: the minimap's picture on the screen this frame (x, y, w,
        // h; no width: not shown), for orders given on it.
        std::array<float, 4> minimap{};
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
    std::uint8_t seat_ = 0;
    bool spectating_ = false;
    bool view_all_ = false;
    net::NetSession* net_ = nullptr;
    Interaction ui_;
    FogView fog_;
};

// Phase 77. Whether the local player is choosing where to found its town:
// it has none, may found one, and (if it came later) said it wants to.
[[nodiscard]] bool choosing_site(const sim::Game& game, const GameSession::Interaction& ui, std::uint8_t local);

// Phase 78. The seat a player called `name` has in a saved game; if none
// has that name, the founder of the first town there is (else seat 0).
[[nodiscard]] std::uint8_t seat_for(const sim::Game& game, std::string_view name);

// Text key explaining a load result to the player.
[[nodiscard]] const char* load_result_key(GameSession::LoadResult r);

}  // namespace sc
