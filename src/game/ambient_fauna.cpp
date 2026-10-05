#include "game/ambient_fauna.h"

#include <algorithm>
#include <cmath>
#include <numbers>

#include "game/map_scene.h"
#include "game/model_file.h"

namespace sc::fauna {

namespace {

constexpr std::string_view kFiles[kSpecies] = {
    "models/fauna/squirrel.glb",    "models/fauna/squirrel_gray.glb", "models/fauna/owl.glb",
    "models/fauna/owl_snowy.glb",   "models/fauna/sparrow.glb",       "models/fauna/robin.glb",
    "models/fauna/bluebird.glb",    "models/fauna/crow.glb",          "models/fauna/raven.glb",
    "models/fauna/vulture.glb",     "models/fauna/fox.glb",           "models/fauna/fox_arctic.glb",
    "models/fauna/butterflies.glb", "models/fauna/fireflies.glb",     "models/fauna/dragonflies.glb",
    "models/fauna/hen.glb",         "models/fauna/hen_white.glb",     "models/fauna/chick.glb",
    "models/fauna/dog.glb",         "models/fauna/dog_shepherd.glb",  "models/fauna/dog_mastiff.glb",
    "models/fauna/dog_terrier.glb", "models/fauna/cat.glb",           "models/fauna/cat_tabby.glb",
    "models/fauna/cat_black.glb",   "models/fauna/cat_white.glb",     "models/fauna/kitten.glb",
    "models/animals/sheep.glb",     "models/fauna/ram.glb",           "models/fauna/goat.glb",
    "models/fauna/goat_brown.glb",  "models/fauna/goat_pied.glb",     "models/fauna/rabbit.glb",
    "models/fauna/lynx.glb",        "models/fauna/wildcat.glb",       "models/fauna/mammoth.glb",
};

constexpr float kTau = 2.0f * std::numbers::pi_v<float>;

std::uint32_t mix(std::int32_t x, std::int32_t z, std::uint32_t salt) {
    std::uint32_t h = static_cast<std::uint32_t>(x) * 0x9E3779B1u ^ static_cast<std::uint32_t>(z) * 0x85EBCA77u ^
                      (salt + 1u) * 0xC2B2AE3Du;
    h ^= h >> 15;
    h *= 0x2C1B3C6Du;
    h ^= h >> 12;
    h *= 0x297A2D39u;
    h ^= h >> 15;
    return h;
}

float unit(std::uint32_t h, std::uint32_t shift = 0) {
    return static_cast<float>((h >> shift) & 0xFFu) / 255.0f;
}

float to_float(sim::Fixed f) {
    return static_cast<float>(f.raw()) / 65536.0f;
}

std::uint64_t key(std::int32_t x, std::int32_t z) {
    return (static_cast<std::uint64_t>(static_cast<std::uint32_t>(x)) << 32) | static_cast<std::uint32_t>(z);
}

bool inside(const sim::MapData& map, std::int32_t cx, std::int32_t cz) {
    return cx >= 0 && cz >= 0 && cx < map.size && cz < map.size;
}

bool water(const sim::MapData& map, std::int32_t cx, std::int32_t cz) {
    return inside(map, cx, cz) && map.water_at(cx, cz);
}

bool land(const sim::MapData& map, float x, float z) {
    const auto cx = static_cast<std::int32_t>(std::floor(x));
    const auto cz = static_cast<std::int32_t>(std::floor(z));
    return inside(map, cx, cz) && !map.water_at(cx, cz);
}

bool sea(const sim::MapData& map, std::int32_t cx, std::int32_t cz) {
    const std::size_t cell = static_cast<std::size_t>(cz) * static_cast<std::size_t>(map.size) + static_cast<std::size_t>(cx);
    const auto region = static_cast<std::size_t>(map.region_at(cx, cz));
    return region < map.sea_levels.size() && map.sea_levels[region] != 0 && map.water[cell] == map.sea_levels[region];
}

// How close a person may come before an animal of this habit takes fright,
// and how far it then goes, in meters.
// The animals of the village: used to people, and they walk.
bool poultry(Species s) {
    return s >= Species::Hen && s < Species::Rabbit;
}
float fear(Species s) {
    if (poultry(s)) {
        return 1.2f;  // Used to people.
    }
    if (s == Species::Mammoth) {
        return 2.5f;  // It hardly minds them.
    }
    return s == Species::Fox || s == Species::FoxArctic ? 14.0f : habit(s) == Habit::Bird ? 5.0f : 6.0f;
}
float flight(Species s) {
    if (poultry(s)) {
        return 2.5f;
    }
    if (s == Species::Mammoth) {
        return 5.0f;
    }
    return s == Species::Fox || s == Species::FoxArctic ? 22.0f : habit(s) == Habit::Bird ? 12.0f : 7.0f;
}

}  // namespace

std::string_view model_file(Species species) {
    return species < Species::Count ? kFiles[static_cast<std::size_t>(species)] : std::string_view{};
}

Habit habit(Species species) {
    switch (species) {
        case Species::Squirrel:
        case Species::SquirrelGray:
        case Species::Fox:
        case Species::FoxArctic:
        case Species::Hen:
        case Species::HenWhite:
        case Species::Chick:
        case Species::Dog:
        case Species::DogShepherd:
        case Species::DogMastiff:
        case Species::DogTerrier:
        case Species::Cat:
        case Species::CatTabby:
        case Species::CatBlack:
        case Species::CatWhite:
        case Species::Kitten:
        case Species::Sheep:
        case Species::Ram:
        case Species::Goat:
        case Species::GoatBrown:
        case Species::GoatPied:
        case Species::Rabbit:
        case Species::Lynx:
        case Species::Wildcat:
        case Species::Mammoth: return Habit::Ground;
        case Species::Owl:
        case Species::OwlSnowy: return Habit::Perched;
        case Species::Butterflies:
        case Species::Fireflies:
        case Species::Dragonflies: return Habit::Swarm;
        default: return Habit::Bird;
    }
}

When when(const sim::Game& game) {
    When w;
    w.season = game.calendar().season;
    w.snow = game.snow() >= 30;
    w.night = game.night();
    const sim::DayTime time = game.day_time();
    w.twilight = !game.rules().day_night.enabled() || (!time.night && (time.progress < 150 || time.progress >= 850));
    w.day = static_cast<std::uint32_t>(game.calendar_day());
    return w;
}

std::optional<Species> resident(const Site& site, const When& when, std::uint32_t roll, std::uint32_t pick) {
    if (site.water) {
        return std::nullopt;
    }
    const bool warm = when.season == sim::Season::Spring || when.season == sim::Season::Summer;
    // The small birds are here from spring to summer; the robin stays the winter.
    const auto small_bird = [&] {
        constexpr Species kBirds[] = {Species::Sparrow, Species::Bluebird, Species::Robin};
        return warm ? kBirds[pick % 3u] : Species::Robin;
    };
    if (when.night) {
        if (site.tree && roll < 120) {
            return site.cold || when.snow ? Species::OwlSnowy : Species::Owl;
        }
        const bool damp = site.fresh_shore || site.terrain == sim::Terrain::ForestFloor || site.terrain == sim::Terrain::Meadow;
        if (when.season == sim::Season::Summer && damp && roll >= 120 && roll < 300) {
            return Species::Fireflies;
        }
        return std::nullopt;  // The rest are asleep.
    }
    if (site.garden) {
        // Gardens, orchards and flower beds draw the birds, and butterflies while they bloom.
        if (roll < (warm ? 600u : 250u)) {
            return small_bird();
        }
        if (warm && roll >= 600 && roll < 850) {
            return Species::Butterflies;
        }
        return std::nullopt;
    }
    if (site.fresh_shore && warm && roll < 250) {
        return Species::Dragonflies;
    }
    if (site.tree && !when.snow && roll < 140) {
        return (pick & 1u) != 0 ? Species::SquirrelGray : Species::Squirrel;
    }
    if (site.tree && roll >= 140 && roll < (warm ? 240u : 170u)) {
        return small_bird();
    }
    if (warm && site.flowers > 0 && roll >= 240 && roll < 240u + static_cast<std::uint32_t>(site.flowers) * 3u) {
        return Species::Butterflies;
    }
    const bool open = site.terrain == sim::Terrain::Meadow || site.terrain == sim::Terrain::Grass ||
                      site.terrain == sim::Terrain::ForestFloor;
    if (!site.built && open && roll >= 990) {
        return site.cold || when.snow ? Species::FoxArctic : Species::Fox;
    }
    return std::nullopt;
}

Species carrion_bird(bool dry, std::size_t which) {
    return dry ? Species::Vulture : which == 0 ? Species::Raven : Species::Crow;
}

float reach(int detail) {
    constexpr float kReach[] = {0.0f, 48.0f, 80.0f, 112.0f};
    return kReach[std::clamp(detail, 0, 3)];
}

void AmbientFauna::load(render::SceneRenderer& renderer, const mods::BuildResult& pack) {
    if (loaded_) {
        return;
    }
    for (std::size_t k = 0; k < kSpecies; ++k) {
        const std::filesystem::path file = mods::mod_file(pack.dir("core"), kFiles[k]);
        const auto data = file.empty() ? std::nullopt : load_model_file(file);
        Body body;
        if (!data.has_value() || !renderer.add_skinned_model(*data, body.id)) {
            continue;  // Not drawn.
        }
        const int idle = renderer.clip_index(body.id, habit(static_cast<Species>(k)) == Habit::Swarm ? "fly" : "idle");
        if (idle < 0) {
            continue;
        }
        const auto clip = [&](std::string_view name, std::uint32_t& index, float& length, float* speed) {
            const int i = renderer.clip_index(body.id, name);
            index = static_cast<std::uint32_t>(i < 0 ? idle : i);
            length = std::max(0.05f, renderer.clip_duration(body.id, index));
            if (speed != nullptr && i >= 0 && static_cast<std::size_t>(i) < data->clips.size() && data->clips[static_cast<std::size_t>(i)].speed > 0.0f) {
                *speed = data->clips[static_cast<std::size_t>(i)].speed;
            }
        };
        body.idle = static_cast<std::uint32_t>(idle);
        body.idle_length = std::max(0.05f, renderer.clip_duration(body.id, body.idle));
        clip("eat", body.eat, body.eat_length, nullptr);
        clip("walk", body.walk, body.walk_length, &body.walk_speed);
        clip("run", body.run, body.run_length, &body.run_speed);
        clip("fly", body.fly, body.fly_length, &body.fly_speed);
        body.loaded = true;
        bodies_[k] = body;
    }
    loaded_ = true;
}

void AmbientFauna::reset() {
    animals_.clear();
    built_.clear();
    gardens_.clear();
    carrion_.clear();
    map_ = nullptr;
    settled_ = false;
    ++built_version_;
}

void AmbientFauna::note_death(const sim::Game& game, float x, float z) {
    const sim::MapData& map = game.map();
    const auto cx = static_cast<std::int32_t>(std::floor(x));
    const auto cz = static_cast<std::int32_t>(std::floor(z));
    if (!inside(map, cx, cz) || map.water_at(cx, cz)) {
        return;
    }
    const std::uint8_t b = map.biome_at(cx, cz);
    const sim::Content& content = game.content();
    const bool dry = b < content.flora.biomes.size() &&
                     (content.flora.biomes[b].cover & (1u << static_cast<unsigned>(sim::BiomeCover::DryGrass))) != 0;
    if (carrion_.size() >= 16) {
        carrion_.erase(carrion_.begin());
    }
    carrion_.push_back({x, z, game.tick() + kCarrionTicks, dry});
    settled_ = false;
}

void AmbientFauna::survey(const sim::Game& game) {
    built_.clear();
    gardens_.clear();
    const sim::Content& content = game.content();
    for (const sim::Building& b : game.buildings().data()) {
        const sim::BuildingDef& d = content.buildings[b.def];
        const bool garden = (d.kind == sim::BuildingKind::Decoration &&
                             (d.category == sim::kGardenCategory || d.category == sim::kNatureCategory)) ||
                            d.mature_years > 0;
        // The squares it stands in, and those half a square around.
        const std::int32_t half = kSquare / 2;
        for (std::int32_t sz = (b.z - half) / kSquare - (b.z < half ? 1 : 0); sz <= (b.z + b.depth + half) / kSquare; ++sz) {
            for (std::int32_t sx = (b.x - half) / kSquare - (b.x < half ? 1 : 0); sx <= (b.x + b.width + half) / kSquare; ++sx) {
                built_.insert(key(sx, sz));
                if (garden) {
                    gardens_.insert(key(sx, sz));
                }
            }
        }
    }
}

Site AmbientFauna::site_of(const sim::Game& game, std::int32_t sx, std::int32_t sz, std::uint32_t& tree) const {
    const sim::MapData& map = game.map();
    const sim::Content& content = game.content();
    Site site;
    const std::int32_t cx = std::clamp(sx * kSquare + kSquare / 2, 0, map.size - 1);
    const std::int32_t cz = std::clamp(sz * kSquare + kSquare / 2, 0, map.size - 1);
    site.terrain = map.terrain_at(cx, cz);
    site.water = map.water_at(cx, cz);
    for (std::int32_t d = 2; d <= 6 && !site.fresh_shore; d += 2) {
        for (const auto& [dx, dz] : {std::pair{d, 0}, std::pair{-d, 0}, std::pair{0, d}, std::pair{0, -d}}) {
            if (water(map, cx + dx, cz + dz) && !sea(map, cx + dx, cz + dz)) {
                site.fresh_shore = true;
            }
        }
    }
    tree = game.tree_on(sx * kSquare, sz * kSquare, kSquare, kSquare, 0);
    site.tree = tree != 0;
    site.garden = gardens_.contains(key(sx, sz));
    site.built = built_.contains(key(sx, sz));
    const std::uint8_t b = map.biome_at(cx, cz);
    if (b < content.flora.biomes.size()) {
        const sim::BiomeDef& biome = content.flora.biomes[b];
        site.dry = (biome.cover & (1u << static_cast<unsigned>(sim::BiomeCover::DryGrass))) != 0;
        site.cold = biome.temperature[1] <= 45;
    }
    site.flowers = sim::wildflowers(map, content, cx, cz);
    return site;
}

std::uint32_t AmbientFauna::next(Animal& a) {
    return mix(static_cast<std::int32_t>(a.seed), static_cast<std::int32_t>(++a.steps), 9);
}

void AmbientFauna::rest(Animal& a) {
    const Body& body = bodies_[static_cast<std::size_t>(a.species)];
    const std::uint32_t h = next(a);
    a.mode = Mode::Rest;
    a.timer = 2.0f + 5.0f * unit(h);
    a.lift = 0.0f;
    const Habit how = habit(a.species);
    const bool eats = how != Habit::Perched && how != Habit::Swarm && (h & 0x100u) != 0;
    a.clip = eats ? body.eat : body.idle;
    a.clip_length = eats ? body.eat_length : body.idle_length;
    a.clip_time = std::fmod(a.clip_time, a.clip_length);
}

void AmbientFauna::move(const sim::Game& game, Animal& a, math::Vec3 goal, bool flee) {
    const sim::MapData& map = game.map();
    if (!land(map, goal.x, goal.z)) {
        return;  // Not into the water, not off the map: it stays where it is.
    }
    const Body& body = bodies_[static_cast<std::size_t>(a.species)];
    const float dx = goal.x - a.position.x;
    const float dz = goal.z - a.position.z;
    const float dist = std::sqrt(dx * dx + dz * dz);
    if (dist < 0.2f) {
        return;
    }
    const bool bird = habit(a.species) == Habit::Bird;
    const bool fox = a.species == Species::Fox || a.species == Species::FoxArctic;
    float speed = 1.0f;
    if (bird && (flee || dist > 2.0f)) {
        // A bird goes any distance on the wing, in an arc.
        a.mode = flee ? Mode::Flee : Mode::Fly;
        a.clip = body.fly;
        a.clip_length = body.fly_length;
        a.lift = std::min(4.0f, 0.6f + dist * 0.25f);
        speed = std::max(3.0f, body.fly_speed * 0.7f);
    } else if (bird) {
        a.mode = Mode::Move;  // A few hops.
        a.clip = body.walk;
        a.clip_length = body.walk_length;
        a.lift = 0.0f;
        speed = std::max(0.3f, body.walk_speed);
    } else {
        // A squirrel always scurries; a fox trots off and runs when frightened; hens walk.
        const bool runs = flee || !(fox || poultry(a.species));
        a.mode = flee ? Mode::Flee : Mode::Move;
        a.clip = runs ? body.run : body.walk;
        a.clip_length = runs ? body.run_length : body.walk_length;
        a.lift = 0.0f;
        speed = std::max(0.3f, runs ? body.run_speed : body.walk_speed) * (flee && !fox ? 1.6f : 1.0f);
    }
    a.from = a.position;
    a.goal = {goal.x, map_surface_height(map, goal.x, goal.z), goal.z};
    a.span = dist / speed;
    a.timer = 0.0f;
    a.yaw = std::atan2(dx, dz);
}

void AmbientFauna::step(const sim::Game& game, Animal& a, float dt) {
    a.clip_time = std::fmod(a.clip_time + dt, a.clip_length);
    const Habit how = habit(a.species);
    if (how == Habit::Swarm || how == Habit::Perched || dt <= 0.0f) {
        return;
    }
    // People near: off it goes, away from the nearest.
    a.look_in -= dt;
    if (a.look_in <= 0.0f && a.mode != Mode::Flee) {
        a.look_in = 0.3f + 0.2f * unit(next(a));
        const float reach2 = fear(a.species) * fear(a.species);
        float best = reach2;
        float away_x = 0.0f, away_z = 0.0f;
        for (const sim::Villager& v : game.villagers().data()) {
            const float dx = a.position.x - to_float(v.position.x);
            const float dz = a.position.z - to_float(v.position.z);
            const float d2 = dx * dx + dz * dz;
            if (d2 < best) {
                best = d2;
                away_x = dx;
                away_z = dz;
            }
        }
        if (best < reach2) {
            const float len = std::max(0.01f, std::sqrt(best));
            const float far = flight(a.species);
            move(game, a, {a.position.x + away_x / len * far, 0.0f, a.position.z + away_z / len * far}, true);
        }
    }
    if (a.mode == Mode::Rest) {
        a.timer -= dt;
        if (a.timer > 0.0f) {
            return;
        }
        // Somewhere around home; a bird that strayed (it fled) flies back.
        const std::uint32_t h = next(a);
        const float angle = unit(h) * kTau;
        const float hop = how == Habit::Bird && (h & 0x300u) != 0 ? 1.5f : a.range;
        const float away = std::hypot(a.position.x - a.home.x, a.position.z - a.home.z);
        const math::Vec3 around = away > a.range * 1.5f ? a.home : a.position;
        const float r = hop * (0.3f + 0.7f * unit(h, 8));
        math::Vec3 goal{around.x + std::sin(angle) * r, 0.0f, around.z + std::cos(angle) * r};
        if (std::hypot(goal.x - a.home.x, goal.z - a.home.z) > a.range) {
            goal = {a.home.x + std::sin(angle) * a.range * 0.5f, 0.0f, a.home.z + std::cos(angle) * a.range * 0.5f};
        }
        const Mode before = a.mode;
        move(game, a, goal, false);
        if (a.mode == before) {
            rest(a);  // Nowhere to go this time.
        }
        return;
    }
    a.timer += dt;
    const float t = std::min(1.0f, a.timer / std::max(0.01f, a.span));
    a.position.x = a.from.x + (a.goal.x - a.from.x) * t;
    a.position.z = a.from.z + (a.goal.z - a.from.z) * t;
    const float ground = a.lift > 0.0f ? a.from.y + (a.goal.y - a.from.y) * t
                                       : map_surface_height(game.map(), a.position.x, a.position.z);
    a.position.y = ground + a.lift * 4.0f * t * (1.0f - t);
    if (t >= 1.0f) {
        const bool fled = a.mode == Mode::Flee;
        rest(a);
        if (fled) {
            a.timer += 4.0f;  // It keeps its distance a while.
        }
    }
}

void AmbientFauna::add(const sim::Game& game, std::uint64_t id, Species species, float x, float z, float perch, float range) {
    const Body& body = bodies_[static_cast<std::size_t>(species)];
    if (!body.loaded) {
        return;
    }
    const sim::MapData& map = game.map();
    Animal a;
    a.species = species;
    a.home = {x, map_surface_height(map, x, z), z};
    a.perch = perch;
    a.range = range;
    a.position = a.home;
    a.seed = mix(static_cast<std::int32_t>(id), static_cast<std::int32_t>(id >> 32), 5);
    a.yaw = unit(a.seed, 8) * kTau;
    a.clip_time = unit(a.seed, 16) * 3.0f;
    a.stays = true;
    rest(a);
    if (habit(species) == Habit::Swarm) {
        a.clip = body.fly;
        a.clip_length = body.fly_length;
    }
    animals_.emplace(id, a);
}

void AmbientFauna::settle(const sim::Game& game, std::int32_t fsx, std::int32_t fsz, std::int32_t span) {
    const sim::MapData& map = game.map();
    for (auto& [id, a] : animals_) {
        a.stays = false;
    }
    const std::int32_t last = (map.size - 1) / kSquare;
    for (std::int32_t sz = std::max(0, fsz - span); sz <= std::min(last, fsz + span); ++sz) {
        for (std::int32_t sx = std::max(0, fsx - span); sx <= std::min(last, fsx + span); ++sx) {
            if ((sx - fsx) * (sx - fsx) + (sz - fsz) * (sz - fsz) > span * span) {
                continue;
            }
            std::uint32_t tree = 0;
            const Site site = site_of(game, sx, sz, tree);
            const std::uint32_t h = mix(sx, sz, 4);
            const std::optional<Species> who = resident(site, when_, h % 1000u, (h >> 12) & 63u);
            if (!who) {
                continue;
            }
            const std::uint64_t id = key(sx, sz);
            if (const auto it = animals_.find(id); it != animals_.end() && it->second.species == *who) {
                it->second.stays = true;
                continue;
            }
            animals_.erase(id);
            // Home: by its tree for those of the trees, else somewhere in the square.
            float x = static_cast<float>(sx * kSquare) + 2.0f + unit(h, 16) * static_cast<float>(kSquare - 4);
            float z = static_cast<float>(sz * kSquare) + 2.0f + unit(h, 24) * static_cast<float>(kSquare - 4);
            float perch = 0.0f;
            const Habit how = habit(*who);
            const bool of_trees = *who == Species::Squirrel || *who == Species::SquirrelGray || how == Habit::Perched ||
                                  (how == Habit::Bird && !site.garden);
            if (of_trees && tree != 0 && tree - 1 < map.features.size()) {
                const sim::MapFeature& f = map.features[tree - 1];
                x = to_float(f.x) + (how == Habit::Perched ? 0.5f : 1.2f);
                z = to_float(f.z) + (how == Habit::Perched ? 0.3f : 0.8f);
                if (how == Habit::Perched) {
                    perch = static_cast<float>(sim::MapData::tree_height_cm(f)) * 0.01f * 0.5f;
                }
            }
            if (*who != Species::Dragonflies && !land(map, x, z)) {
                continue;
            }
            const float range = how == Habit::Ground ? (*who == Species::Fox || *who == Species::FoxArctic ? 14.0f : 5.0f)
                                                     : how == Habit::Bird ? 6.0f : 0.0f;
            add(game, id, *who, x, z, perch, range);
        }
    }
    // The carrion birds, around each place where somebody died.
    const float far = static_cast<float>((span + 1) * kSquare);
    const float fx = static_cast<float>(fsx * kSquare + kSquare / 2);
    const float fz = static_cast<float>(fsz * kSquare + kSquare / 2);
    for (std::size_t c = 0; c < carrion_.size(); ++c) {
        const Carrion& place = carrion_[c];
        if (std::hypot(place.x - fx, place.z - fz) > far) {
            continue;
        }
        const std::uint64_t base = (std::uint64_t{1} << 63) | (place.until << 8);
        for (std::size_t bird = 0; bird < kCarrionBirds; ++bird) {
            const std::uint64_t id = base | bird;
            if (const auto it = animals_.find(id); it != animals_.end()) {
                it->second.stays = true;
                continue;
            }
            const float angle = static_cast<float>(bird) * kTau / static_cast<float>(kCarrionBirds);
            add(game, id, carrion_bird(place.dry, bird), place.x + std::sin(angle) * 1.2f, place.z + std::cos(angle) * 1.2f, 0.0f, 4.0f);
        }
    }
    // Phase 105: the hens of each coop, as many as it has left, and a chick with two or more.
    for (std::size_t i = 0; i < game.buildings().size(); ++i) {
        const sim::Building& b = game.buildings().data()[i];
        const sim::BuildingDef& d = game.content().buildings[b.def];
        if (d.coop_gives == sim::kNoDef || b.state != sim::BuildingState::Complete || when_.night) {
            continue;  // (At night they are inside.)
        }
        const float cx = static_cast<float>(b.x) + static_cast<float>(b.width) * 0.5f;
        const float cz = static_cast<float>(b.z) + static_cast<float>(b.depth) * 0.5f;
        if (std::hypot(cx - fx, cz - fz) > far) {
            continue;
        }
        const std::size_t birds = b.flock + (b.flock >= 2 ? 1u : 0u);
        const std::uint64_t base = (std::uint64_t{1} << 62) | (static_cast<std::uint64_t>(game.buildings().entities()[i].index) << 8);
        for (std::size_t bird = 0; bird < birds; ++bird) {
            const std::uint64_t id = base | bird;
            if (const auto it = animals_.find(id); it != animals_.end()) {
                it->second.stays = true;
                continue;
            }
            const Species who = bird >= b.flock ? Species::Chick : bird % 2 == 0 ? Species::Hen : Species::HenWhite;
            const float angle = static_cast<float>(bird) * kTau / static_cast<float>(birds) + 0.6f;
            const float out_by = static_cast<float>(std::max(b.width, b.depth)) * 0.5f + 1.0f;
            add(game, id, who, cx + std::sin(angle) * out_by, cz + std::cos(angle) * out_by, 0.0f, 2.5f);
        }
    }
    // Phase 109: rabbits out in their zones at dawn and dusk, a few of those there are; and the lynx of a
    // zone (a wildcat in every other one), one day in four.
    for (std::size_t zi = 0; zi < game.map().zones.size() && when_.twilight; ++zi) {
        const sim::Zone& zone = game.map().zones[zi];
        if (zone.type != sim::ZoneType::Rabbits && zone.type != sim::ZoneType::Lynx) {
            continue;
        }
        const float zx = to_float(zone.x), zz = to_float(zone.z), zr = to_float(zone.radius);
        if (std::hypot(zx - fx, zz - fz) > far + zr) {
            continue;
        }
        const bool lynx = zone.type == sim::ZoneType::Lynx;
        const std::int32_t living = zi < game.zone_animals().size() ? game.zone_animals()[zi] : 0;
        if (lynx && mix(static_cast<std::int32_t>(zi), static_cast<std::int32_t>(when_.day), 12) % 4u != 0) {
            continue;
        }
        const std::size_t shown = lynx ? (living > 0 ? 1u : 0u) : static_cast<std::size_t>(std::clamp(living / 3, 0, 5));
        for (std::size_t n = 0; n < shown; ++n) {
            const std::uint64_t id = (std::uint64_t{1} << 59) | (static_cast<std::uint64_t>(zi) << 8) | n;
            if (const auto it = animals_.find(id); it != animals_.end()) {
                it->second.stays = true;
                continue;
            }
            const std::uint32_t h = mix(static_cast<std::int32_t>(zi), static_cast<std::int32_t>(n), 13);
            const float angle = unit(h) * kTau;
            const float out_by = unit(h, 8) * zr * 0.6f;
            const float x = zx + std::sin(angle) * out_by, z = zz + std::cos(angle) * out_by;
            if (std::hypot(x - fx, z - fz) > far || !land(game.map(), x, z)) {
                continue;
            }
            add(game, id, lynx ? (zi % 2 == 0 ? Species::Lynx : Species::Wildcat) : Species::Rabbit, x, z, 0.0f, lynx ? 10.0f : 4.0f);
        }
    }
    // Phase 111: the mammoths of a zone, those left of the herd, day and night while the winter lasts.
    for (std::size_t zi = 0; zi < game.map().zones.size(); ++zi) {
        const sim::Zone& zone = game.map().zones[zi];
        const std::int32_t living = zi < game.zone_animals().size() ? game.zone_animals()[zi] : 0;
        if (zone.type != sim::ZoneType::Mammoths || living <= 0) {
            continue;
        }
        const float zx = to_float(zone.x), zz = to_float(zone.z), zr = to_float(zone.radius);
        if (std::hypot(zx - fx, zz - fz) > far + zr) {
            continue;
        }
        for (std::size_t n = 0; n < static_cast<std::size_t>(living); ++n) {
            const std::uint64_t id = (std::uint64_t{1} << 58) | (static_cast<std::uint64_t>(zi) << 8) | n;
            if (const auto it = animals_.find(id); it != animals_.end()) {
                it->second.stays = true;
                continue;
            }
            const std::uint32_t h = mix(static_cast<std::int32_t>(zi), static_cast<std::int32_t>(n), 14);
            const float angle = unit(h) * kTau;
            const float out_by = 6.0f + unit(h, 8) * zr * 0.35f;
            const float x = zx + std::sin(angle) * out_by, z = zz + std::cos(angle) * out_by;
            if (std::hypot(x - fx, z - fz) > far || !land(game.map(), x, z)) {
                continue;
            }
            add(game, id, Species::Mammoth, x, z, 0.0f, 14.0f);
        }
    }
    // Phase 107: the herd of each fold: in its pasture by day, by the fold at night (or with no pasture).
    for (std::size_t i = 0; i < game.buildings().size(); ++i) {
        const sim::Building& b = game.buildings().data()[i];
        const sim::HerdDef* herd = b.state == sim::BuildingState::Complete ? game.herd_of(b) : nullptr;
        if (herd == nullptr) {
            continue;
        }
        const float cx = static_cast<float>(b.x) + static_cast<float>(b.width) * 0.5f;
        const float cz = static_cast<float>(b.z) + static_cast<float>(b.depth) * 0.5f;
        if (std::hypot(cx - fx, cz - fz) > far) {
            continue;
        }
        const bool out = !when_.night && !b.fields.empty();
        const std::size_t animals = static_cast<std::size_t>(b.females) + b.males;
        // (Another herd in the same fold is other animals: phase 108.)
        const std::uint64_t base = (std::uint64_t{1} << 60) | (static_cast<std::uint64_t>(herd->look) << 56) |
                                   (static_cast<std::uint64_t>(game.buildings().entities()[i].index) << 8) | (out ? 0x80u : 0u);
        for (std::size_t n = 0; n < animals && n < 64; ++n) {
            const std::uint64_t id = base | n;
            if (const auto it = animals_.find(id); it != animals_.end()) {
                it->second.stays = true;
                continue;
            }
            const std::uint32_t h = mix(b.x + static_cast<std::int32_t>(n) * 7, b.z, 11);
            float x = cx + (unit(h) - 0.5f) * static_cast<float>(b.width) * 0.5f;
            float z = cz + (unit(h, 8) - 0.5f) * static_cast<float>(b.depth) * 0.5f;
            float range = 1.5f;
            if (out) {
                const sim::Field& f = b.fields[0];
                x = static_cast<float>(f.x) + 1.5f + unit(h) * std::max(0.0f, static_cast<float>(f.w) - 3.0f);
                z = static_cast<float>(f.z) + 1.5f + unit(h, 8) * std::max(0.0f, static_cast<float>(f.d) - 3.0f);
                range = std::max(1.0f, static_cast<float>(std::min(f.w, f.d)) * 0.25f);
            }
            const bool female = n < b.females;
            const Species who = herd->look == 1 ? (!female ? Species::GoatPied : n % 2 == 0 ? Species::Goat : Species::GoatBrown)
                                                : (female ? Species::Sheep : Species::Ram);
            add(game, id, who, x, z, 0.0f, range);
        }
    }
    // Phase 106: the dog of each kennel, and the cat of each house that has one.
    for (std::size_t i = 0; i < game.buildings().size(); ++i) {
        const sim::Building& b = game.buildings().data()[i];
        const sim::BuildingDef& d = game.content().buildings[b.def];
        const bool kennel = d.guard_radius > 0;
        if ((!kennel && b.cat == 0) || b.state != sim::BuildingState::Complete) {
            continue;
        }
        const float cx = static_cast<float>(b.x) + static_cast<float>(b.width) * 0.5f;
        const float cz = static_cast<float>(b.z) + static_cast<float>(b.depth) * 0.5f;
        if (std::hypot(cx - fx, cz - fz) > far) {
            continue;
        }
        const std::uint64_t id = (std::uint64_t{1} << 61) | (static_cast<std::uint64_t>(game.buildings().entities()[i].index) << 8) |
                                 (kennel ? 0u : b.cat);
        if (const auto it = animals_.find(id); it != animals_.end()) {
            it->second.stays = true;
            continue;
        }
        constexpr Species kDogs[] = {Species::Dog, Species::DogShepherd, Species::DogMastiff, Species::DogTerrier};
        constexpr Species kCats[] = {Species::Cat, Species::CatTabby, Species::CatBlack, Species::CatWhite, Species::Kitten};
        const Species who = kennel ? kDogs[mix(b.x, b.z, 9) % std::size(kDogs)] : kCats[(b.cat - 1u) % std::size(kCats)];
        // By the door (the kennel's, the house's), roaming a little: a dog farther than a cat.
        const float out_by = static_cast<float>(std::max(b.width, b.depth)) * 0.5f + 1.2f;
        const float angle = unit(mix(b.x, b.z, 10)) * kTau;
        add(game, id, who, cx + std::sin(angle) * out_by, cz + std::cos(angle) * out_by, 0.0f, kennel ? 6.0f : 3.0f);
    }
    std::erase_if(animals_, [](const auto& entry) { return !entry.second.stays; });
}

void AmbientFauna::update(const sim::Game& game, math::Vec3 focus, int detail, float game_dt,
                          std::vector<render::CharacterInstance>& out) {
    if (!loaded_) {
        return;
    }
    detail = std::clamp(detail, 0, 3);
    const float far = reach(detail);
    if (far <= 0.0f) {
        animals_.clear();
        settled_ = false;
        detail_ = detail;
        return;
    }
    const sim::MapData& map = game.map();
    if (map_ != &map) {
        animals_.clear();
        map_ = &map;
        settled_ = false;
        built_seen_ = 0;
    }
    const std::size_t before = carrion_.size();
    std::erase_if(carrion_, [&](const Carrion& c) { return game.tick() >= c.until; });
    if (carrion_.size() != before) {
        settled_ = false;
    }
    if (built_seen_ != built_version_) {
        survey(game);
        built_seen_ = built_version_;
        settled_ = false;
    }
    const When now = when(game);
    const auto fsx = static_cast<std::int32_t>(std::floor(focus.x / static_cast<float>(kSquare)));
    const auto fsz = static_cast<std::int32_t>(std::floor(focus.z / static_cast<float>(kSquare)));
    if (!settled_ || !(now == when_) || detail != detail_ || fsx != focus_sx_ || fsz != focus_sz_) {
        when_ = now;
        detail_ = detail;
        focus_sx_ = fsx;
        focus_sz_ = fsz;
        settled_ = true;
        settle(game, fsx, fsz, static_cast<std::int32_t>(std::ceil(far / static_cast<float>(kSquare))));
    }
    const float dt = std::clamp(game_dt, 0.0f, 0.25f);
    for (auto& [id, a] : animals_) {
        step(game, a, dt);
        const Body& body = bodies_[static_cast<std::size_t>(a.species)];
        render::CharacterInstance c;
        c.body = body.id;
        c.clip = a.clip;
        c.time = a.clip_time;
        c.position = {a.position.x, a.position.y + a.perch, a.position.z};
        c.yaw = a.yaw;
        out.push_back(c);
    }
}

}  // namespace sc::fauna
