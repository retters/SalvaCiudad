// What a frame cost, by parts, gathered over a few seconds for the "perf:"
// line of the log (phase 129).
#pragma once

#include <cstdint>

namespace sc {

// A frame slower than this counts as a slow frame.
inline constexpr float kSlowFrameMs = 50.0f;

// One frame, in milliseconds of the CPU.
struct FrameSample {
    float frame_ms = 0.0f;    // From the start of this frame to the start of the next.
    float sim_ms = 0.0f;      // The simulation's steps.
    float world_ms = 0.0f;    // Bringing the world's views up to date (village, map, ground cover).
    float scene_ms = 0.0f;    // The 3D renderer recording the frame.
    float prepare_ms = 0.0f;  // Of scene_ms: laying out and sorting the instances.
    float cull_ms = 0.0f;     // Of scene_ms: choosing what is seen.
};

struct PerfSummary {
    int frames = 0;
    float seconds = 0.0f;
    float fps = 0.0f;
    float worst_ms = 0.0f;
    int slow_frames = 0;
    // Averages per frame.
    float sim_ms = 0.0f;
    float world_ms = 0.0f;
    float scene_ms = 0.0f;
    float other_ms = 0.0f;  // The rest: interface, waiting for the screen.
    // Worst frame of each.
    float worst_prepare_ms = 0.0f;
    float worst_cull_ms = 0.0f;
};

class PerfWindow {
public:
    void add(const FrameSample& sample);
    [[nodiscard]] float seconds() const { return seconds_; }
    [[nodiscard]] int frames() const { return frames_; }
    // What was gathered; starts over.
    [[nodiscard]] PerfSummary take();
    void clear();

private:
    int frames_ = 0;
    float seconds_ = 0.0f;
    float worst_ = 0.0f;
    int slow_ = 0;
    double sim_ = 0.0;
    double world_ = 0.0;
    double scene_ = 0.0;
    float worst_prepare_ = 0.0f;
    float worst_cull_ = 0.0f;
};

}  // namespace sc
