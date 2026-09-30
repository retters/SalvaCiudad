// Developer statistics drawn with Dear ImGui (only for debugging, never the
// player's interface). Toggled with the "debug overlay" key.
#pragma once

#include <array>
#include <functional>
#include <cstdint>
#include <string>
#include <vector>

#include <SDL3/SDL_events.h>
#include <SDL3/SDL_gpu.h>
#include <SDL3/SDL_video.h>

#include "render/gpu_device.h"
#include "render/scene_renderer.h"

namespace sc {

struct DebugInfo {
    float frame_ms = 0.0f;
    float fps = 0.0f;
    const char* backend = "";
    std::uint32_t width = 0;
    std::uint32_t height = 0;
    float ui_scale = 1.0f;
    bool scene_drawn = false;
    render::RenderStats scene;
    float camera_distance = 0.0f;
    float camera_x = 0.0f;
    float camera_z = 0.0f;
    std::uint64_t sim_tick = 0;
    std::uint64_t sim_hash = 0;
    std::uint32_t sim_entities = 0;
    // What is under the cursor on a map (phase 37), already in text; empty
    // when there is no map.
    std::vector<std::string> cursor;
};

class DebugOverlay {
public:
    DebugOverlay() = default;
    ~DebugOverlay();
    DebugOverlay(const DebugOverlay&) = delete;
    DebugOverlay& operator=(const DebugOverlay&) = delete;

    bool create(SDL_Window* window, GpuDevice& gpu);
    void destroy();

    void process_event(const SDL_Event& event);
    void toggle() { visible_ = !visible_; }
    [[nodiscard]] bool visible() const { return visible_; }
    // Debug option: pull the camera far back so the whole test scene is on
    // screen at once, to measure the worst case.
    [[nodiscard]] bool stress_view() const { return visible_ && stress_view_; }
    // True while the pointer is over an ImGui window (statistics or tools).
    [[nodiscard]] bool wants_mouse() const;
    // True while an ImGui text field has the keyboard.
    [[nodiscard]] bool wants_keyboard() const;

    // Builds the windows for this frame: the statistics if visible, and
    // `extra` (more ImGui windows) if `extra_active`. Call before prepare().
    void build(const DebugInfo& info, const std::function<void()>& extra = {}, bool extra_active = false);
    // Nothing of it this frame (a map report's capture, phase 38): call
    // instead of build().
    void skip_frame() {
        built_ = false;
        active_ = false;
    }
    // Uploads the draw data; must run before the render pass.
    void prepare(SDL_GPUCommandBuffer* cmd);
    void render(SDL_GPUCommandBuffer* cmd, SDL_GPURenderPass* pass);

private:
    bool ready_ = false;
    bool visible_ = false;
    bool built_ = false;
    bool active_ = false;  // A frame was built last time (for input).
    bool stress_view_ = false;
    std::array<float, 120> frame_history_{};
    std::size_t history_pos_ = 0;
};

}  // namespace sc
