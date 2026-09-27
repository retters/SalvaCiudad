#include "render/gpu_device.h"

#include <SDL3/SDL_error.h>

#include "core/log.h"

namespace sc {

namespace {

// Every backend's shader format, compiled from HLSL at build time (D-006).
constexpr SDL_GPUShaderFormat kShaderFormats =
    SDL_GPU_SHADERFORMAT_SPIRV | SDL_GPU_SHADERFORMAT_DXIL | SDL_GPU_SHADERFORMAT_MSL;

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
    if (!vsync) {
        if (SDL_WindowSupportsGPUPresentMode(device_, window_, SDL_GPU_PRESENTMODE_MAILBOX)) {
            mode = SDL_GPU_PRESENTMODE_MAILBOX;
        } else if (SDL_WindowSupportsGPUPresentMode(device_, window_, SDL_GPU_PRESENTMODE_IMMEDIATE)) {
            mode = SDL_GPU_PRESENTMODE_IMMEDIATE;
        }
    }
    if (!SDL_SetGPUSwapchainParameters(device_, window_, SDL_GPU_SWAPCHAINCOMPOSITION_SDR, mode)) {
        log::error("gpu: SDL_SetGPUSwapchainParameters failed: {}", SDL_GetError());
        return false;
    }
    return true;
}

bool GpuDevice::clear_frame(ClearColor color) {
    SDL_GPUCommandBuffer* cmd = SDL_AcquireGPUCommandBuffer(device_);
    if (cmd == nullptr) {
        log::error("gpu: SDL_AcquireGPUCommandBuffer failed: {}", SDL_GetError());
        return false;
    }
    SDL_GPUTexture* swapchain = nullptr;
    if (!SDL_WaitAndAcquireGPUSwapchainTexture(cmd, window_, &swapchain, nullptr, nullptr)) {
        log::error("gpu: SDL_WaitAndAcquireGPUSwapchainTexture failed: {}", SDL_GetError());
        (void)SDL_CancelGPUCommandBuffer(cmd);
        return false;
    }
    if (swapchain != nullptr) {
        SDL_GPUColorTargetInfo target{};
        target.texture = swapchain;
        target.clear_color = SDL_FColor{color.r, color.g, color.b, 1.0f};
        target.load_op = SDL_GPU_LOADOP_CLEAR;
        target.store_op = SDL_GPU_STOREOP_STORE;
        SDL_GPURenderPass* pass = SDL_BeginGPURenderPass(cmd, &target, 1, nullptr);
        if (pass != nullptr) {
            SDL_EndGPURenderPass(pass);
        }
    }
    if (!SDL_SubmitGPUCommandBuffer(cmd)) {
        log::error("gpu: SDL_SubmitGPUCommandBuffer failed: {}", SDL_GetError());
        return false;
    }
    return true;
}

const char* GpuDevice::driver_name() const {
    const char* name = device_ != nullptr ? SDL_GetGPUDeviceDriver(device_) : nullptr;
    return name != nullptr ? name : "none";
}

}  // namespace sc
