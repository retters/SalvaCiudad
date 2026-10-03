#include "game/walkers.h"

#include <algorithm>
#include <cmath>

#include "game/camera.h"

namespace sc {

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

bool Walkers::load(render::SceneRenderer& renderer, const std::filesystem::path& core_dir, const sim::Content& content) {
    villagers_.clear();
    return cast_.load(renderer, core_dir, content);
}

void Walkers::clear() {
    villagers_.clear();
}

std::size_t Walkers::add_villager(math::Vec3 at, std::optional<bool> female) {
    if (!cast_.loaded()) {
        return 0;
    }
    // Any character; with a sex, one a race has for it.
    const std::uint32_t bits = next_random();
    const std::size_t races = std::max<std::size_t>(1, cast_.race_count());
    Villager v;
    v.body = female.has_value() ? &cast_.body(next_random() % races, *female, bits)
                                : &cast_.bodies()[next_random() % cast_.bodies().size()];
    v.home = at;
    v.roam = 6.0f;
    v.look.position = {at.x, ground_ ? ground_(at.x, at.z) : at.y, at.z};
    v.look.yaw = static_cast<float>(next_random() % 628) / 100.0f;
    v.look.scale = people::scale_of(sim::village::kAdultAgeYears, bits);
    v.look.palette = people::Cast::palette(*v.body, bits);
    v.motion.time = static_cast<float>(next_random() % 1000) / 1000.0f;
    v.target = random_point(at, v.roam);
    v.speed = 1.2f + static_cast<float>(next_random() % 40) / 100.0f;
    v.rest_time = next_random() % 5 == 0 ? static_cast<float>(next_random() % 400) / 100.0f : 0.0f;
    if (villagers_.size() % 3 == 0) {
        v.load = static_cast<people::Load>(1 + (villagers_.size() / 3) % (people::kLoads - 1));
    }
    people::pose(*v.body, v.motion, v.look, v.load);
    villagers_.push_back(v);
    return villagers_.size() - 1;
}

void Walkers::remove_villager(std::size_t i) {
    if (i < villagers_.size()) {
        villagers_.erase(villagers_.begin() + static_cast<std::ptrdiff_t>(i));
    }
}

float Walkers::height(std::size_t i) const {
    return i < villagers_.size() ? villagers_[i].body->height * villagers_[i].look.scale : 1.8f;
}

Walkers::VillagerInfo Walkers::info(std::size_t i) const {
    VillagerInfo out;
    if (i >= villagers_.size()) {
        return out;
    }
    const Villager& v = villagers_[i];
    out.model = v.body->name;
    out.palette = v.look.palette - v.body->first_palette;
    out.walking = v.motion.act == people::Act::Walk || v.motion.act == people::Act::Run;
    out.speed = v.speed;
    out.scale = v.look.scale;
    out.yaw = v.look.yaw;
    out.target = v.target;
    out.home = v.home;
    return out;
}

std::optional<std::size_t> Walkers::pick(math::Vec3 origin, math::Vec3 dir) const {
    constexpr float kRadius = 0.4f;
    std::optional<std::size_t> best;
    float best_t = 1e30f;
    for (std::size_t i = 0; i < villagers_.size(); ++i) {
        const render::CharacterInstance& c = villagers_[i].look;
        const RayHit hit = ray_to_vertical_segment(origin, dir, c.position, height(i));
        if (hit.distance <= kRadius * c.scale && hit.t < best_t) {
            best_t = hit.t;
            best = i;
        }
    }
    return best;
}

void Walkers::update(render::SceneRenderer& renderer, float dt, std::span<const render::CharacterInstance> others) {
    instances_.assign(others.begin(), others.end());
    for (Villager& v : villagers_) {
        const math::Vec3 to = v.target - v.look.position;
        const float distance = math::length(to);
        if (v.rest_time > 0.0f) {
            v.rest_time -= dt;
            people::advance(*v.body, v.motion, people::Act::Idle, 0.0f, dt, dt, v.load);
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
            // The walk plays faster or slower so the feet match the ground.
            people::advance(*v.body, v.motion, people::Act::Walk, v.speed, dt, dt, v.load);
        }
        people::pose(*v.body, v.motion, v.look, v.load);
        instances_.push_back(v.look);
    }
    renderer.set_characters(instances_);
}

}  // namespace sc
