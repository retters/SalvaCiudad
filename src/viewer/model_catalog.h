// The model viewer's catalog (phase 30): every model file of the mods, by
// category and group, with the definitions and code that use each one, the
// files nothing uses and the definitions whose file is missing. No window or
// GPU here, so the tests can check it.
#pragma once

#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <span>
#include <string>
#include <string_view>
#include <vector>

#include "game/builtin_models.h"
#include "math/vec.h"
#include "mods/mod_library.h"
#include "render/model.h"

namespace sc::viewer {

enum class Category : std::uint8_t { Buildings, Trees, Props, Characters, Animals, Other, Count };

// Text key of a category, "viewer.category.buildings".
[[nodiscard]] std::string_view category_key(Category category);

// Who uses a model.
struct Use {
    std::string kind;      // "building", "mapFeature", "species", "race" or "code".
    std::string id;        // The definition's id, or the code's group ("cloud").
    std::string name_key;  // The definition's name; may be empty.
};

struct CatalogModel {
    std::string mod;
    std::string path;  // Inside the mod, with '/': "models/props/rock.glb".
    std::filesystem::path file;
    Category category = Category::Other;
    std::size_t group = 0;  // Index into Catalog::groups.
    std::vector<Use> uses;

    [[nodiscard]] bool used() const { return !uses.empty(); }
};

// Models shown together: the variants of one thing. A definition's models
// (a species' sizes, a race's bodies), the models of one use in the code
// (the hats), or files that differ only in a size or sex suffix.
struct CatalogGroup {
    std::string id;        // "core:house", "code:hat" or "<mod>:file:<stem>".
    std::string name_key;  // May be empty.
    Category category = Category::Other;
    std::vector<std::size_t> models;  // Into Catalog::models, smallest first.
};

struct ModFolder {
    std::string id;
    std::filesystem::path dir;
};

namespace catalog_limits {
inline constexpr std::size_t kMaxModels = 4096;
inline constexpr int kMaxDepth = 8;
}  // namespace catalog_limits

struct Catalog {
    std::vector<CatalogModel> models;
    std::vector<CatalogGroup> groups;       // By category, then id.
    std::vector<mods::ModelRef> missing;    // Definitions whose file is not there.
    bool truncated = false;                 // More files than kMaxModels.

    [[nodiscard]] std::size_t unused_count() const;
    [[nodiscard]] const CatalogModel* find(std::string_view mod, std::string_view path) const;
};

// Lists the .glb files under each mod's `models` folder and matches them
// with `refs` (from the mod build) and with the models the code loads by name
// (in `builtin_mod`).
[[nodiscard]] Catalog build_catalog(std::span<const ModFolder> mods, std::span<const mods::ModelRef> refs,
                                    std::span<const builtin_models::Use> builtin = builtin_models::kAll,
                                    std::string_view builtin_mod = mods::kCoreModId);

// A line of the catalog list as shown: a category header, a group, or a
// model inside an open group.
enum class RowKind : std::uint8_t { Category, Group, Model };

struct CatalogRow {
    RowKind kind = RowKind::Category;
    Category category = Category::Other;
    std::size_t group = 0;  // Groups and models.
    std::size_t model = 0;  // Models.
    bool expandable = false;
    bool open = false;

    // The same line, whether it is open or not.
    [[nodiscard]] bool same(const CatalogRow& o) const {
        return kind == o.kind && category == o.category && (kind == RowKind::Category || group == o.group) &&
               (kind != RowKind::Model || model == o.model);
    }
};

enum class NavKey : std::uint8_t { Up, Down, Left, Right };

// What a key does on the list: where the cursor goes and whether the line
// under it opens or closes.
struct NavResult {
    std::size_t cursor = 0;
    enum class Toggle : std::uint8_t { None, Open, Close } toggle = Toggle::None;
};

// Up and down move one line. Right opens a closed line, or enters an open
// one. Left closes an open line, or goes up to the line that contains it.
[[nodiscard]] NavResult navigate(std::span<const CatalogRow> rows, std::size_t cursor, NavKey key);

// What a model costs to draw.
struct ModelStats {
    std::size_t vertices = 0;
    std::size_t triangles = 0;
    std::size_t draw_calls = 0;  // Per pass: one per primitive.
    std::size_t materials = 0;   // Used by its primitives.
    std::size_t textures = 0;
    int largest_texture = 0;     // Pixels on the longest side.
    math::Vec3 size;             // Of its bounding box, meters.
    bool skinned = false;
    std::size_t joints = 0;
    std::vector<std::string> clips;
};

[[nodiscard]] ModelStats model_stats(const render::ModelData& model);

}  // namespace sc::viewer
