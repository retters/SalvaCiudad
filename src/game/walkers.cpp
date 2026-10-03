#include "game/walkers.h"

#include <algorithm>
#include <cmath>

#include "core/log.h"
#include "game/builtin_models.h"
#include "game/camera.h"
#include "game/model_file.h"
#include "sim/content.h"

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

std::uint32_t Walkers::next_random() {
    // xorshift32; presentation only.
    random_state_ ^= random_state_ << 13;
    random_state_ ^= random_state_ >> 17;
    random_state_ ^= random_state_ << 5;
    return random_state_;
}

math::Vec3 Walkers::random_point(math::Vec3 center, float radius) {
    const float a = static_cast<float>(next_random() % 10000) / 10000.0f * 2.0f * math::kPi;
    const float r = std::sqrt(static_cast<float>(next_random() % 10000) / 10000.0f) * radius;
    const float x = center.x + std::cos(a) * r;
    const float z = center.z + std::sin(a) * r;
    return {x, ground_ ? ground_(x, z) : 0.0f, z};
}

void Walkers::set_ground(std::function<float(float, float)> ground) {
    ground_ = std::move(ground);
}

bool Walkers::load(render::SceneRenderer& renderer, const std::filesystem::path& core_dir,
                     const std::vector<std::string>& bodies) {
    kinds_.clear();
    const auto accessory = [&](std::string_view file, render::SkinnedId body, const char* bone, std::uint32_t& bit) {
        const auto model = load_model_file(core_dir / file);
        return model.has_value() && renderer.add_accessory(*model, body, bone, bit);
    };
    for (const std::string& prefix : bodies) {
    for (const bool female : {false, true}) {
        const auto body = load_model_file(core_dir / sim::race_body_file(prefix, female));
        BodyKind kind;
        kind.female = female;
        kind.body = prefix;
        if (!body || body->clip_index("idle") < 0 || body->clip_index("walk") < 0 ||
            !renderer.add_skinned_model(*body, kind.id)) {
            log::warn("villagers: body model unavailable: {}", prefix);
            continue;
        }
        kind.idle = static_cast<std::uint32_t>(body->clip_index("idle"));
        kind.walk = static_cast<std::uint32_t>(body->clip_index("walk"));
        std::uint32_t bit = 0;
        for (const std::string_view hat : builtin_models::kHats) {
            if (accessory(hat, kind.id, builtin_models::kHeadBone, bit)) {
                kind.hats.push_back(bit);
            }
        }
        if (!female && accessory(builtin_models::kBeard, kind.id, builtin_models::kHeadBone, bit)) {
            kind.beard = bit;
        }
        if (accessory(female ? builtin_models::kApronFemale : builtin_models::kApronMale, kind.id,
                      builtin_models::kHipsBone, bit)) {
            kind.apron = bit;
        }
        kinds_.push_back(kind);
    }
    }
    renderer.set_palettes(make_villager_palettes());
    loaded_ = !kinds_.empty();
    return loaded_;
}

Walkers::Villager Walkers::make_villager(std::size_t kind_index, math::Vec3 home, float roam) {
    const auto palettes = static_cast<std::uint32_t>(make_villager_palettes().size());
    Villager v;
    v.kind = kind_index;
    v.home = home;
    v.roam = roam;
    const BodyKind& kind = kinds_[v.kind];
    v.look.body = kind.id;
    v.look.clip = kind.walk;
    v.look.position = random_point(home, roam);
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
    v.target = random_point(home, roam);
    v.speed = 1.2f + static_cast<float>(next_random() % 40) / 100.0f;
    v.rest_time = next_random() % 5 == 0 ? static_cast<float>(next_random() % 400) / 100.0f : 0.0f;
    return v;
}

void Walkers::clear() {
    villagers_.clear();
    hidden_.reset();
}

std::size_t Walkers::add_villager(math::Vec3 at, std::optional<bool> female) {
    if (kinds_.empty()) {
        return 0;
    }
    std::size_t kind = next_random() % kinds_.size();
    if (female.has_value()) {
        for (std::size_t k = 0; k < kinds_.size(); ++k) {
            if (kinds_[k].female == *female) {
                kind = k;
            }
        }
    }
    Villager v = make_villager(kind, at, 6.0f);
    v.look.position = {at.x, ground_ ? ground_(at.x, at.z) : at.y, at.z};
    villagers_.push_back(v);
    return villagers_.size() - 1;
}

void Walkers::remove_villager(std::size_t i) {
    if (i < villagers_.size()) {
        villagers_.erase(villagers_.begin() + static_cast<std::ptrdiff_t>(i));
        hidden_.reset();
    }
}

Walkers::VillagerInfo Walkers::info(std::size_t i) const {
    VillagerInfo out;
    if (i >= villagers_.size()) {
        return out;
    }
    const Villager& v = villagers_[i];
    const BodyKind& kind = kinds_[v.kind];
    out.female = kind.female;
    out.palette = v.look.palette;
    out.walking = v.rest_time <= 0.0f && v.look.clip == kind.walk;
    out.speed = v.speed;
    out.scale = v.look.scale;
    out.yaw = v.look.yaw;
    out.target = v.target;
    out.home = v.home;
    for (const std::uint32_t bit : kind.hats) {
        out.hat = out.hat || ((v.look.accessories >> bit) & 1u) != 0;
    }
    out.beard = kind.beard != ~0u && ((v.look.accessories >> kind.beard) & 1u) != 0;
    out.apron = kind.apron != ~0u && ((v.look.accessories >> kind.apron) & 1u) != 0;
    return out;
}

std::optional<std::size_t> Walkers::pick(math::Vec3 origin, math::Vec3 dir) const {
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

void Walkers::update(render::SceneRenderer& renderer, float dt, std::span<const render::CharacterInstance> others) {
    instances_.assign(others.begin(), others.end());
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
            v.target = random_point(v.home, v.roam);
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
