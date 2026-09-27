// GPU device on top of the SDL3 GPU API (Direct3D 12, Vulkan or Metal).
// Phase 1 only clears the screen; the 3D renderer builds on this in phase 3.
#pragma once

#include <SDL3/SDL_gpu.h>
#include <SDL3/SDL_video.h>

namespace sc {

struct ClearColor {
    float r = 0.0f;
    float g = 0.0f;
    float b = 0.0f;
};

class GpuDevice {
public:
    GpuDevice() = default;
    ~GpuDevice();
    GpuDevice(const GpuDevice&) = delete;
    GpuDevice& operator=(const GpuDevice&) = delete;

    bool create(SDL_Window* window, bool vsync);
    void destroy();

    // With vsync off, uses mailbox or immediate presentation if available.
    bool set_vsync(bool vsync);

    // Records and submits one frame that only clears the swapchain. Does
    // nothing (and succeeds) while the window has no drawable surface, for
    // example when it is minimized.
    bool clear_frame(ClearColor color);

    [[nodiscard]] const char* driver_name() const;

private:
    SDL_GPUDevice* device_ = nullptr;
    SDL_Window* window_ = nullptr;
};

}  // namespace sc
