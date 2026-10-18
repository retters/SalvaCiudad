#include "game/model_studio.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstring>

#include <SDL3/SDL_error.h>

#include "core/log.h"
#include "core/text.h"
#include "game/model_file.h"
#include "game/settings.h"

namespace sc {

namespace {

bool plain(std::string_view s) {
    return !s.empty() && s.size() <= 64 && std::all_of(s.begin(), s.end(), [](char c) {
        return (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '_' || c == '-';
    });
}

std::vector<std::string_view> parts(std::string_view key) {
    std::vector<std::string_view> out;
    std::size_t start = 0;
    while (start <= key.size()) {
        const std::size_t slash = key.find('/', start);
        out.push_back(key.substr(start, slash == std::string_view::npos ? std::string_view::npos : slash - start));
        if (slash == std::string_view::npos) {
            break;
        }
        start = slash + 1;
    }
    return out;
}

constexpr std::string_view kDefTypes[] = {"building", "mapFeature", "species", "resource", "crop"};

// Where the camera looks from: front, right and above, as in the mockups.
const math::Vec3 kModelView = math::normalize({0.85f, 0.7f, 1.15f});
const math::Vec3 kPortraitView = math::normalize({0.3f, 0.1f, 1.0f});
constexpr float kModelFov = 0.5f;
constexpr float kPortraitFov = 0.45f;

}  // namespace

std::optional<ThumbKey> parse_thumb_key(std::string_view key) {
    if (key.starts_with(kThumbPrefix)) {
        key.remove_prefix(kThumbPrefix.size());
    }
    if (key.size() > 200) {
        return std::nullopt;
    }
    const std::vector<std::string_view> p = parts(key);
    ThumbKey out;
    if (p.size() == 5 && p[0] == "person") {
        if (!plain(p[1]) || !plain(p[2]) || (p[3] != "f" && p[3] != "m") || p[4].empty() || p[4].size() > 10 ||
            !std::all_of(p[4].begin(), p[4].end(), [](char c) { return c >= '0' && c <= '9'; })) {
            return std::nullopt;
        }
        const std::uint64_t look = std::stoull(std::string(p[4]));
        if (look > 0xffffffffull) {
            return std::nullopt;
        }
        out.kind = ThumbKey::Kind::Person;
        out.def_id = std::string(p[1]) + ":" + std::string(p[2]);
        out.female = p[3] == "f";
        out.appearance = static_cast<std::uint32_t>(look);
        return out;
    }
    if (p.size() == 3 && std::find(std::begin(kDefTypes), std::end(kDefTypes), p[0]) != std::end(kDefTypes) &&
        plain(p[1]) && plain(p[2])) {
        out.kind = ThumbKey::Kind::Model;
        out.def_type = std::string(p[0]);
        out.def_id = std::string(p[1]) + ":" + std::string(p[2]);
        return out;
    }
    return std::nullopt;
}

std::string thumb_key(std::string_view def_type, std::string_view def_id) {
    std::string id(def_id);
    std::replace(id.begin(), id.end(), ':', '/');
    return std::string(def_type) + "/" + id;
}

std::string portrait_key(const sim::Content& content, const sim::Villager& v) {
    if (v.race >= content.races.size()) {
        return {};
    }
    std::string race = content.races[v.race].id;
    std::replace(race.begin(), race.end(), ':', '/');
    return "person/" + race + (v.sex == sim::Sex::Female ? "/f/" : "/m/") + std::to_string(v.appearance);
}

std::optional<std::filesystem::path> thumb_model_file(const mods::BuildResult& pack, std::string_view def_type,
                                                      std::string_view def_id) {
    for (const mods::ModelRef& ref : pack.model_refs) {
        if (ref.def_type == def_type && ref.def_id == def_id && ref.exists) {
            const std::filesystem::path dir = pack.dir(ref.mod);
            const std::filesystem::path file = dir.empty() ? std::filesystem::path() : mods::mod_file(dir, ref.path);
            if (!file.empty()) {
                return file;
            }
        }
    }
    return std::nullopt;
}

ModelStudio::ModelStudio() = default;

ModelStudio::~ModelStudio() {
    destroy();
}

bool ModelStudio::create(GpuDevice& gpu) {
    const auto start = std::chrono::steady_clock::now();
    gpu_ = &gpu;
    GraphicsSettings g;
    g.shadows = 1;
    g.antialiasing = 2;  // 4x: small pictures want smooth edges.
    g.ground_detail = 0;
    renderer_ = std::make_unique<render::SceneRenderer>();
    if (!renderer_->create(gpu, g)) {
        log::warn("studio: cannot create its renderer; no thumbnails");
        renderer_.reset();
        return false;
    }
    log::info("studio: ready in {:.0f} ms",
              std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - start).count());
    return true;
}

void ModelStudio::destroy() {
    if (gpu_ != nullptr) {
        SDL_GPUDevice* device = gpu_->device();
        for (Batch& b : in_flight_) {
            if (b.fence != nullptr) {
                SDL_WaitForGPUFences(device, true, &b.fence, 1);
                SDL_ReleaseGPUFence(device, b.fence);
            }
            SDL_ReleaseGPUTransferBuffer(device, b.download);
        }
        for (SDL_GPUTexture* t : targets_) {
            SDL_ReleaseGPUTexture(device, t);
        }
    }
    in_flight_.clear();
    targets_.clear();
    cast_.reset();
    renderer_.reset();
    files_.clear();
    failed_files_.clear();
}

void ModelStudio::set_content(std::shared_ptr<const mods::BuildResult> pack) {
    const bool again = pack_ != nullptr;
    pack_ = std::move(pack);
    // Other mods: start over (the GPU work in flight is finished first, so
    // nothing points to what goes away).
    if (again && renderer_ != nullptr && gpu_ != nullptr) {
        GpuDevice& gpu = *gpu_;
        destroy();
        (void)create(gpu);
    }
    queue_.clear();
    warm_.clear();
    asked_.clear();
    done_.clear();
    fresh_.clear();
    wanted_.clear();
    if (renderer_ == nullptr || pack_ == nullptr) {
        return;
    }
    load_cast();
    // Every definition with a model, in the background.
    for (const mods::ModelRef& ref : pack_->model_refs) {
        if (ref.exists && ref.def_type != "race") {
            std::string key = thumb_key(ref.def_type, ref.def_id);
            if (!asked_.contains(key) && parse_thumb_key(key)) {
                asked_[key] = true;
                warm_.push_back(std::move(key));
            }
        }
    }
}

void ModelStudio::load_cast() {
    const auto start = std::chrono::steady_clock::now();
    cast_ = std::make_unique<people::Cast>();
    if (!cast_->load(*renderer_, pack_->dir(mods::kCoreModId), pack_->content)) {
        log::warn("studio: no bodies; no portraits");
        cast_.reset();
    }
    cast_ms_ = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - start).count();
    log::info("studio: bodies loaded in {:.0f} ms", cast_ms_);
}

