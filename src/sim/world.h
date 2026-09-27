// The simulated world. For now a test world of walkers that exercises
// every part of the deterministic core: random numbers, square roots,
// trigonometry, entities appearing and disappearing, and commands. The
// village simulation replaces the walkers from phase 8 on.
#pragma once

#include <cstdint>
#include <span>
#include <vector>

#include "sim/command.h"
#include "sim/entity.h"
#include "sim/fixed.h"
#include "sim/rng.h"
#include "sim/serialize.h"

namespace sc::sim {

// Bump when the simulation rules change: older replays then stop being
// comparable and are rejected with a clear message.
inline constexpr std::uint32_t kRulesVersion = 1;

struct Walker {
    FixedVec2 position;
    FixedVec2 target;
    Fixed speed;              // Meters per tick.
    std::uint16_t wait = 0;   // Ticks to stand still.
    std::int32_t energy = 0;  // Ticks left before leaving.
    std::uint8_t owner = 0;

    bool operator==(const Walker&) const = default;
};

class World {
public:
    static constexpr std::int32_t kHalfSizeMeters = 512;
    static constexpr std::uint32_t kMaxWalkers = 100'000;
    static constexpr std::uint64_t kSpawnEveryTicks = 50;

    explicit World(std::uint64_t seed = 0);

    // Applies a command at the current tick. Invalid ones (a dead entity, a
    // full world) are ignored and counted, the same on every machine.
    void apply(const Command& command);
    // Advances one tick.
    void step();

    [[nodiscard]] std::uint64_t tick() const { return tick_; }
    [[nodiscard]] std::uint64_t hash() const;
    [[nodiscard]] std::uint32_t rejected_commands() const { return rejected_; }
    [[nodiscard]] const EntityRegistry& registry() const { return registry_; }
    [[nodiscard]] const ComponentStore<Walker>& walkers() const { return walkers_; }

    void save(BinaryWriter& w) const;
    // Replaces this world with a saved one. On failure the world is left
    // unchanged and false is returned.
    [[nodiscard]] bool load(BinaryReader& r);

    [[nodiscard]] std::vector<std::uint8_t> snapshot() const;
    [[nodiscard]] bool restore(std::span<const std::uint8_t> bytes);

private:
    EntityId spawn_walker(FixedVec2 position, std::uint8_t owner, Rng& rng);
    [[nodiscard]] static FixedVec2 clamp_to_world(FixedVec2 p);

    std::uint64_t tick_ = 0;
    Rng rng_;        // Walker decisions.
    Rng spawn_rng_;  // Arrivals, so they do not depend on walker decisions.
    EntityRegistry registry_;
    ComponentStore<Walker> walkers_;
    std::uint32_t rejected_ = 0;
};

}  // namespace sc::sim
