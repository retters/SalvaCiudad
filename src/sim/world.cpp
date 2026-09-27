#include "sim/world.h"

#include <utility>

namespace sc::sim {

namespace {

constexpr std::uint32_t kSnapshotVersion = 1;
constexpr std::uint64_t kWalkerStream = 1;
constexpr std::uint64_t kSpawnStream = 2;

}  // namespace

World::World(std::uint64_t seed) : rng_(seed, kWalkerStream), spawn_rng_(seed, kSpawnStream) {}

FixedVec2 World::clamp_to_world(FixedVec2 p) {
    const Fixed lo = Fixed::from_int(-kHalfSizeMeters);
    const Fixed hi = Fixed::from_int(kHalfSizeMeters);
    const auto clamp = [&](Fixed v) { return v < lo ? lo : (v > hi ? hi : v); };
    return {clamp(p.x), clamp(p.z)};
}

EntityId World::spawn_walker(FixedVec2 position, std::uint8_t owner, Rng& rng) {
    if (walkers_.size() >= kMaxWalkers) {
        return {};
    }
    const EntityId id = registry_.create();
    if (!id.valid()) {
        return {};
    }
    Walker w;
    w.position = clamp_to_world(position);
    w.target = w.position;
    w.speed = Fixed::from_ratio(rng.range(10, 20), 100);  // 1 to 2 m/s at 10 ticks per second.
    w.energy = rng.range(200, 3000);
    w.owner = owner;
    walkers_.add(id, w);
    return id;
}

void World::apply(const Command& c) {
    switch (c.type) {
        case CommandType::SpawnWalkers: {
            for (std::uint16_t i = 0; i < c.count; ++i) {
                // Spread the group around the point.
                const Angle a = spawn_rng_.angle();
                const Fixed r = Fixed::from_int(spawn_rng_.range(0, 8));
                if (!spawn_walker(c.position + FixedVec2{cos(a) * r, sin(a) * r}, c.player, spawn_rng_).valid()) {
                    ++rejected_;
                    return;
                }
            }
            return;
        }
        case CommandType::SendWalker: {
            Walker* w = registry_.alive(c.entity) ? walkers_.get(c.entity) : nullptr;
            if (w == nullptr) {
                ++rejected_;
                return;
            }
            w->target = clamp_to_world(c.position);
            w->wait = 0;
            return;
        }
        case CommandType::RemoveWalker: {
            if (!registry_.alive(c.entity) || !walkers_.remove(c.entity)) {
                ++rejected_;
                return;
            }
            registry_.destroy(c.entity);
            return;
        }
    }
    ++rejected_;
}

void World::step() {
    std::vector<EntityId> expired;
    const std::vector<EntityId>& ids = walkers_.entities();
    std::vector<Walker>& data = walkers_.data();
    for (std::size_t i = 0; i < data.size(); ++i) {
        Walker& w = data[i];
        w.energy -= 1;
        if (w.energy <= 0) {
            expired.push_back(ids[i]);
            continue;
        }
        if (w.wait > 0) {
            --w.wait;
            continue;
        }
        const FixedVec2 to = w.target - w.position;
        if (to.length() <= w.speed) {
            // Arrived: rest a moment, then wander somewhere nearby.
            w.position = w.target;
            const Angle a = rng_.angle();
            const Fixed r = Fixed::from_int(rng_.range(5, 60));
            w.target = clamp_to_world(w.position + FixedVec2{cos(a) * r, sin(a) * r});
            w.wait = static_cast<std::uint16_t>(rng_.below(20));
        } else {
            w.position = w.position + to.normalized() * w.speed;
        }
    }
    // Remove after the loop, in the order found, so iteration was stable.
    for (const EntityId id : expired) {
        walkers_.remove(id);
        registry_.destroy(id);
    }
    ++tick_;
    if (tick_ % kSpawnEveryTicks == 0) {
        const FixedVec2 p{Fixed::from_int(spawn_rng_.range(-kHalfSizeMeters, kHalfSizeMeters)),
                          Fixed::from_int(spawn_rng_.range(-kHalfSizeMeters, kHalfSizeMeters))};
        (void)spawn_walker(p, 0, spawn_rng_);
    }
}

void World::save(BinaryWriter& w) const {
    w.u32(kSnapshotVersion);
    w.u32(kRulesVersion);
    w.u64(tick_);
    w.u64(rng_.state());
    w.u64(rng_.increment());
    w.u64(spawn_rng_.state());
    w.u64(spawn_rng_.increment());
    w.u32(rejected_);

    w.u32(registry_.slot_count());
    for (std::uint32_t i = 0; i < registry_.slot_count(); ++i) {
        w.u32(registry_.generations()[i]);
        w.u8(registry_.alive_flags()[i]);
    }
    w.u32(static_cast<std::uint32_t>(registry_.free_slots().size()));
    for (const std::uint32_t f : registry_.free_slots()) {
        w.u32(f);
    }

    // Dense order is saved as is, so iteration continues identically.
    w.u32(static_cast<std::uint32_t>(walkers_.size()));
    for (std::size_t i = 0; i < walkers_.size(); ++i) {
        const EntityId id = walkers_.entities()[i];
        const Walker& k = walkers_.data()[i];
        w.u32(id.index);
        w.u32(id.generation);
        w.vec2(k.position);
        w.vec2(k.target);
        w.fixed(k.speed);
        w.u16(k.wait);
        w.i32(k.energy);
        w.u8(k.owner);
    }
}

bool World::load(BinaryReader& r) {
    World loaded;
    std::uint32_t version = 0;
    std::uint32_t rules = 0;
    std::uint64_t s1 = 0, i1 = 0, s2 = 0, i2 = 0;
    if (!r.u32(version) || version != kSnapshotVersion || !r.u32(rules) || rules != kRulesVersion ||
        !r.u64(loaded.tick_) || !r.u64(s1) || !r.u64(i1) || !r.u64(s2) || !r.u64(i2) || !r.u32(loaded.rejected_) ||
        !Rng::restore(s1, i1, loaded.rng_) || !Rng::restore(s2, i2, loaded.spawn_rng_)) {
        return false;
    }

    std::uint32_t slots = 0;
    if (!r.count(EntityRegistry::kMaxEntities, 5, slots)) {
        return false;
    }
    std::vector<std::uint32_t> generations(slots);
    std::vector<std::uint8_t> alive(slots);
    for (std::uint32_t i = 0; i < slots; ++i) {
        if (!r.u32(generations[i]) || !r.u8(alive[i])) {
            return false;
        }
    }
    std::uint32_t free_count = 0;
    if (!r.count(slots, 4, free_count)) {
        return false;
    }
    std::vector<std::uint32_t> free(free_count);
    for (std::uint32_t i = 0; i < free_count; ++i) {
        if (!r.u32(free[i])) {
            return false;
        }
    }
    if (!loaded.registry_.restore(std::move(generations), std::move(alive), std::move(free))) {
        return false;
    }

    std::uint32_t count = 0;
    constexpr std::size_t kWalkerBytes = 4 + 4 + 8 + 8 + 4 + 2 + 4 + 1;
    if (!r.count(kMaxWalkers, kWalkerBytes, count)) {
        return false;
    }
    const Fixed limit = Fixed::from_int(kHalfSizeMeters);
    for (std::uint32_t i = 0; i < count; ++i) {
        EntityId id;
        Walker k;
        if (!r.u32(id.index) || !r.u32(id.generation) || !r.vec2(k.position) || !r.vec2(k.target) ||
            !r.fixed(k.speed) || !r.u16(k.wait) || !r.i32(k.energy) || !r.u8(k.owner)) {
            return false;
        }
        const auto inside = [&](FixedVec2 p) { return abs(p.x) <= limit && abs(p.z) <= limit; };
        // Each walker must belong to a live entity, once, with sane values.
        if (!loaded.registry_.alive(id) || loaded.walkers_.get(id) != nullptr || !inside(k.position) ||
            !inside(k.target) || k.speed <= Fixed{} || k.speed > Fixed::one() || k.owner >= kMaxPlayers) {
            return false;
        }
        loaded.walkers_.add(id, k);
    }
    if (!r.at_end()) {
        return false;
    }
    *this = std::move(loaded);
    return true;
}

std::vector<std::uint8_t> World::snapshot() const {
    BinaryWriter w;
    save(w);
    return std::move(w.bytes());
}

bool World::restore(std::span<const std::uint8_t> bytes) {
    BinaryReader r(bytes);
    return load(r);
}

std::uint64_t World::hash() const {
    BinaryWriter w;
    save(w);
    return fnv1a64(w.bytes());
}

}  // namespace sc::sim
