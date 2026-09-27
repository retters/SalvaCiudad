#include "sim/simulation.h"

#include <algorithm>
#include <format>

namespace sc::sim {

namespace {

constexpr std::uint8_t kReplayMagic[4] = {'S', 'C', 'R', 'P'};
constexpr std::uint32_t kReplayFormat = 1;
constexpr std::uint32_t kMaxReplayCommands = 10'000'000;
constexpr std::uint32_t kMaxReplayCheckpoints = 10'000'000;
constexpr std::size_t kCommandBytes = 20;
constexpr std::size_t kScheduledBytes = 8 + 4 + kCommandBytes;

}  // namespace

Simulation::Simulation(std::uint64_t seed) : world_(seed) {
    replay_.seed = seed;
}

bool Simulation::schedule(std::uint64_t tick, const Command& command) {
    if (tick < world_.tick() || pending_.size() >= kMaxPendingCommands) {
        return false;
    }
    const ScheduledCommand sc{tick, next_sequence_++, command};
    // Keep the queue sorted; insertion after equal ticks keeps the order.
    const auto at = std::upper_bound(pending_.begin(), pending_.end(), sc, [](const ScheduledCommand& a, const ScheduledCommand& b) {
        return a.tick < b.tick || (a.tick == b.tick && a.sequence < b.sequence);
    });
    pending_.insert(at, sc);
    return true;
}

void Simulation::step() {
    const std::uint64_t now = world_.tick();
    std::size_t applied = 0;
    while (applied < pending_.size() && pending_[applied].tick == now) {
        world_.apply(pending_[applied].command);
        replay_.commands.push_back(pending_[applied]);
        ++applied;
    }
    pending_.erase(pending_.begin(), pending_.begin() + static_cast<std::ptrdiff_t>(applied));
    world_.step();
    replay_.end_tick = world_.tick();
    if (world_.tick() % kCheckpointInterval == 0) {
        replay_.checkpoints.push_back({world_.tick(), world_.hash()});
    }
}

std::uint64_t Simulation::last_hash() const {
    return replay_.checkpoints.empty() ? 0 : replay_.checkpoints.back().hash;
}

Replay Simulation::recording() const {
    return replay_;
}

bool Simulation::restore(std::span<const std::uint8_t> world_snapshot) {
    if (!world_.restore(world_snapshot)) {
        return false;
    }
    pending_.clear();
    replay_.commands.clear();
    replay_.checkpoints.clear();
    replay_.end_tick = world_.tick();
    return true;
}

ReplayCheck verify_replay(const Replay& replay) {
    ReplayCheck result;
    if (replay.rules_version != kRulesVersion) {
        result.error = std::format("replay made with simulation rules {}, this build uses {}", replay.rules_version,
                                   kRulesVersion);
        return result;
    }
    Simulation sim(replay.seed);
    std::size_t next_command = 0;
    std::size_t next_check = 0;
    while (sim.tick() < replay.end_tick) {
        while (next_command < replay.commands.size() && replay.commands[next_command].tick == sim.tick()) {
            (void)sim.schedule(sim.tick(), replay.commands[next_command].command);
            ++next_command;
        }
        if (next_command < replay.commands.size() && replay.commands[next_command].tick < sim.tick()) {
            result.error = "replay commands are out of order";
            return result;
        }
        sim.step();
        while (next_check < replay.checkpoints.size() && replay.checkpoints[next_check].tick == sim.tick()) {
            if (replay.checkpoints[next_check].hash != sim.world().hash()) {
                result.mismatch_tick = sim.tick();
                result.error = std::format("state differs at tick {}", sim.tick());
                return result;
            }
            ++next_check;
        }
    }
    if (next_check != replay.checkpoints.size() || next_command != replay.commands.size()) {
        result.error = "replay has data past its end";
        return result;
    }
    result.ok = true;
    return result;
}

std::vector<std::uint8_t> encode_replay(const Replay& replay) {
    BinaryWriter w;
    w.raw(kReplayMagic);
    w.u32(kReplayFormat);
    w.u32(replay.rules_version);
    w.u64(replay.seed);
    w.u64(replay.end_tick);
    w.u32(static_cast<std::uint32_t>(replay.commands.size()));
    for (const ScheduledCommand& c : replay.commands) {
        w.u64(c.tick);
        w.u32(c.sequence);
        c.command.write(w);
    }
    w.u32(static_cast<std::uint32_t>(replay.checkpoints.size()));
    for (const Checkpoint& c : replay.checkpoints) {
        w.u64(c.tick);
        w.u64(c.hash);
    }
    w.u64(fnv1a64(w.bytes()));
    return std::move(w.bytes());
}

bool decode_replay(std::span<const std::uint8_t> bytes, Replay& out, std::string& error) {
    if (bytes.size() < 4 + 4 + 4 + 8 + 8 + 4 + 4 + 8) {
        error = "file too short";
        return false;
    }
    const auto body = bytes.first(bytes.size() - 8);
    BinaryReader tail(bytes.last(8));
    std::uint64_t checksum = 0;
    if (!tail.u64(checksum) || checksum != fnv1a64(body)) {
        error = "checksum mismatch: the file is damaged";
        return false;
    }
    BinaryReader r(body);
    std::span<const std::uint8_t> magic;
    std::uint32_t format = 0;
    Replay replay;
    if (!r.bytes(4, magic) || !std::equal(magic.begin(), magic.end(), std::begin(kReplayMagic))) {
        error = "not a SalvaCiudad replay";
        return false;
    }
    if (!r.u32(format) || format != kReplayFormat) {
        error = "unsupported replay format";
        return false;
    }
    std::uint32_t count = 0;
    if (!r.u32(replay.rules_version) || !r.u64(replay.seed) || !r.u64(replay.end_tick) ||
        !r.count(kMaxReplayCommands, kScheduledBytes, count)) {
        error = "damaged replay header";
        return false;
    }
    replay.commands.reserve(count);
    std::uint64_t last_tick = 0;
    for (std::uint32_t i = 0; i < count; ++i) {
        ScheduledCommand c;
        if (!r.u64(c.tick) || !r.u32(c.sequence) || !Command::read(r, c.command) || c.tick < last_tick ||
            c.tick >= replay.end_tick) {
            error = std::format("invalid command {}", i);
            return false;
        }
        last_tick = c.tick;
        replay.commands.push_back(c);
    }
    if (!r.count(kMaxReplayCheckpoints, 16, count)) {
        error = "damaged checkpoint list";
        return false;
    }
    replay.checkpoints.reserve(count);
    for (std::uint32_t i = 0; i < count; ++i) {
        Checkpoint c;
        if (!r.u64(c.tick) || !r.u64(c.hash) || c.tick > replay.end_tick ||
            (!replay.checkpoints.empty() && c.tick <= replay.checkpoints.back().tick)) {
            error = std::format("invalid checkpoint {}", i);
            return false;
        }
        replay.checkpoints.push_back(c);
    }
    if (!r.at_end()) {
        error = "unexpected data at the end";
        return false;
    }
    out = std::move(replay);
    return true;
}

}  // namespace sc::sim
