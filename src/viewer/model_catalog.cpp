#include "viewer/model_catalog.h"

#include <algorithm>
#include <map>
#include <system_error>
#include <tuple>

#include "core/text.h"

namespace sc::viewer {

namespace {

// Suffixes that make a file a variant of another: tree sizes and sexes. The
// order is the order shown.
constexpr std::string_view kVariantSuffixes[] = {"_small", "_medium", "_large", "_huge", "_male", "_female"};

bool ends_with(std::string_view s, std::string_view end) {
    return s.size() >= end.size() && s.substr(s.size() - end.size()) == end;
}

std::string lower(std::string s) {
    for (char& c : s) {
        if (c >= 'A' && c <= 'Z') {
            c = static_cast<char>(c - 'A' + 'a');
        }
    }
    return s;
}

// The file name without folder, ".glb" and variant suffix.
std::string base_stem(std::string_view path) {
    std::string_view name = path.substr(path.rfind('/') == std::string_view::npos ? 0 : path.rfind('/') + 1);
    if (ends_with(name, ".glb")) {
        name.remove_suffix(4);
    }
    for (const std::string_view suffix : kVariantSuffixes) {
        if (ends_with(name, suffix) && name.size() > suffix.size()) {
            name.remove_suffix(suffix.size());
            break;
        }
    }
    return std::string(name);
}

// Where a file goes in a group: after its variant suffix, then by name.
std::size_t variant_rank(std::string_view path) {
    std::string_view name = path;
    if (ends_with(name, ".glb")) {
        name.remove_suffix(4);
    }
    for (std::size_t i = 0; i < std::size(kVariantSuffixes); ++i) {
        if (ends_with(name, kVariantSuffixes[i])) {
            return i + 1;
        }
    }
    return 0;
}

Category category_of(std::string_view path, const std::vector<Use>& uses) {
    const bool species = std::any_of(uses.begin(), uses.end(), [](const Use& u) { return u.kind == "species"; });
    if (path.starts_with("models/buildings/")) {
        return Category::Buildings;
    }
    if (path.starts_with("models/characters/")) {
        return Category::Characters;
    }
    if (path.starts_with("models/animals/")) {
        return Category::Animals;
    }
    if (species || path.starts_with("models/props/tree_")) {
        return Category::Trees;
    }
    if (path.starts_with("models/props/")) {
        return Category::Props;
    }
    return Category::Other;
}

// The .glb files of one mod, as paths inside it. Links are not followed.
void scan_mod(const ModFolder& mod, Catalog& out) {
    const std::filesystem::path root = mod.dir / "models";
    std::error_code ec;
    if (!std::filesystem::is_directory(root, ec)) {
        return;
    }
    std::filesystem::recursive_directory_iterator it(root, std::filesystem::directory_options::skip_permission_denied,
                                                     ec);
    const std::filesystem::recursive_directory_iterator end;
    std::vector<CatalogModel> found;
    for (; !ec && it != end; it.increment(ec)) {
        if (it.depth() >= catalog_limits::kMaxDepth) {
            it.disable_recursion_pending();
        }
        const std::filesystem::directory_entry& entry = *it;
        std::error_code ec2;
        if (entry.is_symlink(ec2)) {
            if (entry.is_directory(ec2)) {
                it.disable_recursion_pending();
            }
            continue;
        }
        if (!entry.is_regular_file(ec2) || lower(text::path_to_utf8(entry.path().extension())) != ".glb") {
            continue;
        }
        if (out.models.size() + found.size() >= catalog_limits::kMaxModels) {
            out.truncated = true;
            break;
        }
        CatalogModel m;
        m.mod = mod.id;
        m.path = text::path_to_utf8(entry.path().lexically_relative(mod.dir));
        std::replace(m.path.begin(), m.path.end(), '\\', '/');
        m.file = entry.path();
        found.push_back(std::move(m));
    }
    // The directory order depends on the file system.
    std::sort(found.begin(), found.end(), [](const CatalogModel& a, const CatalogModel& b) { return a.path < b.path; });
    for (CatalogModel& m : found) {
        out.models.push_back(std::move(m));
    }
}

}  // namespace

std::string_view category_key(Category category) {
    switch (category) {
        case Category::Buildings: return "viewer.category.buildings";
        case Category::Trees: return "viewer.category.trees";
        case Category::Props: return "viewer.category.props";
        case Category::Characters: return "viewer.category.characters";
        case Category::Animals: return "viewer.category.animals";
        case Category::Other:
        case Category::Count: break;
    }
    return "viewer.category.other";
}

std::size_t Catalog::unused_count() const {
    return static_cast<std::size_t>(
        std::count_if(models.begin(), models.end(), [](const CatalogModel& m) { return !m.used(); }));
}

const CatalogModel* Catalog::find(std::string_view mod, std::string_view path) const {
    for (const CatalogModel& m : models) {
        if (m.mod == mod && m.path == path) {
            return &m;
        }
    }
    return nullptr;
}

Catalog build_catalog(std::span<const ModFolder> mods, std::span<const mods::ModelRef> refs,
                      std::span<const builtin_models::Use> builtin, std::string_view builtin_mod) {
    Catalog out;
    for (const ModFolder& mod : mods) {
        scan_mod(mod, out);
    }
    // Who uses each file.
    for (const mods::ModelRef& ref : refs) {
        if (!ref.exists) {
            out.missing.push_back(ref);
            continue;
        }
        for (CatalogModel& m : out.models) {
            if (m.mod == ref.mod && m.path == ref.path) {
                m.uses.push_back({ref.def_type, ref.def_id, ref.name_key});
            }
        }
    }
    for (const builtin_models::Use& use : builtin) {
        for (CatalogModel& m : out.models) {
            if (m.mod == builtin_mod && m.path == use.path) {
                m.uses.push_back({"code", std::string(use.group), {}});
            }
        }
    }
    // Groups: the first definition that uses a file, else its use in the
    // code, else its name without a size or sex suffix.
    std::map<std::string, std::size_t> by_id;
    for (std::size_t i = 0; i < out.models.size(); ++i) {
        CatalogModel& m = out.models[i];
        m.category = category_of(m.path, m.uses);
        std::string id;
        std::string name_key;
        const auto def = std::find_if(m.uses.begin(), m.uses.end(), [](const Use& u) { return u.kind != "code"; });
        if (def != m.uses.end()) {
            id = def->id;
            name_key = def->name_key;
        } else if (!m.uses.empty()) {
            id = "code:" + m.uses.front().id;
        } else {
            id = m.mod + ":file:" + base_stem(m.path);
        }
        auto [it, added] = by_id.try_emplace(id, out.groups.size());
        if (added) {
            out.groups.push_back({id, name_key, m.category, {}});
        }
        out.groups[it->second].models.push_back(i);
    }
    for (CatalogGroup& g : out.groups) {
        std::sort(g.models.begin(), g.models.end(), [&](std::size_t a, std::size_t b) {
            const CatalogModel& ma = out.models[a];
            const CatalogModel& mb = out.models[b];
            return std::tuple(variant_rank(ma.path), ma.path) < std::tuple(variant_rank(mb.path), mb.path);
        });
    }
    // Sort the groups and point the models at their new places.
    std::vector<std::size_t> order(out.groups.size());
    for (std::size_t i = 0; i < order.size(); ++i) {
        order[i] = i;
    }
    std::sort(order.begin(), order.end(), [&](std::size_t a, std::size_t b) {
        return std::tuple(out.groups[a].category, out.groups[a].id) < std::tuple(out.groups[b].category, out.groups[b].id);
    });
    std::vector<CatalogGroup> sorted;
    sorted.reserve(order.size());
    for (const std::size_t g : order) {
        for (const std::size_t m : out.groups[g].models) {
            out.models[m].group = sorted.size();
        }
        sorted.push_back(std::move(out.groups[g]));
    }
    out.groups = std::move(sorted);
    return out;
}

NavResult navigate(std::span<const CatalogRow> rows, std::size_t cursor, NavKey key) {
    NavResult out;
    if (rows.empty()) {
        return out;
    }
    cursor = std::min(cursor, rows.size() - 1);
    out.cursor = cursor;
    const CatalogRow& row = rows[cursor];
    switch (key) {
        case NavKey::Up: out.cursor = cursor > 0 ? cursor - 1 : 0; break;
        case NavKey::Down: out.cursor = std::min(cursor + 1, rows.size() - 1); break;
        case NavKey::Right:
            if (row.expandable && !row.open) {
                out.toggle = NavResult::Toggle::Open;
            } else if (row.expandable && cursor + 1 < rows.size() && rows[cursor + 1].kind != RowKind::Category &&
                       rows[cursor + 1].kind != row.kind) {
                out.cursor = cursor + 1;  // Into its first line.
            }
            break;
        case NavKey::Left:
            if (row.expandable && row.open) {
                out.toggle = NavResult::Toggle::Close;
            } else if (row.kind != RowKind::Category) {
                // Up to the line that holds it.
                const RowKind parent = row.kind == RowKind::Model ? RowKind::Group : RowKind::Category;
                for (std::size_t i = cursor; i-- > 0;) {
                    if (rows[i].kind == parent) {
                        out.cursor = i;
                        break;
                    }
                }
            }
            break;
    }
    return out;
}

ModelStats model_stats(const render::ModelData& model) {
    ModelStats s;
    s.vertices = model.vertices.size();
    s.triangles = model.indices.size() / 3;
    s.draw_calls = model.primitives.size();
    std::vector<std::uint32_t> used;
    for (const render::ModelPrimitive& p : model.primitives) {
        if (std::find(used.begin(), used.end(), p.material) == used.end()) {
            used.push_back(p.material);
        }
    }
    s.materials = used.size();
    s.textures = model.textures.size();
    for (const render::ModelTexture& t : model.textures) {
        s.largest_texture = std::max({s.largest_texture, t.width, t.height});
    }
    s.size = model.bounds_max - model.bounds_min;
    s.skinned = model.skinned();
    s.joints = model.joint_names.size();
    for (const render::ModelClip& c : model.clips) {
        s.clips.push_back(c.name);
    }
    return s;
}

}  // namespace sc::viewer
