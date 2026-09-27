#include "game/test_scene.h"

#include <algorithm>
#include <cmath>
#include <optional>

#include "core/file_io.h"
#include "core/log.h"
#include "core/text.h"
#include "game/camera.h"

namespace sc {

namespace {

// Small deterministic generator (PCG32); presentation only.
class Random {
public:
    explicit Random(std::uint64_t seed) : state_(seed * 6364136223846793005ull + 1442695040888963407ull) {}

    std::uint32_t next() {
        const std::uint64_t old = state_;
        state_ = old * 6364136223846793005ull + 1442695040888963407ull;
        const auto xorshifted = static_cast<std::uint32_t>(((old >> 18u) ^ old) >> 27u);
        const auto rot = static_cast<std::uint32_t>(old >> 59u);
        return (xorshifted >> rot) | (xorshifted << ((32u - rot) & 31u));
    }
    float unit() { return static_cast<float>(next() >> 8) * (1.0f / 16777216.0f); }
    float range(float lo, float hi) { return lo + (hi - lo) * unit(); }

private:
    std::uint64_t state_;
};

float clamp_to_area(float v) {
    return std::clamp(v, -kTestSceneHalfSize + 5.0f, kTestSceneHalfSize - 5.0f);
}

}  // namespace

TestSceneLayout make_test_scene_layout(std::size_t count, std::uint32_t seed) {
    TestSceneLayout layout;
    Random rng(seed);
    const std::size_t houses_target = count * 6 / 100;
    const std::size_t rocks_target = count * 10 / 100;
    const std::size_t trees_target = count - houses_target - rocks_target;

    // Villages: houses around a few centers, on a loose grid, facing the center.
    const int villages = std::max(1, static_cast<int>(houses_target / 120));
    for (std::size_t i = 0; i < houses_target; ++i) {
        const int v = static_cast<int>(i % static_cast<std::size_t>(villages));
        Random vr(seed * 977u + static_cast<std::uint32_t>(v));
        const float cx = v == 0 ? 0.0f : vr.range(-800.0f, 800.0f);
        const float cz = v == 0 ? 0.0f : vr.range(-800.0f, 800.0f);
        const float ring = 12.0f + 9.0f * std::sqrt(static_cast<float>(i / static_cast<std::size_t>(villages)));
        const float angle = rng.range(0.0f, 2.0f * math::kPi);
        render::Instance h;
        h.position = {clamp_to_area(cx + std::cos(angle) * ring), 0.0f, clamp_to_area(cz + std::sin(angle) * ring)};
        h.yaw = std::atan2(cx - h.position.x, cz - h.position.z);
        h.scale = rng.range(0.9f, 1.15f);
        const float shade = rng.range(0.85f, 1.05f);
        h.tint = {shade, shade * rng.range(0.95f, 1.0f), shade * rng.range(0.88f, 1.0f)};
        layout.houses.push_back(h);
    }

    // Forests: clusters with dense cores.
    const int forests = 60;
    std::vector<std::pair<float, float>> centers;
    for (int f = 0; f < forests; ++f) {
        centers.emplace_back(rng.range(-950.0f, 950.0f), rng.range(-950.0f, 950.0f));
    }
    for (std::size_t i = 0; i < trees_target; ++i) {
        const auto& c = centers[i % centers.size()];
        const float r = 140.0f * std::sqrt(rng.unit()) * rng.range(0.4f, 1.0f);
        const float a = rng.range(0.0f, 2.0f * math::kPi);
        render::Instance t;
        t.position = {clamp_to_area(c.first + std::cos(a) * r), 0.0f, clamp_to_area(c.second + std::sin(a) * r)};
        t.yaw = rng.range(0.0f, 2.0f * math::kPi);
        t.scale = rng.range(0.7f, 1.4f);
        const float g = rng.range(0.8f, 1.15f);
        t.tint = {g * rng.range(0.9f, 1.05f), g, g * rng.range(0.85f, 1.0f)};
        layout.trees.push_back(t);
    }

    for (std::size_t i = 0; i < rocks_target; ++i) {
        render::Instance r;
        r.position = {rng.range(-990.0f, 990.0f), 0.0f, rng.range(-990.0f, 990.0f)};
        r.yaw = rng.range(0.0f, 2.0f * math::kPi);
        r.scale = rng.range(0.4f, 2.2f);
        const float s = rng.range(0.85f, 1.1f);
        r.tint = {s, s, s};
        layout.rocks.push_back(r);
    }
    return layout;
}

render::ModelData make_ground_model(float half_size) {
    render::ModelData m;
    constexpr int kCells = 32;
    constexpr float kTile = 8.0f;  // Meters per texture repeat.
    const float cell = 2.0f * half_size / kCells;
    for (int z = 0; z <= kCells; ++z) {
        for (int x = 0; x <= kCells; ++x) {
            const float px = -half_size + static_cast<float>(x) * cell;
            const float pz = -half_size + static_cast<float>(z) * cell;
            m.vertices.push_back({px, 0.0f, pz, 0.0f, 1.0f, 0.0f, px / kTile, pz / kTile});
        }
    }
    for (int z = 0; z < kCells; ++z) {
        for (int x = 0; x < kCells; ++x) {
            const auto i = static_cast<std::uint32_t>(z * (kCells + 1) + x);
            const auto row = static_cast<std::uint32_t>(kCells + 1);
            // Counter-clockwise seen from above (+y).
            for (const std::uint32_t idx : {i, i + row, i + 1, i + 1, i + row, i + row + 1}) {
                m.indices.push_back(idx);
            }
        }
    }
    // Grass: a tileable pattern of small value noise.
    render::ModelTexture tex;
    tex.width = tex.height = 64;
    Random rng(7);
    for (int y = 0; y < 64; ++y) {
        for (int x = 0; x < 64; ++x) {
            const float n = rng.range(-1.0f, 1.0f);
            const float stripe = 0.5f + 0.5f * std::sin(static_cast<float>(x + y) * 0.39f);
            const auto g = static_cast<std::uint8_t>(std::clamp(134.0f + n * 14.0f + stripe * 6.0f, 0.0f, 255.0f));
            const auto r = static_cast<std::uint8_t>(std::clamp(112.0f + n * 12.0f, 0.0f, 255.0f));
            const auto b = static_cast<std::uint8_t>(std::clamp(72.0f + n * 8.0f, 0.0f, 255.0f));
            tex.rgba.insert(tex.rgba.end(), {r, g, b, 255});
        }
    }
    m.textures.push_back(std::move(tex));
    render::ModelMaterial mat;
    mat.texture = 0;
    m.materials.push_back(mat);
    m.primitives.push_back({0, static_cast<std::uint32_t>(m.indices.size()), 0});
    m.bounds_min = {-half_size, 0.0f, -half_size};
    m.bounds_max = {half_size, 0.0f, half_size};
    m.radius = half_size * 1.4143f;
    return m;
}

std::optional<render::ModelData> load_model_file(const std::filesystem::path& file) {
    const std::string name = text::path_to_utf8(file.filename());
    const fs::ReadResult r = fs::read_file(file, render::model_limits::kMaxFileBytes);
    if (r.error != fs::IoError::None) {
        log::warn("models: cannot read {} ({})", name, fs::io_error_name(r.error));
        return std::nullopt;
    }
    render::ModelLoadResult model =
        render::load_glb({reinterpret_cast<const std::uint8_t*>(r.data.data()), r.data.size()});
    if (!model.ok) {
        log::warn("models: {} rejected: {}", name, model.error);
        return std::nullopt;
    }
    return std::move(model.model);
}

bool TestScene::load(render::SceneRenderer& renderer, const std::filesystem::path& models_dir, std::size_t count) {
    const auto load_model = [&](const char* file, render::ModelId& id) {
        const auto model = load_model_file(models_dir / file);
        return model.has_value() && renderer.add_model(*model, id);
    };

    render::ModelId ground = 0;
    if (!renderer.add_model(make_ground_model(kTestSceneHalfSize), ground)) {
        return false;
    }
    placed_.clear();
    placed_.push_back({ground, {render::Instance{}}});

    TestSceneLayout layout = make_test_scene_layout(count, 2026);
    render::ModelId id = 0;
    instances_ = 0;
    if (load_model("tree_pine.glb", id)) {
        instances_ += layout.trees.size();
        placed_.push_back({id, std::move(layout.trees)});
    }
    if (load_model("house_small.glb", id)) {
        instances_ += layout.houses.size();
        placed_.push_back({id, std::move(layout.houses)});
    }
    if (load_model("rock.glb", id)) {
        instances_ += layout.rocks.size();
        placed_.push_back({id, std::move(layout.rocks)});
    }
    for (const Placed& p : placed_) {
        renderer.set_instances(p.model, p.instances);
    }
    visible_ = true;
    loaded_ = true;
    log::info("test scene: {} instances", instances_);
    return true;
}

void TestScene::set_visible(render::SceneRenderer& renderer, bool visible) {
    if (!loaded_ || visible == visible_) {
        return;
    }
    for (const Placed& p : placed_) {
        renderer.set_instances(p.model, visible ? std::span<const render::Instance>(p.instances)
                                                : std::span<const render::Instance>());
    }
    visible_ = visible;
}

}  // namespace sc

