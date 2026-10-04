// Deterministic lockstep over a star (section 7.4, docs/RED.md). The host
// gathers everybody's commands into numbered turns, one per tick, and sends
// each turn a few ticks ahead ("delay") so every machine runs tick T with
// the same commands. Clients send back acknowledgements with the state's
// hashes every few seconds; a mismatch is a desynchronization, reported and
// repaired by sending the host's state. Also: the lobby, joining a game
// already started, reconnection, speed votes and slow players.
//
// Nothing here knows about ENet, windows or the renderer: it works on a
// Link and a sim::Game, so the tests can run many machines in one process.
#pragma once

#include <array>
#include <cstdint>
#include <map>
#include <memory>
#include <optional>
#include <string>
#include <vector>

#include "net/link.h"
#include "net/protocol.h"
#include "sim/game.h"

namespace sc::net {

// Who this machine is, for the checks when joining.
struct LocalInfo {
    std::string game_version;
    std::uint64_t content_hash = 0;
    std::vector<ModRef> mods;
    std::string name;
    std::uint8_t color = 0;
};

// Something the interface should tell the player.
struct NetEvent {
    enum class Kind : std::uint8_t {
        PlayerJoined,
        PlayerLeft,
        PlayerRejoined,
        Desync,          // Detail: which parts differ.
        WrongMap,
        SpeedChanged,    // `value` is the speed, `reason` why.
        VoteFailed,
        Rejected,        // `reject` says why.
        ConnectionLost,
        Resynced,        // A snapshot from the host was loaded.
    };
    Kind kind = Kind::PlayerJoined;
    std::uint8_t slot = 0;
    int value = 0;
    SpeedReason reason = SpeedReason::Vote;
    Reject reject;
    std::string detail;  // English, for the log.
};

class NetSession {
public:
    enum class Role : std::uint8_t { Host, Client };
    enum class State : std::uint8_t { Connecting, Lobby, Loading, Playing, Closed };

    // Ticks a client may fall behind the host before the host waits (3 s at x1).
    static constexpr std::uint64_t kMaxLagTicks = 30;
    static constexpr std::uint32_t kMinDelay = 2;
    static constexpr std::uint32_t kMaxDelay = 10;
    static constexpr std::uint64_t kVoteTimeoutMs = 15'000;
    static constexpr std::uint64_t kSlowPlayerMs = 3'000;

    virtual ~NetSession() = default;

    [[nodiscard]] virtual Role role() const = 0;
    [[nodiscard]] State state() const { return state_; }
    [[nodiscard]] const Lobby& lobby() const { return lobby_; }
    [[nodiscard]] std::uint8_t local_slot() const { return slot_; }
    [[nodiscard]] int speed() const { return speed_; }

    // Handles what arrived; call every frame.
    virtual void poll(std::uint64_t now_ms) = 0;

    // --- Starting the game (both roles) ------------------------------------
    // The game to build, once, when the host starts it.
    [[nodiscard]] std::optional<Start> take_start();
    // The game was built from the start data: `game` is where the turns go.
    virtual void game_built(sim::Game* game, std::uint64_t map_hash) = 0;
    // A snapshot to load (joining a game already started, or a resync).
    [[nodiscard]] std::optional<std::vector<std::uint8_t>> take_snapshot();
    // The snapshot was loaded into `game`.
    virtual void snapshot_loaded(sim::Game* game) = 0;

    // --- Playing ----------------------------------------------------------------
    virtual void issue(const sim::Command& command) = 0;
    // Runs up to `ticks` ticks (clients may catch up with more). Returns
    // how many ran.
    virtual int advance(int ticks, std::uint64_t now_ms) = 0;
    // Pause is immediate; other speeds are voted (section 7.5).
    virtual void request_speed(int speed) = 0;
    [[nodiscard]] const std::optional<SpeedVote>& vote() const { return vote_; }
    virtual void answer_vote(bool accept) = 0;
    // The seat the game waits for, if it is waiting.
    [[nodiscard]] std::optional<std::uint8_t> waiting_for() const { return waiting_for_; }
    [[nodiscard]] std::uint32_t delay() const { return delay_; }

    [[nodiscard]] std::vector<NetEvent> take_events();

protected:
    State state_ = State::Connecting;
    Lobby lobby_;
    std::uint8_t slot_ = 0;
    int speed_ = 4;  // Quarters of the normal speed; 0 pauses.
    std::uint32_t delay_ = kMinDelay;
    sim::Game* game_ = nullptr;
    std::optional<Start> start_;
    std::optional<std::vector<std::uint8_t>> snapshot_;
    std::optional<SpeedVote> vote_;
    std::optional<std::uint8_t> waiting_for_;
    std::vector<NetEvent> events_;
    std::map<std::uint64_t, Turn> turns_;  // Received or closed, not yet run.

    void event(NetEvent e) { events_.push_back(std::move(e)); }
    // Runs one turn on the game.
    void run_turn(const Turn& turn);
    [[nodiscard]] static PartHashes parts_of(const sim::Game& game);
};

class NetHost final : public NetSession {
public:
    NetHost(Link& link, LocalInfo local);

    [[nodiscard]] Role role() const override { return Role::Host; }
    void poll(std::uint64_t now_ms) override;

    // Lobby.
    void set_config(const GameConfig& config);
    void set_local(const std::string& name, std::uint8_t color);
    // Everybody connected is ready (the host always is).
    [[nodiscard]] bool can_start() const;
    bool start();

