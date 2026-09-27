// Commands: the only way players change the simulation. In multiplayer
// they are what travels over the network (section 7.4), so they are small,
// fully validated when read, and applied in a fixed order.
//
// The command set is a test set for the deterministic core (phase 5);
// the game's real commands arrive with the game (phase 8).
#pragma once

#include <cstdint>

#include "sim/entity.h"
#include "sim/fixed.h"
#include "sim/serialize.h"

namespace sc::sim {

enum class CommandType : std::uint8_t {
    SpawnWalkers = 1,  // `count` walkers around `position`.
    SendWalker = 2,    // Walker `entity` walks to `position`.
    RemoveWalker = 3,  // Walker `entity` leaves.
};

inline constexpr std::uint8_t kMaxPlayers = 12;
inline constexpr std::uint16_t kMaxSpawnPerCommand = 64;

struct Command {
    CommandType type = CommandType::SpawnWalkers;
    std::uint8_t player = 0;
    EntityId entity;
    FixedVec2 position;
    std::uint16_t count = 0;

    void write(BinaryWriter& w) const;
    // Reads and validates the shape of a command (not whether its target
    // entity exists: that depends on the state and is checked on apply).
    [[nodiscard]] static bool read(BinaryReader& r, Command& out);

    bool operator==(const Command&) const = default;
};

// A command bound to the tick it runs in. Within a tick, commands run by
// `sequence`, which the host assigns in multiplayer.
struct ScheduledCommand {
    std::uint64_t tick = 0;
    std::uint32_t sequence = 0;
    Command command;

    bool operator==(const ScheduledCommand&) const = default;
};

}  // namespace sc::sim
