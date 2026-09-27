#include "net/link.h"

namespace sc::net {

MemoryNetwork::Endpoint& MemoryNetwork::add() {
    auto e = std::make_unique<Endpoint>();
    e->net_ = this;
    e->self_ = next_++;
    Endpoint& ref = *e;
    endpoints_[ref.self_] = std::move(e);
    return ref;
}

void MemoryNetwork::connect(PeerId a, PeerId b) {
    endpoints_.at(a)->inbox_.push_back({LinkEvent::Type::Connected, b, {}});
    endpoints_.at(b)->inbox_.push_back({LinkEvent::Type::Connected, a, {}});
}

void MemoryNetwork::cut(PeerId id) {
    cut_[id] = true;
}

void MemoryNetwork::Endpoint::send(PeerId peer, std::span<const std::uint8_t> data) {
    const auto it = net_->endpoints_.find(peer);
    if (it == net_->endpoints_.end() || net_->cut_[peer] || net_->cut_[self_]) {
        return;
    }
    it->second->inbox_.push_back({LinkEvent::Type::Received, self_, {data.begin(), data.end()}});
}

void MemoryNetwork::Endpoint::disconnect(PeerId peer) {
    const auto it = net_->endpoints_.find(peer);
    if (it != net_->endpoints_.end()) {
        it->second->inbox_.push_back({LinkEvent::Type::Disconnected, self_, {}});
    }
    inbox_.push_back({LinkEvent::Type::Disconnected, peer, {}});
}

bool MemoryNetwork::Endpoint::poll(LinkEvent& event) {
    if (inbox_.empty()) {
        return false;
    }
    event = std::move(inbox_.front());
    inbox_.pop_front();
    return true;
}

}  // namespace sc::net
