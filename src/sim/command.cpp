#include "sim/command.h"

namespace sc::sim {

namespace {

// Commands may only point inside the largest map, with margin.
constexpr std::int32_t kMaxCoordinateMeters = 8192;

bool coordinate_ok(Fixed v) {
    return v >= Fixed::from_int(-kMaxCoordinateMeters) && v <= Fixed::from_int(kMaxCoordinateMeters);
}

}  // namespace

namespace {
bool valid_name_text(std::string_view name, std::size_t max_bytes);
}

bool valid_villager_name(std::string_view name) {
    return valid_name_text(name, kMaxNameBytes);
}

bool valid_seat_name(std::string_view name) {
    return valid_name_text(name, kMaxSeatNameBytes);
}

namespace {

bool valid_name_text(std::string_view name, std::size_t max_bytes) {
    if (name.size() > max_bytes) {
        return false;
    }
    if (!name.empty() && (name.front() == ' ' || name.back() == ' ')) {
        return false;
    }
    // Well-formed UTF-8 (no overlong forms, no surrogates) without controls.
    for (std::size_t i = 0; i < name.size();) {
        const auto c = static_cast<unsigned char>(name[i]);
        std::size_t extra = 0;
        std::uint32_t code = 0;
        std::uint32_t least = 0;
        if (c < 0x80) {
            code = c;
        } else if ((c & 0xE0) == 0xC0) {
            extra = 1;
            code = c & 0x1Fu;
            least = 0x80;
        } else if ((c & 0xF0) == 0xE0) {
            extra = 2;
            code = c & 0x0Fu;
            least = 0x800;
        } else if ((c & 0xF8) == 0xF0) {
            extra = 3;
            code = c & 0x07u;
            least = 0x10000;
        } else {
            return false;
        }
        if (i + extra >= name.size() + (extra == 0 ? 1 : 0)) {
            return false;
        }
        for (std::size_t k = 1; k <= extra; ++k) {
            const auto next = static_cast<unsigned char>(name[i + k]);
            if ((next & 0xC0) != 0x80) {
                return false;
            }
            code = (code << 6) | (next & 0x3Fu);
        }
        if (code < least || code > 0x10FFFF || (code >= 0xD800 && code <= 0xDFFF) || code < 0x20 ||
            (code >= 0x7F && code < 0xA0)) {
            return false;
        }
        i += extra + 1;
    }
    return true;
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
    w.string(text);
}

bool Command::read(BinaryReader& r, Command& out) {
    std::uint8_t type = 0;
    Command c;
    if (!r.u8(type) || !r.u8(c.player) || !r.u32(c.entity.index) || !r.u32(c.entity.generation) ||
        !r.vec2(c.position) || !r.u16(c.count) || !r.u16(c.def) || !r.i32(c.value) || !r.u16(c.def2) ||
        !r.i32(c.value2) || !r.string(kMaxSeatNameBytes, c.text)) {
        return false;
    }
    bool ok = c.player < kMaxPlayers && coordinate_ok(c.position.x) && coordinate_ok(c.position.z);
    // Only a rename and a new seat carry text.
    ok = ok && (static_cast<CommandType>(type) == CommandType::RenameVillager ||
                static_cast<CommandType>(type) == CommandType::AddSeat || c.text.empty());
    switch (static_cast<CommandType>(type)) {
        case CommandType::PlaceBuilding:
        case CommandType::FoundTown:
            ok = ok && c.value >= 0 && c.value <= 3 && c.position.x >= Fixed{} && c.position.z >= Fixed{};
            break;
        case CommandType::Trace:
            ok = ok && c.count <= 1 && c.position.x >= Fixed{} && c.position.z >= Fixed{} && c.value >= 0 &&
                 c.value <= kMaxCoordinateMeters && c.value2 >= 0 && c.value2 <= kMaxCoordinateMeters;
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
        case CommandType::DevBuild:
            break;
        case CommandType::DevSpawn:
            ok = ok && c.value >= 1 && c.value <= 1000;
            break;
        case CommandType::TrainUnit:
            ok = ok && c.entity.valid() && (c.value == 0 || c.value == 1);
            break;
        case CommandType::RenameVillager:
            ok = ok && c.entity.valid() && valid_villager_name(c.text);
            break;
        case CommandType::AddSeat:
            ok = ok && valid_seat_name(c.text) && c.count <= kMaxSeatColor;
            break;
        case CommandType::JoinTown:
        case CommandType::RequestJoin:
        case CommandType::RefuseJoin:
            ok = ok && c.count < kMaxPlayers && c.count != c.player;
            break;
        case CommandType::CancelJoin:
            break;
        case CommandType::SetAccess:
            ok = ok && c.value >= 0 && c.value <= access::kAll;
            break;
        case CommandType::SetProduction:
            ok = ok && c.entity.valid() && (c.value == 0 || c.value == 1);
            break;
        case CommandType::SetOption:
            ok = ok && c.entity.valid() && (c.value == 0 || c.value == 1) && c.count < 8;
            break;
        case CommandType::BuyMale:
            ok = ok && c.entity.valid();
            break;
        case CommandType::SetHerd:
            ok = ok && c.entity.valid() && c.value >= 0 && c.value < 8;
            break;
        case CommandType::AnswerHappening:
            ok = ok && c.def < 16 && (c.value == 1 || c.value == 2);
            break;
        case CommandType::DevBeast:
            ok = ok && c.position.x >= Fixed{} && c.position.z >= Fixed{} && c.def <= 3;
            break;
        case CommandType::DevFeature:
            ok = ok && c.position.x >= Fixed{} && c.position.z >= Fixed{} && c.value > 0 && c.value <= (16 << 16) &&
                 c.value2 >= 0 && c.value2 <= 0xFFFF && c.count < 16 && c.def2 < 256;
            break;
        case CommandType::MoveVillager:
            ok = ok && c.entity.valid() && c.position.x >= Fixed{} && c.position.z >= Fixed{};
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
