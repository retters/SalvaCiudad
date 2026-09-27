#include "sim/command.h"

namespace sc::sim {

namespace {

// Commands may only point inside the largest map, with margin.
constexpr std::int32_t kMaxCoordinateMeters = 8192;

bool coordinate_ok(Fixed v) {
    return v >= Fixed::from_int(-kMaxCoordinateMeters) && v <= Fixed::from_int(kMaxCoordinateMeters);
}

}  // namespace

void Command::write(BinaryWriter& w) const {
    w.u8(static_cast<std::uint8_t>(type));
    w.u8(player);
    w.u32(entity.index);
    w.u32(entity.generation);
    w.vec2(position);
    w.u16(count);
}

bool Command::read(BinaryReader& r, Command& out) {
    std::uint8_t type = 0;
    Command c;
    if (!r.u8(type) || !r.u8(c.player) || !r.u32(c.entity.index) || !r.u32(c.entity.generation) ||
        !r.vec2(c.position) || !r.u16(c.count)) {
        return false;
    }
    bool ok = c.player < kMaxPlayers && coordinate_ok(c.position.x) && coordinate_ok(c.position.z);
    switch (static_cast<CommandType>(type)) {
        case CommandType::SpawnWalkers:
            ok = ok && c.count >= 1 && c.count <= kMaxSpawnPerCommand;
            break;
        case CommandType::SendWalker:
        case CommandType::RemoveWalker:
            ok = ok && c.entity.valid();
            break;
        default:
            ok = false;
            break;
    }
    if (!ok) {
        r.fail();
        return false;
    }
    c.type = static_cast<CommandType>(type);
    out = c;
    return true;
}

}  // namespace sc::sim