// --- Test crowd --------------------------------------------------------------

namespace sc {

namespace {

// sRGB 0xRRGGBB to linear, as the shaders light in linear space.
math::Vec3 linear_rgb(std::uint32_t hex) {
    const auto lin = [](std::uint32_t c) {
        const float v = static_cast<float>(c) / 255.0f;
        return v <= 0.04045f ? v / 12.92f : std::pow((v + 0.055f) / 1.055f, 2.4f);
    };
    return {lin((hex >> 16) & 255u), lin((hex >> 8) & 255u), lin(hex & 255u)};
}

}  // namespace

std::vector<render::Palette> make_villager_palettes() {
    // Slots: skin, hair, top, bottom, shoes, belt, hat, apron.
    constexpr std::uint32_t kOutfits[][6] = {
        {0x8C6A3F, 0x4E5A3A, 0x3B2A1E, 0x2E2016, 0xC9A860, 0xD8CFB8},  // Peasant: browns and greens.
        {0x3F5A7A, 0x5A5048, 0x2E241C, 0x4A3524, 0x6E4A2E, 0xB8A88A},  // Worker: blue and grey.
        {0x8A2E2E, 0x3A3A46, 0x241C16, 0x1E1612, 0x3A5A3A, 0xE0D8C8},  // Townsfolk: red and dark.
    };
    constexpr std::uint32_t kSkins[] = {0xF1C8A4, 0xE0B08A, 0xC68E62, 0x9A6440, 0x6E4428};
    constexpr std::uint32_t kHair[] = {0x2A1E16, 0x5A3A22, 0x8A5A2E, 0xC89A5A, 0x8C8C88};
    std::vector<render::Palette> out;
    for (const auto& outfit : kOutfits) {
        for (const std::uint32_t skin : kSkins) {
            for (const std::uint32_t hair : kHair) {
                render::Palette p;
                p.colors[0] = linear_rgb(skin);
                p.colors[1] = linear_rgb(hair);
                for (std::size_t i = 0; i < 6; ++i) {
                    p.colors[2 + i] = linear_rgb(outfit[i]);
                }
                out.push_back(p);
            }
        }
    }
    return out;
}

std::uint32_t TestCrowd::next_random() {
    // xorshift32; presentation only.
    random_state_ ^= random_state_ << 13;
    random_state_ ^= random_state_ >> 17;
    random_state_ ^= random_state_ << 5;
    return random_state_;
}

math::Vec3 TestCrowd::random_point() {
    const float a = static_cast<float>(next_random() % 10000) / 10000.0f * 2.0f * math::kPi;
    const float r = std::sqrt(static_cast<float>(next_random() % 10000) / 10000.0f) * radius_;
    const float x = center_.x + std::cos(a) * r;
    const float z = center_.z + std::sin(a) * r;
    return {x, ground_ ? ground_(x, z) : 0.0f, z};
}

void TestCrowd::set_area(math::Vec3 center, std::function<float(float, float)> ground) {
    center_ = center;
    ground_ = std::move(ground);
}

bool TestCrowd::load(render::SceneRenderer& renderer, const std::filesystem::path& dir) {
    kinds_.clear();
    const auto accessory = [&](const char* file, render::SkinnedId body, const char* bone, std::uint32_t& bit) {
        const auto model = load_model_file(dir / file);
        return model.has_value() && renderer.add_accessory(*model, body, bone, bit);
    };
    for (const bool female : {false, true}) {
        const auto body = load_model_file(dir / (female ? "human_female.glb" : "human_male.glb"));
        BodyKind kind;
        if (!body || body->clip_index("idle") < 0 || body->clip_index("walk") < 0 ||
            !renderer.add_skinned_model(*body, kind.id)) {
            log::warn("test crowd: body model unavailable");
            continue;
        }
        kind.idle = static_cast<std::uint32_t>(body->clip_index("idle"));
        kind.walk = static_cast<std::uint32_t>(body->clip_index("walk"));
        std::uint32_t bit = 0;
        for (const char* hat : {"hat_straw.glb", "hat_cap.glb"}) {
            if (accessory(hat, kind.id, "head", bit)) {
                kind.hats.push_back(bit);
            }
        }
        if (!female && accessory("beard.glb", kind.id, "head", bit)) {
            kind.beard = bit;
        }
        if (accessory(female ? "apron_female.glb" : "apron_male.glb", kind.id, "hips", bit)) {
            kind.apron = bit;
        }
        kinds_.push_back(kind);
    }
    renderer.set_palettes(make_villager_palettes());
    loaded_ = !kinds_.empty();
    return loaded_;
}

void TestCrowd::spawn(std::size_t count, std::uint32_t seed, float radius) {
    villagers_.clear();
    if (kinds_.empty()) {
        return;
    }
    random_state_ = seed == 0 ? 1u : seed;
    radius_ = radius;
    const auto palettes = static_cast<std::uint32_t>(make_villager_palettes().size());
    for (std::size_t i = 0; i < count; ++i) {
        Villager v;
        v.kind = next_random() % kinds_.size();
        const BodyKind& kind = kinds_[v.kind];
        v.look.body = kind.id;
        v.look.clip = kind.walk;
        v.look.position = random_point();
        v.look.yaw = static_cast<float>(next_random() % 628) / 100.0f;
        v.look.scale = 0.94f + static_cast<float>(next_random() % 12) / 100.0f;
        v.look.palette = next_random() % palettes;
        v.look.time = static_cast<float>(next_random() % 1000) / 1000.0f;
        std::uint32_t mask = 0;
        const std::uint32_t hat = next_random() % 3;  // None, or one of the hats.
        if (hat > 0 && hat <= kind.hats.size()) {
            mask |= 1u << kind.hats[hat - 1];
        }
        if (kind.beard != ~0u && next_random() % 3 == 0) {
            mask |= 1u << kind.beard;
        }
        if (kind.apron != ~0u && next_random() % 4 == 0) {
            mask |= 1u << kind.apron;
        }
        v.look.accessories = mask;
        v.target = random_point();
        v.speed = 1.2f + static_cast<float>(next_random() % 40) / 100.0f;
        v.rest_time = next_random() % 5 == 0 ? static_cast<float>(next_random() % 400) / 100.0f : 0.0f;
        villagers_.push_back(v);
    }
}

std::optional<std::size_t> TestCrowd::pick(math::Vec3 origin, math::Vec3 dir) const {
    constexpr float kHeight = 1.8f;
    constexpr float kRadius = 0.4f;
    std::optional<std::size_t> best;
    float best_t = 1e30f;
    for (std::size_t i = 0; i < villagers_.size(); ++i) {
        const render::CharacterInstance& c = villagers_[i].look;
        const RayHit hit = ray_to_vertical_segment(origin, dir, c.position, kHeight * c.scale);
        if (hit.distance <= kRadius * c.scale && hit.t < best_t) {
            best_t = hit.t;
            best = i;
        }
    }
    return best;
}

void TestCrowd::update(render::SceneRenderer& renderer, float dt) {
    instances_.clear();
    for (std::size_t index = 0; index < villagers_.size(); ++index) {
        Villager& v = villagers_[index];
        const BodyKind& kind = kinds_[v.kind];
        const math::Vec3 to = v.target - v.look.position;
        const float distance = math::length(to);
        if (v.rest_time > 0.0f) {
            v.rest_time -= dt;
            v.look.clip = kind.idle;
            v.look.time += dt;
        } else if (distance < 0.5f) {
            // Arrived: sometimes stop for a while, then pick a new goal.
            v.target = random_point();
            if (next_random() % 4 == 0) {
                v.rest_time = 1.5f + static_cast<float>(next_random() % 400) / 100.0f;
            }
        } else {
            const float step = std::min(distance, v.speed * dt);
            v.look.position += to * (step / distance);
            if (ground_) {
                v.look.position.y = ground_(v.look.position.x, v.look.position.z);
            }
            // Turn smoothly toward the goal; the model's front is +Z.
            const float want = std::atan2(to.x, to.z);
            float diff = want - v.look.yaw;
            while (diff > math::kPi) diff -= 2.0f * math::kPi;
            while (diff < -math::kPi) diff += 2.0f * math::kPi;
            v.look.yaw += diff * std::min(1.0f, dt * 6.0f);
            v.look.clip = kind.walk;
            // Play the walk faster or slower so the feet match the ground.
            v.look.time += dt * (v.speed / kWalkReferenceSpeed);
        }
        if (hidden_ != index) {
            instances_.push_back(v.look);
        }
    }
    renderer.set_characters(instances_);
}

}  // namespace sc
