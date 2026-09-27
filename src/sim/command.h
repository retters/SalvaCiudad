// Commands: the only way players change the simulation. In multiplayer
// they are what travels over the network (section 7.4), so they are small,
// fully validated when read, and applied in a fixed order.
//
// The first three are the test set of the deterministic core (phase 5,
// the walkers world); the others are the village game's (phase 8 on).
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
    PlaceBuilding = 10,   // Building `def` with its corner cell at `position`, rotation `value` (0..3).
    RemoveBuilding = 11,  // Cancel a construction or demolish `entity`.
    SetWorkers = 12,      // Wanted workers of `entity`: `value`.
    PlaceField = 13,      // A field of farm `entity`: corner at `position`, size `value` (w | d << 8).
    DevGrant = 14,        // Developer tools: `value` units of resource `def` to the town center.
    SetCrop = 15,         // Farm `entity`, field `value & 0xFF`, year `value >> 8`: crop `def` (kNoDef = fallow).
    RemoveField = 16,     // Farm `entity`, field `value`.
    UpgradeBuilding = 17, // Start upgrading `entity` (the town center) to its next level.
    SetLimit = 18,        // Stock of its product `entity` works up to: `value` (0 = automatic).
    DevIgnite = 19,       // Developer tools: set `entity` on fire.
    Trade = 20,           // With the merchant at trading post `entity`: buy (`value` > 0) or sell `def`.
    OfferTrade = 21,      // To player `count`: give `value` of `def`, want `value2` of `def2` (kCoins: coins).
    AnswerOffer = 22,     // Offer `value`: accept (`count` 1) or decline / withdraw (0).
    RingBell = 23,        // The town's alarm on (`value` 1) or off (0): adults take up arms.
    DevRaid = 24,         // Developer tools: raiders come now.
    TrainUnit = 25,       // Barracks `entity`: train one unit `def` (`value` 1), or cancel the last (`value` 0).
    DevLevel = 27,        // Developer tools: the town center goes up a level at once.
    DevSpawn = 28,        // Developer tools: `value` adults (couples) arrive at the town center.
    ArmyOrder = 26,       // The army: defend around `position` (`value` 0), attack player `count` (1) or retreat (2).
};

inline constexpr std::uint8_t kMaxPlayers = 12;
inline constexpr std::uint16_t kMaxSpawnPerCommand = 64;
inline constexpr std::int32_t kMaxDevGrant = 10000;
inline constexpr std::int32_t kMaxTrade = 10000;
// Coins in a trade offer, in place of a resource.
inline constexpr std::uint16_t kCoins = 0xFFFE;

struct Command {
    CommandType type = CommandType::SpawnWalkers;
    std::uint8_t player = 0;
    EntityId entity;
    FixedVec2 position;
    std::uint16_t count = 0;
    std::uint16_t def = 0;     // Definition index (buildings...).
    std::int32_t value = 0;    // Rotation, worker count...
    std::uint16_t def2 = 0;    // A second definition (trade offers).
    std::int32_t value2 = 0;

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
