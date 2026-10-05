#include "mods/defs.h"

#include <algorithm>
#include <format>
#include <system_error>

#include "mods/mod_library.h"
#include "sim/command.h"
#include "sim/vision.h"

namespace sc::mods {

namespace {

constexpr std::size_t kMaxDefs = 20000;

const char* str(yyjson_mut_val* obj, const char* key) {
    return yyjson_mut_get_str(yyjson_mut_obj_get(obj, key));
}

bool valid_name_part(std::string_view s) {
    if (s.empty() || s.size() > 48) {
        return false;
    }
    return std::all_of(s.begin(), s.end(), [](char c) { return (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '_'; });
}

constexpr std::string_view kTypes[] = {"resource", "mapFeature", "building", "recipe", "species", "biome",
                                        "crop",     "disease",    "unit",   "tutorial", "race",   "herd"};
// In the order of sim::BiomeWater and sim::BiomeRegion (phase 54).
constexpr std::string_view kBiomeWaters[] = {"any", "fresh", "sea"};
constexpr std::string_view kBiomeRegions[] = {"plain", "hills", "mountains", "plateau", "basin"};
static_assert(std::size(kBiomeWaters) == static_cast<std::size_t>(sim::BiomeWater::Count));
static_assert(std::size(kBiomeRegions) == static_cast<std::size_t>(sim::BiomeRegion::Count));
constexpr std::string_view kSkillNames[] = {"wood", "stone", "forage", "farm",  "orchard",
                                            "hunt", "fish",  "build",  "craft", "metal"};
constexpr std::string_view kTutorialGoals[] = {"none",  "camera", "place",      "build", "workers",
                                               "speed", "stock",  "population", "lua"};
constexpr std::string_view kTutorialSizes[] = {"small", "medium"};
constexpr std::string_view kDiseaseSources[] = {"cold", "water", "rats", "food"};
constexpr std::string_view kSeasons[] = {"spring", "summer", "autumn", "winter"};
// In the order of sim::TreeState.
constexpr std::string_view kTreeStateNames[] = {"bloom", "autumn", "bare"};
static_assert(std::size(kTreeStateNames) == sim::kTreeStates);

bool known_type(std::string_view t) {
    return std::find(std::begin(kTypes), std::end(kTypes), t) != std::end(kTypes);
}

// Reads fields of one definition, collecting its errors.
class Reader {
public:
    Reader(const RawDef& def, std::vector<DefError>& errors) : def_(def), obj_(def.obj), errors_(errors) {}
    // Fields of an object inside the definition (errors name the definition).
    Reader(const RawDef& def, yyjson_mut_val* obj, std::vector<DefError>& errors)
        : def_(def), obj_(obj), errors_(errors) {}

    void fail(std::string message) {
        ok_ = false;
        errors_.push_back({def_.mod, std::format("{} '{}': {}", def_.type, def_.id, message)});
    }
    [[nodiscard]] bool ok() const { return ok_; }

    std::int32_t integer(const char* key, std::int32_t min, std::int32_t max, std::int32_t fallback, bool required = false) {
        std::int64_t v = 0;
        const json::Field f = json::get_int(obj_, key, min, max, v);
        if (f == json::Field::Ok) {
            return static_cast<std::int32_t>(v);
        }
        if (f == json::Field::Invalid || required) {
            fail(std::format("\"{}\" must be a whole number from {} to {}", key, min, max));
        }
        return fallback;
    }

    std::string text(const char* key, bool required, std::size_t max = 128) {
        std::string v;
        const json::Field f = json::get_string(obj_, key, max, v);
        if (f == json::Field::Invalid || (required && f == json::Field::Missing)) {
            fail(std::format("\"{}\" must be a text", key));
        }
        return v;
    }

    bool flag(const char* key) {
        bool v = false;
        if (json::get_bool(obj_, key, v) == json::Field::Invalid) {
            fail(std::format("\"{}\" must be true or false", key));
        }
        return v;
    }

    // One of `names`; returns its index.
    template <std::size_t N>
    int choice(const char* key, const std::string_view (&names)[N], int fallback, bool required = false) {
        const char* v = str(obj_, key);
        if (v == nullptr) {
            if (required || yyjson_mut_obj_get(obj_, key) != nullptr) {
                fail(std::format("\"{}\" is required", key));
            }
            return fallback;
        }
        for (std::size_t i = 0; i < N; ++i) {
            if (names[i] == v) {
                return static_cast<int>(i);
            }
        }
        fail(std::format("\"{}\" has an unknown value '{}'", key, v));
        return fallback;
    }

    // A list of choices, as bits.
    template <typename Bits = std::uint8_t, std::size_t N>
    Bits choices(const char* key, const std::string_view (&names)[N]) {
        Bits bits = 0;
        yyjson_mut_val* arr = yyjson_mut_obj_get(obj_, key);
        if (arr == nullptr) {
            return 0;
        }
        if (!yyjson_mut_is_arr(arr)) {
            fail(std::format("\"{}\" must be a list", key));
            return 0;
        }
        std::size_t idx = 0, max = 0;
        yyjson_mut_val* item = nullptr;
        yyjson_mut_arr_foreach(arr, idx, max, item) {
            const char* v = yyjson_mut_get_str(item);
            bool found = false;
            for (std::size_t i = 0; v != nullptr && i < N && i < sizeof(Bits) * 8; ++i) {
                if (names[i] == v) {
                    bits = static_cast<Bits>(bits | (1u << i));
                    found = true;
                }
            }
            if (!found) {
                fail(std::format("\"{}\" has an unknown entry", key));
            }
        }
        return bits;
    }

    // A list of exactly `n` numbers.
    template <typename T>
    void numbers(const char* key, T* out, std::size_t n, std::int32_t min, std::int32_t max) {
        yyjson_mut_val* arr = yyjson_mut_obj_get(obj_, key);
        if (arr == nullptr) {
            return;
        }
        if (!yyjson_mut_is_arr(arr) || yyjson_mut_arr_size(arr) != n) {
            fail(std::format("\"{}\" must be a list of {} numbers", key, n));
            return;
        }
        for (std::size_t i = 0; i < n; ++i) {
            yyjson_mut_val* v = yyjson_mut_arr_get(arr, i);
            if (!yyjson_mut_is_int(v) || yyjson_mut_get_sint(v) < min || yyjson_mut_get_sint(v) > max) {
                fail(std::format("\"{}\" entries must be from {} to {}", key, min, max));
                return;
            }
            out[i] = static_cast<T>(yyjson_mut_get_sint(v));
        }
    }

    // {"id": amount, ...} with ids found by `find`.
    template <typename Find>
    std::vector<std::pair<int, std::int32_t>> table(const char* key, Find find, std::int32_t min, std::int32_t max,
                                                    std::size_t most) {
        std::vector<std::pair<int, std::int32_t>> out;
        yyjson_mut_val* obj = yyjson_mut_obj_get(obj_, key);
        if (obj == nullptr) {
            return out;
        }
        if (!yyjson_mut_is_obj(obj) || yyjson_mut_obj_size(obj) > most) {
            fail(std::format("\"{}\" must be an object with at most {} entries", key, most));
            return out;
        }
        std::size_t idx = 0, max_i = 0;
        yyjson_mut_val* k = nullptr;
        yyjson_mut_val* v = nullptr;
        yyjson_mut_obj_foreach(obj, idx, max_i, k, v) {
            const char* name = yyjson_mut_get_str(k);
            const int found = name != nullptr ? find(name) : -1;
            if (found < 0) {
                fail(std::format("\"{}\" refers to '{}', which does not exist", key, name != nullptr ? name : "?"));
                continue;
            }
            if (!yyjson_mut_is_int(v) || yyjson_mut_get_sint(v) < min || yyjson_mut_get_sint(v) > max) {
                fail(std::format("\"{}\" amounts must be from {} to {}", key, min, max));
                continue;
            }
            out.emplace_back(found, static_cast<std::int32_t>(yyjson_mut_get_sint(v)));
        }
        return out;
    }

    [[nodiscard]] bool has(const char* key) const { return yyjson_mut_obj_get(obj_, key) != nullptr; }

    // "models" as an object of lists by state (a tree species, phase 51):
    // {"bloom": [...], "autumn": [...], "bare": [...]}. The first state is
    // required; each list has 1 to kMaxModelVariants files that must exist.
    // An entry is a file, or {"model": file, "far": file} with its far
    // version (phase 52); `far` gets one entry per file, "" without one.
    void state_models(const std::function<std::filesystem::path(const std::string&)>& mod_dir,
                      const std::string_view* names, std::vector<std::string>* out, std::vector<std::string>* far,
                      std::size_t states, std::vector<ModelRef>* refs, const std::string& name_key) {
        yyjson_mut_val* obj = yyjson_mut_obj_get(obj_, "models");
        if (obj == nullptr || !yyjson_mut_is_obj(obj)) {
            fail("\"models\" of a species must be an object with the files of each state");
            return;
        }
        std::size_t idx = 0, max = 0;
        yyjson_mut_val* k = nullptr;
        yyjson_mut_val* list = nullptr;
        yyjson_mut_obj_foreach(obj, idx, max, k, list) {
            const char* key = yyjson_mut_get_str(k);
            std::size_t state = states;
            for (std::size_t s = 0; s < states && key != nullptr; ++s) {
                if (names[s] == key) {
                    state = s;
                }
            }
            if (state == states) {
                fail(std::format("\"models\" has an unknown state '{}'", key != nullptr ? key : "?"));
                continue;
            }
            if (!yyjson_mut_is_arr(list) || yyjson_mut_arr_size(list) == 0 ||
                yyjson_mut_arr_size(list) > sim::kMaxModelVariants) {
                fail(std::format("\"models\" state '{}' must be a list of 1 to {} files", key, sim::kMaxModelVariants));
                continue;
            }
            std::size_t i = 0, n = 0;
            yyjson_mut_val* item = nullptr;
            yyjson_mut_arr_foreach(list, i, n, item) {
                const bool pair = yyjson_mut_is_obj(item);
                const char* v = pair ? yyjson_mut_get_str(yyjson_mut_obj_get(item, "model")) : yyjson_mut_get_str(item);
                const char* fv = pair ? yyjson_mut_get_str(yyjson_mut_obj_get(item, "far")) : nullptr;
                const std::string rel = v != nullptr ? v : "";
                const std::string far_rel = fv != nullptr ? fv : "";
                if (rel.empty() || rel.size() > 200 || far_rel.size() > 200 ||
                    (pair && (far_rel.empty() || yyjson_mut_obj_size(item) != 2))) {
                    fail("\"models\" entries must be file paths of up to 200 characters, or {\"model\": file, \"far\": file}");
                    continue;
                }
                if (std::find(out[state].begin(), out[state].end(), rel) != out[state].end()) {
                    fail(std::format("\"models\" lists '{}' twice", rel));
                    continue;
                }
                for (const std::string& file : {rel, far_rel}) {
                    if (file.empty()) {
                        continue;
                    }
                    const std::filesystem::path path = mod_file(mod_dir(def_.model_mod), file);
                    std::error_code ec;
                    const bool exists = !path.empty() && std::filesystem::is_regular_file(path, ec);
                    if (!exists) {
                        fail(std::format("model '{}' not found in mod '{}'", file, def_.model_mod));
                    }
                    if (refs != nullptr) {
                        refs->push_back({def_.type, def_.id, name_key, def_.model_mod, file, exists});
                    }
                }
                out[state].push_back(rel);
                far[state].push_back(far_rel);
            }
        }
        if (out[0].empty()) {
            fail(std::format("\"models\" needs the state '{}'", names[0]));
        }
    }

    // A line building's "pieces" (phase 93): an object of model files by
    // piece name; each named file must exist inside the model's mod folder.
    // One more model file of the definition under `key`, which may not be there.
    std::string extra_model(const char* key, const std::function<std::filesystem::path(const std::string&)>& mod_dir,
                            std::vector<ModelRef>* refs, const std::string& name_key) {
        const std::string rel = text(key, false, 200);
        if (rel.empty()) {
            return rel;
        }
        const std::filesystem::path path = mod_file(mod_dir(def_.model_mod), rel);
        std::error_code ec;
        const bool exists = !path.empty() && std::filesystem::is_regular_file(path, ec);
        if (!exists) {
            fail(std::format("model '{}' not found in mod '{}'", rel, def_.model_mod));
        }
        if (refs != nullptr) {
            refs->push_back({def_.type, def_.id, name_key, def_.model_mod, rel, exists});
        }
        return rel;
    }

    void pieces(const std::function<std::filesystem::path(const std::string&)>& mod_dir, std::vector<ModelRef>* refs,
                const std::string& name_key, std::array<std::string, sim::kLinePieces>& out) {
        static constexpr std::string_view kNames[sim::kLinePieces] = {"pillar", "end",      "straight", "corner", "tee",
                                                                      "cross",  "diagonal", "step",     "site",   "breach"};
        yyjson_mut_val* obj = yyjson_mut_obj_get(obj_, "pieces");
        if (obj == nullptr) {
            return;
        }
        if (!yyjson_mut_is_obj(obj)) {
            fail("\"pieces\" must be an object of model files");
            return;
        }
        std::size_t idx = 0, max = 0;
        yyjson_mut_val* k = nullptr;
        yyjson_mut_val* v = nullptr;
        yyjson_mut_obj_foreach(obj, idx, max, k, v) {
            const char* key = yyjson_mut_get_str(k);
            const char* file = yyjson_mut_get_str(v);
            const auto name = std::find(std::begin(kNames), std::end(kNames), std::string_view(key != nullptr ? key : ""));
            const std::string rel = file != nullptr ? file : "";
            if (name == std::end(kNames) || rel.empty() || rel.size() > 200) {
                fail(std::format("\"pieces\" has an unknown piece or a bad file: '{}'", key != nullptr ? key : ""));
                continue;
            }
            const std::filesystem::path path = mod_file(mod_dir(def_.model_mod), rel);
            std::error_code ec;
            const bool exists = !path.empty() && std::filesystem::is_regular_file(path, ec);
            if (!exists) {
                fail(std::format("piece model '{}' not found in mod '{}'", rel, def_.model_mod));
            }
            if (refs != nullptr) {
                refs->push_back({def_.type, def_.id, name_key, def_.model_mod, rel, exists});
            }
            out[static_cast<std::size_t>(name - std::begin(kNames))] = rel;
        }
    }

    // A resource's "pile" (phase 89): the start of the names of its three
    // pile models, "<pile>_1.glb" to "<pile>_3.glb", which must all exist
    // inside the model's mod folder. Returns "" if it has none.
    std::string pile(const std::function<std::filesystem::path(const std::string&)>& mod_dir,
                     std::vector<ModelRef>* refs, const std::string& name_key) {
        const std::string base = text("pile", false, 190);
        if (base.empty()) {
            return base;
        }
        for (int level = 1; level <= sim::kPileLevels; ++level) {
            const std::string rel = sim::pile_file(base, level);
            const std::filesystem::path path = mod_file(mod_dir(def_.model_mod), rel);
            std::error_code ec;
            const bool exists = !path.empty() && std::filesystem::is_regular_file(path, ec);
            if (!exists) {
                fail(std::format("pile model '{}' not found in mod '{}'", rel, def_.model_mod));
            }
            if (refs != nullptr) {
                refs->push_back({def_.type, def_.id, name_key, def_.model_mod, rel, exists});
            }
        }
        return base;
    }

    // The model files: "models", a list of variants (phase 31), or
    // "model", one file. Each must exist inside the model's mod folder.
    // With `refs`, records every file (found or not) under `name_key`.
    // `in_mod`: the mod whose folder holds them, if not the definition's
    // model mod (a building's levels).
    std::vector<std::string> models(const std::function<std::filesystem::path(const std::string&)>& mod_dir,
                                    bool required, std::vector<ModelRef>* refs, const std::string& name_key = {},
                                    const std::string& in_mod = {}) {
        const std::string& mod = in_mod.empty() ? def_.model_mod : in_mod;
        std::vector<std::string> out;
        yyjson_mut_val* list = yyjson_mut_obj_get(obj_, "models");
        if (list != nullptr && yyjson_mut_obj_get(obj_, "model") != nullptr) {
            fail("use \"model\" or \"models\", not both");
            return out;
        }
        if (list == nullptr) {
            const std::string rel = text("model", required, 200);
            if (!rel.empty()) {
                out.push_back(rel);
            }
        } else if (!yyjson_mut_is_arr(list) || yyjson_mut_arr_size(list) == 0 ||
                   yyjson_mut_arr_size(list) > sim::kMaxModelVariants) {
            fail(std::format("\"models\" must be a list of 1 to {} files", sim::kMaxModelVariants));
            return out;
        } else {
            std::size_t idx = 0, max = 0;
            yyjson_mut_val* item = nullptr;
            yyjson_mut_arr_foreach(list, idx, max, item) {
                const char* v = yyjson_mut_get_str(item);
                const std::string rel = v != nullptr ? v : "";
                if (rel.empty() || rel.size() > 200) {
                    fail("\"models\" entries must be file paths of up to 200 characters");
                } else if (std::find(out.begin(), out.end(), rel) != out.end()) {
                    fail(std::format("\"models\" lists '{}' twice", rel));
                } else {
                    out.push_back(rel);
                }
            }
        }
        for (const std::string& rel : out) {
            const std::filesystem::path path = mod_file(mod_dir(mod), rel);
            std::error_code ec;
            const bool exists = !path.empty() && std::filesystem::is_regular_file(path, ec);
            if (!exists) {
                fail(std::format("model '{}' not found in mod '{}'", rel, mod));
            }
            if (refs != nullptr) {
                refs->push_back({def_.type, def_.id, name_key, mod, rel, exists});
            }
        }
        return out;
    }

private:
    const RawDef& def_;
    yyjson_mut_val* obj_ = nullptr;
    std::vector<DefError>& errors_;
    bool ok_ = true;
};

constexpr std::string_view kCategories[] = {"food", "material", "fuel", "good", "gold"};
constexpr std::string_view kWorkKinds[] = {"none", "gather", "produce", "build", "haul",
                                           "farm", "hunt",   "fish",    "explore"};
constexpr std::string_view kBuildingKinds[] = {"house",   "storage", "workplace", "townCenter", "decoration",
                                               "defense", "military", "market"};
constexpr std::string_view kBuildCategories[] = {"housing",  "food",       "resources", "industry",
                                                 "services", "decoration", "defense",   "plaza",
                                                 "garden",   "nature",     "monuments", "ruins"};
constexpr std::string_view kNeeds[] = {"food",   "water",  "clothes", "shoes",  "religion", "entertainment",
                                       "heating", "beauty", "market",  "hygiene", "healer",  "doctor"};
constexpr std::string_view kFeatureKinds[] = {"tree",         "stone",       "ironOre",     "berryBush",   "herbs",
                                              "stoneDeposit", "beeTree",     "nest",        "stump",       "mushroomRing",
                                              "clayDeposit",  "coalDeposit", "goldDeposit", "looseStones",
                                              "fishShoal",    "reedBank",    "ducks"};
static_assert(std::size(kFeatureKinds) == static_cast<std::size_t>(sim::FeatureType::Count));
constexpr std::string_view kSizes[] = {"small", "medium", "large", "huge"};

template <typename T>
int index_of(const std::vector<T>& list, std::string_view id) {
    for (std::size_t i = 0; i < list.size(); ++i) {
        if (list[i].id == id) {
            return static_cast<int>(i);
        }
    }
    return -1;
}

std::vector<sim::ResourceAmount> amounts(const std::vector<std::pair<int, std::int32_t>>& in) {
    std::vector<sim::ResourceAmount> out;
    for (const auto& [r, n] : in) {
        out.push_back({static_cast<sim::DefIndex>(r), n});
    }
    return out;
}

}  // namespace

bool is_valid_def_id(std::string_view id) {
    const std::size_t colon = id.find(':');
    return colon != std::string_view::npos && is_valid_mod_id(id.substr(0, colon)) &&
           valid_name_part(id.substr(colon + 1));
}

RawDef* DefSet::find(std::string_view type, std::string_view id) {
    for (RawDef& d : defs_) {
        if (d.id == id && d.type == type) {
            return &d;
        }
    }
    return nullptr;
}

void DefSet::add_file(std::string_view json_text, const std::string& mod, const std::string& file_name,
                      std::vector<DefError>& errors) {
    json::ParseResult parsed = json::parse_object(json_text);
    if (parsed.error != json::ParseError::None) {
        errors.push_back({mod, std::format("defs/{} is not valid JSON: {}", file_name, parsed.message)});
        return;
    }
    yyjson_mut_val* root = yyjson_mut_doc_get_root(parsed.doc.get());
    std::int64_t schema = 0;
    yyjson_mut_val* list = yyjson_mut_obj_get(root, "defs");
    if (json::get_int(root, "schemaVersion", 1, 1000, schema) != json::Field::Ok || schema != 1 ||
        !yyjson_mut_is_arr(list) || yyjson_mut_arr_size(list) > limits::kMaxDefsPerFile) {
        errors.push_back({mod, std::format("defs/{} needs \"schemaVersion\": 1 and a \"defs\" list", file_name)});
        return;
    }
    std::size_t idx = 0, max = 0;
    yyjson_mut_val* item = nullptr;
    yyjson_mut_arr_foreach(list, idx, max, item) {
        if (!yyjson_mut_is_obj(item)) {
            errors.push_back({mod, std::format("defs/{}: entry {} is not an object", file_name, idx)});
            continue;
        }
        const char* remove = str(item, "remove");
        const char* patch = str(item, "patch");
        const char* type = str(item, "type");
        const char* id = str(item, "id");
        if ((remove != nullptr || patch != nullptr) && (type == nullptr || !known_type(type))) {
            errors.push_back({mod, std::format("defs/{}: entry {} needs its \"type\" to patch or remove", file_name, idx)});
            continue;
        }
        if (remove != nullptr) {
            const auto before = defs_.size();
            std::erase_if(defs_, [&](const RawDef& d) { return d.id == remove && d.type == type; });
            if (defs_.size() == before) {
                errors.push_back({mod, std::format("defs/{}: cannot remove '{}', which does not exist", file_name, remove)});
            }
            continue;
        }
        if (patch != nullptr) {
            RawDef* target = find(type, patch);
            if (target == nullptr) {
                errors.push_back({mod, std::format("defs/{}: cannot patch '{}', which does not exist", file_name, patch)});
                continue;
            }
            // Replace each given field; "patch" and "type" are not copied.
            std::size_t pi = 0, pmax = 0;
            yyjson_mut_val* k = nullptr;
            yyjson_mut_val* v = nullptr;
            yyjson_mut_obj_foreach(item, pi, pmax, k, v) {
                const char* key = yyjson_mut_get_str(k);
                if (key == nullptr || std::string_view(key) == "patch" || std::string_view(key) == "type" ||
                    std::string_view(key) == "id") {
                    continue;
                }
                (void)yyjson_mut_obj_remove_key(target->obj, key);
                // "model" and "models" are two forms of one field.
                if (std::string_view(key) == "model" || std::string_view(key) == "models") {
                    (void)yyjson_mut_obj_remove_key(target->obj, std::string_view(key) == "model" ? "models" : "model");
                }
                yyjson_mut_val* copy = yyjson_mut_val_mut_copy(target->doc.get(), v);
                yyjson_mut_val* kc = yyjson_mut_strcpy(target->doc.get(), key);
                if (copy != nullptr && kc != nullptr) {
                    (void)yyjson_mut_obj_add(target->obj, kc, copy);
                }
                // A resource's "pile" and a wall's "pieces" name model files too.
                if (std::string_view(key) == "model" || std::string_view(key) == "models" ||
                    std::string_view(key) == "pile" || std::string_view(key) == "pieces") {
                    target->model_mod = mod;
                }
                if (std::string_view(key) == "levels") {
                    target->levels_model_mod = mod;
                }
            }
            target->mod = mod;
            continue;
        }
        if (type == nullptr || !known_type(type)) {
            errors.push_back({mod, std::format("defs/{}: entry {} has no known \"type\"", file_name, idx)});
            continue;
        }
        if (id == nullptr || !is_valid_def_id(id) || std::string_view(id).substr(0, std::string_view(id).find(':')) != mod) {
            errors.push_back({mod, std::format("defs/{}: \"id\" must be \"{}:name\" (a-z, 0-9, _)", file_name, mod)});
            continue;
        }
        if (find(type, id) != nullptr) {
            errors.push_back({mod, std::format("defs/{}: '{}' is defined twice", file_name, id)});
            continue;
        }
        if (defs_.size() >= kMaxDefs) {
            errors.push_back({mod, "too many definitions"});
            return;
        }
        RawDef def;
        def.type = type;
        def.id = id;
        def.doc = json::MutDoc(yyjson_mut_doc_new(nullptr));
        def.obj = def.doc ? yyjson_mut_val_mut_copy(def.doc.get(), item) : nullptr;
        if (def.obj == nullptr) {
            errors.push_back({mod, "out of memory"});
            return;
        }
        yyjson_mut_doc_set_root(def.doc.get(), def.obj);
        def.mod = mod;
        def.model_mod = mod;
        def.levels_model_mod = mod;
        defs_.push_back(std::move(def));
    }
}

void build_content(const DefSet& set, const std::function<std::filesystem::path(const std::string&)>& mod_dir,
                   sim::Content& out, std::vector<DefError>& errors, std::vector<ModelRef>* refs) {
    out = sim::Content{};
    // Ids first, so definitions can refer to each other in any order.
    std::vector<const RawDef*> resources, features, buildings, recipes, species, biomes, crops, diseases, units,
        tutorials, races, herds;
    for (const RawDef& d : set.defs()) {
        if (d.type == "resource") resources.push_back(&d);
        else if (d.type == "mapFeature") features.push_back(&d);
        else if (d.type == "building") buildings.push_back(&d);
        else if (d.type == "recipe") recipes.push_back(&d);
        else if (d.type == "species") species.push_back(&d);
        else if (d.type == "biome") biomes.push_back(&d);
        else if (d.type == "crop") crops.push_back(&d);
        else if (d.type == "disease") diseases.push_back(&d);
        else if (d.type == "unit") units.push_back(&d);
        else if (d.type == "tutorial") tutorials.push_back(&d);
        else if (d.type == "race") races.push_back(&d);
        else if (d.type == "herd") herds.push_back(&d);
    }
    if (species.size() > sim::kMaxSpecies || biomes.size() > sim::kMaxBiomes ||
        resources.size() > 1000 || buildings.size() > 1000 || recipes.size() > 2000) {
        errors.push_back({"", "too many definitions of one type"});
        return;
    }
    // Resources.
    for (const RawDef* d : resources) {
        Reader r(*d, errors);
        sim::ResourceDef def;
        def.id = d->id;
        def.name_key = r.text("name", true);
        def.category = static_cast<sim::ResourceCategory>(r.choice("category", kCategories, 1, true));
        def.nutrition = r.integer("nutrition", 0, 1000, 0);
        def.value = r.integer("value", 0, 10000, 0);
        def.sell_only = r.flag("sellOnly");
        def.bad_percent = r.integer("badPercent", 0, 100, 0);
        def.weight = r.integer("weight", 1, 12, 1);
        def.carry = r.integer("carry", 0, 1000, 0);
        // "load": "crate", "logs", "stone", "sack" or "basket".
        static constexpr std::string_view kLoads[] = {"crate", "logs", "stone", "sack", "basket"};
        def.load = static_cast<sim::LoadKind>(
            r.choice("load", kLoads, def.category == sim::ResourceCategory::Food ? 4 : 0));
        def.pile = r.pile(mod_dir, refs, def.name_key);
        def.mod = d->model_mod;
        if (r.ok()) {
            out.resources.push_back(std::move(def));
        }
    }
    const auto find_resource = [&](std::string_view id) { return index_of(out.resources, id); };
    // Recipes (buildings refer to them).
    for (const RawDef* d : recipes) {
        Reader r(*d, errors);
        sim::RecipeDef def;
        def.id = d->id;
        def.inputs = amounts(r.table("inputs", find_resource, 1, 1000, 8));
        def.outputs = amounts(r.table("outputs", find_resource, 1, 1000, 8));
        def.work = r.integer("work", 1, 100000, 50);
        if (def.outputs.empty()) {
            r.fail("\"outputs\" needs at least one resource");
        }
        if (r.ok()) {
            out.recipes.push_back(std::move(def));
        }
    }
    const auto find_recipe = [&](std::string_view id) { return index_of(out.recipes, id); };
    // Races.
    for (const RawDef* d : races) {
        Reader r(*d, errors);
        sim::RaceDef def;
        def.id = d->id;
        def.name_key = r.text("name", true);
        // "bodies": {"male": [...], "female": [...]}: plain file names of
        // characters in core. A missing file is only left out of the
        // crowd, so it is not an error here.
        yyjson_mut_val* bodies = yyjson_mut_obj_get(d->obj, "bodies");
        if (bodies == nullptr || !yyjson_mut_is_obj(bodies)) {
            r.fail("\"bodies\" must be an object with the lists \"male\" and \"female\"");
        } else {
            for (const bool female : {false, true}) {
                yyjson_mut_val* list = yyjson_mut_obj_get(bodies, female ? "female" : "male");
                if (list == nullptr) {
                    continue;
                }
                if (!yyjson_mut_is_arr(list) || yyjson_mut_arr_size(list) > sim::kMaxRaceBodies) {
                    r.fail("a list of \"bodies\" must have at most 8 file names");
                    continue;
                }
                std::size_t idx = 0, max = 0;
                yyjson_mut_val* item = nullptr;
                yyjson_mut_arr_foreach(list, idx, max, item) {
                    const char* text = yyjson_mut_get_str(item);
                    const std::string name = text != nullptr ? text : "";
                    if (name.empty() || name.size() > 32 || !std::all_of(name.begin(), name.end(), [](char c) {
                            return (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '_';
                        })) {
                        r.fail("a body must be a plain file name ([a-z0-9_])");
                        continue;
                    }
                    (female ? def.bodies_female : def.bodies_male).push_back(name);
                    if (refs != nullptr) {
                        const std::string rel = sim::race_body_file(name);
                        const std::filesystem::path path = mod_file(mod_dir(kCoreModId), rel);
                        std::error_code ec;
                        refs->push_back({d->type, d->id, def.name_key, kCoreModId, rel,
                                         !path.empty() && std::filesystem::is_regular_file(path, ec)});
                        // Its far version, when it has one.
                        const std::string far_rel = sim::race_body_file(name + "_far");
                        const std::filesystem::path far_path = mod_file(mod_dir(kCoreModId), far_rel);
                        if (!far_path.empty() && std::filesystem::is_regular_file(far_path, ec)) {
                            refs->push_back({d->type, d->id, def.name_key, kCoreModId, far_rel, true});
                        }
                    }
                }
            }
            if (def.bodies_male.empty() && def.bodies_female.empty()) {
                r.fail("\"bodies\" names no character");
            }
        }
        // "skins" and "hairs": lists of "#rrggbb".
        const auto colors = [&](const char* key, std::vector<std::uint32_t>& out) {
            yyjson_mut_val* list = yyjson_mut_obj_get(d->obj, key);
            if (list == nullptr) {
                return;
            }
            if (!yyjson_mut_is_arr(list) || yyjson_mut_arr_size(list) > sim::kMaxRaceColors) {
                r.fail(std::format("\"{}\" must be a list of at most 12 colors", key));
                return;
            }
            std::size_t idx = 0, max = 0;
            yyjson_mut_val* item = nullptr;
            yyjson_mut_arr_foreach(list, idx, max, item) {
                const char* text = yyjson_mut_get_str(item);
                const std::string_view hex = text != nullptr ? text : "";
                std::uint32_t value = 0;
                bool ok = hex.size() == 7 && hex[0] == '#';
                for (std::size_t k = 1; ok && k < 7; ++k) {
                    const char c = hex[k];
                    const int digit = c >= '0' && c <= '9' ? c - '0' : c >= 'a' && c <= 'f' ? c - 'a' + 10
                                    : c >= 'A' && c <= 'F' ? c - 'A' + 10 : -1;
                    ok = digit >= 0;
                    value = value * 16u + static_cast<std::uint32_t>(std::max(digit, 0));
                }
                if (!ok) {
                    r.fail(std::format("a color of \"{}\" must be \"#rrggbb\"", key));
                    return;
                }
                out.push_back(value);
            }
        };
        colors("skins", def.skins);
        colors("hairs", def.hairs);
        // "names": {"male": [...], "female": [...]}: what its villagers are called.
        if (yyjson_mut_val* names = yyjson_mut_obj_get(d->obj, "names"); names != nullptr) {
            if (!yyjson_mut_is_obj(names)) {
                r.fail("\"names\" must be an object with the lists \"male\" and \"female\"");
            } else {
                for (const bool female : {false, true}) {
                    yyjson_mut_val* list = yyjson_mut_obj_get(names, female ? "female" : "male");
                    if (list == nullptr) {
                        continue;
                    }
                    if (!yyjson_mut_is_arr(list) || yyjson_mut_arr_size(list) > sim::kMaxRaceNames) {
                        r.fail("a list of \"names\" must have at most 64 names");
                        continue;
                    }
                    std::size_t idx = 0, max = 0;
                    yyjson_mut_val* item = nullptr;
                    yyjson_mut_arr_foreach(list, idx, max, item) {
                        const char* text = yyjson_mut_get_str(item);
                        const std::string name = text != nullptr ? text : "";
                        if (name.empty() || !sim::valid_villager_name(name)) {
                            r.fail("a name must be 1 to 24 bytes of plain text");
                            continue;
                        }
                        (female ? def.names_female : def.names_male).push_back(name);
                    }
                }
            }
        }
        def.move = r.integer("move", 50, 200, 100);
        def.cold = r.integer("cold", -100, 90, 0);
        def.disease = r.integer("disease", -100, 90, 0);
        def.night_vision = r.flag("nightVision");
        def.likes_cats = r.flag("likesCats");
        def.lanterns = r.flag("lanterns");
        // Phase 116: the body of its soldiers, one of those it has for that sex.
        def.soldier_male = r.text("soldierMale", false);
        def.soldier_female = r.text("soldierFemale", false);
        const auto one_of = [](const std::string& name, const std::vector<std::string>& bodies) {
            return name.empty() || std::find(bodies.begin(), bodies.end(), name) != bodies.end();
        };
        if (!one_of(def.soldier_male, def.bodies_male) || !one_of(def.soldier_female, def.bodies_female)) {
            r.fail("\"soldierMale\" and \"soldierFemale\" must be among the \"bodies\" of that sex");
        }
        def.sight = r.integer("sight", 1, sim::kMaxSight, 12);
        if (yyjson_mut_val* work = yyjson_mut_obj_get(d->obj, "work"); work != nullptr) {
            if (!yyjson_mut_is_obj(work)) {
                r.fail("\"work\" must be an object of skill: percent");
            } else {
                Reader wr(*d, work, errors);
                for (std::size_t k = 0; k < std::size(kSkillNames); ++k) {
                    def.work[k] = wr.integer(std::string(kSkillNames[k]).c_str(), 25, 300, 100);
                }
                if (!wr.ok()) {
                    r.fail("a work speed has errors");
                }
            }
        }
        if (r.ok() && out.races.size() < 16) {
            out.races.push_back(std::move(def));
        }
    }
    // Tutorials.
    for (const RawDef* d : tutorials) {
        Reader r(*d, errors);
        sim::TutorialDef def;
        def.id = d->id;
        def.mod = d->mod;
        def.name_key = r.text("name", true);
        def.seed = r.integer("seed", 1, 2000000000, 1);
        def.size = static_cast<std::uint8_t>(r.choice("size", kTutorialSizes, 0));
        if (yyjson_mut_val* steps = yyjson_mut_obj_get(d->obj, "steps");
            steps == nullptr || !yyjson_mut_is_arr(steps) || yyjson_mut_arr_size(steps) == 0 ||
            yyjson_mut_arr_size(steps) > 40) {
            r.fail("\"steps\" must be a list of 1 to 40 objects");
        } else {
            std::size_t si = 0, smax = 0;
            yyjson_mut_val* item = nullptr;
            yyjson_mut_arr_foreach(steps, si, smax, item) {
                if (!yyjson_mut_is_obj(item)) {
                    r.fail("\"steps\" entries must be objects");
                    continue;
                }
                Reader sr(*d, item, errors);
                sim::TutorialStep step;
                step.text_key = sr.text("text", true);
                step.goal = static_cast<sim::TutorialGoal>(sr.choice("goal", kTutorialGoals, 0));
                step.target = sr.text("target", false, 64);
                step.amount = sr.integer("amount", 1, 100000, 1);
                step.highlight = sr.text("highlight", false, 64);
                if (!sr.ok()) {
                    r.fail("a step has errors");
                }
                def.steps.push_back(std::move(step));
            }
        }
        if (r.ok() && out.tutorials.size() < 16) {
            out.tutorials.push_back(std::move(def));
        }
    }
    // Units.
    for (const RawDef* d : units) {
        Reader r(*d, errors);
        sim::UnitDef def;
        def.id = d->id;
        def.name_key = r.text("name", true);
        def.health = r.integer("health", 1, 100000, 500);
        def.damage = r.integer("damage", 0, 10000, 50);
        def.attack_every = r.integer("attackEvery", 1, 1000, 10);
        def.range = r.integer("range", 1, 60, 2);
        def.speed = r.integer("speed", 5, 60, 21);
        def.cost = amounts(r.table("cost", find_resource, 1, 1000, 8));
        def.train_work = r.integer("trainWork", 1, 100000, 300);
        def.power = r.integer("power", 0, 1000, 1);
        def.tier = static_cast<std::uint8_t>(r.integer("tier", 0, 10, 0));
        def.sight = r.integer("sight", 1, sim::kMaxSight, 16);
        static constexpr std::string_view kUnitWeapons[] = {"none", "club", "spear", "bow"};
        static_assert(std::size(kUnitWeapons) == static_cast<std::size_t>(sim::UnitWeapon::Count));
        def.weapon = static_cast<sim::UnitWeapon>(r.choice("weapon", kUnitWeapons, 0));
        def.shield = r.flag("shield");
        if (r.ok() && out.units.size() < 64) {
            out.units.push_back(std::move(def));
        }
    }
    // Diseases.
    for (const RawDef* d : diseases) {
        Reader r(*d, errors);
        sim::DiseaseDef def;
        def.id = d->id;
        def.name_key = r.text("name", true);
        def.source = static_cast<sim::DiseaseSource>(r.choice("source", kDiseaseSources, 0, true));
        def.chance = r.integer("chance", 0, 10000, 20);
        def.contagion = r.integer("contagion", 0, 1000, 20);
        def.severity = r.integer("severity", 0, 1000, 60);
        def.days = r.integer("days", 1, 365, 8);
        if (r.ok() && out.diseases.size() < 32) {
            out.diseases.push_back(std::move(def));
        }
    }
    // Crops.
    for (const RawDef* d : crops) {
        Reader r(*d, errors);
        sim::CropDef def;
        def.id = d->id;
        def.name_key = r.text("name", true);
        const std::string res = r.text("resource", true);
        const int ri = find_resource(res);
        if (ri < 0) {
            r.fail(std::format("\"resource\" '{}' does not exist", res));
        }
        def.resource = static_cast<sim::DefIndex>(ri < 0 ? 0 : ri);
        def.yield = r.integer("yield", 1, 1000, 10);
        def.grow_days = r.integer("growDays", 1, 1000, 40);
        def.fertility = r.integer("fertility", -100, 100, -10);
        def.hardy = r.flag("hardy");
        def.rabbits = r.flag("rabbitsEat");
        def.models = r.models(mod_dir, false, refs, def.name_key);
        def.mod = d->model_mod;
        if (!def.models.empty() && def.models.size() != sim::kCropStages) {
            r.fail("\"models\" must list the crop's three stages: sprouts, green and ripe");
        }
        def.sways = r.flag("sways");
        if (r.ok() && out.crops.size() < 250) {
            out.crops.push_back(std::move(def));
        }
    }
    // Herds (phase 107).
    for (const RawDef* d : herds) {
        Reader r(*d, errors);
        sim::HerdDef def;
        def.id = d->id;
        def.name_key = r.text("name", true);
        def.start = r.integer("start", 1, 50, 3);
        def.start_male = !r.flag("noMale");
        def.area = r.integer("area", 1, 1000, 40);
        def.most = r.integer("most", 1, 200, 16);
        def.male_price = r.integer("malePrice", 0, 10000, 30);
        def.spring = amounts(r.table("spring", find_resource, 1, 1000, 4));
        def.cull = amounts(r.table("cull", find_resource, 1, 1000, 4));
        def.gives = amounts(r.table("gives", find_resource, 1, 1000, 4));
        def.gives_days = r.integer("givesDays", 1, 365, 8);
        def.steep = r.integer("steep", 50, 1000, 300);
        static constexpr std::string_view kHerdLooks[] = {"sheep", "goat"};
        def.look = static_cast<std::uint8_t>(r.choice("look", kHerdLooks, 0));
        if (def.start + (def.start_male ? 1 : 0) > def.most) {
            r.fail("a herd starts with no more than its \"most\"");
        }
        if (r.ok() && out.herds.size() < 250) {
            out.herds.push_back(std::move(def));
        }
    }
    // Map features.
    for (const RawDef* d : features) {
        Reader r(*d, errors);
        sim::FeatureDef def;
        def.id = d->id;
        def.kind = static_cast<sim::FeatureKind>(r.choice("kind", kFeatureKinds, 0, true));
        const std::string res = r.text("resource", true);
        const int ri = find_resource(res);
        if (ri < 0) {
            r.fail(std::format("\"resource\" '{}' does not exist", res));
        }
        def.resource = static_cast<sim::DefIndex>(ri < 0 ? 0 : ri);
        def.amount = r.integer("amount", 1, 10000, 10);
        def.work = r.integer("work", 1, 10000, 20);
        def.regrow_days = r.integer("regrowDays", 0, 3650, 0);
        def.seasons = r.choices("seasons", kSeasons);
        def.after_rain = r.flag("afterRain");
        if (def.after_rain && def.seasons == 0) {
            r.fail("\"afterRain\" needs \"seasons\"");
        }
        if (def.seasons != 0 && (def.regrow_days != 0 || def.kind == sim::FeatureKind::Tree || sim::is_deposit(def.kind))) {
            r.fail("what gives by \"seasons\" does not regrow, and is not a tree or a deposit");
        }
        def.landmark = r.flag("landmark");
        def.loose = r.flag("loose");
        if (def.loose && (def.seasons != 0 || def.regrow_days != 0 || def.kind == sim::FeatureKind::Tree || sim::is_deposit(def.kind))) {
            r.fail("what lies \"loose\" does not regrow or give by seasons, and is not a tree or a deposit");
        }
        def.rock_of_biome = r.flag("rockOfBiome");
        // Features have no name of their own: the viewer shows the resource's.
        def.models = r.models(mod_dir, false, refs,
                              ri < 0 ? std::string{} : out.resources[static_cast<std::size_t>(ri)].name_key);
        def.model_green = r.extra_model("green", mod_dir, refs,
                                        ri < 0 ? std::string{} : out.resources[static_cast<std::size_t>(ri)].name_key);
        def.model_flower = r.extra_model("flower", mod_dir, refs,
                                         ri < 0 ? std::string{} : out.resources[static_cast<std::size_t>(ri)].name_key);
        def.mod = d->model_mod;
        if (r.ok()) {
            out.features.push_back(std::move(def));
        }
    }
    // Buildings.
    std::size_t road_kinds = 0;
    std::size_t annexes = 0;
    for (const RawDef* d : buildings) {
        Reader r(*d, errors);
        sim::BuildingDef def;
        def.id = d->id;
        def.name_key = r.text("name", true);
        def.mod = d->model_mod;
        def.models = r.models(mod_dir, true, refs, def.name_key);
        def.kind = static_cast<sim::BuildingKind>(r.choice("kind", kBuildingKinds, 2, true));
        std::int32_t size[2] = {4, 4};
        r.numbers("size", size, 2, 1, 32);
        def.width = size[0];
        def.depth = size[1];
        def.cost = amounts(r.table("cost", find_resource, 1, 10000, 8));
        def.build_work = r.integer("buildWork", 0, 100000, 100);
        def.workers = r.integer("workers", 0, 50, 0);
        def.work = static_cast<sim::WorkKind>(r.choice("work", kWorkKinds, 0));
        def.gathers = r.choices<std::uint16_t>("gathers", kFeatureKinds);
        def.work_radius = r.integer("radius", 0, 500, 0);
        def.picks_fruit = r.flag("picksFruit");
        def.residents = r.integer("residents", 0, 50, 0);
        def.storage = r.integer("storage", 0, 100000, 0);
        def.stores = r.choices("stores", kCategories);
        yyjson_mut_val* list = yyjson_mut_obj_get(d->obj, "recipes");
        if (list != nullptr) {
            std::size_t i = 0, max = 0;
            yyjson_mut_val* item = nullptr;
            yyjson_mut_arr_foreach(list, i, max, item) {
                const char* id = yyjson_mut_get_str(item);
                const int ri = id != nullptr ? find_recipe(id) : -1;
                if (ri < 0) {
                    r.fail("\"recipes\" refers to a recipe that does not exist");
                } else {
                    def.recipes.push_back(static_cast<sim::DefIndex>(ri));
                }
            }
        }
        def.tier = r.integer("tier", 0, 10, 0);
        def.desirability = r.integer("desirability", -100, 100, 0);
        def.unique = r.flag("unique");
        def.fireproof = r.flag("fireproof");
        def.trade = r.flag("trade");
        def.hp = r.integer("hp", 1, 100000, 500);
        def.gate = r.flag("gate");
        def.trap = r.flag("trap");
        def.attack_range = r.integer("attackRange", 0, 200, 0);
        def.attack_damage = r.integer("attackDamage", 0, 10000, 0);
        def.attack_every = r.integer("attackEvery", 1, 1000, 20);
        def.sight = r.integer("sight", 1, sim::kMaxSight, 12);
        def.landmark = r.flag("landmark");
        def.trains = r.flag("trains");
        def.worker_sight = r.integer("workerSight", 0, sim::kMaxSight, 0);
        def.warmth = r.integer("warmth", 0, 100, 0);
        def.light = r.integer("light", 0, sim::kMaxLight, 0);
        def.cool_light = r.flag("coolLight");
        def.wards = r.flag("wardsBeasts");
        if (def.wards && def.light <= 0) {
            r.fail("\"wardsBeasts\" needs a \"light\"");
        }
        def.cart = r.flag("cart");
        // Phase 93: walls and the like, placed in lines.
        def.line = r.text("line", false, 32);
        def.line_diagonal = r.flag("diagonal");
        r.pieces(mod_dir, refs, def.name_key, def.line_pieces);
        if (def.line.empty() && (def.line_diagonal || std::any_of(def.line_pieces.begin(), def.line_pieces.end(),
                                                                  [](const std::string& p) { return !p.empty(); }))) {
            r.fail("\"diagonal\" and \"pieces\" need a \"line\"");
        }
        // Phase 94: hedges.
        def.desirability_radius = r.integer("desirabilityRadius", 0, 30, 0);
        def.yields = amounts(r.table("yields", find_resource, 1, 1000, 4));
        def.yield_per = r.integer("yieldPer", 1, 1000, 1);
        if (!def.yields.empty() && def.line.empty()) {
            r.fail("\"yields\" needs a \"line\"");
        }
        // Phase 95: roads.
        def.road = r.integer("road", 0, 200, 0);
        def.road_eraser = r.flag("roadEraser");
        def.road_desirability = r.integer("roadDesirability", 0, 100, 0);
        def.road_muddy = r.flag("muddy");
        if (def.road_muddy && def.road <= 0) {
            r.fail("\"muddy\" needs a \"road\"");
        }
        if (def.road != 0 && def.road <= 100) {
            r.fail("\"road\" is how fast people walk on it, percent: more than 100");
        }
        if (def.road > 0 || def.road_eraser) {
            if (def.line.empty() || def.width != sim::kRoadModule || def.depth != sim::kRoadModule || def.gate || def.trap ||
                def.line_diagonal || (def.road > 0 && def.road_eraser)) {
                r.fail("a road is a \"line\" of 2 x 2, without diagonals, and not a gate or a trap");
            }
            if (def.road > 0 && ++road_kinds > sim::kMaxRoadKinds) {
                r.fail("too many kinds of road");
            }
        } else if (def.road_desirability != 0) {
            r.fail("\"roadDesirability\" needs a \"road\"");
        }
        def.seasons = r.choices("seasons", kSeasons);
        def.mature_years = r.integer("matureYears", 0, 50, 0);
        def.yearly_limit = r.integer("yearlyLimit", 0, 100000, 0);
        def.fields = r.integer("fields", 0, 16, 0);
        // Upgrades.
        if (yyjson_mut_val* levels = yyjson_mut_obj_get(d->obj, "levels"); levels != nullptr) {
            if (!yyjson_mut_is_arr(levels) || yyjson_mut_arr_size(levels) > 8) {
                r.fail("\"levels\" must be a list of at most 8 objects");
            } else {
                std::size_t li = 0, lmax = 0;
                yyjson_mut_val* item = nullptr;
                yyjson_mut_arr_foreach(levels, li, lmax, item) {
                    if (!yyjson_mut_is_obj(item)) {
                        r.fail("\"levels\" entries must be objects");
                        continue;
                    }
                    Reader lr(*d, item, errors);
                    sim::LevelDef level;
                    level.residents = lr.integer("residents", 0, 50, 0);
                    level.cost = amounts(lr.table("cost", find_resource, 1, 10000, 8));
                    level.work = lr.integer("work", 0, 100000, 200);
                    level.needs = lr.choices<std::uint16_t>("needs", kNeeds);
                    level.tier = lr.integer("tier", 0, 10, 0);
                    level.population = lr.integer("population", 0, 100000, 0);
                    // Its own look (phase 31); none: the building's.
                    level.models = lr.models(mod_dir, false, refs, def.name_key, d->levels_model_mod);
                    level.models_mod = d->levels_model_mod;
                    if (!lr.ok()) {
                        r.fail("a level has errors");
                    }
                    def.levels.push_back(std::move(level));
                }
            }
        }
        // Service to the homes nearby.
        const int service = r.choice("service", kNeeds, -1);
        def.service = service < 0 ? sim::kNoNeed : static_cast<std::uint8_t>(service);
        def.service_radius = r.integer("serviceRadius", 0, 500, 0);
        def.service_uses = amounts(r.table("serviceUses", find_resource, 1, 1000, 4));
        def.service_any = r.flag("serviceUsesAny");
        if (def.service_any && def.service_uses.empty()) {
            r.fail("\"serviceUsesAny\" needs \"serviceUses\"");
        }
        def.model_winter = r.extra_model("winterModel", mod_dir, refs, def.name_key);
        // Phase 107: folds.
        def.pasture_fence = r.text("pastureFence", false);
        if (yyjson_mut_val* kinds = yyjson_mut_obj_get(d->obj, "herds"); kinds != nullptr) {
            std::size_t i = 0, max = 0;
            yyjson_mut_val* item = nullptr;
            yyjson_mut_arr_foreach(kinds, i, max, item) {
                const char* id = yyjson_mut_get_str(item);
                const int hi = id != nullptr ? index_of(out.herds, id) : -1;
                if (hi < 0) {
                    r.fail("\"herds\" refers to a herd that does not exist");
                } else if (def.herds.size() < 8) {
                    def.herds.push_back(static_cast<sim::DefIndex>(hi));
                }
            }
            if (def.kind != sim::BuildingKind::Workplace || def.storage <= 0 || def.work_radius <= 0 ||
                def.work != sim::WorkKind::None || !def.recipes.empty()) {
                r.fail("a building with \"herds\" is a workplace with \"storage\" and a \"radius\", and no other work");
            }
        }
        // Phase 105: coops and guards.
        if (const std::string eggs = r.text("coopGives", false); !eggs.empty()) {
            const int ei = find_resource(eggs);
            if (ei < 0) {
                r.fail(std::format("\"coopGives\" '{}' does not exist", eggs));
            } else if (def.kind != sim::BuildingKind::Decoration || def.storage <= 0 || def.workers > 0) {
                r.fail("\"coopGives\" is for a decoration with \"storage\" and no workers");
            } else {
                def.coop_gives = static_cast<sim::DefIndex>(ei);
            }
        }
        def.coop_hens = r.integer("coopHens", 1, 20, 4);
        def.coop_days = r.integer("coopDays", 1, 100, 3);
        def.coop_feed_days = r.integer("coopFeedDays", 1, 100, 6);
        for (const sim::ResourceAmount& feed : amounts(r.table("coopFeed", find_resource, 1, 1, 4))) {
            def.coop_feed.push_back(feed.resource);
        }
        if (def.coop_gives != sim::kNoDef && def.coop_feed.empty()) {
            r.fail("\"coopGives\" needs \"coopFeed\": what the hens eat");
        }
        def.guard_radius = r.integer("guardRadius", 0, 60, 0);
        // Phase 111: the weapons of a hunters' lodge.
        if (const std::string arms = r.text("huntArms", false); !arms.empty()) {
            const int ai = find_resource(arms);
            if (ai < 0) {
                r.fail(std::format("\"huntArms\" '{}' does not exist", arms));
            } else if (def.work != sim::WorkKind::Hunt || def.storage <= 0) {
                r.fail("\"huntArms\" is for a workplace that hunts, with \"storage\"");
            } else {
                def.hunt_arms = static_cast<sim::DefIndex>(ai);
            }
        }
        // Phase 104: gardens and hives.
        def.garden_modules = r.integer("gardenModules", 0, 100, 0);
        def.garden_house = r.flag("houseGarden");
        def.garden_desirability = r.integer("gardenDesirability", 0, 50, 0);
        def.garden_gives = amounts(r.table("gardenGives", find_resource, 1, 1000, 4));
        def.garden_formal = r.flag("formalGarden");
        if (def.garden_modules > 0 && (def.line.empty() || def.garden_house == def.garden_formal)) {
            r.fail("\"gardenModules\" is for a line, with either \"houseGarden\" or \"formalGarden\"");
        }
        if (def.garden_modules == 0 &&
            (def.garden_house || def.garden_formal || def.garden_desirability != 0 || !def.garden_gives.empty())) {
            r.fail("\"houseGarden\", \"formalGarden\", \"gardenDesirability\" and \"gardenGives\" need \"gardenModules\"");
        }
        if (const std::string honey = r.text("hiveGives", false); !honey.empty()) {
            const int hi = find_resource(honey);
            if (hi < 0) {
                r.fail(std::format("\"hiveGives\" '{}' does not exist", honey));
            } else if (def.kind != sim::BuildingKind::Decoration || def.storage <= 0 || def.workers > 0) {
                r.fail("\"hiveGives\" is for a decoration with \"storage\" and no workers");
            } else {
                def.hive_gives = static_cast<sim::DefIndex>(hi);
            }
        }
        def.hive_radius = r.integer("hiveRadius", 1, 60, 30);
        // Phase 103: annexes.
        def.annex = r.flag("annex");
        def.annex_radius = r.integer("annexRadius", 1, 60, 3);
        def.annex_desirability = r.integer("annexDesirability", -50, 50, 0);
        def.annex_need = static_cast<std::uint8_t>(r.choice("annexNeed", kNeeds, sim::kNoNeed));
        def.annex_happiness = r.integer("annexHappiness", -50, 50, 0);
        def.annex_children = r.flag("annexChildren");
        def.annex_rain = r.flag("annexRain");
        def.annex_firewood = r.integer("annexFirewood", 0, 1000, 0);
        if (def.annex) {
            if (def.kind != sim::BuildingKind::Decoration || def.workers > 0 || def.residents > 0 || !def.line.empty() ||
                def.road > 0) {
                r.fail("an \"annex\" is a decoration: no workers, residents, line or road");
            }
            if (annexes >= sim::kMaxAnnexes) {
                r.fail(std::format("too many annexes (the most is {})", sim::kMaxAnnexes));
            } else {
                def.annex_bit = static_cast<std::int8_t>(annexes++);
            }
        } else if (def.annex_desirability != 0 || def.annex_need != sim::kNoNeed || def.annex_happiness != 0 || def.annex_children ||
                   def.annex_rain || def.annex_firewood != 0) {
            r.fail("\"annexDesirability\", \"annexNeed\", \"annexHappiness\", \"annexChildren\", \"annexRain\" and "
                   "\"annexFirewood\" need \"annex\"");
        }
        // The build bar's group: given, or from what the building is.
        auto category = sim::BuildCategory::Industry;
        switch (def.kind) {
            case sim::BuildingKind::House: category = sim::BuildCategory::Housing; break;
            case sim::BuildingKind::Storage:
            case sim::BuildingKind::Market:
            case sim::BuildingKind::TownCenter: category = sim::BuildCategory::Services; break;
            case sim::BuildingKind::Decoration: category = sim::BuildCategory::Decoration; break;
            case sim::BuildingKind::Defense: category = sim::BuildCategory::Defense; break;
            default:
                if (def.work == sim::WorkKind::Gather) {
                    category = sim::BuildCategory::Resources;
                } else if (def.work == sim::WorkKind::Farm || def.work == sim::WorkKind::Hunt ||
                           def.work == sim::WorkKind::Fish) {
                    category = sim::BuildCategory::Food;
                } else if (def.service != sim::kNoNeed) {
                    category = sim::BuildCategory::Services;
                }
                break;
        }
        static_assert(kBuildCategories[sim::kPlazaCategory] == "plaza");
        static_assert(kBuildCategories[sim::kGardenCategory] == "garden");
        static_assert(kBuildCategories[sim::kNatureCategory] == "nature");
        def.category = static_cast<std::uint8_t>(r.choice("category", kBuildCategories, static_cast<int>(category)));
        if (def.work == sim::WorkKind::Farm && def.fields == 0) {
            r.fail("a farm needs \"fields\"");
        }
        if (def.work == sim::WorkKind::Gather && def.gathers == 0) {
            r.fail("gathering needs \"gathers\"");
        }
        if (def.work == sim::WorkKind::Produce && def.recipes.empty()) {
            r.fail("producing needs \"recipes\"");
        }
        if (r.ok()) {
            out.buildings.push_back(std::move(def));
        }
    }
    // Species.
    std::vector<std::string> giant_biomes;  // One per species kept.
    for (const RawDef* d : species) {
        Reader r(*d, errors);
        sim::SpeciesDef def;
        def.id = d->id;
        def.name_key = r.text("name", true);
        def.mod = d->model_mod;
        def.sizes = r.choices("sizes", kSizes);
        if (def.sizes == 0) {
            r.fail("\"sizes\" needs at least one size");
        }
        r.numbers("logs", def.logs, sim::kTreeSizes, 0, 1000);
        r.numbers("fruit", def.fruit, sim::kTreeSizes, 0, 1000);
        def.landmark = r.flag("landmark");
        // Phase 55: a giant names the biome it stands in (found once the
        // biomes are read) and how near its water it must be.
        std::string giant_biome = r.text("giantBiome", false, 200);
        def.giant_water_m = static_cast<std::uint16_t>(r.integer("giantWater", 0, 250, 0));
        // The files of each state (phase 51), with their far versions.
        r.state_models(mod_dir, kTreeStateNames, def.state_models, def.state_far, sim::kTreeStates, refs, def.name_key);
        if (r.ok()) {
            giant_biomes.push_back(std::move(giant_biome));
            out.flora.species.push_back(std::move(def));
        }
    }
    const auto find_species = [&](std::string_view id) { return out.flora.find_species(id); };
    // Biomes.
    for (const RawDef* d : biomes) {
        Reader r(*d, errors);
        sim::BiomeDef def;
        def.id = d->id;
        def.name_key = r.text("name", true);
        for (const auto& [s, w] : r.table("species", find_species, 0, 10000, 64)) {
            def.species.push_back({static_cast<std::uint8_t>(s), static_cast<std::uint16_t>(w)});
        }
        r.numbers("sizeWeights", def.size_weights, sim::kTreeSizes, 0, 10000);
        def.density = static_cast<std::uint16_t>(r.integer("density", 0, 400, 100));
        def.grass = static_cast<std::uint8_t>(r.integer("grass", 0, 255, 180));
        def.flowers = static_cast<std::uint16_t>(r.integer("flowers", 0, 400, 100));
        static constexpr std::string_view kBiomeCovers[] = {"ferns", "clover", "dryGrass", "petals", "scree", "crag", "alpine"};
        static_assert(std::size(kBiomeCovers) == static_cast<std::size_t>(sim::BiomeCover::Count));
        def.cover = r.choices("cover", kBiomeCovers);
        static constexpr std::string_view kBushKinds[] = {"berries", "blueberries", "thorn"};
        static_assert(std::size(kBushKinds) == static_cast<std::size_t>(sim::BushKind::Count));
        def.bush = static_cast<std::uint8_t>(r.choice("bush", kBushKinds, 0));
        static constexpr std::string_view kRockKinds[] = {"gray", "mossy", "sandstone"};
        static_assert(std::size(kRockKinds) == static_cast<std::size_t>(sim::RockKind::Count));
        def.rock = static_cast<std::uint8_t>(r.choice("rock", kRockKinds, 0));
        def.mammoths = r.flag("mammoths");
        def.unicorn = r.flag("unicorn");
        // Phase 54: where it grows. Ranges are [low, high], 0 to 100.
        const auto range = [&](const char* key, std::uint8_t* out2) {
            r.numbers(key, out2, 2, 0, 100);
            if (out2[0] > out2[1]) {
                r.fail(std::format("\"{}\" must be [low, high]", key));
            }
        };
        range("temperature", def.temperature);
        range("humidity", def.humidity);
        range("altitude", def.altitude);
        def.water = static_cast<sim::BiomeWater>(r.choice("water", kBiomeWaters, 0));
        def.water_m = static_cast<std::uint16_t>(r.integer("waterDistance", 0, 250, 0));
        if ((def.water == sim::BiomeWater::Any) != (def.water_m == 0)) {
            r.fail("\"water\" (fresh or sea) and \"waterDistance\" go together");
        }
        def.regions = r.choices("regions", kBiomeRegions);
        def.weight = static_cast<std::uint16_t>(r.integer("weight", 1, 1000, 100));
        if (r.ok()) {
            out.flora.biomes.push_back(std::move(def));
        }
    }
    if (out.flora.biomes.empty()) {
        errors.push_back({"", "the content has no biomes"});
    }
    for (std::size_t i = 0; i < out.flora.species.size() && i < giant_biomes.size(); ++i) {
        if (giant_biomes[i].empty()) {
            continue;
        }
        const int b = out.flora.find_biome(giant_biomes[i]);
        if (b < 0) {
            errors.push_back({out.flora.species[i].id, std::format("\"giantBiome\" refers to '{}', which does not exist", giant_biomes[i])});
        } else if (!out.flora.species_has_size(i, sim::TreeSize::Huge)) {
            errors.push_back({out.flora.species[i].id, "a giant needs the size \"huge\""});
        } else {
            out.flora.species[i].giant_biome = static_cast<std::int16_t>(b);
        }
    }
}

}  // namespace sc::mods
