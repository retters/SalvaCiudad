// Definitions from the mods' `defs/*.json`, merged in load order: a mod adds
// definitions, patches fields of earlier ones ("type": "building", "patch":
// "core:house") or removes them ("type": "building", "remove": "core:house").
// Ids are unique within each type. Once everything is merged, each
// definition is checked and turned into the simulation's content.
#pragma once

#include <filesystem>
#include <functional>
#include <string>
#include <string_view>
#include <vector>

#include "core/json.h"
#include "mods/mod_library.h"
#include "sim/content.h"

namespace sc::mods {

struct DefError {
    std::string mod;      // The mod to blame.
    std::string message;  // English.
};

struct RawDef {
    std::string type;
    std::string id;
    json::MutDoc doc;         // Owns `obj`.
    yyjson_mut_val* obj = nullptr;
    std::string mod;          // Last mod that added or patched it.
    std::string model_mod;    // Mod whose folder holds its model files.
};

class DefSet {
public:
    // Adds one `defs/*.json` file of `mod`. Errors of single entries are
    // recorded and the entry is skipped; a broken file adds one error.
    void add_file(std::string_view json_text, const std::string& mod, const std::string& file_name,
                  std::vector<DefError>& errors);

    [[nodiscard]] const std::vector<RawDef>& defs() const { return defs_; }

private:
    [[nodiscard]] RawDef* find(std::string_view type, std::string_view id);

    std::vector<RawDef> defs_;
};

// Checks every definition and fills `out` (except `hash`). `mod_dir` gives
// each mod's folder, to find model files. Definitions with errors are left
// out and the errors blame the mod that last changed them. With `refs`,
// also lists the model files the definitions use.
void build_content(const DefSet& defs, const std::function<std::filesystem::path(const std::string&)>& mod_dir,
                   sim::Content& out, std::vector<DefError>& errors, std::vector<ModelRef>* refs = nullptr);

// Definition ids: "<mod>:<name>", name of 1..48 characters of [a-z0-9_].
[[nodiscard]] bool is_valid_def_id(std::string_view id);

}  // namespace sc::mods
