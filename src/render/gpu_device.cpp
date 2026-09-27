#include "render/gpu_device.h"

#include <SDL3/SDL_error.h>

#include "core/log.h"

namespace sc {

namespace {

// Shader formats built from HLSL at build time. For now only DXIL, so the
// device is Direct3D 12 (decision D-201).
constexpr SDL_GPUShaderFormat kShaderFormats = SDL_GPU_SHADERFORMAT_DXIL;

#ifdef NDEBUG
constexpr bool kDebugDevice = false;
#else
constexpr bool kDebugDevice = true;
#endif

}  // namespace

GpuDevice::~GpuDevice() {
    destroy();
}

bool GpuDevice::create(SDL_Window* window, bool vsync) {
    device_ = SDL_CreateGPUDevice(kShaderFormats, kDebugDevice, nullptr);
    if (device_ == nullptr && kDebugDevice) {
        // The validation layers are optional system components; run without
        // them rather than not at all.
        log::warn("gpu: debug device unavailable ({}), retrying without validation", SDL_GetError());
        device_ = SDL_CreateGPUDevice(kShaderFormats, false, nullptr);
    }
    if (device_ == nullptr) {
        log::error("gpu: SDL_CreateGPUDevice failed: {}", SDL_GetError());
        return false;
    }
    if (!SDL_ClaimWindowForGPUDevice(device_, window)) {
        log::error("gpu: SDL_ClaimWindowForGPUDevice failed: {}", SDL_GetError());
        SDL_DestroyGPUDevice(device_);
        device_ = nullptr;
        return false;
    }
    window_ = window;
    log::info("gpu: using the {} backend", driver_name());
    return set_vsync(vsync);
}

void GpuDevice::destroy() {
    if (device_ != nullptr) {
        if (window_ != nullptr) {
            SDL_ReleaseWindowFromGPUDevice(device_, window_);
            window_ = nullptr;
        }
        SDL_DestroyGPUDevice(device_);
        device_ = nullptr;
    }
}

bool GpuDevice::set_vsync(bool vsync) {
    SDL_GPUPresentMode mode = SDL_GPU_PRESENTMODE_VSYNC;
    // Without vsync, immediate presentation first: mailbox still waits for
    // the display refresh on Direct3D 12 (decision D-306).
    if (!vsync) {
        if (SDL_WindowSupportsGPUPresentMode(device_, window_, SDL_GPU_PRESENTMODE_IMMEDIATE)) {
            mode = SDL_GPU_PRESENTMODE_IMMEDIATE;
        } else if (SDL_WindowSupportsGPUPresentMode(device_, window_, SDL_GPU_PRESENTMODE_MAILBOX)) {
            mode = SDL_GPU_PRESENTMODE_MAILBOX;
        }
    }
    if (!SDL_SetGPUSwapchainParameters(device_, window_, SDL_GPU_SWAPCHAINCOMPOSITION_SDR, mode)) {
        log::error("gpu: SDL_SetGPUSwapchainParameters failed: {}", SDL_GetError());
        return false;
    }
    log::info("gpu: present mode {}", mode == SDL_GPU_PRESENTMODE_VSYNC       ? "vsync"
                                      : mode == SDL_GPU_PRESENTMODE_MAILBOX ? "mailbox"
                                                                            : "immediate");
    return true;
}

bool GpuDevice::begin_frame(GpuFrame& frame) {
    frame = GpuFrame{};
    frame.cmd = SDL_AcquireGPUCommandBuffer(device_);
    if (frame.cmd == nullptr) {
        log::error("gpu: SDL_AcquireGPUCommandBuffer failed: {}", SDL_GetError());
        return false;
    }
    if (!SDL_WaitAndAcquireGPUSwapchainTexture(frame.cmd, window_, &frame.target, &frame.width, &frame.height)) {
        log::error("gpu: SDL_WaitAndAcquireGPUSwapchainTexture failed: {}", SDL_GetError());
        (void)SDL_CancelGPUCommandBuffer(frame.cmd);
        frame = GpuFrame{};
        return false;
    }
    return true;
}

bool GpuDevice::end_frame(GpuFrame& frame) {
    if (frame.cmd == nullptr) {
        return false;
    }
    const bool ok = SDL_SubmitGPUCommandBuffer(frame.cmd);
    if (!ok) {
        log::error("gpu: SDL_SubmitGPUCommandBuffer failed: {}", SDL_GetError());
    }
    frame = GpuFrame{};
    return ok;
}

SDL_GPUTextureFormat GpuDevice::swapchain_format() const {
    return SDL_GetGPUSwapchainTextureFormat(device_, window_);
}

SDL_GPUShaderFormat GpuDevice::shader_format() const {
    return device_ != nullptr ? SDL_GetGPUShaderFormats(device_) : SDL_GPU_SHADERFORMAT_INVALID;
}

const char* GpuDevice::driver_name() const {
    const char* name = device_ != nullptr ? SDL_GetGPUDeviceDriver(device_) : nullptr;
    return name != nullptr ? name : "none";
}

}  // namespace sc
