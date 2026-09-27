// What the lockstep needs from the network: numbered peers, reliable
// ordered messages, and connect/disconnect events. ENet provides it in the
// game (enet_link.h); the tests use MemoryNetwork, which passes messages
// between objects in one process.
#pragma once

#include <cstdint>
#include <deque>
#include <map>
#include <memory>
#include <span>
#include <vector>

namespace sc::net {

using PeerId = std::uint32_t;

struct LinkEvent {
    enum class Type : std::uint8_t { Connected, Received, Disconnected };
    Type type = Type::Received;
    PeerId peer = 0;
    std::vector<std::uint8_t> data;
};

class Link {
public:
    virtual ~Link() = default;
    // Reliable and in order.
    virtual void send(PeerId peer, std::span<const std::uint8_t> data) = 0;
    virtual void disconnect(PeerId peer) = 0;
    // The next event, if any.
    virtual bool poll(LinkEvent& event) = 0;
    // Round-trip time to a peer, in milliseconds (0 when unknown).
    [[nodiscard]] virtual std::uint32_t round_trip_ms(PeerId peer) const = 0;
};

// Many links in one process, connected in memory. Messages arrive in order
// on the next poll, optionally after a delay counted in polls.
class MemoryNetwork {
public:
    class Endpoint final : public Link {
    public:
        void send(PeerId peer, std::span<const std::uint8_t> data) override;
        void disconnect(PeerId peer) override;
        bool poll(LinkEvent& event) override;
        [[nodiscard]] std::uint32_t round_trip_ms(PeerId) const override { return net_->rtt_ms; }
        [[nodiscard]] PeerId self_id() const { return self_; }

    private:
        friend class MemoryNetwork;
        MemoryNetwork* net_ = nullptr;
        PeerId self_ = 0;
        std::deque<LinkEvent> inbox_;
    };

    std::uint32_t rtt_ms = 20;

    // A new endpoint; its id is how others address it.
    Endpoint& add();
    // Connects two endpoints (both get a Connected event).
    void connect(PeerId a, PeerId b);
    [[nodiscard]] Endpoint& endpoint(PeerId id) { return *endpoints_.at(id); }
    // Messages sent to this peer are dropped (a machine that went away).
    void cut(PeerId id);

private:
    std::map<PeerId, std::unique_ptr<Endpoint>> endpoints_;
    std::map<PeerId, bool> cut_;
    PeerId next_ = 1;
};

}  // namespace sc::net
