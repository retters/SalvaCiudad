// Thumbnails and portraits rendered by the game (phase 120, D-11709).
//
// The interface shows buildings, things and animals by their own models,
// and villagers by their bodies and colors, rendered by a second
// SceneRenderer of its own (the "studio": no ground, one model, a fixed
// light and camera). With the content it loads the bodies, and then makes
// the picture of every definition in the background, a few milliseconds
// per frame; what a document asks for goes first. Pictures are kept.
//
// Keys (also the image paths the documents use, under "thumbs/"):
//   <def type>/<mod>/<name>              a definition's model: "building/core/stonecutter"
//                                        (types as in mods::ModelRef: building, mapFeature,
//                                        species, resource, crop)
//   person/<mod>/<race>/<f|m>/<look>     a villager: race id, sex and appearance bits
//
// A villager's key comes only from what the game saves (race, sex and
// appearance), so its portrait is the same after loading.
//
// Transparency: each picture is rendered twice, over a black sky and over a
// white one; where they differ is background. That needs nothing from the
// shaders and gives soft edges.
#pragma once

#include <cstdint>
#include <filesystem>
#include <map>
#include <memory>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

#include <SDL3/SDL_gpu.h>

#include "game/people.h"
#include "mods/mod_library.h"
#include "render/gpu_device.h"
#include "render/scene_renderer.h"
#include "sim/content.h"

namespace sc {

inline constexpr int kThumbSize = 128;  // Pixels, square.
inline constexpr std::string_view kThumbPrefix = "thumbs/";

struct ThumbKey {
    enum class Kind : std::uint8_t { Model, Person };
    Kind kind = Kind::Model;
    std::string def_type;  // Model: as in mods::ModelRef.
    std::string def_id;    // Model: "core:stonecutter"; Person: the race, "core:elf".
    bool female = false;
    std::uint32_t appearance = 0;
};

// Parses a key (with or without the "thumbs/" prefix); nothing if invalid.
[[nodiscard]] std::optional<ThumbKey> parse_thumb_key(std::string_view key);
// The key of a definition's model: "building/core/stonecutter".
[[nodiscard]] std::string thumb_key(std::string_view def_type, std::string_view def_id);
// The key of a villager's portrait, or empty if its race is unknown.
[[nodiscard]] std::string portrait_key(const sim::Content& content, const sim::Villager& v);

// The model file of a definition: the first one found of its references.
[[nodiscard]] std::optional<std::filesystem::path> thumb_model_file(const mods::BuildResult& pack,
                                                                    std::string_view def_type,
                                                                    std::string_view def_id);

class ModelStudio {
public:
    ModelStudio();
    ~ModelStudio();
    ModelStudio(const ModelStudio&) = delete;
    ModelStudio& operator=(const ModelStudio&) = delete;

    bool create(GpuDevice& gpu);
    void destroy();
    [[nodiscard]] bool ready() const { return renderer_ != nullptr; }

    // The content to draw from; forgets every picture (mods changed), loads
    // the bodies and queues every definition's picture.
    void set_content(std::shared_ptr<const mods::BuildResult> pack);

    // Asks for a picture; it comes out of take_ready() a few frames later
    // (at once if it was already made). Unknown keys never come.
    void request(std::string_view key);
    // Renders some of what was asked and collects what the GPU finished;
    // once per frame, outside any pass.
    void update();
    struct Picture {
        std::string key;
        std::vector<std::uint8_t> rgba;  // kThumbSize^2, premultiplied.
    };
    [[nodiscard]] std::vector<Picture> take_ready();

    [[nodiscard]] std::size_t made() const { return done_.size(); }
    [[nodiscard]] std::size_t bytes() const { return done_.size() * kThumbSize * kThumbSize * 4u; }
    [[nodiscard]] double last_batch_ms() const { return last_batch_ms_; }

    static constexpr int kPerFrame = 4;            // Pictures rendered per frame, at most,
    static constexpr double kFrameBudgetMs = 6.0;  // and no more once this much CPU went (after one).

private:
    struct Job {
        std::string key;
        ThumbKey parsed;
    };
    struct Batch {
        std::vector<Job> jobs;
        SDL_GPUFence* fence = nullptr;
        SDL_GPUTransferBuffer* download = nullptr;
    };
    // Puts the subject of `job` in the studio and returns how to look at it.
    bool stage(const Job& job, render::SceneView& view, float& radius);
    std::optional<render::ModelId> model(const std::filesystem::path& file, bool& skinned, render::SkinnedId& body,
                                         float& radius, float& base);
    bool ensure_targets(std::size_t count);
    void finish(Batch& batch);
    void load_cast();

    GpuDevice* gpu_ = nullptr;
    std::unique_ptr<render::SceneRenderer> renderer_;
    std::shared_ptr<const mods::BuildResult> pack_;
    std::unique_ptr<people::Cast> cast_;  // Loaded with the content.
    double cast_ms_ = 0.0;
    struct Loaded {
        bool skinned = false;
        render::ModelId model = 0;
        render::SkinnedId body = 0;
        float radius = 1.0f;
        float base = 0.0f;  // Lowest point (models stand on y = 0).
        float height = 1.0f;
    };
    std::map<std::string, Loaded> files_;
    std::map<std::string, std::optional<Loaded>> failed_files_;
    std::vector<std::string> queue_;     // Asked by the interface: first.
    std::vector<std::string> warm_;      // Every definition, in the background.
    std::map<std::string, bool> asked_;  // Queued or rendering.
    std::map<std::string, std::vector<std::uint8_t>> done_;
    std::vector<std::string> fresh_;     // Done since the last take_ready().
    std::vector<std::string> wanted_;    // Asked when already done: handed again.
    std::vector<Batch> in_flight_;
    std::vector<SDL_GPUTexture*> targets_;  // Two per job: black and white sky.
    double last_batch_ms_ = 0.0;
    double busy_ms_ = 0.0;  // CPU of the batches since the queue was last empty.
};

}  // namespace sc
