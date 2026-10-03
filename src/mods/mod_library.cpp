#include "mods/mod_library.h"

#include <algorithm>
#include <format>
#include <system_error>

#include "core/file_io.h"
#include "core/log.h"
#include "core/text.h"
#include "mods/defs.h"

namespace sc::mods {

namespace {

std::uint64_t fnv(std::string_view bytes, std::uint64_t h) {
    for (const char c : bytes) {
        h ^= static_cast<std::uint8_t>(c);
        h *= 0x100000001b3ull;
    }
    return h;
}

constexpr std::uint64_t kFnvBasis = 0xcbf29ce484222325ull;

// Files of a folder, recursively, as sorted relative generic paths.
bool list_files(const std::filesystem::path& dir, std::vector<std::string>& out, std::string& error) {
    std::error_code ec;
    std::filesystem::recursive_directory_iterator it(dir, std::filesystem::directory_options::none, ec);
    if (ec) {
        error = "cannot read the folder";
        return false;
    }
    for (const std::filesystem::recursive_directory_iterator end; it != end; it.increment(ec)) {
        if (ec) {
            error = "cannot read the folder";
            return false;
        }
        std::error_code ec2;
        if (it->is_regular_file(ec2)) {
            if (out.size() >= limits::kMaxFilesPerMod) {
                error = "too many files";
                return false;
            }
            std::string rel = text::path_to_utf8(it->path().lexically_relative(dir));
            std::replace(rel.begin(), rel.end(), '\\', '/');
            out.push_back(std::move(rel));
        }
    }
    std::sort(out.begin(), out.end());
    return true;
}

// Sorted *.json files directly in a folder.
std::vector<std::filesystem::path> json_files(const std::filesystem::path& dir) {
    std::vector<std::filesystem::path> files;
    std::error_code ec;
    std::filesystem::directory_iterator it(dir, ec);
    if (ec) {
        return files;
    }
    for (const std::filesystem::directory_iterator end; it != end; it.increment(ec)) {
        if (ec) {
            break;
        }
        std::error_code ec2;
        if (it->is_regular_file(ec2) && it->path().extension() == ".json") {
            files.push_back(it->path());
        }
    }
    std::sort(files.begin(), files.end());
    return files;
}

}  // namespace

std::filesystem::path mod_file(const std::filesystem::path& mod_dir, std::string_view relative) {
    if (relative.empty() || relative.size() > 240 || relative.find('\\') != std::string_view::npos ||
        relative.find(':') != std::string_view::npos || relative.front() == '/') {
        return {};
    }
    const std::filesystem::path rel = text::path_from_utf8(relative);
    if (rel.empty() || rel.is_absolute() || rel.has_root_name() || rel.has_root_directory()) {
        return {};
    }
    for (const auto& part : rel) {
        if (part == ".." || part == ".") {
            return {};
        }
    }
    return mod_dir / rel;
}

std::filesystem::path BuildResult::dir(std::string_view mod) const {
    for (std::size_t i = 0; i < load_order.size() && i < dirs.size(); ++i) {
        if (load_order[i] == mod) {
            return dirs[i];
        }
    }
    return {};
}

std::uint64_t hash_folder(const std::filesystem::path& dir, std::string& error) {
    std::vector<std::string> files;
    if (!list_files(dir, files, error)) {
        return 0;
    }
    std::uint64_t h = kFnvBasis;
    for (const std::string& rel : files) {
        const fs::ReadResult r = fs::read_file(dir / text::path_from_utf8(rel), limits::kMaxFileBytes);
        if (r.error != fs::IoError::None) {
            error = std::format("cannot read '{}'", rel);
            return 0;
        }
        h = fnv(rel, h);
        h = fnv(std::string_view("\0", 1), h);
        h = fnv(std::to_string(r.data.size()), h);
        h = fnv(r.data, h);
    }
    return h;
}

void ModLibrary::scan(const std::filesystem::path& builtin_dir, const std::filesystem::path& user_dir,
                      const Version& game) {
    mods_.clear();
    for (const bool builtin : {true, false}) {
        const std::filesystem::path& root = builtin ? builtin_dir : user_dir;
        if (root.empty()) {
            continue;
        }
        std::error_code ec;
        std::filesystem::directory_iterator it(root, ec);
        if (ec) {
            continue;
        }
        std::vector<std::filesystem::path> dirs;
        for (const std::filesystem::directory_iterator end; it != end; it.increment(ec)) {
            if (ec) {
                break;
            }
            std::error_code ec2;
            if (it->is_directory(ec2)) {
                dirs.push_back(it->path());
            }
        }
        std::sort(dirs.begin(), dirs.end());
        for (const std::filesystem::path& dir : dirs) {
            if (mods_.size() >= limits::kMaxMods) {
                log::warn("mods: more than {} mods; the rest are ignored", limits::kMaxMods);
                break;
            }
            const fs::ReadResult r = fs::read_file(dir / "mod.json", limits::kMaxManifestBytes);
            if (r.error == fs::IoError::NotFound) {
                continue;  // Not a mod folder.
            }
            ModInfo info;
            info.dir = dir;
            info.builtin = builtin;
            if (r.error != fs::IoError::None) {
                info.errors.emplace_back("cannot read mod.json");
            } else if (!parse_manifest(r.data, info.manifest, info.errors)) {
                // Errors recorded.
            } else if (!info.manifest.game_version.contains(game)) {
                info.errors.push_back(std::format("needs another version of the game (this is {})", version_text(game)));
            }
            if (info.manifest.id.empty()) {
                info.manifest.id = text::path_to_utf8(dir.filename());
            }
            if (find(info.manifest.id) != nullptr) {
                info.errors.push_back(std::format("another mod already uses the id '{}'", info.manifest.id));
                info.manifest.id += builtin ? "#builtin" : "#user";
            }
            std::string error;
            info.hash = hash_folder(dir, error);
            if (!error.empty()) {
                info.errors.push_back(error);
            }
            info.enabled = info.manifest.id == kCoreModId;
            mods_.push_back(std::move(info));
            log::info("mods: found '{}' {} ({}){}", mods_.back().manifest.id, version_text(mods_.back().manifest.version),
                      builtin ? "built-in" : "user", mods_.back().errors.empty() ? "" : ", with errors");
        }
    }
}

const ModInfo* ModLibrary::find(std::string_view id) const {
    for (const ModInfo& m : mods_) {
        if (m.manifest.id == id) {
            return &m;
        }
    }
    return nullptr;
}

void ModLibrary::select(const std::vector<std::string>& enabled) {
    order_.clear();
    for (ModInfo& m : mods_) {
        m.enabled = m.manifest.id == kCoreModId;
    }
    for (const std::string& id : enabled) {
        for (ModInfo& m : mods_) {
            if (m.manifest.id == id && id != kCoreModId && !m.enabled) {
                m.enabled = true;
                order_.push_back(id);
            }
        }
    }
}

std::vector<std::string> ModLibrary::enabled_ids() const {
    std::vector<std::string> out;
    for (const std::string& id : order_) {
        const ModInfo* m = find(id);
        if (m != nullptr && m->enabled) {
            out.push_back(id);
        }
    }
    // Enabled mods not yet in the order go last.
    for (const ModInfo& m : mods_) {
        if (m.enabled && m.manifest.id != kCoreModId && std::find(out.begin(), out.end(), m.manifest.id) == out.end()) {
            out.push_back(m.manifest.id);
        }
    }
    return out;
}

void ModLibrary::move(std::string_view id, int delta) {
    order_ = enabled_ids();
    const auto it = std::find(order_.begin(), order_.end(), id);
    if (it == order_.end()) {
        return;
    }
    const auto pos = static_cast<int>(it - order_.begin());
    const int to = std::clamp(pos + delta, 0, static_cast<int>(order_.size()) - 1);
    std::swap(order_[static_cast<std::size_t>(pos)], order_[static_cast<std::size_t>(to)]);
}

// Core first, then the enabled mods in the player's order, moved later when
// a dependency or "loadAfter" asks for it. Mods with missing dependencies or
// in a cycle are left out.
std::vector<std::size_t> ModLibrary::load_order() {
    std::vector<std::size_t> wanted;
    const auto index = [&](std::string_view id) -> int {
        for (std::size_t i = 0; i < mods_.size(); ++i) {
            if (mods_[i].manifest.id == id) {
                return static_cast<int>(i);
            }
        }
        return -1;
    };
    const int core = index(kCoreModId);
    if (core >= 0 && mods_[static_cast<std::size_t>(core)].errors.empty()) {
        wanted.push_back(static_cast<std::size_t>(core));
    }
    for (const std::string& id : enabled_ids()) {
        const int i = index(id);
        if (i >= 0 && mods_[static_cast<std::size_t>(i)].errors.empty()) {
            wanted.push_back(static_cast<std::size_t>(i));
        }
    }
    // Drop mods whose dependencies are not enabled (repeat: dropping one may
    // break another).
    for (bool changed = true; changed;) {
        changed = false;
        for (std::size_t w = 0; w < wanted.size(); ++w) {
            ModInfo& m = mods_[wanted[w]];
            for (const std::string& dep : m.manifest.dependencies) {
                const int di = index(dep);
                if (di < 0 || std::find(wanted.begin(), wanted.end(), static_cast<std::size_t>(di)) == wanted.end()) {
                    m.errors.push_back(std::format("needs the mod '{}', which is not enabled", dep));
                    wanted.erase(wanted.begin() + static_cast<std::ptrdiff_t>(w));
                    changed = true;
                    break;
                }
            }
            if (changed) {
                break;
            }
        }
    }
    // Stable topological order over dependencies and loadAfter.
    std::vector<std::size_t> order;
    std::vector<std::size_t> pending = wanted;
    while (!pending.empty()) {
        bool placed = false;
        for (std::size_t p = 0; p < pending.size(); ++p) {
            const ModInfo& m = mods_[pending[p]];
            bool ready = true;
            for (const auto* list : {&m.manifest.dependencies, &m.manifest.load_after}) {
                for (const std::string& dep : *list) {
                    const int di = index(dep);
                    if (di >= 0 && std::find(pending.begin(), pending.end(), static_cast<std::size_t>(di)) != pending.end() &&
                        static_cast<std::size_t>(di) != pending[p]) {
                        ready = false;
                    }
                }
            }
            if (ready) {
                order.push_back(pending[p]);
                pending.erase(pending.begin() + static_cast<std::ptrdiff_t>(p));
                placed = true;
                break;
            }
        }
        if (!placed) {
            for (const std::size_t p : pending) {
                mods_[p].errors.emplace_back("its load order forms a cycle with other mods");
            }
            break;
        }
    }
    return order;
}

BuildResult ModLibrary::build() {
    BuildResult result;
    for (ModInfo& m : mods_) {
        m.loaded = false;
        // Keep errors of the manifest and files; drop those of a previous build.
        std::erase_if(m.errors, [](const std::string& e) { return e.starts_with("[defs] ") || e.starts_with("needs the mod") ||
                                                                   e.starts_with("its load order"); });
    }
    std::vector<std::size_t> order = load_order();
    const auto dir_of = [&](const std::string& id) -> std::filesystem::path {
        const ModInfo* m = find(id);
        return m != nullptr ? m->dir : std::filesystem::path{};
    };
    // The models of every attempt, so those of mods left out still show.
    std::vector<ModelRef> refs;
    const auto same = [](const ModelRef& a, const ModelRef& b) {
        return a.def_id == b.def_id && a.mod == b.mod && a.path == b.path;
    };
    // Build; if a mod has errors, leave it out and build again.
    for (int attempt = 0; attempt < 16; ++attempt) {
        DefSet set;
        std::vector<DefError> errors;
        for (const std::size_t i : order) {
            const ModInfo& m = mods_[i];
            for (const std::filesystem::path& file : json_files(m.dir / "defs")) {
                const fs::ReadResult r = fs::read_file(file, limits::kMaxDefFileBytes);
                if (r.error != fs::IoError::None) {
                    errors.push_back({m.manifest.id, std::format("cannot read defs/{}", text::path_to_utf8(file.filename()))});
                    continue;
                }
                set.add_file(r.data, m.manifest.id, text::path_to_utf8(file.filename()), errors);
            }
        }
        result.content = sim::Content{};
        std::vector<ModelRef> attempt_refs;
        build_content(set, dir_of, result.content, errors, &attempt_refs);
        for (ModelRef& ref : attempt_refs) {
            if (std::none_of(refs.begin(), refs.end(), [&](const ModelRef& m) { return same(m, ref); })) {
                refs.push_back(std::move(ref));
            }
        }
        // Errors that blame a mod other than core drop that mod.
        std::vector<std::string> blamed;
        for (const DefError& e : errors) {
            const std::string who = e.mod.empty() ? std::string(kCoreModId) : e.mod;
            for (ModInfo& m : mods_) {
                if (m.manifest.id == who) {
                    m.errors.push_back("[defs] " + e.message);
                }
            }
            if (who != kCoreModId && std::find(blamed.begin(), blamed.end(), who) == blamed.end()) {
                blamed.push_back(who);
            }
            log::warn("mods: {}: {}", who, e.message);
        }
        if (blamed.empty()) {
            break;
        }
        std::erase_if(order, [&](std::size_t i) {
            return std::find(blamed.begin(), blamed.end(), mods_[i].manifest.id) != blamed.end();
        });
        // Mods that depended on a dropped one go too.
        std::erase_if(order, [&](std::size_t i) {
            for (const std::string& dep : mods_[i].manifest.dependencies) {
                if (std::find(blamed.begin(), blamed.end(), dep) != blamed.end()) {
                    mods_[i].errors.push_back(std::format("needs the mod '{}', which has errors", dep));
                    return true;
                }
            }
            return false;
        });
    }
    result.model_refs = std::move(refs);
    std::uint64_t hash = kFnvBasis;
    for (const std::size_t i : order) {
        ModInfo& m = mods_[i];
        m.loaded = true;
        result.load_order.push_back(m.manifest.id);
        result.dirs.push_back(m.dir);
        if (m.manifest.affects_simulation) {
            hash = fnv(m.manifest.id, hash);
            hash = fnv(version_text(m.manifest.version), hash);
            hash ^= m.hash;
            hash *= 0x100000001b3ull;
        }
        for (const std::filesystem::path& file : json_files(m.dir / "lang")) {
            result.language_files.push_back(file);
        }
        const fs::ReadResult script = fs::read_file(m.dir / "scripts" / "main.lua", limits::kMaxScriptBytes);
        if (script.error == fs::IoError::None) {
            result.scripts.push_back({m.manifest.id, m.dir, script.data});
        } else if (script.error != fs::IoError::NotFound) {
            m.errors.emplace_back("cannot read scripts/main.lua");
        }
    }
    result.content.hash = hash;
    log::info("mods: loaded {} mod(s): {} resources, {} buildings, {} species, {} biomes, hash {:016x}", order.size(),
              result.content.resources.size(), result.content.buildings.size(), result.content.flora.species.size(),
              result.content.flora.biomes.size(), hash);
    return result;
}

}  // namespace sc::mods
