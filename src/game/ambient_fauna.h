// Phase 92: the animals that only give the map life. Squirrels among the
// trees, owls at night, small birds that leave in autumn, butterflies over
// the flowers, fireflies, dragonflies, a fox now and then, and crows where
// somebody died. The view draws them near the camera and moves them; they
// are not in the simulation, its hashes or the saved games.
#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <string_view>
#include <unordered_map>
#include <unordered_set>
#include <vector>

#include "math/vec.h"
#include "mods/mod_library.h"
#include "render/scene_renderer.h"
#include "sim/game.h"

namespace sc::fauna {

enum class Species : std::uint8_t {
    Squirrel,
    SquirrelGray,
    Owl,
    OwlSnowy,
    Sparrow,
    Robin,
    Bluebird,
    Crow,
    Raven,
    Vulture,
    Fox,
    FoxArctic,
    Butterflies,
    Fireflies,
    Dragonflies,
    // Phase 105: the hens of a coop, as many as it has, and a chick. Not wild.
    Hen,
    HenWhite,
    Chick,
    // Phase 106: the dog of a kennel (one of four, by the kennel) and the cat of a house (by its look).
    Dog,
    DogShepherd,
    DogMastiff,
    DogTerrier,
    Cat,
    CatTabby,
    CatBlack,
    CatWhite,
    Kitten,
    // Phase 107: the animals of a fold: as many as it has, in its pasture by day and by the fold at night.
    Sheep,
    Ram,
    // Phase 108: goats (the pied one is the male).
    Goat,
    GoatBrown,
    GoatPied,
    Count
};
inline constexpr std::size_t kSpecies = static_cast<std::size_t>(Species::Count);

// Its model, a file of the core mod.
[[nodiscard]] std::string_view model_file(Species species);

// How an animal lives: on the ground, as a bird (on the ground, and flying
// off), perched in a tree, or as a swarm that stays in the air of its place.
enum class Habit : std::uint8_t { Ground, Bird, Perched, Swarm };
[[nodiscard]] Habit habit(Species species);

// What the time does to who is about.
struct When {
    sim::Season season = sim::Season::Spring;
    bool snow = false;
    bool night = false;
    bool operator==(const When&) const = default;
};
[[nodiscard]] When when(const sim::Game& game);

// The map is looked at in squares of this many meters: one animal (or one
// swarm) at most lives in each.
inline constexpr std::int32_t kSquare = 16;

// What a square offers an animal.
struct Site {
    sim::Terrain terrain = sim::Terrain::Grass;
    bool water = false;        // Its middle is water.
    bool fresh_shore = false;  // Fresh water within a few meters of its middle.
    bool tree = false;         // A tree stands in it.
    bool garden = false;       // A garden, an orchard or a nature decoration stands in it or beside it.
    bool built = false;        // Buildings in it or beside it: the shy ones keep away.
    bool dry = false;          // A biome of dry summers.
    bool cold = false;         // A cold biome.
    std::int32_t flowers = 0;  // sim::wildflowers at its middle, 0 to 100.
};

// Who lives in a square, if anybody: by what it offers, the time, and two
// numbers of the square (`roll`, 0 to 999, and `pick`). The same answer for
// the same questions.
[[nodiscard]] std::optional<Species> resident(const Site& site, const When& when, std::uint32_t roll, std::uint32_t pick);

// The carrion birds that gather where somebody died: crows and a raven, or
// vultures where summers are dry. They stay this many ticks (a month).
inline constexpr std::uint64_t kCarrionTicks = 1000;
inline constexpr std::size_t kCarrionBirds = 3;
[[nodiscard]] Species carrion_bird(bool dry, std::size_t which);

// How far from where the camera looks animals are drawn, by the "ground
// detail" setting (0: none).
[[nodiscard]] float reach(int detail);

// Moves and draws them.
class AmbientFauna {
public:
    void load(render::SceneRenderer& renderer, const mods::BuildResult& pack);
    // A new map: nobody about, nothing remembered.
    void reset();
    void buildings_changed() { ++built_version_; }
    // Somebody died at (x, z): carrion birds will gather there for a while.
    void note_death(const sim::Game& game, float x, float z);
    // Adds the animals around `focus` to `out`. `game_dt`: the game time
    // passed (0 while paused: they hold still).
    void update(const sim::Game& game, math::Vec3 focus, int detail, float game_dt,
                std::vector<render::CharacterInstance>& out);
    [[nodiscard]] std::size_t shown() const { return animals_.size(); }

private:
    struct Body {
        bool loaded = false;
        render::SkinnedId id = 0;
        std::uint32_t idle = 0, eat = 0, walk = 0, run = 0, fly = 0;
        float idle_length = 1.0f, eat_length = 1.0f, walk_length = 1.0f, run_length = 1.0f, fly_length = 1.0f;
        float walk_speed = 0.5f, run_speed = 2.0f, fly_speed = 6.0f;  // m/s at which each clip's limbs keep pace.
    };
    enum class Mode : std::uint8_t { Rest, Move, Fly, Flee };
    struct Animal {
        Species species = Species::Squirrel;
        math::Vec3 home;         // Where it lives (on the ground).
        float perch = 0.0f;      // Meters over the ground it sits at (owls).
        float range = 4.0f;      // How far from home it goes.
        math::Vec3 position;
        math::Vec3 from;         // Where the move under way started.
        math::Vec3 goal;
        float yaw = 0.0f;
        Mode mode = Mode::Rest;
        float timer = 0.0f;      // Seconds left of a rest; seconds into a move.
        float span = 1.0f;       // Seconds the move under way takes.
        float lift = 0.0f;       // Meters a flight rises at its middle.
        std::uint32_t clip = 0;
        float clip_time = 0.0f;
        float clip_length = 1.0f;
        std::uint32_t steps = 0; // Decisions taken, to draw the next number from.
        std::uint32_t seed = 0;
        float look_in = 0.0f;    // Seconds until it looks around for people again.
        bool stays = false;      // Still wanted after the last look at who lives where.
    };
    struct Carrion {
        float x = 0.0f;
        float z = 0.0f;
        std::uint64_t until = 0;
        bool dry = false;
    };

    void survey(const sim::Game& game);
    [[nodiscard]] Site site_of(const sim::Game& game, std::int32_t sx, std::int32_t sz, std::uint32_t& tree) const;
    void settle(const sim::Game& game, std::int32_t fsx, std::int32_t fsz, std::int32_t span);
    void add(const sim::Game& game, std::uint64_t id, Species species, float x, float z, float perch, float range);
    void rest(Animal& a);
    void move(const sim::Game& game, Animal& a, math::Vec3 goal, bool flee);
    void step(const sim::Game& game, Animal& a, float dt);
    [[nodiscard]] std::uint32_t next(Animal& a);

    std::array<Body, kSpecies> bodies_{};
    bool loaded_ = false;
    std::unordered_map<std::uint64_t, Animal> animals_;  // By the square (or the carrion and bird) they belong to.
    std::unordered_set<std::uint64_t> built_;            // Squares with buildings in or beside them.
    std::unordered_set<std::uint64_t> gardens_;          // Squares with a garden, an orchard or a nature decoration in or beside them.
    std::uint64_t built_version_ = 1;
    std::uint64_t built_seen_ = 0;
    std::vector<Carrion> carrion_;
    When when_;
    const void* map_ = nullptr;
    int detail_ = -1;
    std::int32_t focus_sx_ = 0;
    std::int32_t focus_sz_ = 0;
    bool settled_ = false;
};

}  // namespace sc::fauna