void ModelStudio::request(std::string_view key) {
    if (key.starts_with(kThumbPrefix)) {
        key.remove_prefix(kThumbPrefix.size());
    }
    const std::string k(key);
    if (done_.contains(k)) {
        wanted_.push_back(k);
        return;
    }
    if (const auto w = std::find(warm_.begin(), warm_.end(), k); w != warm_.end()) {
        warm_.erase(w);  // Waiting in the background: now it goes first.
        queue_.push_back(k);
        return;
    }
    if (asked_.contains(k) || !parse_thumb_key(k)) {
        return;
    }
    asked_[k] = true;
    queue_.push_back(k);
}

std::optional<render::ModelId> ModelStudio::model(const std::filesystem::path& file, bool& skinned,
                                                  render::SkinnedId& body, float& radius, float& base) {
    const std::string name = text::path_to_utf8(file);
    if (const auto it = files_.find(name); it != files_.end()) {
        skinned = it->second.skinned;
        body = it->second.body;
        radius = it->second.radius;
        base = it->second.base;
        return it->second.model;
    }
    if (failed_files_.contains(name)) {
        return std::nullopt;
    }
    const std::optional<render::ModelData> data = load_model_file(file);
    Loaded l;
    bool ok = data.has_value();
    if (ok) {
        l.skinned = data->skinned() && !data->clips.empty();
        const math::Vec3 size = data->bounds_max - data->bounds_min;
        l.radius = std::max(0.05f, 0.5f * math::length(size));
        l.base = data->bounds_min.y;
        l.height = size.y;
        ok = l.skinned ? renderer_->add_skinned_model(*data, l.body) : renderer_->add_model(*data, l.model);
    }
    if (!ok) {
        log::warn("studio: cannot load '{}'", name);
        failed_files_[name] = std::nullopt;
        return std::nullopt;
    }
    files_[name] = l;
    skinned = l.skinned;
    body = l.body;
    radius = l.radius;
    base = l.base;
    return l.model;
}

