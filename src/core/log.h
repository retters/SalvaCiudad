// Engine log: English messages, written to a rotating file in the user data
// folder. Thread-safe. Never log personal data unless it is needed to
// diagnose a problem.
#pragma once

#include <cstdint>
#include <filesystem>
#include <format>
#include <string_view>
#include <utility>

namespace sc::log {

enum class Level : std::uint8_t { Debug, Info, Warn, Error };

struct Options {
    std::uintmax_t max_file_bytes = 2u * 1024u * 1024u;
    int kept_files = 3;       // salvasprosperia.log plus .1 ... .(kept_files - 1)
    bool echo_to_stderr = false;
    Level min_level = Level::Info;
};

// Opens `<dir>/salvasprosperia.log`, rotating the previous log first. Returns
// false if the file cannot be opened; logging then only goes to stderr (if
// enabled) and the game keeps running.
bool open(const std::filesystem::path& dir, const Options& options);
void close();

[[nodiscard]] bool is_open();
[[nodiscard]] std::filesystem::path current_file();

void write(Level level, std::string_view message);

template <typename... Args>
void debug(std::format_string<Args...> fmt, Args&&... args) {
    write(Level::Debug, std::format(fmt, std::forward<Args>(args)...));
}

template <typename... Args>
void info(std::format_string<Args...> fmt, Args&&... args) {
    write(Level::Info, std::format(fmt, std::forward<Args>(args)...));
}

template <typename... Args>
void warn(std::format_string<Args...> fmt, Args&&... args) {
    write(Level::Warn, std::format(fmt, std::forward<Args>(args)...));
}

template <typename... Args>
void error(std::format_string<Args...> fmt, Args&&... args) {
    write(Level::Error, std::format(fmt, std::forward<Args>(args)...));
}

}  // namespace sc::log
