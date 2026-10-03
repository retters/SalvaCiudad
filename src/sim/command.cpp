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
    w.u16(def);
    w.i32(value);
    w.u16(def2);
    w.i32(value2);
}

bool Command::read(BinaryReader& r, Command& out) {
    std::uint8_t type = 0;
    Command c;
    if (!r.u8(type) || !r.u8(c.player) || !r.u32(c.entity.index) || !r.u32(c.entity.generation) ||
        !r.vec2(c.position) || !r.u16(c.count) || !r.u16(c.def) || !r.i32(c.value) || !r.u16(c.def2) ||
        !r.i32(c.value2)) {
        return false;
    }
    bool ok = c.player < kMaxPlayers && coordinate_ok(c.position.x) && coordinate_ok(c.position.z);
    switch (static_cast<CommandType>(type)) {
        case CommandType::PlaceBuilding:
            ok = ok && c.value >= 0 && c.value <= 3 && c.position.x >= Fixed{} && c.position.z >= Fixed{};
            break;
        case CommandType::RemoveBuilding:
            ok = ok && c.entity.valid();
            break;
        case CommandType::SetWorkers:
            ok = ok && c.entity.valid() && c.value >= 0 && c.value <= 100;
            break;
        case CommandType::DevGrant:
            ok = ok && c.value >= 1 && c.value <= kMaxDevGrant;
            break;
        case CommandType::PlaceField:
            ok = ok && c.entity.valid() && c.value >= 0 && c.value <= 0xFFFF && c.position.x >= Fixed{} &&
                 c.position.z >= Fixed{};
            break;
        case CommandType::SetCrop:
            ok = ok && c.entity.valid() && (c.value & 0xFF) < 16 && (c.value >> 8) < 3 && c.value >= 0;
            break;
        case CommandType::RemoveField:
            ok = ok && c.entity.valid() && c.value >= 0 && c.value < 16;
            break;
        case CommandType::UpgradeBuilding:
            ok = ok && c.entity.valid();
            break;
        case CommandType::SetLimit:
            ok = ok && c.entity.valid() && c.value >= 0 && c.value <= 10000;
            break;
        case CommandType::DevIgnite:
            ok = ok && c.entity.valid();
            break;
        case CommandType::Trade:
            ok = ok && c.entity.valid() && c.value != 0 && c.value >= -kMaxTrade && c.value <= kMaxTrade;
            break;
        case CommandType::SetTradeRule:
            // Buying up to more than one sells over would trade back and forth.
            ok = ok && c.value >= kNoRule && c.value <= kMaxRule && c.value2 >= kNoRule && c.value2 <= kMaxRule &&
                 (c.value == kNoRule || c.value2 == kNoRule || c.value2 <= c.value) && valid_price_limit(c.count) &&
                 valid_price_limit(c.def2);
            break;
        case CommandType::OfferTrade:
            ok = ok && c.count < kMaxPlayers && c.count != c.player && c.value >= 1 && c.value <= kMaxTrade &&
                 c.value2 >= 1 && c.value2 <= kMaxTrade && c.def != c.def2;
            break;
        case CommandType::AnswerOffer:
            ok = ok && c.value >= 1 && c.count <= 1;
            break;
        case CommandType::RingBell:
            ok = ok && (c.value == 0 || c.value == 1);
            break;
        case CommandType::DevRaid:
        case CommandType::DevLevel:
            break;
        case CommandType::DevSpawn:
            ok = ok && c.value >= 1 && c.value <= 1000;
            break;
        case CommandType::TrainUnit:
            ok = ok && c.entity.valid() && (c.value == 0 || c.value == 1);
            break;
        case CommandType::ArmyOrder:
            ok = ok && c.value >= 0 && c.value <= 2 && c.count < kMaxPlayers && c.position.x >= Fixed{} &&
                 c.position.z >= Fixed{};
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
