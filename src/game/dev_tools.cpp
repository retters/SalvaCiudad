#include "game/dev_tools.h"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <numbers>

#include <imgui.h>

#include "game/camera.h"
#include "game/game_session.h"
#include "game/map_scene.h"
#include "game/terrain_names.h"
#include "game/test_scene.h"
#include "i18n/translator.h"
#include "render/scene_renderer.h"

namespace sc {

using i18n::tr;

namespace {

constexpr std::int32_t kIndexCell = 16;  // Meters per picking cell.
constexpr float kMaxPick = 3000.0f;      // Farthest pick along the ray, meters.

float to_float(sim::Fixed f) {
    return static_cast<float>(f.raw()) / 65536.0f;
}

sim::Fixed to_fixed(float v) {
    return sim::Fixed::from_raw(static_cast<std::int32_t>(std::lround(static_cast<double>(v) * 65536.0)));
}

const char* feature_key(sim::FeatureType t) {
    switch (t) {
        case sim::FeatureType::Stone: return "feature.stone";
        case sim::FeatureType::IronOre: return "feature.ironOre";
        case sim::FeatureType::BerryBush: return "feature.berryBush";
        case sim::FeatureType::Herbs: return "feature.herbs";
        default: return "feature.tree";
    }
}

// Rough height of a non-tree feature at scale 1, meters.
float feature_base_height(sim::FeatureType t) {
    switch (t) {
        case sim::FeatureType::Stone: return 1.0f;
        case sim::FeatureType::IronOre: return 1.1f;
        case sim::FeatureType::BerryBush: return 0.9f;
        case sim::FeatureType::Herbs: return 0.6f;
        default: return 1.0f;
    }
}

std::string species_name(const sim::Content* content, std::size_t s) {
    if (content == nullptr || s >= content->flora.species.size()) {
        return "?";
    }
    return tr(content->flora.species[s].name_key);
}

std::string size_name(std::size_t s) {
    return tr(std::string("treeSize.") + sim::size_info(static_cast<sim::TreeSize>(s)).id);
}

// Label with a hidden, stable id, so the text can be translated.
std::string label(std::string_view key, std::string_view id) {
    return tr(key) + "###" + std::string(id);
}

}  // namespace

std::string fold_for_search(std::string_view text) {
    std::string out;
    out.reserve(text.size());
    for (std::size_t i = 0; i < text.size(); ++i) {
        const auto c = static_cast<unsigned char>(text[i]);
        if (c == 0xC3 && i + 1 < text.size()) {
            // Latin-1 letters with accents, as UTF-8: fold to plain ASCII.
            const auto d = static_cast<unsigned char>(text[i + 1]);
            static constexpr const char* kFold = "aaaaaaaceeeeiiiidnooooo/ouuuuyty";
            const unsigned low = (d & 0x1Fu);
            if (d >= 0x80 && d <= 0xBF) {
                out += kFold[low];
                ++i;
                continue;
            }
        }
        out += static_cast<char>(c < 0x80 ? std::tolower(c) : c);
    }
    return out;
}

void DevTools::reset() {
    selected_ = {};
    hovered_ = {};
    indexed_map_ = nullptr;
    indexed_count_ = 0;
    terrain_names_.reset();
    index_.clear();
    list_.clear();
    list_dirty_ = true;
}

// --- Objects -----------------------------------------------------------------

bool DevTools::valid(const DevContext& ctx, DevObject o) const {
    switch (o.kind) {
        case DevObject::Kind::Feature: return ctx.map != nullptr && o.index < ctx.map->features.size();
        case DevObject::Kind::House: return ctx.map != nullptr && ctx.scene != nullptr && o.index < ctx.scene->houses().size();
        case DevObject::Kind::Villager: return ctx.crowd != nullptr && o.index < ctx.crowd->size();
        case DevObject::Kind::None: break;
    }
    return false;
}

math::Vec3 DevTools::position(const DevContext& ctx, DevObject o) const {
    switch (o.kind) {
        case DevObject::Kind::Feature: {
            const sim::MapFeature& f = ctx.map->features[o.index];
            return {to_float(f.x), to_float(ctx.map->height_at(f.x, f.z)), to_float(f.z)};
        }
        case DevObject::Kind::House: return ctx.scene->houses()[o.index].position;
        case DevObject::Kind::Villager: return ctx.crowd->position(o.index);
        case DevObject::Kind::None: break;
    }
    return {};
}

float DevTools::height(const DevContext& ctx, DevObject o) const {
    switch (o.kind) {
        case DevObject::Kind::Feature: {
            const sim::MapFeature& f = ctx.map->features[o.index];
            if (f.type == sim::FeatureType::Tree) {
                return static_cast<float>(sim::MapData::tree_height_cm(f)) / 100.0f;
            }
            return feature_base_height(f.type) * to_float(f.scale);
        }
        case DevObject::Kind::House: return 5.2f;
        case DevObject::Kind::Villager: return 1.8f * ctx.crowd->scale(o.index);
        case DevObject::Kind::None: break;
    }
    return 0.0f;
}

std::string DevTools::name(const DevContext& ctx, DevObject o) const {
    switch (o.kind) {
        case DevObject::Kind::Feature: {
            const sim::MapFeature& f = ctx.map->features[o.index];
            if (f.type == sim::FeatureType::Tree) {
                return tr("dev.treeName", species_name(ctx.content, f.species), size_name(f.size));
            }
            return tr(feature_key(f.type));
        }
        case DevObject::Kind::House: return tr("dev.object.house");
        case DevObject::Kind::Villager:
            return tr(ctx.crowd->info(o.index).female ? "dev.object.villagerFemale" : "dev.object.villagerMale");
        case DevObject::Kind::None: break;
    }
    return {};
}

std::optional<math::Vec3> DevTools::selected_marker(const DevContext& ctx) const {
    if (!visible_ || !valid(ctx, selected_)) {
        return std::nullopt;
    }
    return position(ctx, selected_) + math::Vec3{0.0f, height(ctx, selected_) + 0.5f, 0.0f};
}

std::optional<math::Vec3> DevTools::hovered_marker(const DevContext& ctx) const {
    if (!visible_ || !valid(ctx, hovered_) || hovered_ == selected_) {
        return std::nullopt;
    }
    return position(ctx, hovered_) + math::Vec3{0.0f, height(ctx, hovered_) + 0.5f, 0.0f};
}

// --- Picking -----------------------------------------------------------------

void DevTools::build_index(const sim::MapData& map) {
    index_side_ = (map.size + kIndexCell - 1) / kIndexCell;
    index_.assign(static_cast<std::size_t>(index_side_) * static_cast<std::size_t>(index_side_), {});
    for (std::size_t i = 0; i < map.features.size(); ++i) {
        const sim::MapFeature& f = map.features[i];
        const std::int32_t cx = std::clamp(f.x.floor_int() / kIndexCell, 0, index_side_ - 1);
        const std::int32_t cz = std::clamp(f.z.floor_int() / kIndexCell, 0, index_side_ - 1);
        index_[static_cast<std::size_t>(cz * index_side_ + cx)].push_back(static_cast<std::uint32_t>(i));
    }
    indexed_map_ = &map;
    indexed_count_ = map.features.size();
}

std::optional<float> DevTools::ground_hit(const DevContext& ctx) const {
    if (ctx.map == nullptr || !ctx.ray_valid) {
        return std::nullopt;
    }
    // March along the ray, then refine between the last two steps.
    constexpr float kStep = 2.0f;
    float prev = 0.0f;
    for (float t = kStep; t < kMaxPick; t += kStep) {
        const math::Vec3 p = ctx.ray_origin + ctx.ray_dir * t;
        if (p.y <= map_surface_height(*ctx.map, p.x, p.z)) {
            float lo = prev;
            float hi = t;
            for (int i = 0; i < 12; ++i) {
                const float mid = (lo + hi) * 0.5f;
                const math::Vec3 q = ctx.ray_origin + ctx.ray_dir * mid;
                (q.y <= map_surface_height(*ctx.map, q.x, q.z) ? hi : lo) = mid;
            }
            return hi;
        }
        prev = t;
    }
    return std::nullopt;
}

void DevTools::pick(DevContext& ctx) {
    hovered_ = {};
    hovered_ground_.reset();
    if (!ctx.ray_valid) {
        return;
    }
    if (const auto t = ground_hit(ctx)) {
        hovered_ground_ = ctx.ray_origin + ctx.ray_dir * *t;
    }
    float best = kMaxPick;
    const auto consider = [&](DevObject o, math::Vec3 base, float h, float radius) {
        const RayHit hit = ray_to_vertical_segment(ctx.ray_origin, ctx.ray_dir, base, h);
        if (hit.t > 0.0f && hit.distance <= radius && hit.t < best) {
            best = hit.t;
            hovered_ = o;
        }
    };
    if (ctx.crowd != nullptr) {
        for (std::size_t i = 0; i < ctx.crowd->size(); ++i) {
            const DevObject o{DevObject::Kind::Villager, i};
            consider(o, ctx.crowd->position(i), height(ctx, o), 0.45f);
        }
    }
    if (ctx.map == nullptr) {
        return;
    }
    if (ctx.scene != nullptr) {
        for (std::size_t i = 0; i < ctx.scene->houses().size(); ++i) {
            const DevObject o{DevObject::Kind::House, i};
            consider(o, position(ctx, o), 5.2f, 3.2f);
        }
    }
    if (indexed_map_ != ctx.map || indexed_count_ != ctx.map->features.size()) {
        build_index(*ctx.map);
    }
    // Features in the picking cells along the ray, up to the ground.
    const float end = std::min(kMaxPick, hovered_ground_ ? math::length(*hovered_ground_ - ctx.ray_origin) + 30.0f : kMaxPick);
    std::vector<std::int32_t> cells;
    for (float t = 0.0f; t <= end; t += kIndexCell * 0.5f) {
        const math::Vec3 p = ctx.ray_origin + ctx.ray_dir * t;
        const std::int32_t cx = static_cast<std::int32_t>(std::floor(p.x / kIndexCell));
        const std::int32_t cz = static_cast<std::int32_t>(std::floor(p.z / kIndexCell));
        for (std::int32_t dz = -1; dz <= 1; ++dz) {
            for (std::int32_t dx = -1; dx <= 1; ++dx) {
                const std::int32_t x = cx + dx;
                const std::int32_t z = cz + dz;
                if (x >= 0 && z >= 0 && x < index_side_ && z < index_side_) {
                    cells.push_back(z * index_side_ + x);
                }
            }
        }
    }
    std::sort(cells.begin(), cells.end());
    cells.erase(std::unique(cells.begin(), cells.end()), cells.end());
    for (const std::int32_t c : cells) {
        for (const std::uint32_t i : index_[static_cast<std::size_t>(c)]) {
            const DevObject o{DevObject::Kind::Feature, i};
            const float h = height(ctx, o);
            const bool tree = ctx.map->features[i].type == sim::FeatureType::Tree;
            consider(o, position(ctx, o), h, tree ? std::max(0.8f, h * 0.22f) : std::max(0.5f, h * 0.9f));
        }
    }
}

void DevTools::update(DevContext& ctx) {
    if (!visible_) {
        hovered_ = {};
        return;
    }
    if (!valid(ctx, selected_)) {
        selected_ = {};
    }
    pick(ctx);
    if (!ctx.clicked) {
        return;
    }
    // Clicks only create while the Create tab is the one shown.
    if (place_on_click_ && active_tab_ == Tab::Create) {
        if (const auto t = ground_hit(ctx)) {
            place(ctx, ctx.ray_origin + ctx.ray_dir * *t);
        }
        return;
    }
    selected_ = hovered_;
    if (selected_.kind != DevObject::Kind::None) {
        switch_to_ = Tab::Inspector;
    }
}

// --- Changes -----------------------------------------------------------------

void DevTools::place(DevContext& ctx, math::Vec3 at) {
    if (create_kind_ == CreateKind::Person) {
        if (ctx.crowd == nullptr) {
            return;
        }
        std::optional<bool> female;
        if (person_body_ != 0) {
            female = person_body_ == 2;
        }
        for (int i = 0; i < person_count_; ++i) {
            const float a = static_cast<float>(i) * 2.399963f;
            const float r = i == 0 ? 0.0f : 1.2f * std::sqrt(static_cast<float>(i));
            selected_ = {DevObject::Kind::Villager,
                         ctx.crowd->add_villager(at + math::Vec3{std::cos(a) * r, 0.0f, std::sin(a) * r}, female)};
        }
        last_message_ = i18n::tr_n("dev.create.addedPeople", person_count_);
        list_dirty_ = true;
        return;
    }
    if (ctx.map == nullptr || ctx.scene == nullptr || ctx.renderer == nullptr) {
        last_message_ = tr("dev.create.noMap");
        return;
    }
    const float size = static_cast<float>(ctx.map->size);
    if (at.x < 0.0f || at.z < 0.0f || at.x >= size || at.z >= size) {
        last_message_ = tr("dev.create.outside");
        return;
    }
    const auto rotation = static_cast<std::uint16_t>((static_cast<std::uint32_t>(at.x * 977.0f) ^
                                                      static_cast<std::uint32_t>(at.z * 613.0f)) * 40503u);
    if (create_kind_ == CreateKind::House) {
        render::Instance h;
        h.position = {at.x, map_surface_height(*ctx.map, at.x, at.z) - 0.1f, at.z};
        h.yaw = house_yaw_deg_ * std::numbers::pi_v<float> / 180.0f;
        ctx.scene->add_house(*ctx.renderer, h);
        selected_ = {DevObject::Kind::House, ctx.scene->houses().size() - 1};
        last_message_ = tr("dev.create.added", tr("dev.object.house"));
        list_dirty_ = true;
        return;
    }
    sim::MapFeature f;
    f.x = to_fixed(at.x);
    f.z = to_fixed(at.z);
    f.rotation = rotation;
    switch (create_kind_) {
        case CreateKind::Tree: {
            if (ctx.content == nullptr || ctx.content->flora.species.empty()) {
                return;
            }
            const auto species = std::min<std::size_t>(static_cast<std::size_t>(species_), ctx.content->flora.species.size() - 1);
            const auto tsize = ctx.content->flora.fit_size(species, static_cast<sim::TreeSize>(size_));
            const sim::SizeInfo& si = sim::size_info(tsize);
            const auto cm = std::clamp(static_cast<std::int32_t>(height_m_ * 100.0f), si.min_cm, si.max_cm);
            f.type = sim::FeatureType::Tree;
            f.species = static_cast<std::uint8_t>(species);
            f.size = static_cast<std::uint8_t>(tsize);
            f.scale = sim::Fixed::from_ratio(cm, si.model_cm);
            break;
        }
        case CreateKind::BerryBush: f.type = sim::FeatureType::BerryBush; break;
        case CreateKind::Herbs: f.type = sim::FeatureType::Herbs; break;
        case CreateKind::Stone: f.type = sim::FeatureType::Stone; f.scale = sim::Fixed::from_ratio(3, 2); break;
        case CreateKind::IronOre: f.type = sim::FeatureType::IronOre; f.scale = sim::Fixed::from_ratio(3, 2); break;
        default: return;
    }
    ctx.map->features.push_back(f);
    ctx.scene->refresh_features(*ctx.renderer, *ctx.map, *ctx.content);
    selected_ = {DevObject::Kind::Feature, ctx.map->features.size() - 1};
    last_message_ = tr("dev.create.added", name(ctx, selected_));
    list_dirty_ = true;
}

void DevTools::remove(DevContext& ctx, DevObject o) {
    if (!valid(ctx, o)) {
        return;
    }
    switch (o.kind) {
        case DevObject::Kind::Feature:
            ctx.map->features.erase(ctx.map->features.begin() + static_cast<std::ptrdiff_t>(o.index));
            ctx.scene->refresh_features(*ctx.renderer, *ctx.map, *ctx.content);
            break;
        case DevObject::Kind::House: ctx.scene->remove_house(*ctx.renderer, o.index); break;
        case DevObject::Kind::Villager: ctx.crowd->remove_villager(o.index); break;
        case DevObject::Kind::None: break;
    }
    // Indices after the removed one moved; start clean.
    selected_ = {};
    hovered_ = {};
    list_dirty_ = true;
}

void DevTools::go_to(DevContext& ctx, DevObject o) {
    if (ctx.camera == nullptr || !valid(ctx, o)) {
        return;
    }
    ctx.camera->set_target(position(ctx, o));
    ctx.camera->set_distance(std::max(25.0f, height(ctx, o) * 2.5f));
}

// --- Window ------------------------------------------------------------------

void DevTools::draw(DevContext& ctx) {
    if (!visible_) {
        return;
    }
    ImGui::SetNextWindowPos(ImVec2(12.0f, 200.0f), ImGuiCond_FirstUseEver);
    ImGui::SetNextWindowSize(ImVec2(440.0f, 560.0f), ImGuiCond_FirstUseEver);
    const std::string title = tr("dev.title") + "###devtools";
    // Set again below by the tab that is shown; a collapsed window shows none.
    active_tab_ = Tab::Inspector;
    if (ImGui::Begin(title.c_str(), &visible_)) {
        if (ImGui::BeginTabBar("tabs")) {
            const auto tab = [&](Tab t, const char* key, const char* id) {
                const ImGuiTabItemFlags flags = switch_to_ == t ? ImGuiTabItemFlags_SetSelected : 0;
                return ImGui::BeginTabItem(label(key, id).c_str(), nullptr, flags);
            };
            if (tab(Tab::Inspector, "dev.tab.inspector", "inspector")) {
                active_tab_ = Tab::Inspector;
                inspector_tab(ctx);
                ImGui::EndTabItem();
            }
            if (tab(Tab::Create, "dev.tab.create", "create")) {
                active_tab_ = Tab::Create;
                create_tab(ctx);
                ImGui::EndTabItem();
            }
            if (tab(Tab::Explorer, "dev.tab.explorer", "explorer")) {
                active_tab_ = Tab::Explorer;
                explorer_tab(ctx);
                ImGui::EndTabItem();
            }
            if (ctx.session != nullptr && tab(Tab::Village, "dev.tab.village", "village")) {
                active_tab_ = Tab::Village;
                village_tab(ctx);
                ImGui::EndTabItem();
            }
            switch_to_.reset();
            ImGui::EndTabBar();
        }
    }
    ImGui::End();
}

// Village: goods for testing (a command, so the game stays deterministic).
void DevTools::village_tab(DevContext& ctx) {
    if (ctx.session == nullptr) {
        return;
    }
    const sim::Game& game = ctx.session->game();
    ImGui::SliderInt("##grant", &grant_amount_, 10, 1000);
    if (ImGui::Button((tr("dev.village.grant", grant_amount_) + "###grant").c_str())) {
        for (std::size_t r = 0; r < game.content().resources.size(); ++r) {
            sim::Command c;
            c.type = sim::CommandType::DevGrant;
            c.def = static_cast<sim::DefIndex>(r);
            c.value = grant_amount_;
            ctx.session->issue(c);
        }
    }
    const sim::EntityId selected = ctx.session->ui().selected_building;
    ImGui::BeginDisabled(game.buildings().get(selected) == nullptr);
    if (ImGui::Button((tr("dev.village.ignite") + "###ignite").c_str())) {
        sim::Command c;
        c.type = sim::CommandType::DevIgnite;
        c.entity = selected;
        ctx.session->issue(c);
    }
    ImGui::EndDisabled();
    if (ImGui::Button((tr("dev.village.level") + "###level").c_str())) {
        sim::Command c;
        c.type = sim::CommandType::DevLevel;
        ctx.session->issue(c);
    }
    if (ImGui::Button((tr("dev.village.spawn") + "###spawn").c_str())) {
        sim::Command c;
        c.type = sim::CommandType::DevSpawn;
        c.value = 500;
        ctx.session->issue(c);
    }
    if (ImGui::Button((tr("dev.village.raid") + "###raid").c_str())) {
        sim::Command c;
        c.type = sim::CommandType::DevRaid;
        ctx.session->issue(c);
    }
    // Phase 32: see through the fog of war. Only this view changes, and only
    // where the developer tools' commands are allowed.
    if (game.fog()) {
        bool reveal = ctx.session->fog().revealed();
        ImGui::BeginDisabled(!game.dev_commands());
        if (ImGui::Checkbox((tr("dev.village.reveal") + "###reveal").c_str(), &reveal)) {
            ctx.session->fog().set_revealed(reveal);
        }
        ImGui::EndDisabled();
    }
    ImGui::Separator();
    ImGui::Text("tick %llu", static_cast<unsigned long long>(game.tick()));
    ImGui::Text("villagers %zu, buildings %zu", game.villagers().size(), game.buildings().size());
    ImGui::Text("rejected commands %u", game.rejected_commands());
}

void DevTools::terrain_info(const DevContext& ctx, math::Vec3 at) {
    if (ctx.map == nullptr) {
        return;
    }
    const auto cx = static_cast<std::int32_t>(std::floor(at.x));
    const auto cz = static_cast<std::int32_t>(std::floor(at.z));
    ImGui::SeparatorText(tr("dev.terrain.title").c_str());
    for (const std::string& line : describe_lines(terrain_names_.describe(*ctx.map, cx, cz), ctx.content)) {
        ImGui::TextUnformatted(line.c_str());
    }
}

void DevTools::inspector_tab(DevContext& ctx) {
    const bool selected = valid(ctx, selected_);
    const DevObject o = selected ? selected_ : hovered_;
    if (!valid(ctx, o)) {
        ImGui::TextWrapped("%s", tr("dev.inspector.empty").c_str());
        if (hovered_ground_) {
            const math::Vec3 g = *hovered_ground_;
            ImGui::Text("%s: %.2f, %.2f, %.2f", tr("dev.inspector.position").c_str(), static_cast<double>(g.x),
                        static_cast<double>(g.y), static_cast<double>(g.z));
            terrain_info(ctx, g);
        }
        return;
    }
    ImGui::TextDisabled("%s", tr(selected ? "dev.inspector.selected" : "dev.inspector.hovered").c_str());
    ImGui::Text("%s", name(ctx, o).c_str());
    const math::Vec3 p = position(ctx, o);
    ImGui::Text("%s: %zu", tr("dev.inspector.index").c_str(), o.index);
    ImGui::Text("%s: %.2f, %.2f, %.2f", tr("dev.inspector.position").c_str(), static_cast<double>(p.x),
                static_cast<double>(p.y), static_cast<double>(p.z));
    if (ctx.camera != nullptr) {
        ImGui::Text("%s: %.1f m", tr("dev.inspector.distance").c_str(),
                    static_cast<double>(math::length(p - ctx.camera->eye())));
    }
    ImGui::Text("%s: %.2f m", tr("dev.inspector.height").c_str(), static_cast<double>(height(ctx, o)));

    if (o.kind == DevObject::Kind::Feature) {
        const sim::MapFeature& f = ctx.map->features[o.index];
        ImGui::Text("%s: %.1f°", tr("dev.inspector.rotation").c_str(), static_cast<double>(f.rotation) * 360.0 / 65536.0);
        if (f.type == sim::FeatureType::Tree) {
            const sim::Flora& flora = ctx.content->flora;
            const std::size_t species = f.species;
            ImGui::SeparatorText(tr("dev.inspector.tree").c_str());
            ImGui::Text("%s: %s", tr("dev.inspector.species").c_str(), species_name(ctx.content, f.species).c_str());
            const sim::SizeInfo& si = sim::size_info(static_cast<sim::TreeSize>(f.size));
            ImGui::Text("%s: %s (%.0f-%.0f m)", tr("dev.inspector.size").c_str(), size_name(f.size).c_str(),
                        static_cast<double>(si.min_cm) / 100.0, static_cast<double>(si.max_cm) / 100.0);
            std::string sizes;
            for (std::size_t s = 0; s < sim::kTreeSizes; ++s) {
                if (flora.species_has_size(species, static_cast<sim::TreeSize>(s))) {
                    sizes += (sizes.empty() ? "" : ", ") + size_name(s);
                }
            }
            ImGui::Text("%s: %s", tr("dev.inspector.sizes").c_str(), sizes.c_str());
            if (species < flora.species.size()) {
                ImGui::Text("%s: %s", tr("dev.inspector.model").c_str(),
                            tree_model_file(flora.species[species], static_cast<sim::TreeSize>(f.size)).c_str());
            }
        } else {
            ImGui::Text("%s: %.2f", tr("dev.inspector.scale").c_str(), static_cast<double>(to_float(f.scale)));
        }
    } else if (o.kind == DevObject::Kind::House) {
        ImGui::Text("%s: %.1f°", tr("dev.inspector.rotation").c_str(),
                    static_cast<double>(ctx.scene->houses()[o.index].yaw) * 180.0 / std::numbers::pi);
        ImGui::Text("%s: house_small.glb", tr("dev.inspector.model").c_str());
    } else if (o.kind == DevObject::Kind::Villager) {
        const TestCrowd::VillagerInfo v = ctx.crowd->info(o.index);
        ImGui::SeparatorText(tr("dev.inspector.villager").c_str());
        ImGui::Text("%s: %s", tr("dev.inspector.activity").c_str(),
                    tr(v.walking ? "dev.inspector.walking" : "dev.inspector.resting").c_str());
        ImGui::Text("%s: %.2f m/s", tr("dev.inspector.speed").c_str(), static_cast<double>(v.speed));
        ImGui::Text("%s: %u", tr("dev.inspector.palette").c_str(), v.palette);
        ImGui::Text("%s: %s%s%s", tr("dev.inspector.accessories").c_str(), v.hat ? tr("dev.inspector.hat").c_str() : "",
                    v.beard ? (" " + tr("dev.inspector.beard")).c_str() : "",
                    v.apron ? (" " + tr("dev.inspector.apron")).c_str() : "");
        ImGui::Text("%s: %.1f, %.1f", tr("dev.inspector.target").c_str(), static_cast<double>(v.target.x),
                    static_cast<double>(v.target.z));
        ImGui::Text("%s: %.1f, %.1f", tr("dev.inspector.home").c_str(), static_cast<double>(v.home.x),
                    static_cast<double>(v.home.z));
    }
    terrain_info(ctx, p);

    ImGui::Separator();
    if (ImGui::Button(label("dev.inspector.goTo", "goto").c_str())) {
        go_to(ctx, o);
    }
    ImGui::SameLine();
    if (selected && ImGui::Button(label("dev.inspector.deselect", "deselect").c_str())) {
        selected_ = {};
    }
    ImGui::SameLine();
    if (ImGui::Button(label("dev.inspector.delete", "delete").c_str())) {
        remove(ctx, o);
    }
}

void DevTools::create_tab(DevContext& ctx) {
    static constexpr const char* kKinds[] = {"dev.create.kind.tree",  "feature.berryBush", "feature.herbs",
                                             "feature.stone",         "feature.ironOre",   "dev.object.house",
                                             "dev.create.kind.person"};
    int kind = static_cast<int>(create_kind_);
    if (ImGui::BeginCombo(label("dev.create.kind", "kind").c_str(), tr(kKinds[kind]).c_str())) {
        for (int i = 0; i < static_cast<int>(std::size(kKinds)); ++i) {
            if (ImGui::Selectable((tr(kKinds[i]) + "###k" + std::to_string(i)).c_str(), i == kind)) {
                create_kind_ = static_cast<CreateKind>(i);
            }
        }
        ImGui::EndCombo();
    }
    if (create_kind_ == CreateKind::Tree) {
        if (ImGui::BeginCombo(label("dev.inspector.species", "species").c_str(),
                              species_name(ctx.content, static_cast<std::size_t>(species_)).c_str())) {
            const std::size_t count = ctx.content != nullptr ? ctx.content->flora.species.size() : 0;
            for (std::size_t s = 0; s < count; ++s) {
                if (ImGui::Selectable((species_name(ctx.content, s) + "###s" + std::to_string(s)).c_str(),
                                      static_cast<int>(s) == species_)) {
                    species_ = static_cast<int>(s);
                }
            }
            ImGui::EndCombo();
        }
        static const sim::Flora kNoFlora;
        const sim::Flora& flora = ctx.content != nullptr ? ctx.content->flora : kNoFlora;
        const auto species = static_cast<std::size_t>(species_);
        size_ = static_cast<int>(flora.fit_size(species, static_cast<sim::TreeSize>(size_)));
        if (ImGui::BeginCombo(label("dev.inspector.size", "size").c_str(), size_name(static_cast<std::size_t>(size_)).c_str())) {
            for (std::size_t s = 0; s < sim::kTreeSizes; ++s) {
                if (!flora.species_has_size(species, static_cast<sim::TreeSize>(s))) {
                    continue;
                }
                if (ImGui::Selectable((size_name(s) + "###z" + std::to_string(s)).c_str(), static_cast<int>(s) == size_)) {
                    size_ = static_cast<int>(s);
                }
            }
            ImGui::EndCombo();
        }
        const sim::SizeInfo& si = sim::size_info(static_cast<sim::TreeSize>(size_));
        const float lo = static_cast<float>(si.min_cm) / 100.0f;
        const float hi = static_cast<float>(si.max_cm) / 100.0f;
        height_m_ = std::clamp(height_m_, lo, hi);
        ImGui::SliderFloat(label("dev.inspector.height", "height").c_str(), &height_m_, lo, hi, "%.1f m");
    } else if (create_kind_ == CreateKind::House) {
        ImGui::SliderFloat(label("dev.inspector.rotation", "rot").c_str(), &house_yaw_deg_, 0.0f, 359.0f, "%.0f°");
    } else if (create_kind_ == CreateKind::Person) {
        const std::string bodies[] = {tr("dev.create.body.random"), tr("dev.create.body.man"), tr("dev.create.body.woman")};
        if (ImGui::BeginCombo(label("dev.create.body", "body").c_str(), bodies[person_body_].c_str())) {
            for (int i = 0; i < 3; ++i) {
                if (ImGui::Selectable((bodies[i] + "###b" + std::to_string(i)).c_str(), i == person_body_)) {
                    person_body_ = i;
                }
            }
            ImGui::EndCombo();
        }
        ImGui::SliderInt(label("dev.create.count", "count").c_str(), &person_count_, 1, 50);
    }
    ImGui::Separator();
    ImGui::Checkbox(label("dev.create.onClick", "onclick").c_str(), &place_on_click_);
    if (ImGui::Button(label("dev.create.atView", "atview").c_str()) && ctx.camera != nullptr) {
        place(ctx, ctx.camera->target());
    }
    ImGui::TextWrapped("%s", tr("dev.create.hint").c_str());
    if (!last_message_.empty()) {
        ImGui::TextColored(ImVec4(0.85f, 0.65f, 0.25f, 1.0f), "%s", last_message_.c_str());
    }
}

bool DevTools::passes(const DevContext& ctx, DevObject o) const {
    switch (filter_) {
        case Filter::All: break;
        case Filter::Trees:
            if (o.kind != DevObject::Kind::Feature || ctx.map->features[o.index].type != sim::FeatureType::Tree) {
                return false;
            }
            break;
        case Filter::Plants: {
            if (o.kind != DevObject::Kind::Feature) {
                return false;
            }
            const sim::FeatureType t = ctx.map->features[o.index].type;
            if (t != sim::FeatureType::BerryBush && t != sim::FeatureType::Herbs) {
                return false;
            }
            break;
        }
        case Filter::Rocks: {
            if (o.kind != DevObject::Kind::Feature) {
                return false;
            }
            const sim::FeatureType t = ctx.map->features[o.index].type;
            if (t != sim::FeatureType::Stone && t != sim::FeatureType::IronOre) {
                return false;
            }
            break;
        }
        case Filter::Houses:
            if (o.kind != DevObject::Kind::House) {
                return false;
            }
            break;
        case Filter::People:
            if (o.kind != DevObject::Kind::Villager) {
                return false;
            }
            break;
        case Filter::Count: break;
    }
    return true;
}

void DevTools::rebuild_list(const DevContext& ctx) {
    list_.clear();
    const std::string needle = fold_for_search(applied_search_);
    // Features share few distinct names: fold each name once per slot.
    std::vector<std::int8_t> slot_match(ctx.content != nullptr ? visual_slot_count(*ctx.content) : 0, -1);
    const auto matches = [&](DevObject o) {
        if (!passes(ctx, o)) {
            return false;
        }
        if (needle.empty()) {
            return true;
        }
        if (o.kind == DevObject::Kind::Feature) {
            const std::size_t slot = visual_slot(*ctx.content, ctx.map->features[o.index]);
            if (slot >= slot_match.size()) {
                return false;
            }
            std::int8_t& m = slot_match[slot];
            if (m < 0) {
                m = fold_for_search(name(ctx, o)).find(needle) != std::string::npos ? 1 : 0;
            }
            return m == 1;
        }
        return fold_for_search(name(ctx, o)).find(needle) != std::string::npos;
    };
    if (ctx.crowd != nullptr) {
        for (std::size_t i = 0; i < ctx.crowd->size(); ++i) {
            if (matches({DevObject::Kind::Villager, i})) {
                list_.push_back({DevObject::Kind::Villager, i});
            }
        }
    }
    if (ctx.map != nullptr && ctx.scene != nullptr) {
        for (std::size_t i = 0; i < ctx.scene->houses().size(); ++i) {
            if (matches({DevObject::Kind::House, i})) {
                list_.push_back({DevObject::Kind::House, i});
            }
        }
        for (std::size_t i = 0; i < ctx.map->features.size(); ++i) {
            if (matches({DevObject::Kind::Feature, i})) {
                list_.push_back({DevObject::Kind::Feature, i});
            }
        }
    }
    if (sort_by_distance_ && ctx.camera != nullptr) {
        const math::Vec3 eye = ctx.camera->target();
        std::vector<std::pair<float, DevObject>> keyed;
        keyed.reserve(list_.size());
        for (const DevObject o : list_) {
            const math::Vec3 d = position(ctx, o) - eye;
            keyed.push_back({d.x * d.x + d.z * d.z, o});
        }
        std::stable_sort(keyed.begin(), keyed.end(), [](const auto& a, const auto& b) { return a.first < b.first; });
        for (std::size_t i = 0; i < keyed.size(); ++i) {
            list_[i] = keyed[i].second;
        }
    }
    list_dirty_ = false;
}

void DevTools::explorer_tab(DevContext& ctx) {
    static constexpr const char* kFilters[] = {"dev.filter.all",   "dev.filter.trees",  "dev.filter.plants",
                                               "dev.filter.rocks", "dev.filter.houses", "dev.filter.people"};
    int filter = static_cast<int>(filter_);
    if (ImGui::BeginCombo(label("dev.explorer.category", "category").c_str(), tr(kFilters[filter]).c_str())) {
        for (int i = 0; i < static_cast<int>(std::size(kFilters)); ++i) {
            if (ImGui::Selectable((tr(kFilters[i]) + "###f" + std::to_string(i)).c_str(), i == filter)) {
                filter_ = static_cast<Filter>(i);
            }
        }
        ImGui::EndCombo();
    }
    ImGui::InputTextWithHint(label("dev.explorer.search", "search").c_str(), tr("dev.explorer.searchHint").c_str(),
                             search_, sizeof(search_));
    if (ImGui::Checkbox(label("dev.explorer.byDistance", "bydist").c_str(), &sort_by_distance_)) {
        list_dirty_ = true;
    }
    ImGui::SameLine();
    if (ImGui::Button(label("dev.explorer.refresh", "refresh").c_str())) {
        list_dirty_ = true;
    }
    if (applied_search_ != search_ || applied_filter_ != filter_) {
        applied_search_ = search_;
        applied_filter_ = filter_;
        list_dirty_ = true;
    }
    // Stale indices after a change elsewhere would point at other objects.
    for (const DevObject o : list_) {
        if (!valid(ctx, o)) {
            list_dirty_ = true;
            break;
        }
    }
    if (list_dirty_) {
        rebuild_list(ctx);
    }
    ImGui::Text("%s", i18n::tr_n("dev.explorer.count", static_cast<std::int64_t>(list_.size())).c_str());
    if (ImGui::BeginTable("objects", 3,
                          ImGuiTableFlags_ScrollY | ImGuiTableFlags_RowBg | ImGuiTableFlags_BordersInnerV |
                              ImGuiTableFlags_Resizable)) {
        ImGui::TableSetupScrollFreeze(0, 1);
        ImGui::TableSetupColumn(tr("dev.explorer.name").c_str());
        ImGui::TableSetupColumn(tr("dev.inspector.position").c_str());
        ImGui::TableSetupColumn(tr("dev.inspector.distance").c_str());
        ImGui::TableHeadersRow();
        ImGuiListClipper clipper;
        clipper.Begin(static_cast<int>(list_.size()));
        while (clipper.Step()) {
            for (int row = clipper.DisplayStart; row < clipper.DisplayEnd; ++row) {
                const DevObject o = list_[static_cast<std::size_t>(row)];
                if (!valid(ctx, o)) {
                    continue;
                }
                const math::Vec3 p = position(ctx, o);
                ImGui::TableNextRow();
                ImGui::TableNextColumn();
                const std::string text = name(ctx, o) + "##row" + std::to_string(row);
                if (ImGui::Selectable(text.c_str(), o == selected_, ImGuiSelectableFlags_SpanAllColumns)) {
                    selected_ = o;
                    go_to(ctx, o);
                }
                ImGui::TableNextColumn();
                ImGui::Text("%.0f, %.0f", static_cast<double>(p.x), static_cast<double>(p.z));
                ImGui::TableNextColumn();
                const float d = ctx.camera != nullptr ? math::length(p - ctx.camera->target()) : 0.0f;
                ImGui::Text("%.0f m", static_cast<double>(d));
            }
        }
        ImGui::EndTable();
    }
}

}  // namespace sc