bool ModelStudio::stage(const Job& job, render::SceneView& view, float& radius) {
    renderer_->clear_instances();
    renderer_->set_characters({});
    math::Vec3 center{};
    math::Vec3 from = kModelView;
    float fov = kModelFov;
    if (job.parsed.kind == ThumbKey::Kind::Person) {
        if (cast_ == nullptr || !cast_->loaded()) {
            return false;
        }
        std::size_t race = pack_->content.races.size();
        for (std::size_t i = 0; i < pack_->content.races.size(); ++i) {
            if (pack_->content.races[i].id == job.parsed.def_id) {
                race = i;
            }
        }
        if (race >= pack_->content.races.size()) {
            return false;
        }
        const people::Body& body = cast_->body(race, job.parsed.female, job.parsed.appearance);
        render::CharacterInstance c;
        c.body = body.id;
        const int idle = renderer_->clip_index(body.id, "idle");
        c.clip = idle >= 0 ? static_cast<std::uint32_t>(idle) : 0u;
        c.palette = people::Cast::palette(body, job.parsed.appearance);
        renderer_->set_characters(std::span<const render::CharacterInstance>(&c, 1));
        // The head and shoulders.
        center = {0.0f, body.height * 0.8f, 0.0f};
        radius = body.height * 0.2f;
        from = kPortraitView;
        fov = kPortraitFov;
    } else {
        const auto file = thumb_model_file(*pack_, job.parsed.def_type, job.parsed.def_id);
        if (!file) {
            return false;
        }
        bool skinned = false;
        render::SkinnedId body = 0;
        float base = 0.0f;
        const auto id = model(*file, skinned, body, radius, base);
        if (!id) {
            return false;
        }
        const Loaded& l = files_.at(text::path_to_utf8(*file));
        center = {0.0f, base + l.height * 0.5f, 0.0f};
        if (skinned) {
            render::CharacterInstance c;
            c.body = body;
            const int idle = renderer_->clip_index(body, "idle");
            c.clip = idle >= 0 ? static_cast<std::uint32_t>(idle) : 0u;
            renderer_->set_characters(std::span<const render::CharacterInstance>(&c, 1));
        } else {
            render::Instance inst;
            renderer_->set_instances(*id, std::span<const render::Instance>(&inst, 1));
        }
    }
    const float distance = radius / std::sin(fov * 0.5f) * 1.04f;
    view.eye = center + from * distance;
    view.view = math::look_at(view.eye, center, {0.0f, 1.0f, 0.0f});
    view.fov_y = fov;
    view.aspect = 1.0f;
    view.near_z = std::max(0.02f, distance - radius * 2.0f);
    // The fog grows with the square of the draw distance over it: far
    // enough that it does not touch the model.
    view.draw_distance_override = 2000.0f;
    return true;
}

bool ModelStudio::ensure_targets(std::size_t count) {
    SDL_GPUDevice* device = gpu_->device();
    while (targets_.size() < count) {
        SDL_GPUTextureCreateInfo ti{};
        ti.type = SDL_GPU_TEXTURETYPE_2D;
        ti.format = gpu_->swapchain_format();
        ti.usage = SDL_GPU_TEXTUREUSAGE_COLOR_TARGET | SDL_GPU_TEXTUREUSAGE_SAMPLER;
        ti.width = kThumbSize;
        ti.height = kThumbSize;
        ti.layer_count_or_depth = 1;
        ti.num_levels = 1;
        SDL_GPUTexture* t = SDL_CreateGPUTexture(device, &ti);
        if (t == nullptr) {
            log::warn("studio: cannot create a target: {}", SDL_GetError());
            return false;
        }
        targets_.push_back(t);
    }
    return true;
}

