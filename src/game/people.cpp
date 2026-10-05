#include "game/people.h"

#include <algorithm>
#include <cmath>

#include "core/log.h"
#include "game/builtin_models.h"
#include "game/model_file.h"

namespace sc::people {

namespace {

// sRGB 0xRRGGBB to linear, as the shaders light in linear space.
math::Vec3 linear_rgb(std::uint32_t hex) {
    const auto lin = [](std::uint32_t c) {
        const float v = static_cast<float>(c) / 255.0f;
        return v <= 0.04045f ? v / 12.92f : std::pow((v + 0.055f) / 1.055f, 2.4f);
    };
    return {lin((hex >> 16) & 255u), lin((hex >> 8) & 255u), lin(hex & 255u)};
}

// The clothes the villagers come in, besides each character's own: the
// main garment and the second one (trousers, a sash).
constexpr std::uint32_t kOutfits[][2] = {
    {0x3559C0, 0x4B4450},  // Blue.
    {0x8E3B2C, 0x443C3A},  // Russet.
    {0x3F7A4A, 0x4A4038},  // Green.
    {0x8C6A3F, 0x4E5A3A},  // Brown over olive.
    {0x6A4A8A, 0x3A3A46},  // Purple.
    {0xB8A070, 0x5A4A3A},  // Undyed cloth.
    {0x5A6A72, 0x3A3530},  // Slate.
};

// Where a tool goes in the body's bind pose: its grip at the middle of the
// bone that holds it, its long axis (+Y in the file) along the hand's
// forward direction at rest (+Z, the model's front), turned `roll` about
// that axis. The same rule as art/blender/study_preview.py.
math::Mat4 tool_placement(const render::ModelData& body, int joint, const render::ModelData& tool, float roll_degrees,
                          bool upright = false) {
    const float length = static_cast<std::size_t>(joint) < body.joint_length.size()
                             ? body.joint_length[static_cast<std::size_t>(joint)]
                             : 0.0f;
    const math::Vec3 middle =
        body.joint_rest[static_cast<std::size_t>(joint)].transform_point({0.0f, length * 0.5f, 0.0f});
    // A quarter turn about X, as a quaternion; none for what is held upright (+Y in the file is up already).
    const float half = upright ? 0.0f : math::kPi * 0.25f;
    const float roll = roll_degrees * math::kPi / 360.0f;
    // The tools are made for a person 1.8 m tall: smaller hands hold smaller ones.
    const float size = std::clamp(body.bounds_max.y / 1.8f, 0.7f, 1.15f);
    return math::translation(middle) * math::rotation_quat(std::sin(half), 0.0f, 0.0f, std::cos(half)) *
           math::rotation_quat(0.0f, std::sin(roll), 0.0f, std::cos(roll)) * math::scaling({size, size, size}) *
           math::translation(-tool.grip);
}

// Phase 116. Where a shield goes in the body's bind pose: flat against the
// outer side of the forearm that carries it, its middle (its grip) at the
// middle of the bone and its face looking away from the body. In its file a
// shield stands in the XY plane and looks along +Z.
math::Mat4 shield_placement(const render::ModelData& body, int joint, const render::ModelData& shield) {
    const float length = static_cast<std::size_t>(joint) < body.joint_length.size()
                             ? body.joint_length[static_cast<std::size_t>(joint)]
                             : 0.0f;
    const math::Vec3 middle =
        body.joint_rest[static_cast<std::size_t>(joint)].transform_point({0.0f, length * 0.5f, 0.0f});
    const float size = std::clamp(body.bounds_max.y / 1.8f, 0.7f, 1.15f) * 0.8f;
    // The arm is on its side of the body: away from it is farther along X.
    const float side = middle.x < 0.0f ? -1.0f : 1.0f;
    const float half = side * math::kPi * 0.25f;  // A quarter turn about Y: its face looks along X.
    return math::translation(middle + math::Vec3{side * 0.075f * size, 0.0f, 0.0f}) *
           math::rotation_quat(0.0f, std::sin(half), 0.0f, std::cos(half)) * math::scaling({size, size, size}) *
           math::translation(-shield.grip);
}

// Where a load goes in the body's bind pose (art: docs/ARTE.md): its grip
// on the chest bone's start, pushed out a little behind the back or in
// front of the chest; smaller on a smaller body.
math::Mat4 load_placement(const render::ModelData& body, int joint, const render::ModelData& load, bool arms) {
    const math::Vec3 chest = body.joint_rest[static_cast<std::size_t>(joint)].transform_point({0.0f, 0.0f, 0.0f});
    const float size = std::clamp(body.bounds_max.y / 1.8f, 0.7f, 1.15f);
    // The model's front is +Z: the back is behind.
    const math::Vec3 out{0.0f, 0.0f, (arms ? 0.115f : -0.115f) * size};
    return math::translation(chest + out) * math::scaling({size, size, size}) * math::translation(-load.grip);
}

}  // namespace

Load load_for(const sim::ResourceDef& resource, std::int32_t amount) {
    if (amount <= 0) {
        return Load::None;
    }
    const std::int32_t trip = resource.carry > 0 ? resource.carry : std::max(1, sim::village::kCarry / std::max(1, resource.weight));
    const bool back = amount * 2 > trip;
    switch (resource.load) {
        case sim::LoadKind::Logs: return back ? Load::LogsBack : Load::LogsArms;
        case sim::LoadKind::Stone: return back ? Load::StoneBack : Load::StoneArms;
        case sim::LoadKind::Sack: return back ? Load::SackBack : Load::CrateArms;  // (No sack to hold in the arms.)
        case sim::LoadKind::Basket: return back ? Load::BasketBack : Load::BasketArms;
        default: return back ? Load::CrateBack : Load::CrateArms;
    }
}

Load load_of(const sim::Content& content, const sim::Villager& v) {
    if (v.carrying.amount <= 0 || v.carrying.resource >= content.resources.size()) {
        return Load::None;
    }
    return load_for(content.resources[v.carrying.resource], v.carrying.amount);
}

void advance(const Body& body, Motion& m, Act wanted, float speed, float game_dt, float rest_dt, Load load) {
    const auto index = [](Act a) { return static_cast<std::size_t>(a); };
    const bool arms = in_arms(load);
    if (arms && (wanted == Act::Walk || wanted == Act::Run)) {
        // Holding something: the same stride, with the arms around it.
        const float length = body.length[index(Act::CarryWalk)];
        if (m.act == Act::Walk) {
            m.time = m.time / body.length[index(Act::Walk)] * length;
        } else if (m.act != Act::CarryWalk) {
            m.time = 0.0f;
        }
        m.act = Act::CarryWalk;
        m.time = std::fmod(m.time + game_dt * speed / body.walk_speed, length);
        return;
    }
    if (arms && wanted == Act::Idle) {
        if (m.act != Act::CarryIdle) {
            m.act = Act::CarryIdle;
            m.time = 0.0f;
        }
        m.time = std::fmod(m.time + rest_dt, body.length[index(Act::CarryIdle)]);
        return;
    }
    if (wanted == Act::Walk || wanted == Act::Run) {
        const Act gait = wanted == Act::Run || speed > body.walk_speed * kRunAbove ? Act::Run : Act::Walk;
        const float length = body.length[index(gait)];
        if (m.act == Act::CarryWalk) {
            m.time = gait == Act::Walk ? m.time / body.length[index(Act::CarryWalk)] * length : 0.0f;
            m.act = gait;
        }
        if (m.act == Act::Walk || m.act == Act::Run) {
            if (m.act != gait) {  // The same point of the stride in the other gait.
                m.time = m.time / body.length[index(m.act)] * length;
            }
        } else {
            m.time = 0.0f;
        }
        m.act = gait;
        const float clip_speed = gait == Act::Run ? body.run_speed : body.walk_speed;
        m.time = std::fmod(m.time + game_dt * speed / clip_speed, length);
        return;
    }
    // Fishing starts with the cast, played once.
    if (wanted == Act::Fish && m.act != Act::Fish && m.act != Act::FishCast) {
        m.act = Act::FishCast;
        m.time = 0.0f;
        return;
    }
    if (wanted == Act::Fish && m.act == Act::FishCast) {
        m.time += rest_dt;
        if (m.time >= body.length[index(Act::FishCast)]) {
            m.act = Act::Fish;
            m.time = 0.0f;
        }
        return;
    }
    if (m.act != wanted) {
        // Keep an idle's phase (it was given at random), start the rest over.
        m.time = wanted == Act::Idle && (m.act == Act::Walk || m.act == Act::Run) ? m.time : 0.0f;
        m.act = wanted;
    }
    m.time = std::fmod(m.time + rest_dt, body.length[index(m.act)]);
}

void pose(const Body& body, const Motion& m, render::CharacterInstance& c, Load load) {
    const auto a = static_cast<std::size_t>(m.act);
    c.body = body.id;
    c.clip = body.clip[a];
    // A clip played once holds its last pose; the others loop.
    c.time = std::min(m.time, std::max(0.0f, body.length[a] - 1.0f / 60.0f));
    c.accessories = body.tools[a];
    // What it carries, unless its hands are busy with a tool.
    c.near_only = body.loads[static_cast<std::size_t>(load)];
    if (c.near_only != 0 && (c.accessories == 0 || !in_arms(load))) {
        c.accessories |= c.near_only;
    } else {
        c.near_only = 0;
    }
}

std::uint32_t soldier_gear(const Body& body, const sim::UnitDef& unit) {
    const auto bit = [&](Gear g) { return body.gear[static_cast<std::size_t>(g)]; };
    std::uint32_t weapon = 0;
    switch (unit.weapon) {
        case sim::UnitWeapon::Club: weapon = bit(Gear::Club); break;
        case sim::UnitWeapon::Spear: weapon = bit(Gear::Spear); break;
        case sim::UnitWeapon::Bow: weapon = bit(Gear::Bow); break;
        case sim::UnitWeapon::None:
        case sim::UnitWeapon::Count: break;
    }
    if (weapon == 0) {
        return 0;
    }
    return weapon | (unit.shield ? bit(Gear::Shield) : 0u);
}

Act soldier_attack(const sim::UnitDef& unit) {
    return unit.weapon == sim::UnitWeapon::Bow ? Act::Shoot : Act::Chop;
}

Act act_of(const sim::Game& game, const sim::Villager& v, bool moving) {
    using sim::Task;
    if (moving) {
        const bool hurry = v.task == Task::Flee || v.task == Task::GoFire || v.task == Task::GoFight ||
                           (v.owner < game.player_count() && game.player(v.owner).alarm);
        return hurry ? Act::Run : Act::Walk;
    }
    switch (v.task) {
        case Task::Gather: {
            const auto& features = game.map().features;
            const bool tree = v.node > 0 && v.node - 1 < features.size() && features[v.node - 1].type == sim::FeatureType::Tree;
            return tree ? Act::Chop : Act::Work;
        }
        case Task::Fight: return Act::Chop;
        case Task::Hunt: return Act::Shoot;
        case Task::Fish: return Act::Fish;
        case Task::Build:
        case Task::Produce:
        case Task::Farm:
        case Task::FightFire: return Act::Work;
        default: return Act::Idle;
    }
}

float scale_of(std::int32_t age_years, std::uint32_t appearance) {
    if (age_years < sim::village::kAdultAgeYears) {
        return 0.55f + 0.4f * static_cast<float>(std::max(0, age_years)) / static_cast<float>(sim::village::kAdultAgeYears);
    }
    return 0.94f + static_cast<float>((appearance >> 3) % 12u) / 100.0f;
}

std::vector<render::Palette> make_palettes(const render::ModelData& model, std::span<const std::uint32_t> skins,
                                           std::span<const std::uint32_t> hairs, std::uint32_t& skin_count,
                                           std::uint32_t& hair_count, std::uint32_t& outfit_count) {
    // The model's own colors: a slot it does not use stays white.
    math::Vec3 own[render::kPaletteSlots];
    bool used[render::kPaletteSlots] = {};
    for (std::size_t s = 0; s < render::kPaletteSlots; ++s) {
        own[s] = {1.0f, 1.0f, 1.0f};
        used[s] = render::palette_reference(model, s, own[s]);
    }
    // Its own first, then the given ones, if it has what to recolor.
    std::vector<math::Vec3> skin_colors{own[kSkinSlot]}, hair_colors{own[kHairSlot]};
    for (std::size_t i = 0; i < skins.size() && used[kSkinSlot]; ++i) {
        skin_colors.push_back(linear_rgb(skins[i]));
    }
    for (std::size_t i = 0; i < hairs.size() && used[kHairSlot]; ++i) {
        hair_colors.push_back(linear_rgb(hairs[i]));
    }
    std::vector<std::pair<math::Vec3, math::Vec3>> outfits{{own[kTopSlot], own[kBottomSlot]}};
    if (used[kTopSlot] || used[kBottomSlot]) {
        for (const auto& o : kOutfits) {
            outfits.emplace_back(linear_rgb(o[0]), linear_rgb(o[1]));
        }
    }
    skin_count = static_cast<std::uint32_t>(skin_colors.size());
    hair_count = static_cast<std::uint32_t>(hair_colors.size());
    outfit_count = static_cast<std::uint32_t>(outfits.size());
    std::vector<render::Palette> out;
    out.reserve(skin_colors.size() * hair_colors.size() * outfits.size());
    for (const math::Vec3& skin : skin_colors) {
        for (const math::Vec3& hair : hair_colors) {
            for (const auto& [top, bottom] : outfits) {
                render::Palette p;
                for (std::size_t s = 0; s < render::kPaletteSlots; ++s) {
                    p.colors[s] = own[s];
                }
                p.colors[kSkinSlot] = skin;
                p.colors[kHairSlot] = hair;
                p.colors[kTopSlot] = top;
                p.colors[kBottomSlot] = bottom;
                out.push_back(p);
            }
        }
    }
    return out;
}

bool load_body(render::SceneRenderer& renderer, const std::filesystem::path& core_dir, const render::ModelData& model,
               const render::ModelData* far, Body& body) {
    const int idle = model.clip_index("idle");
    if (idle < 0 || model.clip_index("walk") < 0 || !renderer.add_skinned_model(model, body.id)) {
        return false;
    }
    body.height = std::max(0.5f, model.bounds_max.y);
    if (far != nullptr && !renderer.set_far_body(*far, body.id)) {
        log::warn("people: a far version does not fit its character");
    }
    for (std::size_t a = 0; a < kActs; ++a) {
        const int found = model.clip_index(kActClips[a]);
        const bool walks = a == static_cast<std::size_t>(Act::Run) || a == static_cast<std::size_t>(Act::CarryWalk);
        const int clip = found >= 0 ? found : (walks ? model.clip_index("walk") : idle);
        body.clip[a] = static_cast<std::uint32_t>(clip);
        body.length[a] = std::max(0.05f, renderer.clip_duration(body.id, body.clip[a]));
        body.tools[a] = 0;
        const render::ModelClip& c = model.clips[static_cast<std::size_t>(clip)];
        if (a == static_cast<std::size_t>(Act::Walk) && c.speed > 0.0f) {
            body.walk_speed = c.speed;
        }
        if (a == static_cast<std::size_t>(Act::Run)) {
            body.run_speed = c.speed > 0.0f ? c.speed : body.walk_speed;
        }
    }
    // The tools: one accessory per kind and bone, shared by the clips that name it.
    std::vector<std::pair<std::string, std::uint32_t>> loaded;
    for (std::size_t a = 0; a < kActs; ++a) {
        const std::string& prop = model.clips[body.clip[a]].prop;
        if (prop.empty()) {
            continue;
        }
        const auto known = std::find_if(loaded.begin(), loaded.end(), [&](const auto& l) { return l.first == prop; });
        if (known != loaded.end()) {
            body.tools[a] = 1u << known->second;
            continue;
        }
        const std::size_t colon = prop.find(':');
        const std::string_view kind = std::string_view(prop).substr(0, colon);
        const std::string bone = colon == std::string::npos ? std::string() : prop.substr(colon + 1);
        const int joint = model.joint_index(bone);
        const auto tool = std::find_if(std::begin(builtin_models::kTools), std::end(builtin_models::kTools),
                                       [&](const builtin_models::Tool& t) { return t.kind == kind; });
        if (joint < 0 || tool == std::end(builtin_models::kTools)) {
            continue;
        }
        const auto data = load_model_file(core_dir / tool->path);
        std::uint32_t bit = 0;
        if (data.has_value() && !data->skinned() &&
            renderer.add_accessory(*data, body.id, bone, tool_placement(model, joint, *data, tool->roll), bit)) {
            body.tools[a] = 1u << bit;
            loaded.emplace_back(prop, bit);
        }
    }
    // Phase 116: what the soldiers hold. A thing some clip already put in the same hand is the same accessory.
    struct GearSpec {
        Gear gear;
        std::string_view kind;
        std::string_view bone;
    };
    static constexpr GearSpec kGearSpecs[] = {{Gear::Club, "club", "hand.R"},
                                              {Gear::Spear, "spear", "hand.R"},
                                              {Gear::Bow, "bow", "hand.L"},
                                              {Gear::Shield, "shield", "lower_arm.L"}};
    body.gear.fill(0);
    for (const GearSpec& g : kGearSpecs) {
        const std::string prop = std::string(g.kind) + ":" + std::string(g.bone);
        const auto known = std::find_if(loaded.begin(), loaded.end(), [&](const auto& l) { return l.first == prop; });
        if (known != loaded.end()) {
            body.gear[static_cast<std::size_t>(g.gear)] = 1u << known->second;
            continue;
        }
        const int joint = model.joint_index(g.bone);
        const auto tool = std::find_if(std::begin(builtin_models::kTools), std::end(builtin_models::kTools),
                                       [&](const builtin_models::Tool& t) { return t.kind == g.kind; });
        if (joint < 0 || tool == std::end(builtin_models::kTools)) {
            continue;
        }
        const auto data = load_model_file(core_dir / tool->path);
        std::uint32_t bit = 0;
        if (data.has_value() && !data->skinned() &&
            renderer.add_accessory(*data, body.id, g.bone,
                                   g.gear == Gear::Shield ? shield_placement(model, joint, *data)
                                                          : tool_placement(model, joint, *data, tool->roll, tool->upright),
                                   bit)) {
            body.gear[static_cast<std::size_t>(g.gear)] = 1u << bit;
            loaded.emplace_back(prop, bit);
        }
    }
    // The loads (phase 67), pinned to the chest.
    body.loads.fill(0);
    if (const int chest = model.joint_index("chest"); chest >= 0) {
        for (std::size_t k = 0; k < std::size(builtin_models::kLoads) && k + 1 < kLoads; ++k) {
            const auto data = load_model_file(core_dir / builtin_models::kLoads[k]);
            std::uint32_t bit = 0;
            const bool arms = in_arms(static_cast<Load>(k + 1));
            if (data.has_value() && !data->skinned() &&
                renderer.add_accessory(*data, body.id, "chest", load_placement(model, chest, *data, arms), bit)) {
                body.loads[k + 1] = 1u << bit;
            }
        }
    }
    return true;
}

bool Cast::load(render::SceneRenderer& renderer, const std::filesystem::path& core_dir, const sim::Content& content) {
    bodies_.clear();
    races_.clear();
    palettes_.clear();
    for (const sim::RaceDef& race : content.races) {
        RaceBodies mine;
        for (const bool female : {false, true}) {
            for (const std::string& name : female ? race.bodies_female : race.bodies_male) {
                auto known = std::find_if(bodies_.begin(), bodies_.end(), [&](const Body& b) { return b.name == name; });
                if (known == bodies_.end()) {
                    const auto model = load_model_file(core_dir / sim::race_body_file(name));
                    Body body;
                    body.name = name;
                    // Its far version, if it has one.
                    const std::filesystem::path far_file = core_dir / sim::race_body_file(name + "_far");
                    std::error_code ec;
                    const auto far = std::filesystem::is_regular_file(far_file, ec) ? load_model_file(far_file) : std::nullopt;
                    if (!model.has_value() || !load_body(renderer, core_dir, *model, far.has_value() ? &*far : nullptr, body)) {
                        log::warn("people: character model unavailable: {}", name);
                        continue;
                    }
                    // Its palettes go by the first race that uses it.
                    body.first_palette = static_cast<std::uint32_t>(palettes_.size());
                    const std::vector<render::Palette> own =
                        make_palettes(*model, race.skins, race.hairs, body.skins, body.hairs, body.outfits);
                    palettes_.insert(palettes_.end(), own.begin(), own.end());
                    bodies_.push_back(std::move(body));
                    known = bodies_.end() - 1;
                }
                (female ? mine.female : mine.male).push_back(static_cast<std::uint32_t>(known - bodies_.begin()));
                if (name == (female ? race.soldier_female : race.soldier_male)) {
                    (female ? mine.soldier_female : mine.soldier_male) = static_cast<std::uint32_t>(known - bodies_.begin());
                }
            }
        }
        races_.push_back(std::move(mine));
    }
    // Pale and all of one color, whatever the body.
    render::Palette ghost;
    for (math::Vec3& c : ghost.colors) {
        c = {0.62f, 0.72f, 0.85f};
    }
    ghost_palette_ = static_cast<std::uint32_t>(palettes_.size());
    palettes_.push_back(ghost);
    renderer.set_palettes(palettes_);
    return loaded();
}

const Body& Cast::body(std::size_t race, bool female, std::uint32_t appearance) const {
    static const std::vector<std::uint32_t> kNone;
    const auto pick = [&](std::size_t r) -> const std::vector<std::uint32_t>& {
        if (r >= races_.size()) {
            return kNone;
        }
        const RaceBodies& b = races_[r];
        // A people with one model for everybody has it under either sex.
        return female ? (b.female.empty() ? b.male : b.female) : (b.male.empty() ? b.female : b.male);
    };
    const std::vector<std::uint32_t>* list = &pick(race);
    for (std::size_t r = 0; list->empty() && r < races_.size(); ++r) {
        list = &pick(r);  // A race without models borrows the first that has any.
    }
    if (list->empty()) {
        return bodies_.front();
    }
    return bodies_[(*list)[(appearance >> 7) % list->size()]];
}

const Body& Cast::soldier_body(std::size_t race, bool female, std::uint32_t appearance) const {
    if (race < races_.size()) {
        const RaceBodies& b = races_[race];
        // (A people with one body for both sexes names its soldier under either.)
        const std::uint32_t named = female ? (b.soldier_female != kNoBody ? b.soldier_female : b.soldier_male)
                                           : (b.soldier_male != kNoBody ? b.soldier_male : b.soldier_female);
        const bool has_own = female ? !b.female.empty() : !b.male.empty();
        const std::uint32_t own = female ? b.soldier_female : b.soldier_male;
        const std::uint32_t pick = has_own ? own : named;
        if (pick != kNoBody && pick < bodies_.size()) {
            return bodies_[pick];
        }
    }
    return body(race, female, appearance);
}

const Body& Cast::any_body(std::uint32_t seed) const {
    return body(0, false, seed * 2654435761u);
}

std::uint32_t Cast::palette(const Body& body, std::uint32_t appearance) {
    const std::uint32_t h = appearance * 2654435761u;
    const std::uint32_t skin = h % body.skins;
    const std::uint32_t hair = (h >> 9) % body.hairs;
    const std::uint32_t outfit = (h >> 18) % body.outfits;
    return body.first_palette + (skin * body.hairs + hair) * body.outfits + outfit;
}

const Body* Cast::find(std::string_view name) const {
    const auto it = std::find_if(bodies_.begin(), bodies_.end(), [&](const Body& b) { return b.name == name; });
    return it == bodies_.end() ? nullptr : &*it;
}

}  // namespace sc::people
