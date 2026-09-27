#include "platform/paths.h"

#include <system_error>

#include <SDL3/SDL_filesystem.h>
#include <SDL3/SDL_stdinc.h>

#include "core/text.h"

namespace sc {

namespace {

// SDL recommends a non-empty organization; it becomes the parent folder,
// for example %APPDATA%\Salva\SalvaCiudad on Windows (decision D-101).
constexpr const char* kOrgName = "Salva";
constexpr const char* kAppName = "SalvaCiudad";

bool create_user_dirs(const DataPaths& p) {
    std::error_code ec;
    for (const auto& dir : {p.user_dir, p.logs_dir(), p.saves_dir(), p.user_mods_dir()}) {
        std::filesystem::create_directories(dir, ec);
        if (ec || !std::filesystem::is_directory(dir, ec)) {
            return false;
        }
    }
    return true;
}

// Takes ownership of an SDL-allocated UTF-8 string.
std::filesystem::path take_sdl_path(char* s) {
    if (s == nullptr) {
        return {};
    }
    std::filesystem::path p = text::path_from_utf8(s);
    SDL_free(s);
    return p;
}

}  // namespace

DataPaths choose_data_paths(const std::filesystem::path& install_dir,
                            const std::filesystem::path& platform_user_dir) {
    DataPaths p;
    p.install_dir = install_dir;
    std::error_code ec;
    if (std::filesystem::is_regular_file(install_dir / kPortableMarker, ec)) {
        p.portable = true;
        p.user_dir = install_dir / "userdata";
    } else {
        p.user_dir = platform_user_dir;
    }
    return p;
}

bool prepare_data_paths(DataPaths& paths, const std::filesystem::path& platform_user_dir) {
    if (create_user_dirs(paths)) {
        return true;
    }
    if (paths.portable && !platform_user_dir.empty()) {
        paths.portable = false;
        paths.user_dir = platform_user_dir;
        return create_user_dirs(paths);
    }
    return false;
}

std::optional<DataPaths> resolve_data_paths() {
    const char* base = SDL_GetBasePath();  // Owned by SDL.
    if (base == nullptr) {
        return std::nullopt;
    }
    const std::filesystem::path install_dir = text::path_from_utf8(base);
    const std::filesystem::path user_dir = take_sdl_path(SDL_GetPrefPath(kOrgName, kAppName));
    if (install_dir.empty()) {
        return std::nullopt;
    }
    DataPaths p = choose_data_paths(install_dir, user_dir);
    if (p.user_dir.empty() || !prepare_data_paths(p, user_dir)) {
        return std::nullopt;
    }
    return p;
}

}  // namespace sc
