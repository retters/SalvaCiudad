// Generates a map on a worker thread so the window stays responsive, with
// progress and cancellation for the "generating" screen.
#pragma once

#include <atomic>
#include <cstdint>
#include <memory>
#include <mutex>
#include <thread>

#include "game/map_scene.h"
#include "sim/map.h"
#include "sim/worldgen.h"

namespace sc {

struct GeneratedMap {
    sim::MapData map;
    MapVisuals visuals;
    double seconds = 0.0;
};

// Steps shown to the player: the generator's stages, then preparing the
// view.
inline constexpr int kMapGenSteps = static_cast<int>(sim::GenStage::Count) + 1;

struct MapGenStatus {
    enum class State : std::uint8_t { Idle, Running, Done, Cancelled };
    State state = State::Idle;
    int step = 0;     // 0 .. kMapGenSteps - 1
    int percent = 0;  // Of the current step.

    // Overall progress, 0..1.
    [[nodiscard]] float overall() const;
};

class MapGenerationJob {
public:
    MapGenerationJob() = default;
    ~MapGenerationJob();
    MapGenerationJob(const MapGenerationJob&) = delete;
    MapGenerationJob& operator=(const MapGenerationJob&) = delete;

    // Starts a new generation, cancelling any running one.
    void start(const sim::MapSettings& settings);
    // Asks the worker to stop and waits for it.
    void cancel();

    [[nodiscard]] MapGenStatus status() const;
    // The result once the state is Done; empty otherwise. Resets to Idle.
    [[nodiscard]] std::unique_ptr<GeneratedMap> take();

private:
    void run(sim::MapSettings settings);
    void join();

    std::thread worker_;
    std::atomic<bool> cancel_{false};
    std::atomic<int> state_{static_cast<int>(MapGenStatus::State::Idle)};
    std::atomic<int> step_{0};
    std::atomic<int> percent_{0};
    mutable std::mutex result_mutex_;
    std::unique_ptr<GeneratedMap> result_;
};

}  // namespace sc
