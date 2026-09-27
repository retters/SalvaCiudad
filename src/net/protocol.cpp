#include "net/protocol.h"

#include <zstd.h>

#include "core/text.h"

namespace sc::net {

namespace {

using sim::BinaryReader;
using sim::BinaryWriter;

constexpr std::size_t kMaxVersionBytes = 40;
constexpr std::size_t kMaxModIdBytes = 64;
constexpr std::size_t kMaxPlayers = sim::kMaxPlayers;

void write_mods(BinaryWriter& w, const std::vector<ModRef>& mods) {
    w.u32(static_cast<std::uint32_t>(mods.size()));
    for (const ModRef& m : mods) {
        w.string(m.id);
        w.string(m.version);
        w.u64(m.hash);
    }
}

bool read_mods(BinaryReader& r, std::vector<ModRef>& mods) {
    std::uint32_t n = 0;
    if (!r.count(kMaxMods, 16, n)) {
        return false;
    }
    mods.resize(n);
    for (ModRef& m : mods) {
        if (!r.string(kMaxModIdBytes, m.id) || !r.string(kMaxVersionBytes, m.version) || !r.u64(m.hash)) {
            return false;
        }
    }
    return true;
}

bool read_bool(BinaryReader& r, bool& out) {
    std::uint8_t v = 0;
    if (!r.u8(v) || v > 1) {
        r.fail();
        return false;
    }
    out = v != 0;
    return true;
}

bool read_name(BinaryReader& r, std::string& out) {
    if (!r.string(kMaxNameBytes, out) || !valid_name(out)) {
        r.fail();
        return false;
    }
    return true;
}

bool read_speed(BinaryReader& r, std::uint8_t& speed) {
    if (!r.u8(speed) || speed > 3) {
        r.fail();
        return false;
    }
    return true;
}

bool read_slot(BinaryReader& r, std::uint8_t& slot) {
    if (!r.u8(slot) || slot >= kMaxPlayers) {
        r.fail();
        return false;
    }
    return true;
}

template <typename E>
bool read_enum(BinaryReader& r, E& out) {
    std::uint8_t v = 0;
    if (!r.u8(v) || v >= static_cast<std::uint8_t>(E::Count)) {
        r.fail();
        return false;
    }
    out = static_cast<E>(v);
    return true;
}

// --- Per message ----------------------------------------------------------------

void write(BinaryWriter& w, const Hello& m) {
    w.u32(m.protocol);
    w.string(m.game_version);
    w.u64(m.content_hash);
    write_mods(w, m.mods);
    w.string(m.name);
}
bool read(BinaryReader& r, Hello& m) {
    // The protocol number first: a newer client may send other fields.
    return r.u32(m.protocol) && r.string(kMaxVersionBytes, m.game_version) && r.u64(m.content_hash) &&
           read_mods(r, m.mods) && read_name(r, m.name);
}

void write(BinaryWriter& w, const Welcome& m) { w.u8(m.slot); }
bool read(BinaryReader& r, Welcome& m) { return read_slot(r, m.slot); }

void write(BinaryWriter& w, const Reject& m) {
    w.u8(static_cast<std::uint8_t>(m.reason));
    w.string(m.host_version);
    write_mods(w, m.host_mods);
}
bool read(BinaryReader& r, Reject& m) {
    return read_enum(r, m.reason) && r.string(kMaxVersionBytes, m.host_version) && read_mods(r, m.host_mods);
}

void write(BinaryWriter& w, const Lobby& m) {
    write_config(w, m.config);
    w.u8(static_cast<std::uint8_t>(m.phase));
    w.u8(static_cast<std::uint8_t>(m.players.size()));
    for (const LobbyPlayer& p : m.players) {
        w.u8(p.slot);
        w.string(p.name);
        w.u8(p.color);
        w.u8(p.ready ? 1 : 0);
        w.u8(p.connected ? 1 : 0);
        w.u8(p.loaded ? 1 : 0);
    }
}
bool read(BinaryReader& r, Lobby& m) {
    std::uint8_t n = 0;
    if (!read_config(r, m.config) || !read_enum(r, m.phase) || !r.u8(n) || n > kMaxPlayers) {
        r.fail();
        return false;
    }
    m.players.resize(n);
    for (LobbyPlayer& p : m.players) {
        if (!read_slot(r, p.slot) || !read_name(r, p.name) || !r.u8(p.color) || p.color >= kColors ||
            !read_bool(r, p.ready) || !read_bool(r, p.connected) || !read_bool(r, p.loaded)) {
            r.fail();
            return false;
        }
    }
    return true;
}

void write(BinaryWriter& w, const SetInfo& m) {
    w.string(m.name);
    w.u8(m.color);
    w.u8(m.ready ? 1 : 0);
}
bool read(BinaryReader& r, SetInfo& m) {
    if (!read_name(r, m.name) || !r.u8(m.color) || m.color >= kColors || !read_bool(r, m.ready)) {
        r.fail();
        return false;
    }
    return true;
}

void write(BinaryWriter& w, const Start& m) {
    write_config(w, m.config);
    w.u8(m.players);
}
bool read(BinaryReader& r, Start& m) {
    if (!read_config(r, m.config) || !r.u8(m.players) || m.players < 1 || m.players > kMaxPlayers) {
        r.fail();
        return false;
    }
    return true;
}

void write(BinaryWriter& w, const Loaded& m) { w.u64(m.map_hash); }
bool read(BinaryReader& r, Loaded& m) { return r.u64(m.map_hash); }

void write(BinaryWriter& w, const Commands& m) {
    w.u32(static_cast<std::uint32_t>(m.commands.size()));
    for (const sim::Command& c : m.commands) {
        c.write(w);
    }
}
bool read(BinaryReader& r, Commands& m) {
    std::uint32_t n = 0;
    if (!r.count(kMaxCommandsPerMessage, 26, n)) {
        return false;
    }
    m.commands.resize(n);
    for (sim::Command& c : m.commands) {
        if (!sim::Command::read(r, c)) {
            return false;
        }
    }
    return true;
}

void write(BinaryWriter& w, const Turn& m) {
    w.u64(m.tick);
    w.u8(m.speed);
    w.u32(static_cast<std::uint32_t>(m.commands.size()));
    for (const TurnCommand& c : m.commands) {
        w.u8(c.player);
        c.command.write(w);
    }
}
bool read(BinaryReader& r, Turn& m) {
    std::uint32_t n = 0;
    if (!r.u64(m.tick) || !read_speed(r, m.speed) || !r.count(kMaxCommandsPerTurn, 27, n)) {
        return false;
    }
    m.commands.resize(n);
    for (TurnCommand& c : m.commands) {
        if (!read_slot(r, c.player) || !sim::Command::read(r, c.command) || c.command.player != c.player) {
            r.fail();
            return false;
        }
    }
    return true;
}

void write(BinaryWriter& w, const Ack& m) {
    w.u64(m.tick);
    w.u8(m.has_hashes ? 1 : 0);
    if (m.has_hashes) {
        for (const std::uint64_t h : m.hashes.parts) {
            w.u64(h);
        }
    }
}
bool read(BinaryReader& r, Ack& m) {
    if (!r.u64(m.tick) || !read_bool(r, m.has_hashes)) {
        return false;
    }
    for (std::size_t i = 0; m.has_hashes && i < m.hashes.parts.size(); ++i) {
        if (!r.u64(m.hashes.parts[i])) {
            return false;
        }
    }
    return true;
}

void write(BinaryWriter& w, const Snapshot& m) {
    w.u64(m.tick);
    w.u32(m.raw_size);
    w.u32(static_cast<std::uint32_t>(m.packed.size()));
    w.raw(m.packed);
}
bool read(BinaryReader& r, Snapshot& m) {
    std::uint32_t n = 0;
    std::span<const std::uint8_t> bytes;
    if (!r.u64(m.tick) || !r.u32(m.raw_size) || m.raw_size > kMaxSnapshotBytes || !r.u32(n) || !r.bytes(n, bytes)) {
        r.fail();
        return false;
    }
    m.packed.assign(bytes.begin(), bytes.end());
    return true;
}

void write(BinaryWriter& w, const SpeedPropose& m) { w.u8(m.speed); }
bool read(BinaryReader& r, SpeedPropose& m) { return read_speed(r, m.speed); }

void write(BinaryWriter& w, const SpeedVote& m) {
    w.u32(m.id);
    w.u8(m.speed);
    w.u8(m.from);
}
bool read(BinaryReader& r, SpeedVote& m) { return r.u32(m.id) && read_speed(r, m.speed) && read_slot(r, m.from); }

void write(BinaryWriter& w, const SpeedAnswer& m) {
    w.u32(m.id);
    w.u8(m.accept ? 1 : 0);
}
bool read(BinaryReader& r, SpeedAnswer& m) { return r.u32(m.id) && read_bool(r, m.accept); }

void write(BinaryWriter& w, const SpeedSet& m) {
    w.u8(m.speed);
    w.u8(m.by);
    w.u8(static_cast<std::uint8_t>(m.reason));
}
bool read(BinaryReader& r, SpeedSet& m) { return read_speed(r, m.speed) && read_slot(r, m.by) && read_enum(r, m.reason); }

void write(BinaryWriter& w, const VoteEnded& m) { w.u32(m.id); }
bool read(BinaryReader& r, VoteEnded& m) { return r.u32(m.id); }

void write(BinaryWriter& w, const Notice& m) {
    w.u8(static_cast<std::uint8_t>(m.kind));
    w.u8(m.slot);
    w.u64(m.tick);
}
bool read(BinaryReader& r, Notice& m) { return read_enum(r, m.kind) && read_slot(r, m.slot) && r.u64(m.tick); }

template <std::size_t I = 0>
bool read_alternative(std::size_t index, BinaryReader& r, Message& out) {
    if constexpr (I < std::variant_size_v<Message>) {
        if (index == I) {
            std::variant_alternative_t<I, Message> m{};
            if (!read(r, m)) {
                return false;
            }
            out = std::move(m);
            return true;
        }
        return read_alternative<I + 1>(index, r, out);
    } else {
        return false;
    }
}

template <std::size_t I = 0>
void write_alternative(BinaryWriter& w, const Message& m) {
    if constexpr (I < std::variant_size_v<Message>) {
        if (const auto* v = std::get_if<I>(&m)) {
            write(w, *v);
            return;
        }
        write_alternative<I + 1>(w, m);
    }
}

}  // namespace

bool valid_name(std::string_view name) {
    if (name.empty() || name.size() > kMaxNameBytes || !text::is_valid_utf8(name)) {
        return false;
    }
    for (const char c : name) {
        if (static_cast<unsigned char>(c) < 0x20 || c == 0x7F) {
            return false;
        }
    }
    return true;
}

void write_config(BinaryWriter& w, const GameConfig& c) {
    c.map.write(w);
    w.u8(c.shared_town ? 1 : 0);
    w.u64(c.seed);
}

bool read_config(BinaryReader& r, GameConfig& c) {
    return sim::MapSettings::read(r, c.map) && read_bool(r, c.shared_town) && r.u64(c.seed);
}

std::vector<std::uint8_t> encode(const Message& message) {
    BinaryWriter w;
    w.u8(static_cast<std::uint8_t>(message.index() + 1));
    write_alternative(w, message);
    return std::move(w.bytes());
}

std::optional<Message> decode(std::span<const std::uint8_t> bytes) {
    if (bytes.empty()) {
        return std::nullopt;
    }
    const std::size_t index = static_cast<std::size_t>(bytes[0]) - 1;
    // Only snapshots may be big.
    const bool snapshot = index == static_cast<std::size_t>(Message(Snapshot{}).index());
    if (index >= std::variant_size_v<Message> || (!snapshot && bytes.size() > kMaxMessageBytes)) {
        return std::nullopt;
    }
    BinaryReader r(bytes.subspan(1));
    Message out;
    if (!read_alternative(index, r, out) || !r.at_end()) {
        return std::nullopt;
    }
    return out;
}

Snapshot pack_snapshot(std::uint64_t tick, const std::vector<std::uint8_t>& state) {
    Snapshot s;
    s.tick = tick;
    s.raw_size = static_cast<std::uint32_t>(state.size());
    s.packed.resize(ZSTD_compressBound(state.size()));
    const std::size_t n = ZSTD_compress(s.packed.data(), s.packed.size(), state.data(), state.size(), 3);
    if (ZSTD_isError(n) != 0) {
        s.packed.clear();
        s.raw_size = 0;
        return s;
    }
    s.packed.resize(n);
    return s;
}

bool unpack_snapshot(const Snapshot& s, std::vector<std::uint8_t>& state) {
    if (s.raw_size == 0 || s.raw_size > kMaxSnapshotBytes ||
        ZSTD_getFrameContentSize(s.packed.data(), s.packed.size()) != s.raw_size) {
        return false;
    }
    state.resize(s.raw_size);
    const std::size_t n = ZSTD_decompress(state.data(), state.size(), s.packed.data(), s.packed.size());
    return ZSTD_isError(n) == 0 && n == s.raw_size;
}

}  // namespace sc::net