    // Phase 76. A game already going on this machine (one player's) becomes
    // a network game hosted here, at `speed` (cut to the network's fastest):
    // no lobby, no loading. Its seats keep the names they have in the game,
    // so whoever comes back with one gets that seat; new players get a new
    // seat while the game is open (sim::Game::open()).
    // `host_seat`: the seat of the game this machine plays (and hosts from).
    void adopt(sim::Game* game, const GameConfig& config, int speed, std::uint8_t host_seat = 0);
    // Phase 78. A saved game is hosted from a lobby: its seats wait, by
    // name, for their players, and start() gives the game to whoever is
    // there (the others may come later, by name). No new players until then.
    void adopt_lobby(sim::Game* game, const GameConfig& config, std::uint8_t host_seat);
    [[nodiscard]] bool saved() const { return saved_; }

    void game_built(sim::Game* game, std::uint64_t map_hash) override;
    void snapshot_loaded(sim::Game* game) override { game_ = game; }
    void issue(const sim::Command& command) override;
    int advance(int ticks, std::uint64_t now_ms) override;
    void request_speed(int speed) override;
    void answer_vote(bool accept) override;

    // Whether every seat's state matches at the last check (for tests).
    [[nodiscard]] std::uint64_t desyncs() const { return desyncs_; }

private:
    struct Seat {
        bool used = false;
        bool connected = false;
        bool in_game = false;
        bool loaded = false;
        bool ready = false;
        PeerId peer = 0;
        std::string name;
        std::uint8_t color = 0;
        std::uint64_t acked = 0;
    };
    Link& link_;
    LocalInfo local_;
    std::array<Seat, sim::kMaxPlayers> seats_{};
    std::map<PeerId, std::uint8_t> peers_;  // Peers that were welcomed.
    std::vector<TurnCommand> pending_;
    std::uint64_t horizon_ = 0;  // Turns before this one are closed.
    // Seats of the simulation, counting those whose AddSeat order is on its way.
    std::uint8_t sim_seats_ = 0;
    bool saved_ = false;  // Phase 78: the lobby of a saved game.
    // Takes this machine's seat to `host_seat` and gives every seat of the
    // game its name, waiting for its player.
    void take_seats(const sim::Game& game, std::uint8_t host_seat, bool in_game);
    std::map<std::uint64_t, Turn> history_;   // Recent turns, for players who join.
    std::map<std::uint64_t, PartHashes> checks_;  // The host's own state checks.
    std::uint64_t host_map_hash_ = 0;
    bool host_loaded_ = false;
    std::uint64_t desyncs_ = 0;
    std::uint32_t next_vote_ = 1;
    std::map<std::uint8_t, bool> answers_;
    std::uint64_t vote_deadline_ms_ = 0;
    std::uint64_t now_ms_ = 0;
    std::uint64_t stalled_since_ms_ = 0;
    std::uint64_t last_delay_update_ms_ = 0;

    void receive(PeerId peer, std::span<const std::uint8_t> data);
    void hello(PeerId peer, const Hello& h);
    void reject(PeerId peer, RejectReason reason);
    void lost(PeerId peer);
    void broadcast(const Message& m, bool in_game_only);
    void send(std::uint8_t slot, const Message& m);
    void send_lobby();
    void close_turn(std::uint64_t tick);
    void send_snapshot(std::uint8_t slot);
    void check(std::uint8_t slot, const Ack& ack);
    void start_vote(std::uint8_t from, std::uint8_t speed);
    void settle_vote(bool force_fail);
    void set_speed(int speed, std::uint8_t by, SpeedReason reason);
    void maybe_begin();
    void update_delay();
    [[nodiscard]] std::string unique_name(std::string name, std::uint8_t except) const;
};

class NetClient final : public NetSession {
public:
    // `host` is the peer the link connected to.
    NetClient(Link& link, PeerId host, LocalInfo local);

    [[nodiscard]] Role role() const override { return Role::Client; }
    void poll(std::uint64_t now_ms) override;
    void set_info(const std::string& name, std::uint8_t color, bool ready);
    [[nodiscard]] bool ready() const { return ready_; }

    void game_built(sim::Game* game, std::uint64_t map_hash) override;
    void snapshot_loaded(sim::Game* game) override;
    void issue(const sim::Command& command) override;
    int advance(int ticks, std::uint64_t now_ms) override;
    void request_speed(int speed) override;
    void answer_vote(bool accept) override;

private:
    Link& link_;
    PeerId host_;
    LocalInfo local_;
    bool ready_ = false;
    bool hello_sent_ = false;
    std::vector<sim::Command> outbox_;
    std::uint64_t snapshot_tick_ = 0;

    void receive(std::span<const std::uint8_t> data);
    void send(const Message& m);
};

// Phase 76. What a game made in the lobby lets newcomers do (sim::access
// bits), the same on every machine: it is open, to join the common town or
// to found a town of their own.
[[nodiscard]] inline std::uint8_t lobby_access(const GameConfig& config) {
    return static_cast<std::uint8_t>(sim::access::kOpen | (config.shared_town ? sim::access::kJoin : sim::access::kFound));
}

// Hash of a map, to check that every machine generated the same one.
[[nodiscard]] std::uint64_t map_hash(const sim::MapData& map);

}  // namespace sc::net
