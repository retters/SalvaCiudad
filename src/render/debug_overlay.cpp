#include "render/debug_overlay.h"

#include <imgui.h>
#include <imgui_impl_sdl3.h>
#include <imgui_impl_sdlgpu3.h>

#include "core/log.h"
#include "i18n/translator.h"

namespace sc {

using i18n::tr;

DebugOverlay::~DebugOverlay() {
    destroy();
}

bool DebugOverlay::create(SDL_Window* window, GpuDevice& gpu) {
    IMGUI_CHECKVERSION();
    ImGui::CreateContext();
    ImGuiIO& io = ImGui::GetIO();
    // Never write imgui.ini next to the game or in the working folder.
    io.IniFilename = nullptr;
    io.LogFilename = nullptr;
    ImGui::StyleColorsDark();
    ImGui::GetStyle().Alpha = 0.92f;

    if (!ImGui_ImplSDL3_InitForSDLGPU(window)) {
        log::error("debug overlay: ImGui SDL3 backend failed");
        ImGui::DestroyContext();
        return false;
    }
    ImGui_ImplSDLGPU3_InitInfo init{};
    init.Device = gpu.device();
    init.ColorTargetFormat = gpu.swapchain_format();
    init.MSAASamples = SDL_GPU_SAMPLECOUNT_1;
    if (!ImGui_ImplSDLGPU3_Init(&init)) {
        log::error("debug overlay: ImGui GPU backend failed");
        ImGui_ImplSDL3_Shutdown();
        ImGui::DestroyContext();
        return false;
    }
    ready_ = true;
    return true;
}

void DebugOverlay::destroy() {
    if (!ready_) {
        return;
    }
    ImGui_ImplSDLGPU3_Shutdown();
    ImGui_ImplSDL3_Shutdown();
    ImGui::DestroyContext();
    ready_ = false;
}

void DebugOverlay::process_event(const SDL_Event& event) {
    if (ready_) {
        ImGui_ImplSDL3_ProcessEvent(&event);
    }
}

void DebugOverlay::build(const DebugInfo& info) {
    frame_history_[history_pos_] = info.frame_ms;
    history_pos_ = (history_pos_ + 1) % frame_history_.size();
    built_ = false;
    if (!ready_ || !visible_) {
        return;
    }
    ImGui_ImplSDLGPU3_NewFrame();
    ImGui_ImplSDL3_NewFrame();
    ImGui::NewFrame();

    // Top-right corner, clear of the game's own hints on the left.
    ImGui::SetNextWindowPos(ImVec2(ImGui::GetIO().DisplaySize.x - 10.0f, 10.0f), ImGuiCond_Always, ImVec2(1.0f, 0.0f));
    ImGui::SetNextWindowBgAlpha(0.8f);
    const std::string title = tr("debug.title") + "###debug";
    if (ImGui::Begin(title.c_str(), nullptr, ImGuiWindowFlags_AlwaysAutoResize)) {
        ImGui::Text("%s: %.0f  (%.2f ms)", tr("debug.fps").c_str(), static_cast<double>(info.fps),
                    static_cast<double>(info.frame_ms));
        ImGui::PlotLines("##frames", frame_history_.data(), static_cast<int>(frame_history_.size()),
                         static_cast<int>(history_pos_), nullptr, 0.0f, 33.3f, ImVec2(260, 50));
        ImGui::Text("%s: %s  %ux%u", tr("debug.gpu").c_str(), info.backend, info.width, info.height);
        ImGui::Text("%s: %.2f", tr("debug.uiScale").c_str(), static_cast<double>(info.ui_scale));
        if (info.scene_drawn) {
            const render::RenderStats& s = info.scene;
            ImGui::Separator();
            ImGui::Text("%s: %u", tr("debug.drawCalls").c_str(), s.draw_calls);
            ImGui::Text("%s: %u / %u", tr("debug.instances").c_str(), s.instances_drawn, s.instances_total);
            ImGui::Text("%s: %u", tr("debug.shadowInstances").c_str(), s.shadow_instances);
            ImGui::Text("%s: %u / %u", tr("debug.characters").c_str(), s.characters_drawn, s.characters_total);
            ImGui::Text("%s: %.2f M", tr("debug.triangles").c_str(), static_cast<double>(s.triangles) / 1e6);
            ImGui::Text("%s: %.2f ms", tr("debug.cull").c_str(), static_cast<double>(s.cull_ms));
            ImGui::Text("MSAA: %dx", s.msaa_samples);
            ImGui::Text("%s: %d x %d px", tr("debug.shadows").c_str(), s.shadow_cascades, s.shadow_map_size);
            ImGui::Text("%s: %.0f m", tr("debug.drawDistance").c_str(), static_cast<double>(s.draw_distance));
            ImGui::Text("%s: %.0f m  (%.0f, %.0f)", tr("debug.camera").c_str(), static_cast<double>(info.camera_distance),
                        static_cast<double>(info.camera_x), static_cast<double>(info.camera_z));
            ImGui::Checkbox(tr("debug.stressView").c_str(), &stress_view_);
        }
    }
    ImGui::End();
    ImGui::Render();
    built_ = true;
}

void DebugOverlay::prepare(SDL_GPUCommandBuffer* cmd) {
    if (built_) {
        ImGui_ImplSDLGPU3_PrepareDrawData(ImGui::GetDrawData(), cmd);
    }
}

void DebugOverlay::render(SDL_GPUCommandBuffer* cmd, SDL_GPURenderPass* pass) {
    if (built_) {
        ImGui_ImplSDLGPU3_RenderDrawData(ImGui::GetDrawData(), cmd, pass);
    }
}

}  // namespace sc
