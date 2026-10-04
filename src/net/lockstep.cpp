#include "net/lockstep.h"

#include "core/speed.h"

#include <algorithm>

#include "core/log.h"

namespace sc::net {

namespace {

constexpr std::size_t kHistoryTurns = 600;  // A minute at x1.
constexpr std::size_t kChecksKept = 64;
constexpr std::uint64_t kAckEvery = 5;       // Ticks between acknowledgements.

// Real milliseconds a tick takes at a speed (in quarters), at least 1.
std::uint32_t tick_ms(int speed) {
    return std::max<std::uint32_t>(1, 400u / static_cast<std::uint32_t>(std::max(1, speed)));
}

// How far behind a player may be: kMaxLagTicks at x1 and below, and the
// same three seconds of real time above it.
std::uint64_t lag_ticks(int speed) {
    return std::max<std::uint64_t>(NetSession::kMaxLagTicks, NetSession::kMaxLagTicks * 100u / tick_ms(speed));
}
constexpr std::uint64_t kDelayUpdateMs = 1000;

const char* kPartNames[] = {"header", "players", "entities", "nodes", "buildings", "villagers", "vision", "random"};

std::string differing_parts(const PartHashes& a, const PartHashes& b) {
    std::string out;
    for (std::size_t i = 0; i < a.parts.size(); ++i) {
        if (a.parts[i] != b.parts[i]) {
            out += out.empty() ? "" : ", ";
            out += kPartNames[i];
        }
    }
    return out;
}

// The first bytes of a Hello: its protocol number, readable even when the
// rest of a newer client's message is not.
bool hello_protocol(std::span<const std::uint8_t> data, std::uint32_t& protocol) {
    if (data.size() < 5 || data[0] != static_cast<std::uint8_t>(Message(Hello{}).index() + 1)) {
        return false;
    }
    sim::BinaryReader r(data.subspan(1, 4));
    return r.u32(protocol);
}

}  // namespace

std::uint64_t map_hash(const sim::MapData& map) {
    return map.checksum();
}

// --- NetSession --------------------------------------------------------------

std::optional<Start> NetSession::take_start() {
    std::optional<Start> s;
    s.swap(start_);
    return s;
}

std::optional<std::vector<std::uint8_t>> NetSession::take_snapshot() {
    std::optional<std::vector<std::uint8_t>> s;
    s.swap(snapshot_);
    return s;
}

std::vector<NetEvent> NetSession::take_events() {
    std::vector<NetEvent> out;
    out.swap(events_);
    return out;
}

void NetSession::run_turn(const Turn& turn) {
    for (const TurnCommand& c : turn.commands) {
        game_->apply(c.command);
    }
    game_->step();
}

PartHashes NetSession::parts_of(const sim::Game& game) {
    PartHashes h;
    const auto parts = game.hash_parts();
    for (std::size_t i = 0; i < h.parts.size() && i < parts.size(); ++i) {
        h.parts[i] = parts[i].hash;
    }
    return h;
}

// --- NetHost -------------------------------------------------------------------

NetHost::NetHost(Link& link, LocalInfo local) : link_(link), local_(std::move(local)) {
    state_ = State::Lobby;
    slot_ = 0;
    Seat& me = seats_[0];
    me.used = true;
    me.connected = true;
    me.ready = true;
    me.name = local_.name;
    me.color = local_.color;
    send_lobby();
}

void NetHost::take_seats(const sim::Game& game, std::uint8_t host_seat, bool in_game) {
    const Seat me = seats_[slot_];
    seats_.fill(Seat{});
    slot_ = host_seat < game.player_count() ? host_seat : std::uint8_t{0};
    for (std::uint8_t p = 0; p < game.player_count(); ++p) {
        Seat& s = seats_[p];
        s.used = true;
        s.in_game = in_game;
        s.loaded = in_game;
        s.connected = p == slot_;
        s.ready = p == slot_;
        // Nobody can come back to a seat without a name.
        s.name = !game.player(p).name.empty() ? game.player(p).name : p == slot_ ? me.name : std::string();
        s.color = static_cast<std::uint8_t>(game.player(p).color % kColors);
    }
    seats_[slot_].used = true;
    seats_[slot_].connected = true;
    seats_[slot_].ready = true;
    if (seats_[slot_].name.empty()) {
        seats_[slot_].name = me.name;
    }
}

void NetHost::adopt_lobby(sim::Game* game, const GameConfig& config, std::uint8_t host_seat) {
    game_ = game;
    lobby_.config = config;
    lobby_.saved = true;
    saved_ = true;
    take_seats(*game, host_seat, false);
    peers_.clear();
    state_ = State::Lobby;
    sim_seats_ = game->player_count();
    send_lobby();
}

void NetHost::adopt(sim::Game* game, const GameConfig& config, int speed, std::uint8_t host_seat) {
    game_ = game;
    lobby_.config = config;
    take_seats(*game, host_seat, true);
    peers_.clear();
    pending_.clear();
    turns_.clear();
    history_.clear();
    checks_.clear();
    vote_.reset();
    host_loaded_ = true;
    state_ = State::Playing;
    horizon_ = game->turn();
    sim_seats_ = game->player_count();
    speed_ = speed <= 0 ? 0 : speed::snap(std::min(speed, speed::kMaxNetwork), speed::kMaxNetwork);
    send_lobby();
}

void NetHost::set_config(const GameConfig& config) {
    if (state_ != State::Lobby) {
        return;
    }
    lobby_.config = config;
    send_lobby();
}

void NetHost::set_local(const std::string& name, std::uint8_t color) {
    if (!valid_name(name) || color >= kColors || saved_) {
        return;  // In a saved game the seats keep their names.
    }
    seats_[slot_].name = unique_name(name, slot_);
    seats_[slot_].color = color;
    send_lobby();
}

std::string NetHost::unique_name(std::string name, std::uint8_t except) const {
    const std::string base = name;
    for (int n = 2; n < 100; ++n) {
        bool taken = false;
        for (std::size_t i = 0; i < seats_.size(); ++i) {
            taken = taken || (i != except && seats_[i].used && seats_[i].name == name);
        }
        if (!taken) {
            return name;
        }
        // "Name (2)", cut so it stays within the limit.
        const std::string suffix = " (" + std::to_string(n) + ")";
        name = base.substr(0, kMaxNameBytes - suffix.size()) + suffix;
        while (!valid_name(name) && !name.empty()) {
            name.erase(name.size() - suffix.size() - 1, 1);  // Do not cut a UTF-8 sequence in half.
        }
    }
    return name;
}

void NetHost::send_lobby() {
    lobby_.players.clear();
    for (std::size_t i = 0; i < seats_.size(); ++i) {
        const Seat& s = seats_[i];
        if (s.used) {
            lobby_.players.push_back({static_cast<std::uint8_t>(i), s.name, s.color, s.ready, s.connected, s.loaded});
        }
    }
    lobby_.phase = state_ == State::Playing ? LobbyPhase::Playing
                   : state_ == State::Loading ? LobbyPhase::Loading
                                              : LobbyPhase::Lobby;
    broadcast(lobby_, false);
}

void NetHost::broadcast(const Message& m, bool in_game_only) {
    const std::vector<std::uint8_t> bytes = encode(m);
    for (std::size_t i = 0; i < seats_.size(); ++i) {
        const Seat& s = seats_[i];
        if (i != slot_ && s.used && s.connected && (!in_game_only || s.in_game)) {
            link_.send(s.peer, bytes);
        }
    }
}

void NetHost::send(std::uint8_t slot, const Message& m) {
    if (slot != slot_ && slot < seats_.size() && seats_[slot].connected) {
        link_.send(seats_[slot].peer, encode(m));
    }
}

void NetHost::reject(PeerId peer, RejectReason reason) {
    Reject r;
    r.reason = reason;
    r.host_version = local_.game_version;
    r.host_mods = local_.mods;
    link_.send(peer, encode(r));
    link_.disconnect(peer);
}

void NetHost::poll(std::uint64_t now_ms) {
    now_ms_ = now_ms;
    LinkEvent e;
    while (link_.poll(e)) {
        switch (e.type) {
            case LinkEvent::Type::Connected: break;  // Waits for its Hello.
            case LinkEvent::Type::Received: receive(e.peer, e.data); break;
            case LinkEvent::Type::Disconnected: lost(e.peer); break;
        }
    }
    if (vote_ && now_ms_ >= vote_deadline_ms_) {
        settle_vote(true);
    }
    if (state_ == State::Playing && now_ms_ - last_delay_update_ms_ >= kDelayUpdateMs) {
        last_delay_update_ms_ = now_ms_;
        update_delay();
    }
}

void NetHost::update_delay() {
    // Half the slowest round trip, plus a margin, in ticks at this speed.
    std::uint32_t rtt = 0;
    for (std::size_t i = 0; i < seats_.size(); ++i) {
        if (i != slot_ && seats_[i].connected && seats_[i].in_game) {
            rtt = std::max(rtt, link_.round_trip_ms(seats_[i].peer));
        }
    }
    // The longest delay is kMaxDelay ticks of x1 in real time (a second),
    // whatever the speed.
    const std::uint32_t tick = tick_ms(speed_);
    delay_ = std::clamp((rtt / 2 + 50) / tick + 1, kMinDelay, std::max(kMaxDelay, kMaxDelay * 100u / tick));
}

void NetHost::receive(PeerId peer, std::span<const std::uint8_t> data) {
    const auto known = peers_.find(peer);
    std::uint32_t protocol = 0;
    if (known == peers_.end() && hello_protocol(data, protocol) && protocol != kProtocolVersion) {
        reject(peer, RejectReason::Protocol);
        return;
    }
    const std::optional<Message> m = decode(data);
    if (!m) {
        log::warn("net: invalid message from peer {}; disconnected", peer);
        link_.disconnect(peer);
        return;
    }
    if (known == peers_.end()) {
        if (const Hello* h = std::get_if<Hello>(&*m)) {
            hello(peer, *h);
        } else {
            link_.disconnect(peer);  // Anything before Hello is wrong.
        }
        return;
    }
    const std::uint8_t slot = known->second;
    Seat& seat = seats_[slot];
    if (const SetInfo* info = std::get_if<SetInfo>(&*m)) {
        if (state_ == State::Lobby) {
            if (!saved_) {  // In a saved game the seats keep their names.
                seat.name = unique_name(info->name, slot);
                seat.color = info->color;
            }
            seat.ready = info->ready;
            send_lobby();
        }
    } else if (const Loaded* loaded = std::get_if<Loaded>(&*m)) {
        if (state_ == State::Loading && seat.in_game) {
            if (host_loaded_ && loaded->map_hash != host_map_hash_) {
                event({NetEvent::Kind::WrongMap, slot});
                broadcast(Notice{NoticeKind::WrongMap, slot, 0}, false);
                link_.disconnect(peer);
                return;
            }
            seat.loaded = true;
            send_lobby();
            maybe_begin();
        }
    } else if (const Commands* cmds = std::get_if<Commands>(&*m)) {
        if (state_ == State::Playing && seat.in_game) {
            for (sim::Command c : cmds->commands) {
                if (pending_.size() >= kMaxCommandsPerTurn) {
                    break;
                }
                c.player = slot;  // A player only gives orders as themselves.
                pending_.push_back({slot, c});
            }
        }
    } else if (const Ack* ack = std::get_if<Ack>(&*m)) {
        if (state_ == State::Playing && seat.in_game) {
            seat.acked = std::max(seat.acked, ack->tick);
            if (ack->has_hashes) {
                check(slot, *ack);
            }
        }
    } else if (const SpeedPropose* p = std::get_if<SpeedPropose>(&*m)) {
        // Not while the game waits for its founders (phase 74): the turns
        // must keep going for their orders to arrive.
        if (state_ == State::Playing && seat.in_game && !game_->awaiting_founders()) {
            if (p->speed == 0) {
                set_speed(0, slot, SpeedReason::Pause);
            } else {
                start_vote(slot, p->speed);
            }
        }
    } else if (const SpeedAnswer* a = std::get_if<SpeedAnswer>(&*m)) {
        if (vote_ && a->id == vote_->id) {
            answers_[slot] = a->accept;
            settle_vote(false);
        }
    } else {
        log::warn("net: unexpected message from seat {}; ignored", slot);
    }
}

void NetHost::hello(PeerId peer, const Hello& h) {
    if (h.game_version != local_.game_version) {
        reject(peer, RejectReason::Version);
        return;
    }
    if (h.content_hash != local_.content_hash) {
        reject(peer, RejectReason::Mods);
        return;
    }
    // A seat: in the lobby any free one; in a game, the player's own seat
    // back (same name), a free seat of a common town, or a town left alone.
    std::optional<std::uint8_t> seat;
    bool rejoin = false;
    bool new_seat = false;
    if (state_ == State::Lobby && saved_) {
        // Phase 78: the lobby of a saved game keeps each seat for its player.
        for (std::uint8_t i = 0; i < seats_.size() && !seat; ++i) {
            if (i != slot_ && seats_[i].used && !seats_[i].connected && !seats_[i].name.empty() &&
                seats_[i].name == h.name) {
                seat = i;
            }
        }
        if (!seat) {
            reject(peer, RejectReason::NotStarted);
            return;
        }
    } else if (state_ == State::Lobby) {
        for (std::uint8_t i = 1; i < seats_.size() && !seat; ++i) {
            if (!seats_[i].used) {
                seat = i;
            }
        }
    } else if (state_ == State::Playing && game_ != nullptr) {
        for (std::uint8_t i = 0; i < seats_.size() && !seat; ++i) {
            if (i != slot_ && seats_[i].used && seats_[i].in_game && !seats_[i].connected && !seats_[i].name.empty() &&
                seats_[i].name == h.name) {
                seat = i;
                rejoin = true;
            }
        }
        // Phase 76: somebody new gets a seat made for them, without a
        // town, if the game is open.
        if (!seat && !game_->open()) {
            reject(peer, RejectReason::Closed);
            return;
        }
        if (!seat && sim_seats_ < sim::kMaxPlayers && !seats_[sim_seats_].used) {
            seat = sim_seats_;
            new_seat = true;
        }
    }
    if (!seat) {
        reject(peer, RejectReason::Full);
        return;
    }
    Seat& s = seats_[*seat];
    s.used = true;
    s.connected = true;
    s.peer = peer;
    if (!rejoin && !(saved_ && state_ == State::Lobby)) {
        s.name = unique_name(h.name, *seat);
    }
    s.ready = false;
    peers_[peer] = *seat;
    link_.send(peer, encode(Welcome{*seat}));
    if (new_seat) {
        // The seat comes into the simulation by an order of the host, on
        // every machine at the same turn.
        sim::Command add;
        add.type = sim::CommandType::AddSeat;
        add.text = sim::valid_seat_name(s.name) ? s.name : std::string();
        add.count = std::min<std::uint8_t>(s.color, sim::kMaxSeatColor);
        issue(add);
        ++sim_seats_;
    }
    if (state_ == State::Playing) {
        s.in_game = true;
        s.loaded = true;
        event({rejoin ? NetEvent::Kind::PlayerRejoined : NetEvent::Kind::PlayerJoined, *seat});
        broadcast(Notice{rejoin ? NoticeKind::Rejoined : NoticeKind::Joined, *seat, game_->turn()}, false);
        send_lobby();
        send_snapshot(*seat);
    } else {
        event({NetEvent::Kind::PlayerJoined, *seat});
        send_lobby();
    }
}

void NetHost::lost(PeerId peer) {
    const auto it = peers_.find(peer);
    if (it == peers_.end()) {
        return;
    }
    const std::uint8_t slot = it->second;
    peers_.erase(it);
    Seat& s = seats_[slot];
    s.connected = false;
    if (state_ == State::Lobby && !saved_) {
        s = Seat{};  // The seat is free again.
    }
    s.ready = false;
    answers_.erase(slot);
    event({NetEvent::Kind::PlayerLeft, slot});
    broadcast(Notice{NoticeKind::Left, slot, game_ != nullptr ? game_->turn() : 0}, false);
    send_lobby();
    if (vote_) {
        settle_vote(false);
    }
    maybe_begin();  // Somebody the others were waiting for left.
}

bool NetHost::can_start() const {
    if (state_ != State::Lobby) {
        return false;
    }
    for (std::size_t i = 0; i < seats_.size(); ++i) {
        if (i != slot_ && seats_[i].used && seats_[i].connected && !seats_[i].ready) {
            return false;
        }
    }
    return true;
}

bool NetHost::start() {
    if (!can_start()) {
        return false;
    }
    if (saved_) {
        // Phase 78: the game exists already. It starts with whoever is
        // here; each gets it as a snapshot. The seats of the others wait.
        state_ = State::Playing;
        horizon_ = game_->turn();
        sim_seats_ = game_->player_count();
        host_loaded_ = true;
        for (std::uint8_t i = 0; i < seats_.size(); ++i) {
            if (seats_[i].used) {
                seats_[i].in_game = true;
                seats_[i].loaded = true;
            }
        }
        send_lobby();
        for (std::uint8_t i = 0; i < seats_.size(); ++i) {
            if (i != slot_ && seats_[i].used && seats_[i].connected) {
                send_snapshot(i);
            }
        }
        return true;
    }
    // Seats are packed so the towns are 0..n-1.
    std::array<Seat, sim::kMaxPlayers> packed{};
    std::uint8_t n = 0;
    for (const Seat& s : seats_) {
        if (s.used && s.connected) {
            packed[n++] = s;
        }
    }
    seats_ = packed;
    peers_.clear();
    for (std::uint8_t i = 0; i < n; ++i) {
        seats_[i].in_game = true;
        seats_[i].loaded = false;
        seats_[i].acked = 0;
        if (i > 0) {
            peers_[seats_[i].peer] = i;
            send(i, Welcome{i});
        }
    }
    Start st;
    st.config = lobby_.config;
    // Phase 74: the map has the sites the host asked for, and at least one
    // for each town that will be founded.
    st.config.map.players = std::max(lobby_.config.map.players, lobby_.config.shared_town ? std::uint8_t{1} : n);
    st.config.map.separate = st.config.map.separate && !lobby_.config.shared_town;
    st.players = n;
    lobby_.config = st.config;
    state_ = State::Loading;
    send_lobby();
    broadcast(st, true);
    start_ = st;  // This machine builds the game too.
    return true;
}

void NetHost::game_built(sim::Game* game, std::uint64_t map_hash) {
    game_ = game;
    host_map_hash_ = map_hash;
    host_loaded_ = true;
    seats_[slot_].loaded = true;
    send_lobby();
    maybe_begin();
}

void NetHost::maybe_begin() {
    if (state_ != State::Loading || !host_loaded_) {
        return;
    }
    for (const Seat& s : seats_) {
        if (s.in_game && s.connected && !s.loaded) {
            return;
        }
    }
    state_ = State::Playing;
    horizon_ = game_->turn();
    sim_seats_ = game_->player_count();
    send_lobby();
}

void NetHost::issue(const sim::Command& command) {
    if (state_ != State::Playing || pending_.size() >= kMaxCommandsPerTurn) {
        return;
    }
    sim::Command c = command;
    c.player = slot_;
    pending_.push_back({slot_, c});
}

void NetHost::close_turn(std::uint64_t tick) {
    Turn t;
    t.tick = tick;
    t.speed = static_cast<std::uint8_t>(speed_);
    t.commands.swap(pending_);
    broadcast(t, true);
    history_[tick] = t;
    while (history_.size() > kHistoryTurns) {
        history_.erase(history_.begin());
    }
    turns_[tick] = std::move(t);
}

int NetHost::advance(int ticks, std::uint64_t now_ms) {
    now_ms_ = now_ms;
    waiting_for_.reset();
    if (state_ != State::Playing || game_ == nullptr || speed_ == 0) {
        stalled_since_ms_ = 0;
        return 0;
    }
    int ran = 0;
    for (; ran < ticks; ++ran) {
        const std::uint64_t t = game_->turn();
        // Wait for the slowest connected player.
        for (std::uint8_t i = 0; i < seats_.size(); ++i) {
            const Seat& s = seats_[i];
            if (i != slot_ && s.in_game && s.connected && s.acked + lag_ticks(speed_) < t) {
                waiting_for_ = i;
            }
        }
        if (waiting_for_) {
            break;
        }
        while (horizon_ <= t + delay_) {
            close_turn(horizon_++);
        }
        const auto it = turns_.find(t);
        if (it == turns_.end()) {
            break;  // Cannot happen: turns up to the horizon are closed.
        }
        const int turn_speed = it->second.speed;
        run_turn(it->second);
        turns_.erase(it);
        if (game_->turn() % hash_interval(turn_speed) == 0) {
            checks_[game_->turn()] = parts_of(*game_);
            while (checks_.size() > kChecksKept) {
                checks_.erase(checks_.begin());
            }
        }
    }
    // A player that keeps the game waiting slows it down for everybody.
    if (waiting_for_) {
        if (stalled_since_ms_ == 0) {
            stalled_since_ms_ = now_ms_;
        } else if (now_ms_ - stalled_since_ms_ > kSlowPlayerMs && speed_ > speed::kNormal) {
            set_speed(speed::slower(speed_), *waiting_for_, SpeedReason::SlowPlayer);
            stalled_since_ms_ = now_ms_;
        }
    } else {
        stalled_since_ms_ = 0;
    }
    return ran;
}

void NetHost::check(std::uint8_t slot, const Ack& ack) {
    const auto it = checks_.find(ack.tick);
    if (it == checks_.end() || it->second == ack.hashes) {
        return;
    }
    ++desyncs_;
    NetEvent e{NetEvent::Kind::Desync, slot};
    e.value = static_cast<int>(ack.tick);
    e.detail = differing_parts(it->second, ack.hashes);
    log::error("net: desynchronization with seat {} at tick {} in: {}", slot, ack.tick, e.detail);
    event(e);
    broadcast(Notice{NoticeKind::Desync, slot, ack.tick}, false);
    send_snapshot(slot);  // The host's state is the one that counts.
}

void NetHost::send_snapshot(std::uint8_t slot) {
    if (game_ == nullptr) {
        return;
    }
    sim::BinaryWriter w;
    game_->save(w);
    const std::uint64_t tick = game_->turn();
    send(slot, pack_snapshot(tick, w.bytes()));
    // The turns already closed after it, so it can follow.
    for (auto it = history_.lower_bound(tick); it != history_.end(); ++it) {
        send(slot, it->second);
    }
    seats_[slot].acked = tick;
}

void NetHost::request_speed(int speed) {
    if (state_ != State::Playing || !speed::valid(speed) || speed > speed::kMaxNetwork ||
        (game_ != nullptr && game_->awaiting_founders())) {
        return;
    }
    if (speed == 0) {
        set_speed(0, slot_, SpeedReason::Pause);
    } else {
        start_vote(slot_, static_cast<std::uint8_t>(speed));
    }
}

void NetHost::start_vote(std::uint8_t from, std::uint8_t speed) {
    if (vote_ || speed == speed_) {
        return;
    }
    vote_ = SpeedVote{next_vote_++, speed, from};
    answers_.clear();
    answers_[from] = true;
    vote_deadline_ms_ = now_ms_ + kVoteTimeoutMs;
    broadcast(*vote_, true);
    settle_vote(false);
}

void NetHost::answer_vote(bool accept) {
    if (vote_) {
        answers_[slot_] = accept;
        settle_vote(false);
    }
}

void NetHost::settle_vote(bool force_fail) {
    if (!vote_) {
        return;
    }
    bool all = true;
    bool refused = false;
    for (std::uint8_t i = 0; i < seats_.size(); ++i) {
        const Seat& s = seats_[i];
        if (!s.in_game || !s.connected) {
            continue;
        }
        const auto it = answers_.find(i);
        all = all && it != answers_.end() && it->second;
        refused = refused || (it != answers_.end() && !it->second);
    }
    if (all && !force_fail) {
        const SpeedVote v = *vote_;
        vote_.reset();
        set_speed(v.speed, v.from, SpeedReason::Vote);
    } else if (refused || force_fail) {
        const std::uint32_t id = vote_->id;
        vote_.reset();
        broadcast(VoteEnded{id}, true);
        event({NetEvent::Kind::VoteFailed, 0});
    }
}

void NetHost::set_speed(int speed, std::uint8_t by, SpeedReason reason) {
    speed_ = speed;
    broadcast(SpeedSet{static_cast<std::uint8_t>(speed), by, reason}, true);
    NetEvent e{NetEvent::Kind::SpeedChanged, by};
    e.value = speed;
    e.reason = reason;
    event(e);
}

// --- NetClient -----------------------------------------------------------------

NetClient::NetClient(Link& link, PeerId host, LocalInfo local) : link_(link), host_(host), local_(std::move(local)) {}

void NetClient::send(const Message& m) {
    link_.send(host_, encode(m));
}

void NetClient::set_info(const std::string& name, std::uint8_t color, bool ready) {
    if (!valid_name(name) || color >= kColors) {
        return;
    }
    local_.name = name;
    local_.color = color;
    ready_ = ready;
    if (state_ == State::Lobby) {
        send(SetInfo{name, color, ready});
    }
}

void NetClient::poll(std::uint64_t now_ms) {
    (void)now_ms;
    LinkEvent e;
    while (link_.poll(e)) {
        if (e.peer != host_) {
            continue;
        }
        if (e.type == LinkEvent::Type::Connected && !hello_sent_) {
            // Introduce ourselves as soon as the connection is up.
            Hello h;
            h.game_version = local_.game_version;
            h.content_hash = local_.content_hash;
            h.mods = local_.mods;
            h.name = local_.name;
            send(h);
            hello_sent_ = true;
        } else if (e.type == LinkEvent::Type::Received) {
            receive(e.data);
        } else if (e.type == LinkEvent::Type::Disconnected && state_ != State::Closed) {
            state_ = State::Closed;
            event({NetEvent::Kind::ConnectionLost, 0});
        }
    }
    if (!outbox_.empty() && state_ == State::Playing) {
        Commands c;
        const std::size_t n = std::min(outbox_.size(), kMaxCommandsPerMessage);
        c.commands.assign(outbox_.begin(), outbox_.begin() + static_cast<std::ptrdiff_t>(n));
        outbox_.erase(outbox_.begin(), outbox_.begin() + static_cast<std::ptrdiff_t>(n));
        send(c);
    }
}

void NetClient::receive(std::span<const std::uint8_t> data) {
    const std::optional<Message> m = decode(data);
    if (!m) {
        log::warn("net: invalid message from the host; disconnecting");
        link_.disconnect(host_);
        state_ = State::Closed;
        event({NetEvent::Kind::ConnectionLost, 0});
        return;
    }
    if (const Welcome* w = std::get_if<Welcome>(&*m)) {
        slot_ = w->slot;
        if (state_ == State::Connecting) {
            state_ = State::Lobby;
            send(SetInfo{local_.name, local_.color, ready_});
        }
    } else if (const Reject* r = std::get_if<Reject>(&*m)) {
        NetEvent e{NetEvent::Kind::Rejected, 0};
        e.reject = *r;
        event(e);
        state_ = State::Closed;
    } else if (const Lobby* l = std::get_if<Lobby>(&*m)) {
        lobby_ = *l;
    } else if (const Start* s = std::get_if<Start>(&*m)) {
        if (state_ == State::Lobby) {
            start_ = *s;
            lobby_.config = s->config;
            state_ = State::Loading;
        }
    } else if (const Turn* t = std::get_if<Turn>(&*m)) {
        if (turns_.size() < 100'000 && (game_ == nullptr || t->tick >= game_->turn())) {
            turns_[t->tick] = *t;
        }
    } else if (const Snapshot* snap = std::get_if<Snapshot>(&*m)) {
        std::vector<std::uint8_t> state;
        if (unpack_snapshot(*snap, state)) {
            snapshot_ = std::move(state);
            snapshot_tick_ = snap->tick;
            // Turns before it are not needed any more.
            turns_.erase(turns_.begin(), turns_.lower_bound(snap->tick));
        } else {
            log::warn("net: a snapshot from the host could not be unpacked");
        }
    } else if (const SpeedSet* sp = std::get_if<SpeedSet>(&*m)) {
        speed_ = sp->speed;
        vote_.reset();
        NetEvent e{NetEvent::Kind::SpeedChanged, sp->by};
        e.value = sp->speed;
        e.reason = sp->reason;
        event(e);
    } else if (const SpeedVote* v = std::get_if<SpeedVote>(&*m)) {
        vote_ = *v;
        if (v->from == slot_) {
            answer_vote(true);
        }
    } else if (const VoteEnded* ve = std::get_if<VoteEnded>(&*m)) {
        if (vote_ && vote_->id == ve->id) {
            vote_.reset();
        }
        event({NetEvent::Kind::VoteFailed, 0});
    } else if (const Notice* n = std::get_if<Notice>(&*m)) {
        switch (n->kind) {
            case NoticeKind::Joined: event({NetEvent::Kind::PlayerJoined, n->slot}); break;
            case NoticeKind::Left: event({NetEvent::Kind::PlayerLeft, n->slot}); break;
            case NoticeKind::Rejoined: event({NetEvent::Kind::PlayerRejoined, n->slot}); break;
            case NoticeKind::Desync: {
                NetEvent e{NetEvent::Kind::Desync, n->slot};
                e.value = static_cast<int>(n->tick);
                event(e);
                break;
            }
            case NoticeKind::WrongMap: event({NetEvent::Kind::WrongMap, n->slot}); break;
            case NoticeKind::Count: break;
        }
    }
}

void NetClient::game_built(sim::Game* game, std::uint64_t map_hash) {
    game_ = game;
    send(Loaded{map_hash});
    state_ = State::Playing;
}

void NetClient::snapshot_loaded(sim::Game* game) {
    game_ = game;
    const bool resync = state_ == State::Playing;
    state_ = State::Playing;
    if (resync) {
        event({NetEvent::Kind::Resynced, slot_});
    }
}

void NetClient::issue(const sim::Command& command) {
    if (state_ == State::Playing && outbox_.size() < kMaxCommandsPerTurn) {
        sim::Command c = command;
        c.player = slot_;
        outbox_.push_back(c);
    }
}

int NetClient::advance(int ticks, std::uint64_t now_ms) {
    (void)now_ms;
    if (state_ != State::Playing || game_ == nullptr || snapshot_) {
        return 0;  // A snapshot waits to be loaded first.
    }
    // Behind the host: catch up a little faster.
    const std::uint64_t t0 = game_->turn();
    std::uint64_t available = 0;
    while (turns_.contains(t0 + available)) {
        ++available;
    }
    int budget = ticks;
    if (available > delay_ + 3) {
        budget = std::max(budget, static_cast<int>(std::min<std::uint64_t>(available - delay_, 8)));
    }
    int ran = 0;
    for (; ran < budget; ++ran) {
        const auto it = turns_.find(game_->turn());
        if (it == turns_.end()) {
            break;
        }
        speed_ = it->second.speed;  // The host's speed travels with every turn.
        const int turn_speed = speed_;
        run_turn(it->second);
        turns_.erase(it);
        const std::uint64_t t = game_->turn();
        if (t % hash_interval(turn_speed) == 0) {
            send(Ack{t, true, parts_of(*game_)});
        } else if (t % kAckEvery == 0) {
            send(Ack{t, false, {}});
        }
    }
    waiting_for_.reset();
    if (ran < ticks && speed_ > 0) {
        waiting_for_ = game_->host();  // Waiting for the host's turns.
    }
    return ran;
}

void NetClient::request_speed(int speed) {
    if (state_ == State::Playing && speed::valid(speed) && speed <= speed::kMaxNetwork) {
        send(SpeedPropose{static_cast<std::uint8_t>(speed)});
    }
}

void NetClient::answer_vote(bool accept) {
    if (vote_) {
        send(SpeedAnswer{vote_->id, accept});
        if (vote_->from != slot_) {
            vote_.reset();
        }
    }
}

}  // namespace sc::net
