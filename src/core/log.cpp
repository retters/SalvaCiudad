#include "core/log.h"

#include <chrono>
#include <cstdio>
#include <mutex>
#include <string>
#include <system_error>

#ifdef _WIN32
#include <share.h>
#endif

namespace sc::log {

namespace {

constexpr std::string_view kFileStem = "salvaciudad";

struct State {
    std::mutex mutex;
    std::FILE* file = nullptr;
    std::filesystem::path dir;
    std::uintmax_t written = 0;
    Options options;
};

State& state() {
    static State s;
    return s;
}

std::filesystem::path log_path(const std::filesystem::path& dir, int index) {
    std::string name(kFileStem);
    if (index > 0) {
        name += '.';
        name += std::to_string(index);
    }
    name += ".log";
    return dir / name;
}

std::FILE* open_for_append(const std::filesystem::path& path) {
#ifdef _WIN32
    // Other processes may read the log while the game runs, but not write it.
    return _wfsopen(path.c_str(), L"ab", _SH_DENYWR);
#else
    return std::fopen(path.c_str(), "ab");
#endif
}

// Shifts salvaciudad.log -> .1 -> .2 ..., dropping the oldest. Errors are
// ignored: a failed rotation only means an older log is overwritten or kept.
void rotate_files(const std::filesystem::path& dir, int kept_files) {
    std::error_code ec;
    if (kept_files < 1) {
        kept_files = 1;
    }
    std::filesystem::remove(log_path(dir, kept_files - 1), ec);
    for (int i = kept_files - 2; i >= 0; --i) {
        const auto from = log_path(dir, i);
        if (std::filesystem::exists(from, ec)) {
            std::filesystem::rename(from, log_path(dir, i + 1), ec);
        }
    }
}

std::string_view level_name(Level level) {
    switch (level) {
        case Level::Debug: return "DEBUG";
        case Level::Info: return "INFO ";
        case Level::Warn: return "WARN ";
        case Level::Error: return "ERROR";
    }
    return "?????";
}

}  // namespace

bool open(const std::filesystem::path& dir, const Options& options) {
    State& s = state();
    std::lock_guard lock(s.mutex);
    if (s.file != nullptr) {
        std::fclose(s.file);
        s.file = nullptr;
    }
    s.options = options;
    s.dir = dir;
    s.written = 0;
    std::error_code ec;
    std::filesystem::create_directories(dir, ec);
    const auto current = log_path(dir, 0);
    if (std::filesystem::exists(current, ec) && std::filesystem::file_size(current, ec) > 0) {
        rotate_files(dir, options.kept_files);
    }
    s.file = open_for_append(current);
    return s.file != nullptr;
}

void close() {
    State& s = state();
    std::lock_guard lock(s.mutex);
    if (s.file != nullptr) {
        std::fclose(s.file);
        s.file = nullptr;
    }
}

bool is_open() {
    State& s = state();
    std::lock_guard lock(s.mutex);
    return s.file != nullptr;
}

std::filesystem::path current_file() {
    State& s = state();
    std::lock_guard lock(s.mutex);
    return s.file != nullptr ? log_path(s.dir, 0) : std::filesystem::path{};
}

void write(Level level, std::string_view message) {
    State& s = state();
    std::lock_guard lock(s.mutex);
    if (level < s.options.min_level) {
        return;
    }
    const auto now = std::chrono::floor<std::chrono::milliseconds>(std::chrono::system_clock::now());
    // UTC, so logs from players in different time zones line up.
    std::string line = std::format("{:%Y-%m-%d %H:%M:%S}Z {} ", now, level_name(level));
    // Keep one entry per line even if a message contains line breaks.
    for (const char c : message) {
        line += (c == '\n' || c == '\r') ? ' ' : c;
    }
    line += '\n';

    if (s.options.echo_to_stderr) {
        std::fwrite(line.data(), 1, line.size(), stderr);
    }
    if (s.file == nullptr) {
        return;
    }
    if (s.written + line.size() > s.options.max_file_bytes) {
        std::fclose(s.file);
        s.file = nullptr;
        rotate_files(s.dir, s.options.kept_files);
        s.file = open_for_append(log_path(s.dir, 0));
        s.written = 0;
        if (s.file == nullptr) {
            return;
        }
    }
    if (std::fwrite(line.data(), 1, line.size(), s.file) == line.size()) {
        s.written += line.size();
    }
    // Flush warnings and errors right away so they survive a crash.
    if (level >= Level::Warn) {
        std::fflush(s.file);
    }
}

}  // namespace sc::log
