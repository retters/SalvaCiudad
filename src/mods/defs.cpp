#include "mods/defs.h"

#include <algorithm>
#include <format>
#include <system_error>

#include "mods/mod_library.h"

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

constexpr std::string_view kTypes[] = {"resource", "mapFeature", "building", "recipe", "species", "biome", "mapType",
                                        "crop",     "disease",    "unit",    "tutorial", "race"};
constexpr std::string_view kSkillNames[] = {"wood", "stone", "forage", "farm",  "orchard",
                                            "hunt", "fish",  "build",  "craft", "metal"};
constexpr std::string_view kTutorialGoals[] = {"none",  "camera", "place",      "build", "workers",
                                               "speed", "stock",  "population", "lua"};
constexpr std::string_view kTutorialSizes[] = {"small", "medium"};
constexpr std::string_view kDiseaseSources[] = {"cold", "water", "rats"};
constexpr std::string_view kSeasons[] = {"spring", "summer", "autumn", "winter"};

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
constexpr std::string_view kWorkKinds[] = {"none", "gather", "produce", "build", "haul", "farm", "hunt", "fish"};
constexpr std::string_view kBuildingKinds[] = {"house",   "storage", "workplace", "townCenter", "decoration",
                                               "defense", "military", "market"};
constexpr std::string_view kBuildCategories[] = {"housing",  "food",       "resources", "industry",
                                                 "services", "decoration", "defense"};
constexpr std::string_view kNeeds[] = {"food",   "water",  "clothes", "shoes",  "religion", "entertainment",
                                       "heating", "beauty", "market",  "hygiene", "healer",  "doctor"};
constexpr std::string_view kFeatureKinds[] = {"tree", "stone", "ironOre", "berryBush", "herbs"};
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
                if (std::string_view(key) == "model" || std::string_view(key) == "models") {
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
    std::vector<const RawDef*> resources, features, buildings, recipes, species, biomes, map_types, crops, diseases,
        units, tutorials, races;
    for (const RawDef& d : set.defs()) {
        if (d.type == "resource") resources.push_back(&d);
        else if (d.type == "mapFeature") features.push_back(&d);
        else if (d.type == "building") buildings.push_back(&d);
        else if (d.type == "recipe") recipes.push_back(&d);
        else if (d.type == "species") species.push_back(&d);
        else if (d.type == "biome") biomes.push_back(&d);
        else if (d.type == "mapType") map_types.push_back(&d);
        else if (d.type == "crop") crops.push_back(&d);
        else if (d.type == "disease") diseases.push_back(&d);
        else if (d.type == "unit") units.push_back(&d);
        else if (d.type == "tutorial") tutorials.push_back(&d);
        else if (d.type == "race") races.push_back(&d);
    }
    if (species.size() > sim::kMaxSpecies || biomes.size() > sim::kMaxBiomes || map_types.size() > sim::kMaxMapTypes ||
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
        def.weight = r.integer("weight", 1, 12, 1);
        def.carry = r.integer("carry", 0, 1000, 0);
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
        def.body = r.text("body", true, 32);
        if (!def.body.empty() && !std::all_of(def.body.begin(), def.body.end(), [](char c) {
                return (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '_';
            })) {
            r.fail("\"body\" must be a plain file name ([a-z0-9_])");
        } else if (!def.body.empty() && refs != nullptr) {
            // The game takes every body from core; a missing one is only
            // left out of the crowd, so it is not an error here.
            for (const bool female : {false, true}) {
                const std::string rel = sim::race_body_file(def.body, female);
                const std::filesystem::path path = mod_file(mod_dir(kCoreModId), rel);
                std::error_code ec;
                refs->push_back({d->type, d->id, def.name_key, kCoreModId, rel,
                                 !path.empty() && std::filesystem::is_regular_file(path, ec)});
            }
        }
        def.move = r.integer("move", 50, 200, 100);
        def.cold = r.integer("cold", -100, 90, 0);
        def.disease = r.integer("disease", -100, 90, 0);
        def.night_vision = r.flag("nightVision");
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
        if (r.ok() && out.crops.size() < 250) {
            out.crops.push_back(std::move(def));
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
        // Features have no name of their own: the viewer shows the resource's.
        def.models = r.models(mod_dir, false, refs,
                              ri < 0 ? std::string{} : out.resources[static_cast<std::size_t>(ri)].name_key);
        def.mod = d->model_mod;
        if (r.ok()) {
            out.features.push_back(std::move(def));
        }
    }
    // Buildings.
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
        def.gathers = r.choices("gathers", kFeatureKinds);
        def.work_radius = r.integer("radius", 0, 500, 0);
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
        def.trains = r.flag("trains");
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
        def.evergreen = r.flag("evergreen");
        const std::string prefix = r.text("model", true, 200);
        for (std::size_t s = 0; s < sim::kTreeSizes && r.ok(); ++s) {
            if (((def.sizes >> s) & 1u) == 0) {
                continue;
            }
            const std::string rel = prefix + "_" + sim::size_info(static_cast<sim::TreeSize>(s)).id + ".glb";
            const std::filesystem::path path = mod_file(mod_dir(d->model_mod), rel);
            std::error_code ec;
            const bool exists = !path.empty() && std::filesystem::is_regular_file(path, ec);
            if (!exists) {
                r.fail(std::format("model '{}' not found in mod '{}'", rel, d->model_mod));
            }
            if (refs != nullptr) {
                refs->push_back({d->type, d->id, def.name_key, d->model_mod, rel, exists});
            }
        }
        def.model = prefix;
        if (r.ok()) {
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
        if (r.ok()) {
            out.flora.biomes.push_back(std::move(def));
        }
    }
    const auto find_biome = [&](std::string_view id) { return out.flora.find_biome(id); };
    // Map types.
    for (const RawDef* d : map_types) {
        Reader r(*d, errors);
        sim::MapTypeDef def;
        def.id = d->id;
        def.name_key = r.text("name", true);
        for (const auto& [b, w] : r.table("biomes", find_biome, 0, 10000, 64)) {
            def.biomes.push_back({static_cast<std::uint8_t>(b), static_cast<std::uint16_t>(w)});
        }
        r.numbers("sizeBias", def.size_bias, sim::kTreeSizes, 0, 1000);
        def.patch_m = r.integer("patchSize", 0, 5000, 350);
        def.islands = r.flag("islands");
        if (r.ok()) {
            out.flora.map_types.push_back(std::move(def));
        }
    }
    if (out.flora.map_types.empty() || out.flora.biomes.empty()) {
        errors.push_back({"", "the content has no map types or no biomes"});
    }
}

}  // namespace sc::mods
