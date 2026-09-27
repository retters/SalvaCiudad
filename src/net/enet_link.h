// The real network: ENet over UDP (reliable, ordered, one channel), and
// the discovery of games on the local network by broadcast (section 7.4).
// Polled from the main thread every frame (decision D-903).
#pragma once

#include <cstdint>
#include <deque>
#include <map>
#include <memory>
#include <string>
#include <vector>

#include "net/link.h"

struct _ENetHost;
struct _ENetPeer;

namespace sc::net {

// ENet's global start-up, once per process.
class EnetLibrary {
public:
    EnetLibrary();
    ~EnetLibrary();
    EnetLibrary(const EnetLibrary&) = delete;
    EnetLibrary& operator=(const EnetLibrary&) = delete;
    [[nodiscard]] bool ok() const { return ok_; }

private:
    bool ok_ = false;
};

class EnetLink final : public Link {
public:
    EnetLink() = default;
    ~EnetLink() override;
    EnetLink(const EnetLink&) = delete;
    EnetLink& operator=(const EnetLink&) = delete;

    // A host listening on `port` for up to `max_clients`; `loopback_only`
    // listens on 127.0.0.1 alone (the tests: no firewall prompt).
    bool listen(std::uint16_t port, std::size_t max_clients, bool loopback_only = false);
    // A client connecting to `address` (IPv4 or a name) and `port`. The
    // Connected event arrives when the host answers.
    bool connect(const std::string& address, std::uint16_t port);
    [[nodiscard]] PeerId server() const { return server_; }

    void send(PeerId peer, std::span<const std::uint8_t> data) override;
    void disconnect(PeerId peer) override;
    bool poll(LinkEvent& event) override;
    [[nodiscard]] std::uint32_t round_trip_ms(PeerId peer) const override;
    // Sends what is queued and says goodbye to every peer (on leaving).
    void close();

private:
    void service();
    _ENetHost* host_ = nullptr;
    std::map<PeerId, _ENetPeer*> peers_;
    PeerId next_ = 1;
    PeerId server_ = 0;
    std::deque<LinkEvent> events_;
};

// A game found on the local network.
struct LanGame {
    std::string address;  // IPv4, as text.
    std::uint16_t port = 0;
    std::string host_name;
    std::uint8_t players = 0;
    bool playing = false;
    std::uint64_t seen_ms = 0;
    bool operator==(const LanGame& o) const { return address == o.address && port == o.port; }
};

// The host answers probes with its game; clients probe every second and
// list the answers. Everything read is validated like any network input.
class LanDiscovery {
public:
    LanDiscovery() = default;
    ~LanDiscovery();
    LanDiscovery(const LanDiscovery&) = delete;
    LanDiscovery& operator=(const LanDiscovery&) = delete;

    // Host side: answer on the discovery port.
    bool announce(std::uint16_t game_port);
    void set_game(const std::string& host_name, std::uint8_t players, bool playing);
    // Client side.
    bool search();
    void update(std::uint64_t now_ms);
    [[nodiscard]] const std::vector<LanGame>& games() const { return games_; }

private:
    std::uintptr_t socket_ = ~std::uintptr_t{0};
    bool host_ = false;
    std::uint16_t game_port_ = 0;
    std::string host_name_;
    std::uint8_t players_ = 0;
    bool playing_ = false;
    std::uint64_t last_probe_ms_ = 0;
    std::vector<LanGame> games_;
};

// Encoding of the discovery datagrams (tested separately).
[[nodiscard]] std::vector<std::uint8_t> discovery_probe();
[[nodiscard]] bool is_discovery_probe(std::span<const std::uint8_t> data);
[[nodiscard]] std::vector<std::uint8_t> discovery_answer(std::uint16_t port, const std::string& host_name,
                                                         std::uint8_t players, bool playing);
[[nodiscard]] bool read_discovery_answer(std::span<const std::uint8_t> data, LanGame& out);

}  // namespace sc::net
