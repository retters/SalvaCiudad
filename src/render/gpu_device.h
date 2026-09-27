// GPU device on top of the SDL3 GPU API (Direct3D 12, Vulkan or Metal).
#pragma once

#include <cstdint>

#include <SDL3/SDL_gpu.h>
#include <SDL3/SDL_video.h>

namespace sc {

struct ClearColor {
    float r = 0.0f;
    float g = 0.0f;
    float b = 0.0f;
};

// One frame in flight: a command buffer and the swapchain texture to draw
// into. `target` is null while the window has no drawable surface (for
// example when minimized); the frame must still be ended.
struct GpuFrame {
    SDL_GPUCommandBuffer* cmd = nullptr;
    SDL_GPUTexture* target = nullptr;
    std::uint32_t width = 0;
    std::uint32_t height = 0;
};

class GpuDevice {
public:
    GpuDevice() = default;
    ~GpuDevice();
    GpuDevice(const GpuDevice&) = delete;
    GpuDevice& operator=(const GpuDevice&) = delete;

    bool create(SDL_Window* window, bool vsync);
    void destroy();

    // With vsync off, uses immediate (or else mailbox) presentation.
    bool set_vsync(bool vsync);

    bool begin_frame(GpuFrame& frame);
    bool end_frame(GpuFrame& frame);

    [[nodiscard]] SDL_GPUDevice* device() const { return device_; }
    [[nodiscard]] SDL_GPUTextureFormat swapchain_format() const;
    [[nodiscard]] SDL_GPUShaderFormat shader_format() const;
    [[nodiscard]] const char* driver_name() const;

private:
    SDL_GPUDevice* device_ = nullptr;
    SDL_Window* window_ = nullptr;
};

}  // namespace sc
