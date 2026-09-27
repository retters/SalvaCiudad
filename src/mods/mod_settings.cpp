#include "mods/mod_settings.h"

#include "core/file_io.h"
#include "core/json.h"
#include "core/log.h"
#include "mods/mod_library.h"
#include "mods/mod_manifest.h"

namespace sc::mods {

namespace {
constexpr std::size_t kMaxBytes = 64 * 1024;
}

ModSelection load_selection(const std::filesystem::path& file) {
    ModSelection sel;
    const fs::ReadResult r = fs::read_file(file, kMaxBytes);
    if (r.error == fs::IoError::NotFound) {
        return sel;
    }
    json::ParseResult parsed = r.error == fs::IoError::None ? json::parse_object(r.data) : json::ParseResult{};
    yyjson_mut_val* list = parsed.doc ? yyjson_mut_obj_get(yyjson_mut_doc_get_root(parsed.doc.get()), "enabled") : nullptr;
    if (r.error != fs::IoError::None || parsed.error != json::ParseError::None || !yyjson_mut_is_arr(list)) {
        log::warn("mods: mods.json is damaged; quarantined, starting without extra mods");
        (void)fs::quarantine_file(file);
        return sel;
    }
    std::size_t idx = 0, max = 0;
    yyjson_mut_val* item = nullptr;
    yyjson_mut_arr_foreach(list, idx, max, item) {
        const char* id = yyjson_mut_get_str(item);
        if (id != nullptr && is_valid_mod_id(id) && sel.enabled.size() < limits::kMaxMods) {
            sel.enabled.emplace_back(id);
        } else {
            log::warn("mods: mods.json has an invalid entry, ignored");
        }
    }
    return sel;
}

bool save_selection(const std::filesystem::path& file, const ModSelection& selection) {
    json::MutDoc doc = json::new_object_doc();
    if (!doc) {
        return false;
    }
    yyjson_mut_val* root = yyjson_mut_doc_get_root(doc.get());
    bool ok = json::set_int(doc.get(), root, "schemaVersion", 1);
    yyjson_mut_val* list = yyjson_mut_arr(doc.get());
    for (const std::string& id : selection.enabled) {
        ok = ok && list != nullptr && yyjson_mut_arr_add_strcpy(doc.get(), list, id.c_str());
    }
    ok = ok && yyjson_mut_obj_add_val(doc.get(), root, "enabled", list);
    const std::string text = ok ? json::write_pretty(doc.get()) : std::string{};
    if (text.empty() || fs::write_file_atomic(file, text) != fs::IoError::None) {
        log::error("mods: cannot save mods.json");
        return false;
    }
    return true;
}

}  // namespace sc::mods
