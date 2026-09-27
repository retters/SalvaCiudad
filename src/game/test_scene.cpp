#include "game/test_scene.h"

#include <algorithm>
#include <cmath>

#include "core/file_io.h"
#include "core/log.h"
#include "core/text.h"

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

bool TestScene::load(render::SceneRenderer& renderer, const std::filesystem::path& models_dir, std::size_t count) {
    const auto load_model = [&](const char* file, render::ModelId& id) {
        const fs::ReadResult r = fs::read_file(models_dir / file, render::model_limits::kMaxFileBytes);
        if (r.error != fs::IoError::None) {
            log::warn("test scene: cannot read {} ({})", file, fs::io_error_name(r.error));
            return false;
        }
        const render::ModelLoadResult model = render::load_glb(
            {reinterpret_cast<const std::uint8_t*>(r.data.data()), r.data.size()});
        if (!model.ok) {
            log::warn("test scene: {} rejected: {}", file, model.error);
            return false;
        }
        return renderer.add_model(model.model, id);
    };

    render::ModelId ground = 0;
    if (!renderer.add_model(make_ground_model(kTestSceneHalfSize), ground)) {
        return false;
    }
    const render::Instance ground_instance{};
    renderer.set_instances(ground, {&ground_instance, 1});

    const TestSceneLayout layout = make_test_scene_layout(count, 2026);
    render::ModelId id = 0;
    instances_ = 0;
    if (load_model("test_tree.glb", id)) {
        renderer.set_instances(id, layout.trees);
        instances_ += layout.trees.size();
    }
    if (load_model("test_house.glb", id)) {
        renderer.set_instances(id, layout.houses);
        instances_ += layout.houses.size();
    }
    if (load_model("test_rock.glb", id)) {
        renderer.set_instances(id, layout.rocks);
        instances_ += layout.rocks.size();
    }
    loaded_ = true;
    log::info("test scene: {} instances", instances_);
    return true;
}

}  // namespace sc
