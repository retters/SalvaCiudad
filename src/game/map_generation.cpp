#include "game/map_generation.h"

#include <algorithm>
#include <chrono>

#include "core/log.h"

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

void MapGenerationJob::start(const sim::MapSettings& settings) {
    cancel();
    {
        const std::lock_guard lock(result_mutex_);
        result_.reset();
    }
    cancel_ = false;
    step_ = 0;
    percent_ = 0;
    state_ = static_cast<int>(MapGenStatus::State::Running);
    worker_ = std::thread([this, settings] { run(settings); });
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

void MapGenerationJob::run(sim::MapSettings settings) {
    using State = MapGenStatus::State;
    const auto t0 = std::chrono::steady_clock::now();
    auto result = std::make_unique<GeneratedMap>();
    std::optional<sim::MapData> map = sim::generate_map(settings, [this](sim::GenStage stage, int percent) {
        step_ = static_cast<int>(stage);
        percent_ = percent;
        return !cancel_.load();
    });
    if (!map.has_value() || cancel_) {
        state_ = static_cast<int>(State::Cancelled);
        return;
    }
    step_ = kMapGenSteps - 1;
    percent_ = 0;
    result->map = std::move(*map);
    result->visuals = build_map_visuals(result->map);
    if (cancel_) {
        state_ = static_cast<int>(State::Cancelled);
        return;
    }
    percent_ = 100;
    result->seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
    log::info("map: seed {} size {} generated in {:.2f} s, {} features, checksum {:016x}", settings.seed,
              result->map.size, result->seconds, result->map.features.size(), result->map.checksum());
    {
        const std::lock_guard lock(result_mutex_);
        result_ = std::move(result);
    }
    state_ = static_cast<int>(State::Done);
}

}  // namespace sc
