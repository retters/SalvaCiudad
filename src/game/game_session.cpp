#include "game/game_session.h"

#include <chrono>
#include <ctime>
#include <format>

#include "core/log.h"
#include "net/lockstep.h"
#include "version.h"

namespace sc {

namespace {

std::string now_iso() {
    const std::time_t t = std::time(nullptr);
    std::tm local{};
#if defined(_WIN32)
    if (localtime_s(&local, &t) != 0) {
        return {};
    }
#else
    if (localtime_r(&t, &local) == nullptr) {
        return {};
    }
#endif
    return std::format("{:04}-{:02}-{:02}T{:02}:{:02}:{:02}", local.tm_year + 1900, local.tm_mon + 1, local.tm_mday,
                       local.tm_hour, local.tm_min, local.tm_sec);
}

}  // namespace

GameSession::GameSession(std::shared_ptr<const sim::Content> content, sim::MapData map, const sim::GameSetup& setup,
                         std::uint8_t local_player)
    : game_(std::make_unique<sim::Game>(std::move(content), std::move(map), setup)),
      local_player_(local_player),
      seat_(local_player) {
    fog_.begin(*game_, game_->vision_group(local_player_));
}

GameSession::GameSession(std::unique_ptr<sim::Game> game, std::uint8_t local_player)
    : game_(std::move(game)), local_player_(local_player), seat_(local_player) {
    fog_.begin(*game_, game_->vision_group(local_player_));
}

void GameSession::set_local_player(std::uint8_t player) {
    local_player_ = player;
    seat_ = player;
    fog_.begin(*game_, game_->vision_group(local_player_));
}

void GameSession::watch(std::uint8_t as, bool all, std::uint8_t own_seat) {
    spectating_ = true;
    view_all_ = all;
    seat_ = own_seat;
    local_player_ = as < sim::kMaxPlayers ? as : std::uint8_t{0};
    pending_.clear();
    ui_.placing = sim::kNoDef;
    ui_.field_farm = {};
    ui_.found_mode = false;
    ui_.found_asked = false;
    ui_.found_sent = 0;
    fog_.set_watch_all(all);
    if (const std::uint8_t group = game_->vision_group(local_player_); group != fog_.group()) {
        fog_.begin(*game_, group);
    }
}

void GameSession::play(std::uint8_t seat) {
    spectating_ = false;
    view_all_ = false;
    seat_ = seat;
    local_player_ = seat;
    fog_.set_watch_all(false);
    if (const std::uint8_t group = game_->vision_group(local_player_); group != fog_.group()) {
        fog_.begin(*game_, group);
    }
}

std::uint8_t seat_for(const sim::Game& game, std::string_view name) {
    for (std::uint8_t p = 0; p < game.player_count() && !name.empty(); ++p) {
        if (game.player(p).active && game.player(p).name == name) {
            return p;
        }
    }
    for (std::uint8_t p = 0; p < game.player_count(); ++p) {
        if (game.town_exists(p)) {
            return p;
        }
    }
    return 0;
}

void GameSession::attach(net::NetSession* net) {
    net_ = net;
    // Orders not run yet (a game opened to others, phase 76) go on the network.
    if (net_ != nullptr) {
        for (const sim::Command& c : pending_) {
            net_->issue(c);
        }
        pending_.clear();
    }
}

void GameSession::issue(sim::Command command) {
    if (spectating_) {
        return;  // Whoever watches gives no orders (phase 79).
    }
    command.player = local_player();
    if (net_ != nullptr) {
        net_->issue(command);
        return;
    }
    if (pending_.size() < 256) {
        pending_.push_back(command);
    }
}

void GameSession::step() {
    for (const sim::Command& c : pending_) {
        game_->apply(c);
    }
    pending_.clear();
    game_->step();
}

save::SaveData GameSession::make_save(const std::string& name, const mods::ModLibrary& mods) const {
    save::SaveData data;
    save::Header& h = data.header;
    h.name = name;
    h.game_version = SC_VERSION_STRING;
    h.saved_at = now_iso();
    h.mode = net_ != nullptr ? (game_->shared_town() ? "coopShared" : "coopTowns") : "single";
    h.players = game_->player_count();
    h.rules_version = sim::kGameRulesVersion;
    h.content_hash = game_->content().hash;
    h.seed = game_->map().settings.seed;
    h.tick = game_->tick();
    h.population = static_cast<std::uint32_t>(game_->population(town()));
    for (const mods::ModInfo& m : mods.mods()) {
        if (m.loaded) {
            h.mods.push_back({m.manifest.id, mods::version_text(m.manifest.version), std::format("{:016x}", m.hash)});
        }
    }
    sim::BinaryWriter w;
    game_->save(w);
    data.put("GAME", std::move(w.bytes()));
    return data;
}

GameSession::LoadResult GameSession::load(const save::SaveData& data, std::shared_ptr<const sim::Content> content,
                                          std::unique_ptr<GameSession>& out) {
    if (data.header.rules_version != sim::kGameRulesVersion || data.header.game_version != SC_VERSION_STRING) {
        return LoadResult::OtherVersion;
    }
    if (data.header.content_hash != content->hash) {
        return LoadResult::OtherMods;
    }
    const save::Chunk* chunk = data.find("GAME");
    if (chunk == nullptr) {
        return LoadResult::Damaged;
    }
    std::unique_ptr<GameSession> session(new GameSession());
    session->game_ = std::make_unique<sim::Game>(content, sim::MapData{}, 0, 0);
    sim::BinaryReader r(chunk->data);
    if (!session->game_->load(r, content) || !r.at_end()) {
        log::warn("save: the game data could not be read");
        return LoadResult::Damaged;
    }
    session->fog_.begin(*session->game_, session->game_->vision_group(session->local_player_));
    out = std::move(session);
    return LoadResult::Ok;
}

const char* load_result_key(GameSession::LoadResult r) {
    switch (r) {
        case GameSession::LoadResult::Ok: return "load.ok";
        case GameSession::LoadResult::Unreadable: return "load.error.unreadable";
        case GameSession::LoadResult::OtherVersion: return "load.error.otherVersion";
        case GameSession::LoadResult::OtherMods: return "load.error.otherMods";
        case GameSession::LoadResult::Damaged: return "load.error.damaged";
    }
    return "load.error.damaged";
}

}  // namespace sc