void ModelStudio::update() {
    if (renderer_ == nullptr || pack_ == nullptr) {
        return;
    }
    SDL_GPUDevice* device = gpu_->device();
    // What the GPU finished.
    for (Batch& b : in_flight_) {
        if (b.fence != nullptr && SDL_QueryGPUFence(device, b.fence)) {
            finish(b);
        }
    }
    std::erase_if(in_flight_, [](const Batch& b) { return b.fence == nullptr; });
    if (in_flight_.empty() && queue_.empty() && warm_.empty() && busy_ms_ > 0.0) {
        log::info("studio: {} pictures made, {:.1f} ms of CPU in this run of batches", done_.size(), busy_ms_);
        busy_ms_ = 0.0;
    }
    // One batch at a time: the targets are shared.
    if (!in_flight_.empty() || (queue_.empty() && warm_.empty())) {
        return;
    }
    const auto start = std::chrono::steady_clock::now();
    if (!ensure_targets(static_cast<std::size_t>(kPerFrame) * 2)) {
        return;
    }
    SDL_GPUCommandBuffer* cmd = SDL_AcquireGPUCommandBuffer(device);
    if (cmd == nullptr) {
        return;
    }
    render::Lighting light;
    light.disc = 0.0f;
    light.stars = 0.0f;
    Batch batch;
    std::vector<bool> drawn;
    // Loading a model file is most of the work: stop once the frame's share
    // of time is gone.
    while ((!queue_.empty() || !warm_.empty()) && batch.jobs.size() < static_cast<std::size_t>(kPerFrame) &&
           (batch.jobs.empty() ||
            std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - start).count() <
                kFrameBudgetMs)) {
        std::vector<std::string>& from = queue_.empty() ? warm_ : queue_;
        Job job;
        job.key = from.front();
        from.erase(from.begin());
        job.parsed = *parse_thumb_key(job.key);
        batch.jobs.push_back(std::move(job));
        drawn.push_back(false);
        const std::size_t i = batch.jobs.size() - 1;
        render::SceneView view;
        float radius = 1.0f;
        if (!stage(batch.jobs[i], view, radius)) {
            log::warn("studio: nothing to draw for '{}'", batch.jobs[i].key);
            continue;
        }
        for (int sky = 0; sky < 2; ++sky) {
            const math::Vec3 c = sky == 0 ? math::Vec3{0.0f, 0.0f, 0.0f} : math::Vec3{1.0f, 1.0f, 1.0f};
            light.zenith_color = c;
            light.horizon_color = c;
            GpuFrame frame{cmd, targets_[i * 2 + static_cast<std::size_t>(sky)], kThumbSize, kThumbSize};
            drawn[i] = renderer_->render(frame, view, light) && (sky == 0 || drawn[i]);
        }
    }
    const std::uint32_t one = kThumbSize * kThumbSize * 4u;
    SDL_GPUTransferBufferCreateInfo tb{};
    tb.usage = SDL_GPU_TRANSFERBUFFERUSAGE_DOWNLOAD;
    tb.size = one * static_cast<std::uint32_t>(batch.jobs.size()) * 2u;
    batch.download = SDL_CreateGPUTransferBuffer(device, &tb);
    if (batch.download != nullptr) {
        SDL_GPUCopyPass* copy = SDL_BeginGPUCopyPass(cmd);
        for (std::size_t i = 0; i < batch.jobs.size() * 2; ++i) {
            SDL_GPUTextureRegion src{};
            src.texture = targets_[i];
            src.w = kThumbSize;
            src.h = kThumbSize;
            src.d = 1;
            SDL_GPUTextureTransferInfo dst{};
            dst.transfer_buffer = batch.download;
            dst.offset = one * static_cast<std::uint32_t>(i);
            dst.pixels_per_row = kThumbSize;
            dst.rows_per_layer = kThumbSize;
            SDL_DownloadFromGPUTexture(copy, &src, &dst);
        }
        SDL_EndGPUCopyPass(copy);
    }
    batch.fence = SDL_SubmitGPUCommandBufferAndAcquireFence(cmd);
    if (batch.fence == nullptr || batch.download == nullptr) {
        log::warn("studio: a batch failed: {}", SDL_GetError());
        SDL_ReleaseGPUTransferBuffer(device, batch.download);
        if (batch.fence != nullptr) {
            SDL_WaitForGPUFences(device, true, &batch.fence, 1);
            SDL_ReleaseGPUFence(device, batch.fence);
        }
        return;
    }
    for (std::size_t i = 0; i < batch.jobs.size(); ++i) {
        if (!drawn[i]) {
            batch.jobs[i].key.clear();  // Not drawn: it never comes.
        }
    }
    in_flight_.push_back(std::move(batch));
    last_batch_ms_ = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - start).count();
    busy_ms_ += last_batch_ms_;
}

