// The people of the game (phase 57): the low-poly characters, one or more
// per race and sex, with their clips, the tools they hold while a clip
// plays and their palettes (skin, hair and clothes). View only: nothing
// here changes the simulation.
#pragma once

#include <array>
#include <cstdint>
#include <filesystem>
#include <span>
#include <string>
#include <string_view>
#include <vector>

#include "render/model.h"
#include "render/scene_renderer.h"
#include "sim/content.h"
#include "sim/game.h"

namespace sc::people {

// What a character is doing, as far as its animation goes.
enum class Act : std::uint8_t { Idle, Walk, Run, Chop, Shoot, FishCast, Fish, Work, Count };
inline constexpr std::size_t kActs = static_cast<std::size_t>(Act::Count);
// The clip of each act; a body without one plays "idle" instead.
inline constexpr std::string_view kActClips[kActs] = {"idle", "walk", "run", "chop", "shoot", "fish_cast", "fish_stand", "work"};

// A character model loaded in the renderer.
struct Body {
    std::string name;  // Its file's name without ".glb".
    render::SkinnedId id = 0;
    std::array<std::uint32_t, kActs> clip{};
    std::array<float, kActs> length{};          // Seconds.
    std::array<std::uint32_t, kActs> tools{};   // Accessory bits shown while the act plays.
    float walk_speed = 1.4f;  // Meters per second its clips cover at their own rate.
    float run_speed = 2.8f;
    float height = 1.8f;
    // Its palettes in the renderer's list: skins x hairs x outfits.
    std::uint32_t first_palette = 0;
    std::uint32_t skins = 1;
    std::uint32_t hairs = 1;
    std::uint32_t outfits = 1;

    [[nodiscard]] std::uint32_t palette_count() const { return skins * hairs * outfits; }
};

// The animation state of one character.
struct Motion {
    Act act = Act::Idle;
    float time = 0.0f;
};

// A character runs when it must (see act_of) or when it moves this many
// times faster than its walk.
inline constexpr float kRunAbove = 1.5f;

// Advances `m` toward `wanted`. Walking and running play at the rate that
// keeps the feet on the ground at `speed` (m/s of game time); the other
// acts play at their own rate. `game_dt`: seconds of game time; `rest_dt`:
// the same, never faster than real time.
void advance(const Body& body, Motion& m, Act wanted, float speed, float game_dt, float rest_dt);
// The clip, its time and the tool in hand, into `c`.
void pose(const Body& body, const Motion& m, render::CharacterInstance& c);

// What a villager's task looks like. `moving`: it changed place this tick.
[[nodiscard]] Act act_of(const sim::Game& game, const sim::Villager& v, bool moving);

// How big a villager is drawn: children are the adult's body, smaller.
[[nodiscard]] float scale_of(std::int32_t age_years, std::uint32_t appearance);

// The palette slots this module fills; the others stay white.
inline constexpr std::size_t kSkinSlot = 0;
inline constexpr std::size_t kHairSlot = 1;
inline constexpr std::size_t kTopSlot = 2;
inline constexpr std::size_t kBottomSlot = 3;

// The palettes of a model: its own skin and every one of `skins`, its own
// hair and every one of `hairs`, its own clothes and the game's outfits,
// in the order Cast::palette counts them. Colors are 0xRRGGBB, sRGB. What
// the model has no material for is not multiplied.
[[nodiscard]] std::vector<render::Palette> make_palettes(const render::ModelData& model, std::span<const std::uint32_t> skins,
                                                         std::span<const std::uint32_t> hairs, std::uint32_t& skin_count,
                                                         std::uint32_t& hair_count, std::uint32_t& outfit_count);

// Loads a character into the renderer with the tools its clips name
// ("<clip>_prop"), read from `core_dir`, and its far version if `far` is
// given. `body.name` and the palette fields are left to the caller. False
// if it is not a usable character.
[[nodiscard]] bool load_body(render::SceneRenderer& renderer, const std::filesystem::path& core_dir,
                             const render::ModelData& model, const render::ModelData* far, Body& body);

// Every character of the races, loaded once.
class Cast {
public:
    // Loads the bodies of every race of `content` from the core mod's
    // folder and sets the renderer's palettes. A missing model is skipped.
    bool load(render::SceneRenderer& renderer, const std::filesystem::path& core_dir, const sim::Content& content);

    [[nodiscard]] bool loaded() const { return !bodies_.empty(); }
    [[nodiscard]] const std::vector<Body>& bodies() const { return bodies_; }
    // The palettes handed to the renderer (the viewer adds its own after them).
    [[nodiscard]] const std::vector<render::Palette>& palettes() const { return palettes_; }
    // The body of a villager: one of its race's for its sex, by its
    // appearance bits. Never fails once loaded.
    [[nodiscard]] const Body& body(std::size_t race, bool female, std::uint32_t appearance) const;
    [[nodiscard]] std::size_t race_count() const { return races_.size(); }
    // Any body, for whoever has no race (raiders, soldiers): a human's.
    [[nodiscard]] const Body& any_body(std::uint32_t seed) const;
    // Its palette, by the same bits.
    [[nodiscard]] static std::uint32_t palette(const Body& body, std::uint32_t appearance);
    // The body loaded from `name`, or null.
    [[nodiscard]] const Body* find(std::string_view name) const;

private:
    struct RaceBodies {
        std::vector<std::uint32_t> male;
        std::vector<std::uint32_t> female;
    };
    std::vector<Body> bodies_;
    std::vector<RaceBodies> races_;
    std::vector<render::Palette> palettes_;
};

}  // namespace sc::people
