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

bool GpuDevice::end_frame_captured(GpuFrame& frame, FrameCapture& capture) {
    capture = FrameCapture{};
    if (frame.cmd == nullptr) {
        return false;
    }
    // Byte order of the swapchain's pixels; other formats are not read.
    const SDL_GPUTextureFormat format = swapchain_format();
    const bool bgra = format == SDL_GPU_TEXTUREFORMAT_B8G8R8A8_UNORM || format == SDL_GPU_TEXTUREFORMAT_B8G8R8A8_UNORM_SRGB;
    const bool rgba = format == SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM || format == SDL_GPU_TEXTUREFORMAT_R8G8B8A8_UNORM_SRGB;
    if (frame.target == nullptr || frame.width == 0 || frame.height == 0 || (!bgra && !rgba)) {
        log::warn("gpu: cannot capture this frame (format {})", static_cast<int>(format));
        (void)end_frame(frame);
        return false;
    }
    const std::uint32_t bytes = frame.width * frame.height * 4u;
    SDL_GPUTransferBufferCreateInfo info{};
    info.usage = SDL_GPU_TRANSFERBUFFERUSAGE_DOWNLOAD;
    info.size = bytes;
    SDL_GPUTransferBuffer* buffer = SDL_CreateGPUTransferBuffer(device_, &info);
    if (buffer == nullptr) {
        log::error("gpu: SDL_CreateGPUTransferBuffer failed: {}", SDL_GetError());
        (void)end_frame(frame);
        return false;
    }
    SDL_GPUCopyPass* copy = SDL_BeginGPUCopyPass(frame.cmd);
    SDL_GPUTextureRegion region{};
    region.texture = frame.target;
    region.w = frame.width;
    region.h = frame.height;
    region.d = 1;
    SDL_GPUTextureTransferInfo to{};
    to.transfer_buffer = buffer;
    to.pixels_per_row = frame.width;
    to.rows_per_layer = frame.height;
    SDL_DownloadFromGPUTexture(copy, &region, &to);
    SDL_EndGPUCopyPass(copy);
    SDL_GPUFence* fence = SDL_SubmitGPUCommandBufferAndAcquireFence(frame.cmd);
    const std::uint32_t width = frame.width;
    const std::uint32_t height = frame.height;
    frame = GpuFrame{};
    if (fence == nullptr) {
        log::error("gpu: SDL_SubmitGPUCommandBufferAndAcquireFence failed: {}", SDL_GetError());
        SDL_ReleaseGPUTransferBuffer(device_, buffer);
        return false;
    }
    const bool done = SDL_WaitForGPUFences(device_, true, &fence, 1);
    SDL_ReleaseGPUFence(device_, fence);
    const auto* pixels = done ? static_cast<const std::uint8_t*>(SDL_MapGPUTransferBuffer(device_, buffer, false)) : nullptr;
    if (pixels == nullptr) {
        log::error("gpu: reading the frame back failed: {}", SDL_GetError());
        SDL_ReleaseGPUTransferBuffer(device_, buffer);
        return false;
    }
    capture.width = width;
    capture.height = height;
    capture.rgb.resize(static_cast<std::size_t>(width) * height * 3u);
    for (std::size_t i = 0, n = static_cast<std::size_t>(width) * height; i < n; ++i) {
        capture.rgb[i * 3 + 0] = pixels[i * 4 + (bgra ? 2 : 0)];
        capture.rgb[i * 3 + 1] = pixels[i * 4 + 1];
        capture.rgb[i * 3 + 2] = pixels[i * 4 + (bgra ? 0 : 2)];
    }
    SDL_UnmapGPUTransferBuffer(device_, buffer);
    SDL_ReleaseGPUTransferBuffer(device_, buffer);
    return true;
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
