// Network messages of the lockstep multiplayer (section 7.4, docs/RED.md).
// Every message is a type byte followed by its fields in the simulation's
// little-endian encoding. Readers treat the bytes as untrusted input:
// sizes, counts, ranges and texts are all checked, and a message that fails
// is dropped (and its sender disconnected by the caller).
#pragma once

#include <array>
#include <cstdint>
#include <optional>
#include <span>
#include <string>
#include <variant>
#include <vector>

#include "sim/climate.h"
#include "sim/command.h"
#include "sim/map.h"
#include "sim/serialize.h"

namespace sc::net {

inline constexpr std::uint32_t kProtocolVersion = 5;
inline constexpr std::uint16_t kDefaultPort = 47800;
inline constexpr std::uint16_t kDiscoveryPort = 47799;
inline constexpr std::size_t kMaxNameBytes = 32;
inline constexpr std::size_t kMaxMods = 256;
inline constexpr std::size_t kMaxCommandsPerMessage = 256;
inline constexpr std::size_t kMaxCommandsPerTurn = 4096;
inline constexpr std::size_t kMaxMessageBytes = 256u * 1024u;          // Everything but snapshots.
// Unpacked: a colossal map's game is about 1.9 GiB (phase 21).
inline constexpr std::size_t kMaxSnapshotBytes = 3u * 1024u * 1024u * 1024u;
inline constexpr std::uint8_t kColors = 12;
// Ticks between state checks (5 s at x1).
inline constexpr std::uint64_t kHashInterval = 50;

struct ModRef {
    std::string id;
    std::string version;
    std::uint64_t hash = 0;
    bool operator==(const ModRef&) const = default;
};

// What every machine needs to build the same game.
struct GameConfig {
    sim::MapSettings map;
    bool shared_town = false;  // Cooperative: one town for everybody (section 7.7).
    std::uint64_t seed = 1;    // The game's own random numbers.
    sim::GameRules rules;      // Climate, starting goods, population limit.
    bool operator==(const GameConfig&) const = default;
};

enum class RejectReason : std::uint8_t { Protocol, Version, Mods, Full, BadName, Count };
enum class LobbyPhase : std::uint8_t { Lobby, Loading, Playing, Count };
enum class SpeedReason : std::uint8_t { Vote, Pause, SlowPlayer, Count };
enum class NoticeKind : std::uint8_t { Joined, Left, Rejoined, Desync, WrongMap, Count };

struct LobbyPlayer {
    std::uint8_t slot = 0;
    std::string name;
    std::uint8_t color = 0;
    bool ready = false;
    bool connected = false;
    bool loaded = false;
    bool operator==(const LobbyPlayer&) const = default;
};

// A command with the seat it came from, in the order it runs.
struct TurnCommand {
    std::uint8_t player = 0;
    sim::Command command;
    bool operator==(const TurnCommand&) const = default;
};

struct PartHashes {
    std::array<std::uint64_t, 8> parts{};
    bool operator==(const PartHashes&) const = default;
};

// --- Messages ------------------------------------------------------------------

struct Hello {  // Client to host, first thing after connecting.
    std::uint32_t protocol = kProtocolVersion;
    std::string game_version;
    std::uint64_t content_hash = 0;
    std::vector<ModRef> mods;  // Those that affect the simulation.
    std::string name;
    bool operator==(const Hello&) const = default;
};
struct Welcome {  // Host to client: accepted, in this seat.
    std::uint8_t slot = 0;
    bool operator==(const Welcome&) const = default;
};
struct Reject {  // Host to client, before disconnecting it.
    RejectReason reason = RejectReason::Protocol;
    std::string host_version;
    std::vector<ModRef> host_mods;
    bool operator==(const Reject&) const = default;
};
struct Lobby {  // Host to all.
    GameConfig config;
    LobbyPhase phase = LobbyPhase::Lobby;
    std::vector<LobbyPlayer> players;
    bool operator==(const Lobby&) const = default;
};
struct SetInfo {  // Client to host.
    std::string name;
    std::uint8_t color = 0;
    bool ready = false;
    bool operator==(const SetInfo&) const = default;
};
struct Start {  // Host to all: generate the map and build the game.
    GameConfig config;
    std::uint8_t players = 1;  // Seats in the game.
    bool operator==(const Start&) const = default;
};
struct Loaded {  // Client to host: the map is ready.
    std::uint64_t map_hash = 0;
    bool operator==(const Loaded&) const = default;
};
struct Commands {  // Client to host.
    std::vector<sim::Command> commands;
    bool operator==(const Commands&) const = default;
};
struct Turn {  // Host to all: what runs in `tick`.
    std::uint64_t tick = 0;
    std::uint8_t speed = 1;
    std::vector<TurnCommand> commands;
    bool operator==(const Turn&) const = default;
};
struct Ack {  // Client to host: ran up to `tick`; state check on check ticks.
    std::uint64_t tick = 0;
    bool has_hashes = false;
    PartHashes hashes;
    bool operator==(const Ack&) const = default;
};
struct Snapshot {  // Host to client: the whole game at `tick`, zstd-packed.
    std::uint64_t tick = 0;
    std::uint32_t raw_size = 0;
    std::vector<std::uint8_t> packed;
    bool operator==(const Snapshot&) const = default;
};
struct SpeedPropose {  // Client to host.
    std::uint8_t speed = 1;
    bool operator==(const SpeedPropose&) const = default;
};
struct SpeedVote {  // Host to all: someone asks for a speed.
    std::uint32_t id = 0;
    std::uint8_t speed = 1;
    std::uint8_t from = 0;
    bool operator==(const SpeedVote&) const = default;
};
struct SpeedAnswer {  // Client to host.
    std::uint32_t id = 0;
    bool accept = false;
    bool operator==(const SpeedAnswer&) const = default;
};
struct SpeedSet {  // Host to all.
    std::uint8_t speed = 1;
    std::uint8_t by = 0;
    SpeedReason reason = SpeedReason::Vote;
    bool operator==(const SpeedSet&) const = default;
};
struct VoteEnded {  // Host to all: the vote `id` did not pass.
    std::uint32_t id = 0;
    bool operator==(const VoteEnded&) const = default;
};
struct Notice {  // Host to all.
    NoticeKind kind = NoticeKind::Joined;
    std::uint8_t slot = 0;
    std::uint64_t tick = 0;
    bool operator==(const Notice&) const = default;
};

using Message = std::variant<Hello, Welcome, Reject, Lobby, SetInfo, Start, Loaded, Commands, Turn, Ack, Snapshot,
                             SpeedPropose, SpeedVote, SpeedAnswer, SpeedSet, VoteEnded, Notice>;

[[nodiscard]] std::vector<std::uint8_t> encode(const Message& message);
// Nothing if the bytes are not a valid message.
[[nodiscard]] std::optional<Message> decode(std::span<const std::uint8_t> bytes);

void write_config(sim::BinaryWriter& w, const GameConfig& c);
[[nodiscard]] bool read_config(sim::BinaryReader& r, GameConfig& c);

// Player names: 1..32 bytes of UTF-8 without control characters.
[[nodiscard]] bool valid_name(std::string_view name);

// A game's state as a snapshot (Game::save, packed) and back.
[[nodiscard]] Snapshot pack_snapshot(std::uint64_t tick, const std::vector<std::uint8_t>& state);
[[nodiscard]] bool unpack_snapshot(const Snapshot& s, std::vector<std::uint8_t>& state);

}  // namespace sc::net
