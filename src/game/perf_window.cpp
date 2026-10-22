#include "game/perf_window.h"

#include <algorithm>

namespace sc {

void PerfWindow::add(const FrameSample& sample) {
    ++frames_;
    seconds_ += sample.frame_ms * 0.001f;
    worst_ = std::max(worst_, sample.frame_ms);
    if (sample.frame_ms > kSlowFrameMs) {
        ++slow_;
    }
    sim_ += sample.sim_ms;
    world_ += sample.world_ms;
    scene_ += sample.scene_ms;
    worst_prepare_ = std::max(worst_prepare_, sample.prepare_ms);
    worst_cull_ = std::max(worst_cull_, sample.cull_ms);
}

PerfSummary PerfWindow::take() {
    PerfSummary s;
    s.frames = frames_;
    s.seconds = seconds_;
    if (frames_ > 0) {
        const double n = frames_;
        s.fps = seconds_ > 0.0f ? static_cast<float>(frames_) / seconds_ : 0.0f;
        s.worst_ms = worst_;
        s.slow_frames = slow_;
        s.sim_ms = static_cast<float>(sim_ / n);
        s.world_ms = static_cast<float>(world_ / n);
        s.scene_ms = static_cast<float>(scene_ / n);
        const float frame_ms = seconds_ * 1000.0f / static_cast<float>(frames_);
        s.other_ms = std::max(0.0f, frame_ms - s.sim_ms - s.world_ms - s.scene_ms);
        s.worst_prepare_ms = worst_prepare_;
        s.worst_cull_ms = worst_cull_;
    }
    clear();
    return s;
}

void PerfWindow::clear() {
    *this = PerfWindow{};
}

}  // namespace sc
