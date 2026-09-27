// Runs the world tick by tick: applies the commands scheduled for each tick
// in a fixed order, records everything for replays, and keeps state hashes
// at regular checkpoints to detect desynchronization (section 7.3).
#pragma once

#include <cstdint>
#include <span>
#include <string>
#include <vector>

#include "sim/command.h"
#include "sim/world.h"

namespace sc::sim {

struct Checkpoint {
    std::uint64_t tick = 0;
    std::uint64_t hash = 0;
    bool operator==(const Checkpoint&) const = default;
};

// Everything needed to play a game again exactly: the seed, every command
// with its tick, and the hashes it must produce.
struct Replay {
    std::uint32_t rules_version = kRulesVersion;
    std::uint64_t seed = 0;
    std::uint64_t end_tick = 0;
    std::vector<ScheduledCommand> commands;
    std::vector<Checkpoint> checkpoints;

    bool operator==(const Replay&) const = default;
};

class Simulation {
public:
    // A hash every second of game time (10 ticks).
    static constexpr std::uint64_t kCheckpointInterval = 10;
    static constexpr std::size_t kMaxPendingCommands = 100'000;

    explicit Simulation(std::uint64_t seed);

    // Queues a command for `tick`, which must not be in the past. Commands
    // for the same tick run in the order they were scheduled.
    bool schedule(std::uint64_t tick, const Command& command);
    // Runs one tick.
    void step();

    [[nodiscard]] std::uint64_t tick() const { return world_.tick(); }
    [[nodiscard]] const World& world() const { return world_; }
    [[nodiscard]] const std::vector<Checkpoint>& checkpoints() const { return replay_.checkpoints; }
    [[nodiscard]] std::uint64_t last_hash() const;

    // Everything run so far, as a replay.
    [[nodiscard]] Replay recording() const;

    // Continues from a saved world (for example a save game or a network
    // snapshot). Pending commands and the recording start over.
    [[nodiscard]] bool restore(std::span<const std::uint8_t> world_snapshot);

private:
    World world_;
    std::vector<ScheduledCommand> pending_;  // Sorted by (tick, sequence).
    std::uint32_t next_sequence_ = 0;
    Replay replay_;
};

struct ReplayCheck {
    bool ok = false;
    std::uint64_t mismatch_tick = 0;  // First checkpoint that differed.
    std::string error;                // English, for the log.
};

// Plays a replay from its seed and compares every checkpoint.
[[nodiscard]] ReplayCheck verify_replay(const Replay& replay);

// Binary format with a magic, versions, limits and a checksum.
[[nodiscard]] std::vector<std::uint8_t> encode_replay(const Replay& replay);
[[nodiscard]] bool decode_replay(std::span<const std::uint8_t> bytes, Replay& out, std::string& error);

}  // namespace sc::sim
