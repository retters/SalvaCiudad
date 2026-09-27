#include "net/enet_link.h"

#include <algorithm>
#include <cstring>

#include <enet/enet.h>

#include "core/log.h"
#include "net/protocol.h"
#include "sim/serialize.h"

namespace sc::net {

namespace {

constexpr std::size_t kMaxPacketBytes = 128u * 1024u * 1024u;
constexpr std::uint32_t kConnectTimeoutMs = 8000;
constexpr std::uint64_t kProbeEveryMs = 1000;
constexpr std::uint64_t kForgetAfterMs = 5000;
constexpr char kProbeMagic[8] = {'S', 'C', 'P', 'R', 'O', 'B', 'E', '1'};
constexpr char kAnswerMagic[8] = {'S', 'C', 'G', 'A', 'M', 'E', '1', '\0'};

ENetSocket as_socket(std::uintptr_t s) {
    return static_cast<ENetSocket>(s);
}

}  // namespace

// --- Library -----------------------------------------------------------------------

EnetLibrary::EnetLibrary() : ok_(enet_initialize() == 0) {
    if (!ok_) {
        log::error("net: ENet could not start");
    }
}

EnetLibrary::~EnetLibrary() {
    if (ok_) {
        enet_deinitialize();
    }
}

// --- Link --------------------------------------------------------------------------

EnetLink::~EnetLink() {
    if (host_ != nullptr) {
        enet_host_destroy(host_);
    }
}

bool EnetLink::listen(std::uint16_t port, std::size_t max_clients, bool loopback_only) {
    ENetAddress address{};
    address.host = ENET_HOST_ANY;
    if (loopback_only && enet_address_set_host_ip(&address, "127.0.0.1") != 0) {
        return false;
    }
    address.port = port;
    host_ = enet_host_create(&address, max_clients, 1, 0, 0);
    if (host_ == nullptr) {
        log::error("net: cannot listen on port {}", port);
        return false;
    }
    host_->maximumPacketSize = kMaxPacketBytes;
    return true;
}

bool EnetLink::connect(const std::string& address_text, std::uint16_t port) {
    host_ = enet_host_create(nullptr, 1, 1, 0, 0);
    if (host_ == nullptr) {
        return false;
    }
    host_->maximumPacketSize = kMaxPacketBytes;
    ENetAddress address{};
    address.port = port;
    if (enet_address_set_host_ip(&address, address_text.c_str()) != 0 &&
        enet_address_set_host(&address, address_text.c_str()) != 0) {
        log::warn("net: cannot resolve the host address");
        return false;
    }
    ENetPeer* peer = enet_host_connect(host_, &address, 1, 0);
    if (peer == nullptr) {
        return false;
    }
    enet_peer_timeout(peer, 0, kConnectTimeoutMs, kConnectTimeoutMs * 2);
    server_ = next_++;
    peer->data = reinterpret_cast<void*>(static_cast<std::uintptr_t>(server_));
    peers_[server_] = peer;
    return true;
}

void EnetLink::service() {
    if (host_ == nullptr) {
        return;
    }
    ENetEvent e;
    while (enet_host_service(host_, &e, 0) > 0) {
        switch (e.type) {
            case ENET_EVENT_TYPE_CONNECT: {
                PeerId id = static_cast<PeerId>(reinterpret_cast<std::uintptr_t>(e.peer->data));
                if (id == 0) {  // A client arriving at the host.
                    id = next_++;
                    e.peer->data = reinterpret_cast<void*>(static_cast<std::uintptr_t>(id));
                    peers_[id] = e.peer;
                }
                events_.push_back({LinkEvent::Type::Connected, id, {}});
                break;
            }
            case ENET_EVENT_TYPE_RECEIVE: {
                const auto id = static_cast<PeerId>(reinterpret_cast<std::uintptr_t>(e.peer->data));
                events_.push_back({LinkEvent::Type::Received, id,
                                   std::vector<std::uint8_t>(e.packet->data, e.packet->data + e.packet->dataLength)});
                enet_packet_destroy(e.packet);
                break;
            }
            case ENET_EVENT_TYPE_DISCONNECT: {
                const auto id = static_cast<PeerId>(reinterpret_cast<std::uintptr_t>(e.peer->data));
                peers_.erase(id);
                e.peer->data = nullptr;
                events_.push_back({LinkEvent::Type::Disconnected, id, {}});
                break;
            }
            case ENET_EVENT_TYPE_NONE: break;
        }
    }
}

void EnetLink::send(PeerId peer, std::span<const std::uint8_t> data) {
    const auto it = peers_.find(peer);
    if (it == peers_.end() || data.size() > kMaxPacketBytes) {
        return;
    }
    ENetPacket* packet = enet_packet_create(data.data(), data.size(), ENET_PACKET_FLAG_RELIABLE);
    if (packet != nullptr && enet_peer_send(it->second, 0, packet) != 0) {
        enet_packet_destroy(packet);
    }
}

void EnetLink::disconnect(PeerId peer) {
    const auto it = peers_.find(peer);
    if (it != peers_.end()) {
        enet_peer_disconnect_later(it->second, 0);
    }
}

bool EnetLink::poll(LinkEvent& event) {
    if (events_.empty()) {
        service();
    }
    if (events_.empty()) {
        return false;
    }
    event = std::move(events_.front());
    events_.pop_front();
    return true;
}

std::uint32_t EnetLink::round_trip_ms(PeerId peer) const {
    const auto it = peers_.find(peer);
    return it == peers_.end() ? 0 : it->second->roundTripTime;
}

void EnetLink::close() {
    if (host_ == nullptr) {
        return;
    }
    for (auto& [id, peer] : peers_) {
        enet_peer_disconnect_later(peer, 0);
    }
    enet_host_flush(host_);
}

// --- Discovery ---------------------------------------------------------------------

std::vector<std::uint8_t> discovery_probe() {
    sim::BinaryWriter w;
    w.raw({reinterpret_cast<const std::uint8_t*>(kProbeMagic), sizeof(kProbeMagic)});
    w.u32(kProtocolVersion);
    return std::move(w.bytes());
}

bool is_discovery_probe(std::span<const std::uint8_t> data) {
    return data.size() == sizeof(kProbeMagic) + 4 && std::memcmp(data.data(), kProbeMagic, sizeof(kProbeMagic)) == 0;
}

std::vector<std::uint8_t> discovery_answer(std::uint16_t port, const std::string& host_name, std::uint8_t players,
                                           bool playing) {
    sim::BinaryWriter w;
    w.raw({reinterpret_cast<const std::uint8_t*>(kAnswerMagic), sizeof(kAnswerMagic)});
    w.u32(kProtocolVersion);
    w.u16(port);
    w.u8(players);
    w.u8(playing ? 1 : 0);
    w.string(host_name);
    return std::move(w.bytes());
}

bool read_discovery_answer(std::span<const std::uint8_t> data, LanGame& out) {
    if (data.size() < sizeof(kAnswerMagic) || data.size() > 256 ||
        std::memcmp(data.data(), kAnswerMagic, sizeof(kAnswerMagic)) != 0) {
        return false;
    }
    sim::BinaryReader r(data.subspan(sizeof(kAnswerMagic)));
    std::uint32_t protocol = 0;
    std::uint8_t playing = 0;
    if (!r.u32(protocol) || protocol != kProtocolVersion || !r.u16(out.port) || out.port == 0 || !r.u8(out.players) ||
        out.players > sim::kMaxPlayers || !r.u8(playing) || playing > 1 || !r.string(kMaxNameBytes, out.host_name) ||
        !valid_name(out.host_name) || !r.at_end()) {
        return false;
    }
    out.playing = playing != 0;
    return true;
}

LanDiscovery::~LanDiscovery() {
    if (socket_ != ~std::uintptr_t{0}) {
        enet_socket_destroy(as_socket(socket_));
    }
}

bool LanDiscovery::announce(std::uint16_t game_port) {
    const ENetSocket s = enet_socket_create(ENET_SOCKET_TYPE_DATAGRAM);
    if (s == ENET_SOCKET_NULL) {
        return false;
    }
    enet_socket_set_option(s, ENET_SOCKOPT_NONBLOCK, 1);
    enet_socket_set_option(s, ENET_SOCKOPT_REUSEADDR, 1);
    ENetAddress address{};
    address.host = ENET_HOST_ANY;
    address.port = kDiscoveryPort;
    if (enet_socket_bind(s, &address) != 0) {
        log::warn("net: the discovery port is busy; this game will not be listed on the local network");
        enet_socket_destroy(s);
        return false;
    }
    socket_ = static_cast<std::uintptr_t>(s);
    host_ = true;
    game_port_ = game_port;
    return true;
}

void LanDiscovery::set_game(const std::string& host_name, std::uint8_t players, bool playing) {
    host_name_ = host_name;
    players_ = players;
    playing_ = playing;
}

bool LanDiscovery::search() {
    const ENetSocket s = enet_socket_create(ENET_SOCKET_TYPE_DATAGRAM);
    if (s == ENET_SOCKET_NULL) {
        return false;
    }
    enet_socket_set_option(s, ENET_SOCKOPT_NONBLOCK, 1);
    enet_socket_set_option(s, ENET_SOCKOPT_BROADCAST, 1);
    ENetAddress any{};
    any.host = ENET_HOST_ANY;
    any.port = 0;
    if (enet_socket_bind(s, &any) != 0) {
        enet_socket_destroy(s);
        return false;
    }
    socket_ = static_cast<std::uintptr_t>(s);
    host_ = false;
    return true;
}

void LanDiscovery::update(std::uint64_t now_ms) {
    if (socket_ == ~std::uintptr_t{0}) {
        return;
    }
    const ENetSocket s = as_socket(socket_);
    std::uint8_t buffer[512];
    for (int i = 0; i < 64; ++i) {
        ENetAddress from{};
        ENetBuffer b{};
        b.data = buffer;
        b.dataLength = sizeof(buffer);
        const int n = enet_socket_receive(s, &from, &b, 1);
        if (n <= 0) {
            break;
        }
        const std::span<const std::uint8_t> data(buffer, static_cast<std::size_t>(n));
        if (host_) {
            if (is_discovery_probe(data)) {
                const std::vector<std::uint8_t> answer = discovery_answer(game_port_, host_name_, players_, playing_);
                ENetBuffer out{};
                out.data = const_cast<std::uint8_t*>(answer.data());
                out.dataLength = answer.size();
                (void)enet_socket_send(s, &from, &out, 1);
            }
            continue;
        }
        LanGame g;
        char ip[64] = {};
        if (read_discovery_answer(data, g) && enet_address_get_host_ip(&from, ip, sizeof(ip)) == 0) {
            g.address = ip;
            g.seen_ms = now_ms;
            const auto it = std::find(games_.begin(), games_.end(), g);
            if (it != games_.end()) {
                *it = g;
            } else if (games_.size() < 64) {
                games_.push_back(g);
            }
        }
    }
    if (!host_) {
        std::erase_if(games_, [&](const LanGame& g) { return now_ms - g.seen_ms > kForgetAfterMs; });
        if (now_ms - last_probe_ms_ >= kProbeEveryMs) {
            last_probe_ms_ = now_ms;
            const std::vector<std::uint8_t> probe = discovery_probe();
            ENetBuffer out{};
            out.data = const_cast<std::uint8_t*>(probe.data());
            out.dataLength = probe.size();
            ENetAddress to{};
            to.host = ENET_HOST_BROADCAST;
            to.port = kDiscoveryPort;
            (void)enet_socket_send(s, &to, &out, 1);
        }
    }
}

}  // namespace sc::net
