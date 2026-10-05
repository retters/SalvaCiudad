// Commands: the only way players change the simulation. In multiplayer
// they are what travels over the network (section 7.4), so they are small,
// fully validated when read, and applied in a fixed order.
//
#pragma once

#include <cstdint>
#include <string>
#include <string_view>

#include "sim/entity.h"
#include "sim/fixed.h"
#include "sim/serialize.h"

namespace sc::sim {

enum class CommandType : std::uint8_t {
    PlaceBuilding = 10,   // Building `def` with its corner cell at `position`, rotation `value` (0..3).
    RemoveBuilding = 11,  // Cancel a construction or demolish `entity`.
    SetWorkers = 12,      // Wanted workers of `entity`: `value`.
    PlaceField = 13,      // A field of farm `entity`: corner at `position`, size `value` (w | d << 8).
    DevGrant = 14,        // Developer tools: `value` units of resource `def` to the town center.
    SetCrop = 15,         // Farm `entity`, field `value & 0xFF`, year `value >> 8`: crop `def` (kNoDef = fallow).
    RemoveField = 16,     // Farm `entity`, field `value`.
    UpgradeBuilding = 17, // Start upgrading `entity` (the town center) to its next level.
    SetLimit = 18,        // Stock of its product `entity` works up to: `value` (0 = automatic); gold a trading post keeps.
    DevIgnite = 19,       // Developer tools: set `entity` on fire.
    Trade = 20,           // With the merchant at trading post `entity`: buy (`value` > 0) or sell `def`.
    OfferTrade = 21,      // To player `count`: give `value` of `def`, want `value2` of `def2`.
    AnswerOffer = 22,     // Offer `value`: accept (`count` 1) or decline / withdraw (0).
    RingBell = 23,        // The town's alarm on (`value` 1) or off (0): adults take up arms.
    DevRaid = 24,         // Developer tools: raiders come now.
    TrainUnit = 25,       // Barracks `entity`: train one unit `def` (`value` 1), or cancel the last (`value` 0).
    DevLevel = 27,        // Developer tools: the town center goes up a level at once.
    DevSpawn = 28,        // Developer tools: `value` adults (couples) arrive at the town center.
    ArmyOrder = 26,       // The army: defend around `position` (`value` 0), attack player `count` (1) or retreat (2).
    SetTradeRule = 29,    // Automatic trade of `def`: sell over `value`, buy under `value2` (kNoRule: off);
                          // `count` and `def2`: the price limits of each, percent (0: any price).
    RenameVillager = 30,  // Villager `entity` is called `text` from now on ("": its own name again).
    SetProduction = 31,   // Workplace `entity` works (`value` 1) or stands idle and lets its workers go (0).
    MoveVillager = 32,    // Explorer `entity` (a villager) goes to `position` and waits there.
    DevFeature = 33,      // Developer tools: a natural feature at `position`: type `def`, species `def2`,
                          // size `count`, scale `value` (raw fixed point), rotation `value2`.
    FoundTown = 34,       // Phase 73: the seat's town, its center's corner cell at `position`, rotation `value` (0..3).
    AddSeat = 35,         // Phase 75, the host only: a new seat without a town; `text` its name, `count` its color.
    JoinTown = 36,        // A town's founder only: seat `count`, which asked to (phase 77), joins the sender's town.
    SetAccess = 37,       // Phase 76, the host only: who may come into the game, `value` as access bits.
    RequestJoin = 38,     // Phase 77: the sender, who has no town, asks the founder of town `count` to join it.
    CancelJoin = 39,      // Phase 77: the sender withdraws its request.
    RefuseJoin = 40,      // Phase 77, a town's founder only: seat `count`'s request to join is refused.
    SetOption = 41,       // Phase 85: workplace `entity`'s option number `count` (sim::option) on (`value` 1) or off (0).
    Trace = 42,           // Phase 93: a line of modules `def` from the cell at `position` to the cell (`value`, `value2`);
                          // `count` 1: an L goes along z first.

};

inline constexpr std::uint8_t kMaxPlayers = 12;
inline constexpr std::int32_t kMaxDevGrant = 10000;
inline constexpr std::int32_t kMaxTrade = 10000;
// An automatic trade rule that is off; the largest amount one can name.
inline constexpr std::int32_t kNoRule = -1;
// A rule's price limit: none (0), or 75 to 125 % of the good's value in
// steps of 5 (merchants' prices go from 75 to 125 %).
inline constexpr std::int32_t kMinPriceLimit = 75;
inline constexpr std::int32_t kMaxPriceLimit = 125;
[[nodiscard]] constexpr bool valid_price_limit(std::int32_t percent) {
    return percent == 0 || (percent >= kMinPriceLimit && percent <= kMaxPriceLimit && percent % 5 == 0);
}
inline constexpr std::int32_t kMaxRule = 100000;
// A villager's name: at most this many bytes of UTF-8, no control
// characters, no space at either end. "" is valid: no name of its own.
inline constexpr std::size_t kMaxNameBytes = 24;
[[nodiscard]] bool valid_villager_name(std::string_view name);
// A seat's name (the player's): the same rules, up to this many bytes; ""
// is valid (the interface then calls it by its number).
inline constexpr std::size_t kMaxSeatNameBytes = 32;
[[nodiscard]] bool valid_seat_name(std::string_view name);
inline constexpr std::uint8_t kMaxSeatColor = 15;
// Phase 76: what a game lets newcomers do. Closed, nobody new gets a seat
// (those who have one may always come back).
namespace access {
inline constexpr std::uint8_t kOpen = 1;   // New players get a seat.
inline constexpr std::uint8_t kJoin = 2;   // They may ask to join a town.
inline constexpr std::uint8_t kFound = 4;  // They may found a town of their own.
// Phase 79: people may come in to watch, without a seat. They are
// connections, not part of the game: nothing else of the simulation knows
// about them.
inline constexpr std::uint8_t kWatch = 8;
inline constexpr std::uint8_t kAll = kOpen | kJoin | kFound | kWatch;
}  // namespace access

struct Command {
    CommandType type = CommandType::PlaceBuilding;
    std::uint8_t player = 0;
    EntityId entity;
    FixedVec2 position;
    std::uint16_t count = 0;
    std::uint16_t def = 0;     // Definition index (buildings...).
    std::int32_t value = 0;    // Rotation, worker count...
    std::uint16_t def2 = 0;    // A second definition (trade offers).
    std::int32_t value2 = 0;
    std::string text;          // A name (RenameVillager, AddSeat); empty in every other command.

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