void ModelStudio::finish(Batch& b) {
    SDL_GPUDevice* device = gpu_->device();
    const std::uint32_t one = kThumbSize * kThumbSize * 4u;
    const auto* bytes = static_cast<const std::uint8_t*>(SDL_MapGPUTransferBuffer(device, b.download, false));
    const SDL_GPUTextureFormat format = gpu_->swapchain_format();
    const bool bgra = format == SDL_GPU_TEXTUREFORMAT_B8G8R8A8_UNORM || format == SDL_GPU_TEXTUREFORMAT_B8G8R8A8_UNORM_SRGB;
    if (bytes != nullptr) {
        for (std::size_t i = 0; i < b.jobs.size(); ++i) {
            if (b.jobs[i].key.empty()) {
                continue;
            }
            const std::uint8_t* black = bytes + one * (i * 2);
            const std::uint8_t* white = bytes + one * (i * 2 + 1);
            // The two skies as they came out (light and tone change them a
            // little), from the first pixel: the camera always leaves the
            // corners empty.
            int sky_black[3];
            int span[3];
            int span_sum = 0;
            for (int c = 0; c < 3; ++c) {
                sky_black[c] = black[c];
                span[c] = std::max(1, white[c] - black[c]);
                span_sum += span[c];
            }
            std::vector<std::uint8_t> rgba(one);
            for (std::uint32_t p = 0; p < one; p += 4) {
                // How much of the sky shows through: the background.
                int through = 0;
                for (int c = 0; c < 3; ++c) {
                    through += white[p + c] - black[p + c];
                }
                const float a = std::clamp(1.0f - static_cast<float>(through) / static_cast<float>(span_sum), 0.0f, 1.0f);
                const int alpha = static_cast<int>(std::lround(a * 255.0f));
                // Over black, minus the black sky behind: the color times its alpha.
                int out[3];
                for (int c = 0; c < 3; ++c) {
                    const float v = static_cast<float>(black[p + c]) - (1.0f - a) * static_cast<float>(sky_black[c]);
                    out[c] = std::clamp(static_cast<int>(std::lround(v)), 0, alpha);
                }
                rgba[p] = static_cast<std::uint8_t>(out[bgra ? 2 : 0]);
                rgba[p + 1] = static_cast<std::uint8_t>(out[1]);
                rgba[p + 2] = static_cast<std::uint8_t>(out[bgra ? 0 : 2]);
                rgba[p + 3] = static_cast<std::uint8_t>(alpha);
            }
            done_[b.jobs[i].key] = std::move(rgba);
            fresh_.push_back(b.jobs[i].key);
        }
        SDL_UnmapGPUTransferBuffer(device, b.download);
    }
    for (const Job& j : b.jobs) {
        asked_.erase(j.key);
    }
    SDL_ReleaseGPUTransferBuffer(device, b.download);
    SDL_ReleaseGPUFence(device, b.fence);
    b.download = nullptr;
    b.fence = nullptr;
}

std::vector<ModelStudio::Picture> ModelStudio::take_ready() {
    std::vector<Picture> out;
    for (const std::vector<std::string>* list : {&fresh_, &wanted_}) {
        for (const std::string& key : *list) {
            if (const auto it = done_.find(key); it != done_.end()) {
                out.push_back({key, it->second});
            }
        }
    }
    fresh_.clear();
    wanted_.clear();
    return out;
}

}  // namespace sc
