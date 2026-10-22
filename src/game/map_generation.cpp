#include "game/map_generation.h"

#include <algorithm>
#include <chrono>
#include <format>
#include <iterator>
#include <string>

#include "core/log.h"
#include "script/map_script.h"

namespace sc {

float MapGenStatus::overall() const {
    const float done = static_cast<float>(step) + static_cast<float>(percent) / 100.0f;
    return std::min(1.0f, std::max(0.0f, done / static_cast<float>(kMapGenSteps)));
}

MapGenerationJob::~MapGenerationJob() {
    cancel();
}

void MapGenerationJob::join() {
    if (worker_.joinable()) {
        worker_.join();
    }
}

void MapGenerationJob::start(const sim::MapSettings& settings, std::shared_ptr<const mods::BuildResult> pack) {
    cancel();
    {
        const std::lock_guard lock(result_mutex_);
        result_.reset();
    }
    cancel_ = false;
    step_ = 0;
    percent_ = 0;
    state_ = static_cast<int>(MapGenStatus::State::Running);
    worker_ = std::thread([this, settings, pack = std::move(pack)] { run(settings, pack); });
}

void MapGenerationJob::cancel() {
    cancel_ = true;
    join();
    if (state_ == static_cast<int>(MapGenStatus::State::Running)) {
        state_ = static_cast<int>(MapGenStatus::State::Cancelled);
    }
}

MapGenStatus MapGenerationJob::status() const {
    MapGenStatus s;
    s.state = static_cast<MapGenStatus::State>(state_.load());
    s.step = step_.load();
    s.percent = percent_.load();
    return s;
}

std::unique_ptr<GeneratedMap> MapGenerationJob::take() {
    if (state_ != static_cast<int>(MapGenStatus::State::Done)) {
        return nullptr;
    }
    join();
    state_ = static_cast<int>(MapGenStatus::State::Idle);
    const std::lock_guard lock(result_mutex_);
    return std::move(result_);
}

void MapGenerationJob::run(sim::MapSettings settings, std::shared_ptr<const mods::BuildResult> pack) {
    using State = MapGenStatus::State;
    const auto t0 = std::chrono::steady_clock::now();
    auto result = std::make_unique<GeneratedMap>();
    script::MapScripts scripts(pack->scripts, pack->content);
    // Phase 135: how long each stage took, for the log.
    static constexpr const char* kStageNames[] = {"relief", "lakes", "rivers", "soil", "biomes",
                                                 "forests", "resources", "starts", "view"};
    static_assert(std::size(kStageNames) == static_cast<std::size_t>(sim::GenStage::Count) + 1);
    std::string stages;
    int stage_shown = -1;
    auto stage_start = t0;
    const auto stage_done = [&](int next) {
        const auto now = std::chrono::steady_clock::now();
        if (stage_shown >= 0) {
            stages += std::format(" {} {:.1f} s,", kStageNames[stage_shown],
                                  std::chrono::duration<double>(now - stage_start).count());
        }
        stage_shown = next;
        stage_start = now;
    };
    std::optional<sim::MapData> map = sim::generate_map(settings, pack->content, [&](sim::GenStage stage, int percent) {
        if (static_cast<int>(stage) != stage_shown) {
            stage_done(static_cast<int>(stage));
        }
        step_ = static_cast<int>(stage);
        percent_ = percent;
        return !cancel_.load();
    }, &scripts);
    if (!map.has_value() || cancel_) {
        state_ = static_cast<int>(State::Cancelled);
        return;
    }
    stage_done(static_cast<int>(sim::GenStage::Count));
    step_ = kMapGenSteps - 1;
    percent_ = 0;
    result->map = std::move(*map);
    result->visuals = build_map_visuals(result->map, pack->content);
    stage_done(-1);
    if (!stages.empty()) {
        stages.pop_back();
    }
    result->script_errors = scripts.errors();
    if (cancel_) {
        state_ = static_cast<int>(State::Cancelled);
        return;
    }
    percent_ = 100;
    result->seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
    log::info("map: seed {} size {} generated in {:.2f} s, {} features, checksum {:016x}", settings.seed,
              result->map.size, result->seconds, result->map.features.size(), result->map.checksum());
    log::info("map: stages:{}", stages);
    {
        const std::lock_guard lock(result_mutex_);
        result_ = std::move(result);
    }
    state_ = static_cast<int>(State::Done);
}

}  // namespace sc
